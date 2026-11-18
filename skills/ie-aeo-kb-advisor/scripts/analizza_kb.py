#!/usr/bin/env python3
"""Segnali per l'analisi della knowledge base di un cliente: cosa c'è, quanto è solida, cosa manca.

Uso, dalla radice del repo del cliente:
    python3 -I analizza_kb.py [--json segnali.json] [--precedente analisi/kb-advisor/AAAA-MM-GG.json]

Stampa, e con --json salva:
- struttura: file previsti dalla struttura IE-AEO che mancano o sono quasi vuoti;
- aree: per area (azienda, audience, offerta, brand voice, ogni pillar) parole, citazioni,
  [DA VALIDARE], [DA RACCOGLIERE], domande aperte collegate, file validati, e il livello con i criteri;
- fonti: codici del registro mai citati, citati ma non registrati, fonti non lette,
  materiali non analizzati per priorità, data delle fonti più recenti per tipo;
- domande: aperte, per area, riferimenti rotti, incoerenze senza domanda;
- domanda reale: ricerche di Search Console e pagine con visite AI di GA4, con la copertura
  dei loro termini nella knowledge base (un indizio da giudicare, non una prova: le parole
  in un'altra lingua non si trovano);
- contenuti: segnaposto [DATO DA FORNIRE] nei contenuti non pubblicati;
- con --precedente, le voci del piano precedente per controllarne l'avanzamento.
Non scrive nella knowledge base.
"""
import argparse
import csv
import datetime as dt
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ie-aeo-rispondi-a-domande-aperte" / "scripts"))
import stato_domande as sd  # noqa: E402

PREFISSI = "SDMCERGXHA"
RX_CITAZIONE = re.compile(rf"\[([{PREFISSI}]\d{{2,3}}\b[^\]]*)\]")
RX_CODICE = re.compile(rf"\b[{PREFISSI}]\d{{2,3}}\b")
RX_REGISTRO = re.compile(rf"^\|\s*`?([{PREFISSI}]\d{{2,3}})`?\s*\|(.*)$", re.M)
AREE_KB = ("01-azienda", "02-audience", "03-offerta", "04-brand-voice", "05-content-pillars")
PREVISTI = [
    "01-azienda/profilo.md", "01-azienda/posizionamento.md", "01-azienda/mercato-e-competitor.md",
    "02-audience/icp.md", "02-audience/personas/*.md",
    "03-offerta/panoramica.md", "03-offerta/prodotti/*.md", "03-offerta/servizi.md", "03-offerta/tecnologie.md",
    "04-brand-voice/tone-of-voice.md", "04-brand-voice/messaggi-chiave.md", "04-brand-voice/glossario.md",
    "04-brand-voice/esempi/*.md",
    "05-content-pillars/*/pillar.md", "05-content-pillars/*/topic-cluster.md",
    "05-content-pillars/*/domande-aeo.md", "05-content-pillars/*/dati-e-fonti.md",
    "fonti/registro-fonti.md", "fonti/incoerenze-cliente-sito.md", "fonti/materiali-non-analizzati.md",
    "domande-aperte.md",
]
PAROLE_MINIME = 150
STOP = set("""della delle degli dello dell nella nelle negli come cosa quale quali quanto sono with from that this what
which your have does that para como para pour avec dans sont mehr eine oder und für""".split())


def leggi(f):
    try:
        return f.read_text(encoding="utf-8")
    except OSError:
        return ""


def corpo(testo):
    return re.sub(r"\A---\n.*?\n---\n", "", testo, flags=re.S)


def parole(testo):
    return len(re.findall(r"\w+", corpo(testo)))


def area_di(rel):
    p = rel.split("/")
    if p[0] == "05-content-pillars" and len(p) > 2:
        return f"05-content-pillars/{p[1]}"
    return p[0] if p[0] in AREE_KB else None


def file_kb(radice):
    for a in AREE_KB:
        for f in sorted((radice / a).rglob("*.md")):
            rel = f.relative_to(radice).as_posix()
            if f.name != "README.md":
                yield rel, f


def ultima(radice, cartella):
    p = radice / cartella
    if not p.is_dir():
        return None
    d = sorted(x for x in p.iterdir() if x.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", x.name))
    return d[-1] if d else None


def leggi_csv(f):
    if not f or not f.exists():
        return []
    with f.open(newline="", encoding="utf-8-sig") as h:
        return list(csv.DictReader(h))


def num(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def termini(testo):
    return [w for w in re.findall(r"[a-zà-ü0-9]+", testo.lower()) if len(w) >= 4 and w not in STOP]


def copertura(t, testo_kb):
    ts = termini(t)
    if not ts:
        return None
    return sum(1 for w in ts if w in testo_kb) / len(ts)


def struttura(radice):
    mancanti, vuoti = [], []
    for p in PREVISTI:
        trovati = [f for f in radice.glob(p) if f.name != "README.md"]
        if not trovati:
            mancanti.append(p)
        for f in trovati:
            if parole(leggi(f)) < PAROLE_MINIME:
                vuoti.append(f.relative_to(radice).as_posix())
    return {"mancanti": mancanti, "quasi_vuoti": sorted(set(vuoti)), "soglia_parole": PAROLE_MINIME}


def domande_per_file(radice):
    """{file: [numeri delle domande aperte]} dai link della colonna 'File interessato' e dalle citazioni."""
    f = radice / "domande-aperte.md"
    if not f.exists():
        return None, {}, {}, []
    d = sd.Domande(f)
    cit = sd.citazioni(radice, "domande-aperte.md")
    per_file = defaultdict(set)
    for n, v in d.aperte.items():
        for p in sd.RX_LINK.findall(d.campo(v, "file")):
            per_file[p.lstrip("./")].add(n)
        for rel, _, _ in cit.get(n, []):
            per_file[rel].add(n)
    return d, per_file, cit, sd.incoerenze(radice)


def aree(radice, per_file, oggi):
    dati = defaultdict(lambda: Counter())
    elenco = defaultdict(list)
    for rel, f in file_kb(radice):
        a = area_di(rel)
        t = leggi(f)
        fm = sd.frontmatter(t)
        c = corpo(t)
        p = parole(t)
        cit = len(RX_CITAZIONE.findall(c))
        dv = c.count("DA VALIDARE")
        dr = c.count("DA RACCOGLIERE")
        dom = len(per_file.get(rel, ()))
        agg = fm.get("ultimo_aggiornamento", "")
        try:
            giorni = (oggi - dt.date.fromisoformat(agg)).days
        except ValueError:
            giorni = None
        x = dati[a]
        x["file"] += 1
        x["parole"] += p
        x["citazioni"] += cit
        x["da_validare"] += dv
        x["da_raccogliere"] += dr
        x["domande"] += dom
        x["validati"] += fm.get("stato") == "validato"
        elenco[a].append({"file": rel, "stato": fm.get("stato", ""), "parole": p, "citazioni": cit,
                          "citazioni_100_parole": round(cit * 100 / p, 1) if p else 0, "da_validare": dv, "da_raccogliere": dr,
                          "domande_aperte": sorted(per_file.get(rel, ())), "giorni_da_aggiornamento": giorni})
    out = []
    for a in sorted(dati):
        x = dati[a]
        poco_fonti = [e["file"] for e in elenco[a] if e["parole"] >= PAROLE_MINIME and e["citazioni_100_parole"] < 0.5]
        incerti = (x["da_validare"] + x["da_raccogliere"] + x["domande"]) / x["file"]
        if x["parole"] < 300 or x["citazioni"] == 0:
            livello, perche = "scoperta", "meno di 300 parole o nessuna fonte citata"
        elif incerti >= 2 or poco_fonti:
            livello = "parziale"
            perche = "; ".join(filter(None, [
                f"{incerti:.1f} tra [DA VALIDARE], [DA RACCOGLIERE] e domande aperte per file" if incerti >= 2 else "",
                f"file con meno di una citazione ogni 200 parole: {', '.join(poco_fonti)}" if poco_fonti else ""]))
        else:
            livello, perche = "solida", "fonti citate, pochi punti da validare"
        out.append({"area": a, "livello": livello, "perche": perche, "file": x["file"], "parole": x["parole"],
                    "citazioni": x["citazioni"], "da_validare": x["da_validare"], "da_raccogliere": x["da_raccogliere"], "domande_aperte": x["domande"],
                    "validati_dal_cliente": x["validati"], "dettaglio": elenco[a]})
    return out


def fonti(radice, oggi):
    reg = leggi(radice / "fonti" / "registro-fonti.md")
    registrati = {}
    for codice, resto in RX_REGISTRO.findall(reg):
        celle = [c.strip() for c in resto.split("|")]
        registrati[codice] = celle
    citati = Counter()
    for rel, f in [*file_kb(radice), *[(p.relative_to(radice).as_posix(), p) for p in (radice / "contenuti").rglob("*.md")],
                   *[(p.relative_to(radice).as_posix(), p) for p in (radice / "analisi").rglob("*.md")],
                   *[(n, radice / n) for n in ("domande-aperte.md", "fonti/incoerenze-cliente-sito.md")]]:
        for g in RX_CITAZIONE.findall(corpo(leggi(f))):
            for c in RX_CODICE.findall(g):
                citati[c] += 1
    non_lette = [{"codice": c, "descrizione": " | ".join(v)[:220]} for c, v in registrati.items()
                 if re.search(r"non (ancora )?lett|non letto|troppo grande", " ".join(v), re.I)]
    date_tipo = {}
    for c, v in registrati.items():
        for cella in v:
            m = re.search(r"\d{4}-\d{2}-\d{2}", cella)
            if m:
                date_tipo.setdefault(c[0], []).append(m.group())
                break
    materiali = Counter()
    righe_materiali = []
    for r in sd_tabelle(leggi(radice / "fonti" / "materiali-non-analizzati.md")):
        pr = next((v for k, v in r.items() if "priorit" in k), "")
        materiali[pr or "-"] += 1
        righe_materiali.append({k: v for k, v in r.items()})
    return {
        "registrati": len(registrati),
        "per_tipo": dict(Counter(c[0] for c in registrati)),
        "fonte_piu_recente_per_tipo": {k: max(v) for k, v in sorted(date_tipo.items())},
        "mai_citati": sorted(c for c in registrati if not citati[c]),
        "citati_non_registrati": sorted(c for c in citati if c not in registrati),
        "non_lette": non_lette,
        "materiali_non_analizzati": dict(materiali),
        "materiali_righe": righe_materiali[:40],
    }


def sd_tabelle(testo):
    righe, testa = [], None
    for r in testo.splitlines():
        if not r.startswith("|"):
            testa = None
            continue
        c = sd.celle(r)
        if testa is None:
            testa = [x.lower() for x in c]
        elif not sd.separatore(r):
            righe.append(dict(zip(testa, c)))
    return righe


def maiuscola(t):
    return t[:1].upper() + t[1:]


def domande(d, per_file, cit, inc):
    if d is None:
        return {"presente": False}
    per_area = Counter()
    for f, ns in per_file.items():
        a = area_di(f) or f.split("/")[0]
        per_area[a] += len(ns)
    rotti = [{"file": rel, "riga": i, "domanda": n, "stato": "risolta" if n in d.risolte else "non esiste"}
             for n, righe in cit.items() if n not in d.aperte for rel, i, _ in righe]
    return {"presente": True, "aperte": len(d.aperte), "risolte": len(d.risolte),
            "per_area": dict(per_area.most_common()), "riferimenti_rotti": rotti,
            "incoerenze_senza_domanda": [{"numero": x[0], "tema": x[1], "gravita": x[2]} for x in inc if "nuova" in x[3].lower()],
            "per_chi": dict(Counter(maiuscola(re.split(r"\s*/\s*", d.campo(v, "chi") or "non indicato")[0]) for v in d.aperte.values()).most_common())}


def domanda_reale(radice, testo_kb, righe):
    out = {}
    marchi = []
    conf = radice / "analisi" / "search-console" / "config.json"
    if conf.exists():
        try:
            marchi = [m.lower() for m in json.loads(leggi(conf)).get("brand", [])]
        except ValueError:
            pass
    g = ultima(radice, "raw/gsc")
    if g:
        q = [r for r in leggi_csv(g / "query.csv") or leggi_csv(g / "opportunita.csv")
             if not any(m in r.get("query", "").lower() for m in marchi)]
        q.sort(key=lambda r: -num(r.get("impressioni")))
        out["search_console"] = {"estrazione": g.name, "query": [
            {"query": r["query"], "impressioni": int(num(r.get("impressioni"))), "click": int(num(r.get("click"))),
             "copertura_kb": copertura(r["query"], testo_kb)} for r in q[:righe]]}
        dom = [r for r in leggi_csv(g / "opportunita.csv") if r.get("domanda") == "sì"]
        dom.sort(key=lambda r: -num(r.get("impressioni")))
        out["search_console"]["domande"] = [
            {"query": r["query"], "impressioni": int(num(r.get("impressioni"))), "copertura_kb": copertura(r["query"], testo_kb)}
            for r in dom[:righe]]
    a = ultima(radice, "raw/ga4")
    if a:
        per = Counter()
        for r in leggi_csv(a / "ai_pagine.csv"):
            pag = r.get("pagina", "")
            if pag and pag != "(not set)" and not re.fullmatch(r"/?([a-z]{2}(-[a-z]{2})?)?/?", pag):
                per[pag] += num(r.get("sessioni"))
        out["ga4"] = {"estrazione": a.name, "pagine": [
            {"pagina": p, "sessioni_ai": int(s), "copertura_kb": copertura(p.replace("-", " ").replace("/", " "), testo_kb)}
            for p, s in per.most_common(righe)]}
    h = ultima(radice, "raw/hubspot-aeo")
    if h and (h / "raccomandazioni.json").exists():
        try:
            dati = json.loads(leggi(h / "raccomandazioni.json"))
            rec = []
            for blocco in dati if isinstance(dati, list) else [dati]:
                rec += (blocco.get("risposta") or {}).get("recommendations", [])
            # Le raccomandazioni tecniche (schema, titoli, velocità) non dicono nulla sulla knowledge base
            rec = [r for r in rec if r.get("type") == "CONTENT" or r.get("actionCategory") == "CREATE_CONTENT"]
            out["hubspot_aeo"] = {"estrazione": h.name, "raccomandazioni": [
                {"titolo": r.get("title"), "priorita": r.get("priority"), "stato": r.get("status"),
                 "copertura_kb": copertura(r.get("title", ""), testo_kb)} for r in rec]}
        except ValueError:
            pass
    return out


def da_raccogliere(radice):
    """Le informazioni che mancano del tutto, marcate [DA RACCOGLIERE: ...], con file e riga."""
    out = []
    for rel, f in file_kb(radice):
        for i, r in enumerate(corpo(leggi(f)).splitlines(), 1):
            for m in re.finditer(r"\[DA RACCOGLIERE:?\s*([^\]]*)\]", r):
                out.append({"file": rel, "testo": m.group(1).strip() or r.strip()[:160]})
    return out


def contenuti(radice):
    out = []
    for f in sorted((radice / "contenuti").rglob("*.md")):
        t = leggi(f)
        n = t.count("DATO DA FORNIRE")
        st = sd.frontmatter(t).get("stato", "")
        if n and st not in sd.CONCLUSI:
            out.append({"file": f.relative_to(radice).as_posix(), "stato": st, "segnaposto": n})
    return out


def analisi(radice):
    out = {}
    cartella = radice / "analisi"
    if cartella.is_dir():
        for c in sorted(x for x in cartella.iterdir() if x.is_dir()):
            date = sorted(f.stem for f in c.glob("*.md") if re.fullmatch(r"\d{4}-\d{2}-\d{2}", f.stem))
            out[c.name] = date[-1] if date else ("config" if (c / "config.json").exists() else "")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", help="salva i segnali in questo file")
    ap.add_argument("--precedente", help="JSON del report precedente, per l'avanzamento del piano")
    ap.add_argument("--righe", type=int, default=25)
    a = ap.parse_args()
    radice = Path(".").resolve()
    if not (radice / "01-azienda").is_dir():
        sys.exit("Lancia lo script dalla radice del repo della knowledge base del cliente.")
    oggi = dt.date.today()
    testo_kb = " ".join(corpo(leggi(f)).lower() for _, f in file_kb(radice))
    d, per_file, cit, inc = domande_per_file(radice)
    segnali = {
        "data": oggi.isoformat(),
        "struttura": struttura(radice),
        "aree": aree(radice, per_file, oggi),
        "fonti": fonti(radice, oggi),
        "domande": domande(d, per_file, cit, inc),
        "domanda_reale": domanda_reale(radice, testo_kb, a.righe),
        "da_raccogliere": da_raccogliere(radice),
        "contenuti_con_segnaposto": contenuti(radice),
        "analisi_disponibili": analisi(radice),
    }
    if a.precedente:
        prec = json.loads(Path(a.precedente).read_text(encoding="utf-8"))
        segnali["piano_precedente"] = {"data": prec.get("data"), "voci": prec.get("piano", [])}
    if a.json:
        Path(a.json).write_text(json.dumps(segnali, ensure_ascii=False, indent=1), encoding="utf-8")
    stampa(segnali)


def pct(x):
    return "-" if x is None else f"{x * 100:.0f}%"


def stampa(s):
    print(f"# Segnali della knowledge base ({s['data']})\n")
    st = s["struttura"]
    print("## Struttura\n")
    print(f"- File previsti mancanti: {', '.join(st['mancanti']) or 'nessuno'}")
    print(f"- File sotto {st['soglia_parole']} parole: {', '.join(st['quasi_vuoti']) or 'nessuno'}")
    print("\n## Aree\n")
    print("Livello: scoperta = meno di 300 parole o nessuna fonte; parziale = almeno 2 tra [DA VALIDARE], [DA RACCOGLIERE] e domande aperte "
          "per file, o un file con meno di una citazione ogni 200 parole; solida = il resto.\n")
    print("| Area | Livello | File | Parole | Citazioni | DA VALIDARE | DA RACCOGLIERE | Domande aperte | Validati | Perché |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for x in s["aree"]:
        print(f"| {x['area']} | {x['livello']} | {x['file']} | {x['parole']} | {x['citazioni']} | {x['da_validare']} | {x['da_raccogliere']} | "
              f"{x['domande_aperte']} | {x['validati_dal_cliente']}/{x['file']} | {x['perche']} |")
    f = s["fonti"]
    print("\n## Fonti\n")
    print(f"- Registrate: {f['registrati']} ({', '.join(f'{k} {v}' for k, v in f['per_tipo'].items())})")
    print(f"- Data più recente per tipo: {', '.join(f'{k} {v}' for k, v in f['fonte_piu_recente_per_tipo'].items())}")
    print(f"- Mai citate: {', '.join(f['mai_citati']) or 'nessuna'}")
    print(f"- Citate ma non registrate: {', '.join(f['citati_non_registrati']) or 'nessuna'}")
    for x in f["non_lette"]:
        print(f"- Non letta: {x['codice']}: {x['descrizione']}")
    print(f"- Materiali non analizzati per priorità: {', '.join(f'{k} {v}' for k, v in f['materiali_non_analizzati'].items()) or 'nessuno'}")
    d = s["domande"]
    print("\n## Domande aperte\n")
    if not d.get("presente"):
        print("Manca domande-aperte.md.")
    else:
        print(f"- {d['aperte']} aperte, {d['risolte']} risolte")
        print(f"- Per area: {', '.join(f'{k} {v}' for k, v in d['per_area'].items())}")
        print(f"- Per chi può rispondere: {', '.join(f'{k} {v}' for k, v in d['per_chi'].items())}")
        for x in d["riferimenti_rotti"]:
            print(f"- {x['file']}:{x['riga']} cita la domanda {x['domanda']}, che {x['stato']}")
        if d["incoerenze_senza_domanda"]:
            print(f"- Incoerenze senza domanda: {', '.join(x['numero'] + ' (' + x['gravita'] + ')' for x in d['incoerenze_senza_domanda'])}")
    r = s["domanda_reale"]
    print("\n## Domanda reale e copertura nella knowledge base\n")
    print("Copertura = quota dei termini (4+ lettere) trovati nel testo della knowledge base. Bassa non vuol dire "
          "per forza scoperta: le ricerche in altre lingue non si trovano. Va giudicata.\n")
    if "search_console" in r:
        g = r["search_console"]
        print(f"### Search Console ({g['estrazione']}), ricerche senza marchio per impressioni\n")
        for x in g["query"]:
            print(f"- {x['query']}: {x['impressioni']} impressioni, {x['click']} click, copertura {pct(x['copertura_kb'])}")
        if g["domande"]:
            print("\nDomande:")
            for x in g["domande"]:
                print(f"- {x['query']}: {x['impressioni']} impressioni, copertura {pct(x['copertura_kb'])}")
    if "ga4" in r:
        print(f"\n### GA4 ({r['ga4']['estrazione']}), pagine di arrivo dagli assistenti AI\n")
        for x in r["ga4"]["pagine"]:
            print(f"- {x['pagina']}: {x['sessioni_ai']} sessioni AI, copertura {pct(x['copertura_kb'])}")
    if "hubspot_aeo" in r:
        print(f"\n### HubSpot AEO ({r['hubspot_aeo']['estrazione']}), raccomandazioni\n")
        for x in r["hubspot_aeo"]["raccomandazioni"]:
            print(f"- [{x['priorita']}, {x['stato']}] {x['titolo']}: copertura {pct(x['copertura_kb'])}")
    print(f"\n## Informazioni da raccogliere ({len(s['da_raccogliere'])})\n")
    for x in s["da_raccogliere"]:
        print(f"- {x['file']}: {x['testo'][:160]}")
    print("\n## Contenuti con [DATO DA FORNIRE]\n")
    for x in s["contenuti_con_segnaposto"]:
        print(f"- {x['file']} ({x['stato']}): {x['segnaposto']}")
    if not s["contenuti_con_segnaposto"]:
        print("Nessuno.")
    print("\n## Analisi disponibili (ultimo report)\n")
    print(", ".join(f"{k} {v}" for k, v in s["analisi_disponibili"].items()) or "Nessuna.")
    if "piano_precedente" in s:
        p = s["piano_precedente"]
        print(f"\n## Piano precedente ({p['data']}): {len(p['voci'])} voci da verificare\n")
        for v in p["voci"]:
            print(f"- {v.get('id')}: {v.get('azione')} ({v.get('chi')}, {v.get('stato', 'da fare')})")


if __name__ == "__main__":
    main()
