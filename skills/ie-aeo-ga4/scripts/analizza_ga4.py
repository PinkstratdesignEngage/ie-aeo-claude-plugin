#!/usr/bin/env python3
"""Analizza un'estrazione di GA4 (raw/ga4/<data>/) e stampa i numeri del traffico dagli assistenti AI.

Uso, dalla radice del repo del cliente:
    python3 -I analizza_ga4.py raw/ga4/<data> [--righe 15]

Raggruppa le sorgenti per assistente, calcola sessioni, quota sul totale, coinvolgimento ed eventi
chiave, confronta gli ultimi tre mesi completi con i tre precedenti e con gli stessi mesi dell'anno
prima, ed elenca le pagine di arrivo. Stampa anche le sorgenti riconosciute come AI, da controllare:
l'espressione cerca parole brevi e può prendere sorgenti estranee. Non scrive nulla.
"""
import argparse
import csv
import datetime as dt
import json
import re
from collections import defaultdict
from pathlib import Path

ASSISTENTI = [
    ("ChatGPT", r"chatgpt|openai"), ("Perplexity", r"perplexity"), ("Copilot", r"copilot"),
    ("Gemini", r"gemini|bard"), ("Claude", r"claude|anthropic"), ("DeepSeek", r"deepseek"),
    ("Meta AI", r"meta\.ai"), ("Mistral", r"mistral"), ("Grok", r"grok|x\.ai"),
]


def assistente(sorgente):
    s = sorgente.lower()
    for nome, rx in ASSISTENTI:
        if re.search(rx, s):
            return nome
    return "Altri"


def leggi(f):
    with f.open(newline="", encoding="utf-8") as h:
        return list(csv.DictReader(h))


def n(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def fmt(x):
    return f"{x:,.0f}".replace(",", ".")


def pct(x):
    return "-" if x is None else f"{x * 100:.1f}".replace(".", ",") + "%"


def var(x):
    return "-" if x is None else ("+" if x >= 0 else "") + f"{x * 100:.1f}".replace(".", ",") + "%"


def mesi_indietro(mese, k):
    a, m = int(mese[:4]), int(mese[4:])
    m -= k
    while m <= 0:
        m += 12
        a -= 1
    return f"{a}{m:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cartella")
    ap.add_argument("--righe", type=int, default=15)
    a = ap.parse_args()
    c = Path(a.cartella)
    meta = json.loads((c / "metadati.json").read_text(encoding="utf-8"))
    ai = leggi(c / "ai_mensile.csv")
    canali = leggi(c / "canali_mensile.csv")
    pagine = leggi(c / "ai_pagine.csv")

    tot_mese = defaultdict(float)
    org_mese = defaultdict(float)
    for r in canali:
        tot_mese[r["mese"]] += n(r["sessioni"])
        if r["canale"].lower().startswith("organic search"):
            org_mese[r["mese"]] += n(r["sessioni"])
    ai_mese, ai_ass, ai_ass_mese, sorgenti = defaultdict(float), defaultdict(lambda: defaultdict(float)), defaultdict(lambda: defaultdict(float)), defaultdict(float)
    for r in ai:
        nome = assistente(r["sorgente"])
        ai_mese[r["mese"]] += n(r["sessioni"])
        for k in ("sessioni", "sessioni_coinvolte", "eventi_chiave"):
            ai_ass[nome][k] += n(r[k])
        ai_ass_mese[nome][r["mese"]] += n(r["sessioni"])
        sorgenti[(r["sorgente"], nome)] += n(r["sessioni"])

    fine = dt.date.fromisoformat(meta["periodo"]["fine"])
    ultimo_completo = f"{fine.year}{fine.month:02d}" if (fine + dt.timedelta(days=1)).day == 1 else mesi_indietro(f"{fine.year}{fine.month:02d}", 1)
    ultimi = [mesi_indietro(ultimo_completo, k) for k in range(3)]
    precedenti = [mesi_indietro(ultimo_completo, k) for k in range(3, 6)]
    anno_prima = [mesi_indietro(m, 12) for m in ultimi]

    def somma(d, mesi):
        return sum(d.get(m, 0) for m in mesi)

    print(f"# Traffico dagli assistenti AI: proprietà {meta['proprieta']}\n")
    print(f"Periodo: {meta['periodo']['inizio']} – {meta['periodo']['fine']}. Ultimi tre mesi completi: {', '.join(m[:4] + '-' + m[4:] for m in sorted(ultimi))}.\n")
    tot_ai, tot = sum(ai_mese.values()), sum(tot_mese.values())
    print("## Totali\n")
    print(f"- Sessioni dagli assistenti AI: {fmt(tot_ai)} su {fmt(tot)} ({pct(tot_ai / tot if tot else None)})")
    u, p, y = somma(ai_mese, ultimi), somma(ai_mese, precedenti), somma(ai_mese, anno_prima)
    print(f"- Ultimi tre mesi: {fmt(u)} sessioni AI; tre mesi prima: {fmt(p)}"
          + (f" ({var((u - p) / p)})" if p else "") + f"; stessi mesi dell'anno prima: {fmt(y)}" + (f" ({var((u - y) / y)})" if y else ""))
    uo = somma(org_mese, ultimi)
    org_coinv = sum(n(r["sessioni_coinvolte"]) for r in canali if r["mese"] in ultimi and r["canale"].lower().startswith("organic search"))
    ai_coinv = sum(n(r["sessioni_coinvolte"]) for r in ai if r["mese"] in ultimi)
    print(f"- Ultimi tre mesi, ricerca organica: {fmt(uo)} sessioni; le sessioni AI sono il {pct(u / uo if uo else None)} della ricerca organica")
    print(f"- Coinvolgimento negli ultimi tre mesi: sessioni AI {pct(ai_coinv / u if u else None)}, ricerca organica {pct(org_coinv / uo if uo else None)}")

    print("\n## Per assistente\n")
    print("| Assistente | Sessioni | Quota sulle sessioni AI | Coinvolte | Eventi chiave | Ultimi 3 mesi |")
    print("|---|---|---|---|---|---|")
    for nome, v in sorted(ai_ass.items(), key=lambda x: -x[1]["sessioni"]):
        print(f"| {nome} | {fmt(v['sessioni'])} | {pct(v['sessioni'] / tot_ai if tot_ai else None)} | "
              f"{pct(v['sessioni_coinvolte'] / v['sessioni'] if v['sessioni'] else None)} | {fmt(v['eventi_chiave'])} | {fmt(somma(ai_ass_mese[nome], ultimi))} |")

    print("\n## Mese per mese\n")
    print("| Mese | Sessioni AI | Tutte le sessioni | Quota AI |")
    print("|---|---|---|---|")
    for m in sorted(tot_mese):
        etichetta = f"{m[:4]}-{m[4:]}" + (" (parziale)" if m > ultimo_completo else "")
        print(f"| {etichetta} | {fmt(ai_mese.get(m, 0))} | {fmt(tot_mese[m])} | {pct(ai_mese.get(m, 0) / tot_mese[m] if tot_mese[m] else None)} |")

    print("\n## Pagine di arrivo dagli assistenti AI\n")
    per_pag = defaultdict(lambda: defaultdict(float))
    for r in pagine:
        per_pag[r["pagina"]]["sessioni"] += n(r["sessioni"])
        per_pag[r["pagina"]]["eventi_chiave"] += n(r["eventi_chiave"])
        per_pag[r["pagina"]][assistente(r["sorgente"])] += n(r["sessioni"])
    print("| Pagina | Sessioni | Eventi chiave | Assistente principale |")
    print("|---|---|---|---|")
    for pag, v in sorted(per_pag.items(), key=lambda x: -x[1]["sessioni"])[:a.righe]:
        princ = max((k for k in v if k not in ("sessioni", "eventi_chiave")), key=lambda k: v[k], default="-")
        print(f"| {pag} | {fmt(v['sessioni'])} | {fmt(v['eventi_chiave'])} | {princ} |")

    print("\n## Sorgenti riconosciute come AI (da controllare)\n")
    for (s, nome), v in sorted(sorgenti.items(), key=lambda x: -x[1]):
        print(f"- {s} → {nome}: {fmt(v)} sessioni")


if __name__ == "__main__":
    main()
