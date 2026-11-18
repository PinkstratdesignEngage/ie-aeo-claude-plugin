#!/usr/bin/env python3
"""Controlli automatici su una knowledge base IE-AEO.

Uso: python3 verifica_kb.py <cartella-repo> [--allinea-fonti]

Esce con codice 1 se trova errori; gli avvisi non bloccano.
Con --allinea-fonti riscrive il campo `fonti` del frontmatter di ogni file
con i codici effettivamente citati nel testo, prima di eseguire i controlli.
"""
import re
import subprocess
import sys
from pathlib import Path

STATI = {"bozza", "da-validare", "validato"}
# I file in contenuti/ hanno il ciclo di vita dei contenuti
STATI_CONTENUTI = {"brief", "bozza", "approvato", "pubblicato"}
CAMPI = ("titolo", "stato", "ultimo_aggiornamento", "fonti")
# File che possono nominare _privato perché ne spiegano l'esclusione
PUO_CITARE_PRIVATO = {"CLAUDE.md", "README.md", ".gitignore"}
# File di root che spiegano le convenzioni: contengono citazioni e marcatori d'esempio
DOC_CONVENZIONI = {Path("README.md"), Path("CLAUDE.md")}

# Una citazione è una parentesi quadra che inizia con un codice fonte:
# [S01], [M01 00:13], [S31 slug-pagina], [S01, D02], [D18 sl. 3, 24]
# Prefissi: sito, Drive, riunioni, contenuti, esterne, risposte; Search Console, Semrush o Ahrefs, HubSpot AEO, GA4
PREFISSI = "SDMCERGXHA"
RE_CITAZIONE = re.compile(rf"\[([{PREFISSI}]\d{{2,3}}\b[^\]]*)\]")
RE_CODICE = re.compile(rf"\b[{PREFISSI}]\d{{2,3}}\b")
RE_CODICE_REGISTRO = re.compile(rf"^\|\s*`?([{PREFISSI}]\d{{2,3}})`?\s*\|", re.M)
RE_LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def file_md(root):
    for p in sorted(root.rglob("*.md")):
        rel = p.relative_to(root)
        if rel.parts[0] in ("_privato", ".git", "raw"):
            continue
        yield p, rel


def leggi_frontmatter(testo):
    if not testo.startswith("---\n"):
        return None
    fine = testo.find("\n---", 4)
    if fine == -1:
        return None
    campi = {}
    for riga in testo[4:fine].splitlines():
        if ":" in riga:
            k, v = riga.split(":", 1)
            campi[k.strip()] = v.strip()
    return campi


def codici_citati(corpo):
    return {c for gruppo in RE_CITAZIONE.findall(corpo) for c in RE_CODICE.findall(gruppo)}


def ordina_codici(codici):
    return sorted(codici, key=lambda c: (PREFISSI.index(c[0]), int(c[1:])))


def allinea_fonti(root):
    """Riscrive `fonti:` nel frontmatter con i codici citati nel corpo."""
    modificati = []
    for p, rel in file_md(root):
        if rel in DOC_CONVENZIONI or rel.parts[0] in ("fonti", "contenuti"):
            continue
        testo = p.read_text(encoding="utf-8")
        if leggi_frontmatter(testo) is None:
            continue
        fine = testo.find("\n---", 4)
        testa, corpo = testo[:fine], testo[fine:]
        nuova = "fonti: [" + ", ".join(ordina_codici(codici_citati(corpo))) + "]"
        testa2 = re.sub(r"^fonti:.*$", nuova, testa, count=1, flags=re.M)
        if testa2 != testa:
            p.write_text(testa2 + corpo, encoding="utf-8")
            modificati.append(str(rel))
    return modificati


def main():
    argomenti = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(argomenti) != 1:
        print(__doc__)
        sys.exit(2)
    root = Path(argomenti[0]).expanduser().resolve()
    errori, avvisi = [], []

    if "--allinea-fonti" in sys.argv:
        for nome in allinea_fonti(root):
            print(f"fonti allineate: {nome}")

    registro = root / "fonti" / "registro-fonti.md"
    codici_registrati = set()
    if registro.exists():
        codici_registrati = set(RE_CODICE_REGISTRO.findall(registro.read_text(encoding="utf-8")))
    else:
        errori.append("manca fonti/registro-fonti.md")

    gitignore = root / ".gitignore"
    if not gitignore.exists() or "_privato" not in gitignore.read_text(encoding="utf-8"):
        errori.append(".gitignore non esclude _privato/")

    # _privato non deve essere tracciato da git
    try:
        tracciati = subprocess.run(
            ["git", "-C", str(root), "ls-files", "_privato"],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        if tracciati:
            errori.append(f"git traccia file in _privato/: {tracciati.splitlines()[:3]}")
    except FileNotFoundError:
        avvisi.append("git non disponibile: controllo su _privato/ saltato")

    da_validare = {}
    citazioni_usate = set()
    for p, rel in file_md(root):
        testo = p.read_text(encoding="utf-8")
        nome = str(rel)

        if rel.name != "README.md" and rel.name != "CLAUDE.md":
            fm = leggi_frontmatter(testo)
            if fm is None:
                errori.append(f"{nome}: frontmatter mancante")
            else:
                for c in CAMPI:
                    if c not in fm:
                        errori.append(f"{nome}: frontmatter senza '{c}'")
                ammessi = STATI_CONTENUTI if rel.parts[0] == "contenuti" else STATI
                if fm.get("stato") and fm["stato"] not in ammessi:
                    errori.append(f"{nome}: stato '{fm['stato']}' non valido")

        if "{{" in testo:
            errori.append(f"{nome}: segnaposto del template non sostituito")

        if "_privato" in testo and rel.name not in PUO_CITARE_PRIVATO:
            errori.append(f"{nome}: cita _privato/")

        if rel in DOC_CONVENZIONI:
            corpo = ""
        else:
            corpo = testo.split("\n---", 1)[-1] if testo.startswith("---") else testo
        usati = codici_citati(corpo)
        citazioni_usate |= usati
        if rel.parts[0] != "fonti":
            for c in sorted(usati - codici_registrati):
                errori.append(f"{nome}: cita [{c}] che non è nel registro fonti")
            fm = leggi_frontmatter(testo) or {}
            dichiarate = set(RE_CODICE.findall(fm.get("fonti", "")))
            mancanti = sorted(usati - dichiarate)
            if mancanti and rel.name != "README.md":
                avvisi.append(f"{nome}: fonti citate nel testo ma non nel frontmatter: {', '.join(mancanti)}")

        for link in RE_LINK.findall(testo):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            if not (p.parent / link).exists():
                errori.append(f"{nome}: link rotto -> {link}")

        n = corpo.count("[DA VALIDARE")
        if n:
            da_validare[nome] = n

        contenuto = corpo.strip()
        if (
            rel.parts[0] in ("01-azienda", "02-audience", "03-offerta", "04-brand-voice", "05-content-pillars")
            and rel.name != "README.md"
            and len(contenuto) > 400
            and not usati
        ):
            avvisi.append(f"{nome}: nessuna citazione di fonte")

    for c in sorted(codici_registrati - citazioni_usate):
        avvisi.append(f"fonte {c} registrata ma mai citata")

    print(f"Knowledge base: {root}")
    print(f"\nErrori: {len(errori)}")
    for e in errori:
        print(f"  ✗ {e}")
    print(f"\nAvvisi: {len(avvisi)}")
    for a in avvisi:
        print(f"  ! {a}")
    print(f"\n[DA VALIDARE] totali: {sum(da_validare.values())}")
    for nome, n in sorted(da_validare.items(), key=lambda x: -x[1]):
        print(f"  {n:3d}  {nome}")

    sys.exit(1 if errori else 0)


if __name__ == "__main__":
    main()
