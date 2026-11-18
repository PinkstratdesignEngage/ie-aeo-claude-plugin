#!/usr/bin/env python3
"""Salva in raw/ahrefs/<data>/originali/ le risposte del connettore Ahrefs, così come sono arrivate.

Uso, dalla radice del repo del cliente:
    python3 -I salva_risposte.py raw/ahrefs/<AAAA-MM-GG> --dominio esempio.com
        [--dal 2026-10-28T12:00] [--sessione <file.jsonl>]

Le risposte del connettore arrivano nella conversazione, non su disco: questo script le
legge dal registro della sessione di Claude Code (~/.claude/projects/<progetto>/<sessione>.jsonl),
così nessun dato passa per una trascrizione a mano. Con --sessione si indica il file, che
serve quando si lavora in un repo diverso da quello in cui gira Claude Code.

Riconosce gli strumenti dal nome, qualunque sia l'id del server MCP, e scrive i file che
normalizza_ahrefs.py si aspetta:

    site-explorer-organic-keywords      posizioni-<paese>.json se il target è il dominio del
                                        cliente, altrimenti keyword-<paese>-<target>.json
    site-explorer-organic-competitors   competitor-<paese>.json
    site-explorer-top-pages             top-pages.json
    site-explorer-ai-responses-count    ai-risposte.json
    site-audit-issues                   site-audit-problemi.json
    site-audit-page-explorer            site-audit-pagine.json, le pagine di tutti i problemi
    site-audit-projects                 progetto.json, solo la riga del cliente

L'elenco dei progetti contiene gli altri clienti dell'agenzia: nel repo del cliente resta
solo il suo. Scrive anche unita.json, con il costo reale di ogni chiamata, che il connettore
riporta in apiUsageCosts. Le risposte troppo grandi per il contesto, che l'harness salva in
un file a parte, vengono recuperate da lì: sono le più care e non devono andare perse.
"""
import argparse
import json
import re
import sys
from pathlib import Path

STRUMENTI = {
    "site-explorer-organic-keywords": "keywords",
    "site-explorer-organic-competitors": "competitor",
    "site-explorer-top-pages": "top-pages",
    "site-explorer-ai-responses-count": "ai-risposte",
    "site-audit-issues": "site-audit-problemi",
    "site-audit-page-explorer": "site-audit-pagine",
    "site-audit-projects": "progetto",
}


def registro_predefinito():
    progetto = re.sub(r"[^A-Za-z0-9]", "-", str(Path.cwd()))
    cartella = Path.home() / ".claude" / "projects" / progetto
    file = sorted(cartella.glob("*.jsonl"), key=lambda f: f.stat().st_mtime) if cartella.is_dir() else []
    if not file:
        sys.exit(f"Nessun registro di sessione in {cartella}: indica il file con --sessione.")
    return file[-1]


def pulisci(d):
    return re.sub(r"^https?://(www\.)?", "", str(d or "").strip().lower()).split("/")[0]


RE_SALVATA = re.compile(r"saved to:?\s+(/\S+\.txt)")


def blocchi(contenuto):
    """I testi di un tool_result, che per il connettore sono più di uno.

    Una risposta troppo grande per il contesto non arriva qui: l'harness la scrive in un
    file e lascia solo il percorso. In quel caso si legge il file, che ha la stessa forma
    (un elenco di blocchi {type, text}). Senza questo le chiamate più grandi, che sono
    anche le più care, andrebbero perse.
    """
    if isinstance(contenuto, str):
        testi = [contenuto]
    elif isinstance(contenuto, list):
        testi = [b.get("text", "") for b in contenuto if isinstance(b, dict) and b.get("type") == "text"]
    else:
        return []
    fuori = []
    for x in testi:
        m = RE_SALVATA.search(x)
        if not m or len(x) > 4000:
            continue  # un testo lungo è già la risposta, non un rimando
        f = Path(m.group(1))
        if not f.exists():
            print(f"  risposta salvata fuori dal registro ma il file non c'è: {f}")
            continue
        try:
            fuori += [b.get("text", "") for b in json.loads(f.read_text(encoding="utf-8"))
                      if isinstance(b, dict) and b.get("type") == "text"]
        except (ValueError, OSError) as e:
            print(f"  non riesco a leggere {f}: {e}")
    return testi + fuori


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cartella")
    p.add_argument("--dominio", required=True, help="dominio del cliente: distingue le sue keyword da quelle dei competitor")
    p.add_argument("--dal", default="", help="considera solo le chiamate da questo istante (ISO, come nel registro)")
    p.add_argument("--sessione", help="file .jsonl del registro di sessione")
    a = p.parse_args()

    registro = Path(a.sessione) if a.sessione else registro_predefinito()
    if not registro.exists():
        sys.exit(f"Registro non trovato: {registro}")
    cliente = pulisci(a.dominio)

    chiamate, risultati = {}, {}
    for riga in open(registro, encoding="utf-8"):
        try:
            d = json.loads(riga)
        except ValueError:
            continue
        if a.dal and d.get("timestamp", "") < a.dal:
            continue
        contenuto = (d.get("message") or {}).get("content")
        if not isinstance(contenuto, list):
            continue
        for b in contenuto:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use":
                nome = b.get("name", "").rsplit("__", 1)[-1]
                if nome in STRUMENTI:
                    chiamate[b["id"]] = (nome, b.get("input") or {}, d.get("timestamp", ""))
            elif b.get("type") == "tool_result" and b.get("tool_use_id") in chiamate:
                # Una risposta troppo grande arriva marcata come errore, con il percorso del
                # file: blocchi() la recupera, quindi non si scarta per is_error
                risultati[b["tool_use_id"]] = blocchi(b.get("content"))

    uscita = Path(a.cartella) / "originali"
    uscita.mkdir(parents=True, exist_ok=True)
    pagine_audit, registro_unita, totale, scritti = [], [], 0, {}

    for uid, (nome, params, quando) in chiamate.items():
        if uid not in risultati:
            continue
        dati, costi = None, None
        for testo in risultati[uid]:
            try:
                x = json.loads(testo)
            except ValueError:
                continue  # testo di servizio, per esempio il suggerimento di rendering
            if isinstance(x, dict) and "apiUsageCosts" in x:
                costi = x["apiUsageCosts"]
            elif dati is None:
                dati = x
        reali = (costi or {}).get("units-cost-total-actual")
        totale += reali or 0
        registro_unita.append({"strumento": nome, "quando": quando, "righe": (costi or {}).get("rows"),
                               "unita_per_riga": (costi or {}).get("units-cost-row"),
                               "unita": reali, "unita_di_listino": (costi or {}).get("units-cost-total"),
                               "params": {k: v for k, v in params.items() if k != "select"}})
        if dati is None:
            continue

        paese = (params.get("country") or "xx").lower()
        target = pulisci(params.get("target"))
        if nome == "site-explorer-organic-keywords":
            file = f"posizioni-{paese}.json" if target == cliente else f"keyword-{paese}-{target}.json"
        elif nome == "site-explorer-organic-competitors":
            file = f"competitor-{paese}.json"
        elif nome == "site-audit-pagine":
            file = None
        elif nome == "site-audit-page-explorer":
            file = None
        elif nome == "progetto" or nome == "site-audit-projects":
            file = "progetto.json"
        else:
            file = STRUMENTI[nome] + ".json"

        if nome == "site-audit-page-explorer":
            # Una chiamata per problema: le pagine si accumulano in un unico file
            righe = dati.get("pages") or dati.get("data") or (dati if isinstance(dati, list) else [])
            for r in righe:
                url = r.get("url") if isinstance(r, dict) else r
                if url:
                    pagine_audit.append({"url": url, "issue_id": params.get("issue_id", "")})
            continue
        if nome == "site-audit-projects":
            elenco = dati.get("healthscores") or dati.get("projects") or (dati if isinstance(dati, list) else [])
            mio = next((x for x in elenco
                        if str(x.get("project_id")) == str(params.get("project_id"))
                        or pulisci(x.get("target_url")) == cliente), None)
            if not mio:
                print("  progetto del cliente non trovato nell'elenco: progetto.json non scritto")
                continue
            dati = mio  # nel repo del cliente non entra l'elenco degli altri clienti
        (uscita / file).write_text(json.dumps(dati, ensure_ascii=False, indent=1), encoding="utf-8")
        n = len(next((v for v in dati.values() if isinstance(v, list)), [])) if isinstance(dati, dict) else 0
        scritti[file] = n
        print(f"  {file}: {n or '—'} righe, {reali if reali is not None else '?'} unità")

    if pagine_audit:
        # I nomi dei problemi stanno in site-audit-problemi.json: si uniscono qui
        problemi = {}
        f = uscita / "site-audit-problemi.json"
        if f.exists():
            for i in json.loads(f.read_text(encoding="utf-8")).get("issues", []):
                problemi[i.get("issue_id")] = i
        for r in pagine_audit:
            i = problemi.get(r["issue_id"], {})
            r["issue"] = i.get("name", r["issue_id"])
            r["importance"] = i.get("importance", "")
            r["category"] = i.get("category", "")
        (uscita / "site-audit-pagine.json").write_text(
            json.dumps(pagine_audit, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  site-audit-pagine.json: {len(pagine_audit)} coppie pagina-problema")

    (uscita / "unita.json").write_text(json.dumps(
        {"totale": totale, "fonte": "connettore MCP Ahrefs", "registro": registro.name,
         "chiamate": registro_unita}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  unita.json: {totale} unità in {len(registro_unita)} chiamate (registro {registro.name})")
    if not scritti and not pagine_audit:
        print("Nessuna risposta del connettore trovata: controlla --sessione e --dal.")


if __name__ == "__main__":
    main()
