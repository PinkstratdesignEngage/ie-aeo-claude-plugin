#!/usr/bin/env python3
"""Raccoglie dal repo di un cliente i segnali per il piano editoriale del mese.

Uso, dalla radice del repo del cliente:
    python3 -I raccogli_segnali.py [--decisioni <file.json>] [--righe 12]
                                   [--tema "parola, sinonimo, nome prodotto" ...] [--solo-temi]

Legge, se ci sono, solo file già presenti nel repo, nei percorsi standard del plugin IE-AEO:
- analisi/dashboard/dati.json: azioni della dashboard realizzabili con una skill di contenuto;
- --decisioni: le decisioni della dashboard, salvate da ArtifactData list (collezione decisioni);
- l'ultima cartella di raw/hubspot-aeo/: raccomandazioni di contenuto e prompt a bassa visibilità;
- l'ultima cartella di raw/gsc/: opportunità (domande prima) e pagine in calo;
- l'ultima cartella di raw/semrush/: ricerche con AI Overview, gap con i competitor, keyword confermate;
- 05-content-pillars/*/domande-aeo.md e topic-cluster.md: domande non ancora coperte da un contenuto;
- contenuti/: contenuti in brief o in bozza, e domande AEO coperte;
- contenuti/piano-editoriale/AAAA-MM.md: le voci non chiuse dell'ultimo piano.

Con --tema (ripetibile, una volta per tema proposto dall'editor) cerca anche le tracce del tema
nel repo: query e pagine di Search Console, keyword di Semrush, prompt di HubSpot AEO, domande AEO,
file della knowledge base e contenuti che lo nominano. Con --solo-temi stampa solo questa parte.

Non chiama servizi esterni e non scrive nulla: stampa i segnali in Markdown, con i riferimenti
(id di azione, id di raccomandazione, query, numero di domanda) da citare nel piano.
"""
import argparse
import csv
import datetime as dt
import json
import re
from pathlib import Path

CHIUSI = {"pubblicato", "fatto", "scartato", "rinviato-chiuso"}


def ultima(radice):
    p = Path(radice)
    if not p.is_dir():
        return None
    d = sorted(x for x in p.iterdir() if x.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", x.name))
    return d[-1] if d else None


def eta(cartella):
    return (dt.date.today() - dt.date.fromisoformat(cartella.name)).days


def leggi_csv(f):
    if not f.exists():
        return []
    with f.open(newline="", encoding="utf-8-sig") as h:
        return list(csv.DictReader(h))


def num(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def frontmatter(testo):
    m = re.match(r"---\n(.*?)\n---", testo, re.S)
    out = {}
    if m:
        for riga in m.group(1).splitlines():
            if ":" in riga and not riga.startswith(" "):
                k, v = riga.split(":", 1)
                out[k.strip()] = v.strip()
    return out


def tabelle(testo):
    """Righe delle tabelle Markdown come dizionari, per nome di colonna in minuscolo."""
    righe, testa = [], None
    for r in testo.splitlines():
        if not r.startswith("|"):
            testa = None
            continue
        celle = [c.strip() for c in r.strip().strip("|").split("|")]
        if testa is None:
            testa = [c.lower() for c in celle]
        elif not set("".join(celle)) <= set("-: "):
            righe.append(dict(zip(testa, celle)))
    return righe


def tabella(titolo, intestazione, righe, n):
    print(f"\n### {titolo}\n")
    if not righe:
        print("Nessuno.")
        return
    print("| " + " | ".join(intestazione) + " |")
    print("|" + "---|" * len(intestazione))
    for r in righe[:n]:
        print("| " + " | ".join(str(c).replace("|", "/") for c in r) + " |")
    if len(righe) > n:
        print(f"\n…e altri {len(righe) - n}.")


def decisioni(percorso):
    if not percorso:
        return {}
    dati = json.loads(Path(percorso).read_text(encoding="utf-8"))
    if isinstance(dati, dict) and "documents" in dati:
        dati = dati["documents"]
    out = {}
    if isinstance(dati, dict):
        for k, v in dati.items():
            out[k] = (v or {}).get("stato", "")
    else:
        for d in dati:
            k = d.get("doc_id") or d.get("id")
            corpo = d.get("data") or d
            out[k] = corpo.get("stato", "")
    return out


def parole_tema(tema):
    return [w.strip().lower() for w in tema.split(",") if w.strip()]


def contiene(testo, parole):
    t = (testo or "").lower()
    return any(p in t for p in parole)


def tracce_tema(tema, gsc, sem, hs, n):
    parole = parole_tema(tema)
    print(f"\n## Tema proposto: {tema}\n")
    # Search Console
    righe = [r for r in leggi_csv(gsc / "query_pagina.csv") if contiene(r.get("query"), parole)] if gsc else []
    if gsc:
        imp = sum(num(r.get("impressioni")) for r in righe)
        clic = sum(num(r.get("click", r.get("clic"))) for r in righe)
        query, pagine = {}, {}
        for r in righe:
            query[r["query"]] = query.get(r["query"], 0) + num(r.get("impressioni"))
            pagine[r["pagina"]] = pagine.get(r["pagina"], 0) + num(r.get("impressioni"))
        print(f"- **Search Console:** {len(query)} query, {int(imp)} impressioni, {int(clic)} click negli ultimi 16 mesi")
        for q, v in sorted(query.items(), key=lambda x: -x[1])[:n]:
            print(f"  - query \"{q}\": {int(v)} impressioni")
        for u, v in sorted(pagine.items(), key=lambda x: -x[1])[:3]:
            print(f"  - pagina che le riceve: {u} ({int(v)} impressioni)")
    else:
        print("- **Search Console:** nessuna estrazione")
    # Semrush
    if sem:
        kw = []
        for f in ("opportunita_keyword.csv", "aio.csv", "gap_contenuti.csv", "posizioni.csv"):
            for r in leggi_csv(sem / f):
                if contiene(r.get("keyword"), parole):
                    kw.append((r.get("database", ""), r.get("keyword", ""), num(r.get("volume")), f.split(".")[0]))
        visti, uniche = set(), []
        for k in sorted(kw, key=lambda x: -x[2]):
            if k[:2] not in visti:
                visti.add(k[:2])
                uniche.append(k)
        print(f"- **Semrush:** {len(uniche)} keyword")
        for db, k, v, f in uniche[:n]:
            print(f"  - [{db}] \"{k}\": volume {int(v)} ({f})")
    else:
        print("- **Semrush:** nessuna estrazione")
    # HubSpot AEO
    if hs and (hs / "metriche.json").exists():
        metr = json.loads((hs / "metriche.json").read_text(encoding="utf-8"))
        pr = [p for v in metr.values() if isinstance(v, dict) and isinstance(v.get("prompts"), dict)
              for p in v["prompts"].get("prompts", []) if contiene(p.get("prompt"), parole)]
        print(f"- **HubSpot AEO:** {len(pr)} prompt tracciati sul tema")
        for p in pr[:n]:
            print(f"  - {p.get('id')} \"{p.get('prompt')}\": visibilità {p.get('visibility')}")
    else:
        print("- **HubSpot AEO:** nessuna estrazione")
    # Domande AEO, knowledge base e contenuti
    dom = []
    for f in Path("05-content-pillars").glob("*/domande-aeo.md"):
        for riga in f.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|", riga)
            if m and contiene(m.group(2), parole):
                dom.append(f"{f.parent.name} #{m.group(1)}: {m.group(2)}")
    print(f"- **Domande AEO dei pillar:** {len(dom)}")
    for d in dom[:n]:
        print(f"  - {d}")
    kb, cont = [], []
    for f in sorted(Path(".").rglob("*.md")):
        parti = f.parts
        if not parti or parti[0] in ("raw", "_privato", "analisi", ".git", ".claude"):
            continue
        try:
            t = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        volte = sum(t.lower().count(p) for p in parole)
        if volte:
            (cont if parti[0] == "contenuti" else kb).append((volte, str(f)))
    print(f"- **Knowledge base:** {len(kb)} file lo nominano")
    for v, f in sorted(kb, reverse=True)[:n]:
        print(f"  - {f} ({v})")
    print(f"- **Contenuti del repo:** {len(cont)} file lo nominano")
    for v, f in sorted(cont, reverse=True)[:n]:
        print(f"  - {f} ({v})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--decisioni", default="")
    ap.add_argument("--righe", type=int, default=12)
    ap.add_argument("--tema", action="append", default=[])
    ap.add_argument("--solo-temi", action="store_true")
    a = ap.parse_args()
    n = a.righe

    gsc, sem, hs = ultima("raw/gsc"), ultima("raw/semrush"), ultima("raw/hubspot-aeo")
    if a.solo_temi:
        print("# Tracce dei temi proposti\n")
        for t in a.tema:
            tracce_tema(t, gsc, sem, hs, 5)
        return
    dash = Path("analisi/dashboard/dati.json")
    print("# Segnali per il piano editoriale\n")
    print("## Fonti\n")
    for nome, c in [("Search Console", gsc), ("Semrush", sem), ("HubSpot AEO", hs)]:
        print(f"- **{nome}:** " + (f"`{c}`, {eta(c)} giorni fa" if c else "nessuna estrazione"))
    print(f"- **Dashboard:** " + (f"`{dash}`" if dash.exists() else "assente"))
    dec = decisioni(a.decisioni)
    print(f"- **Decisioni della dashboard:** " + (f"{len(dec)} lette" if a.decisioni else "non fornite (--decisioni)"))

    # Dashboard
    if dash.exists():
        d = json.loads(dash.read_text(encoding="utf-8"))
        pagine = d.get("pagine", [])
        ordine = {"approvata": 0, "in-corso": 1, "": 2, "da-decidere": 2, "fatta": 3}
        prio = {"alta": 0, "media": 1, "bassa": 2}
        righe = []
        for x in d.get("azioni", []):
            if "ie-aeo-" not in (x.get("skill") or ""):
                continue
            stato = dec.get(x["id"], "")
            if stato == "scartata":
                continue
            url = ", ".join(pagine[i] for i in (x.get("pagine") or [])[:2] if isinstance(i, int) and i < len(pagine))
            righe.append(((ordine.get(stato, 2), prio.get(x.get("priorita"), 3), -num(x.get("punteggio"))),
                          [x["id"], stato or "da-decidere", x.get("priorita", ""), x.get("titolo", ""), x.get("skill", ""),
                           int(num(x.get("impressioni"))), url]))
        righe.sort(key=lambda r: r[0])
        print("\n## Dashboard SEO e AEO")
        tabella("Azioni realizzabili con una skill di contenuto (scartate escluse)",
                ["Id", "Decisione", "Priorità", "Azione", "Skill", "Impressioni", "Pagine"], [r[1] for r in righe], n)

    # HubSpot AEO
    print("\n## HubSpot AEO")
    if hs:
        racc = {}
        fonti = [json.loads((hs / "raccomandazioni.json").read_text(encoding="utf-8"))] if (hs / "raccomandazioni.json").exists() else []
        for f in (hs / "prompt").glob("*.json") if (hs / "prompt").is_dir() else []:
            fonti.append(json.loads(f.read_text(encoding="utf-8")))

        def raccogli(o):
            if isinstance(o, dict):
                if "recommendations" in o and isinstance(o["recommendations"], list):
                    for r in o["recommendations"]:
                        racc[r.get("id")] = r
                for v in o.values():
                    raccogli(v)
            elif isinstance(o, list):
                for v in o:
                    raccogli(v)
        for f in fonti:
            raccogli(f)
        cont = [r for r in racc.values() if (r.get("type") == "CONTENT" or r.get("actionCategory") == "CREATE_CONTENT")
                and r.get("status") in ("NEW", "IN_PROGRESS", None)]
        p_ord = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        cont.sort(key=lambda r: p_ord.get(r.get("priority"), 3))
        tabella("Raccomandazioni di contenuto aperte", ["Id", "Priorità", "Raccomandazione", "Contenuto suggerito", "Tipo", "Prompt"],
                [[r.get("id"), r.get("priority"), r.get("title"), r.get("contentTitle", ""), r.get("contentType", ""), r.get("promptId", "")] for r in cont], n)
        metr = json.loads((hs / "metriche.json").read_text(encoding="utf-8"))
        prompts = []
        for v in metr.values():
            if isinstance(v, dict) and isinstance(v.get("prompts"), dict):
                prompts = v["prompts"].get("prompts", [])
        prompts = [p for p in prompts if p.get("trackingStatus", "TRACKED") == "TRACKED"]
        prompts.sort(key=lambda p: p.get("visibility") or 0)
        tabella("Prompt tracciati, dalla visibilità più bassa", ["Id", "Prompt", "Fase", "Lingua", "Visibilità", "Citazioni"],
                [[p.get("id"), p.get("prompt"), p.get("buyingJourneyPhase"), p.get("language"), p.get("visibility"), p.get("citationCount")] for p in prompts], n)
    else:
        print("\nNessuna estrazione.")

    # Search Console
    print("\n## Search Console")
    if gsc:
        op = leggi_csv(gsc / "opportunita.csv")
        dom = sorted([r for r in op if r.get("domanda") == "sì"], key=lambda r: -num(r.get("impressioni")))
        tabella("Domande con impressioni, posizione da migliorare", ["Query", "Impressioni", "Click", "Posizione", "Pagina principale"],
                [[r["query"], r["impressioni"], r["click"], r["posizione"], r["pagina_principale"]] for r in dom], n)
        calo = sorted(leggi_csv(gsc / "pagine_in_calo.csv"), key=lambda r: num(r.get("click_recenti")) - num(r.get("click_anno_prima")))
        tabella("Pagine in calo (tre mesi contro l'anno prima)", ["Pagina", "Click ora", "Click anno prima", "Variazione"],
                [[r["pagina"], r["click_recenti"], r["click_anno_prima"], r["variazione_click"]] for r in calo], n)
    else:
        print("\nNessuna estrazione.")

    # Semrush
    print("\n## Semrush")
    if sem:
        visti, aio = set(), []
        for r in sorted(leggi_csv(sem / "aio.csv"), key=lambda r: -num(r.get("volume"))):
            k = (r.get("database"), r.get("keyword"), r.get("url"))
            if k not in visti:
                visti.add(k)
                aio.append(r)
        tabella("Ricerche con AI Overview", ["Mercato", "Keyword", "Volume", "Posizione del cliente", "Pagina"],
                [[r["database"], r["keyword"], r["volume"], r.get("posizione_cliente", ""), r.get("url", "")] for r in aio], n)
        gap = sorted(leggi_csv(sem / "gap_contenuti.csv"), key=lambda r: -num(r.get("volume")))
        tabella("Gap con i competitor", ["Mercato", "Keyword", "Volume", "Posizione del cliente", "Competitor migliore"],
                [[r["database"], r["keyword"], r["volume"], r.get("posizione_cliente", ""), r.get("miglior_competitor", "")] for r in gap], n)
    else:
        print("\nNessuna estrazione.")

    # Contenuti e domande AEO
    coperte, aperti = {}, []
    for f in sorted(Path("contenuti").rglob("*.md")):
        if "piano-editoriale" in f.parts or "modelli" in f.parts or f.name == "README.md":
            continue
        fm = frontmatter(f.read_text(encoding="utf-8"))
        if not fm or not fm.get("tipo"):
            continue
        for x in re.findall(r"\d+", fm.get("domande_aeo", "")):
            coperte.setdefault(fm.get("pillar", "*"), set()).add(x)
        if fm.get("stato") in ("brief", "bozza"):
            aperti.append([str(f), fm.get("tipo", ""), fm.get("stato", ""), fm.get("titolo", "")[:90], fm.get("pubblicazione", "")])
    print("\n## Knowledge base e contenuti")
    tabella("Contenuti in brief o in bozza", ["File", "Tipo", "Stato", "Titolo", "Pubblicazione"], aperti, n)

    for pil in sorted(Path("05-content-pillars").glob("*/domande-aeo.md")):
        nome = pil.parent.name
        cop = coperte.get(nome, set()) | coperte.get("*", set())
        prio = {}
        tc = pil.parent / "topic-cluster.md"
        if tc.exists():
            for r in tabelle(tc.read_text(encoding="utf-8")):
                if r.get("id"):
                    prio[r["id"]] = r.get("priorità", r.get("priorita", ""))
        libere, sezione = [], ""
        for riga in pil.read_text(encoding="utf-8").splitlines():
            if riga.startswith("## "):
                sezione = riga[3:].split(":")[0].strip()
            m = re.match(r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|", riga)
            if m and m.group(1) not in cop and "esclus" not in sezione.lower():
                cl = m.group(4).strip()
                libere.append([m.group(1), sezione, m.group(2), m.group(3), cl, prio.get(cl, "")])
        ordine = {"Alta": 0, "Media": 1, "Bassa": 2}
        libere.sort(key=lambda r: (ordine.get(r[5].split()[0] if r[5] else "", 3), int(r[0])))
        tabella(f"Domande AEO non coperte: {nome} ({len(cop)} coperte o in lavorazione)", ["#", "Sezione", "Domanda", "Persona", "Cluster", "Priorità del cluster"], libere, n * 2)

    # Piano precedente
    print("\n## Piano precedente")
    piani = sorted(Path("contenuti/piano-editoriale").glob("[0-9][0-9][0-9][0-9]-[0-9][0-9].md")) if Path("contenuti/piano-editoriale").is_dir() else []
    if not piani:
        print("\nNessun piano precedente.")
    else:
        righe = [r for r in tabelle(piani[-1].read_text(encoding="utf-8")) if r.get("stato") and r.get("stato") not in CHIUSI]
        tabella(f"Voci non chiuse di `{piani[-1]}`", ["Id", "Contenuto", "Skill", "Stato"],
                [[r.get("id", ""), r.get("contenuto", r.get("titolo", "")), r.get("skill", ""), r.get("stato", "")] for r in righe], n)

    if a.tema:
        print("\n# Tracce dei temi proposti")
        for t in a.tema:
            tracce_tema(t, gsc, sem, hs, 5)


if __name__ == "__main__":
    main()
