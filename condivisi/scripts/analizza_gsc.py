#!/usr/bin/env python3
"""Analizza un export di Google Search Console con le coppie query-pagina.

Uso:
  python3 -I analizza_gsc.py <export.csv> <url-della-pagina> [--quota 0.2] [--min-clic 1]
  python3 -I analizza_gsc.py <export.csv> --tema "parola, altra parola" [--min-impressioni 10]

L'export di riferimento è raw/gsc/<AAAA-MM-GG>/query_pagina.csv, prodotto
dalla skill ie-aeo-search-console. Va bene anche un altro export con una riga
per coppia query-pagina e le colonne query, pagina, clic e impressioni (la
posizione è facoltativa), per esempio da Looker Studio o da Search Analytics
for Sheets; l'export dell'interfaccia web non ha le due dimensioni insieme.
Riconosce i nomi delle colonne in italiano e in inglese.

Con l'URL stampa due tabelle in Markdown:
1. le query che portano traffico alla pagina, da proteggere nella ristrutturazione;
2. le possibili cannibalizzazioni: per ogni query della pagina, le altre pagine
   del sito che prendono almeno la quota indicata dei suoi clic (o delle
   impressioni, se i clic sono pochi).

Con --tema, per un contenuto nuovo, stampa:
1. le pagine del sito che ricevono già traffico dalle query che contengono
   almeno una delle parole indicate;
2. quelle query, con le pagine che le ricevono: le query con più pagine sono
   possibili cannibalizzazioni da non peggiorare.
"""
import sys, csv, re
from collections import defaultdict

COLONNE = {
    "query": ["query", "query principali", "top queries", "keys_query", "chiave"],
    "pagina": ["page", "pagina", "pagine principali", "top pages", "landing page", "url", "keys_page"],
    "clic": ["clicks", "clic", "click"],
    "impressioni": ["impressions", "impressioni"],
    "posizione": ["position", "posizione", "posizione media", "average position"],
}

def numero(v, intero=False):
    v = (v or "").strip().replace("%", "")
    if not v:
        return 0.0
    if intero:
        # clic e impressioni sono interi: punti e virgole sono separatori delle migliaia
        v = re.sub(r"[.,\s]", "", v)
    elif "," in v and "." in v:
        v = v.replace(".", "").replace(",", ".")
    elif "," in v:
        v = v.replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return 0.0

def norm_url(u):
    u = u.strip().lower()
    u = re.sub(r"^https?://(www\.)?", "", u)
    return u.split("#")[0].split("?")[0].rstrip("/")

def mappa_colonne(intestazione):
    trovate = {}
    for chiave, nomi in COLONNE.items():
        for i, nome in enumerate(intestazione):
            if nome.strip().lower() in nomi:
                trovate[chiave] = i
                break
    mancanti = [c for c in ("query", "pagina", "clic", "impressioni") if c not in trovate]
    if mancanti:
        sys.exit(f"Colonne mancanti: {', '.join(mancanti)}. Intestazione letta: {intestazione}")
    return trovate

def leggi_export(percorso):
    with open(percorso, newline="", encoding="utf-8-sig") as f:
        campione = f.read(4096)
        f.seek(0)
        dialetto = csv.Sniffer().sniff(campione, delimiters=",;\t")
        righe = list(csv.reader(f, dialetto))
    col = mappa_colonne(righe[0])

    per_query = defaultdict(list)
    for r in righe[1:]:
        if len(r) <= max(col.values()):
            continue
        per_query[r[col["query"]].strip().lower()].append({
            "pagina": r[col["pagina"]].strip(),
            "clic": numero(r[col["clic"]], intero=True),
            "impressioni": numero(r[col["impressioni"]], intero=True),
            "posizione": numero(r[col["posizione"]]) if "posizione" in col else None,
        })
    return per_query

def pos(p):
    return f"{p['posizione']:.1f}" if p["posizione"] else "-"

def analizza_tema(per_query, tema, min_imp):
    parole = [p.strip().lower() for p in tema.split(",") if p.strip()]
    trovate = {q: pagine for q, pagine in per_query.items()
               if any(p in q for p in parole) and sum(x["impressioni"] for x in pagine) >= min_imp}
    if not trovate:
        print(f"Nessuna query con almeno {min_imp:.0f} impressioni contiene: {', '.join(parole)}.")
        print("Il tema non porta ancora traffico al sito: nessun rischio di cannibalizzazione dai dati.")
        return

    per_pagina = defaultdict(lambda: {"clic": 0, "impressioni": 0, "query": 0})
    for pagine in trovate.values():
        for p in pagine:
            d = per_pagina[p["pagina"]]
            d["clic"] += p["clic"]
            d["impressioni"] += p["impressioni"]
            d["query"] += 1

    print(f"## Pagine che ricevono già traffico sul tema ({', '.join(parole)})\n")
    print("| Pagina | Clic | Impressioni | Query del tema |")
    print("|---|---|---|---|")
    for pagina, d in sorted(per_pagina.items(), key=lambda x: (-x[1]["clic"], -x[1]["impressioni"]))[:20]:
        print(f"| {pagina} | {d['clic']:.0f} | {d['impressioni']:.0f} | {d['query']} |")

    print(f"\n## Query del tema ({len(trovate)})\n")
    print("| Query | Clic | Impressioni | Pagine | Pagina principale | Posizione |")
    print("|---|---|---|---|---|---|")
    ordinate = sorted(trovate.items(), key=lambda x: -sum(p["impressioni"] for p in x[1]))
    for q, pagine in ordinate[:40]:
        prima = max(pagine, key=lambda p: (p["clic"], p["impressioni"]))
        print(f"| {q} | {sum(p['clic'] for p in pagine):.0f} | {sum(p['impressioni'] for p in pagine):.0f} "
              f"| {len(pagine)} | {prima['pagina']} | {pos(prima)} |")
    if len(ordinate) > 40:
        print(f"\n…e altre {len(ordinate) - 40} query.")

def main():
    args, opzioni, it = [], {}, iter(sys.argv[1:])
    for a in it:
        if a.startswith("--"):
            opzioni[a] = next(it, "")
        else:
            args.append(a)
    tema = opzioni.get("--tema")
    if len(args) != (1 if tema else 2):
        sys.exit(__doc__)
    quota = float(opzioni.get("--quota", 0.2))
    min_clic = float(opzioni.get("--min-clic", 1))
    per_query = leggi_export(args[0])
    if tema:
        return analizza_tema(per_query, tema, float(opzioni.get("--min-impressioni", 10)))
    url = args[1]
    obiettivo = norm_url(url)

    proprie = []
    for q, pagine in per_query.items():
        mia = next((p for p in pagine if norm_url(p["pagina"]) == obiettivo), None)
        if mia:
            proprie.append((q, mia, [p for p in pagine if norm_url(p["pagina"]) != obiettivo]))
    if not proprie:
        sys.exit(f"Nessuna query trovata per {url}. Controlla che l'URL sia scritto come nell'export.")
    proprie.sort(key=lambda x: (-x[1]["clic"], -x[1]["impressioni"]))

    print(f"## Query della pagina {url}\n")
    print("| Query | Clic | Impressioni | Posizione |")
    print("|---|---|---|---|")
    for q, mia, _ in proprie:
        print(f"| {q} | {mia['clic']:.0f} | {mia['impressioni']:.0f} | {pos(mia)} |")

    print(f"\n## Possibili cannibalizzazioni (quota minima {quota:.0%})\n")
    trovate = 0
    print("| Query | Clic della pagina | Altra pagina | Clic | Impressioni | Posizione | Quota |")
    print("|---|---|---|---|---|---|---|")
    for q, mia, altre in proprie:
        tot_clic = mia["clic"] + sum(p["clic"] for p in altre)
        tot_imp = mia["impressioni"] + sum(p["impressioni"] for p in altre)
        usa_clic = tot_clic >= max(min_clic, 1) * 2
        for p in sorted(altre, key=lambda p: (-p["clic"], -p["impressioni"])):
            q_val = p["clic"] / tot_clic if usa_clic else (p["impressioni"] / tot_imp if tot_imp else 0)
            if q_val >= quota:
                trovate += 1
                base = "clic" if usa_clic else "impr."
                print(f"| {q} | {mia['clic']:.0f} | {p['pagina']} | {p['clic']:.0f} | {p['impressioni']:.0f} | {pos(p)} | {q_val:.0%} {base} |")
    if not trovate:
        print("| Nessuna | | | | | | |")

if __name__ == "__main__":
    main()
