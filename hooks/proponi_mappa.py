#!/usr/bin/env python3
"""Hook Stop: a fine turno, se la knowledge base è cambiata, fa chiedere se rigenerare la mappa.

Agisce solo nei repo dei clienti con la mappa (analisi/knowledge-graph/config.json). Scatta
quando ci sono file Markdown della knowledge base cambiati dopo l'ultima mappa (vedi
file_cambiati in controlla_aggiornamenti.py) e tra questi ce n'è almeno uno che in questa
sessione non è ancora stato segnalato. Così chiede una volta per gruppo di modifiche, non a
ogni turno. Lo script non rigenera niente: chiede a Claude di domandarlo all'utente.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from controlla_aggiornamenti import file_cambiati  # noqa: E402


def main():
    try:
        evento = json.load(sys.stdin)
    except ValueError:
        evento = {}
    if evento.get("stop_hook_active"):
        return  # Claude sta già rispondendo a questo promemoria
    repo = Path(os.environ.get("CLAUDE_PROJECT_DIR") or evento.get("cwd") or os.getcwd())
    cambiati = file_cambiati(repo)
    if not cambiati:
        return

    sessione = "".join(c for c in str(evento.get("session_id", "senza-id")) if c.isalnum() or c == "-")
    memoria = Path(tempfile.gettempdir()) / f"ie-aeo-mappa-{sessione}.json"
    try:
        segnalati = set(json.loads(memoria.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        segnalati = set()
    nuovi = [f for f in cambiati if f not in segnalati]
    if not nuovi:
        return
    memoria.write_text(json.dumps(sorted(segnalati | set(cambiati))), encoding="utf-8")

    elenco = ", ".join(cambiati[:5]) + (" e altri" if len(cambiati) > 5 else "")
    print(json.dumps({
        "decision": "block",
        "reason": (
            f"[Promemoria IE-AEO] Sono cambiati {len(cambiati)} file Markdown della knowledge base dopo "
            f"l'ultima mappa ({elenco}): la mappa e la sua chat rispondono ancora sulla versione vecchia. "
            "Chiedi all'utente, in una riga e alla fine della tua risposta, se vuole rigenerarla e "
            "ripubblicarla allo stesso link con la skill ie-aeo-knowledgegraph. Non farlo senza il suo ok. "
            "Se in questa sessione ha già detto di no, non chiedere di nuovo."
        ),
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # un promemoria non deve mai bloccare la sessione
