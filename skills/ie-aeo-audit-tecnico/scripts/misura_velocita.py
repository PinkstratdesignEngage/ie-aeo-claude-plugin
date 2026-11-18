#!/usr/bin/env python3
"""Misura l'attesa prima della risposta: dati reali di Chrome e misura da crawler.

Uso, dalla radice del repo del cliente:
    python3 -I misura_velocita.py https://esempio.com raw/audit-tecnico/<AAAA-MM-GG>
        [--chiave ~/.config/ie-aeo-psi/chiave.txt] [--misure 5] [--strategia mobile]

Scrive velocita.json nella cartella dell'estrazione. È separato dalla scansione perché la
velocità cambia di giorno in giorno mentre la struttura del sito no: si rimisura senza
riscansionare tutto.

Due numeri, che non vanno confusi:

- **campo**: il TTFB che Google misura sugli utenti Chrome veri (CrUX), sugli ultimi 28
  giorni. Si prende anche `category` (FAST / AVERAGE / SLOW), che è il verdetto di Google
  sul proprio dato: lo usiamo al posto delle nostre soglie, perché quale percentile
  restituisca PSI non è documentato in modo coerente e la soglia ufficiale degli 800 ms è
  definita al 75° percentile. Esiste solo sui siti con traffico sufficiente: su un sito
  piccolo manca, e va detto invece di sostituirlo di nascosto col dato di laboratorio.
- **crawler**: la stessa attesa misurata da noi, con lo user-agent di un assistente, da
  un server e senza le ottimizzazioni che aiutano un browser. È la misura che conta per
  l'AEO, e lo scarto fra le due dice se la cache lavora solo per le persone.

La chiave dell'API PageSpeed Insights è gratuita (console.cloud.google.com, API
«PageSpeed Insights»), 25.000 richieste al giorno. Senza chiave lo script fa comunque la
misura da crawler e lo dichiara.
"""
import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CHIAVE_DEFAULT = Path.home() / ".config" / "ie-aeo-psi" / "chiave.txt"
PSI = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
UA_CRAWLER = "Mozilla/5.0 (compatible; OAI-SearchBot/1.0; +https://openai.com/searchbot)"


# Segni che quello che abbiamo in mano non e' una chiave ma un segnaposto rimasto li'.
SEGNAPOSTO = ("tua-chiave", "your-key", "your_api_key", "inserisci", "xxxx", "<", "placeholder",
              "la-tua", "chiave-qui", "api-key-here", "changeme")


def sembra_chiave(v):
    """Una chiave Google e' AIza seguita da 35 caratteri. Non siamo rigidi sul formato,
    che Google ha gia' cambiato in passato, ma un segnaposto lo riconosciamo."""
    v = (v or "").strip()
    if len(v) < 20:
        return False, "troppo corta"
    if any(s in v.lower() for s in SEGNAPOSTO):
        return False, "è un segnaposto"
    return True, ""


def chiave_api(percorso):
    """La chiave, da PSI_API_KEY o dal file. Un segnaposto vale come chiave assente."""
    da_env = (os.environ.get("PSI_API_KEY") or "").strip()
    if da_env:
        ok, perche = sembra_chiave(da_env)
        if ok:
            return da_env
        print(f"  PSI_API_KEY non sembra una chiave ({perche}): la ignoro.")
    p = Path(percorso).expanduser()
    if not p.exists():
        return ""
    righe = [r.strip() for r in p.read_text(encoding="utf-8").splitlines() if r.strip()]
    if not righe:
        return ""
    ok, perche = sembra_chiave(righe[0])
    if not ok:
        print(f"  In {p} non c'è una chiave ({perche}): la ignoro.")
        print("  Mettici la chiave vera, oppure cancella il file e usa PSI_API_KEY.")
        return ""
    if not righe[0].startswith("AIza"):
        print("  La chiave non ha la forma solita di Google (AIza…): provo lo stesso.")
    return righe[0]


def attesa_ms(url, ua, timeout=25):
    """Millisecondi fino alle intestazioni della risposta: il corpo non è ancora stato letto."""
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "text/html,*/*"})
    inizio = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ms = round((time.monotonic() - inizio) * 1000)
            r.read(1)
            return ms, r.status, ""
    except urllib.error.HTTPError as e:
        return round((time.monotonic() - inizio) * 1000), e.code, ""
    except Exception as e:
        return None, None, f"{type(e).__name__}: {e}"


def psi(url, chiave, strategia):
    q = {"url": url, "strategy": strategia, "category": "performance"}
    if chiave:
        q["key"] = chiave
    try:
        with urllib.request.urlopen(f"{PSI}?{urllib.parse.urlencode(q)}", timeout=120) as r:
            return json.loads(r.read().decode("utf-8")), ""
    except urllib.error.HTTPError as e:
        corpo = e.read(600).decode("utf-8", "replace")
        return None, f"PageSpeed ha risposto {e.code}: {corpo[:300]}"
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("sito")
    p.add_argument("cartella", help="cartella dell'estrazione, es. raw/audit-tecnico/2026-11-12")
    p.add_argument("--chiave", default=str(CHIAVE_DEFAULT))
    p.add_argument("--misure", type=int, default=5)
    p.add_argument("--strategia", default="mobile", choices=["mobile", "desktop"])
    a = p.parse_args()

    base = a.sito if "://" in a.sito else "https://" + a.sito
    cartella = Path(a.cartella)
    if not cartella.is_dir():
        sys.exit(f"{cartella} non esiste: lancia prima scansiona_sito.py.")
    out = {"sito": base, "strategia": a.strategia, "misure": a.misure}

    print(f"Misura da crawler ({a.misure} richieste con lo user-agent di un assistente)")
    valori, stati = [], []
    for i in range(a.misure):
        ms, status, err = attesa_ms(base, UA_CRAWLER)
        if ms is not None:
            valori.append(ms)
            stati.append(status)
            print(f"  {i + 1}. {ms} ms (status {status})")
        else:
            print(f"  {i + 1}. errore: {err}")
        time.sleep(1)
    if valori:
        out.update(ttfb_crawler_ms=round(statistics.median(valori)),
                   ttfb_crawler_min=min(valori), ttfb_crawler_max=max(valori),
                   ttfb_crawler_status=sorted(set(stati)))
        print(f"  mediana: {out['ttfb_crawler_ms']} ms\n")
    else:
        out["ttfb_crawler_errore"] = "nessuna misura riuscita"
        print("  nessuna misura riuscita\n")

    chiave = chiave_api(a.chiave)
    if not chiave:
        print("Nessuna chiave PageSpeed: salto i dati reali di Chrome.")
        print(f"  Mettila in {a.chiave} oppure in PSI_API_KEY. La chiave è gratuita.")
        out["psi"] = "nessuna chiave"
    else:
        print(f"PageSpeed Insights ({a.strategia})")
        dati, errore = psi(base, chiave, a.strategia)
        if errore:
            print(f"  {errore}")
            out["psi_errore"] = errore
        else:
            campo = (dati.get("loadingExperience") or {}).get("metrics", {}) \
                .get("EXPERIMENTAL_TIME_TO_FIRST_BYTE")
            origine = (dati.get("originLoadingExperience") or {}).get("metrics", {}) \
                .get("EXPERIMENTAL_TIME_TO_FIRST_BYTE")
            fonte = "pagina" if campo else "origine" if origine else None
            m = campo or origine
            if m:
                out.update(ttfb_campo_ms=m.get("percentile"),
                           ttfb_campo_categoria=m.get("category"), ttfb_campo_fonte=fonte)
                print(f"  utenti reali (p75, {fonte}): {m.get('percentile')} ms — {m.get('category')}")
            else:
                out["ttfb_campo_ms"] = None
                print("  nessun dato di campo: traffico insufficiente per CrUX")
            lab = (dati.get("lighthouseResult") or {}).get("audits", {}).get("server-response-time", {})
            if lab.get("numericValue") is not None:
                out["ttfb_lab_ms"] = round(lab["numericValue"])
                print(f"  laboratorio (una esecuzione): {out['ttfb_lab_ms']} ms")
            punteggio = ((dati.get("lighthouseResult") or {}).get("categories", {})
                         .get("performance", {}).get("score"))
            if punteggio is not None:
                out["lighthouse_performance"] = round(punteggio * 100)

    if out.get("ttfb_campo_ms") and out.get("ttfb_crawler_ms"):
        out["scarto_ms"] = out["ttfb_crawler_ms"] - out["ttfb_campo_ms"]
        print(f"\nScarto fra assistente e utenti reali: {out['scarto_ms']:+} ms")

    (cartella / "velocita.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                            encoding="utf-8")
    print(f"\nvelocita.json in {cartella}")


if __name__ == "__main__":
    main()
