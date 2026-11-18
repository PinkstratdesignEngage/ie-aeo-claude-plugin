#!/usr/bin/env python3
"""Collega Google Analytics 4 di un cliente e scarica le visite arrivate dagli assistenti AI.

Uso, dalla radice del repo del cliente, nell'ordine in cui servono:
    python3 estrai_ga4.py verifica
    python3 estrai_ga4.py trova --dominio esempio.com
    python3 estrai_ga4.py estrai --proprieta <id> [--host "<espressione>"] [--mesi 16] [--sorgenti-extra "a|b"]
    python3 estrai_ga4.py proprieta

- `verifica` controlla librerie, credenziali, consenso e API, e dice in parole semplici cosa manca.
- `trova` cerca tra le proprietà visibili quelle che misurano il dominio del cliente, con le sessioni
  reali e gli host, e consiglia proprietà e filtro sull'host da mettere in analisi/ga4/config.json.
- `estrai` scrive in raw/ga4/<data di oggi>/: ai_mensile.csv, ai_pagine.csv, ai_paesi.csv,
  canali_mensile.csv, metadati.json. Con --host considera solo le visite a quegli host (espressione
  regolare su hostName), per confrontarle con la proprietà di Search Console.
- `proprieta` elenca tutte le proprietà visibili (anche di altri clienti: non copiarle nel repo).

Le credenziali stanno fuori dal repo e sono le stesse di ie-aeo-search-console
(default ~/.config/ie-aeo-gsc/credenziali.json, oppure --credenziali o GA4_CREDENZIALI). Con un client
OAuth "Desktop app" il primo comando apre il browser per il consenso; il token va in
~/.config/ie-aeo-gsc/token-ga4.json, separato da quello di Search Console.
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")  # avvisi di versione di Python e OpenSSL: non bloccano

CARTELLA_CONFIG = Path.home() / ".config" / "ie-aeo-gsc"
CREDENZIALI_DEFAULT = CARTELLA_CONFIG / "credenziali.json"
TOKEN_OAUTH = CARTELLA_CONFIG / "token-ga4.json"
SCOPE = ["https://www.googleapis.com/auth/analytics.readonly"]
API = {"analyticsdata.googleapis.com": "Google Analytics Data API",
       "analyticsadmin.googleapis.com": "Google Analytics Admin API"}

# Sorgenti con cui GA4 registra le visite dagli assistenti AI (referrer o utm_source).
# Si allarga con --sorgenti-extra quando compaiono assistenti nuovi.
SORGENTI_AI = [
    r"chatgpt\.com", r"chat\.openai\.com", r"openai", r"perplexity", r"copilot\.microsoft\.com",
    r"copilot\.cloud\.microsoft", r"gemini\.google\.com", r"bard\.google\.com", r"claude\.ai",
    r"anthropic", r"(^|\.)you\.com$", r"phind", r"deepseek", r"meta\.ai", r"chat\.mistral\.ai",
    r"mistral", r"grok", r"x\.ai", r"poe\.com", r"kagi", r"brave.*leo", r"duckduckgo.*chat",
]


def num(x):
    return f"{int(x):,}".replace(",", ".")


def ferma(*righe):
    print("\n".join(righe))
    sys.exit(1)


def progetto(percorso):
    try:
        d = json.loads(Path(percorso).read_text())
    except (OSError, ValueError):
        return ""
    return d.get("project_id") or next((v.get("project_id", "") for v in d.values() if isinstance(v, dict)), "")


def credenziali(percorso):
    if not percorso.exists():
        ferma(f"✗ Mancano le credenziali Google in {percorso}.",
              "  Sono le stesse di Search Console: chiedi il file al referente tecnico",
              "  o segui references/accesso.md della skill ie-aeo-search-console, poi rilancia.")
    contenuto = json.loads(percorso.read_text())
    if contenuto.get("type") == "service_account":
        from google.oauth2 import service_account
        return service_account.Credentials.from_service_account_file(str(percorso), scopes=SCOPE)
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    cred = None
    if TOKEN_OAUTH.exists():
        cred = Credentials.from_authorized_user_file(str(TOKEN_OAUTH), SCOPE)
    if cred and cred.expired and cred.refresh_token:
        try:
            cred.refresh(Request())
        except Exception:
            cred = None
    if not cred or not cred.valid:
        print("→ Si apre il browser: accedi con l'account Google a cui il cliente ha dato accesso a GA4,")
        print("  poi accetta la richiesta di \"visualizzare i dati di Google Analytics\". Solo lettura.")
        flow = InstalledAppFlow.from_client_secrets_file(str(percorso), SCOPE)
        cred = flow.run_local_server(port=0)
    TOKEN_OAUTH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_OAUTH.write_text(cred.to_json())
    os.chmod(TOKEN_OAUTH, 0o600)
    return cred


def servizi(cred):
    from googleapiclient.discovery import build
    return (build("analyticsdata", "v1beta", credentials=cred, cache_discovery=False),
            build("analyticsadmin", "v1beta", credentials=cred, cache_discovery=False))


def spiega_errore(e, percorso_cred):
    testo = str(e)
    for api, nome in API.items():
        if api in testo and ("has not been used" in testo or "disabled" in testo or "SERVICE_DISABLED" in testo):
            prog = progetto(percorso_cred)
            ferma(f"✗ La \"{nome}\" non è attiva nel progetto Google Cloud delle credenziali.",
                  f"  Apri https://console.cloud.google.com/apis/library/{api}" + (f"?project={prog}" if prog else ""),
                  "  premi \"Abilita\", aspetta un minuto e rilancia lo stesso comando.")
    if "PERMISSION_DENIED" in testo or "403" in testo:
        ferma("✗ L'account non ha accesso a questa proprietà GA4.",
              "  Controlla l'id con il comando `trova`, oppure chiedi al cliente l'accesso come Visualizzatore",
              "  (testo pronto in references/accesso.md).")
    ferma(f"✗ Errore da Google: {testo[:300]}")


def tutte_le_proprieta(admin):
    righe, token = [], None
    while True:
        r = admin.accountSummaries().list(pageSize=200, pageToken=token).execute()
        for acc in r.get("accountSummaries", []):
            for p in acc.get("propertySummaries", []):
                righe.append({"id": p["property"].split("/")[-1], "nome": p.get("displayName", ""),
                              "account": acc.get("displayName", "")})
        token = r.get("nextPageToken")
        if not token:
            return righe


def report(data, prop, dimensioni, metriche, inizio, fine, filtro=None, limite=100000, ordine=None):
    righe, offset = [], 0
    while True:
        corpo = {"dateRanges": [{"startDate": inizio, "endDate": fine}],
                 "dimensions": [{"name": d} for d in dimensioni], "metrics": [{"name": m} for m in metriche],
                 "limit": limite, "offset": offset, "keepEmptyRows": False}
        if filtro:
            corpo["dimensionFilter"] = filtro
        if ordine:
            corpo["orderBys"] = ordine
        r = data.properties().runReport(property=f"properties/{prop}", body=corpo).execute()
        for x in r.get("rows", []):
            righe.append([v["value"] for v in x["dimensionValues"]] + [v["value"] for v in x["metricValues"]])
        offset += limite
        if offset >= int(r.get("rowCount", 0)) or limite < 100000:
            return righe


def cmd_verifica(a):
    print("Controllo il collegamento a Google Analytics 4…\n")
    try:
        import googleapiclient  # noqa: F401
        import google_auth_oauthlib  # noqa: F401
    except ImportError:
        ferma("✗ Mancano le librerie Google per Python.",
              "  Lancia: pip3 install -r <percorso della skill>/scripts/requirements.txt  e poi rilancia.")
    print("✓ Librerie installate")
    percorso = Path(a.credenziali).expanduser()
    cred = credenziali(percorso)
    print("✓ Credenziali e consenso a posto")
    data, admin = servizi(cred)
    try:
        props = tutte_le_proprieta(admin)
    except Exception as e:
        spiega_errore(e, percorso)
    print("✓ Google Analytics Admin API attiva")
    if not props:
        ferma("✗ Questo account Google non vede nessuna proprietà GA4.",
              "  Il cliente deve aggiungerlo come Visualizzatore: testo pronto in references/accesso.md.")
    try:
        report(data, props[0]["id"], ["date"], ["sessions"], "7daysAgo", "yesterday", limite=1)
    except Exception as e:
        spiega_errore(e, percorso)
    print("✓ Google Analytics Data API attiva")
    print(f"✓ Proprietà visibili: {len(props)}")
    print("\nTutto pronto. Passo successivo: `trova --dominio <dominio del cliente>`.")


def cmd_trova(a):
    dominio = a.dominio.lower().removeprefix("https://").removeprefix("http://").removeprefix("www.").strip("/")
    percorso = Path(a.credenziali).expanduser()
    data, admin = servizi(credenziali(percorso))
    try:
        props = tutte_le_proprieta(admin)
    except Exception as e:
        spiega_errore(e, percorso)
    trovate = []
    radice = dominio.split(".")[0]
    for p in props:
        try:
            stream = admin.properties().dataStreams().list(parent=f"properties/{p['id']}").execute().get("dataStreams", [])
        except Exception:
            stream = []
        uri = [s.get("webStreamData", {}).get("defaultUri", "") for s in stream if s.get("type") == "WEB_DATA_STREAM"]
        if any(dominio in u.lower() for u in uri) or radice in p["nome"].lower() or radice in p["account"].lower():
            p["stream"] = uri
            trovate.append(p)
    if not trovate:
        ferma(f"✗ Nessuna proprietà visibile misura {dominio}.",
              "  Il cliente deve aggiungere il tuo account come Visualizzatore sulla proprietà del sito:",
              "  testo pronto in references/accesso.md.")
    print(f"Proprietà collegate a {dominio} (ultimi 30 giorni):\n")
    print("| Id | Nome | Stream web | Sessioni | Host principali |")
    print("|---|---|---|---|---|")
    migliore, top = None, -1
    for p in trovate:
        try:
            r = report(data, p["id"], ["hostName"], ["sessions"], "30daysAgo", "yesterday", limite=5,
                       ordine=[{"metric": {"metricName": "sessions"}, "desc": True}])
        except Exception:
            r = []
        tot = sum(int(x[1]) for x in r)
        sul_dominio = sum(int(x[1]) for x in r if x[0].lower().endswith(dominio))
        host = "; ".join(f"{x[0]} ({num(x[1])})" for x in r) or "nessuna sessione"
        print(f"| {p['id']} | {p['nome']} | {', '.join(p['stream']) or '-'} | {num(tot)} | {host} |")
        if sul_dominio > top:
            migliore, top, p["host_dominio"] = p, sul_dominio, [x[0] for x in r if x[0].lower().endswith(dominio)]
    if not migliore or top <= 0:
        ferma("\n✗ Nessuna di queste proprietà ha ricevuto visite sul dominio negli ultimi 30 giorni.",
              "  Chiedi al cliente quale proprietà usa davvero il sito.")
    host = migliore["host_dominio"][0] if migliore["host_dominio"] else dominio
    espressione = "^" + re.escape(host) + "$"
    print(f"\nConsigliata: {migliore['id']} ({migliore['nome']}), {num(top)} sessioni su {dominio} negli ultimi 30 giorni.")
    print("Se ci sono altri host del cliente (altri siti o domini del gruppo), il filtro tiene solo il sito principale,")
    print("come la proprietà di Search Console. Proposta per analisi/ga4/config.json:\n")
    print(json.dumps({"proprieta": migliore["id"], "nome": host, "host": espressione, "mesi": 16,
                      "sorgenti_extra": "", "frequenza_giorni": 30}, indent=2, ensure_ascii=False))


def scrivi(percorso, intestazione, righe):
    with percorso.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(intestazione)
        w.writerows(righe)
    print(f"  {percorso.name}: {len(righe)} righe")


def filtro_e(*filtri):
    filtri = [f for f in filtri if f]
    if not filtri:
        return None
    return filtri[0] if len(filtri) == 1 else {"andGroup": {"expressions": filtri}}


def regexp(campo, valore):
    return {"filter": {"fieldName": campo,
                       "stringFilter": {"matchType": "PARTIAL_REGEXP", "value": valore, "caseSensitive": False}}}


def cmd_estrai(a):
    if not a.proprieta.isdigit():
        ferma("✗ Indica --proprieta con l'id numerico (lo consiglia il comando `trova`).")
    percorso = Path(a.credenziali).expanduser()
    data, _ = servizi(credenziali(percorso))
    oggi = dt.date.today()
    fine = oggi - dt.timedelta(days=1)
    inizio = (fine.replace(day=1) - dt.timedelta(days=31 * (a.mesi - 1))).replace(day=1)
    sorgenti = "|".join(SORGENTI_AI + ([a.sorgenti_extra] if a.sorgenti_extra else []))
    f_host = regexp("hostName", a.host) if a.host else None
    f_ai = filtro_e(regexp("sessionSource", sorgenti), f_host)
    cartella = Path("raw/ga4") / oggi.isoformat()
    cartella.mkdir(parents=True, exist_ok=True)
    print(f"Proprietà {a.proprieta}, dal {inizio} al {fine}" + (f", host {a.host}" if a.host else "") + f", in {cartella}/")
    met = ["sessions", "engagedSessions", "totalUsers", "keyEvents"]
    try:
        ai_mesi = report(data, a.proprieta, ["yearMonth", "sessionSource", "sessionMedium"], met, str(inizio), str(fine), f_ai)
        scrivi(cartella / "ai_mensile.csv", ["mese", "sorgente", "mezzo", "sessioni", "sessioni_coinvolte", "utenti", "eventi_chiave"], ai_mesi)
        ai_pag = report(data, a.proprieta, ["landingPage", "sessionSource"], met + ["averageSessionDuration"], str(inizio), str(fine), f_ai)
        scrivi(cartella / "ai_pagine.csv", ["pagina", "sorgente", "sessioni", "sessioni_coinvolte", "utenti", "eventi_chiave", "durata_media_s"], ai_pag)
        ai_pae = report(data, a.proprieta, ["country", "sessionSource"], ["sessions", "keyEvents"], str(inizio), str(fine), f_ai)
        scrivi(cartella / "ai_paesi.csv", ["paese", "sorgente", "sessioni", "eventi_chiave"], ai_pae)
        canali = report(data, a.proprieta, ["yearMonth", "sessionDefaultChannelGroup"], met, str(inizio), str(fine), f_host)
        scrivi(cartella / "canali_mensile.csv", ["mese", "canale", "sessioni", "sessioni_coinvolte", "utenti", "eventi_chiave"], canali)
    except Exception as e:
        spiega_errore(e, percorso)
    tot_ai = sum(int(r[3]) for r in ai_mesi)
    tot = sum(int(r[2]) for r in canali)
    metadati = {
        "proprieta": a.proprieta, "host": a.host or None,
        "periodo": {"inizio": str(inizio), "fine": str(fine)}, "estratto_il": oggi.isoformat(),
        "regex_sorgenti_ai": sorgenti,
        "totali": {"sessioni": tot, "sessioni_ai": tot_ai, "quota_ai": round(tot_ai / tot, 5) if tot else None},
        "righe": {"ai_mensile": len(ai_mesi), "ai_pagine": len(ai_pag), "ai_paesi": len(ai_pae), "canali_mensile": len(canali)},
    }
    (cartella / "metadati.json").write_text(json.dumps(metadati, indent=2, ensure_ascii=False))
    print(f"  metadati.json: {tot_ai} sessioni dagli assistenti AI su {tot} totali")


def cmd_proprieta(a):
    percorso = Path(a.credenziali).expanduser()
    _, admin = servizi(credenziali(percorso))
    try:
        props = tutte_le_proprieta(admin)
    except Exception as e:
        spiega_errore(e, percorso)
    if not props:
        print("Nessuna proprietà GA4 visibile: il cliente non ha ancora dato l'accesso. Vedi references/accesso.md.")
        return
    print("| Id proprietà | Nome | Account |\n|---|---|---|")
    for p in props:
        print(f"| {p['id']} | {p['nome']} | {p['account']} |")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("comando", choices=["verifica", "trova", "estrai", "proprieta"])
    ap.add_argument("--dominio", default="")
    ap.add_argument("--proprieta", default="")
    ap.add_argument("--host", default="")
    ap.add_argument("--mesi", type=int, default=16)
    ap.add_argument("--sorgenti-extra", default="")
    ap.add_argument("--credenziali", default=os.environ.get("GA4_CREDENZIALI", str(CREDENZIALI_DEFAULT)))
    a = ap.parse_args()
    if a.comando != "verifica":
        try:
            import googleapiclient  # noqa: F401
        except ImportError:
            ferma("✗ Mancano le librerie Google: lancia prima `verifica`.")
    if a.comando == "trova" and not a.dominio:
        ferma("✗ Indica il dominio del sito del cliente: trova --dominio esempio.com")
    {"verifica": cmd_verifica, "trova": cmd_trova, "estrai": cmd_estrai, "proprieta": cmd_proprieta}[a.comando](a)


if __name__ == "__main__":
    main()
