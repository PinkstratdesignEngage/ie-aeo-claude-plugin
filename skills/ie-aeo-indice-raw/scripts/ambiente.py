#!/usr/bin/env python3
"""Prepara l'ambiente Python della skill ie-aeo-indice-raw in ~/.cache/ie-aeo-indice/.

Gira con il python3 di sistema (anche 3.9). Usa uv per avere Python 3.12 senza Homebrew:
se uv non c'è, lo installa in un ambiente di appoggio dentro la stessa cartella.

    python3 ambiente.py                 ambiente completo: costruire l'indice e ricerca ibrida (~4 GB)
    python3 ambiente.py --solo-ricerca  ambiente leggero: scaricare l'indice e cercare per parola (~0,5 GB)
    python3 ambiente.py --verifica      dice cosa c'è, senza installare nulla

Tutto sta in ~/.cache/ie-aeo-indice/ (Python, librerie, modelli): per toglierlo basta cancellare la cartella.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

BASE = Path.home() / ".cache" / "ie-aeo-indice"
VENV = BASE / "venv"
PYTHON = VENV / "bin" / "python"
QUI = Path(__file__).resolve().parent
MODELLO = "BAAI/bge-m3"
REVISIONE_MODELLO = "5617a9f61b028005a4858fdac845db406aefb181"
FILE_MODELLO = ["*.json", "pytorch_model.bin", "sentencepiece.bpe.model", "1_Pooling/*"]
SPAZIO_GB = {"completo": 6, "ricerca": 1}


def env_uv():
    return {**os.environ, "UV_CACHE_DIR": str(BASE / "cache-uv"), "UV_PYTHON_INSTALL_DIR": str(BASE / "python"),
            "HF_HOME": str(BASE / "modelli")}


def esegui(cmd, **kw):
    print("$ " + " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, env=env_uv(), **kw)


def togli_residui():
    """Toglie ciò che un'installazione interrotta può lasciare e che blocca la successiva:
    collegamenti rotti e cartelle vuote al posto dell'ambiente o dei modelli."""
    for p in (VENV, BASE / "modelli"):
        if p.is_symlink() and not p.exists():
            print(f"Tolgo il collegamento rotto {p} -> {os.readlink(p)}", flush=True)
            p.unlink()
        elif p.is_dir() and not p.is_symlink() and not any(p.iterdir()):
            p.rmdir()
    if VENV.exists() and not PYTHON.exists():
        sys.exit(f"{VENV} esiste ma non contiene Python: è un'installazione a metà. "
                 "Cancellala e rilancia lo script.")


def uv():
    trovato = shutil.which("uv")
    if trovato:
        return trovato
    appoggio = BASE / "uv-boot"
    if not (appoggio / "bin" / "uv").exists():
        esegui([sys.executable, "-m", "venv", appoggio])
        esegui([appoggio / "bin" / "pip", "install", "-q", "uv"])
    return str(appoggio / "bin" / "uv")


def stato():
    info = {"cartella": str(BASE), "ambiente": PYTHON.exists(), "tipo": None, "modello": False}
    if PYTHON.exists():
        r = subprocess.run([str(PYTHON), "-c", "import importlib.util as u; "
                            "print(u.find_spec('lancedb') is not None, u.find_spec('docling') is not None)"],
                           capture_output=True, text=True)
        lance, docling = (r.stdout.split() + ["False", "False"])[:2]
        info["tipo"] = "completo" if docling == "True" else "ricerca" if lance == "True" else "incompleto"
    snap = BASE / "modelli" / "hub" / "models--BAAI--bge-m3" / "snapshots" / REVISIONE_MODELLO / "pytorch_model.bin"
    info["modello"] = snap.exists()
    if BASE.exists():
        r = subprocess.run(["du", "-sh", str(BASE)], capture_output=True, text=True)
        info["occupato"] = r.stdout.split("\t")[0] if r.returncode == 0 else None
    info["libero_gb"] = round(shutil.disk_usage(Path.home()).free / 1e9, 1)
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--solo-ricerca", action="store_true", help="solo download e ricerca per parola")
    parser.add_argument("--verifica", action="store_true", help="mostra lo stato senza installare")
    parser.add_argument("--forza", action="store_true", help="installa anche con poco spazio libero")
    args = parser.parse_args()

    if args.verifica:
        print(json.dumps(stato(), ensure_ascii=False, indent=1))
        return

    tipo = "ricerca" if args.solo_ricerca else "completo"
    libero = shutil.disk_usage(Path.home()).free / 1e9
    if libero < SPAZIO_GB[tipo] and not args.forza:
        sys.exit(f"Spazio libero {libero:.1f} GB: l'ambiente {tipo} ne richiede circa {SPAZIO_GB[tipo]}. "
                 "Libera spazio o rilancia con --forza.")

    BASE.mkdir(parents=True, exist_ok=True)
    togli_residui()
    u = uv()
    if not PYTHON.exists():
        esegui([u, "venv", "-q", "-p", "3.12", VENV])
    requisiti = QUI / ("requirements-ricerca.txt" if args.solo_ricerca else "requirements.txt")
    esegui([u, "pip", "install", "-q", "-p", PYTHON, "-r", requisiti])
    if not args.solo_ricerca:
        esegui([PYTHON, "-c",
                "from huggingface_hub import snapshot_download as s; "
                f"s('{MODELLO}', revision='{REVISIONE_MODELLO}', allow_patterns={FILE_MODELLO!r})"])
    esegui([u, "cache", "clean", "-q"])  # i pacchetti scaricati sono già installati: la cache è solo spazio
    print(json.dumps(stato(), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
