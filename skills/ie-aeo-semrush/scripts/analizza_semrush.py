#!/usr/bin/env python3
"""L'analisi è ora in condivisi/scripts/analizza_ricerche.py, condivisa con la skill ie-aeo-ahrefs.

Semrush e Ahrefs scrivono gli stessi file normalizzati, quindi l'incrocio con Search Console
è lo stesso per entrambi. Questo file resta perché i comandi già scritti continuino a
funzionare: passa gli stessi argomenti allo script condiviso, con --strumento Semrush.

Uso, dalla radice del repo del cliente, invariato:
    python3 -I analizza_semrush.py raw/semrush/<AAAA-MM-GG> --gsc raw/gsc/<AAAA-MM-GG> [--brand "a,b"]
"""
import runpy
import sys
from pathlib import Path

CONDIVISO = Path(__file__).resolve().parents[3] / "condivisi" / "scripts" / "analizza_ricerche.py"

if not CONDIVISO.exists():
    sys.exit(f"Manca lo script condiviso {CONDIVISO}: aggiorna il plugin ie-aeo.")
if "--strumento" not in sys.argv:
    sys.argv += ["--strumento", "Semrush"]
sys.argv[0] = str(CONDIVISO)
runpy.run_path(str(CONDIVISO), run_name="__main__")
