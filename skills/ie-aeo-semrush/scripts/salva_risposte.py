#!/usr/bin/env python3
"""Salva in raw/semrush/<data>/originali/ le risposte del connettore Semrush, così come sono arrivate.

Uso, dalla radice del repo del cliente:
    python3 -I salva_risposte.py raw/semrush/<AAAA-MM-GG> [--dal 2026-10-27T00:00] [--sessione <file.jsonl>]

Le risposte di execute_report arrivano nella conversazione, non su disco: questo script le
legge dal registro della sessione di Claude Code (~/.claude/projects/<progetto>/<sessione>.jsonl,
di default il più recente del progetto), così nessun dato passa per una trascrizione a mano.

Scrive:
- risposte.jsonl: una riga per chiamata riuscita, con report, parametri, metadati e risposta;
- posizioni-<db>.csv, competitor-<db>.csv, gap-<db>.csv: il CSV restituito dal connettore,
  con le pagine dello stesso report e database unite sotto un'unica intestazione;
- crediti.json: crediti usati per chiamata e in totale, da metadata.usage.api_units;
- site-audit-problemi.json, se ci sono risposte di meta_issues e issue_details: una riga
  {url, issue, type} per pagina e problema. La gravità segue la numerazione dei problemi di
  Semrush: id sotto 100 errore, da 101 a 199 avviso, da 200 nota (sulla prima estrazione i
  totali coincidono con quelli del report info, salvo il blocco della scansione, id 4).
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Report dell'account Semrush, non del cliente: non si salvano nel repo del cliente
RISERVATI = {"list_projects", "get_project"}
PREFISSI = {"resource_organic": "posizioni", "domain_organic_organic": "competitor", "domain_domains": "gap"}


def registro_predefinito():
    progetto = re.sub(r"[^A-Za-z0-9]", "-", str(Path.cwd()))
    cartella = Path.home() / ".claude" / "projects" / progetto
    file = sorted(cartella.glob("*.jsonl"), key=lambda f: f.stat().st_mtime)
    if not file:
        sys.exit(f"Nessun registro di sessione in {cartella}: indica il file con --sessione.")
    return file[-1]


def testo(contenuto):
    if isinstance(contenuto, str):
        return contenuto
    return "".join(x.get("text", "") for x in contenuto if isinstance(x, dict))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cartella")
    p.add_argument("--dal", default="", help="considera solo le chiamate da questo istante (ISO, ora UTC del registro)")
    p.add_argument("--sessione", help="file .jsonl del registro di sessione")
    a = p.parse_args()

    registro = Path(a.sessione) if a.sessione else registro_predefinito()
    chiamate, risultati = {}, {}
    for riga in open(registro, encoding="utf-8"):
        try:
            d = json.loads(riga)
        except ValueError:
            continue
        if a.dal and d.get("timestamp", "") < a.dal:
            continue
        contenuto = (d.get("message") or {}).get("content")
        if not isinstance(contenuto, list):
            continue
        for b in contenuto:
            if b.get("type") == "tool_use" and b.get("name", "").endswith("__execute_report"):
                chiamate[b["id"]] = (b["input"], d.get("timestamp", ""))
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in chiamate and not b.get("is_error"):
                risultati[b["tool_use_id"]] = testo(b.get("content"))

    uscita = Path(a.cartella) / "originali"
    uscita.mkdir(parents=True, exist_ok=True)
    pagine = defaultdict(list)
    titoli, problemi = {}, defaultdict(set)
    crediti, totale = [], 0
    with open(uscita / "risposte.jsonl", "w", encoding="utf-8") as f:
        for uid, (inp, quando) in chiamate.items():
            if uid not in risultati:
                continue
            try:
                risposta = json.loads(risultati[uid])
            except ValueError:
                continue  # errore o risposta non JSON: non è un dato
            usati = ((risposta.get("metadata") or {}).get("usage") or {}).get("api_units", 0)
            totale += usati
            report, params = inp["report"], inp.get("params", {})
            crediti.append({"report": report, "database": params.get("database", ""), "quando": quando,
                            "righe": str(risposta.get("data", "")).count("\n") - 1 if isinstance(risposta.get("data"), str) else None,
                            "crediti": usati})
            if report in RISERVATI:
                continue  # l'elenco dei progetti contiene gli altri clienti: nel repo resta solo il costo
            f.write(json.dumps({"report": report, "params": params, "quando": quando, "risposta": risposta},
                               ensure_ascii=False) + "\n")
            if report == "meta_issues" and isinstance(risposta.get("data"), list):
                titoli.update({m["id"]: m["title"] for m in risposta["data"] if "id" in m})
            if report == "issue_details" and isinstance(risposta.get("data"), dict):
                for r in risposta["data"].get("data", []):
                    problemi[int(risposta["data"].get("issue_id", params.get("issueid", 0)))].add(r.get("source_url", ""))
            if report in PREFISSI and isinstance(risposta.get("data"), str):
                pagine[(PREFISSI[report], params.get("database", "xx"))].append(risposta["data"])

    for (prefisso, db), testi in pagine.items():
        righe, intestazione = [], None
        for t in testi:
            linee = [l for l in t.splitlines() if l.strip()]
            if not linee:
                continue
            intestazione = intestazione or linee[0]
            righe.extend(linee[1:])
        (uscita / f"{prefisso}-{db}.csv").write_text("\n".join([intestazione] + righe) + "\n", encoding="utf-8")
        print(f"  {prefisso}-{db}.csv: {len(righe)} righe da {len(testi)} chiamate")
    if problemi:
        gravita = lambda i: "error" if i < 100 else "warning" if i < 200 else "notice"
        righe = [{"url": u, "issue": titoli.get(i, f"issue {i}"), "type": gravita(i), "issue_id": i}
                 for i, urls in sorted(problemi.items()) for u in sorted(urls) if u]
        (uscita / "site-audit-problemi.json").write_text(json.dumps(righe, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"  site-audit-problemi.json: {len(righe)} righe per {len(problemi)} problemi")
    (uscita / "crediti.json").write_text(json.dumps({"totale": totale, "chiamate": crediti}, indent=2,
                                                    ensure_ascii=False), encoding="utf-8")
    print(f"  crediti.json: {totale} crediti in {len(crediti)} chiamate (registro {registro.name})")


if __name__ == "__main__":
    main()
