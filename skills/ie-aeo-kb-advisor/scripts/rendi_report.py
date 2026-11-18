#!/usr/bin/env python3
"""Compone la pagina HTML del report dal JSON scritto con la skill.

Uso, dalla radice del repo del cliente:
    python3 -I rendi_report.py analisi/kb-advisor/AAAA-MM-GG.json [--out analisi/kb-advisor/index.html]

Controlla il JSON (campi obbligatori, valori ammessi, rimandi tra cosa manca e piano) e si ferma
con l'elenco degli errori; se è corretto scrive la pagina, da pubblicare come artifact.
"""
import argparse
import json
import sys
from pathlib import Path

MODELLO = Path(__file__).resolve().parent.parent / "assets" / "report.html"
TIPI = {"materiale", "domanda", "fonte", "decisione", "task", "coerenza"}
PRIORITA = {"alta", "media", "bassa"}
ORIZZONTI = {"subito", "questo mese", "prossimi mesi"}
LIVELLI = {"solida", "parziale", "scoperta"}


def controlla(d):
    err = []
    for k in ("cliente", "data", "sintesi", "funziona", "aree", "gap", "piano"):
        if not d.get(k):
            err.append(f"manca '{k}'")
    piano = {p.get("id") for p in d.get("piano", [])}
    gap = {g.get("id") for g in d.get("gap", [])}
    for a in d.get("aree", []):
        if a.get("livello") not in LIVELLI:
            err.append(f"area {a.get('area')}: livello '{a.get('livello')}' non ammesso")
    for g in d.get("gap", []):
        if g.get("tipo") not in TIPI:
            err.append(f"{g.get('id')}: tipo '{g.get('tipo')}' non ammesso")
        for p in g.get("piano", []):
            if p not in piano:
                err.append(f"{g.get('id')} rimanda a {p}, che non è nel piano")
    for p in d.get("piano", []):
        for k in ("id", "azione", "tipo", "chi", "priorita", "orizzonte"):
            if not p.get(k):
                err.append(f"voce {p.get('id', '?')}: manca '{k}'")
        if p.get("tipo") not in TIPI:
            err.append(f"{p.get('id')}: tipo '{p.get('tipo')}' non ammesso")
        if p.get("priorita") not in PRIORITA:
            err.append(f"{p.get('id')}: priorità '{p.get('priorita')}' non ammessa")
        if p.get("orizzonte") not in ORIZZONTI:
            err.append(f"{p.get('id')}: orizzonte '{p.get('orizzonte')}' non ammesso")
        for g in p.get("gap", []):
            if g not in gap:
                err.append(f"{p.get('id')} rimanda a {g}, che non è tra le cose che mancano")
    testo = json.dumps(d, ensure_ascii=False).lower()
    for parola in ("airops", "roadmap"):
        if parola in testo:
            err.append(f"il report contiene '{parola}': non va nelle pagine per i clienti")
    return err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dati")
    ap.add_argument("--out", default="analisi/kb-advisor/index.html")
    a = ap.parse_args()
    d = json.loads(Path(a.dati).read_text(encoding="utf-8"))
    err = controlla(d)
    if err:
        sys.exit("Il JSON del report non va bene:\n- " + "\n- ".join(err))
    titolo = d.get("titolo") or f"Piano della knowledge base {d['cliente']}"
    dati = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
    html = MODELLO.read_text(encoding="utf-8").replace("{{TITOLO}}", titolo.replace("<", "&lt;")).replace("{{DATI}}", dati)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(html, encoding="utf-8")
    print(f"Scritto {a.out}: {len(d['funziona'])} punti che funzionano, {len(d['gap'])} cose che mancano, {len(d['piano'])} azioni.")


if __name__ == "__main__":
    main()
