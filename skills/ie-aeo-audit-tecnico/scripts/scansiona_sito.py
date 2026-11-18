#!/usr/bin/env python3
"""Scansiona il sito di un cliente e raccoglie i dati grezzi dell'audit tecnico AEO.

Uso, dalla radice del repo del cliente:
    python3 -I scansiona_sito.py https://esempio.com [--max-pagine N] [--pausa 0.5]
        [--uscita raw/audit-tecnico] [--solo-aeo] [--ignora-robots]

Scrive in raw/audit-tecnico/<AAAA-MM-GG>/ un file per fase, **appena la fase finisce**,
così una scansione interrotta non si perde e si riprende da dove era arrivata:

    robots.json     robots.txt interpretato, direttive Sitemap, llms.txt
    crawler.json    accesso vero dei crawler: una richiesta per ogni user-agent
    tls.json        certificato, scadenza, redirect HTTP→HTTPS, HSTS
    sitemap.json    sitemap trovate, URL, lastmod
    pagine.jsonl    una riga per pagina scansionata, scritta subito
    scansione.json  parametri, conteggi, durata

Lo script raccoglie e basta: soglie e giudizi stanno in analizza_audit.py.

**Perché si presenta con il nome dei crawler AI.** Il `robots.txt` dice una cosa, il WAF
o la CDN ne fanno un'altra: molti siti rispondono 403 a GPTBot o ClaudeBot pur avendo un
robots.txt permissivo, e dal solo robots.txt non si vede. Si fa **sul sito del cliente,
con il suo mandato**: non è uno strumento per aggirare i blocchi di terzi.

Attenzione a come si legge il risultato: i controlli sui bot verificati guardano
l'indirizzo di rete, non il nome. Una richiesta che si presenta come Googlebot può essere
respinta proprio perché fallisce quella verifica, mentre il Googlebot vero passa. Qui si
misura come il sito tratta chi si presenta con quel nome, non se il crawler autentico sia
bloccato. Dettagli in references/verifiche.md.
"""
import argparse
import datetime as dt
import gzip
import html
import io
import json
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from collections import deque
from html.parser import HTMLParser
from pathlib import Path

UA_NOSTRO = "Mozilla/5.0 (compatible; IE-AEO-Audit/1.0; audit tecnico su mandato del cliente)"

# User-agent da provare, con la conseguenza che ha bloccarli. La conseguenza serve al
# report: un cliente decide «voglio essere citato ma non addestrare», non «voglio GPTBot».
CRAWLER = [
    ("Googlebot", "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
     "ricerca-google", "Indice di Google: da qui passano anche AI Overviews e AI Mode"),
    ("Google-Extended", "Mozilla/5.0 (compatible; Google-Extended/1.0)",
     "addestramento", "Addestramento e grounding di Gemini. NON governa le AI Overviews"),
    ("Bingbot", "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
     "ricerca-bing", "Indice di Bing, da cui pesca anche Copilot"),
    ("GPTBot", "Mozilla/5.0 (compatible; GPTBot/1.1; +https://openai.com/gptbot)",
     "addestramento", "Addestramento dei modelli OpenAI"),
    ("OAI-SearchBot", "Mozilla/5.0 (compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)",
     "citazione", "Ricerca dentro ChatGPT: senza questo non si viene citati"),
    ("ChatGPT-User", "Mozilla/5.0 (compatible; ChatGPT-User/1.0; +https://openai.com/bot)",
     "citazione", "Pagina aperta da ChatGPT su richiesta di una persona"),
    ("ClaudeBot", "Mozilla/5.0 (compatible; ClaudeBot/1.0; +claudebot@anthropic.com)",
     "addestramento", "Addestramento dei modelli Anthropic"),
    ("Claude-SearchBot", "Mozilla/5.0 (compatible; Claude-SearchBot/1.0; +claudebot@anthropic.com)",
     "citazione", "Ricerca dentro Claude"),
    ("Claude-User", "Mozilla/5.0 (compatible; Claude-User/1.0; +claudebot@anthropic.com)",
     "citazione", "Pagina aperta da Claude su richiesta di una persona"),
    ("PerplexityBot", "Mozilla/5.0 (compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
     "citazione", "Indice di Perplexity"),
    ("Perplexity-User", "Mozilla/5.0 (compatible; Perplexity-User/1.0; +https://perplexity.ai/perplexity-user)",
     "citazione", "Pagina aperta da Perplexity su richiesta di una persona"),
    ("Applebot", "Mozilla/5.0 (compatible; Applebot/0.1; +http://www.apple.com/go/applebot)",
     "ricerca-apple", "Siri e Spotlight"),
    ("Applebot-Extended", "Mozilla/5.0 (compatible; Applebot-Extended/1.0)",
     "addestramento", "Addestramento dei modelli Apple"),
    ("Amazonbot", "Mozilla/5.0 (compatible; Amazonbot/0.1; +https://developer.amazon.com/amazonbot)",
     "citazione", "Alexa e ricerca Amazon"),
    ("Meta-ExternalAgent", "Mozilla/5.0 (compatible; meta-externalagent/1.1)",
     "addestramento", "Addestramento dei modelli Meta"),
    ("CCBot", "CCBot/2.0 (https://commoncrawl.org/faq/)",
     "addestramento", "Common Crawl: alimenta molti modelli di terzi"),
    ("Bytespider", "Mozilla/5.0 (compatible; Bytespider; spider-feedback@bytedance.com)",
     "addestramento", "Addestramento dei modelli ByteDance"),
]

# Un contenitore di root vuoto e' una prova: la pagina senza JavaScript non ha corpo.
RE_SPA_VUOTO = re.compile(
    r'<div\s+id=["\'](root|app|__next|__nuxt|q-app)["\'][^>]*>\s*</div>', re.IGNORECASE)
# Questi invece dicono solo "e' fatto con un framework": ci sono anche su ogni pagina
# Next.js o Nuxt renderizzata lato server, che per un crawler va benissimo. Valgono come
# indizio solo insieme a poco testo.
RE_FRAMEWORK = re.compile(r'__NEXT_DATA__|window\.__NUXT__|ng-version=|data-reactroot',
                          re.IGNORECASE)
RE_NOME_FILE = re.compile(r"^[\w\-. ]+\.(jpe?g|png|gif|webp|svg|avif)$", re.IGNORECASE)
RE_SOFT404 = re.compile(r"pagina non trovata|non è stata trovata|page not found|404 error|"
                        r"contenuto non disponibile|errore 404", re.IGNORECASE)
SALTA_ESTENSIONI = (".pdf", ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".zip", ".mp4",
                    ".mp3", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".avif", ".ico")


class Pagina(HTMLParser):
    """Un solo passaggio sull'HTML grezzo: titoli, immagini, link, JSON-LD, testo visibile.

    Lavora sull'HTML **come arriva**, senza eseguire JavaScript: è esattamente quello che
    vedono GPTBot, ClaudeBot e PerplexityBot. È il punto del controllo, non un limite.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titolo, self.canonical, self.meta_robots, self.descrizione = "", "", "", ""
        self.h1, self.h2, self.h3 = [], [], []
        self.immagini, self.link, self.hreflang, self.jsonld = [], [], [], []
        self.risorse_http = []          # risorse in http:// su una pagina https: mixed content
        self._tag_testo, self._raccogli, self._buffer = None, None, []
        self._salta = 0
        self.testo = []

    def handle_starttag(self, tag, attrs):
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag in ("script", "style", "noscript", "template", "svg"):
            if tag == "script" and a.get("type", "").lower() == "application/ld+json":
                self._raccogli = "jsonld"; self._buffer = []
            else:
                self._salta += 1
            return
        if tag in ("h1", "h2", "h3", "title"):
            self._tag_testo = tag; self._buffer = []
        elif tag == "img":
            self.immagini.append({"src": a.get("src", ""), "alt": a.get("alt"),
                                  "loading": a.get("loading", "")})
            if a.get("src", "").startswith("http://"):
                self.risorse_http.append(a["src"])
        elif tag == "a" and a.get("href"):
            self.link.append({"href": a["href"], "rel": a.get("rel", "")})
        elif tag == "link":
            rel = a.get("rel", "").lower()
            if "canonical" in rel:
                self.canonical = a.get("href", "")
            if "alternate" in rel and a.get("hreflang"):
                self.hreflang.append({"hreflang": a["hreflang"], "href": a.get("href", "")})
            if a.get("href", "").startswith("http://") and "stylesheet" in rel:
                self.risorse_http.append(a["href"])
        elif tag == "meta":
            nome = (a.get("name") or a.get("property") or "").lower()
            if nome == "robots":
                self.meta_robots = a.get("content", "")
            elif nome == "description":
                self.descrizione = a.get("content", "")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "template", "svg"):
            if self._raccogli == "jsonld":
                self.jsonld.append("".join(self._buffer))
                self._raccogli, self._buffer = None, []
            elif self._salta:
                self._salta -= 1
            return
        if tag == self._tag_testo:
            t = re.sub(r"\s+", " ", "".join(self._buffer)).strip()
            if tag == "title":
                self.titolo = self.titolo or t
            elif t:
                getattr(self, tag).append(t)
            self._tag_testo, self._buffer = None, []

    def handle_data(self, dati):
        if self._raccogli == "jsonld" or self._tag_testo:
            self._buffer.append(dati)
        elif not self._salta:
            s = dati.strip()
            if s:
                self.testo.append(s)


# --- Rete ------------------------------------------------------------------

def prendi(url, ua=UA_NOSTRO, metodo="GET", timeout=20, segui=True, max_byte=3_000_000):
    """Una richiesta HTTP. Restituisce sempre un dizionario, anche quando fallisce."""
    esito = {"url": url, "status": None, "url_finale": url, "errore": "", "intestazioni": {},
             "corpo": "", "byte": 0, "secondi": None, "redirect": []}

    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            esito["redirect"].append({"da": req.full_url, "a": newurl, "status": code})
            if not segui:
                return None
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    opener = urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(url, method=metodo, headers={
        "User-Agent": ua, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en;q=0.8", "Accept-Encoding": "gzip"})
    inizio = time.monotonic()
    try:
        with opener.open(req, timeout=timeout) as r:
            grezzo = r.read(max_byte)
            esito.update(status=r.status, url_finale=r.url,
                         intestazioni={k.lower(): v for k, v in r.headers.items()})
            if r.headers.get("Content-Encoding", "").lower() == "gzip":
                try:
                    grezzo = gzip.decompress(grezzo)
                except OSError:
                    pass
            esito["byte"] = len(grezzo)
            tipo = esito["intestazioni"].get("content-type", "")
            if "text" in tipo or "xml" in tipo or "json" in tipo or not tipo:
                carica = re.search(r"charset=([\w-]+)", tipo)
                esito["corpo"] = grezzo.decode(carica.group(1) if carica else "utf-8", "replace")
    except urllib.error.HTTPError as e:
        esito.update(status=e.code, intestazioni={k.lower(): v for k, v in (e.headers or {}).items()})
        try:
            esito["corpo"] = e.read(100_000).decode("utf-8", "replace")
        except Exception:
            pass
    except urllib.error.URLError as e:
        esito["errore"] = str(getattr(e, "reason", e))
    except (socket.timeout, TimeoutError):
        esito["errore"] = "timeout"
    except Exception as e:
        esito["errore"] = f"{type(e).__name__}: {e}"
    esito["secondi"] = round(time.monotonic() - inizio, 3)
    return esito


# --- Fasi ------------------------------------------------------------------

def fase_robots(base):
    """robots.txt interpretato per gruppo di user-agent, più le Sitemap e llms.txt."""
    r = prendi(urllib.parse.urljoin(base, "/robots.txt"))
    gruppi, corrente, sitemap = {}, [], []
    if r["status"] == 200 and r["corpo"]:
        for riga in r["corpo"].splitlines():
            riga = riga.split("#", 1)[0].strip()
            if not riga or ":" not in riga:
                continue
            campo, _, valore = riga.partition(":")
            campo, valore = campo.strip().lower(), valore.strip()
            if campo == "user-agent":
                if corrente and gruppi.get(corrente[-1]) is not None and gruppi[corrente[-1]]["regole"]:
                    corrente = []
                corrente.append(valore)
                gruppi.setdefault(valore, {"regole": [], "crawl_delay": None})
            elif campo in ("allow", "disallow") and corrente:
                for ua in corrente:
                    gruppi[ua]["regole"].append({"tipo": campo, "percorso": valore})
            elif campo == "crawl-delay" and corrente:
                for ua in corrente:
                    gruppi[ua]["crawl_delay"] = valore
            elif campo == "sitemap":
                sitemap.append(valore)

    rp = urllib.robotparser.RobotFileParser()
    rp.parse(r["corpo"].splitlines() if r["status"] == 200 else [])
    permessi = {}
    for nome, ua, _, _ in CRAWLER:
        permessi[nome] = {
            "robots_permette_home": rp.can_fetch(nome, base) if r["status"] == 200 else True,
            "gruppo_esplicito": nome.lower() in {g.lower() for g in gruppi},
        }

    llms = prendi(urllib.parse.urljoin(base, "/llms.txt"))
    return {
        "robots_status": r["status"], "robots_errore": r["errore"],
        "robots_testo": r["corpo"][:20000],
        "gruppi": gruppi, "sitemap_dichiarate": sitemap, "permessi": permessi,
        "llms_txt": {"status": llms["status"], "byte": llms["byte"],
                     "righe": len([x for x in llms["corpo"].splitlines() if x.strip()])
                     if llms["status"] == 200 else 0},
    }


def fase_crawler(base, pagina_profonda, pausa):
    """La verifica che conta: la richiesta vera, con lo user-agent di ogni crawler."""
    esiti = []
    for nome, ua, conseguenza, perche in CRAWLER:
        home = prendi(base, ua=ua, timeout=15)
        time.sleep(pausa)
        deep = prendi(pagina_profonda, ua=ua, timeout=15) if pagina_profonda else None
        time.sleep(pausa)
        esiti.append({
            "crawler": nome, "conseguenza": conseguenza, "perche": perche,
            "home_status": home["status"], "home_errore": home["errore"],
            "home_secondi": home["secondi"], "home_byte": home["byte"],
            "profonda_status": deep["status"] if deep else None,
            "profonda_errore": deep["errore"] if deep else "",
            "server": home["intestazioni"].get("server", ""),
            "cf_mitigated": home["intestazioni"].get("cf-mitigated", ""),
        })
        print(f"  {nome:22} home {home['status'] or home['errore']}"
              + (f" · pagina interna {deep['status'] or deep['errore']}" if deep else ""))
    return esiti


def fase_tls(base):
    p = urllib.parse.urlparse(base)
    host, porta = p.hostname, p.port or 443
    out = {"host": host, "https": p.scheme == "https"}
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, porta), timeout=15) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ss:
                cert = ss.getpeercert()
                out["protocollo"] = ss.version()
        scade = dt.datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z").replace(tzinfo=dt.timezone.utc)
        out.update(valido=True, scade_il=scade.date().isoformat(),
                   giorni_alla_scadenza=(scade - dt.datetime.now(dt.timezone.utc)).days,
                   emesso_da=dict(x[0] for x in cert.get("issuer", ()) if x).get("organizationName", ""))
    except Exception as e:
        out.update(valido=False, errore=f"{type(e).__name__}: {e}")

    http = prendi(f"http://{host}/", segui=False, timeout=15)
    out["http_status"] = http["status"]
    out["http_redirige_a_https"] = bool(http["redirect"] and http["redirect"][0]["a"].startswith("https://"))
    out["http_redirect"] = http["redirect"][:3]
    home = prendi(base)
    hsts = home["intestazioni"].get("strict-transport-security", "")
    out["hsts"] = hsts
    out["x_robots_tag"] = home["intestazioni"].get("x-robots-tag", "")
    return out


def _urls_da_xml(testo):
    url = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", testo, re.IGNORECASE)
    mod = re.findall(r"<lastmod>\s*([^<]+?)\s*</lastmod>", testo, re.IGNORECASE)
    return [html.unescape(u) for u in url], [m.strip() for m in mod]


def fase_sitemap(base, dichiarate, pausa, max_sitemap=50):
    da_provare = list(dichiarate) or [urllib.parse.urljoin(base, "/sitemap.xml")]
    viste, trovate, voci = set(), [], []
    coda = deque(da_provare)
    while coda and len(trovate) < max_sitemap:
        u = coda.popleft()
        if u in viste:
            continue
        viste.add(u)
        r = prendi(u, timeout=25)
        time.sleep(pausa)
        corpo = r["corpo"]
        if r["byte"] and not corpo and u.endswith(".gz"):
            corpo = ""  # .gz non decodificabile: si segnala e si va avanti
        indice = "<sitemapindex" in corpo.lower()
        urls, mod = _urls_da_xml(corpo)
        trovate.append({"url": u, "status": r["status"], "errore": r["errore"],
                        "indice": indice, "url_trovati": len(urls),
                        "con_lastmod": len(mod), "byte": r["byte"]})
        print(f"  sitemap {u} → {r['status']}, {len(urls)} url, {len(mod)} lastmod")
        if indice:
            coda.extend(urls)
        else:
            for i, loc in enumerate(urls):
                voci.append({"url": loc, "lastmod": mod[i] if i < len(mod) else ""})
    return {"sitemap": trovate, "voci": voci,
            "totale_url": len(voci), "con_lastmod": sum(1 for v in voci if v["lastmod"])}


RE_LINGUA = re.compile(r"^[a-z]{2}(?:-[a-z]{2})?$", re.IGNORECASE)


def sezione_di(url, base):
    """La sezione e' la prima cartella vera, saltando il segmento di lingua.

    Senza questo, su un sito multilingua /it/prodotti/x finisce nella sezione "it" e
    tutti gli indicatori per sezione spariscono, senza che nessuno se ne accorga.
    """
    parti = [x for x in urllib.parse.urlparse(url).path.strip("/").split("/") if x]
    if parti and RE_LINGUA.fullmatch(parti[0]):
        parti = parti[1:]
    return parti[0].lower() if parti else "home"


def analizza_pagina(url, r, base, dominio):
    p = Pagina()
    try:
        p.feed(r["corpo"])
    except Exception:
        pass
    testo = " ".join(p.testo)
    parole = len(testo.split())
    tipi_jsonld, blocchi = [], []
    for blocco in p.jsonld:
        try:
            dati = json.loads(blocco)
        except ValueError:
            tipi_jsonld.append("__non_valido__")
            continue
        for oggetto in (dati if isinstance(dati, list) else [dati]):
            if not isinstance(oggetto, dict):
                continue
            grafo = oggetto.get("@graph")
            for o in (grafo if isinstance(grafo, list) else [oggetto]):
                if not isinstance(o, dict):
                    continue
                t = o.get("@type", "")
                for tt in (t if isinstance(t, list) else [t]):
                    if tt:
                        tipi_jsonld.append(str(tt))
                blocchi.append(o)

    interni = []
    for l in p.link:
        href = l["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        assoluto = urllib.parse.urljoin(r["url_finale"] or url, href)
        # Via ancore e query: i filtri di un catalogo generano migliaia di URL
        # equivalenti e si mangerebbero tutto il budget della scansione.
        assoluto = assoluto.split("#")[0].split("?")[0]
        if urllib.parse.urlparse(assoluto).hostname == dominio:
            interni.append(assoluto)

    senza_alt = [i["src"] for i in p.immagini if i["alt"] is None]
    alt_vuoto = [i["src"] for i in p.immagini if i["alt"] == ""]
    alt_nomefile = [i["src"] for i in p.immagini
                    if i["alt"] and RE_NOME_FILE.match(i["alt"].strip())]
    alt_lungo = [i["src"] for i in p.immagini if i["alt"] and len(i["alt"]) > 125]

    return {
        "url": url, "url_finale": r["url_finale"], "status": r["status"], "errore": r["errore"],
        "redirect": r["redirect"], "secondi": r["secondi"], "byte_html": r["byte"],
        "sezione": sezione_di(r["url_finale"] or url, base),
        "titolo": p.titolo, "descrizione": p.descrizione,
        "h1": p.h1, "h2": p.h2, "n_h3": len(p.h3),
        "meta_robots": p.meta_robots,
        "x_robots_tag": r["intestazioni"].get("x-robots-tag", ""),
        "canonical": p.canonical, "hreflang": p.hreflang,
        "immagini": len(p.immagini), "img_senza_alt": senza_alt[:40],
        "img_alt_vuoto": len(alt_vuoto), "img_alt_nomefile": alt_nomefile[:20],
        "img_alt_lungo": len(alt_lungo),
        "jsonld_tipi": tipi_jsonld, "jsonld": blocchi[:12],
        "parole_testo": parole,
        "root_vuoto": bool(RE_SPA_VUOTO.search(r["corpo"][:200000])),
        "framework_js": bool(RE_FRAMEWORK.search(r["corpo"][:200000])),
        "risorse_http": p.risorse_http[:20],
        "possibile_soft404": bool(r["status"] == 200 and parole < 120 and RE_SOFT404.search(testo)),
        "link_interni": sorted(set(interni))[:300],
    }


def fase_pagine(base, dominio, semi, max_pagine, pausa, uscita, rp, rispetta_robots):
    viste, coda, scritte = set(), deque(semi), 0
    percorso = uscita / "pagine.jsonl"
    with open(percorso, "w", encoding="utf-8") as f:
        while coda and scritte < max_pagine:
            url = coda.popleft()
            chiave = url.split("#")[0].rstrip("/") or url
            if chiave in viste:
                continue
            viste.add(chiave)
            if urllib.parse.urlparse(url).path.lower().endswith(SALTA_ESTENSIONI):
                continue
            if rispetta_robots and not rp.can_fetch(UA_NOSTRO, url):
                continue
            r = prendi(url)
            dati = analizza_pagina(url, r, base, dominio)
            f.write(json.dumps(dati, ensure_ascii=False) + "\n")
            f.flush()
            scritte += 1
            if scritte % 25 == 0:
                print(f"  {scritte} pagine")
            for l in dati["link_interni"]:
                if l.split("#")[0].rstrip("/") not in viste:
                    coda.append(l)
            time.sleep(pausa)
    return scritte


def fase_link(uscita, max_controlli, pausa):
    """Controlla i bersagli dei link interni che la scansione non ha raggiunto.

    Senza questo passo l'indicatore sui link rotti non puo' trovare niente quando la
    sitemap e' piu' grande del tetto di pagine: i bersagli rotti quasi mai stanno in
    sitemap, quindi non vengono mai scaricati e il loro status resta sconosciuto.
    """
    pagine, visti = [], {}
    with open(uscita / "pagine.jsonl", encoding="utf-8") as f:
        for riga in f:
            try:
                d = json.loads(riga)
            except ValueError:
                continue
            pagine.append(d)
            visti[(d.get("url_finale") or d["url"]).split("#")[0].rstrip("/")] = d.get("status")

    da_controllare = {}
    for d in pagine:
        for l in d.get("link_interni", []):
            chiave = l.split("#")[0].rstrip("/")
            if chiave in visti or chiave in da_controllare:
                continue
            da_controllare[chiave] = l
    elenco = list(da_controllare.values())[:max_controlli]
    esiti = []
    for i, u in enumerate(elenco):
        r = prendi(u, metodo="HEAD", timeout=12, max_byte=1)
        if r["status"] is None and not r["errore"]:
            r = prendi(u, timeout=12, max_byte=2000)   # qualche server rifiuta HEAD
        esiti.append({"url": u, "status": r["status"], "errore": r["errore"]})
        if (i + 1) % 25 == 0:
            print(f"  {i + 1} link controllati")
        time.sleep(pausa)
    return {"controllati": len(esiti), "non_controllati": max(0, len(da_controllare) - len(elenco)),
            "esiti": esiti}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("sito", help="URL del sito, per esempio https://esempio.com")
    p.add_argument("--max-pagine", type=int, default=None,
                   help="quante pagine leggere al massimo. Senza, si legge tutta la sitemap "
                        "(con un minimo di 400 se la sitemap e' piccola o non c'e')")
    p.add_argument("--pausa", type=float, default=0.5, help="secondi fra una richiesta e l'altra")
    p.add_argument("--uscita", default="raw/audit-tecnico")
    p.add_argument("--data", help="data della scansione, AAAA-MM-GG (default: oggi)")
    p.add_argument("--max-link", type=int, default=400,
                   help="bersagli di link interni da controllare oltre le pagine scansionate")
    p.add_argument("--solo-aeo", action="store_true",
                   help="scansiona meno pagine e, in analisi, tiene solo le verifiche che "
                        "Semrush e Ahrefs non fanno. Non salta la scansione: rendering e "
                        "schema per sezione hanno bisogno delle pagine")
    p.add_argument("--ignora-robots", action="store_true",
                   help="scansiona anche i percorsi vietati dal robots.txt; solo con il mandato del cliente")
    a = p.parse_args()

    base = a.sito if "://" in a.sito else "https://" + a.sito
    base = base.rstrip("/") + "/"
    dominio = urllib.parse.urlparse(base).hostname
    if not dominio:
        sys.exit(f"{a.sito} non è un URL valido.")
    oggi = a.data or dt.date.today().isoformat()
    uscita = Path(a.uscita) / oggi
    uscita.mkdir(parents=True, exist_ok=True)
    inizio = time.monotonic()
    print(f"Audit tecnico di {base} → {uscita}\n")

    print("1. robots.txt e llms.txt")
    robots = fase_robots(base)
    (uscita / "robots.json").write_text(json.dumps(robots, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  robots.txt: {robots['robots_status']}, {len(robots['gruppi'])} gruppi, "
          f"{len(robots['sitemap_dichiarate'])} sitemap dichiarate · "
          f"llms.txt: {robots['llms_txt']['status']}\n")

    print("2. sitemap")
    sitemap = fase_sitemap(base, robots["sitemap_dichiarate"], a.pausa)
    (uscita / "sitemap.json").write_text(json.dumps(sitemap, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  {sitemap['totale_url']} URL, {sitemap['con_lastmod']} con lastmod\n")

    print("3. TLS, redirect, HSTS")
    tls = fase_tls(base)
    (uscita / "tls.json").write_text(json.dumps(tls, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  certificato {'valido' if tls.get('valido') else 'NON valido'}"
          + (f", scade fra {tls['giorni_alla_scadenza']} giorni" if tls.get("valido") else "")
          + f" · HTTP→HTTPS {'sì' if tls['http_redirige_a_https'] else 'NO'}"
          + f" · HSTS {'sì' if tls['hsts'] else 'no'}\n")

    rp = urllib.robotparser.RobotFileParser()
    rp.parse(robots["robots_testo"].splitlines())
    semi = [base] + [v["url"] for v in sitemap["voci"]]
    # La coda parte gia' da tutta la sitemap: il tetto non sceglie quali pagine leggere,
    # taglia e basta. Senza --max-pagine si legge tutto quello che il cliente dichiara,
    # perche' un audit su un campione non dice quante pagine hanno il problema, dice solo
    # quante ne hanno fra quelle che abbiamo guardato. Il minimo di 400 copre i siti senza
    # sitemap, dove i semi sono la sola home e si va avanti per link.
    if a.max_pagine is not None:
        tetto = a.max_pagine
    else:
        tetto = max(400, len(sitemap["voci"]))
    if a.solo_aeo:
        tetto = min(tetto, 60)
    minuti = round(tetto * (a.pausa + 0.3) / 60)
    print(f"4. scansione delle pagine (massimo {tetto}, pausa {a.pausa}s, circa {minuti} minuti)")
    scritte = fase_pagine(base, dominio, semi, tetto, a.pausa, uscita, rp, not a.ignora_robots)
    print(f"  {scritte} pagine in pagine.jsonl\n")

    link = {"controllati": 0, "esiti": []}
    if scritte and not a.solo_aeo:
        print("5. link interni che la scansione non ha raggiunto")
        link = fase_link(uscita, a.max_link, a.pausa)
        print(f"  {link['controllati']} controllati"
              + (f", {link['non_controllati']} oltre il tetto non controllati" if link["non_controllati"] else "")
              + "\n")
    (uscita / "link.json").write_text(json.dumps(link, ensure_ascii=False, indent=1), encoding="utf-8")

    # Le sonde con lo user-agent dei crawler vanno per ultime: se il WAF le segna, una
    # scansione fatta dopo tornerebbe piena di 403 che non c'entrano col sito.
    profonda = next((v["url"] for v in sitemap["voci"]
                     if urllib.parse.urlparse(v["url"]).path.strip("/")), None)
    print("6. accesso dei crawler (una richiesta che si presenta come ciascuno)")
    crawler = fase_crawler(base, profonda, a.pausa)
    (uscita / "crawler.json").write_text(json.dumps(crawler, ensure_ascii=False, indent=1), encoding="utf-8")
    print()

    (uscita / "scansione.json").write_text(json.dumps({
        "sito": base, "dominio": dominio, "data": oggi,
        "max_pagine": a.max_pagine, "pagine_scansionate": scritte,
        "link_controllati": link["controllati"],
        "pausa": a.pausa, "solo_aeo": a.solo_aeo, "robots_rispettato": not a.ignora_robots,
        "user_agent": UA_NOSTRO, "durata_secondi": round(time.monotonic() - inizio),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Fatto in {round((time.monotonic() - inizio) / 60, 1)} minuti.")
    print(f"Ora analizza:  python3 -I <skill>/scripts/analizza_audit.py {uscita}")


if __name__ == "__main__":
    main()
