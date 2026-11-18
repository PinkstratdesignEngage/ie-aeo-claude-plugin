#!/usr/bin/env python3
"""Porta i dati di Ahrefs in CSV con le stesse colonne che usa la skill Semrush.

Uso, dalla radice del repo del cliente:
    python3 -I normalizza_ahrefs.py raw/ahrefs/<AAAA-MM-GG> --dominio esempio.com

Legge i file in <cartella>/originali/, scaricati da estrai_ahrefs.py (JSON dell'API v3) o
esportati dall'interfaccia di Ahrefs (CSV). Il tipo di report si riconosce dal nome:

    posizioni-<paese>.json|csv            Site Explorer > Organic keywords, del cliente
    competitor-<paese>.json|csv           Site Explorer > Organic competitors
    keyword-<paese>-<dominio>.json|csv    Organic keywords di un competitor, per il gap
    top-pages.json|csv                    Site Explorer > Top pages, con le citazioni AI
    ai-risposte.json                      AI responses count, citazioni per assistente
    site-audit-problemi.json|csv          Site Audit > Issues
    site-audit-pagine.json|csv            Site Audit > pagine coinvolte da ogni problema

Scrive nella cartella, con le stesse colonne della skill ie-aeo-semrush, così che
l'analisi e la dashboard siano le stesse: posizioni.csv, competitor.csv, gap.csv,
site_audit.csv, site_audit_riepilogo.json, e in più, che Semrush non dà,
ai_pagine.csv e ai_citazioni.csv. Infine riepilogo_fonti.json.

Il gap non è un report di Ahrefs: si calcola qui, confrontando le keyword dei competitor
con quelle del cliente. Vale quindi solo entro le righe scaricate: una keyword assente dal
file del cliente può essere fuori dal limite di righe, non necessariamente non posizionata.
Il limite è scritto in riepilogo_fonti.json e va dichiarato nel report.
"""
import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

SINONIMI = {
    "keyword": ["keyword", "keywords", "parola chiave"],
    "posizione": ["best_position", "current position", "position", "posizione", "current_position"],
    "posizione_prec": ["best_position_prev", "previous position", "previous_position", "posizione precedente"],
    "volume": ["volume", "search volume", "volume di ricerca"],
    "kd": ["keyword_difficulty", "kd", "difficulty", "difficoltà", "difficolta"],
    "url": ["best_position_url", "current url", "url", "pagina", "current_url"],
    "serp": ["serp_features", "serp features", "funzionalità serp"],
    "traffico": ["sum_traffic", "traffic", "organic traffic", "traffico"],
    "dominio": ["competitor_domain", "domain", "dominio", "competitor", "target"],
    "keyword_comuni": ["keywords_common", "common keywords", "keyword comuni", "shared keywords"],
    "keyword_organiche": ["keywords_competitor", "organic keywords", "keyword organiche", "keywords"],
    "rilevanza": ["share", "competition level", "rilevanza", "overlap"],
    "problema": ["name", "issue", "issue name", "problema"],
    "gravita": ["importance", "type", "severity", "gravità", "gravita"],
    "problema_id": ["issue_id", "id"],
    "categoria": ["category", "categoria"],
    "occorrenze": ["crawled", "urls", "pages", "occorrenze"],
}
INTENTI = [("is_commercial", "commerciale"), ("is_informational", "informativo"),
           ("is_navigationale", "navigazionale"), ("is_navigational", "navigazionale"),
           ("is_transactional", "transazionale")]
GRAVITA = {"error": "errore", "errors": "errore", "errore": "errore",
           "warning": "avviso", "warnings": "avviso", "avviso": "avviso",
           "notice": "nota", "notices": "nota", "nota": "nota", "opportunity": "nota"}
ORDINE_GRAVITA = {"errore": 0, "avviso": 1, "nota": 2}
AI_NOMI = {"chatgpt": "ChatGPT", "perplexity": "Perplexity", "gemini": "Gemini", "copilot": "Copilot",
           "grok": "Grok", "google_ai_overviews": "Google AI Overviews", "google_ai_mode": "Google AI Mode",
           "google_ai_overviews_keywords": "Google AI Overviews (keyword)", "all_platforms": "Tutte le piattaforme"}


def leggi_righe(percorso):
    """Righe di un file dell'API (JSON) o di un export dell'interfaccia (CSV)."""
    testo = percorso.read_text(encoding="utf-8-sig")
    if percorso.suffix.lower() != ".json":
        dialetto = csv.Sniffer().sniff(testo[:4096], delimiters=",;\t")
        return list(csv.DictReader(io.StringIO(testo), dialect=dialetto))
    dati = json.loads(testo)
    if isinstance(dati, dict):
        elenchi = [v for v in dati.values() if isinstance(v, list)]
        if len(elenchi) == 1:
            dati = elenchi[0]
        elif not elenchi:
            return [dati]  # un solo oggetto, per esempio ai-responses-count
        else:
            sys.exit(f"{percorso.name}: la risposta ha più elenchi, non so quale leggere: {list(dati)}")
    if not isinstance(dati, list):
        sys.exit(f"{percorso.name}: JSON non riconosciuto (atteso un elenco di righe).")
    return [r if isinstance(r, dict) else {"valore": r} for r in dati]


def mappa(colonne, richieste, facoltative, percorso):
    trovate, norm = {}, {c: str(c).strip().lower() for c in colonne}
    for chiave in richieste + facoltative:
        for c, nome in norm.items():
            if nome in SINONIMI[chiave]:
                trovate[chiave] = c
                break
    mancanti = [k for k in richieste if k not in trovate]
    if mancanti:
        sys.exit(f"{percorso.name}: non trovo le colonne {', '.join(mancanti)}. Colonne del file: {list(colonne)}")
    return trovate


def numero(v, intero=True):
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float)):
        return int(v) if intero else round(float(v), 2)
    v = (v or "").strip().replace("%", "").replace(" ", "")
    if not v or v in ("-", "n/a", "None", "null"):
        return ""
    v = v.replace(",", ".") if v.count(",") == 1 and "." not in v else v.replace(",", "")
    try:
        return int(float(v)) if intero else round(float(v), 2)
    except ValueError:
        return ""


def testo_serp(v):
    if isinstance(v, (list, tuple)):
        return ", ".join(str(x) for x in v)
    return str(v or "")


def aio(serp, codici):
    s = testo_serp(serp).lower()
    if re.search(r"ai[ _-]?overview|ai[ _-]?mode", s):
        return "sì"
    presenti = {p.strip() for p in re.split(r"[,;|\s]+", s) if p.strip()}
    return "sì" if codici and presenti & codici else "no"


def intento_riga(r):
    """Ahrefs dà un booleano per intento; l'export dell'interfaccia una colonna di testo."""
    trovati = [nome for campo, nome in INTENTI if str(r.get(campo, "")).lower() in ("true", "1", "sì", "si", "yes")]
    if trovati:
        return ", ".join(dict.fromkeys(trovati))
    grezzo = str(r.get("Intents") or r.get("intents") or r.get("intent") or "").lower()
    mappa_testo = {"commercial": "commerciale", "informational": "informativo",
                   "navigational": "navigazionale", "transactional": "transazionale", "branded": "brand"}
    parti = [mappa_testo.get(p.strip(), p.strip()) for p in re.split(r"[,;|]", grezzo) if p.strip()]
    return ", ".join(dict.fromkeys(parti))


def paese(nome, prefisso):
    m = re.match(prefisso + r"-([a-z]{2})(?:-|$)", nome.lower())
    return m.group(1) if m else ""


def dominio_da(nome):
    m = re.match(r"keyword-[a-z]{2}-(.+)$", nome.lower())
    return m.group(1) if m else ""


def pulisci(d):
    return re.sub(r"^https?://(www\.)?", "", str(d).strip().lower()).split("/")[0]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cartella")
    p.add_argument("--dominio", required=True, help="dominio del cliente, es. esempio.com")
    p.add_argument("--codici-aio", default="ai_overview,ai_overview_sitelink,ai_mode",
                   help="valori di serp_features che indicano un AI Overview (default: %(default)s)")
    a = p.parse_args()

    cartella = Path(a.cartella)
    originali = cartella / "originali"
    if not originali.is_dir():
        sys.exit(f"Manca {originali}: lancia prima estrai_ahrefs.py, o salva lì gli export di Ahrefs.")
    cliente = pulisci(a.dominio)
    codici = {c.strip().lower() for c in a.codici_aio.split(",") if c.strip()}
    file = sorted(f for f in originali.iterdir() if f.suffix.lower() in (".csv", ".json"))
    if not file:
        sys.exit(f"Nessun file .csv o .json in {originali}.")

    posizioni, competitor, audit, ai_pagine, ai_citazioni, fonti = [], [], [], [], [], {}
    keyword_competitor, problemi, limite_righe = {}, [], {}

    for f in file:
        nome = f.stem.lower()
        if nome in ("unita", "progetto"):
            continue  # file di servizio, letti più avanti
        try:
            righe = leggi_righe(f)
        except ValueError as e:
            sys.exit(f"{f.name}: non riesco a leggerlo ({e}).")
        fonti[f.name] = len(righe)
        if not righe:
            continue
        colonne = list(righe[0].keys())

        if nome.startswith("posizioni-"):
            m = mappa(colonne, ["keyword", "posizione"], ["posizione_prec", "volume", "kd", "url", "serp"], f)
            pz = paese(nome, "posizioni")
            limite_righe[pz] = max(limite_righe.get(pz, 0), len(righe))
            for r in righe:
                serp = r.get(m.get("serp", ""), "")
                posizioni.append({
                    "database": pz, "keyword": str(r[m["keyword"]]).strip().lower(),
                    "posizione": numero(r[m["posizione"]]),
                    "posizione_prec": numero(r.get(m.get("posizione_prec", ""), "")),
                    "volume": numero(r.get(m.get("volume", ""), "")), "kd": numero(r.get(m.get("kd", ""), "")),
                    "intento": intento_riga(r), "url": str(r.get(m.get("url", ""), "") or "").strip(),
                    "traffico_pct": "", "serp": testo_serp(serp), "aio": aio(serp, codici),
                })
        elif nome.startswith("competitor-"):
            m = mappa(colonne, ["dominio"], ["keyword_comuni", "keyword_organiche", "rilevanza"], f)
            pz = paese(nome, "competitor")
            for r in righe:
                competitor.append({
                    "database": pz, "dominio": pulisci(r[m["dominio"]]),
                    "keyword_comuni": numero(r.get(m.get("keyword_comuni", ""), "")),
                    "keyword_organiche": numero(r.get(m.get("keyword_organiche", ""), "")),
                    "rilevanza": numero(r.get(m.get("rilevanza", ""), ""), intero=False),
                })
        elif nome.startswith("keyword-"):
            m = mappa(colonne, ["keyword", "posizione"], ["volume", "kd", "serp"], f)
            pz, dom = paese(nome, "keyword"), dominio_da(nome)
            for r in righe:
                kw, pos = str(r[m["keyword"]]).strip().lower(), numero(r[m["posizione"]])
                if pos == "" or pos <= 0:
                    continue
                prec = keyword_competitor.get((pz, kw))
                if prec is None or pos < prec["posizione_competitor"]:
                    keyword_competitor[(pz, kw)] = {
                        "database": pz, "keyword": kw, "volume": numero(r.get(m.get("volume", ""), "")),
                        "kd": numero(r.get(m.get("kd", ""), "")), "intento": intento_riga(r),
                        "miglior_competitor": dom, "posizione_competitor": pos,
                        "aio": aio(r.get(m.get("serp", ""), ""), codici),
                    }
        elif nome == "top-pages":
            for r in righe:
                url = str(r.get("url") or r.get("URL") or "").strip()
                if not url:
                    continue
                for campo, etichetta in AI_NOMI.items():
                    v = numero(r.get(f"ai_responses_{campo}", r.get(etichetta, "")))
                    if v not in ("", 0):
                        ai_pagine.append({"url": url, "assistente": etichetta, "risposte": v})
        elif nome == "ai-risposte":
            r = righe[0]
            dati = r.get("ai_responses_count", r)
            for campo, valori in (dati.items() if isinstance(dati, dict) else []):
                if isinstance(valori, dict):
                    ai_citazioni.append({"assistente": AI_NOMI.get(campo, campo),
                                         "citazioni": numero(valori.get("citations", "")),
                                         "pagine": numero(valori.get("pages", ""))})
        elif nome == "site-audit-problemi":
            m = mappa(colonne, ["problema"], ["gravita", "problema_id", "categoria", "occorrenze"], f)
            for r in righe:
                g = str(r.get(m.get("gravita", ""), "")).strip().lower()
                problemi.append({"id": str(r.get(m.get("problema_id", ""), "") or r[m["problema"]]),
                                 "titolo": str(r[m["problema"]]).strip(), "gravita": GRAVITA.get(g, g or "nota"),
                                 "categoria": str(r.get(m.get("categoria", ""), "") or ""),
                                 "occorrenze": numero(r.get(m.get("occorrenze", ""), "")) or 0})
        elif nome == "site-audit-pagine":
            m = mappa(colonne, ["url", "problema"], ["gravita"], f)
            for r in righe:
                g = str(r.get(m.get("gravita", ""), "")).strip().lower()
                audit.append({"url": str(r[m["url"]]).strip(), "problema": str(r[m["problema"]]).strip(),
                              "gravita": GRAVITA.get(g, g or "nota")})
        else:
            print(f"Ignoro {f.name}: il nome non corrisponde a un tipo di report noto.")
            fonti.pop(f.name, None)

    # Una riga per combinazione: le pagine di uno stesso report possono sovrapporsi
    viste, uniche = set(), []
    for r in posizioni:
        k = (r["database"], r["keyword"], r["url"], r["posizione"])
        if k not in viste:
            viste.add(k)
            uniche.append(r)
    posizioni = uniche

    # Gap: keyword dei competitor che il cliente non ha tra quelle scaricate, o ha oltre la 20
    pos_cliente = {}
    for r in posizioni:
        k = (r["database"], r["keyword"])
        p = r["posizione"]
        if p != "" and (k not in pos_cliente or p < pos_cliente[k]):
            pos_cliente[k] = p
    gap = []
    for (pz, kw), r in keyword_competitor.items():
        mia = pos_cliente.get((pz, kw), "")
        gap.append(dict(r, posizione_cliente=mia if mia != "" else ""))
    gap.sort(key=lambda r: -(r["volume"] or 0))

    # Site Audit: riepilogo neutro, che la dashboard legge sia per Semrush sia per Ahrefs
    pagine_per_problema = {}
    for r in audit:
        pagine_per_problema.setdefault(r["problema"], set()).add(r["url"])
    for pr in problemi:
        pr["pagine_lette"] = len(pagine_per_problema.get(pr["titolo"], ()))
    problemi.sort(key=lambda r: (ORDINE_GRAVITA.get(r["gravita"], 3), -(r["occorrenze"] or 0)))
    conta = lambda g: sum(1 for p in problemi if p["gravita"] == g)
    progetto = {}
    if (originali / "progetto.json").exists():
        progetto = json.loads((originali / "progetto.json").read_text(encoding="utf-8"))
    riepilogo = {"strumento": "Ahrefs", "errors": conta("errore"), "warnings": conta("avviso"),
                 "notices": conta("nota"),
                 "pages_crawled": numero(progetto.get("crawled_pages", progetto.get("pages", ""))) or None,
                 "pages_limit": numero(progetto.get("pages_limit", "")) or None,
                 "last_audit": progetto.get("last_crawl") or progetto.get("last_crawl_date") or None,
                 "health_score": numero(progetto.get("health_score", ""), intero=False) or None,
                 "problemi": problemi}

    uscite = {
        "posizioni.csv": (posizioni, ["database", "keyword", "posizione", "posizione_prec", "volume", "kd",
                                      "intento", "url", "traffico_pct", "serp", "aio"]),
        "competitor.csv": (competitor, ["database", "dominio", "keyword_comuni", "keyword_organiche", "rilevanza"]),
        "gap.csv": (gap, ["database", "keyword", "volume", "kd", "intento", "posizione_cliente",
                          "miglior_competitor", "posizione_competitor", "aio"]),
        "site_audit.csv": (audit, ["url", "problema", "gravita"]),
        "ai_pagine.csv": (ai_pagine, ["url", "assistente", "risposte"]),
        "ai_citazioni.csv": (ai_citazioni, ["assistente", "citazioni", "pagine"]),
    }
    for nome, (righe, colonne) in uscite.items():
        with open(cartella / nome, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=colonne)
            w.writeheader()
            w.writerows(righe)
        print(f"  {nome}: {len(righe)} righe")
    (cartella / "site_audit_riepilogo.json").write_text(
        json.dumps(riepilogo, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  site_audit_riepilogo.json: {len(problemi)} problemi "
          f"({riepilogo['errors']} errori, {riepilogo['warnings']} avvisi)")
    (cartella / "riepilogo_fonti.json").write_text(json.dumps(
        {"strumento": "Ahrefs", "dominio": cliente, "file_letti": fonti, "codici_aio": sorted(codici),
         "righe_per_paese": limite_righe,
         "nota_gap": "Il gap confronta le keyword scaricate dei competitor con quelle scaricate del cliente: "
                     "vale entro il limite di righe per paese indicato qui sopra."},
        indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
