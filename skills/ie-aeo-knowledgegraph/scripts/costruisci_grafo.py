#!/usr/bin/env python3
"""Costruisce il grafo della knowledge base di un cliente, da dare alla webapp.

Uso, dalla radice del repo del cliente:
    python3 -I costruisci_grafo.py [--uscita analisi/knowledge-graph] [--con-testo]

Legge i file Markdown della knowledge base, ne prende il frontmatter e i link, e scrive
grafo.json: i nodi sono i file e le voci di tassonomia, gli archi sono i riferimenti.

Nodi:
    file        un documento della knowledge base, con titolo, tipo, stato, copertura,
                data dell'ultimo aggiornamento, estratto e titoli delle sezioni
    soluzione   una voce di `soluzioni:` del frontmatter
    prodotto    una voce di `prodotti:`
    settore     il valore di `settore:`
    fonte       un codice di `fonti:`, per esempio D01 o S02, come nel registro fonti

Archi:
    cita        un link Markdown da un file a un altro file del repo
    riguarda    un file e una voce di tassonomia (soluzione, prodotto, settore)
    fonte       un file e la fonte da cui viene

Cosa resta fuori, sempre: `_privato/`, `.git/`, `node_modules/`, e le cartelle indicate
con --escludi. Anche `raw/` resta fuori: contiene i materiali grezzi e i segnaposto, non
i nodi della knowledge base.

**Di default il testo dei documenti non entra nel grafo.** Di ogni file restano titolo,
metadati, un estratto di poche righe e i titoli delle sezioni: quanto basta per navigare.
Con --con-testo il corpo completo viene incluso e la chat della pagina risponde anche nel
merito: chiunque abbia il link dell'artifact legge allora tutta la knowledge base. Lo
decide il consulente, e la scelta resta in config.json ("con_testo": true).
"""
import argparse
import json
import re
import sys
from pathlib import Path

ESCLUSE = {".git", "node_modules", "_privato", "raw", ".claude", "app", "tools"}
RE_LINK = re.compile(r"\[([^\]]*)\]\(([^)\s]+\.md)(?:#[^)]*)?\)")
RE_TITOLO = re.compile(r"^(#{1,4})\s+(.+?)\s*$", re.MULTILINE)
RE_FONTE = re.compile(r"^[A-Z]\d{2}$")
# Campi del frontmatter che valgono come tassonomia: nome del campo -> tipo di nodo
TASSONOMIA = {"soluzioni": "soluzione", "prodotti": "prodotto", "settore": "settore"}


def frontmatter(testo):
    """Il frontmatter come dizionario. Legge il sottoinsieme YAML che la KB usa davvero:
    chiave: valore, chiave: [a, b], virgolette facoltative. Niente annidamento."""
    if not testo.startswith("---"):
        return {}, testo
    fine = testo.find("\n---", 3)
    if fine == -1:
        return {}, testo
    campi = {}
    for riga in testo[3:fine].splitlines():
        if not riga.strip() or riga.lstrip().startswith("#") or ":" not in riga:
            continue
        if riga[0] in " \t":
            continue  # continuazione o annidamento: non serve alla KB
        chiave, _, valore = riga.partition(":")
        valore = valore.strip()
        if valore.startswith("[") and valore.endswith("]"):
            campi[chiave.strip()] = [v.strip().strip("\"'") for v in valore[1:-1].split(",") if v.strip()]
        else:
            campi[chiave.strip()] = valore.strip("\"'")
    return campi, testo[fine + 4:]


def estratto(corpo, caratteri=320):
    """Il primo paragrafo vero: non un titolo, non una tabella, non un blocco di codice."""
    for blocco in re.split(r"\n\s*\n", corpo):
        b = blocco.strip()
        if not b or b.startswith(("#", "|", "```", ">", "---", "- ", "* ", "<!--")):
            continue
        b = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", b)          # link: resta il testo
        b = re.sub(r"[*_`]", "", b).replace("\n", " ")
        b = re.sub(r"\s+", " ", b).strip()
        if len(b) < 40:
            continue
        return b if len(b) <= caratteri else b[:caratteri].rsplit(" ", 1)[0] + "…"
    return ""


def etichetta(percorso, campi):
    t = campi.get("titolo") or campi.get("nome")
    if t:
        return t
    return percorso.stem.replace("-", " ").replace("_", " ").capitalize()


def tipo_di(percorso, campi):
    if campi.get("tipo"):
        return campi["tipo"]
    # Senza tipo nel frontmatter vale la cartella di primo livello, senza il numero davanti
    parti = percorso.parts
    if len(parti) > 1:
        return re.sub(r"^\d+-", "", parti[0])
    return "documento"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--radice", default=".", help="radice del repo del cliente (default: la cartella corrente)")
    p.add_argument("--uscita", default="analisi/knowledge-graph")
    p.add_argument("--escludi", default="", help="altre cartelle da lasciare fuori, separate da virgola")
    p.add_argument("--con-testo", action="store_true",
                   help="include il corpo completo dei documenti: chi ha il link della pagina legge tutta la knowledge base")
    a = p.parse_args()

    radice = Path(a.radice).resolve()
    if not radice.is_dir():
        sys.exit(f"{radice} non è una cartella.")
    escluse = ESCLUSE | {d.strip() for d in a.escludi.split(",") if d.strip()}

    file = []
    for f in sorted(radice.rglob("*.md")):
        rel = f.relative_to(radice)
        if set(rel.parts) & escluse or rel.name.startswith("."):
            continue
        file.append(rel)
    if not file:
        sys.exit(f"Nessun file Markdown in {radice} fuori da {', '.join(sorted(escluse))}.")

    nodi, archi, per_percorso = {}, [], {}
    for rel in file:
        testo = (radice / rel).read_text(encoding="utf-8", errors="replace")
        campi, corpo = frontmatter(testo)
        nid = str(rel).replace("\\", "/")
        per_percorso[nid] = nid
        per_percorso[rel.name] = nid  # per risolvere i link scritti con il solo nome del file
        nodo = {
            "id": nid, "tipo_nodo": "file", "etichetta": etichetta(rel, campi),
            "tipo": tipo_di(rel, campi), "cartella": rel.parts[0] if len(rel.parts) > 1 else "/",
            "stato": campi.get("stato", ""), "copertura": campi.get("copertura", ""),
            "aggiornato": campi.get("ultimo_aggiornamento", ""), "url": campi.get("url", ""),
            "pubblico": campi.get("pubblico", ""), "percorso": nid,
            "estratto": estratto(corpo),
            "sezioni": [t.strip() for _, t in RE_TITOLO.findall(corpo)][:25],
            "parole": len(corpo.split()),
        }
        if a.con_testo:
            nodo["testo"] = corpo.strip()
        nodi[nid] = nodo

        # Tassonomia e fonti: nodi condivisi, che è ciò che tiene insieme il grafo
        for campo, tipo_nodo in TASSONOMIA.items():
            valori = campi.get(campo) or []
            if isinstance(valori, str):
                valori = [valori] if valori else []
            for v in valori:
                vid = f"{tipo_nodo}:{v.strip().lower()}"
                nodi.setdefault(vid, {"id": vid, "tipo_nodo": tipo_nodo, "etichetta": v.strip(),
                                      "tipo": tipo_nodo, "cartella": "", "stato": "", "copertura": "",
                                      "aggiornato": "", "url": "", "pubblico": "", "percorso": "",
                                      "estratto": "", "sezioni": [], "parole": 0})
                archi.append({"da": nid, "a": vid, "tipo": "riguarda"})
        for f_ in (campi.get("fonti") or []):
            codice = f_.strip().strip("`")
            if not RE_FONTE.match(codice):
                continue
            fid = f"fonte:{codice}"
            nodi.setdefault(fid, {"id": fid, "tipo_nodo": "fonte", "etichetta": codice, "tipo": "fonte",
                                  "cartella": "", "stato": "", "copertura": "", "aggiornato": "",
                                  "url": "", "pubblico": "", "percorso": "", "estratto": "",
                                  "sezioni": [], "parole": 0})
            archi.append({"da": nid, "a": fid, "tipo": "fonte"})

    # Link fra documenti: si risolvono rispetto alla cartella del file che li contiene
    non_risolti = []
    for rel in file:
        nid = str(rel).replace("\\", "/")
        testo = (radice / rel).read_text(encoding="utf-8", errors="replace")
        for _, destinazione in RE_LINK.findall(testo):
            if destinazione.startswith(("http://", "https://")):
                continue
            # Il link è relativo al file che lo contiene: i ../ si normalizzano senza toccare il disco
            norm = []
            for parte in str(rel.parent / destinazione).replace("\\", "/").split("/"):
                if parte == "..":
                    if norm:
                        norm.pop()
                elif parte not in ("", "."):
                    norm.append(parte)
            candidati = ["/".join(norm), destinazione.lstrip("./"), Path(destinazione).name]
            bersaglio = next((per_percorso[c] for c in candidati if c in per_percorso), None)
            if not bersaglio:
                non_risolti.append({"da": nid, "link": destinazione})
                continue
            if bersaglio != nid:
                archi.append({"da": nid, "a": bersaglio, "tipo": "cita"})

    # Un arco per coppia e tipo
    viste, unici = set(), []
    for e in archi:
        k = (e["da"], e["a"], e["tipo"])
        if k not in viste:
            viste.add(k)
            unici.append(e)
    archi = unici

    grado = {n: 0 for n in nodi}
    for e in archi:
        grado[e["da"]] += 1
        grado[e["a"]] += 1
    for n, g in grado.items():
        nodi[n]["grado"] = g
    orfani = [n for n, g in grado.items() if g == 0 and nodi[n]["tipo_nodo"] == "file"]

    dati = {
        "versione": 1,
        "radice": radice.name,
        "generato_il": __import__("datetime").date.today().isoformat(),
        "con_testo": bool(a.con_testo),
        "nodi": list(nodi.values()),
        "archi": archi,
        "conteggi": {
            "file": sum(1 for n in nodi.values() if n["tipo_nodo"] == "file"),
            "tassonomia": sum(1 for n in nodi.values() if n["tipo_nodo"] in TASSONOMIA.values()),
            "fonti": sum(1 for n in nodi.values() if n["tipo_nodo"] == "fonte"),
            "archi": len(archi),
            "cita": sum(1 for e in archi if e["tipo"] == "cita"),
            "orfani": len(orfani),
        },
        "orfani": sorted(orfani),
        "link_non_risolti": non_risolti[:50],
    }
    uscita = Path(a.uscita)
    uscita.mkdir(parents=True, exist_ok=True)
    (uscita / "grafo.json").write_text(json.dumps(dati, ensure_ascii=False, separators=(",", ":")),
                                       encoding="utf-8")
    c = dati["conteggi"]
    print(f"grafo.json in {uscita}: {c['file']} documenti, {c['tassonomia']} voci di tassonomia, "
          f"{c['fonti']} fonti, {c['archi']} archi ({c['cita']} citazioni fra documenti)")
    if orfani:
        print(f"  {len(orfani)} documenti non collegati a niente: " + ", ".join(orfani[:5])
              + (" …" if len(orfani) > 5 else ""))
    if non_risolti:
        print(f"  {len(non_risolti)} link che non puntano a un file esistente, i primi: "
              + ", ".join(f"{x['da']} → {x['link']}" for x in non_risolti[:3]))
    if a.con_testo:
        print("  ATTENZIONE: il grafo contiene il testo completo dei documenti: chi ha il link della pagina legge tutta la knowledge base.")


if __name__ == "__main__":
    main()
