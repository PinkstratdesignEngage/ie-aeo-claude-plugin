#!/usr/bin/env python3
"""Scarica i dati di Ahrefs di un cliente con l'API v3 e li salva in raw/ahrefs/<data>/originali/.

Uso, dalla radice del repo del cliente:
    python3 -I estrai_ahrefs.py limiti
    python3 -I estrai_ahrefs.py progetti
    python3 -I estrai_ahrefs.py estrai                  # preventivo: non spende nulla
    python3 -I estrai_ahrefs.py estrai --conferma       # esegue, dopo l'ok del consulente

La chiave API sta fuori dal repo (default: ~/.config/ie-aeo-ahrefs/chiave.txt, oppure la
variabile AHREFS_API_KEY). Dettagli in references/acquisizione.md della skill ie-aeo-ahrefs.

`estrai` senza --conferma stampa il piano delle chiamate con le unità stimate e si ferma:
è il preventivo da mostrare al consulente. Con --conferma scarica, una chiamata alla volta,
e dopo ognuna rilegge il consumo reale da /subscription-info/limits-and-usage, che è
gratuito. Se il costo supera la stima, o il totale supera --max-unita, si ferma.

Scrive in originali/:
    posizioni-<paese>.json          organic-keywords del cliente
    competitor-<paese>.json         organic-competitors
    keyword-<paese>-<dominio>.json  organic-keywords di un competitor, per il gap
    top-pages.json                  top-pages, con le citazioni negli assistenti AI
    ai-risposte.json                ai-responses-count, citazioni per assistente
    site-audit-problemi.json        site-audit/issues
    site-audit-pagine.json          site-audit/page-explorer, le pagine di ogni problema
    unita.json                      unità consumate per chiamata e in totale
"""
import argparse
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://api.ahrefs.com/v3"
CHIAVE_DEFAULT = Path.home() / ".config" / "ie-aeo-ahrefs" / "chiave.txt"
USCITA_DEFAULT = Path("raw") / "ahrefs"
CONFIG_DEFAULT = Path("analisi") / "ahrefs" / "config.json"
PAUSA = 1.1  # l'API accetta 60 richieste al minuto
MINIMO_UNITA = 50  # costo minimo di ogni richiesta, dichiarato da Ahrefs

# Campi richiesti a ogni report, con il costo per riga delle colonne che ne hanno uno.
# Le altre colonne costano 1 unità ciascuna: il totale per riga è la somma delle colonne.
COSTOSI = {"volume": 10, "keyword_difficulty": 10, "sum_traffic": 10, "value": 10, "traffic": 10,
           "all_positions": 5, "referring_domains": 5, "top_keyword_volume": 10}
AI_CAMPI = ["chatgpt", "perplexity", "google_ai_overviews", "google_ai_mode", "gemini", "copilot", "grok"]

POSIZIONI = ["keyword", "best_position", "best_position_prev", "best_position_url", "volume",
             "keyword_difficulty", "serp_features", "is_branded", "is_commercial", "is_informational",
             "is_navigational", "is_transactional"]
POSIZIONI_COMPETITOR = ["keyword", "best_position", "volume", "serp_features"]
COMPETITOR = ["competitor_domain", "keywords_common", "keywords_competitor", "keywords_target",
              "share", "domain_rating"]
TOP_PAGES = ["url", "keywords", "top_keyword", "sum_traffic"]


def costo_campo(c):
    # Ogni piattaforma AI costa come le colonne di traffico e volume
    return 10 if c.startswith("ai_responses_") else COSTOSI.get(c, 1)


def costo_riga(campi):
    return sum(costo_campo(c) for c in campi)


def dominio_pulito(d):
    return d.strip().lower().removeprefix("https://").removeprefix("http://").removeprefix("www.").split("/")[0]


# --- Accesso all'API -------------------------------------------------------

class Ahrefs:
    def __init__(self, chiave, pausa=PAUSA):
        self.chiave = chiave
        self.pausa = pausa
        self.ultima = 0.0

    def get(self, percorso, params=None):
        url = f"{BASE}{percorso}"
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v not in (None, "")})
        attesa = self.pausa - (time.monotonic() - self.ultima)
        if attesa > 0:
            time.sleep(attesa)
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.chiave}",
                                                   "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                corpo = r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            dettaglio = e.read().decode("utf-8", "replace")[:500]
            if e.code == 429:
                sys.exit(f"Ahrefs ha risposto 429 (troppe richieste) su {percorso}. Riprova più tardi.\n{dettaglio}")
            sys.exit(f"Ahrefs ha risposto {e.code} su {percorso}:\n{dettaglio}")
        except urllib.error.URLError as e:
            sys.exit(f"Non riesco a contattare Ahrefs: {e.reason}")
        finally:
            self.ultima = time.monotonic()
        return json.loads(corpo)

    def usate(self):
        """Unità consumate dalla chiave nel mese. La chiamata è gratuita."""
        d = self.get("/subscription-info/limits-and-usage")
        return d.get("limits_and_usage", d)


def chiave_api(percorso):
    if os.environ.get("AHREFS_API_KEY"):
        return os.environ["AHREFS_API_KEY"].strip()
    p = Path(percorso).expanduser()
    if not p.exists():
        sys.exit(
            f"Chiave API non trovata in {p}.\n"
            "Mettila lì (una riga sola), oppure indicala con --chiave o con la variabile AHREFS_API_KEY.\n"
            "Istruzioni in references/acquisizione.md della skill ie-aeo-ahrefs.")
    righe = [r.strip() for r in p.read_text(encoding="utf-8").splitlines() if r.strip()]
    if not righe:
        sys.exit(f"{p} è vuoto: serve la chiave API di Ahrefs.")
    return righe[0]


# --- Piano delle chiamate --------------------------------------------------

def piano(cfg, oggi, confronto):
    """Elenco delle chiamate da fare, con la stima delle unità."""
    paesi = cfg["paesi"]
    competitor = [dominio_pulito(c) for c in cfg.get("competitor", [])]
    righe_pos = int(cfg.get("righe_posizioni", 500))
    righe_gap = int(cfg.get("righe_gap", 500))
    righe_top = int(cfg.get("righe_top_pages", 100))
    target = dominio_pulito(cfg["dominio"])
    comune = {"date": oggi, "mode": cfg.get("mode", "subdomains"), "protocol": "both"}
    voci = []

    for paese in paesi:
        voci.append({
            "nome": f"posizioni-{paese}", "percorso": "/site-explorer/organic-keywords",
            "params": dict(comune, target=target, country=paese, select=",".join(POSIZIONI),
                           order_by="volume:desc", limit=righe_pos, date_compared=confronto,
                           volume_mode="monthly"),
            "righe": righe_pos, "unita": MINIMO_UNITA + righe_pos * costo_riga(POSIZIONI),
        })
        voci.append({
            "nome": f"competitor-{paese}", "percorso": "/site-explorer/organic-competitors",
            "params": dict(comune, target=target, country=paese, select=",".join(COMPETITOR),
                           order_by="keywords_common:desc", limit=int(cfg.get("righe_competitor", 10))),
            "righe": int(cfg.get("righe_competitor", 10)),
            "unita": MINIMO_UNITA + int(cfg.get("righe_competitor", 10)) * costo_riga(COMPETITOR),
        })
        for c in competitor:
            voci.append({
                "nome": f"keyword-{paese}-{c}", "percorso": "/site-explorer/organic-keywords",
                "params": dict(comune, target=c, country=paese, select=",".join(POSIZIONI_COMPETITOR),
                               order_by="volume:desc", limit=righe_gap, volume_mode="monthly"),
                "righe": righe_gap, "unita": MINIMO_UNITA + righe_gap * costo_riga(POSIZIONI_COMPETITOR),
            })

    campi_ai = [f"ai_responses_{x}" for x in AI_CAMPI]
    if cfg.get("ai", True):
        voci.append({
            "nome": "top-pages", "percorso": "/site-explorer/top-pages",
            "params": dict(comune, target=target, country=cfg.get("paese_ai") or paesi[0],
                           select=",".join(TOP_PAGES + campi_ai), order_by="sum_traffic:desc", limit=righe_top),
            "righe": righe_top, "unita": MINIMO_UNITA + righe_top * costo_riga(TOP_PAGES + campi_ai),
        })
        voci.append({
            "nome": "ai-risposte", "percorso": "/site-explorer/ai-responses-count",
            "params": {"target": target, "date": oggi, "mode": cfg.get("mode", "subdomains"), "protocol": "both",
                       "select": ",".join(["all_platforms"] + AI_CAMPI)},
            "righe": 1, "unita": MINIMO_UNITA + 15 * (len(AI_CAMPI) + 1),
        })
    if cfg.get("progetto_id"):
        voci.append({"nome": "site-audit-problemi", "percorso": "/site-audit/issues",
                     "params": {"project_id": cfg["progetto_id"]}, "righe": None, "unita": MINIMO_UNITA})
    return voci


# --- Comandi ---------------------------------------------------------------

def cmd_limiti(api, _a):
    u = api.usate()
    print("Unità della chiave, mese in corso:")
    for k in ("units_usage_api_key", "units_limit_api_key", "units_usage_workspace",
              "units_limit_workspace", "usage_reset_date"):
        if k in u:
            print(f"  {k}: {u[k]}")
    if not u:
        print("  (l'API non ha restituito i campi attesi)", json.dumps(u, ensure_ascii=False))


def cmd_progetti(api, _a):
    d = api.get("/site-audit/projects")
    progetti = d.get("projects", d if isinstance(d, list) else [])
    if not progetti:
        print("Nessun progetto Site Audit sull'account.")
        return
    print(f"{len(progetti)} progetti sull'account Ahrefs. Metti in config.json solo l'id del cliente:\n")
    for p in progetti:
        print(f"  {p.get('id') or p.get('project_id')}  {p.get('domain') or p.get('name', '')}  "
              f"health {p.get('health_score', '—')}  pagine {p.get('crawled_pages', p.get('pages', '—'))}")
    print("\nL'elenco contiene gli altri clienti dell'agenzia: non salvarlo nel repo del cliente.")


def cmd_estrai(api, a):
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8")) if Path(a.config).exists() else {}
    for campo in ("dominio", "paesi"):
        if not cfg.get(campo):
            sys.exit(f"Manca «{campo}» in {a.config}: vedi la sezione «Prepara» di SKILL.md.")
    oggi = a.data or dt.date.today().isoformat()
    confronto = (dt.date.fromisoformat(oggi) - dt.timedelta(days=int(a.confronto_giorni))).isoformat()
    max_unita = int(a.max_unita or cfg.get("max_unita", 100000))
    voci = piano(cfg, oggi, confronto)
    stima = sum(v["unita"] for v in voci)

    print(f"Piano di estrazione per {cfg['dominio']}, paesi {', '.join(cfg['paesi'])}, data {oggi}.\n")
    print(f"| {'Chiamata':34} | {'Righe':>6} | {'Unità stimate':>13} |")
    print(f"|{'-' * 36}|{'-' * 8}|{'-' * 15}|")
    for v in voci:
        print(f"| {v['nome']:34} | {str(v['righe'] or '—'):>6} | {v['unita']:>13,} |")
    print(f"| {'TOTALE':34} | {'':>6} | {stima:>13,} |")
    print(f"\nTetto: {max_unita:,} unità (max_unita). Le stime usano il listino pubblico: 1 unità per colonna "
          "per riga, 10 per volume, keyword difficulty e traffico, 15 per ogni piattaforma AI, più 50 "
          "di minimo per chiamata. Il costo reale si legge dopo ogni chiamata.")
    if stima > max_unita:
        print(f"\nLa stima supera il tetto di {stima - max_unita:,} unità: riduci righe_posizioni, "
              "righe_gap, i paesi o i competitor in config.json.")
    if not a.conferma:
        print("\nPreventivo: non è stato scaricato nulla. Rilancia con --conferma dopo l'ok del consulente.")
        return
    if stima > max_unita:
        sys.exit("\nNon procedo: la stima supera il tetto.")

    uscita = Path(a.uscita) / oggi / "originali"
    uscita.mkdir(parents=True, exist_ok=True)
    prima = api.usate().get("units_usage_api_key")
    speso, registro = 0, []
    for v in voci:
        d = api.get(v["percorso"], v["params"])
        dopo = api.usate().get("units_usage_api_key")
        reali = (dopo - prima) if (prima is not None and dopo is not None) else None
        prima = dopo
        righe = next((len(x) for x in d.values() if isinstance(x, list)), None) if isinstance(d, dict) else None
        (uscita / f"{v['nome']}.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        registro.append({"chiamata": v["nome"], "percorso": v["percorso"],
                         "params": {k: x for k, x in v["params"].items() if k != "select"},
                         "righe": righe, "unita_stimate": v["unita"], "unita_reali": reali})
        speso += reali or v["unita"]
        print(f"  {v['nome']}: {righe if righe is not None else '—'} righe, "
              f"{reali if reali is not None else '≈' + str(v['unita'])} unità (totale {speso:,})")
        if reali and reali > v["unita"] * 1.5:
            registro.append({"avviso": f"{v['nome']} è costato {reali} unità contro {v['unita']} stimate"})
            print(f"    Costo molto più alto della stima: mi fermo. Rivedi il piano con il consulente.")
            break
        if speso > max_unita:
            print(f"    Raggiunto il tetto di {max_unita:,} unità: mi fermo.")
            break

    # Progetto Site Audit: l'elenco contiene gli altri clienti, nel repo resta solo la sua riga
    if cfg.get("progetto_id") and speso <= max_unita:
        d = api.get("/site-audit/projects")
        elenco = d.get("projects", d if isinstance(d, list) else [])
        mio = next((x for x in elenco if str(x.get("id") or x.get("project_id")) == str(cfg["progetto_id"])), None)
        if mio:
            (uscita / "progetto.json").write_text(json.dumps(mio, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"  progetto.json: {mio.get('domain') or mio.get('name', '')}")
        else:
            print(f"  progetto {cfg['progetto_id']} non trovato sull'account: controlla progetto_id.")
        dopo = api.usate().get("units_usage_api_key")
        speso += ((dopo - prima) if (prima is not None and dopo is not None) else MINIMO_UNITA) or 0
        prima = dopo

    # Site Audit: le pagine di ogni problema, una chiamata per problema
    problemi = uscita / "site-audit-problemi.json"
    if cfg.get("progetto_id") and problemi.exists() and speso <= max_unita:
        elenco = json.loads(problemi.read_text(encoding="utf-8")).get("issues", [])
        da_leggere = [i for i in elenco if i.get("importance") in ("Error", "Warning")
                      and (i.get("crawled") or 0) > 0][:int(a.max_problemi)]
        pagine = []
        for i in da_leggere:
            if speso + MINIMO_UNITA > max_unita:
                print(f"    Tetto raggiunto: resto dei problemi non letto ({len(da_leggere) - len(pagine)}).")
                break
            d = api.get("/site-audit/page-explorer",
                        {"project_id": cfg["progetto_id"], "issue_id": i["issue_id"],
                         "select": "url", "limit": int(a.righe_problema)})
            dopo = api.usate().get("units_usage_api_key")
            reali = (dopo - prima) if (prima is not None and dopo is not None) else MINIMO_UNITA
            prima, speso = dopo, speso + (reali or MINIMO_UNITA)
            for riga in (d.get("pages") or d.get("data") or []):
                url = riga.get("url") if isinstance(riga, dict) else riga
                if url:
                    pagine.append({"url": url, "issue_id": i["issue_id"], "issue": i.get("name", ""),
                                   "importance": i.get("importance", ""), "category": i.get("category", "")})
            registro.append({"chiamata": f"page-explorer:{i['issue_id']}", "percorso": "/site-audit/page-explorer",
                             "params": {"issue_id": i["issue_id"]}, "righe": len(pagine),
                             "unita_stimate": MINIMO_UNITA, "unita_reali": reali})
        (uscita / "site-audit-pagine.json").write_text(json.dumps(pagine, ensure_ascii=False, indent=1),
                                                       encoding="utf-8")
        print(f"  site-audit-pagine.json: {len(pagine)} coppie pagina-problema da {len(da_leggere)} problemi")

    (uscita / "unita.json").write_text(json.dumps({"totale": speso, "stima": stima, "data": oggi,
                                                   "chiamate": registro}, ensure_ascii=False, indent=2),
                                       encoding="utf-8")
    print(f"\nFatto in {uscita}: {speso:,} unità consumate su {stima:,} stimate.")
    print(f"Ora normalizza:  python3 -I <skill>/scripts/normalizza_ahrefs.py {Path(a.uscita) / oggi} "
          f"--dominio {cfg['dominio']}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("comando", choices=["limiti", "progetti", "estrai"])
    p.add_argument("--chiave", default=str(CHIAVE_DEFAULT), help="file con la chiave API (default: %(default)s)")
    p.add_argument("--config", default=str(CONFIG_DEFAULT), help="configurazione del cliente (default: %(default)s)")
    p.add_argument("--uscita", default=str(USCITA_DEFAULT))
    p.add_argument("--data", help="data dell'estrazione, AAAA-MM-GG (default: oggi)")
    p.add_argument("--confronto-giorni", default=30, help="giorni indietro per le posizioni precedenti (default: 30)")
    p.add_argument("--max-unita", type=int, help="tetto di unità; senza, vale max_unita della configurazione")
    p.add_argument("--max-problemi", default=40, help="problemi del Site Audit di cui leggere le pagine (default: 40)")
    p.add_argument("--righe-problema", default=200, help="pagine lette per ogni problema (default: 200)")
    p.add_argument("--conferma", action="store_true", help="esegue davvero; senza, stampa solo il preventivo")
    a = p.parse_args()

    api = Ahrefs(chiave_api(a.chiave))
    {"limiti": cmd_limiti, "progetti": cmd_progetti, "estrai": cmd_estrai}[a.comando](api, a)


if __name__ == "__main__":
    main()
