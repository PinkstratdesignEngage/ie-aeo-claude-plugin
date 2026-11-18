#!/usr/bin/env python3
"""Analizza un'estrazione di Search Console fatta con estrai_gsc.py.

Uso: python3 -I analizza_estrazione.py raw/gsc/<AAAA-MM-GG> [--brand "nome,altro nome"]
     [--quota 0.2] [--min-impressioni 100] [--min-click-calo 20]

Scrive nella stessa cartella tre CSV:
- cannibalizzazioni.csv: query su cui due pagine si dividono click o impressioni;
- pagine_in_calo.csv: pagine che hanno perso click rispetto agli stessi mesi
  dell'anno prima;
- opportunita.csv: query con molte impressioni ma posizione tra 5 e 20, dove
  un contenuto migliore o nuovo può guadagnare click.

Poi stampa un riepilogo in Markdown, da cui la skill scrive il report.
Lo script trova i casi, ma non decide: intento e rimedio li valuta il consulente.
"""
import argparse
import csv
import datetime as dt
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Parole che aprono una domanda, nelle lingue più comuni dei clienti
RE_DOMANDA = re.compile(
    r"^(come|cosa|che cos|quanto|quanti|quale|quali|perch|quando|dove|chi|"
    r"how|what|which|why|when|where|who|is|are|can|does|do|"
    r"wie|was|welche|warum|comment|quel|quelle|pourquoi|como|qu[eé]|cu[aá]nto|por qu[eé])\b",
    re.IGNORECASE,
)


def leggi(percorso):
    with open(percorso, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            r["click"] = int(r["click"])
            r["impressioni"] = int(r["impressioni"])
            r["posizione"] = float(r["posizione"])
            yield r


def scrivi(percorso, righe, colonne):
    with open(percorso, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colonne)
        w.writeheader()
        w.writerows(righe)


def e_brand(query, brand):
    return any(b in query for b in brand)


# --- Cannibalizzazioni -----------------------------------------------------

def cannibalizzazioni(cartella, brand, quota_min, min_imp):
    per_query = defaultdict(list)
    for r in leggi(cartella / "query_pagina.csv"):
        per_query[r["query"]].append(r)

    # Pagina più forte di ogni query, mese per mese
    prime_mensili = defaultdict(dict)
    if (cartella / "query_pagina_mensile.csv").exists():
        migliori = {}
        for r in leggi(cartella / "query_pagina_mensile.csv"):
            k = (r["query"], r["mese"])
            if k not in migliori or (r["click"], r["impressioni"]) > (migliori[k]["click"], migliori[k]["impressioni"]):
                migliori[k] = r
        for (q, mese), r in migliori.items():
            prime_mensili[q][mese] = r["pagina"]

    risultati = []
    for q, pagine in per_query.items():
        tot_imp = sum(p["impressioni"] for p in pagine)
        if len(pagine) < 2 or tot_imp < min_imp:
            continue
        tot_click = sum(p["click"] for p in pagine)
        metrica = "click" if tot_click >= 10 else "impressioni"
        totale = tot_click if metrica == "click" else tot_imp
        altra_metrica = "impressioni" if metrica == "click" else "click"
        pagine.sort(key=lambda p: (-p[metrica], -p[altra_metrica]))
        prima = pagine[0]
        mesi = prime_mensili.get(q, {})
        sequenza = [mesi[m] for m in sorted(mesi)]
        cambi = sum(1 for a, b in zip(sequenza, sequenza[1:]) if a != b)
        for altra in pagine[1:]:
            quota = altra[metrica] / totale if totale else 0
            if quota < quota_min:
                continue
            risultati.append({
                "query": q,
                "brand": "sì" if e_brand(q, brand) else "no",
                "domanda": "sì" if RE_DOMANDA.match(q) else "no",
                "click_totali": tot_click,
                "impressioni_totali": tot_imp,
                "metrica": metrica,
                "pagina_principale": prima["pagina"],
                "quota_principale": round(prima[metrica] / totale, 3) if totale else 0,
                "posizione_principale": prima["posizione"],
                "pagina_concorrente": altra["pagina"],
                "quota_concorrente": round(quota, 3),
                "posizione_concorrente": altra["posizione"],
                "stessa_lingua": "sì" if prima.get("lingua") == altra.get("lingua") else "no",
                "pagine_sulla_query": len(pagine),
                "mesi_con_dati": len(sequenza),
                "mesi_concorrente_prima": sum(1 for p in sequenza if p == altra["pagina"]),
                "cambi_di_pagina": cambi,
            })
    # Prima i casi che pesano di più: tanto traffico conteso e non di brand
    risultati.sort(key=lambda r: (r["brand"] == "sì", -r["impressioni_totali"] * r["quota_concorrente"]))
    return risultati


# --- Pagine in calo --------------------------------------------------------

def mesi_completi(inizio, fine):
    mesi = []
    m = inizio.replace(day=1)
    if m < inizio:
        m = (m.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    while True:
        prossimo = (m.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        if prossimo - dt.timedelta(days=1) > fine:
            return mesi
        mesi.append(m.strftime("%Y-%m"))
        m = prossimo


def pagine_in_calo(cartella, meta, min_click):
    percorso = cartella / "pagine_mensile.csv"
    completi = mesi_completi(dt.date.fromisoformat(meta["inizio"]), dt.date.fromisoformat(meta["fine"]))
    recenti = completi[-3:]
    prima = [f"{int(m[:4]) - 1}{m[4:]}" for m in recenti]
    if not percorso.exists() or len(recenti) < 3 or not set(prima) <= set(completi):
        return [], recenti, prima

    dati = defaultdict(lambda: {"cr": 0, "ca": 0, "ir": 0, "ia": 0, "lingua": ""})
    for r in leggi(percorso):
        d = dati[r["pagina"]]
        d["lingua"] = r.get("lingua", "")
        if r["mese"] in recenti:
            d["cr"] += r["click"]
            d["ir"] += r["impressioni"]
        elif r["mese"] in prima:
            d["ca"] += r["click"]
            d["ia"] += r["impressioni"]

    risultati = []
    for pagina, d in dati.items():
        if d["ca"] < min_click:
            continue
        var = (d["cr"] - d["ca"]) / d["ca"]
        if var > -0.3:
            continue
        risultati.append({
            "pagina": pagina,
            "lingua": d["lingua"],
            "click_recenti": d["cr"],
            "click_anno_prima": d["ca"],
            "variazione_click": round(var, 3),
            "impressioni_recenti": d["ir"],
            "impressioni_anno_prima": d["ia"],
        })
    risultati.sort(key=lambda r: r["click_recenti"] - r["click_anno_prima"])
    return risultati, recenti, prima


# --- Opportunità -----------------------------------------------------------

def opportunita(cartella, brand, min_imp):
    pagine_per_query = defaultdict(list)
    for r in leggi(cartella / "query_pagina.csv"):
        pagine_per_query[r["query"]].append(r)

    risultati = []
    for r in leggi(cartella / "query.csv"):
        q = r["query"]
        if r["impressioni"] < min_imp or not 5 <= r["posizione"] <= 20 or e_brand(q, brand):
            continue
        pagine = sorted(pagine_per_query.get(q, []), key=lambda p: -p["impressioni"])
        risultati.append({
            "query": q,
            "domanda": "sì" if RE_DOMANDA.match(q) else "no",
            "impressioni": r["impressioni"],
            "click": r["click"],
            "ctr": r["ctr"],
            "posizione": r["posizione"],
            "pagina_principale": pagine[0]["pagina"] if pagine else "",
            "pagine_sulla_query": len(pagine),
        })
    risultati.sort(key=lambda r: -r["impressioni"])
    return risultati


# --- Riepilogo -------------------------------------------------------------

def tabella(righe, colonne, n):
    if not righe:
        return "Nessun caso.\n"
    out = ["| " + " | ".join(colonne) + " |", "|" + "---|" * len(colonne)]
    for r in righe[:n]:
        out.append("| " + " | ".join(str(r[c]) for c in colonne) + " |")
    if len(righe) > n:
        out.append(f"\n…e altri {len(righe) - n} casi nel CSV.")
    return "\n".join(out) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cartella", help="cartella dell'estrazione, es. raw/gsc/2026-10-26")
    p.add_argument("--brand", default="", help="nomi del brand separati da virgola, per isolare le query di brand")
    p.add_argument("--quota", type=float, default=0.2, help="quota minima della pagina concorrente (default 0.2)")
    p.add_argument("--min-impressioni", type=int, default=100, help="impressioni minime della query nel periodo")
    p.add_argument("--min-click-calo", type=int, default=20, help="click minimi dell'anno prima per le pagine in calo")
    a = p.parse_args()

    cartella = Path(a.cartella)
    if not (cartella / "metadati.json").exists():
        sys.exit(f"{cartella} non sembra un'estrazione di estrai_gsc.py: manca metadati.json.")
    meta = json.loads((cartella / "metadati.json").read_text(encoding="utf-8"))
    brand = [b.strip().lower() for b in a.brand.split(",") if b.strip()]

    cann = cannibalizzazioni(cartella, brand, a.quota, a.min_impressioni)
    scrivi(cartella / "cannibalizzazioni.csv", cann, list(cann[0]) if cann else ["query"])
    calo, recenti, prima = pagine_in_calo(cartella, meta, a.min_click_calo)
    scrivi(cartella / "pagine_in_calo.csv", calo, list(calo[0]) if calo else ["pagina"])
    opp = opportunita(cartella, brand, a.min_impressioni)
    scrivi(cartella / "opportunita.csv", opp, list(opp[0]) if opp else ["query"])

    pagine = sorted(leggi(cartella / "pagine.csv"), key=lambda r: -r["click"])
    tot = meta["totali"]
    print(f"# Riepilogo Search Console: {meta['sito']}\n")
    print(f"Periodo {meta['inizio']} – {meta['fine']}, tipo {meta['tipo']}. "
          f"Click {tot['click']}, impressioni {tot['impressioni']}. "
          f"Quota di click da query anonime: {meta.get('quota_click_query_anonime')}.\n")
    print("## Pagine con più click\n")
    print(tabella(pagine, ["pagina", "lingua", "click", "impressioni", "posizione"], 20))
    print(f"## Cannibalizzazioni ({len(cann)} casi, quota minima {a.quota:.0%})\n")
    print(tabella([c for c in cann if c["brand"] == "no"],
                  ["query", "impressioni_totali", "pagina_principale", "quota_principale",
                   "pagina_concorrente", "quota_concorrente", "stessa_lingua", "cambi_di_pagina"], 25))
    if recenti and prima:
        print(f"## Pagine in calo ({len(calo)}): {', '.join(recenti)} contro {', '.join(prima)}\n")
        print(tabella(calo, ["pagina", "click_recenti", "click_anno_prima", "variazione_click"], 20))
    else:
        print("## Pagine in calo\n\nStorico insufficiente per il confronto anno su anno.\n")
    print(f"## Opportunità ({len(opp)} query con posizione 5-20)\n")
    print(tabella(opp, ["query", "domanda", "impressioni", "click", "posizione", "pagina_principale"], 25))


if __name__ == "__main__":
    main()
