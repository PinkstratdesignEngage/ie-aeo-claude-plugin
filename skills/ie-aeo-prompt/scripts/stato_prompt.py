#!/usr/bin/env python3
"""Stato dei prompt tracciati in HubSpot AEO di un cliente, dai dati già salvati nel repo.

Uso, dalla radice del repo del cliente:
    python3 -I stato_prompt.py [--hubspot raw/hubspot-aeo] [--registro analisi/prompt-aeo/registro.md]
                               [--pillar 05-content-pillars] [--min-giorni 60] [--dominio esempio.com]

Legge l'ultima cartella con data in raw/hubspot-aeo/ (scritta da ie-aeo-hubspot-aeo) e, se c'è,
quella precedente per il confronto. Non chiama HubSpot e non scrive nulla: stampa in Markdown
- capacità (prompt usati, disponibili, crediti);
- rendimento di ogni prompt tracciato, con età e segnalazioni;
- copertura per fase del percorso d'acquisto, lingua e paese, ICP, prodotto, brand;
- differenze tra il registro del cliente e HubSpot;
- domande AEO dei pillar che non somigliano a nessun prompt, candidate a diventarlo.
"""
import argparse
import datetime as dt
import difflib
import json
import re
import sys
from collections import Counter
from pathlib import Path

FASI = ["AWARENESS", "CONSIDERATION", "EVALUATION", "DECISION"]


def cartelle_con_data(radice):
    if not radice.is_dir():
        return []
    return sorted(d for d in radice.iterdir() if d.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.name))


def cerca(oggetto, chiave):
    """Primo valore di `chiave` trovato in profondità."""
    if isinstance(oggetto, dict):
        if chiave in oggetto:
            return oggetto[chiave]
        for v in oggetto.values():
            r = cerca(v, chiave)
            if r is not None:
                return r
    elif isinstance(oggetto, list):
        for v in oggetto:
            r = cerca(v, chiave)
            if r is not None:
                return r
    return None


def leggi_estrazione(cartella):
    metriche = json.loads((cartella / "metriche.json").read_text(encoding="utf-8"))
    prompt_sez = cerca(metriche, "prompts")
    prompts = prompt_sez.get("prompts", []) if isinstance(prompt_sez, dict) else (prompt_sez or [])
    dettagli = {}
    for f in (cartella / "prompt").glob("*.json") if (cartella / "prompt").is_dir() else []:
        try:
            dettagli[f.stem] = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return {
        "metriche": metriche,
        "prompts": prompts,
        "limiti": cerca(metriche, "limits") or {},
        "marchi": (cerca(metriche, "competitors") or {}).get("brands", []),
        "icp": cerca(metriche, "icps"),
        "prodotti": cerca(metriche, "products"),
        "dettagli": dettagli,
    }


def norm(t):
    t = re.sub(r"[^\w\s]", " ", (t or "").lower())
    return re.sub(r"\s+", " ", t).strip()


def simile(a, b):
    return difflib.SequenceMatcher(None, norm(a), norm(b)).ratio()


def leggi_registro(percorso):
    """Righe della tabella del registro: dizionari per nome di colonna."""
    if not percorso.exists():
        return []
    righe, intestazione = [], None
    for riga in percorso.read_text(encoding="utf-8").splitlines():
        if not riga.startswith("|"):
            intestazione = None if not righe and intestazione is None else intestazione
            continue
        celle = [c.strip() for c in riga.strip().strip("|").split("|")]
        if intestazione is None:
            intestazione = [c.lower() for c in celle]
            continue
        if set("".join(celle)) <= set("-: "):
            continue
        righe.append(dict(zip(intestazione, celle)))
    return righe


def domande_aeo(cartella_pillar):
    out = []
    for f in sorted(cartella_pillar.glob("*/domande-aeo.md")):
        sezione = ""
        for riga in f.read_text(encoding="utf-8").splitlines():
            if riga.startswith("## "):
                sezione = riga[3:].split(":")[0].strip()
            m = re.match(r"\|\s*(\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|\s*([^|]*?)\s*\|", riga)
            if m and "esclus" not in sezione.lower():
                out.append({"pillar": f.parent.name, "n": m.group(1), "domanda": m.group(2),
                            "persona": m.group(3), "cluster": m.group(4), "sezione": sezione})
    return out


def giorni_da(ms):
    if not ms:
        return None
    return (dt.datetime.now(dt.timezone.utc) - dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc)).days


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hubspot", default="raw/hubspot-aeo")
    ap.add_argument("--registro", default="analisi/prompt-aeo/registro.md")
    ap.add_argument("--pillar", default="05-content-pillars")
    ap.add_argument("--min-giorni", type=int, default=60)
    ap.add_argument("--dominio", default="")
    a = ap.parse_args()

    cartelle = cartelle_con_data(Path(a.hubspot))
    if not cartelle:
        sys.exit(f"Nessuna estrazione in {a.hubspot}: lancia prima ie-aeo-hubspot-aeo.")
    ora = leggi_estrazione(cartelle[-1])
    prima = leggi_estrazione(cartelle[-2]) if len(cartelle) > 1 else None
    vis_prima = {p.get("id"): p.get("visibility") for p in (prima["prompts"] if prima else [])}
    dominio = a.dominio or next((m.get("domain") for m in ora["marchi"] if m.get("domain")), "")

    lim = ora["limiti"]
    tracciati = [p for p in ora["prompts"] if p.get("trackingStatus", "TRACKED") == "TRACKED"]
    print(f"# Stato dei prompt HubSpot AEO\n")
    print(f"Estrazione: `{cartelle[-1]}`" + (f", confronto con `{cartelle[-2].name}`" if prima else ", nessuna estrazione precedente") + ".")
    if dominio:
        print(f"Dominio del cliente per le citazioni: `{dominio}`.")
    print(f"\n## Capacità\n")
    print(f"- Prompt usati: {lim.get('promptsUsed', '?')} su {lim.get('promptsCapacity', '?')}")
    print(f"- A crediti: {'sì, ogni prompt nuovo consuma crediti' if lim.get('onCredits') else 'no'}")
    if lim.get("managePromptsUrl"):
        print(f"- Gestione nel portale: {lim['managePromptsUrl']}")
    print(f"- Prompt tracciati nell'estrazione: {len(tracciati)}")

    print(f"\n## Rendimento dei prompt tracciati\n")
    print("| ID | Prompt | Fase | Lingua/paese | Brand | Età (giorni) | Risposte | Visibilità | Prima | Menzioni | Citazioni | Del cliente | Segnalazioni |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for p in sorted(tracciati, key=lambda x: (x.get("visibility") or 0)):
        pid = p.get("id")
        det = ora["dettagli"].get(str(pid), {})
        urls = [u for r in det.get("runSummaries", []) for u in (r.get("citationUrls") or [])]
        del_cliente = sum(1 for u in urls if dominio and dominio in u) if dominio else "?"
        eta = giorni_da(p.get("createdAt"))
        segn = []
        if eta is not None and eta < a.min_giorni:
            segn.append(f"meno di {a.min_giorni} giorni: troppo presto per giudicarlo")
        if not p.get("responseCount"):
            segn.append("nessuna risposta nel periodo")
        if not p.get("icpIds") or not p.get("productIds"):
            segn.append("senza ICP o prodotto")
        print(f"| {pid} | {p.get('prompt', '')} | {p.get('buyingJourneyPhase', '')} | {p.get('language', '')}/{p.get('location', '')} "
              f"| {p.get('brandType', '')} | {eta if eta is not None else '?'} | {p.get('responseCount', 0)} | {p.get('visibility', 0)} "
              f"| {vis_prima.get(pid, '-')} | {p.get('mentionCount', 0)} | {p.get('citationCount', 0)} | {del_cliente} | {'; '.join(segn)} |")

    print(f"\n## Copertura\n")
    for nome, chiave in [("Fase", "buyingJourneyPhase"), ("Lingua", "language"), ("Paese", "location"), ("Brand", "brandType")]:
        c = Counter(p.get(chiave) or "?" for p in tracciati)
        if nome == "Fase":
            voci = ", ".join(f"{f} {c.get(f, 0)}" for f in FASI)
        else:
            voci = ", ".join(f"{k} {v}" for k, v in c.most_common())
        print(f"- **{nome}:** {voci or 'nessuno'}")
    for nome, chiave in [("ICP", "icpNames"), ("Prodotto", "productNames")]:
        c = Counter(n for p in tracciati for n in (p.get(chiave) or ["(nessuno)"]))
        print(f"- **{nome}:** " + (", ".join(f"{k} {v}" for k, v in c.most_common(15)) or "nessuno"))
    if ora["icp"] is not None or ora["prodotti"] is not None:
        print(f"- **Profilo HubSpot:** {len(ora['icp'] or [])} ICP e {len(ora['prodotti'] or [])} prodotti definiti")
    else:
        print("- **Profilo HubSpot:** ICP e prodotti non salvati nell'estrazione (sezione ICPS_AND_PRODUCTS)")

    registro = leggi_registro(Path(a.registro))
    print(f"\n## Registro e HubSpot\n")
    if not registro:
        print(f"Nessun registro in `{a.registro}`: alla prima revisione si crea.")
    else:
        ids_hs = {str(p.get("id")) for p in tracciati}
        id_col = next((k for k in registro[0] if k.startswith("id")), None)
        stati = Counter(r.get("stato", "?") for r in registro)
        print("- Stati nel registro: " + ", ".join(f"{k} {v}" for k, v in stati.most_common()))
        ids_reg = {r.get(id_col, "") for r in registro} if id_col else set()
        fuori = [p for p in tracciati if str(p.get("id")) not in ids_reg]
        for p in fuori:
            print(f"- Tracciato in HubSpot ma assente dal registro: {p.get('id')} \"{p.get('prompt')}\"")
        for r in registro:
            if r.get("stato") == "tracciato" and id_col and r.get(id_col) not in ids_hs:
                print(f"- Nel registro come tracciato ma non in HubSpot: {r.get(id_col)} \"{r.get('prompt')}\"")
            if r.get("stato") == "da-togliere" and id_col and r.get(id_col) in ids_hs:
                print(f"- Da togliere, ancora tracciato in HubSpot: {r.get(id_col)} \"{r.get('prompt')}\"")

    domande = domande_aeo(Path(a.pillar))
    testi = [p.get("prompt", "") for p in tracciati] + [r.get("prompt", "") for r in registro]
    libere = [d for d in domande if not any(simile(d["domanda"], t) >= 0.75 for t in testi if t)]
    print(f"\n## Domande AEO non ancora tracciate\n")
    if not domande:
        print(f"Nessuna tabella di domande in `{a.pillar}/*/domande-aeo.md`.")
    else:
        print(f"{len(libere)} su {len(domande)} domande dei pillar non somigliano a nessun prompt tracciato o del registro.\n")
        print("| Pillar | # | Sezione | Domanda | Persona | Cluster |")
        print("|---|---|---|---|---|---|")
        for d in libere:
            print(f"| {d['pillar']} | {d['n']} | {d['sezione']} | {d['domanda']} | {d['persona']} | {d['cluster']} |")


if __name__ == "__main__":
    main()
