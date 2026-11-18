#!/usr/bin/env python3
"""Incrocia i dati normalizzati di uno strumento SEO con l'ultima estrazione di Search Console.

Uso, dalla radice del repo del cliente:
    python3 -I analizza_ricerche.py raw/<strumento>/<AAAA-MM-GG> --strumento Ahrefs
        --gsc raw/gsc/<AAAA-MM-GG> [--brand "a,b"] [--termini "x,y"] [--min-volume 50]

Lo strumento è Semrush o Ahrefs: i due lavorano sugli stessi file normalizzati, scritti
da normalizza_semrush.py o da normalizza_ahrefs.py. Legge posizioni.csv, gap.csv e
site_audit.csv e, dalla cartella di Search Console, query_pagina.csv, pagine.csv e
cannibalizzazioni.csv. Scrive nella cartella dell'estrazione:
- opportunita_keyword.csv: keyword in posizione 4-20, con il volume dello strumento e i
  numeri di Search Console della stessa query;
- in_calo.csv: keyword che hanno perso almeno 5 posizioni o la prima pagina;
- gap_contenuti.csv: keyword dove un competitor è nei primi 10 e il cliente no;
- aio.csv: keyword che mostrano un AI Overview, con la posizione del cliente;
- site_audit_pesato.csv: problemi del Site Audit pesati con il traffico delle pagine
  coinvolte e con le cannibalizzazioni che le toccano;
- ai_visibilita.csv, solo se c'è ai_pagine.csv (Ahrefs): pagine citate dagli assistenti AI,
  con le impressioni di Search Console.
Poi stampa un riepilogo in Markdown. Lo script trova e ordina, non decide.

Con --termini, opportunità, gap e AI Overview tengono solo le keyword che contengono
almeno una radice dei termini di settore: serve quando i nomi dei prodotti coincidono
con nomi di luoghi o di persone e lo strumento attribuisce al sito ricerche estranee.

Peso delle opportunità, dichiarato nel report: volume × 1 in posizione 4-10 o 0,5
in 11-20, × 1,25 con intento commerciale o transazionale, × 1,2 con AI Overview.
"""
import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

ORDINE_GRAVITA = {"errore": 0, "avviso": 1, "nota": 2}
# Problemi del Site Audit che spiegano o aggravano una cannibalizzazione
LEGATI_CANNIBALIZZAZIONE = re.compile(
    r"hreflang|canonical|duplicate content|duplicate pages|contenut\w* duplicat|pagine duplicat|lang attribute",
    re.IGNORECASE)


def leggi(percorso):
    if not percorso.exists():
        return []
    with open(percorso, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def n(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def norm_url(u):
    u = re.sub(r"^https?://(www\.)?", "", (u or "").strip().lower())
    return u.split("#")[0].split("?")[0].rstrip("/")


def scrivi(percorso, righe, colonne):
    with open(percorso, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colonne)
        w.writeheader()
        w.writerows(righe)


def tabella(righe, colonne, k=15):
    if not righe:
        return "Nessun caso.\n"
    out = ["| " + " | ".join(colonne) + " |", "|" + "---|" * len(colonne)]
    out += ["| " + " | ".join(str(r[c]) for c in colonne) + " |" for r in righe[:k]]
    if len(righe) > k:
        out.append(f"\n…e altri {len(righe) - k} nel CSV.")
    return "\n".join(out) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cartella")
    p.add_argument("--strumento", default="Semrush", help="Semrush o Ahrefs: compare nel riepilogo (default: %(default)s)")
    p.add_argument("--gsc", help="cartella dell'estrazione di Search Console da incrociare")
    p.add_argument("--brand", default="")
    p.add_argument("--min-volume", type=int, default=50)
    p.add_argument("--min-gsc", type=int, default=100,
                   help="impressioni di Search Console sopra cui un'opportunità è confermata (default 100)")
    p.add_argument("--termini", default="", help="radici dei termini di settore separate da virgola: "
                   "opportunità, gap e AI Overview tengono solo le keyword che ne contengono almeno una")
    a = p.parse_args()

    sem = Path(a.cartella)
    if not (sem / "posizioni.csv").exists():
        sys.exit(f"Manca posizioni.csv: lancia prima normalizza_{a.strumento.lower()}.py.")
    brand = [b.strip().lower() for b in a.brand.split(",") if b.strip()]
    e_brand = lambda q: any(b in q for b in brand)
    termini = [t.strip().lower() for t in a.termini.split(",") if t.strip()]
    # Senza termini ogni keyword è del settore; con i termini, quelle che non ne contengono sono rumore
    di_settore = (lambda q: any(t in q for t in termini)) if termini else (lambda q: True)
    scartate = defaultdict(int)

    # Search Console: per query la pagina più forte, per pagina i totali
    gsc_query, gsc_pagine, pagine_cann = {}, {}, defaultdict(int)
    if a.gsc:
        g = Path(a.gsc)
        for r in leggi(g / "query_pagina.csv"):
            q, c, i = r["query"], int(r["click"]), int(r["impressioni"])
            tot = gsc_query.setdefault(q, {"click": 0, "impressioni": 0, "pagina": "", "posizione": "", "best": -1})
            tot["click"] += c
            tot["impressioni"] += i
            if i > tot["best"]:
                tot.update(best=i, pagina=r["pagina"], posizione=r["posizione"])
        for r in leggi(g / "pagine.csv"):
            gsc_pagine[norm_url(r["pagina"])] = (int(r["click"]), int(r["impressioni"]))
        for r in leggi(g / "cannibalizzazioni.csv"):
            if r.get("brand") == "no":
                pagine_cann[norm_url(r["pagina_principale"])] += 1
                pagine_cann[norm_url(r["pagina_concorrente"])] += 1
        if not gsc_query:
            sys.exit(f"Nessun dato in {g}/query_pagina.csv.")

    def con_gsc(riga, keyword):
        d = gsc_query.get(keyword)
        riga.update(gsc_click=d["click"] if d else "", gsc_impressioni=d["impressioni"] if d else "",
                    gsc_posizione=d["posizione"] if d else "", gsc_pagina=d["pagina"] if d else "")
        return riga

    posizioni = leggi(sem / "posizioni.csv")

    # 1. Opportunità
    opp = []
    for r in posizioni:
        pos, vol = n(r["posizione"]), n(r["volume"])
        if pos is None or vol is None or not 4 <= pos <= 20 or vol < a.min_volume or e_brand(r["keyword"]):
            continue
        if not di_settore(r["keyword"]):
            scartate["opportunità"] += 1
            continue
        peso = vol * (1 if pos <= 10 else 0.5)
        if any(x in r["intento"] for x in ("commerciale", "transazionale")):
            peso *= 1.25
        if r["aio"] == "sì":
            peso *= 1.2
        opp.append(con_gsc({"database": r["database"], "keyword": r["keyword"], "posizione": pos, "volume": vol,
                            "kd": r["kd"], "intento": r["intento"], "aio": r["aio"], "url": r["url"],
                            "punteggio": round(peso)}, r["keyword"]))
    # Confermata: anche Search Console vede il sito su quella ricerca. Senza conferma il volume dello
    # strumento può riguardare una ricerca dove il sito compare per caso (nomi di luoghi, prodotti per la casa)
    for r in opp:
        r["confermata_gsc"] = "sì" if (r["gsc_impressioni"] or 0) >= a.min_gsc else "no"
    opp.sort(key=lambda r: (r["confermata_gsc"] != "sì", -r["punteggio"]))

    # 2. In calo
    calo = []
    for r in posizioni:
        pos, prec, vol = n(r["posizione"]), n(r["posizione_prec"]), n(r["volume"])
        if None in (pos, prec, vol) or prec == 0 or vol < a.min_volume:
            continue
        if pos - prec >= 5 or (prec <= 10 < pos):
            calo.append(con_gsc({"database": r["database"], "keyword": r["keyword"], "posizione_prec": prec,
                                 "posizione": pos, "volume": vol, "url": r["url"]}, r["keyword"]))
    calo.sort(key=lambda r: -r["volume"])

    # 3. Gap con i competitor
    gap = []
    for r in leggi(sem / "gap.csv"):
        vol, pc, pcomp = n(r["volume"]), n(r["posizione_cliente"]), n(r["posizione_competitor"])
        if vol is None or vol < a.min_volume or pcomp is None or pcomp > 10 or e_brand(r["keyword"]):
            continue
        if not di_settore(r["keyword"]):
            scartate["gap"] += 1
            continue
        if pc is not None and pc <= 20:
            continue
        gap.append(con_gsc({"database": r["database"], "keyword": r["keyword"], "volume": vol, "kd": r["kd"],
                            "intento": r["intento"], "posizione_cliente": pc or "",
                            "miglior_competitor": r["miglior_competitor"], "posizione_competitor": pcomp,
                            "aio": r["aio"]}, r["keyword"]))
    gap.sort(key=lambda r: -r["volume"])

    # 4. AI Overview
    aio = [{"database": r["database"], "keyword": r["keyword"], "volume": n(r["volume"]) or 0,
            "posizione_cliente": r["posizione"], "url": r["url"], "fonte": "posizioni"}
           for r in posizioni if r["aio"] == "sì" and not e_brand(r["keyword"]) and di_settore(r["keyword"])]
    aio += [{"database": r["database"], "keyword": r["keyword"], "volume": r["volume"],
             "posizione_cliente": r["posizione_cliente"], "url": "", "fonte": "gap"}
            for r in gap if r["aio"] == "sì"]
    aio.sort(key=lambda r: -r["volume"])

    # 5. Site Audit pesato
    per_problema = defaultdict(lambda: {"gravita": "", "pagine": set()})
    for r in leggi(sem / "site_audit.csv"):
        d = per_problema[r["problema"]]
        d["gravita"] = d["gravita"] or r["gravita"]
        d["pagine"].add(norm_url(r["url"]))
    audit = []
    for problema, d in per_problema.items():
        click = sum(gsc_pagine.get(u, (0, 0))[0] for u in d["pagine"])
        imp = sum(gsc_pagine.get(u, (0, 0))[1] for u in d["pagine"])
        cann = sum(1 for u in d["pagine"] if u in pagine_cann)
        prime = sorted(d["pagine"], key=lambda u: -gsc_pagine.get(u, (0, 0))[1])[:5]
        audit.append({"problema": problema, "gravita": d["gravita"], "pagine": len(d["pagine"]),
                      "click_pagine": click, "impressioni_pagine": imp, "pagine_in_cannibalizzazione": cann,
                      "legato_a_cannibalizzazione": "sì" if LEGATI_CANNIBALIZZAZIONE.search(problema) and cann else "no",
                      "pagine_principali": " ".join(prime)})
    audit.sort(key=lambda r: (ORDINE_GRAVITA.get(r["gravita"], 3), -r["impressioni_pagine"], -r["pagine"]))

    # 6. Visibilità negli assistenti AI: solo Ahrefs la misura per pagina
    ai = []
    for r in leggi(sem / "ai_pagine.csv"):
        risposte = n(r.get("risposte")) or 0
        if not risposte:
            continue
        u = norm_url(r["url"])
        ai.append({"url": r["url"], "assistente": r.get("assistente", ""), "risposte": risposte,
                   "gsc_click": gsc_pagine.get(u, ("", ""))[0], "gsc_impressioni": gsc_pagine.get(u, ("", ""))[1]})
    ai.sort(key=lambda r: -r["risposte"])

    gsc_col = ["gsc_click", "gsc_impressioni", "gsc_posizione", "gsc_pagina"]
    scrivi(sem / "opportunita_keyword.csv", opp,
           ["database", "keyword", "posizione", "volume", "kd", "intento", "aio", "url", "punteggio", "confermata_gsc"]
           + gsc_col)
    scrivi(sem / "in_calo.csv", calo, ["database", "keyword", "posizione_prec", "posizione", "volume", "url"] + gsc_col)
    scrivi(sem / "gap_contenuti.csv", gap, ["database", "keyword", "volume", "kd", "intento", "posizione_cliente",
                                           "miglior_competitor", "posizione_competitor", "aio"] + gsc_col)
    scrivi(sem / "aio.csv", aio, ["database", "keyword", "volume", "posizione_cliente", "url", "fonte"])
    scrivi(sem / "site_audit_pesato.csv", audit, ["problema", "gravita", "pagine", "click_pagine", "impressioni_pagine",
                                                  "pagine_in_cannibalizzazione", "legato_a_cannibalizzazione",
                                                  "pagine_principali"])
    if ai:
        scrivi(sem / "ai_visibilita.csv", ai, ["url", "assistente", "risposte", "gsc_click", "gsc_impressioni"])

    print(f"# Riepilogo {a.strumento}: {sem.name}" + (f", incrociato con Search Console {Path(a.gsc).name}" if a.gsc else "") + "\n")
    print(f"Keyword posizionate: {len(posizioni)}. Volume minimo considerato: {a.min_volume}.")
    if termini:
        print(f"Filtro sui termini di settore: scartate {dict(scartate)} keyword che non ne contengono nessuno.")
    print()
    conf = sum(1 for r in opp if r["confermata_gsc"] == "sì")
    print(f"## Opportunità ({len(opp)} keyword in posizione 4-20, {conf} confermate da Search Console)\n")
    print(tabella(opp, ["database", "keyword", "posizione", "volume", "intento", "aio", "url", "gsc_impressioni",
                        "confermata_gsc"], 25))
    print(f"## Keyword in calo ({len(calo)})\n")
    print(tabella(calo, ["database", "keyword", "posizione_prec", "posizione", "volume", "url"]))
    print(f"## Gap con i competitor ({len(gap)})\n")
    print(tabella(gap, ["database", "keyword", "volume", "miglior_competitor", "posizione_competitor", "posizione_cliente", "aio"]))
    print(f"## Keyword con AI Overview ({len(aio)})\n")
    print(tabella(aio, ["database", "keyword", "volume", "posizione_cliente", "url"]))
    print(f"## Site Audit pesato ({len(audit)} problemi)\n")
    print(tabella(audit, ["problema", "gravita", "pagine", "impressioni_pagine", "pagine_in_cannibalizzazione",
                          "legato_a_cannibalizzazione"]))
    if ai:
        print(f"## Pagine citate dagli assistenti AI ({len(ai)} coppie pagina-assistente)\n")
        print(tabella(ai, ["url", "assistente", "risposte", "gsc_impressioni"]))


if __name__ == "__main__":
    main()
