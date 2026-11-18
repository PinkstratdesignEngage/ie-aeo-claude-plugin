#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fondamenta dal sito: copie di testo delle pagine del cliente in raw/sito/.

Uso:  python3 -I sito_fetch.py <comando> --repo <cartella-kb> --sito <url> [opzioni]

  elenco   robots.txt + sitemap  -> seeds.tsv, piu' la tabella delle sezioni
           da far confermare al consulente prima di scaricare
  fetch    scarica le pagine in perimetro nella cache (gzip, TTL, ripartenza)
  estrai   dalla cache           -> raw/sito/<percorso>.md
  all      i tre in sequenza

Opzioni di perimetro:
  --escludi PREFISSO    sezione o prefisso di path da lasciare fuori (ripetibile)
  --solo PREFISSO       lavora solo su questi prefissi (ripetibile)
  --lingua it           su un sito multilingua per prefisso (/it/, /en/) tiene solo
                        questo ramo. Senza, non filtra per lingua
  --soglia-archivio N   una sezione con piu' di N pagine e' un archivio (blog, news):
                        resta fuori dalle copie pagina per pagina. Default 50
  --limite N            solo le prime N pagine, per le prove

Solo libreria standard, Python 3.9+. Nessun pip install.
Non pubblica e non modifica nulla sul sito del cliente: legge, e scrive in locale.

PERCHE' UNO SCRIPT E NON DEI SUBAGENT
Scaricare ed estrarre testo e' un lavoro deterministico: due esecuzioni devono dare
lo stesso risultato, costare zero token e potersi rilanciare fra un mese per vedere
cosa e' cambiato. Un agente che naviga il sito non da' nessuna delle tre cose. Il
giudizio - quali sezioni contano, cosa diventa una scheda, quale fonte ha ragione -
resta al modello e al consulente, dopo, sui file scaricati.

IDEMPOTENZA
Rilanciarlo non cambia nulla: `fetch` salta cio' che e' in cache entro il TTL, ed
`estrai` riscrive un file solo se il testo e' davvero cambiato. La data di lettura
in testa al file resta ferma finche' il testo e' lo stesso, altrimenti ogni
esecuzione sporcherebbe centinaia di file senza motivo.
"""

import argparse
import collections
import csv
import datetime
import gzip
import hashlib
import html as htmllib
import io
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser

UA = "Mozilla/5.0 (compatible; IE-AEO-kb/1.0; +https://www.example.com)"

CONCORRENZA = 4          # misurato su siti HubSpot: zero errori a 4, transitori a 6-8
TIMEOUT = 45
RETRY = 4
PAUSA = 0.08             # secondi fra due richieste dello stesso worker
TTL_ORE = 168            # una settimana: sotto questa soglia non si rifetcha
MAX_SITEMAP = 50         # quante sitemap figlie seguire da un indice
MAX_CRAWL = 400          # tetto del crawl di ripiego, se la sitemap non c'e'

# Pagine che non dicono nulla su azienda, offerta, clienti o posizionamento.
# E' una lista generica: va bene su quasi tutti i siti, e si allarga con --escludi.
PREFISSI_ESCLUSI = (
    "privacy", "cookie", "note-legali", "legal", "terms", "termini",
    "condizioni", "trattamento-", "whistleblowing", "grazie", "thank-you",
    "thankyou", "ricerca", "search", "cerca", "login", "area-riservata",
    "carrello", "cart", "checkout", "sitemap", "404",
)

# Archivi paginati e tassonomie: le copie pagina per pagina non servono.
SEGMENTI_ARCHIVIO = ("tag", "tags", "category", "categoria", "categorie",
                     "author", "autore", "page", "pagina", "archivio", "archive")

# Nomi che di solito indicano un archivio editoriale, non una sezione commerciale.
# I plurali sono scritti per esteso: un taglio della "s" finale sbaglia in modo
# invisibile (manda "news" in "new") e costa piu' di quanto risolve.
NOMI_ARCHIVIO = ("blog", "blogs", "news", "newsroom", "notizie", "articoli",
                 "articles", "magazine", "insights", "press", "post", "posts",
                 "stories", "novita", "eventi", "events")

# Cromo di navigazione: ripetuto identico su ogni pagina, non e' contenuto.
# Si taglia per tag semantico, mai per posizione. Su un sito che non usa i tag
# semantici questa lista va allargata: guarda l'avviso sulle pagine corte.
TAG_CROMO = ("header", "footer", "nav")
TAG_MUTI = ("script", "style", "noscript", "svg", "iframe", "form")

MIN_CARATTERI = 200      # sotto questa soglia la pagina e' sospetta: JS, o cromo tagliato male


def log(msg):
    print(msg, file=sys.stderr, flush=True)


# --- infrastruttura ---------------------------------------------------------

def scrivi_atomico(path, testo):
    """Scrive via file temporaneo + rename: un'interruzione non lascia file mezzi scritti."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(testo)
    os.replace(tmp, path)


def scrivi_tsv(path, intestazione, righe):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter="\t", lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
    w.writerow(intestazione)
    for r in righe:
        w.writerow(["" if c is None else str(c).replace("\t", " ").replace("\n", " ") for c in r])
    scrivi_atomico(path, buf.getvalue())


def leggi_tsv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def chiave_cache(url):
    return hashlib.sha1(url.encode("utf-8")).hexdigest()


def http_get(url, tentativi=RETRY):
    """GET con gzip. Restituisce (testo, http_status, url_finale) oppure solleva."""
    ultimo = None
    for n in range(tentativi):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": UA,
                "Accept-Encoding": "gzip",
            })
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                dati = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    dati = gzip.decompress(dati)
                return dati.decode("utf-8", "replace"), r.status, r.geturl()
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500:
                return "", e.code, url          # 4xx non si ritenta
            ultimo = e
        except Exception as e:
            ultimo = e
        time.sleep(1.5 * (2 ** n) + 0.3 * n)
    raise ultimo if ultimo else RuntimeError("fetch fallito: " + url)


class Ctx:
    """Percorsi e opzioni, ricavati una volta sola dagli argomenti."""

    def __init__(self, args):
        self.repo = os.path.abspath(os.path.expanduser(args.repo))
        if not os.path.isdir(self.repo):
            raise SystemExit("cartella del repo inesistente: " + self.repo)
        self.sito = (args.sito or "").rstrip("/")
        self.origine = urllib.parse.urlsplit(self.sito).scheme + "://" + \
            urllib.parse.urlsplit(self.sito).netloc if self.sito else ""
        self.cache = os.path.join(self.repo, "_privato", "cache-sito")
        self.html = os.path.join(self.cache, "html")
        self.dest = os.path.join(self.repo, "raw", "sito")
        self.seeds = os.path.join(self.cache, "seeds.tsv")
        self.manifest = os.path.join(self.cache, "manifest.tsv")
        self.args = args
        os.makedirs(self.cache, exist_ok=True)


# --- perimetro --------------------------------------------------------------

def percorso_di(url):
    return urllib.parse.urlsplit(url).path.strip("/")


def segmenti(url, lingua=""):
    """I segmenti di path senza il prefisso di lingua. Su un sito organizzato come
    /it/prodotti/... la sezione e' `prodotti`, non `it`: senza questo, con --lingua
    tutto il sito diventa una sezione sola e passa per archivio."""
    p = percorso_di(url)
    segs = p.split("/") if p else []
    if lingua and segs and segs[0] == lingua:
        segs = segs[1:]
    return segs


def sezione_di(url, lingua=""):
    segs = segmenti(url, lingua)
    return segs[0] if segs else "(home)"


def pare_lingua(seg):
    return bool(re.fullmatch(r"[a-z]{2}(-[a-z]{2})?", seg or ""))


def fuori_perimetro(url, args):
    """True se la pagina non ha motivo di stare nelle fondamenta. Generico: niente
    nomi di sezione del cliente qui dentro, quelli arrivano da --escludi."""
    p = percorso_di(url)
    segs = p.split("/") if p else []
    primo = segs[0] if segs else ""
    if any(p.startswith(x) for x in PREFISSI_ESCLUSI):
        return "pagina di servizio"
    if any(s in SEGMENTI_ARCHIVIO for s in segs):
        return "archivio o tassonomia"
    if args.lingua and pare_lingua(primo) and primo != args.lingua:
        return "altra lingua"
    for x in args.escludi:
        if p == x.strip("/") or p.startswith(x.strip("/") + "/"):
            return "escluso a mano"
    if args.solo:
        if not any(p == x.strip("/") or p.startswith(x.strip("/") + "/") for x in args.solo):
            return "fuori da --solo"
    return ""


def nome_file(url, lingua=""):
    """/case-study/air-dolomiti -> case-study__air-dolomiti.md"""
    segs = segmenti(url, lingua)
    nome = "__".join(segs) if segs else "home"
    nome = re.sub(r"[^A-Za-z0-9._-]+", "-", nome).strip("-") or "pagina"
    return nome[:120] + ".md"


# --- scoperta degli URL -----------------------------------------------------

def sitemap_da_robots(ctx):
    """Le sitemap dichiarate in robots.txt, piu' il robotparser per le Disallow."""
    url = ctx.origine + "/robots.txt"
    sitemaps = []
    rp = urllib.robotparser.RobotFileParser()
    try:
        testo, http, _ = http_get(url)
        if http == 200 and testo:
            rp.parse(testo.splitlines())
            for riga in testo.splitlines():
                if riga.lower().startswith("sitemap:"):
                    sitemaps.append(riga.split(":", 1)[1].strip())
        else:
            rp.allow_all = True
    except Exception:
        rp.allow_all = True
    return sitemaps, rp


def url_da_sitemap(xml, ctx, visti, profondita=0):
    """Ritorna [(url, lastmod)]. Segue gli indici di sitemap, una volta sola per URL."""
    out = []
    if "<sitemapindex" in xml[:2000].lower():
        if profondita >= 2:
            return out
        loc = []
        for blocco in re.findall(r"<sitemap>(.*?)</sitemap>", xml, re.S):
            m = re.search(r"<loc>(.*?)</loc>", blocco)
            if m:
                loc.append(htmllib.unescape(m.group(1).strip()))
        lingua = ctx.args.lingua
        if lingua:
            # Le sitemap della lingua richiesta per prime. Un indice con centinaia
            # di locale (i siti dei grandi gruppi) esaurirebbe il tetto prima di
            # arrivare a quella giusta, e il perimetro tornerebbe vuoto.
            loc.sort(key=lambda u: 0 if lingua.lower() in u.lower() else 1)
        if len(loc) > MAX_SITEMAP:
            log("  indice con %d sitemap: ne seguo %d%s" % (
                len(loc), MAX_SITEMAP,
                ", prima quelle di lingua %s" % lingua if lingua else
                " - se il perimetro torna povero, usa --lingua"))
        for u in loc[:MAX_SITEMAP]:
            if u in visti:
                continue
            visti.add(u)
            try:
                testo, http, _ = http_get(u)
                if http == 200 and testo:
                    out += url_da_sitemap(testo, ctx, visti, profondita + 1)
            except Exception as e:
                log("  sitemap figlia non letta: %s (%s)" % (u, str(e)[:60]))
        return out
    for blocco in re.findall(r"<url>(.*?)</url>", xml, re.S):
        m = re.search(r"<loc>(.*?)</loc>", blocco)
        if not m:
            continue
        lm = re.search(r"<lastmod>(.*?)</lastmod>", blocco)
        out.append((htmllib.unescape(m.group(1).strip()),
                    lm.group(1).strip() if lm else ""))
    return out


RE_HREF = re.compile(r'<a\b[^>]*href="([^"#?]+)"', re.I)


def crawl_di_ripiego(ctx, rp):
    """Se la sitemap non c'e': visita in ampiezza i link interni, con un tetto.
    Non sostituisce una sitemap, serve a non lasciare il consulente a mani vuote."""
    log("  nessuna sitemap: passo al crawl dei link interni (tetto %d pagine)" % MAX_CRAWL)
    da_vedere, visti, out = [ctx.sito or ctx.origine], set(), []
    while da_vedere and len(out) < MAX_CRAWL:
        u = da_vedere.pop(0)
        if u in visti:
            continue
        visti.add(u)
        if not rp.can_fetch(UA, u):
            continue
        try:
            testo, http, finale = http_get(u)
        except Exception:
            continue
        if http != 200 or not testo:
            continue
        out.append((u, ""))
        time.sleep(PAUSA)
        for href in RE_HREF.findall(testo):
            v = urllib.parse.urljoin(u, href.strip())
            if not v.startswith(ctx.origine):
                continue
            v = urllib.parse.urlsplit(v)._replace(fragment="", query="").geturl().rstrip("/")
            if v and v not in visti and v not in da_vedere:
                da_vedere.append(v)
    return out


def cmd_elenco(ctx):
    args = ctx.args
    if not ctx.sito:
        raise SystemExit("serve --sito")
    log("Leggo robots.txt...")
    sitemaps, rp = sitemap_da_robots(ctx)
    if not sitemaps:
        sitemaps = [ctx.origine + "/sitemap.xml", ctx.origine + "/sitemap_index.xml"]
    grezzi, visti = [], set()
    for sm in sitemaps:
        if sm in visti:
            continue
        visti.add(sm)
        try:
            testo, http, _ = http_get(sm)
        except Exception as e:
            log("  sitemap non letta: %s (%s)" % (sm, str(e)[:60]))
            continue
        if http == 200 and testo.lstrip().startswith("<"):
            log("  sitemap: %s" % sm)
            grezzi += url_da_sitemap(testo, ctx, visti)
    if not grezzi:
        grezzi = crawl_di_ripiego(ctx, rp)
    if not grezzi:
        raise SystemExit("nessun URL trovato: controlla --sito")

    # normalizza, deduplica, tiene solo le pagine dell'origine
    pagine, scartati = {}, collections.Counter()
    for u, lm in grezzi:
        u = urllib.parse.urlsplit(u)._replace(fragment="", query="").geturl().rstrip("/")
        if not u.startswith(ctx.origine):
            continue
        if re.search(r"\.(pdf|jpe?g|png|gif|svg|webp|zip|docx?|xlsx?|pptx?|mp4|mp3)$", u, re.I):
            scartati["file non HTML"] += 1
            continue
        if not rp.can_fetch(UA, u):
            scartati["vietato da robots.txt"] += 1
            continue
        motivo = fuori_perimetro(u, args)
        if motivo:
            scartati[motivo] += 1
            continue
        pagine[u] = lm or pagine.get(u, "")

    # le sezioni troppo grandi sono archivi editoriali: fuori dalle copie
    conta = collections.Counter(sezione_di(u, args.lingua) for u in pagine)
    archivi = {s for s, n in conta.items()
               if n > args.soglia_archivio or (s in NOMI_ARCHIVIO and n > 10)}
    if args.solo:                       # --solo e' una scelta esplicita: vince
        archivi = set()
    tenute = {u: lm for u, lm in pagine.items() if sezione_di(u, args.lingua) not in archivi}

    righe = sorted(([u, sezione_di(u, args.lingua), lm] for u, lm in tenute.items()),
                   key=lambda r: (r[1], r[0]))
    scrivi_tsv(ctx.seeds, ["url", "sezione", "lastmod"], righe)

    log("")
    log("PERIMETRO PROPOSTO - da confermare col consulente")
    log("  %-28s %s" % ("sezione", "pagine"))
    for s, n in sorted(collections.Counter(r[1] for r in righe).items(),
                       key=lambda x: (-x[1], x[0])):
        log("  %-28s %4d" % (s, n))
    log("  %-28s %4d" % ("TOTALE", len(righe)))
    if archivi:
        log("")
        log("  Archivi tenuti fuori (troppe pagine per una copia a una a una):")
        for s in sorted(archivi):
            log("    %-26s %4d pagine   --solo %s per includerlo" % (s, conta[s], s))
    if scartati:
        log("")
        log("  Scartati: %s" % dict(scartati))
    log("")
    log("  seeds.tsv: %s" % ctx.seeds)
    return 0


# --- fetch ------------------------------------------------------------------

def cmd_fetch(ctx):
    seeds = leggi_tsv(ctx.seeds)
    if not seeds:
        raise SystemExit("seeds.tsv vuoto: lancia prima `elenco`")
    if ctx.args.limite:
        seeds = seeds[:ctx.args.limite]
    os.makedirs(ctx.html, exist_ok=True)
    man = {m["url"]: m for m in leggi_tsv(ctx.manifest)}
    ora = time.time()

    da_fare = []
    for s in seeds:
        m = man.get(s["url"])
        p = os.path.join(ctx.html, chiave_cache(s["url"]) + ".html.gz")
        fresco = (m and os.path.exists(p) and m["http"] == "200"
                  and (ora - float(m["fetched_at"] or 0)) < TTL_ORE * 3600)
        if not fresco:
            da_fare.append(s["url"])
    log("Da scaricare: %d su %d (il resto e' in cache entro %d ore)"
        % (len(da_fare), len(seeds), TTL_ORE))

    def lavora(url):
        try:
            testo, http, _ = http_get(url)
            if http == 200 and testo:
                with gzip.open(os.path.join(ctx.html, chiave_cache(url) + ".html.gz"),
                               "wt", encoding="utf-8") as f:
                    f.write(testo)
            time.sleep(PAUSA)
            return {"url": url, "sha1": chiave_cache(url), "http": str(http),
                    "bytes": len(testo), "fetched_at": "%.0f" % time.time(),
                    "tentativi": "1", "errore": ""}
        except Exception as e:
            return {"url": url, "sha1": chiave_cache(url), "http": "0", "bytes": 0,
                    "fetched_at": "%.0f" % time.time(), "tentativi": str(RETRY),
                    "errore": str(e)[:120]}

    falliti = []
    if da_fare:
        with ThreadPoolExecutor(max_workers=CONCORRENZA) as ex:
            for i, r in enumerate(ex.map(lavora, da_fare), 1):
                man[r["url"]] = r
                if r["http"] != "200":
                    falliti.append(r)
                if i % 25 == 0:
                    log("  %d/%d" % (i, len(da_fare)))
    scrivi_tsv(ctx.manifest,
               ["url", "sha1", "http", "bytes", "fetched_at", "tentativi", "errore"],
               [[m["url"], m["sha1"], m["http"], m["bytes"], m["fetched_at"],
                 m["tentativi"], m["errore"]] for m in man.values()])
    log("In cache: %d pagine. Falliti: %d"
        % (sum(1 for m in man.values() if m["http"] == "200"), len(falliti)))
    for f in falliti[:10]:
        log("  HTTP %s  %s  %s" % (f["http"], f["url"], f["errore"][:60]))
    return 0


# --- estrai -----------------------------------------------------------------

class Testo(HTMLParser):
    """Da HTML a testo leggibile, senza dipendenze. Taglia il cromo di navigazione
    per tag semantico e tiene i titoli su una riga sola."""

    def __init__(self):
        super().__init__()
        self.out, self.muto, self.cromo, self.title, self.intitle = [], 0, 0, "", False
        self.intesta = 0

    def handle_starttag(self, t, a):
        if t in TAG_MUTI:
            self.muto += 1
        if t in TAG_CROMO:
            self.cromo += 1
        if t == "title" and not self.muto and not self.title:
            self.intitle = True          # il primo, e mai quello dentro una <svg>
        if self.muto or self.cromo:
            return
        if t in ("h1", "h2", "h3", "h4"):
            self.out.append("\n" + "#" * int(t[1]) + " ")
            self.intesta += 1
            return
        if self.intesta:
            return                 # dentro un titolo: i div annidati non lo spezzano
        if t in ("p", "div", "li", "br", "tr", "section"):
            self.out.append("\n")
        if t == "li":
            self.out.append("- ")

    def handle_endtag(self, t):
        if t in TAG_MUTI:
            self.muto = max(0, self.muto - 1)
        if t in TAG_CROMO:
            self.cromo = max(0, self.cromo - 1)
        if t in ("h1", "h2", "h3", "h4"):
            self.intesta = max(0, self.intesta - 1)
        if t == "title":
            self.intitle = False

    def handle_data(self, d):
        if self.intitle:
            self.title += d
            return                 # il <title> sta in testa al file, non nel corpo
        if self.muto or self.cromo:
            return
        if self.intesta:
            d = re.sub(r"\s+", " ", d)   # un titolo sta su una riga, come nel markdown
        self.out.append(d)


RE_DATA = re.compile(r"^- Copia di testo salvata il (\d{4}-\d{2}-\d{2})\s*$", re.M)
SEP = "\n---\n\n"


def corpo_di(testo):
    i = testo.find(SEP)
    return testo[i + len(SEP):] if i >= 0 else ""


def cmd_estrai(ctx):
    seeds = leggi_tsv(ctx.seeds)
    if ctx.args.limite:
        seeds = seeds[:ctx.args.limite]
    os.makedirs(ctx.dest, exist_ok=True)
    oggi = datetime.date.today().isoformat()
    nuovi = invariati = aggiornati = mancanti = 0
    corte = []

    for s in seeds:
        url = s["url"]
        p = os.path.join(ctx.html, chiave_cache(url) + ".html.gz")
        if not os.path.exists(p):
            mancanti += 1
            continue
        with gzip.open(p, "rt", encoding="utf-8") as f:
            grezzo = f.read()
        par = Testo()
        par.feed(grezzo)
        txt = re.sub(r"[ \t]+", " ", "".join(par.out))
        txt = htmllib.unescape(re.sub(r"\n\s*\n+", "\n\n", txt).strip())
        titolo = htmllib.unescape(par.title.strip()) or percorso_di(url) or "home"
        if len(txt) < MIN_CARATTERI:
            corte.append((url, len(txt)))

        dest = os.path.join(ctx.dest, nome_file(url, ctx.args.lingua))
        corpo = txt + "\n"
        vecchio = None
        data = oggi
        if os.path.exists(dest):
            with open(dest, encoding="utf-8") as f:
                vecchio = f.read()
            m = RE_DATA.search(vecchio)
            if m and corpo_di(vecchio) == corpo:
                data = m.group(1)    # pagina invariata: resta la data della prima lettura
        nuovo = ("# %s\n\n- URL: %s\n- Copia di testo salvata il %s\n"
                 "- Stato: non analizzato\n" % (titolo, url, data)) + SEP + corpo
        if vecchio == nuovo:
            invariati += 1
            continue
        # Si confronta tutto il file, non solo il corpo: cosi' una correzione del
        # parser (un titolo estratto meglio) arriva anche ai file gia' scritti,
        # senza far avanzare la data di lettura di una pagina che non e' cambiata.
        if vecchio is None:
            nuovi += 1
        else:
            aggiornati += 1
        scrivi_atomico(dest, nuovo)

    log("raw/sito: %d nuovi, %d aggiornati, %d invariati, %d senza cache"
        % (nuovi, aggiornati, invariati, mancanti))
    if corte:
        log("")
        log("  ATTENZIONE: %d pagine sotto %d caratteri di testo." % (len(corte), MIN_CARATTERI))
        log("  Di solito significa che il sito renderizza in JavaScript, oppure che")
        log("  TAG_CROMO ha tagliato anche il contenuto. Controllane una a mano:")
        for u, n in corte[:8]:
            log("     %4d  %s" % (n, u))
    return 0


def cmd_all(ctx):
    for f in (cmd_elenco, cmd_fetch, cmd_estrai):
        r = f(ctx)
        if r:
            return r
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("comando", choices=["elenco", "fetch", "estrai", "all"])
    ap.add_argument("--repo", required=True, help="cartella della knowledge base")
    ap.add_argument("--sito", default="", help="URL del sito, es. https://www.cliente.com")
    ap.add_argument("--escludi", action="append", default=[], help="prefisso da escludere")
    ap.add_argument("--solo", action="append", default=[], help="lavora solo su questi prefissi")
    ap.add_argument("--lingua", default="", help="ramo di lingua da tenere, es. it")
    ap.add_argument("--soglia-archivio", type=int, default=50, dest="soglia_archivio")
    ap.add_argument("--limite", type=int, default=0)
    args = ap.parse_args()
    ctx = Ctx(args)
    return {"elenco": cmd_elenco, "fetch": cmd_fetch,
            "estrai": cmd_estrai, "all": cmd_all}[args.comando](ctx)


if __name__ == "__main__":
    sys.exit(main())
