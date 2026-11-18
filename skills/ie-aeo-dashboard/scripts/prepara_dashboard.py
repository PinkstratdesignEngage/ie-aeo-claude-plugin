#!/usr/bin/env python3
"""Prepara i file della dashboard SEO/AEO di un cliente dalle ultime estrazioni salvate nel repo.

Uso, dalla radice del repo del cliente:
    python3 -I prepara_dashboard.py raw/gsc/<AAAA-MM-GG> --cliente "Nome" [--brand "a,b"]
        [--semrush raw/semrush/<AAAA-MM-GG> | --ahrefs raw/ahrefs/<AAAA-MM-GG>]
        [--hubspot raw/hubspot-aeo/<AAAA-MM-GG>] [--ga4 raw/ga4/<AAAA-MM-GG>] [--soglia-visite-ai 10]
        [--azioni analisi/dashboard/azioni.json] [--uscita analisi/dashboard]

Fonti:
- Search Console (obbligatoria): i CSV di estrai_gsc.py e cannibalizzazioni.csv di
  analizza_estrazione.py, da lanciare prima;
- Semrush o Ahrefs, uno dei due (facoltativa): opportunita_keyword.csv, site_audit_pesato.csv e
  site_audit.csv dell'analisi, più, per il riepilogo del Site Audit, originali/risposte.jsonl
  con Semrush o site_audit_riepilogo.json con Ahrefs. Ahrefs porta anche ai_citazioni.csv e
  ai_visibilita.csv, le citazioni negli assistenti AI, che finiscono nella scheda AEO;
- HubSpot AEO (facoltativa): la cartella del download; finché non c'è, la sezione AEO
  della dashboard resta in attesa;
- GA4 (facoltativa): l'estrazione di ie-aeo-ga4, con le visite dagli assistenti AI. Porta un
  indicatore, la sezione "Dalle risposte al sito" nella scheda AEO e le visite AI sulle pagine
  delle azioni: un'azione su pagine con almeno --soglia-visite-ai sessioni AI nel periodo prende
  GA4 tra le fonti e sale di un livello, come una confermata da HubSpot (una sola volta). Le home
  di lingua (/, /it, /en…) non contano: le loro visite AI sono di navigazione.

Scrive nella cartella di uscita dati.json e index.html (dal modello della skill).

Le azioni, in un unico piano di lavoro, sono di tre categorie:
- cannibalizzazione (Search Console): pagine nella stessa lingua collegate da query in
  comune, oppure, tra lingue diverse, un'azione per tipo di contenuto;
- opportunità (Semrush o Ahrefs, confermate da Search Console): una per pagina, con le
  ricerche in posizione 4-20 che hanno impressioni reali;
- tecnico (Site Audit): una per problema.
La priorità si calcola dentro ogni categoria (alta dal 25% dell'azione più pesante della
categoria, media dal 5%). Un problema del Site Audit che tocca le pagine di una
cannibalizzazione (hreflang, canonical, contenuti duplicati) si aggiunge come seconda fonte.
Il file --azioni, facoltativo, sovrascrive per id titolo, rimedio, skill e priorità.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

MODELLO = Path(__file__).resolve().parent.parent / "assets" / "dashboard.html"

# Problemi del Site Audit di Semrush (id dei report): nome in italiano e intervento
PROBLEMI = {
    6: ("Titoli duplicati", "Dare a ogni pagina un title unico, con prodotto e lingua."),
    7: ("Contenuti duplicati", "Unire le pagine quasi identiche o differenziarle; per quelle che restano entrambe, un canonical."),
    13: ("Immagini interne non funzionanti", "Sostituire o togliere le immagini che non si caricano."),
    15: ("Meta description duplicate", "Scrivere una meta description propria per ogni pagina, a partire dalle più visitate."),
    24: ("Conflitti hreflang nel codice delle pagine", "Correggere il modello delle pagine nel CMS: un solo hreflang per lingua, reciproco tra le versioni."),
    45: ("Errori nei dati strutturati", "Correggere il markup Schema.org del modello di pagina coinvolto: vale per tutte le pagine che lo usano."),
    101: ("Titoli troppo corti", "Allungare i title con prodotto e vantaggio."),
    102: ("Titoli troppo lunghi", "Accorciare i title sotto i 60 caratteri."),
    103: ("H1 mancante", "Aggiungere un H1 con il tema della pagina."),
    104: ("Più H1 nella stessa pagina", "Lasciare un solo H1."),
    105: ("H1 uguale al title", "Differenziare H1 e title."),
    106: ("Meta description mancante", "Scrivere la meta description, a partire dalle pagine più visitate."),
    109: ("Redirect temporanei", "Sostituire i redirect 302 stabili con 301 e aggiornare i link interni alla destinazione finale."),
    112: ("Rapporto testo/HTML basso", "Priorità bassa: aggiungere testo utile dove serve, non come fine."),
    117: ("Pagine con pochi contenuti", "Arricchire o unire le pagine con pochi contenuti utili."),
    122: ("Underscore negli URL", "Priorità bassa: usare trattini nei nuovi URL."),
    135: ("JavaScript e CSS non minimizzati", "Intervento tecnico sulle prestazioni del sito."),
    137: ("llms.txt assente", "Pubblicare un llms.txt che descriva il sito per gli assistenti AI."),
    204: ("Lingua hreflang non corrispondente", "Correggere la lingua dichiarata delle pagine segnalate."),
    205: ("HSTS non supportato", "Intervento tecnico sulla sicurezza del sito."),
    209: ("Pagine bloccate con noindex", "Verificare che siano pagine da escludere (per esempio accessi riservati)."),
    210: ("Risorse esterne bloccate", "Priorità bassa: verificare le risorse esterne bloccate da robots.txt."),
    213: ("Pagine con un solo link interno", "Aggiungere link interni dalle pagine collegate per tema."),
    215: ("Risorse linkate come pagine", "Priorità bassa: controllare i link a file e risorse."),
    216: ("Link senza testo", "Dare un testo ai link, soprattutto quelli su immagini e icone."),
    217: ("Link con testo poco descrittivo", "Sostituire testi come \"clicca qui\" con il tema della pagina di destinazione."),
    218: ("Link esterni con errore 403", "Priorità bassa: verificare i link esterni rifiutati."),
    223: ("Contenuti da ottimizzare", "Vedere le indicazioni del Site Audit per le pagine segnalate."),
}
LEGATI_CANNIBALIZZAZIONE = {7, 24, 204}
# Ahrefs identifica i problemi con un nome, non con un numero: le stesse regole, sul titolo
LEGATI_CANNIBALIZZAZIONE_NOME = re.compile(
    r"hreflang|canonical|duplicate content|duplicate pages|contenut\w* duplicat|lang attribute", re.IGNORECASE)
ORDINE_PRIORITA = {"alta": 0, "media": 1, "bassa": 2}
LIVELLI = ["bassa", "media", "alta"]

# Raccomandazioni di HubSpot AEO che coincidono con un problema del Site Audit di Semrush:
# (espressione sul titolo inglese di HubSpot, problemi del Site Audit in ordine di preferenza).
# Se il problema c'è nel piano, la raccomandazione diventa una seconda fonte di quella azione.
COLLEGAMENTI_HUBSPOT = [
    (r"schema\.org product", [45]),
    (r"single main heading|\bh1\b", [104, 103]),
    (r"page titles and meta descriptions|meta description", [15, 106, 6]),
    (r"file size of your pages|minif", [135]),
    (r"llms\.txt", [137]),
]
# Gli stessi collegamenti quando il problema arriva da Ahrefs, che non ha gli id di Semrush:
# (espressione sul titolo di HubSpot, espressione sul titolo del problema).
COLLEGAMENTI_HUBSPOT_NOME = [
    (r"schema\.org product", r"structured data|schema|rich (results|snippet)"),
    (r"single main heading|\bh1\b", r"\bh1\b"),
    (r"page titles and meta descriptions|meta description", r"meta description|title tag|\btitle\b"),
    (r"file size of your pages|minif", r"page size|minif|slow page|html size|render.blocking"),
    (r"llms\.txt", r"llms\.txt"),
]
# Verifiche dell'audit tecnico che il Site Audit di Semrush o Ahrefs copre gia':
# (id della verifica, espressione sul titolo del problema dell'altro strumento).
SOVRAPPOSIZIONE_AUDIT = {
    "h1": r"\bh1\b|heading",
    "alt": r"\balt\b|attributo alt|image alt|senza testo alternativo",
    "link-rotti": r"broken|rotti|4xx|404",
    "ssl": r"\bssl\b|https|certificat",
    "canonical": r"canonical",
    "peso-html": r"page size|html size|peso delle pagine|minif",
}
PRIORITA_HUBSPOT = {"HIGH": "alta", "MEDIUM": "media", "LOW": "bassa"}
SKILL_HUBSPOT = {
    ("CREATE_CONTENT", "EDUCATIONAL"): "ie-aeo-blogpost",
    ("CREATE_CONTENT", "PRODUCT"): "nuova pagina prodotto, con ie-aeo-faq-prodotto",
    ("UPDATE_ROBOTS", None): "intervento tecnico sul sito (robots.txt)",
}

# Prima cartella dopo la lingua, ricondotta a un tipo di contenuto
FAMIGLIE = {
    "news": ["news", "notizie", "noticias", "actualites", "nachrichten", "blog", "press"],
    "case study": ["case-study", "case-studies", "realizzazioni", "realizaciones", "realisations",
                   "réalisations", "referenzen", "references", "projects", "progetti", "unsere-leistungen"],
    "prodotti": ["prodotti", "products", "productos", "produits", "produkte", "product"],
    "eventi e media": ["foto-e-video", "fotos-y-videos", "photos-et-videos", "fotos-und-videos",
                       "photos-and-videos", "eventi", "events"],
}
MAX_PAGINE_GRUPPO = 6
RE_LINGUA = re.compile(r"^https?://[^/]+/([a-z]{2}(?:-[a-z]{2})?)/", re.IGNORECASE)


def leggi(percorso):
    with open(percorso, encoding="utf-8") as f:
        yield from csv.DictReader(f)


def leggi_se(percorso):
    """Come leggi, ma un file che non c'è vale come vuoto."""
    return list(leggi(percorso)) if Path(percorso).exists() else []


def famiglia(url):
    parti = [p for p in re.sub(r"^https?://[^/]+", "", url).split("/") if p]
    if parti and RE_LINGUA.match(url):
        parti = parti[1:]
    if parti and re.fullmatch(r"[a-z]{2}", parti[0]):  # cartella di lingua ripetuta, es. /it/it/
        parti = parti[1:]
    if not parti:
        return "home page"
    cartella = parti[0].lower()
    for nome, cartelle in FAMIGLIE.items():
        if cartella in cartelle:
            return nome
    if "case-study" in "/".join(parti).lower():
        return "case study"
    return "altre pagine"


def mesi_completi(inizio, fine):
    mesi, m = [], inizio.replace(day=1)
    if m < inizio:
        m = (m.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    while True:
        prossimo = (m.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        if prossimo - dt.timedelta(days=1) > fine:
            return mesi
        mesi.append(m.strftime("%Y-%m"))
        m = prossimo


def id_azione(prefisso, chiave):
    return prefisso + "-" + hashlib.sha1(chiave.encode()).hexdigest()[:8]


def percorso(url):
    return re.sub(r"^https?://[^/]+", "", url) or "/"


ASSISTENTI_GA4 = [
    ("ChatGPT", r"chatgpt|openai"), ("Perplexity", r"perplexity"), ("Copilot", r"copilot"),
    ("Gemini", r"gemini|bard"), ("Claude", r"claude|anthropic"), ("DeepSeek", r"deepseek"),
    ("Meta AI", r"meta\.ai"), ("Mistral", r"mistral"), ("Grok", r"grok|x\.ai"),
]


def assistente_ga4(sorgente):
    for nome, rx in ASSISTENTI_GA4:
        if re.search(rx, (sorgente or "").lower()):
            return nome
    return "Altri"


def leggi_ga4(cartella, dominio, norm, impr_gsc, cit_hubspot):
    """Legge l'estrazione di ie-aeo-ga4: visite dagli assistenti AI per mese, assistente e pagina di arrivo."""
    meta = json.loads((cartella / "metadati.json").read_text(encoding="utf-8"))
    num = lambda v: int(float(v or 0))
    tutte, organica, org_coinv = defaultdict(int), defaultdict(int), defaultdict(int)
    for r in leggi(cartella / "canali_mensile.csv"):
        tutte[r["mese"]] += num(r["sessioni"])
        if r["canale"].lower().startswith("organic search"):
            organica[r["mese"]] += num(r["sessioni"])
            org_coinv[r["mese"]] += num(r["sessioni_coinvolte"])
    ai, ai_coinv = defaultdict(int), defaultdict(int)
    ass = defaultdict(lambda: {"sessioni": 0, "coinvolte": 0, "mesi": defaultdict(int)})
    for r in leggi(cartella / "ai_mensile.csv"):
        ai[r["mese"]] += num(r["sessioni"])
        ai_coinv[r["mese"]] += num(r["sessioni_coinvolte"])
        a = ass[assistente_ga4(r["sorgente"])]
        a["sessioni"] += num(r["sessioni"])
        a["coinvolte"] += num(r["sessioni_coinvolte"])
        a["mesi"][r["mese"]] += num(r["sessioni"])
    fine = dt.date.fromisoformat(meta["periodo"]["fine"])
    ultimo = fine.strftime("%Y%m") if (fine + dt.timedelta(days=1)).day == 1 else \
        (fine.replace(day=1) - dt.timedelta(days=1)).strftime("%Y%m")
    mesi = sorted(tutte)
    completi = [m for m in mesi if m <= ultimo]
    recenti, precedenti = completi[-3:], completi[-6:-3]
    somma = lambda d, ms: sum(d.get(m, 0) for m in ms)
    pagine = defaultdict(lambda: {"sessioni": 0, "assistenti": defaultdict(int)})
    for r in leggi(cartella / "ai_pagine.csv"):
        if not r["pagina"].startswith("/"):
            continue  # pagina di arrivo assente: conta nei totali, non nelle pagine
        v = pagine[norm(dominio + r["pagina"])]
        v["sessioni"] += num(r["sessioni"])
        v["assistenti"][assistente_ga4(r["sorgente"])] += num(r["sessioni"])
    elenco_pagine = sorted(({"pagina": k, "sessioni": v["sessioni"],
                             "assistente": max(v["assistenti"], key=v["assistenti"].get),
                             "gsc_impressioni": impr_gsc.get(k), "citazioni_hubspot": cit_hubspot.get(k, 0)}
                            for k, v in pagine.items()), key=lambda x: -x["sessioni"])
    return {
        "stato": "presente", "estrazione": cartella.name, "proprieta": meta.get("proprieta"), "host": meta.get("host"),
        "periodo": meta["periodo"], "totali": meta.get("totali"),
        "mesi": [{"mese": f"{m[:4]}-{m[4:]}", "ai": ai.get(m, 0), "tutte": tutte[m], "parziale": m > ultimo} for m in mesi],
        "recenti": {"mesi": [f"{m[:4]}-{m[4:]}" for m in recenti], "ai": somma(ai, recenti), "ai_prima": somma(ai, precedenti),
                    "tutte": somma(tutte, recenti), "organica": somma(organica, recenti),
                    "coinvolgimento_ai": somma(ai_coinv, recenti) / somma(ai, recenti) if somma(ai, recenti) else None,
                    "coinvolgimento_organica": somma(org_coinv, recenti) / somma(organica, recenti) if somma(organica, recenti) else None},
        "assistenti": sorted(({"nome": k, "sessioni": v["sessioni"], "coinvolte": v["coinvolte"],
                               "recenti": somma(v["mesi"], recenti)} for k, v in ass.items()), key=lambda x: -x["sessioni"]),
        "pagine": elenco_pagine[:40],
        "_per_pagina": {x["pagina"]: x["sessioni"] for x in elenco_pagine},
    }


def leggi_hubspot(cartella, dominio, impr_gsc):
    """Legge il download di ie-aeo-hubspot-aeo: metriche, prompt con gli URL citati, raccomandazioni."""
    metriche = json.loads((cartella / "metriche.json").read_text(encoding="utf-8")) if (cartella / "metriche.json").exists() else {}
    riepilogo, prompt, limiti, ultimo_run = None, {}, None, None
    for risposta in metriche.values():
        if not isinstance(risposta, dict):
            continue
        if "summary" in risposta:
            riepilogo = risposta
        for p in ((risposta.get("prompts") or {}).get("prompts") or []):
            prompt[p["id"]] = p
        limiti = risposta.get("limits") or limiti
        ultimo_run = (risposta.get("runStatus") or {}).get("lastRunCompletedAt") or ultimo_run
    cliente = lambda u: dominio in re.sub(r"^https?://(www\.)?", "", (u or "").lower()).split("/")[0]

    dettagli = {}
    for f in sorted((cartella / "prompt").glob("*.json")) if (cartella / "prompt").is_dir() else []:
        if f.stem.endswith("-risposte"):
            continue
        d = json.loads(f.read_text(encoding="utf-8"))
        dettagli[(d.get("prompt") or {}).get("id")] = d

    url = defaultdict(lambda: {"citazioni": 0, "assistenti": set(), "prompt": set()})
    elenco_prompt = []
    for pid in sorted(set(prompt) | {k for k in dettagli if k}):
        p = prompt.get(pid) or (dettagli.get(pid) or {}).get("prompt") or {}
        d = dettagli.get(pid) or {}
        per_assistente = defaultdict(lambda: {"risposte": 0, "menzioni": 0, "citazioni": 0, "citazioni_cliente": 0})
        cit_cliente = 0
        for run in d.get("runSummaries") or []:
            pa = per_assistente[run.get("aiAssistant", "?")]
            pa["risposte"] += 1
            pa["menzioni"] += 1 if run.get("ownedMentions") else 0
            pa["citazioni"] += run.get("totalCitations") or 0
            for u in run.get("citationUrls") or []:
                v = url[u]
                v["citazioni"] += 1
                v["assistenti"].add(run.get("aiAssistant", "?"))
                v["prompt"].add(pid)
                if cliente(u):
                    pa["citazioni_cliente"] += 1
                    cit_cliente += 1
        elenco_prompt.append({
            "id": pid, "testo": p.get("prompt", ""), "pubblico": p.get("icpNames") or [], "prodotti": p.get("productNames") or [],
            "gruppi": p.get("groupNames") or [], "lingua": p.get("location") or "", "tipo": p.get("brandType") or "",
            "visibilita": p.get("visibility"), "menzioni": p.get("mentionCount"), "risposte": p.get("responseCount"),
            "citazioni": p.get("citationCount"), "citazioni_cliente": cit_cliente if d else None,
            "per_assistente": dict(per_assistente),
        })
    norm_u = lambda u: re.sub(r"^https?://(www\.)?", "", u.lower()).split("?")[0].split("#")[0].rstrip("/")
    url_citati = sorted(({"url": u, "citazioni": v["citazioni"], "assistenti": sorted(v["assistenti"]),
                          "prompt": len(v["prompt"]), "cliente": cliente(u), "gsc_impressioni": impr_gsc.get(norm_u(u))}
                         for u, v in url.items()), key=lambda r: (not r["cliente"], -r["citazioni"]))

    raccomandazioni, viste = [], set()
    if (cartella / "raccomandazioni.json").exists():
        for pagina in json.loads((cartella / "raccomandazioni.json").read_text(encoding="utf-8")):
            for r in ((pagina.get("risposta") or {}).get("recommendations") or []):
                if r.get("id") not in viste:
                    viste.add(r.get("id"))
                    raccomandazioni.append(r)
    for d in dettagli.values():
        for r in d.get("recommendations") or []:
            if r.get("id") not in viste:
                viste.add(r.get("id"))
                raccomandazioni.append(r)

    portale = (riepilogo or {}).get("portalId")
    return {
        "stato": "presente" if (riepilogo or elenco_prompt or raccomandazioni) else "in attesa",
        "estrazione": cartella.name,
        "periodo": {"inizio": (riepilogo or {}).get("resolvedStartDate"), "fine": (riepilogo or {}).get("resolvedEndDate")},
        "riepilogo": (riepilogo or {}).get("summary"),
        "confronto": ((riepilogo or {}).get("summary") or {}).get("comparison"),
        "citazioni": {k: v for k, v in ((riepilogo or {}).get("citations") or {}).items() if k != "topDomains"},
        "domini": ((riepilogo or {}).get("citations") or {}).get("topDomains") or [],
        "competitor": ((riepilogo or {}).get("competitors") or {}).get("brands") or [],
        "assistenti": ((riepilogo or {}).get("assistantBreakdown") or {}).get("byAssistant") or [],
        "limiti": limiti, "ultimo_run": ultimo_run, "dominio": dominio,
        "link": f"https://app.hubspot.com/ai-visibility/{portale}/" if portale else None,
        "prompt": elenco_prompt, "url_citati": url_citati, "raccomandazioni": raccomandazioni,
        "file": sorted(f.name for f in cartella.iterdir() if f.is_file()),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cartella")
    p.add_argument("--cliente", required=True)
    p.add_argument("--brand", default="")
    p.add_argument("--azioni", help="file JSON con titolo, rimedio, skill e priorità rivisti, per id di azione")
    p.add_argument("--semrush", help="cartella dell'estrazione Semrush analizzata")
    p.add_argument("--ahrefs", help="cartella dell'estrazione Ahrefs analizzata, in alternativa a --semrush")
    p.add_argument("--hubspot", help="cartella del download HubSpot AEO")
    p.add_argument("--ga4", help="cartella dell'estrazione GA4 (ie-aeo-ga4)")
    p.add_argument("--audit-tecnico", help="cartella dell'audit tecnico analizzato (ie-aeo-audit-tecnico)")
    p.add_argument("--soglia-visite-ai", type=int, default=10,
                   help="sessioni AI nel periodo oltre cui una pagina conta come visitata dagli assistenti")
    p.add_argument("--uscita", default="analisi/dashboard")
    p.add_argument("--frequenza", type=int, default=30)
    a = p.parse_args()

    cartella = Path(a.cartella)
    if not (cartella / "cannibalizzazioni.csv").exists():
        sys.exit("Manca cannibalizzazioni.csv: lancia prima analizza_estrazione.py sulla cartella.")
    meta = json.loads((cartella / "metadati.json").read_text(encoding="utf-8"))

    # --- Numeri chiave ---
    per_mese = defaultdict(lambda: [0, 0])
    for r in leggi(cartella / "andamento_giornaliero.csv"):
        per_mese[r["data"][:7]][0] += int(r["click"])
        per_mese[r["data"][:7]][1] += int(r["impressioni"])
    completi = mesi_completi(dt.date.fromisoformat(meta["inizio"]), dt.date.fromisoformat(meta["fine"]))
    recenti = completi[-3:]
    prima = [f"{int(m[:4]) - 1}{m[4:]}" for m in recenti]
    yoy = None
    if len(recenti) == 3 and set(prima) <= set(completi):
        cr = sum(per_mese[m][0] for m in recenti)
        ca = sum(per_mese[m][0] for m in prima)
        ir = sum(per_mese[m][1] for m in recenti)
        ia = sum(per_mese[m][1] for m in prima)
        yoy = {"mesi": recenti, "mesi_prima": prima, "click": cr, "click_prima": ca,
               "impressioni": ir, "impressioni_prima": ia}

    # --- Casi ---
    righe = list(leggi(cartella / "cannibalizzazioni.csv"))
    query_casi = {r["query"] for r in righe}
    mesi = sorted({r["mese"] for r in leggi(cartella / "pagine_mensile.csv")})
    migliori = {}
    if (cartella / "query_pagina_mensile.csv").exists():
        for r in leggi(cartella / "query_pagina_mensile.csv"):
            if r["query"] not in query_casi:
                continue
            k = (r["query"], r["mese"])
            v = (int(r["click"]), int(r["impressioni"]))
            if k not in migliori or v > migliori[k][0]:
                migliori[k] = (v, r["pagina"])

    pagine, indice = [], {}

    def idx(url):
        if url not in indice:
            indice[url] = len(pagine)
            pagine.append(url)
        return indice[url]

    casi = []
    for i, r in enumerate(righe):
        pp, pc = r["pagina_principale"], r["pagina_concorrente"]
        sequenza = ""
        for m in mesi:
            top = migliori.get((r["query"], m))
            sequenza += "." if not top else ("P" if top[1] == pp else "C" if top[1] == pc else "A")
        brand = r["brand"] == "sì"
        tipo = "brand" if brand else ("lingue" if r["stessa_lingua"] == "no" else "stessa-lingua")
        imp = int(r["impressioni_totali"])
        quota_c = float(r["quota_concorrente"])
        mesi_dati = max(int(r["mesi_con_dati"]), 1)
        punteggio = imp * quota_c * (1 + int(r["cambi_di_pagina"]) / max(mesi_dati - 1, 1))
        casi.append({
            "id": i, "query": r["query"], "tipo": tipo, "domanda": r["domanda"] == "sì",
            "impressioni": imp, "click": int(r["click_totali"]), "metrica": r["metrica"],
            "p": idx(pp), "qp": float(r["quota_principale"]), "posp": float(r["posizione_principale"]),
            "c": idx(pc), "qc": quota_c, "posc": float(r["posizione_concorrente"]),
            "cambi": int(r["cambi_di_pagina"]), "mesi_dati": int(r["mesi_con_dati"]),
            "seq": sequenza, "punteggio": round(punteggio, 1), "azione": None,
        })

    # --- Azioni ---
    azioni = {}

    def aggiungi(aid, base, caso):
        az = azioni.setdefault(aid, dict(base, casi=[], pagine=set(), punteggio=0.0, impressioni=0, click=0))
        az["casi"].append(caso["id"])
        az["pagine"].update([caso["p"], caso["c"]])
        az["punteggio"] += caso["punteggio"]
        az["impressioni"] += round(caso["impressioni"] * caso["qc"])
        az["click"] += caso["click"]
        caso["azione"] = aid

    # Stessa lingua: gruppi di pagine collegate (union-find)
    padre = {}

    def radice(x):
        padre.setdefault(x, x)
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    stessa = [c for c in casi if c["tipo"] == "stessa-lingua"]
    for c in stessa:
        padre[radice(c["p"])] = radice(c["c"])
    gruppi = defaultdict(list)
    for c in stessa:
        gruppi[radice(c["p"])].append(c)
    # Un gruppo troppo grande non è una decisione sola: si divide per pagina principale
    divisi = []
    for membri in gruppi.values():
        if len({x for c in membri for x in (c["p"], c["c"])}) <= MAX_PAGINE_GRUPPO:
            divisi.append(membri)
            continue
        per_principale = defaultdict(list)
        for c in membri:
            per_principale[c["p"]].append(c)
        divisi.extend(per_principale.values())
    for membri in divisi:
        forza = defaultdict(float)
        for c in membri:
            forza[c["p"]] += c["impressioni"] * c["qp"]
        principale = max(forza, key=forza.get)
        fam = famiglia(pagine[principale])
        if fam == "prodotti":
            rimedio = ("Differenziare: la pagina più forte risponde alle ricerche generiche, le altre a quelle "
                       "specifiche, con link interni tra loro.")
            skill = "ie-aeo-ristruttura-contenuti"
        elif fam in ("news", "eventi e media"):
            rimedio = ("Collegare le pagine: la news rimanda alla pagina di riferimento del tema; consolidare "
                       "con redirect 301 solo se i contenuti si ripetono.")
            skill = "ie-aeo-ristruttura-contenuti"
        else:
            rimedio = ("Valutare l'intento: differenziare le pagine, consolidarle con un redirect 301 nella più "
                       "forte o, se quasi identiche, indicare un canonical.")
            skill = "ie-aeo-ristruttura-contenuti"
        base = {"tipo": "stessa-lingua", "famiglia": fam, "titolo": "Pagine in concorrenza su " + percorso(pagine[principale]),
                "rimedio": rimedio, "skill": skill, "principale": principale}
        aid = id_azione("sl", pagine[principale])
        for c in membri:
            aggiungi(aid, base, c)

    # Lingue diverse: per tipo di contenuto
    for c in casi:
        if c["tipo"] != "lingue":
            continue
        fam = famiglia(pagine[c["p"]])
        base = {"tipo": "lingue", "famiglia": fam,
                "titolo": f"Versioni linguistiche in concorrenza: {fam}",
                "rimedio": ("Controllare se le versioni nelle altre lingue sono tradotte. Tradurre quelle utili ai "
                            "mercati di quella lingua; per le altre togliere le copie da hreflang e indicizzazione "
                            "o indicare come canonical la versione originale."),
                "skill": "intervento tecnico sul CMS", "principale": None}
        aggiungi(id_azione("ln", fam), base, c)

    for z in azioni.values():
        z.update(categoria="cannibalizzazione", fonti=["Search Console"], keyword=[], problema=None, collegate=[])

    def norm(u):
        return re.sub(r"^https?://(www\.)?", "", (u or "").strip().lower()).split("?")[0].split("#")[0].rstrip("/")

    pagine_norm = {norm(u): i for i, u in enumerate(pagine)}

    def idx_norm(url):
        return pagine_norm.get(norm(url)) if norm(url) in pagine_norm else idx(url)

    if a.semrush and a.ahrefs:
        sys.exit("Passa --semrush oppure --ahrefs: la dashboard legge un solo strumento di ricerca per volta.")
    ricerche = None
    if a.semrush or a.ahrefs:
        strumento = "Semrush" if a.semrush else "Ahrefs"
        sem = Path(a.semrush or a.ahrefs)
        ricerche = {"strumento": strumento, "estrazione": sem.name, "opportunita": 0,
                    "site_audit": None, "ai": None}

        # Opportunità confermate, una per pagina
        per_pagina = defaultdict(list)
        for r in leggi(sem / "opportunita_keyword.csv"):
            if r.get("confermata_gsc") == "sì":
                per_pagina[r["url"]].append(r)
        for url, kws in per_pagina.items():
            pi = idx_norm(url)
            prodotto = famiglia(url) == "prodotti"
            kws.sort(key=lambda r: -float(r["punteggio"] or 0))
            azioni[id_azione("op", norm(url))] = {
                "categoria": "opportunita", "tipo": "opportunita", "famiglia": famiglia(url),
                "fonti": [strumento, "Search Console"],
                "titolo": "Rafforzare " + percorso(url) + " sulle ricerche vicine alla prima pagina",
                "rimedio": ("Le ricerche elencate sono tra la posizione 4 e la 20 e hanno impressioni reali in Search Console. "
                            "Far rispondere la pagina a queste domande: risposta iniziale, sottotitoli, FAQ e dati strutturati."),
                "skill": "ie-aeo-faq-prodotto o ie-aeo-ristruttura-contenuti" if prodotto else "ie-aeo-ristruttura-contenuti",
                "principale": pi, "pagine": {pi}, "casi": [], "problema": None, "collegate": [],
                "punteggio": sum(float(r["punteggio"] or 0) for r in kws),
                "impressioni": sum(int(r["gsc_impressioni"] or 0) for r in kws),
                "click": sum(int(r["gsc_click"] or 0) for r in kws),
                "keyword": [{"keyword": r["keyword"], "database": r["database"], "posizione": int(r["posizione"]),
                             "volume": int(r["volume"]), "aio": r["aio"] == "sì",
                             "gsc_impressioni": int(r["gsc_impressioni"] or 0)} for r in kws],
            }
            ricerche["opportunita"] += len(kws)

        # Site Audit: riepilogo e titoli dalle risposte originali, pagine da site_audit.csv
        info, titoli = None, {}
        risposte = sem / "originali" / "risposte.jsonl"
        if risposte.exists():
            for riga in open(risposte, encoding="utf-8"):
                d = json.loads(riga)
                if d["report"] == "info":
                    info = d["risposta"]["data"]
                elif d["report"] == "meta_issues":
                    titoli = {m["id"]: m["title"] for m in d["risposta"]["data"]}
        pagine_problema = defaultdict(set)
        id_da_titolo = {t: i for i, t in titoli.items()}
        for r in leggi(sem / "site_audit.csv"):
            if r["problema"] in id_da_titolo:
                pagine_problema[id_da_titolo[r["problema"]]].add(r["url"])
        impr_pagina = {norm(r["pagina"]): int(r["impressioni"]) for r in leggi(cartella / "pagine.csv")}
        if info:
            ricerche["site_audit"] = {k: info.get(k) for k in ("errors", "warnings", "notices", "pages_crawled",
                                                                "pages_limit", "last_audit", "markups")}
            for pid_txt, quante in (info.get("defects") or {}).items():
                pid = int(pid_txt)
                if pid == 4 or not quante:
                    continue  # pagine bloccate dalla scansione: non è un problema del sito
                gravita = "errore" if pid < 100 else "avviso" if pid < 200 else "nota"
                nome, rimedio = PROBLEMI.get(pid, (titoli.get(pid, f"Problema {pid}"),
                                                   "Vedere la descrizione del problema nel Site Audit di Semrush."))
                urls = pagine_problema.get(pid, set())
                idxs = {idx_norm(u) for u in urls}
                azioni["sa-" + str(pid)] = {
                    "categoria": "tecnico", "tipo": "tecnico", "famiglia": "",
                    "fonti": ["Site Audit"], "titolo": nome, "rimedio": rimedio,
                    "skill": "intervento tecnico sul sito",
                    "principale": None, "pagine": idxs, "casi": [], "keyword": [], "collegate": [],
                    "problema": {"id": pid, "gravita": gravita, "occorrenze": quante,
                                 "titolo_origine": titoli.get(pid, ""), "pagine_lette": len(urls)},
                    "punteggio": sum(impr_pagina.get(norm(u), 0) for u in urls) or 0,
                    "impressioni": sum(impr_pagina.get(norm(u), 0) for u in urls),
                    "click": 0,
                }

        # Site Audit di Ahrefs: riepilogo e problemi già normalizzati da normalizza_ahrefs.py
        riepilogo = sem / "site_audit_riepilogo.json"
        if riepilogo.exists():
            d = json.loads(riepilogo.read_text(encoding="utf-8"))
            pagine_problema = defaultdict(set)
            for r in leggi_se(sem / "site_audit.csv"):
                pagine_problema[r["problema"]].add(r["url"])
            ricerche["site_audit"] = {k: d.get(k) for k in ("errors", "warnings", "notices", "pages_crawled",
                                                            "pages_limit", "last_audit", "health_score")}
            for pr in d.get("problemi", []):
                urls = pagine_problema.get(pr["titolo"], set())
                idxs = {idx_norm(u) for u in urls}
                chiave = re.sub(r"[^a-z0-9]+", "-", str(pr["id"]).lower()).strip("-") or str(len(azioni))
                azioni["sa-ah-" + chiave] = {
                    "categoria": "tecnico", "tipo": "tecnico", "famiglia": "",
                    "fonti": ["Site Audit"], "titolo": pr["titolo"],
                    "rimedio": "Vedere la descrizione del problema nel Site Audit di Ahrefs"
                               + (f" (categoria {pr['categoria']})." if pr.get("categoria") else "."),
                    "skill": "intervento tecnico sul sito",
                    "principale": None, "pagine": idxs, "casi": [], "keyword": [], "collegate": [],
                    "problema": {"id": pr["id"], "gravita": pr["gravita"], "occorrenze": pr.get("occorrenze") or 0,
                                 "titolo_origine": pr["titolo"], "pagine_lette": len(urls)},
                    "punteggio": sum(impr_pagina.get(norm(u), 0) for u in urls) or 0,
                    "impressioni": sum(impr_pagina.get(norm(u), 0) for u in urls),
                    "click": 0,
                }

        # Citazioni negli assistenti AI: le misura Ahrefs, non Semrush
        citazioni = leggi_se(sem / "ai_citazioni.csv")
        if citazioni:
            tutte = next((r for r in citazioni if r["assistente"].lower().startswith("tutte")), None)
            per_assistente = [{"assistente": r["assistente"], "citazioni": int(r["citazioni"] or 0),
                               "pagine": int(r["pagine"] or 0)}
                              for r in citazioni if r is not tutte and int(r["citazioni"] or 0)]
            per_assistente.sort(key=lambda r: -r["citazioni"])
            per_url = defaultdict(lambda: {"risposte": 0, "assistenti": [], "gsc_impressioni": None})
            for r in leggi_se(sem / "ai_visibilita.csv"):
                u = per_url[r["url"]]
                u["risposte"] += int(r["risposte"] or 0)
                u["assistenti"].append(r["assistente"])
                u["gsc_impressioni"] = int(r["gsc_impressioni"]) if r.get("gsc_impressioni") else u["gsc_impressioni"]
            url_citati = sorted(({"url": k, **v} for k, v in per_url.items()), key=lambda r: -r["risposte"])[:40]
            ricerche["ai"] = {
                "citazioni": int(tutte["citazioni"] or 0) if tutte else sum(r["citazioni"] for r in per_assistente),
                "pagine": int(tutte["pagine"] or 0) if tutte else len(per_url),
                "assistenti": per_assistente, "url_citati": url_citati,
            }

        # Collegamenti: problemi tecnici sulle pagine di una cannibalizzazione, opportunità sulle stesse pagine
        for aid, z in azioni.items():
            if z["categoria"] != "cannibalizzazione":
                continue
            for bid, w in azioni.items():
                if bid == aid or not (z["pagine"] & w["pagine"]):
                    continue
                if w["categoria"] == "tecnico" and (w["problema"]["id"] in LEGATI_CANNIBALIZZAZIONE
                                                     or LEGATI_CANNIBALIZZAZIONE_NOME.search(w["titolo"])):
                    if "Site Audit" not in z["fonti"]:
                        z["fonti"].append("Site Audit")
                    z["collegate"].append(bid)
                    w["collegate"].append(aid)
                elif w["categoria"] == "opportunita":
                    z["collegate"].append(bid)
                    w["collegate"].append(aid)

    audit = None
    if a.audit_tecnico and Path(a.audit_tecnico).is_dir():
        at = Path(a.audit_tecnico)
        risultati = json.loads((at / "risultati.json").read_text(encoding="utf-8")) \
            if (at / "risultati.json").exists() else {}
        elenco = json.loads((at / "azioni.json").read_text(encoding="utf-8")) \
            if (at / "azioni.json").exists() else []
        audit = {"estrazione": at.name, "sito": risultati.get("sito", ""),
                 "pagine": risultati.get("pagine_scansionate", 0),
                 "gruppi": risultati.get("gruppi", {}), "azioni": len(elenco)}
        impr = {norm(r["pagina"]): int(r["impressioni"]) for r in leggi(cartella / "pagine.csv")}
        # Quando Semrush o Ahrefs segnalano gia' lo stesso problema, l'audit non crea una
        # seconda azione: si aggiunge come seconda fonte di quella che c'e'. Altrimenti il
        # piano mostrerebbe due volte "manca l'H1" con due id diversi.
        gia_tecnici = [(aid, z) for aid, z in azioni.items() if z["categoria"] == "tecnico"]
        for v in elenco:
            regola = SOVRAPPOSIZIONE_AUDIT.get(v["id"].replace("sa-ie-", ""))
            doppione = next((aid for aid, z in gia_tecnici
                             if regola and re.search(regola, z["titolo"], re.IGNORECASE)), None)
            if doppione:
                z = azioni[doppione]
                if "Audit tecnico" not in z["fonti"]:
                    z["fonti"].append("Audit tecnico")
                continue
            urls = [u for u in v.get("pagine", []) if u.startswith("http")]
            idxs = {idx_norm(u) for u in urls}
            azioni[v["id"]] = {
                "categoria": "tecnico", "tipo": "tecnico", "famiglia": "",
                "fonti": ["Audit tecnico"], "titolo": v["titolo"], "rimedio": v["rimedio"],
                "skill": "intervento tecnico sul sito",
                "principale": None, "pagine": idxs, "casi": [], "keyword": [], "collegate": [],
                "problema": {"id": v["id"], "gravita": v["gravita"], "occorrenze": v.get("occorrenze") or 0,
                             "titolo_origine": v["titolo"], "pagine_lette": len(urls)},
                "punteggio": sum(impr.get(norm(u), 0) for u in urls) or 0,
                "impressioni": sum(impr.get(norm(u), 0) for u in urls),
                "click": 0,
            }

    for z in azioni.values():
        z.setdefault("hubspot", [])
    dominio = norm(meta["sito"]).split("/")[0]
    hubspot = {"stato": "in attesa"}
    if a.hubspot and Path(a.hubspot).is_dir():
        hubspot = leggi_hubspot(Path(a.hubspot), dominio, impr_gsc={norm(r["pagina"]): int(r["impressioni"])
                                                                     for r in leggi(cartella / "pagine.csv")})
        per_problema = {z["problema"]["id"]: aid for aid, z in azioni.items() if z["categoria"] == "tecnico"}
        for rec in hubspot.get("raccomandazioni", []):
            voce = {"id": rec["id"], "titolo": rec["title"], "priorita": PRIORITA_HUBSPOT.get(rec.get("priority"), "bassa"),
                    "stato": rec.get("status", ""), "categoria": rec.get("actionCategory", ""),
                    "citazioni": rec.get("influencingCitationCount") or 0}
            bersaglio = None
            for regola, problemi in COLLEGAMENTI_HUBSPOT:
                if re.search(regola, rec["title"], re.IGNORECASE):
                    bersaglio = next((per_problema[pid] for pid in problemi if pid in per_problema), None)
                    break
            if not bersaglio:
                for regola, regola_problema in COLLEGAMENTI_HUBSPOT_NOME:
                    if re.search(regola, rec["title"], re.IGNORECASE):
                        bersaglio = next((aid for aid, z in azioni.items() if z["categoria"] == "tecnico"
                                          and re.search(regola_problema, z["titolo"], re.IGNORECASE)), None)
                        break
            if bersaglio:
                z = azioni[bersaglio]
                z["hubspot"].append(voce)
                if "HubSpot AEO" not in z["fonti"]:
                    z["fonti"].append("HubSpot AEO")
                rec["azione"] = bersaglio
                continue
            chiave = (rec.get("actionCategory"), rec.get("contentType"))
            skill = SKILL_HUBSPOT.get(chiave) or SKILL_HUBSPOT.get((rec.get("actionCategory"), None)) \
                or "intervento sul modello di pagina nel CMS"
            aid = "hs-" + str(rec["id"])
            azioni[aid] = {
                "categoria": "aeo", "tipo": "aeo", "famiglia": "", "fonti": ["HubSpot AEO"],
                "titolo": rec["title"], "rimedio": rec.get("summary") or "",
                "skill": skill, "principale": None, "pagine": set(), "casi": [], "keyword": [], "problema": None,
                "collegate": [], "hubspot": [voce], "punteggio": float(voce["citazioni"]),
                "impressioni": 0, "click": 0, "_priorita_hubspot": voce["priorita"],
            }
            rec["azione"] = aid
        # Nel file della dashboard bastano i campi che la pagina mostra
        hubspot["raccomandazioni"] = [
            {"id": r["id"], "titolo": r.get("title", ""), "sintesi": r.get("summary", ""),
             "priorita": PRIORITA_HUBSPOT.get(r.get("priority"), "bassa"), "stato": r.get("status", ""),
             "categoria": r.get("actionCategory", ""), "canale": r.get("actionChannel", ""),
             "tipo_contenuto": r.get("contentType"), "citazioni": r.get("influencingCitationCount") or 0,
             "prompt": r.get("promptId"), "azione": r.get("azione")}
            for r in hubspot.get("raccomandazioni", [])]

    # --- GA4: visite dagli assistenti AI sulle pagine delle azioni ---
    ga4 = {"stato": "in attesa"}
    if a.ga4 and Path(a.ga4).is_dir():
        impr = defaultdict(int)
        for r in leggi(cartella / "pagine.csv"):
            impr[norm(r["pagina"])] += int(r["impressioni"])
        cit = defaultdict(int)
        for u in hubspot.get("url_citati", []) if hubspot.get("stato") == "presente" else []:
            cit[norm(u["url"])] += u["citazioni"]
        ga4 = leggi_ga4(Path(a.ga4), dominio, norm, impr, cit)
        per_pagina = ga4.pop("_per_pagina")
        ga4["soglia"] = a.soglia_visite_ai
        # Le home di lingua ricevono visite AI di navigazione: non dicono nulla sulla pagina in discussione
        home = re.compile(r"^[^/]+(/[a-z]{2}(-[a-z]{2})?)?$")
        for z in azioni.values():
            visite = [per_pagina.get(norm(pagine[i]), 0) for i in z["pagine"] if not home.match(norm(pagine[i]))]
            z["visite_ai"] = sum(visite)
            if any(v >= a.soglia_visite_ai for v in visite) and "GA4" not in z["fonti"]:
                z["fonti"].append("GA4")
    for z in azioni.values():
        z.setdefault("visite_ai", 0)

    # Revisioni del consulente
    riviste = set()
    if a.azioni and Path(a.azioni).exists():
        for aid, campi in json.loads(Path(a.azioni).read_text(encoding="utf-8")).items():
            if aid in azioni:
                azioni[aid].update({k: v for k, v in campi.items() if k in ("titolo", "rimedio", "skill", "priorita")})
                if "priorita" in campi:
                    riviste.add(aid)

    for aid, z in azioni.items():
        z["id"] = aid
    # Priorità dentro ogni categoria; un problema tecnico senza pagine lette resta media se è un errore.
    # Le azioni AEO prendono la priorità di HubSpot.
    for categoria in ("cannibalizzazione", "opportunita", "tecnico", "aeo"):
        gruppo = [z for z in azioni.values() if z["categoria"] == categoria]
        massimo = max((z["punteggio"] for z in gruppo), default=0) or 1
        for z in gruppo:
            z["peso"] = z["punteggio"] / massimo
            if categoria == "aeo":
                calcolata = z.get("_priorita_hubspot", "bassa")
            elif categoria == "tecnico" and not z["punteggio"]:
                calcolata = "media" if z["problema"]["gravita"] == "errore" else "bassa"
            else:
                calcolata = "alta" if z["peso"] >= 0.25 else "media" if z["peso"] >= 0.05 else "bassa"
            z.setdefault("priorita", calcolata)
    # Un'azione confermata anche da HubSpot AEO, o su pagine con visite dagli assistenti AI in GA4,
    # sale di un livello (una volta sola), se il consulente non l'ha rivista
    for aid, z in azioni.items():
        if z["categoria"] != "aeo" and (z["hubspot"] or "GA4" in z["fonti"]) and aid not in riviste:
            z["priorita"] = LIVELLI[min(LIVELLI.index(z["priorita"]) + 1, 2)]
    elenco = sorted(azioni.values(), key=lambda z: (ORDINE_PRIORITA.get(z["priorita"], 3), -z["peso"]))
    for z in elenco:
        z["pagine"] = sorted(z["pagine"], key=lambda i: (i != z["principale"], pagine[i]))
        z["punteggio"] = round(z["punteggio"], 1)
        z["peso"] = round(z["peso"], 3)
        z["casi"].sort(key=lambda i: -casi[i]["punteggio"])
        z["collegate"] = sorted(set(z["collegate"]))
        z.pop("_priorita_hubspot", None)

    # --- Pagine più coinvolte ---
    coinvolte = defaultdict(lambda: {"casi": 0, "impressioni": 0, "come_principale": 0})
    for c in casi:
        if c["tipo"] == "brand":
            continue
        for ruolo, i in (("p", c["p"]), ("c", c["c"])):
            d = coinvolte[i]
            d["casi"] += 1
            d["impressioni"] += round(c["impressioni"] * c["qc"])
            d["come_principale"] += ruolo == "p"
    pagine_top = sorted(({"pagina": i, **d} for i, d in coinvolte.items()), key=lambda d: -d["impressioni"])[:30]

    # --- Confronto con l'estrazione precedente ---
    confronto = None
    precedenti = sorted(d for d in cartella.parent.iterdir()
                        if d.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.name) and d.name < cartella.name
                        and (d / "cannibalizzazioni.csv").exists())
    if precedenti:
        prec = precedenti[-1]
        chiave = lambda r: (r["query"], r["pagina_principale"], r["pagina_concorrente"])
        vecchi = {chiave(r) for r in leggi(prec / "cannibalizzazioni.csv") if r["brand"] == "no"}
        nuovi = {chiave(r) for r in righe if r["brand"] == "no"}
        confronto = {"estrazione": prec.name, "nuove": len(nuovi - vecchi), "risolte": len(vecchi - nuovi),
                     "ancora_aperte": len(nuovi & vecchi)}

    estratta = dt.date.fromisoformat(meta["estratto_il"][:10])
    dati = {
        "versione": 2,
        "cliente": a.cliente,
        "sito": meta["sito"],
        "periodo": {"inizio": meta["inizio"], "fine": meta["fine"]},
        "estrazione": cartella.name,
        "prossima": (estratta + dt.timedelta(days=a.frequenza)).isoformat(),
        "totali": meta["totali"],
        "quota_query_anonime": meta.get("quota_click_query_anonime"),
        "yoy": yoy,
        "soglie": {"quota": 0.2, "min_impressioni": 100},
        "brand": [b.strip() for b in a.brand.split(",") if b.strip()],
        "conteggi": {t: sum(1 for c in casi if c["tipo"] == t) for t in ("stessa-lingua", "lingue", "brand")},
        "mesi": mesi,
        "pagine": pagine,
        "azioni": [{k: z[k] for k in ("id", "categoria", "tipo", "famiglia", "fonti", "titolo", "rimedio", "skill",
                                      "priorita", "punteggio", "peso", "impressioni", "click", "pagine", "casi",
                                      "keyword", "problema", "collegate", "hubspot", "visite_ai")} for z in elenco],
        "ricerche": ricerche,
        "hubspot": hubspot,
        "ga4": ga4,
        "audit_tecnico": audit,
        "casi": casi,
        "pagine_coinvolte": pagine_top,
        "confronto": confronto,
    }

    uscita = Path(a.uscita)
    uscita.mkdir(parents=True, exist_ok=True)
    (uscita / "dati.json").write_text(json.dumps(dati, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    titolo = f"Piano SEO e AEO {a.cliente}"
    html = MODELLO.read_text(encoding="utf-8").replace("{{TITOLO}}", titolo)
    (uscita / "index.html").write_text(html, encoding="utf-8")

    per_cat = defaultdict(int)
    for z in elenco:
        per_cat[(z["categoria"], z["priorita"])] += 1
    print(f"Dashboard preparata in {uscita}: {len(elenco)} azioni, {len(casi)} casi di cannibalizzazione, "
          f"{ricerche['strumento'] if ricerche else 'nessuno strumento di ricerca'}, "
          f"HubSpot {hubspot['stato']}, GA4 {ga4['stato']}, "
          f"audit tecnico {'sì' if audit else 'no'}"
          + (f" ({sum(1 for z in elenco if 'GA4' in z['fonti'])} azioni su pagine con visite AI)" if ga4['stato'] == 'presente' else "")
          + ", dati.json "
          f"{(uscita / 'dati.json').stat().st_size // 1024} KB")
    print("  per categoria e priorità:", dict(sorted(per_cat.items())))
    print("\nPrime 15 azioni:")
    for z in elenco[:15]:
        print(f"  {z['id']:12} {z['categoria']:17} {z['priorita']:5} {'+'.join(z['fonti']):30} {z['titolo'][:70]}")


if __name__ == "__main__":
    main()
