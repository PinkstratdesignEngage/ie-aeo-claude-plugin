#!/usr/bin/env python3
"""Controlla che le FAQ di un contenuto e lo schema FAQPage siano identici.

Uso: python3 verifica_faq_schema.py <file-contenuto.md>

Il file deve avere una sezione "## FAQ" (o "## Domande frequenti", "## Frequently asked
questions") con una domanda per ogni "### " seguita
dalla risposta, e un blocco ```json con lo schema (anche dentro un @graph).
Esce con codice 1 se domande o risposte non coincidono o se il JSON non è valido.
"""
import json
import re
import sys


def normalizza(t):
    t = re.sub(r"[*_`]", "", t)              # markdown inline
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)  # link markdown -> testo
    return re.sub(r"\s+", " ", t).strip()


def faq_dal_testo(testo):
    m = re.search(r"^## (?:FAQ|Domande frequenti|Frequently asked questions).*?$(.*?)(?=^## |\Z)", testo, re.M | re.S | re.I)
    if not m:
        return []
    blocchi = re.split(r"^### +", m.group(1), flags=re.M)[1:]
    out = []
    for b in blocchi:
        righe = b.strip().split("\n", 1)
        out.append((normalizza(righe[0]), normalizza(righe[1] if len(righe) > 1 else "")))
    return out


def faq_dallo_schema(testo):
    for blocco in re.findall(r"```json\s*(.*?)```", testo, re.S):
        try:
            dati = json.loads(blocco)
        except json.JSONDecodeError as e:
            print(f"✗ JSON non valido: {e}")
            sys.exit(1)
        nodi = dati.get("@graph", [dati]) if isinstance(dati, dict) else dati
        for n in nodi:
            if n.get("@type") == "FAQPage":
                return [(normalizza(q["name"]), normalizza(q["acceptedAnswer"]["text"])) for q in n.get("mainEntity", [])]
    return None


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    testo = open(sys.argv[1], encoding="utf-8").read()
    pagina, schema = faq_dal_testo(testo), faq_dallo_schema(testo)
    if not pagina:
        print("✗ Nessuna sezione '## FAQ' o '## Domande frequenti' con domande '### ' trovata")
        sys.exit(1)
    if schema is None:
        print("✗ Nessuno schema FAQPage nei blocchi json")
        sys.exit(1)
    errori = 0
    if len(pagina) != len(schema):
        print(f"✗ {len(pagina)} FAQ nel testo, {len(schema)} nello schema")
        errori += 1
    for i, ((qp, rp), (qs, rs)) in enumerate(zip(pagina, schema), 1):
        if qp != qs:
            print(f"✗ FAQ {i}: domanda diversa\n  testo:  {qp}\n  schema: {qs}")
            errori += 1
        if rp != rs:
            print(f"✗ FAQ {i}: risposta diversa")
            errori += 1
    print("✓ FAQ e schema coincidono" if not errori else f"{errori} differenze")
    sys.exit(1 if errori else 0)


if __name__ == "__main__":
    main()
