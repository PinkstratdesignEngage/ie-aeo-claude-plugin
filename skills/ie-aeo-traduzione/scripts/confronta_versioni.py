#!/usr/bin/env python3
"""Confronta un contenuto master con la sua traduzione e segnala ciò che non torna.

Uso, dalla radice del repo del cliente:
    python3 -I confronta_versioni.py <master.md> <traduzione.md>

Legge la parte pubblicabile dei due file (dal titolo H1 alle sezioni di servizio come
"Metadati per il CMS" o "Schema.org") e controlla che coincidano:
- i numeri, letti con i separatori della lingua di ciascun file (1.500,5 in italiano, 1,500.5 in inglese);
- i nomi scritti in maiuscolo (prodotti, sigle), che di norma non si traducono;
- il numero di sottotitoli H2 e di FAQ;
- i link: quelli che puntano ancora a una pagina nella lingua del master;
- i segnaposto rimasti ([DATO DA FORNIRE], [DA CONFERMARE], [DA VALIDARE]).

Non giudica la qualità della traduzione: trova le differenze meccaniche da controllare.
Esce con codice 1 se ci sono differenze nei numeri o nei nomi.
"""
import re
import sys
from collections import Counter
from pathlib import Path

FINE = ("metadati", "schema.org", "fonti", "note per", "brief", "report prima", "analisi e piano",
        "punti mancanti", "domande aperte che pesano", "cosa migliorare", "cms metadata", "sources",
        "review notes", "translation notes", "note di traduzione", "pubblicazione in hubspot")
SEGNAPOSTO = re.compile(r"\[(DATO DA FORNIRE|DA CONFERMARE|DA VALIDARE|DATA TO BE PROVIDED|TO BE CONFIRMED)[^\]]*\]")


def frontmatter(testo):
    m = re.match(r"---\n(.*?)\n---", testo, re.S)
    fm = {}
    if m:
        for r in m.group(1).splitlines():
            if ":" in r and not r.startswith(" "):
                k, v = r.split(":", 1)
                fm[k.strip()] = v.strip().strip('"')
    return fm


def pubblicabile(testo):
    righe, dentro = [], False
    for r in testo.splitlines():
        if r.startswith("# ") and not dentro:
            dentro = True
        elif dentro and r.startswith("## ") and r[3:].strip().lower().startswith(FINE):
            break
        if dentro:
            righe.append(r)
    return "\n".join(righe)


def numeri(testo, lingua):
    testo = re.sub(r"\]\([^)]*\)", "]", testo)          # niente numeri dagli URL
    testo = re.sub(r"\b(?:R|CO|H|SO|NO)\d+\b", " ", testo)  # sigle come R744, CO2
    out = []
    for t in re.findall(r"(?<![\w.,])\d[\d.,]*\d|(?<![\w.,])\d", testo):
        if lingua.startswith("it"):
            v = t.replace(".", "").replace(",", ".") if re.fullmatch(r"\d{1,3}(\.\d{3})+(,\d+)?|\d+(,\d+)?", t) else t
        else:
            v = t.replace(",", "") if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?|\d+(\.\d+)?", t) else t
        try:
            f = float(v)
            out.append(f"{f:g}")
        except ValueError:
            out.append(t)
    return Counter(out)


def nomi(testo):
    testo = re.sub(r"\]\([^)]*\)", "]", testo)
    return Counter(re.findall(r"\b[A-Z][A-Z0-9@&-]{2,}(?:\s\d+)?(?:\s[A-Z]{1,3}\b)?", testo))


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    a, b = (Path(p).read_text(encoding="utf-8") for p in sys.argv[1:3])
    fa, fb = frontmatter(a), frontmatter(b)
    la, lb = fa.get("lingua", "it"), fb.get("lingua", "en")
    pa, pb = pubblicabile(a), pubblicabile(b)
    if not pa or not pb:
        sys.exit("Non trovo il titolo H1 in uno dei due file.")
    errori = 0

    print(f"# Confronto master ({la}) e traduzione ({lb})\n")
    na, nb = numeri(pa, la), numeri(pb, lb)
    manca, extra = na - nb, nb - na
    print("## Numeri\n")
    if manca or extra:
        errori += 1
        if manca:
            print("- Nel master ma non nella traduzione: " + ", ".join(f"{k} (×{v})" for k, v in manca.items()))
        if extra:
            print("- Nella traduzione ma non nel master: " + ", ".join(f"{k} (×{v})" for k, v in extra.items()))
        print("- Controlla: un numero può cambiare forma legittimamente (anni scritti in lettere, unità convertite su richiesta).")
    else:
        print(f"- Coincidono ({sum(na.values())} numeri).")

    ma, mb = nomi(pa), nomi(pb)
    print("\n## Nomi in maiuscolo\n")
    if ma - mb or mb - ma:
        errori += 1
        if ma - mb:
            print("- Nel master ma non nella traduzione: " + ", ".join(sorted(ma - mb)))
        if mb - ma:
            print("- Nella traduzione ma non nel master: " + ", ".join(sorted(mb - ma)))
    else:
        print(f"- Coincidono ({len(ma)} nomi diversi).")

    print("\n## Struttura\n")
    for nome, rx in [("Sottotitoli H2", r"^## "), ("Sottotitoli H3 e FAQ", r"^### ")]:
        ca, cb = len(re.findall(rx, pa, re.M)), len(re.findall(rx, pb, re.M))
        print(f"- {nome}: master {ca}, traduzione {cb}" + ("" if ca == cb else "  ← diversi"))

    print("\n## Link\n")
    link_b = re.findall(r"\]\((https?://[^)]+)\)", pb)
    rimasti = [u for u in link_b if re.search(rf"/{la[:2]}(/|$)", u)]
    print(f"- Link nella traduzione: {len(link_b)}")
    for u in rimasti:
        print(f"- Punta ancora alla versione {la[:2]}: {u}")

    print("\n## Segnaposto\n")
    for nome, t in [("master", pa), ("traduzione", pb)]:
        s = SEGNAPOSTO.findall(t)
        print(f"- {nome}: {len(s)}")
    sys.exit(1 if errori else 0)


if __name__ == "__main__":
    main()
