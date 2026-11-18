#!/usr/bin/env python3
"""Domande aperte della knowledge base di un cliente: dove pesano, in che ordine affrontarle, come chiuderle.

Uso, dalla radice del repo del cliente:
    python3 -I stato_domande.py elenco [--chi "Marketing"] [--tema "eco ring, chiller"] [--numeri 6,8] [--righe 60]
    python3 -I stato_domande.py dettaglio 47
    python3 -I stato_domande.py risolvi 47 --risposta "..." --fonte R03 [--scrivi]
    python3 -I stato_domande.py nuova --domanda "..." --file "[servizi](03-offerta/servizi.md)" --chi "Service" [--scrivi]

elenco    ordina le domande aperte per peso: contenuti in lavorazione che le citano, incoerenze
          collegate, file della knowledge base interessati. Segnala i riferimenti a domande che non
          esistono o sono già risolte, e le incoerenze che chiedono una domanda nuova.
dettaglio tutto ciò che serve per presentare una domanda: la riga, le righe dei file che la citano,
          i [DA VALIDARE] dei file interessati, le incoerenze e i contenuti collegati.
risolvi   sposta la domanda in "Risolte" con risposta e fonte, e aggiorna il frontmatter.
nuova     aggiunge una domanda con il primo numero libero.
risolvi e nuova mostrano le differenze e scrivono solo con --scrivi; una seconda esecuzione non
cambia nulla. Le altre modifiche (file della knowledge base, registro fonti) le fa Claude.
"""
import argparse
import datetime as dt
import difflib
import re
import sys
from pathlib import Path

FUORI = ("_privato/", "raw/", ".git/", "node_modules/", ".claude/", "app/", "tools/")
RX_CITA = re.compile(r"[Dd]omand[ae](?:\s+apert[ae])?\s+(\d+(?:\s*(?:,|e|ed|/)\s*\d+)*)")
RX_PUNTO = re.compile(r"^\s*[-*]\s*\*\*(\d+(?:\s*(?:,|e|ed)\s*\d+)*)\s*[,:.]")
RX_LINK = re.compile(r"\[[^\]]*\]\(([^)#\s]+)")
CONCLUSI = {"pubblicato", "validato", "approvato-pubblicato"}


def frontmatter(testo):
    m = re.match(r"---\n(.*?)\n---", testo, re.S)
    out = {}
    if m:
        for riga in m.group(1).splitlines():
            if ":" in riga and not riga.startswith(" "):
                k, v = riga.split(":", 1)
                out[k.strip()] = v.strip().strip('"')
    return out


def celle(riga):
    return [c.strip() for c in riga.strip().strip("|").split("|")]


def separatore(riga):
    return riga.startswith("|") and set(riga.strip()) <= set("|-: ")


class Domande:
    """Il file delle domande aperte: tabella delle aperte e tabella delle risolte, con le righe originali."""

    def __init__(self, percorso):
        self.percorso = Path(percorso)
        self.righe = self.percorso.read_text(encoding="utf-8").splitlines()
        self.aperte, self.risolte = {}, {}
        self.testa_aperte, self.testa_risolte = [], []
        self.fine_aperte = self.fine_risolte = None
        sezione, testa = "aperte", None
        for i, r in enumerate(self.righe):
            if r.startswith("## "):
                sezione = "risolte" if re.search(r"risolt|chius", r, re.I) else sezione
                testa = None
                continue
            if not r.startswith("|"):
                testa = None
                continue
            if testa is None:
                testa = [c.lower() for c in celle(r)]
                if sezione == "aperte":
                    self.testa_aperte = testa
                else:
                    self.testa_risolte = testa
                continue
            if separatore(r):
                continue
            c = celle(r)
            if not c or not c[0].isdigit():
                continue
            voce = dict(zip(testa, c))
            voce["#"], voce["_riga"] = int(c[0]), i
            if sezione == "aperte":
                self.aperte[voce["#"]] = voce
                self.fine_aperte = i
            else:
                self.risolte[voce["#"]] = voce
                self.fine_risolte = i

    def campo(self, voce, *nomi):
        for k, v in voce.items():
            if any(n in k for n in nomi):
                return v
        return ""

    def prossimo(self):
        return max([0, *self.aperte, *self.risolte]) + 1


def file_md(radice, escludi):
    for f in sorted(radice.rglob("*.md")):
        rel = f.relative_to(radice).as_posix()
        if rel in escludi or any(rel.startswith(x) or f"/{x}" in f"/{rel}" for x in FUORI):
            continue
        yield rel, f


def numeri(gruppo):
    return [int(x) for x in re.findall(r"\d+", gruppo)]


def citazioni(radice, nome_domande):
    """{numero: [(file, riga, testo)]} per ogni citazione di una domanda aperta fuori dal suo file."""
    out = {}
    for rel, f in file_md(radice, {nome_domande, "fonti/registro-fonti.md"}):
        sezione_domande = False
        for i, r in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if r.startswith("#"):
                sezione_domande = bool(re.search(r"domande aperte", r, re.I))
            trovati = [n for m in RX_CITA.finditer(r) for n in numeri(m.group(1))]
            if sezione_domande:
                m = RX_PUNTO.match(r)
                if m:
                    trovati += numeri(m.group(1))
            for n in dict.fromkeys(trovati):
                out.setdefault(n, []).append((rel, i, r.strip()))
    return out


def incoerenze(radice):
    """Righe della tabella di riepilogo delle incoerenze: (numero, tema, gravità, domanda)."""
    f = radice / "fonti" / "incoerenze-cliente-sito.md"
    out = []
    if not f.exists():
        return out
    testa = None
    for r in f.read_text(encoding="utf-8").splitlines():
        if not r.startswith("|"):
            testa = None
            continue
        if testa is None:
            testa = [c.lower() for c in celle(r)]
            continue
        if separatore(r) or not any("domanda" in t for t in testa):
            continue
        v = dict(zip(testa, celle(r)))
        dom = next((v[k] for k in v if "domanda" in k), "")
        out.append((v.get("#", ""), v.get("tema", ""), v.get("gravità", v.get("gravita", "")).lower(), dom))
    return out


def stato_file(radice, rel):
    try:
        return frontmatter((radice / rel).read_text(encoding="utf-8")).get("stato", "")
    except OSError:
        return ""


def peso(voce, cit, inc, radice, d):
    """Punteggio e motivi: prima ciò che blocca contenuti in lavorazione, poi dati contraddetti, poi la base."""
    punti, motivi = 0, []
    collegati = {p.lstrip("./") for p in RX_LINK.findall(d.campo(voce, "file"))}
    contenuti = sorted({rel for rel, _, _ in cit if rel.startswith("contenuti/")} | {p for p in collegati if p.startswith("contenuti/")})
    attivi = [c for c in contenuti if stato_file(radice, c) not in CONCLUSI]
    if attivi:
        punti += 3 * len(attivi)
        motivi.append(f"{len(attivi)} contenut{'o' if len(attivi) == 1 else 'i'} in lavorazione")
    alte = [x for x in inc if x[2].startswith("alta")]
    if alte:
        punti += 2 * len(alte)
        motivi.append(f"incoerenza alta {', '.join(x[0] for x in alte)}")
    medie = [x for x in inc if not x[2].startswith("alta")]
    if medie:
        punti += len(medie)
        motivi.append(f"incoerenza {', '.join(x[0] for x in medie)}")
    kb = {p for p in collegati if not p.startswith("contenuti/")} | {rel for rel, _, _ in cit if not rel.startswith(("contenuti/", "fonti/"))}
    if any(p.endswith("CLAUDE.md") for p in kb):
        punti += 3
        motivi.append("regola del CLAUDE.md")
    if any(p.startswith("05-content-pillars/") for p in kb) or "pillar" in d.campo(voce, "file").lower():
        punti += 2
        motivi.append("pillar")
    if any(p.startswith("04-brand-voice/") for p in kb):
        punti += 2
        motivi.append("brand voice")
    punti += len(kb)
    if kb:
        motivi.append(f"{len(kb)} file della KB")
    return punti, motivi


def carica(a):
    radice = Path(".").resolve()
    d = Domande(radice / a.file)
    cit = citazioni(radice, Path(a.file).as_posix())
    inc = incoerenze(radice)
    return radice, d, cit, inc


def inc_di(inc, n):
    return [x for x in inc if n in numeri(x[3])]


def breve(t, k=110):
    t = re.sub(r"\s+", " ", t)
    return t if len(t) <= k else t[: k - 1] + "…"


def cmd_elenco(a):
    radice, d, cit, inc = carica(a)
    voci = list(d.aperte.values())
    if a.numeri:
        voluti = {int(x) for x in re.findall(r"\d+", a.numeri)}
        voci = [v for v in voci if v["#"] in voluti]
    if a.chi:
        voci = [v for v in voci if a.chi.lower() in d.campo(v, "chi").lower()]
    if a.tema:
        parole = [w.strip().lower() for w in a.tema.split(",") if w.strip()]
        voci = [v for v in voci if any(w in (d.campo(v, "domanda") + " " + d.campo(v, "file")).lower() for w in parole)]
    pesate = []
    for v in voci:
        p, motivi = peso(v, cit.get(v["#"], []), inc_di(inc, v["#"]), radice, d)
        pesate.append((p, v, motivi))
    pesate.sort(key=lambda x: (-x[0], x[1]["#"]))

    print(f"# Domande aperte: {len(d.aperte)} aperte, {len(d.risolte)} risolte\n")
    if len(voci) != len(d.aperte):
        print(f"Filtro: {len(voci)} domande.\n")
    print("| Ordine | # | Domanda | Chi può rispondere | Peso | Perché |")
    print("|---|---|---|---|---|---|")
    for k, (p, v, motivi) in enumerate(pesate[: a.righe], 1):
        print(f"| {k} | {v['#']} | {breve(d.campo(v, 'domanda')).replace('|', '/')} | {d.campo(v, 'chi')} | {p} | {'; '.join(motivi) or '-'} |")
    if len(pesate) > a.righe:
        print(f"\n…e altre {len(pesate) - a.righe}.")

    chi = {}
    for _, v, _ in pesate:
        for c in re.split(r"\s*/\s*", d.campo(v, "chi") or "non indicato"):
            chi.setdefault(c[:1].upper() + c[1:], []).append(v["#"])
    print("\n## Per chi può rispondere\n")
    for c, ns in sorted(chi.items(), key=lambda x: -len(x[1])):
        print(f"- {c}: {len(ns)} ({', '.join(map(str, ns))})")

    print("\n## Da controllare\n")
    trovato = False
    for n, righe in sorted(cit.items()):
        if n in d.aperte:
            continue
        stato = "risolta" if n in d.risolte else "non esiste"
        for rel, i, _ in righe:
            print(f"- {rel}:{i} cita la domanda {n}, che {stato}")
            trovato = True
    nuove = [x for x in inc if "nuova" in x[3].lower()]
    if nuove:
        trovato = True
        print(f"- Incoerenze che chiedono una domanda nuova, non ancora aperta: {', '.join(f'{x[0]} ({x[1]}, {x[2]})' for x in nuove)}")
    for x in inc:
        for n in numeri(x[3]):
            if n in d.risolte:
                trovato = True
                print(f"- L'incoerenza {x[0]} rimanda alla domanda {n}, già risolta: controlla se l'incoerenza è chiusa")
    if not trovato:
        print("Nulla.")


def cmd_dettaglio(a):
    radice, d, cit, inc = carica(a)
    n = a.numero
    v = d.aperte.get(n) or d.risolte.get(n)
    if not v:
        sys.exit(f"La domanda {n} non c'è in {a.file}.")
    stato = "aperta" if n in d.aperte else "risolta"
    print(f"# Domanda {n} ({stato})\n")
    print(d.righe[v["_riga"]] + "\n")
    p, motivi = peso(v, cit.get(n, []), inc_di(inc, n), radice, d) if stato == "aperta" else (0, [])
    if motivi:
        print(f"Peso {p}: {'; '.join(motivi)}\n")

    print("## Dove è citata\n")
    if not cit.get(n):
        print("In nessun file oltre a questo.")
    for rel, i, t in cit.get(n, []):
        extra = f" (stato: {stato_file(radice, rel)})" if rel.startswith("contenuti/") else ""
        print(f"- {rel}:{i}{extra}: {breve(t, 240)}")

    print("\n## [DA VALIDARE] nei file interessati\n")
    collegati = [p.lstrip("./") for p in RX_LINK.findall(d.campo(v, "file"))]
    vuoto = True
    for rel in dict.fromkeys(collegati):
        f = radice / rel
        if not f.is_file():
            print(f"- {rel}: il link non porta a un file")
            vuoto = False
            continue
        for i, t in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if "DA VALIDARE" in t:
                print(f"- {rel}:{i}: {breve(t, 240)}")
                vuoto = False
    if vuoto:
        print("Nessuno: il file interessato non ha marcatori, o la colonna non ha link.")
    print("\nNon tutti i marcatori riguardano questa domanda: scegli quelli sullo stesso tema.")

    print("\n## Incoerenze collegate\n")
    xs = inc_di(inc, n)
    print("\n".join(f"- {x[0]}. {x[1]} (gravità {x[2]}): voce in fonti/incoerenze-cliente-sito.md" for x in xs) or "Nessuna.")


def scrivi(a, d, nuove, messaggio):
    vecchio = "\n".join(d.righe) + "\n"
    nuovo = "\n".join(nuove) + "\n"
    if vecchio == nuovo:
        print("Nessuna modifica.")
        return
    sys.stdout.writelines(difflib.unified_diff(vecchio.splitlines(True), nuovo.splitlines(True), a.file, a.file))
    if a.scrivi:
        d.percorso.write_text(nuovo, encoding="utf-8")
        print(f"\n{messaggio}")
    else:
        print("\nAnteprima: niente è stato scritto. Rilancia con --scrivi dopo l'ok.")


def frontmatter_aggiornato(righe, fonte):
    oggi = dt.date.today().isoformat()
    out, dentro = [], False
    for k, r in enumerate(righe):
        if r == "---":
            dentro = k == 0
        if dentro and r.startswith("ultimo_aggiornamento:"):
            r = f"ultimo_aggiornamento: {oggi}"
        if dentro and fonte and r.startswith("fonti:"):
            codici = re.findall(r"[A-Za-z]+\d+", r.split(":", 1)[1])
            if fonte not in codici:
                r = f"fonti: [{', '.join(codici + [fonte])}]"
        out.append(r)
    return out


def riga_tabella(testa, valori):
    valori = [x.replace("|", "/").replace("\n", " ") for x in valori]
    valori += [""] * (len(testa) - len(valori))
    return "| " + " | ".join(valori[: len(testa)]) + " |"


def cmd_risolvi(a):
    d = Domande(Path(a.file))
    n = a.numero
    if n not in d.aperte:
        print(f"La domanda {n} non è tra le aperte" + (": è già risolta." if n in d.risolte else "."))
        return
    v = d.aperte[n]
    risposta = a.risposta.strip()
    if a.fonte and f"[{a.fonte}" not in risposta:
        risposta += f" [{a.fonte}]"
    testa = d.testa_risolte or ["#", "domanda", "risposta e fonte"]
    nuova = riga_tabella(testa, [str(n), d.campo(v, "domanda")] + [""] * (len(testa) - 3) + [risposta])
    righe = list(d.righe)
    if d.fine_risolte is not None:
        righe.insert(d.fine_risolte + 1, nuova)
    elif d.testa_risolte:
        k = max(i for i, r in enumerate(righe) if separatore(r))
        righe.insert(k + 1, nuova)
    else:
        righe += ["", "## Risolte", "", "| # | Domanda | Risposta e fonte |", "|---|---|---|", nuova]
    del righe[v["_riga"]]
    scrivi(a, d, frontmatter_aggiornato(righe, a.fonte), f"Domanda {n} spostata in Risolte.")


def cmd_nuova(a):
    d = Domande(Path(a.file))
    for v in d.aperte.values():
        if d.campo(v, "domanda").strip().lower() == a.domanda.strip().lower():
            print(f"La domanda c'è già: è la {v['#']}.")
            return
    n = d.prossimo()
    testa = d.testa_aperte or ["#", "domanda", "file interessato", "chi può rispondere", "stato"]
    riga = riga_tabella(testa, [str(n), a.domanda, a.file_kb, a.chi, "aperta"])
    righe = list(d.righe)
    if d.fine_aperte is not None:
        righe.insert(d.fine_aperte + 1, riga)
    else:
        k = next(i for i, r in enumerate(righe) if separatore(r))
        righe.insert(k + 1, riga)
    scrivi(a, d, frontmatter_aggiornato(righe, None), f"Domanda {n} aggiunta.")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", default="domande-aperte.md", help="file delle domande, dalla radice del repo")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("elenco")
    e.add_argument("--chi")
    e.add_argument("--tema", help="parole separate da virgola, cercate nella domanda e nei file interessati")
    e.add_argument("--numeri")
    e.add_argument("--righe", type=int, default=60)
    t = sub.add_parser("dettaglio")
    t.add_argument("numero", type=int)
    r = sub.add_parser("risolvi")
    r.add_argument("numero", type=int)
    r.add_argument("--risposta", required=True)
    r.add_argument("--fonte", help="codice del registro fonti, per esempio R03")
    r.add_argument("--scrivi", action="store_true")
    nv = sub.add_parser("nuova")
    nv.add_argument("--domanda", required=True)
    nv.add_argument("--file", dest="file_kb", default="", help="cella 'File interessato', con link relativi")
    nv.add_argument("--chi", default="")
    nv.add_argument("--scrivi", action="store_true")
    a = ap.parse_args()
    if not Path(a.file).is_file():
        sys.exit(f"{a.file} non c'è: lancia lo script dalla radice del repo del cliente.")
    {"elenco": cmd_elenco, "dettaglio": cmd_dettaglio, "risolvi": cmd_risolvi, "nuova": cmd_nuova}[a.cmd](a)


if __name__ == "__main__":
    main()
