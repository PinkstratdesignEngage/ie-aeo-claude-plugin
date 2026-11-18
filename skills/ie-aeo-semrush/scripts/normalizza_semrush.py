#!/usr/bin/env python3
"""Porta i dati di Semrush in CSV con colonne fisse, qualunque sia la fonte.

Uso, dalla radice del repo del cliente:
    python3 -I normalizza_semrush.py raw/semrush/<AAAA-MM-GG> --dominio esempio.com [--codici-aio "x,y"]

Legge i file in <cartella>/originali/, salvati dal connettore Semrush (JSON o CSV) o
esportati dall'interfaccia (CSV con virgola, punto e virgola o tabulazione). Il tipo
di report si riconosce dal nome del file:

    posizioni-<db>.csv|json       Organic Research > Positions (connettore: resource_organic)
    competitor-<db>.csv|json      Organic Research > Competitors (connettore: domain_organic_organic)
    gap-<db>.csv|json             Keyword Gap (connettore: domain_domains, con --gap-domini)
    site-audit-problemi.csv|json  Site Audit, un problema per riga con la pagina coinvolta

I nomi delle colonne si riconoscono in inglese, in italiano e come codici dell'API
(Ph, Po, Nq...). Se un file ha colonne che lo script non conosce, si ferma e le elenca.

Scrive nella cartella: posizioni.csv, competitor.csv, gap.csv, site_audit.csv e
riepilogo_fonti.json, con le righe lette per ogni file.
"""
import argparse
import csv
import io
import json
import re
import sys
from pathlib import Path

SINONIMI = {
    "keyword": ["keyword", "keywords", "parola chiave", "ph"],
    "posizione": ["position", "posizione", "po", "pos"],
    "posizione_prec": ["previous position", "previous_position", "posizione precedente", "pp"],
    "volume": ["search volume", "volume", "volume di ricerca", "nq"],
    "kd": ["keyword difficulty", "keyword_difficulty", "kd", "kd%", "difficoltà", "difficolta", "keyword difficulty index"],
    "intento": ["keyword intents", "intents", "intent", "intento", "in"],
    "url": ["url", "page url", "page", "pagina", "ur", "landing page"],
    "traffico_pct": ["traffic (%)", "traffic_share", "traffic %", "traffico (%)", "tr"],
    "serp": ["serp features by keyword", "triggered_serp_features", "serp features", "funzionalità serp", "fk", "fp"],
    "dominio": ["domain", "dominio", "competitor", "dn"],
    "keyword_comuni": ["common keywords", "common_keywords", "keyword comuni", "np"],
    "keyword_organiche": ["organic keywords", "organic_keywords", "se keywords", "keyword organiche", "or"],
    "rilevanza": ["competition level", "competition_level", "competitor relevance", "rilevanza", "cr"],
    "problema": ["issue", "issue name", "issue_title", "title", "problema", "check", "issue type name"],
    "gravita": ["type", "severity", "issue type", "gravità", "gravita", "tipo"],
}
INTENTI = {"0": "commerciale", "1": "informativo", "2": "navigazionale", "3": "transazionale",
           "commercial": "commerciale", "informational": "informativo",
           "navigational": "navigazionale", "transactional": "transazionale"}
GRAVITA = {"error": "errore", "errors": "errore", "errore": "errore", "errori": "errore",
           "warning": "avviso", "warnings": "avviso", "avviso": "avviso", "avvisi": "avviso",
           "notice": "nota", "notices": "nota", "nota": "nota", "note": "nota"}


def leggi_righe(percorso):
    testo = percorso.read_text(encoding="utf-8-sig")
    if percorso.suffix.lower() == ".json":
        dati = json.loads(testo)
        if isinstance(dati, dict):
            for k in ("rows", "data", "results", "items"):
                if isinstance(dati.get(k), list):
                    dati = dati[k]
                    break
        if not isinstance(dati, list) or (dati and not isinstance(dati[0], dict)):
            # Il connettore può restituire il CSV dell'API come testo dentro il JSON
            if isinstance(dati, dict) and isinstance(dati.get("text"), str):
                return leggi_testo(dati["text"])
            sys.exit(f"{percorso}: JSON non riconosciuto (atteso un elenco di righe).")
        return [{str(k): ("" if v is None else str(v)) for k, v in r.items()} for r in dati]
    return leggi_testo(testo)


def leggi_testo(testo):
    dialetto = csv.Sniffer().sniff(testo[:4096], delimiters=",;\t")
    return list(csv.DictReader(io.StringIO(testo), dialect=dialetto))


def mappa(colonne, richieste, facoltative, percorso):
    trovate = {}
    norm = {c: c.strip().lower() for c in colonne}
    for chiave in richieste + facoltative:
        for c, n in norm.items():
            if n in SINONIMI[chiave]:
                trovate[chiave] = c
                break
    mancanti = [k for k in richieste if k not in trovate]
    if mancanti:
        sys.exit(f"{percorso.name}: non trovo le colonne {', '.join(mancanti)}. Colonne del file: {list(colonne)}")
    return trovate


def numero(v, intero=True):
    v = (v or "").strip().replace("%", "")
    if not v or v in ("-", "n/a"):
        return ""
    v = v.replace(",", ".") if v.count(",") == 1 and "." not in v else v.replace(",", "")
    try:
        return int(float(v)) if intero else round(float(v), 2)
    except ValueError:
        return ""


def intento(v):
    parti = [INTENTI.get(p.strip().lower(), p.strip().lower()) for p in re.split(r"[,;|]", v or "") if p.strip()]
    return ", ".join(dict.fromkeys(parti))


def aio(serp, codici):
    s = (serp or "").lower()
    if "ai overview" in s or "ai mode" in s:
        return "sì"
    codici_serp = {p.strip() for p in re.split(r"[,;|\s]", s) if p.strip()}
    return "sì" if codici and codici_serp & codici else "no"


def database(nome, prefisso):
    m = re.match(prefisso + r"-([a-z]{2,3})$", nome.lower())
    return m.group(1) if m else ""


def dominio_da_url(u):
    return re.sub(r"^https?://(www\.)?", "", u.strip().lower()).split("/")[0]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cartella")
    p.add_argument("--dominio", required=True, help="dominio del cliente, es. esempio.com")
    p.add_argument("--codici-aio", default="52,aio", help="codici SERP dell'AI Overview: 52 nei report di analisi, aio nei progetti (default: 52,aio)")
    p.add_argument("--gap-domini", default="", help="competitor del keyword gap nell'ordine passato al report, separati da virgola")
    a = p.parse_args()

    cartella = Path(a.cartella)
    originali = cartella / "originali"
    if not originali.is_dir():
        sys.exit(f"Manca {originali}: salva lì i dati del connettore o gli export di Semrush.")
    cliente = a.dominio.lower().removeprefix("www.")
    codici = {c.strip() for c in a.codici_aio.split(",") if c.strip()}
    gap_domini = [d.strip().lower().removeprefix("www.") for d in a.gap_domini.split(",") if d.strip()]
    file = sorted(f for f in originali.iterdir() if f.suffix.lower() in (".csv", ".json"))
    if not file:
        sys.exit(f"Nessun file .csv o .json in {originali}.")

    posizioni, competitor, gap, audit, fonti = [], [], [], [], {}
    noti = ("posizioni-", "competitor-", "gap-", "site-audit-problemi")
    for f in file:
        if not f.stem.startswith(noti):
            continue  # crediti.json, progetti e altri file di servizio
        nome, righe = f.stem, leggi_righe(f)
        if not righe:
            fonti[f.name] = 0
            continue
        colonne = list(righe[0].keys())
        if nome.startswith("posizioni-"):
            m = mappa(colonne, ["keyword", "posizione", "volume"],
                      ["posizione_prec", "kd", "intento", "url", "traffico_pct", "serp"], f)
            db = database(nome, "posizioni")
            for r in righe:
                serp = r.get(m.get("serp", ""), "")
                posizioni.append({
                    "database": db, "keyword": r[m["keyword"]].strip().lower(),
                    "posizione": numero(r[m["posizione"]]), "posizione_prec": numero(r.get(m.get("posizione_prec", ""), "")),
                    "volume": numero(r[m["volume"]]), "kd": numero(r.get(m.get("kd", ""), "")),
                    "intento": intento(r.get(m.get("intento", ""), "")), "url": r.get(m.get("url", ""), "").strip(),
                    "traffico_pct": numero(r.get(m.get("traffico_pct", ""), ""), intero=False),
                    "serp": serp.strip(), "aio": aio(serp, codici),
                })
        elif nome.startswith("competitor-"):
            m = mappa(colonne, ["dominio"], ["keyword_comuni", "keyword_organiche", "rilevanza"], f)
            db = database(nome, "competitor")
            for r in righe:
                competitor.append({
                    "database": db, "dominio": dominio_da_url(r[m["dominio"]]),
                    "keyword_comuni": numero(r.get(m.get("keyword_comuni", ""), "")),
                    "keyword_organiche": numero(r.get(m.get("keyword_organiche", ""), "")),
                    "rilevanza": numero(r.get(m.get("rilevanza", ""), ""), intero=False),
                })
        elif nome.startswith("gap-"):
            m = mappa(colonne, ["keyword", "volume"], ["kd", "intento", "serp"], f)
            db = database(nome, "gap")
            note = set(m.values())
            posizionali = sorted(c for c in colonne if re.fullmatch(r"position_domain_\d", c))
            if posizionali:
                # Connettore: position_domain_1 è il cliente, le altre seguono l'ordine di --gap-domini
                nomi = [cliente] + gap_domini
                if len(nomi) < len(posizionali):
                    sys.exit(f"{f.name}: il report ha {len(posizionali)} domini, passa i competitor in ordine con --gap-domini.")
                for r in righe:
                    for i, c in enumerate(posizionali):
                        r[nomi[i]] = r.pop(c)
                colonne = [c for c in colonne if c not in posizionali] + nomi[:len(posizionali)]
            # Le altre colonne con un dominio nel nome sono le posizioni di ciascun dominio
            domini = [c for c in colonne if c not in note and "." in c and " " not in c.strip()]
            col_cliente = next((c for c in domini if cliente in c.lower()), None)
            if not col_cliente:
                sys.exit(f"{f.name}: non trovo la colonna del dominio {cliente}. Colonne: {colonne}")
            for r in righe:
                migliore, pos_migliore = "", ""
                for c in domini:
                    if c == col_cliente:
                        continue
                    v = numero(r.get(c, ""))
                    if v != "" and v > 0 and (pos_migliore == "" or v < pos_migliore):
                        migliore, pos_migliore = dominio_da_url(c), v
                pc = numero(r.get(col_cliente, ""))
                serp = r.get(m.get("serp", ""), "")
                gap.append({
                    "database": db, "keyword": r[m["keyword"]].strip().lower(),
                    "volume": numero(r[m["volume"]]), "kd": numero(r.get(m.get("kd", ""), "")),
                    "intento": intento(r.get(m.get("intento", ""), "")),
                    "posizione_cliente": pc if pc not in ("", 0) else "",
                    "miglior_competitor": migliore, "posizione_competitor": pos_migliore,
                    "aio": aio(serp, codici),
                })
        elif nome.startswith("site-audit-problemi"):
            m = mappa(colonne, ["url", "problema"], ["gravita"], f)
            for r in righe:
                g = r.get(m.get("gravita", ""), "").strip().lower()
                audit.append({"url": r[m["url"]].strip(), "problema": r[m["problema"]].strip(),
                              "gravita": GRAVITA.get(g, g)})
        else:
            print(f"Ignoro {f.name}: il nome non corrisponde a un tipo di report noto.")
            continue
        fonti[f.name] = len(righe)

    # Le pagine di uno stesso report possono sovrapporsi (per traffico e per filtro): una riga per combinazione
    viste, uniche = set(), []
    for r in posizioni:
        k = (r["database"], r["keyword"], r["url"], r["posizione"])
        if k not in viste:
            viste.add(k)
            uniche.append(r)
    posizioni = uniche

    uscite = {
        "posizioni.csv": (posizioni, ["database", "keyword", "posizione", "posizione_prec", "volume", "kd", "intento",
                                      "url", "traffico_pct", "serp", "aio"]),
        "competitor.csv": (competitor, ["database", "dominio", "keyword_comuni", "keyword_organiche", "rilevanza"]),
        "gap.csv": (gap, ["database", "keyword", "volume", "kd", "intento", "posizione_cliente",
                          "miglior_competitor", "posizione_competitor", "aio"]),
        "site_audit.csv": (audit, ["url", "problema", "gravita"]),
    }
    for nome, (righe, colonne) in uscite.items():
        with open(cartella / nome, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=colonne)
            w.writeheader()
            w.writerows(righe)
        print(f"  {nome}: {len(righe)} righe")
    (cartella / "riepilogo_fonti.json").write_text(json.dumps(
        {"dominio": cliente, "file_letti": fonti, "codici_aio": sorted(codici)}, indent=2, ensure_ascii=False),
        encoding="utf-8")


if __name__ == "__main__":
    main()
