#!/usr/bin/env python3
"""Salva in raw/hubspot-aeo/<data>/ le risposte del connettore HubSpot AEO, così come sono arrivate.

Uso, dalla radice del repo del cliente:
    python3 -I salva_hubspot.py raw/hubspot-aeo/<AAAA-MM-GG> --dal <AAAA-MM-GG> [--sessione <file.jsonl>]

Le risposte del connettore arrivano nella conversazione, non su disco: lo script le legge dal
registro della sessione di Claude Code (~/.claude/projects/<progetto>/<sessione>.jsonl, di
default il più recente del progetto), così nessun dato passa per una trascrizione a mano.

Considera solo le letture: get_aeo_metrics, manage_aeo_prompts con DETAIL o RESPONSES,
manage_aeo_recommendations con LIST o DETAIL. Le chiamate rifiutate o in errore si saltano.

Scrive nella cartella:
- risposte.jsonl: una riga per chiamata, con strumento, parametri, istante e risposta;
- metriche.json: l'ultima risposta di get_aeo_metrics per ogni combinazione di sezioni
  richieste, in un oggetto {"<SEZIONI>": risposta};
- prompt/<id>.json: il dettaglio di ogni prompt letto (DETAIL), con gli URL citati;
- raccomandazioni.json: le pagine di raccomandazioni (LIST) unite in un elenco di risposte;
- indice.json: cosa è stato salvato, con il periodo richiesto.
"""
import argparse
import json
import re
import sys
from pathlib import Path

LETTURE = {"get_aeo_metrics": None, "manage_aeo_prompts": {"DETAIL", "RESPONSES"},
           "manage_aeo_recommendations": {"LIST", "DETAIL"}}


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
    p.add_argument("--dal", required=True, help="considera solo le chiamate da questo istante (ISO, ora UTC del registro)")
    p.add_argument("--sessione", help="file .jsonl del registro di sessione")
    a = p.parse_args()

    registro = Path(a.sessione) if a.sessione else registro_predefinito()
    chiamate, risultati = {}, {}
    for riga in open(registro, encoding="utf-8"):
        try:
            d = json.loads(riga)
        except ValueError:
            continue
        if d.get("timestamp", "") < a.dal:
            continue
        contenuto = (d.get("message") or {}).get("content")
        if not isinstance(contenuto, list):
            continue
        for b in contenuto:
            if b.get("type") == "tool_use":
                strumento = b.get("name", "").rsplit("__", 1)[-1]
                if strumento not in LETTURE:
                    continue
                operazione = ((b.get("input") or {}).get("operation") or {}).get("_operationType")
                if LETTURE[strumento] is not None and operazione not in LETTURE[strumento]:
                    continue  # CREATE, START_ACTION e simili non sono letture
                chiamate[b["id"]] = (strumento, b.get("input") or {}, d.get("timestamp", ""))
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in chiamate and not b.get("is_error"):
                risultati[b["tool_use_id"]] = testo(b.get("content"))

    cartella = Path(a.cartella)
    (cartella / "prompt").mkdir(parents=True, exist_ok=True)
    metriche, raccomandazioni, prompt, periodi = {}, [], [], set()
    with open(cartella / "risposte.jsonl", "w", encoding="utf-8") as f:
        for uid, (strumento, inp, quando) in chiamate.items():
            if uid not in risultati:
                continue
            try:
                risposta = json.loads(risultati[uid])
            except ValueError:
                continue  # messaggio di errore o testo: non è un dato
            f.write(json.dumps({"strumento": strumento, "parametri": inp, "quando": quando, "risposta": risposta},
                               ensure_ascii=False) + "\n")
            if strumento == "get_aeo_metrics":
                sezioni = "+".join(sorted(inp.get("include") or ["SUMMARY", "RUN_STATUS"]))
                if inp.get("promptsCursor"):
                    sezioni += f"@{inp['promptsCursor']}"
                metriche[sezioni] = risposta
                periodi.add((inp.get("startDate", "ultimi 30 giorni"), inp.get("endDate", "oggi")))
            elif strumento == "manage_aeo_prompts":
                op = inp["operation"]
                pid = op.get("promptId", "senza-id")
                nome = f"{pid}.json" if op["_operationType"] == "DETAIL" else f"{pid}-risposte.json"
                (cartella / "prompt" / nome).write_text(json.dumps(risposta, indent=1, ensure_ascii=False), encoding="utf-8")
                prompt.append(nome)
            else:
                raccomandazioni.append({"operazione": inp["operation"]["_operationType"], "risposta": risposta})

    if not (metriche or prompt or raccomandazioni):
        sys.exit(f"Nessuna lettura HubSpot AEO riuscita nel registro {registro.name} dal {a.dal}.")
    (cartella / "metriche.json").write_text(json.dumps(metriche, indent=1, ensure_ascii=False), encoding="utf-8")
    (cartella / "raccomandazioni.json").write_text(json.dumps(raccomandazioni, indent=1, ensure_ascii=False), encoding="utf-8")
    indice = {"registro": registro.name, "dal": a.dal, "periodi": sorted(periodi),
              "metriche": sorted(metriche), "prompt": sorted(prompt), "pagine_raccomandazioni": len(raccomandazioni)}
    (cartella / "indice.json").write_text(json.dumps(indice, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  metriche.json: {len(metriche)} risposte ({', '.join(sorted(metriche))})")
    print(f"  prompt/: {len(prompt)} file")
    print(f"  raccomandazioni.json: {len(raccomandazioni)} risposte")


if __name__ == "__main__":
    main()
