#!/usr/bin/env python3
"""Prepara un contenuto del repo per il caricamento in HubSpot come bozza.

Uso, dalla radice del repo del cliente:
    python3 -I prepara_pubblicazione.py <contenuti/.../file.md> --out <file.json> [--html <file.html>]

Dal file Markdown di un contenuto (formato di condivisi/archivio-contenuti.md) ricava:
- titolo (H1), corpo in HTML (dal titolo alle sezioni di servizio, H1 escluso), FAQ;
- meta title, meta description, slug, categoria, dalla tabella "Metadati per il CMS" o dal frontmatter;
- il JSON-LD del blocco ```json della sezione "Schema.org";
- lingua, stato, URL e tipo dal frontmatter.

Controlla ciò che impedisce il caricamento: stato non approvato, segnaposto rimasti
([DATO DA FORNIRE], [DA CONFERMARE], [DA VALIDARE]), JSON-LD non valido, FAQ diverse dallo schema,
meta title e description troppo lunghi. Scrive il pacchetto in --out (fuori dal repo) e stampa
un riepilogo. Non chiama HubSpot. Esce con codice 1 se c'è un blocco.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

FINE = ("metadati", "schema.org", "fonti", "note per", "brief", "report prima", "analisi e piano",
        "punti mancanti", "domande aperte che pesano", "cosa migliorare", "cms metadata", "sources",
        "review notes", "translation notes", "note di traduzione", "pubblicazione in hubspot")
FAQ = ("domande frequenti", "faq", "frequently asked questions")
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


def sezioni(testo):
    """Parte pubblicabile (righe) e sezioni di servizio {titolo minuscolo: testo}."""
    pub, servizio, corrente, dentro = [], {}, None, False
    for r in testo.splitlines():
        if r.startswith("# ") and not dentro:
            dentro = True
        if r.startswith("## ") and r[3:].strip().lower().startswith(FINE):
            corrente = r[3:].strip().lower()
            servizio[corrente] = []
            continue
        if corrente:
            if r.startswith("## "):
                corrente = None if not r[3:].strip().lower().startswith(FINE) else r[3:].strip().lower()
                if corrente:
                    servizio[corrente] = []
                continue
            servizio[corrente].append(r)
        elif dentro:
            pub.append(r)
    return pub, {k: "\n".join(v) for k, v in servizio.items()}


def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", t)
    t = re.sub(r"(?<![\w_])_(?!\s)(.+?)(?<!\s)_(?![\w_])", r"<em>\1</em>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t


def celle(r):
    """Celle di una riga di tabella; "\\|" è una barra verticale dentro la cella."""
    r = r.strip()
    r = r[1:] if r.startswith("|") else r
    r = r[:-1] if r.endswith("|") and not r.endswith("\\|") else r
    return [c.replace("\\|", "|").strip() for c in re.split(r"(?<!\\)\|", r)]


def md_html(righe):
    out, i = [], 0
    while i < len(righe):
        r = righe[i]
        if not r.strip():
            i += 1
            continue
        m = re.match(r"(#{2,4}) (.+)", r)
        if m:
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2).strip())}</h{n}>")
            i += 1
        elif r.startswith("|"):
            blocco = []
            while i < len(righe) and righe[i].startswith("|"):
                blocco.append(righe[i])
                i += 1
            testa, corpo = celle(blocco[0]), [celle(b) for b in blocco[1:] if not set(b) <= set("|-: ")]
            t = ["<table>"]
            if any(testa):
                t.append("<thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in testa) + "</tr></thead>")
            t.append("<tbody>" + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in rr) + "</tr>" for rr in corpo) + "</tbody></table>")
            out.append("".join(t))
        elif re.match(r"\s*([-*]|\d+\.) ", r):
            ordinata = bool(re.match(r"\s*\d+\. ", r))
            voci = []
            while i < len(righe) and re.match(r"\s*([-*]|\d+\.) ", righe[i]):
                voci.append(re.sub(r"\s*([-*]|\d+\.) ", "", righe[i], count=1))
                i += 1
            tag = "ol" if ordinata else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(v)}</li>" for v in voci) + f"</{tag}>")
        elif r.startswith(">"):
            blocco = []
            while i < len(righe) and righe[i].startswith(">"):
                blocco.append(righe[i].lstrip("> ").strip())
                i += 1
            out.append("<blockquote><p>" + inline(" ".join(blocco)) + "</p></blockquote>")
        else:
            blocco = []
            while i < len(righe) and righe[i].strip() and not re.match(r"(#{1,4} |\||>|\s*([-*]|\d+\.) )", righe[i]):
                blocco.append(righe[i].strip())
                i += 1
            out.append("<p>" + inline(" ".join(blocco)) + "</p>")
    return "\n".join(out)


def metadati(testo_servizio):
    meta = {}
    for r in testo_servizio.splitlines():
        if not r.startswith("|"):
            continue
        c = celle(r)
        if len(c) < 2:
            continue
        k, v = c[0].lower(), c[1].strip()
        if k.startswith("meta title"):
            meta["meta_title"] = v
        elif k.startswith("meta description"):
            meta["meta_description"] = v
        elif k.startswith("slug"):
            meta["slug"] = v.split()[0] if v else ""
        elif k.startswith(("categoria", "category")):
            meta["categoria"] = v
    return meta


def faq_da(righe):
    testo = "\n".join(righe)
    m = re.search(r"^## (?:" + "|".join(FAQ) + r").*?$(.*?)(?=^## |\Z)", testo, re.M | re.S | re.I)
    if not m:
        return []
    out = []
    for b in re.split(r"^### +", m.group(1), flags=re.M)[1:]:
        q, _, a = b.strip().partition("\n")
        out.append({"domanda": q.strip(), "risposta": " ".join(a.split())})
    return out


def norm(t):
    t = re.sub(r"[*_`]", "", t)
    t = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--out", required=True)
    ap.add_argument("--html", default="")
    a = ap.parse_args()

    testo = Path(a.file).read_text(encoding="utf-8")
    fm = frontmatter(testo)
    pub, servizio = sezioni(testo)
    if not pub:
        sys.exit("Non trovo il titolo H1 del contenuto.")
    h1 = pub[0][2:].strip()
    corpo = pub[1:]
    meta = metadati(next((v for k, v in servizio.items() if k.startswith(("metadati", "cms metadata"))), ""))
    jsonld, errore_json = None, None
    sch = next((v for k, v in servizio.items() if k.startswith("schema.org")), "")
    mj = re.search(r"```json\s*(.*?)```", sch, re.S)
    if mj:
        try:
            jsonld = json.loads(mj.group(1))
        except json.JSONDecodeError as e:
            errore_json = str(e)
    faq = faq_da(corpo)

    blocchi, avvisi = [], []
    if fm.get("stato") not in ("approvato", "pubblicato"):
        blocchi.append(f"stato '{fm.get('stato', '?')}': si carica solo un contenuto approvato")
    corpo_testo = "\n".join(pub)
    for dove, t in [("testo", corpo_testo), ("metadati", json.dumps(meta, ensure_ascii=False)),
                    ("JSON-LD", mj.group(1) if mj else "")]:
        s = SEGNAPOSTO.findall(t)
        if s:
            blocchi.append(f"{len(s)} segnaposto nel {dove}")
    if errore_json:
        blocchi.append(f"JSON-LD non valido: {errore_json}")
    if not mj:
        avvisi.append("nessun JSON-LD nella sezione Schema.org")
    if jsonld and faq:
        nodi = jsonld.get("@graph", [jsonld]) if isinstance(jsonld, dict) else jsonld
        fp = next((n for n in nodi if n.get("@type") == "FAQPage"), None)
        if fp:
            s = [(norm(q["name"]), norm(q["acceptedAnswer"]["text"])) for q in fp.get("mainEntity", [])]
            if s != [(norm(f["domanda"]), norm(f["risposta"])) for f in faq]:
                blocchi.append("FAQ del testo e FAQPage dello schema non coincidono")
    mt, md = meta.get("meta_title", ""), meta.get("meta_description", "")
    if not mt:
        avvisi.append("meta title assente")
    elif len(mt) > 60:
        avvisi.append(f"meta title di {len(mt)} caratteri (consigliati al massimo 60)")
    if not md:
        avvisi.append("meta description assente: in HubSpot serve per pubblicare un blog post")
    elif len(md) > 155:
        avvisi.append(f"meta description di {len(md)} caratteri (consigliati al massimo 155)")

    corpo_html = md_html(corpo)
    pacchetto = {
        "file": a.file,
        "tipo": fm.get("tipo", ""),
        "stato": fm.get("stato", ""),
        "lingua": fm.get("lingua", ""),
        "url": fm.get("url", ""),
        "traduzione_di": fm.get("traduzione_di", ""),
        "titolo": h1,
        "meta_title": mt,
        "meta_description": md,
        "slug": meta.get("slug") or fm.get("slug", ""),
        "categoria": meta.get("categoria") or fm.get("categoria", ""),
        "corpo_html": corpo_html,
        "faq": faq,
        "jsonld": jsonld,
        "head_html": ('<script type="application/ld+json">' + json.dumps(jsonld, ensure_ascii=False) + "</script>") if jsonld else "",
        "blocchi": blocchi,
        "avvisi": avvisi,
    }
    Path(a.out).write_text(json.dumps(pacchetto, ensure_ascii=False, indent=2), encoding="utf-8")
    if a.html:
        Path(a.html).write_text(f"<h1>{inline(h1)}</h1>\n{corpo_html}\n", encoding="utf-8")

    print(f"# Pacchetto per HubSpot: {a.file}\n")
    for k in ("tipo", "stato", "lingua", "slug", "categoria", "url", "traduzione_di"):
        if pacchetto[k]:
            print(f"- **{k}:** {pacchetto[k]}")
    print(f"- **titolo:** {h1}")
    print(f"- **meta title:** {mt or '-'} ({len(mt)})")
    print(f"- **meta description:** {md or '-'} ({len(md)})")
    print(f"- **corpo:** {len(corpo_html)} caratteri di HTML, {corpo_html.count('<h2>')} H2, {len(faq)} FAQ, "
          f"{corpo_html.count('<table>')} tabelle, {corpo_html.count('<a ')} link")
    print(f"- **JSON-LD:** {'presente' if jsonld else 'assente'}")
    print(f"- **pacchetto:** {a.out}" + (f", anteprima HTML: {a.html}" if a.html else ""))
    print("\n## Blocchi\n")
    print("\n".join(f"- {b}" for b in blocchi) or "- Nessuno.")
    print("\n## Avvisi\n")
    print("\n".join(f"- {v}" for v in avvisi) or "- Nessuno.")
    sys.exit(1 if blocchi else 0)


if __name__ == "__main__":
    main()
