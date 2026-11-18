#!/usr/bin/env python3
"""Genera raw/indice.md: l'elenco di tutti i materiali nella cartella raw/ della knowledge base.

Uso: python3 indice_raw.py <cartella-repo>

Convenzioni lette dai nomi dei file:
- "-analizzato" prima dell'estensione = materiale analizzato e usato nella knowledge base;
- ".link.md" = segnaposto per un materiale che non sta nel repo (troppo grande, video, riservato).
"""
import sys
from pathlib import Path

root = Path(sys.argv[1]).expanduser().resolve() / "raw"
righe, tot, analizzati, link, peso = [], 0, 0, 0, 0
for p in sorted(root.rglob("*")):
    if not p.is_file() or p.name in ("README.md", "indice.md") or p.name.startswith("."):
        continue
    rel = p.relative_to(root)
    nome = p.name
    is_link = nome.endswith(".link.md")
    base = nome[: -len(".link.md")] if is_link else nome
    stem = base.rsplit(".", 1)[0] if "." in base else base
    is_an = stem.endswith("-analizzato")
    size = p.stat().st_size
    tot += 1; analizzati += is_an; link += is_link; peso += 0 if is_link else size
    dim = "—" if is_link else (f"{size/1_048_576:.1f} MB" if size > 1_048_576 else f"{size/1024:.0f} KB")
    cartella = str(rel.parent)
    righe.append(f"| {cartella} | [{nome}]({str(rel).replace(' ', '%20')}) | {'sì' if is_an else 'no'} | {'segnaposto' if is_link else 'file'} | {dim} |")

out = [
    "# Indice dei materiali in raw/",
    "",
    "Generato automaticamente con `indice_raw.py`: non modificarlo a mano.",
    "",
    f"- Materiali: **{tot}**, di cui analizzati **{analizzati}** e non analizzati **{tot - analizzati}**",
    f"- Segnaposto (materiali che restano fuori dal repo): **{link}**",
    f"- Peso dei file nel repo: **{peso/1_048_576:.0f} MB**",
    "",
    "| Cartella | File | Analizzato | Tipo | Dimensione |",
    "|---|---|---|---|---|",
    *righe,
    "",
]
(root / "indice.md").write_text("\n".join(out), encoding="utf-8")
print(f"{tot} materiali, {analizzati} analizzati, {link} segnaposto, {peso/1_048_576:.0f} MB")
