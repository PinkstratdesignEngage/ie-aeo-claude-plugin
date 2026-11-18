#!/usr/bin/env python3
"""Estrae i dati di Google Search Console di un sito e li salva come CSV.

Uso, dalla radice del repo del cliente:
    python3 <skill>/scripts/estrai_gsc.py proprieta
    python3 <skill>/scripts/estrai_gsc.py estrai --sito sc-domain:esempio.com

Le credenziali stanno fuori dal repo (default: ~/.config/ie-aeo-gsc/credenziali.json).
Vale sia la chiave JSON di un account di servizio sia un client OAuth "Desktop app".
Dettagli in references/accesso.md della skill ie-aeo-search-console.
"""

import argparse
import calendar
import csv
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path

SCOPE = ["https://www.googleapis.com/auth/webmasters.readonly"]
CARTELLA_CONFIG = Path.home() / ".config" / "ie-aeo-gsc"
CREDENZIALI_DEFAULT = CARTELLA_CONFIG / "credenziali.json"
TOKEN_OAUTH = CARTELLA_CONFIG / "token.json"
USCITA_DEFAULT = Path("raw") / "gsc"  # relativo alla radice del repo del cliente

RIGHE_PER_PAGINA = 25000  # massimo consentito dall'API per richiesta
MESI_STORICO = 16  # Search Console conserva 16 mesi di dati
RITARDO_DATI_GIORNI = 3  # i dati "final" arrivano con 2-3 giorni di ritardo

# Nomi delle colonne nei CSV, nell'ordine in cui li restituisce l'API
NOMI_DIMENSIONI = {
    "date": "data",
    "query": "query",
    "page": "pagina",
    "country": "paese",
    "device": "dispositivo",
}
RE_LINGUA = re.compile(r"^https?://[^/]+/([a-z]{2}(?:-[a-z]{2})?)(?:/|$)", re.IGNORECASE)


# --- Autenticazione --------------------------------------------------------

def servizio(percorso_credenziali):
    """Restituisce il client dell'API Search Console."""
    try:
        from googleapiclient.discovery import build
    except ImportError:
        sys.exit(f"Mancano le librerie Google: pip3 install -r {Path(__file__).parent / 'requirements.txt'}")

    percorso = Path(percorso_credenziali).expanduser()
    if not percorso.exists():
        sys.exit(
            f"Credenziali non trovate in {percorso}.\n"
            "Mettile lì oppure indica il file con --credenziali o la variabile GSC_CREDENZIALI.\n"
            "Istruzioni in references/accesso.md della skill ie-aeo-search-console."
        )
    contenuto = json.loads(percorso.read_text())

    if contenuto.get("type") == "service_account":
        from google.oauth2 import service_account
        cred = service_account.Credentials.from_service_account_file(str(percorso), scopes=SCOPE)
    elif "installed" in contenuto or "web" in contenuto:
        cred = _credenziali_oauth(percorso)
    else:
        sys.exit(f"{percorso} non è né una chiave di account di servizio né un client OAuth.")

    return build("searchconsole", "v1", credentials=cred, cache_discovery=False)


def _credenziali_oauth(percorso_client):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    cred = None
    if TOKEN_OAUTH.exists():
        cred = Credentials.from_authorized_user_file(str(TOKEN_OAUTH), SCOPE)
    if cred and cred.valid:
        return cred
    if cred and cred.expired and cred.refresh_token:
        cred.refresh(Request())
    else:
        # Apre il browser per il consenso con l'account Google che ha accesso alla proprietà
        flow = InstalledAppFlow.from_client_secrets_file(str(percorso_client), SCOPE)
        cred = flow.run_local_server(port=0)
    TOKEN_OAUTH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_OAUTH.write_text(cred.to_json())
    os.chmod(TOKEN_OAUTH, 0o600)
    return cred


# --- Chiamate all'API ------------------------------------------------------

def _esegui(richiesta, tentativi=5):
    """Esegue una richiesta con attesa crescente su limiti di quota ed errori temporanei."""
    from googleapiclient.errors import HttpError

    for n in range(tentativi):
        try:
            return richiesta.execute()
        except HttpError as e:
            if e.resp.status in (429, 500, 502, 503) and n < tentativi - 1:
                time.sleep(2 ** n * 5)
                continue
            raise


def interroga(svc, sito, inizio, fine, dimensioni, tipo, stato_dati):
    """Scarica tutte le righe di un report, pagina dopo pagina."""
    righe = []
    start = 0
    while True:
        corpo = {
            "startDate": inizio.isoformat(),
            "endDate": fine.isoformat(),
            "type": tipo,
            "dataState": stato_dati,
            "rowLimit": RIGHE_PER_PAGINA,
            "startRow": start,
        }
        if dimensioni:
            corpo["dimensions"] = dimensioni
        risposta = _esegui(svc.searchanalytics().query(siteUrl=sito, body=corpo))
        blocco = risposta.get("rows", [])
        righe.extend(blocco)
        if len(blocco) < RIGHE_PER_PAGINA:
            return righe
        start += RIGHE_PER_PAGINA


# --- Utilità ----------------------------------------------------------------

def mesi(inizio, fine):
    """Intervalli (primo giorno, ultimo giorno) di ogni mese, tagliati sul periodo."""
    corrente = inizio.replace(day=1)
    while corrente <= fine:
        prossimo = (corrente.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        yield max(corrente, inizio), min(prossimo - dt.timedelta(days=1), fine)
        corrente = prossimo


def lingua(url):
    """Cartella di lingua dell'URL (es. /it/, /en/), vuota se non c'è."""
    m = RE_LINGUA.match(url)
    return m.group(1).lower() if m else ""


def righe_csv(righe, dimensioni, extra=None):
    """Trasforma le righe dell'API in dizionari pronti per il CSV."""
    for r in righe:
        riga = dict(extra or {})
        for nome, valore in zip(dimensioni, r["keys"]):
            riga[NOMI_DIMENSIONI[nome]] = valore
        if "page" in dimensioni:
            riga["lingua"] = lingua(riga["pagina"])
        riga["click"] = int(r["clicks"])
        riga["impressioni"] = int(r["impressions"])
        riga["ctr"] = round(r["ctr"], 4)
        riga["posizione"] = round(r["position"], 2)
        yield riga


def scrivi_csv(percorso, righe, colonne_iniziali, dimensioni):
    colonne = list(colonne_iniziali) + [NOMI_DIMENSIONI[d] for d in dimensioni]
    if "page" in dimensioni:
        colonne.append("lingua")
    colonne += ["click", "impressioni", "ctr", "posizione"]
    with open(percorso, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colonne)
        w.writeheader()
        n = 0
        for riga in righe:
            w.writerow(riga)
            n += 1
    return n


# --- Comandi ----------------------------------------------------------------

def cmd_proprieta(args):
    svc = servizio(args.credenziali)
    voci = _esegui(svc.sites().list()).get("siteEntry", [])
    if not voci:
        print("Nessuna proprietà visibile con queste credenziali.")
        print("Controlla che l'account sia stato aggiunto come utente in Search Console.")
        return
    for v in sorted(voci, key=lambda v: v["siteUrl"]):
        print(f"{v['siteUrl']}\t{v['permissionLevel']}")


# Report a periodo intero: (nome file, dimensioni)
REPORT_PERIODO = [
    ("andamento_giornaliero.csv", ["date"]),
    ("pagine.csv", ["page"]),
    ("query.csv", ["query"]),
    ("query_pagina.csv", ["query", "page"]),
    ("pagine_paese.csv", ["page", "country"]),
]
# Report ripetuti mese per mese, per vedere l'andamento nel tempo
REPORT_MENSILI = [
    ("pagine_mensile.csv", ["page"]),
    ("query_pagina_mensile.csv", ["query", "page"]),
]


def cmd_estrai(args):
    fine = args.fine or (dt.date.today() - dt.timedelta(days=RITARDO_DATI_GIORNI))
    inizio = args.inizio or _meno_mesi(fine, MESI_STORICO) + dt.timedelta(days=1)
    if inizio > fine:
        sys.exit("La data di inizio è successiva alla data di fine.")

    svc = servizio(args.credenziali)
    cartella = Path(args.uscita) / dt.date.today().isoformat()
    cartella.mkdir(parents=True, exist_ok=True)
    stato = "all" if args.dati_freschi else "final"
    print(f"Sito {args.sito}, dal {inizio} al {fine}, tipo {args.tipo}, dati {stato}")
    print(f"Uscita: {cartella}")

    conteggi = {}
    for nome, dims in REPORT_PERIODO:
        righe = interroga(svc, args.sito, inizio, fine, dims, args.tipo, stato)
        conteggi[nome] = scrivi_csv(cartella / nome, righe_csv(righe, dims), [], dims)
        print(f"  {nome}: {conteggi[nome]} righe")

    for nome, dims in REPORT_MENSILI:
        def tutte():
            for da, a in mesi(inizio, fine):
                righe = interroga(svc, args.sito, da, a, dims, args.tipo, stato)
                yield from righe_csv(righe, dims, {"mese": da.strftime("%Y-%m")})
        conteggi[nome] = scrivi_csv(cartella / nome, tutte(), ["mese"], dims)
        print(f"  {nome}: {conteggi[nome]} righe")

    # Totali senza dimensioni: servono a stimare quanto pesano le query anonimizzate
    totali = interroga(svc, args.sito, inizio, fine, [], args.tipo, stato)
    tot = totali[0] if totali else {"clicks": 0, "impressions": 0}
    click_query = _somma_click(cartella / "query.csv")
    metadati = {
        "sito": args.sito,
        "tipo": args.tipo,
        "stato_dati": stato,
        "inizio": inizio.isoformat(),
        "fine": fine.isoformat(),
        "estratto_il": dt.datetime.now().isoformat(timespec="seconds"),
        "totali": {"click": int(tot["clicks"]), "impressioni": int(tot["impressions"])},
        "click_su_query_visibili": click_query,
        "quota_click_query_anonime": (
            round(1 - click_query / tot["clicks"], 3) if tot["clicks"] else None
        ),
        "righe": conteggi,
    }
    (cartella / "metadati.json").write_text(json.dumps(metadati, indent=2, ensure_ascii=False))
    print(f"  metadati.json: {metadati['totali']['click']} click totali, "
          f"quota da query anonime {metadati['quota_click_query_anonime']}")


def _meno_mesi(data, n):
    anno, mese = divmod(data.year * 12 + data.month - 1 - n, 12)
    mese += 1
    return dt.date(anno, mese, min(data.day, calendar.monthrange(anno, mese)[1]))


def _somma_click(percorso):
    with open(percorso, encoding="utf-8") as f:
        return sum(int(r["click"]) for r in csv.DictReader(f))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--credenziali", default=os.environ.get("GSC_CREDENZIALI", str(CREDENZIALI_DEFAULT)),
                   help="file JSON delle credenziali (default: %(default)s)")
    sub = p.add_subparsers(dest="comando", required=True)

    sub.add_parser("proprieta", help="elenca le proprietà accessibili e il livello di permesso")

    e = sub.add_parser("estrai", help="scarica i report in CSV")
    e.add_argument("--sito", required=True,
                   help="proprietà come la mostra 'proprieta', es. sc-domain:esempio.com o https://www.esempio.com/")
    e.add_argument("--inizio", type=dt.date.fromisoformat, help="AAAA-MM-GG (default: 16 mesi prima della fine)")
    e.add_argument("--fine", type=dt.date.fromisoformat, help="AAAA-MM-GG (default: 3 giorni fa)")
    e.add_argument("--tipo", default="web", choices=["web", "image", "video", "news", "discover", "googleNews"])
    e.add_argument("--dati-freschi", action="store_true",
                   help="include gli ultimi giorni non ancora consolidati (dataState=all)")
    e.add_argument("--uscita", default=str(USCITA_DEFAULT), help="cartella di uscita (default: %(default)s)")

    args = p.parse_args()
    {"proprieta": cmd_proprieta, "estrai": cmd_estrai}[args.comando](args)


if __name__ == "__main__":
    main()
