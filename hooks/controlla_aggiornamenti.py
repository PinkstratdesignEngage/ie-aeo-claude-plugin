#!/usr/bin/env python3
"""Hook SessionStart: controlla se i dati delle fonti IE-AEO del cliente sono da aggiornare.

Agisce solo nei repo dei clienti, per le fonti configurate:

    fonte           configurazione                       dati                 skill
    Search Console  analisi/search-console/config.json   raw/gsc/<data>/      ie-aeo-search-console
    Semrush         analisi/semrush/config.json          raw/semrush/<data>/  ie-aeo-semrush
    Ahrefs          analisi/ahrefs/config.json           raw/ahrefs/<data>/   ie-aeo-ahrefs
    HubSpot AEO     analisi/hubspot-aeo/config.json      raw/hubspot-aeo/<data>/  ie-aeo-hubspot-aeo
    GA4             analisi/ga4/config.json              raw/ga4/<data>/      ie-aeo-ga4

Una fonte è da aggiornare se l'ultima cartella con data (AAAA-MM-GG) è più vecchia di
frequenza_giorni della sua configurazione (default 30), o non c'è. HubSpot AEO e GA4 si
aggiornano senza chiedere, perché sono solo letture senza crediti; Search Console, Semrush e Ahrefs si
propongono (Semrush consuma crediti, Ahrefs unità API). Semrush e Ahrefs sono alternativi: un
cliente ha la configurazione dell'uno o dell'altro. Lo script non scarica nulla: lo dice a Claude.

Propone anche, se il cliente li ha configurati:
- il piano editoriale (contenuti/piano-editoriale/config.json) quando manca il file del mese:
  dal giorno_preparazione (default 20) quello del mese successivo, prima quello corrente;
- la revisione dei prompt HubSpot AEO (analisi/prompt-aeo/config.json) e l'analisi della
  knowledge base (analisi/kb-advisor/config.json) quando l'ultimo report AAAA-MM-GG.md è più
  vecchio di frequenza_giorni (default 30);
- la mappa della knowledge base (analisi/knowledge-graph/config.json) quando un file
  Markdown della knowledge base è cambiato dopo l'ultimo commit di grafo.json, anche solo
  in locale. Restano fuori le cartelle che la mappa non legge (_privato/, raw/ e le altre);
- l'indice di ricerca sui materiali originali (fonti/indice-raw/config.json) quando manca
  in locale (.indice/manifest.json) o quando un file di raw/ da indicizzare è cambiato dopo
  il commit dell'indice.
"""
import datetime as dt
import json
import os
import re
import subprocess
import sys
from pathlib import Path

FONTI = [
    ("Search Console", "search-console", "gsc", "ie-aeo-search-console", "proponi"),
    ("Semrush", "semrush", "semrush", "ie-aeo-semrush", "proponi"),
    ("Ahrefs", "ahrefs", "ahrefs", "ie-aeo-ahrefs", "proponi"),
    ("HubSpot AEO", "hubspot-aeo", "hubspot-aeo", "ie-aeo-hubspot-aeo", "aggiorna"),
    ("GA4", "ga4", "ga4", "ie-aeo-ga4", "aggiorna"),
]


def ultima_data(cartella):
    date = []
    if cartella.is_dir():
        for d in cartella.iterdir():
            if d.is_dir() and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d.name):
                try:
                    date.append(dt.date.fromisoformat(d.name))
                except ValueError:
                    pass
    return max(date) if date else None


# Le cartelle che costruisci_grafo.py lascia sempre fuori: un loro cambio non invecchia la mappa.
FUORI_MAPPA = ("_privato/", "raw/", ".git/", "node_modules/", ".claude/", "app/", "tools/")


def file_cambiati(repo):
    """I file Markdown della knowledge base cambiati dopo l'ultima mappa, in ordine.

    Cambiati rispetto all'ultimo commit di grafo.json (committati e non, più i file nuovi)
    e più recenti di grafo.json sul disco: così una mappa appena rigenerata, non ancora
    committata, non fa scattare il promemoria."""
    conf = repo / "analisi" / "knowledge-graph" / "config.json"
    grafo = conf.parent / "grafo.json"
    if not (conf.exists() and grafo.exists()):
        return []

    def git(*args):
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=4)
        return r.stdout if r.returncode == 0 else ""

    # Il commit che ha scritto l'ultimo grafo; se il grafo non è mai stato committato, niente.
    ultimo = git("log", "-1", "--format=%H", "--", "analisi/knowledge-graph/grafo.json").strip()
    if not ultimo:
        return []
    nomi = git("diff", "--name-only", ultimo).splitlines() + git("ls-files", "--others", "--exclude-standard").splitlines()
    soglia = grafo.stat().st_mtime
    return sorted({n for n in nomi if n.endswith(".md") and not n.startswith(FUORI_MAPPA)
                   and (repo / n).exists() and (repo / n).stat().st_mtime > soglia})


def mappa(repo):
    """La mappa della knowledge base da proporre, se è più vecchia dei file."""
    cambiati = file_cambiati(repo)
    if not cambiati:
        return []
    return [f"Mappa della knowledge base ({len(cambiati)} file Markdown cambiati dall'ultima mappa): "
            "skill ie-aeo-knowledgegraph"]


# Stesse regole di skills/ie-aeo-indice-raw/scripts/indice.py (da_indicizzare): tenerle allineate.
INDICE_ESTENSIONI = (".pdf", ".docx", ".pptx", ".xlsx", ".md", ".html")
INDICE_ESCLUDI = ["raw/gsc", "raw/ga4", "raw/semrush", "raw/ahrefs", "raw/hubspot-aeo"]


def indice_raw(repo):
    """L'indice di raw/ da scaricare o da aggiornare, se il cliente lo usa.

    La configurazione sta in fonti/ e non in analisi/: l'indice non produce report, è uno strumento sulle fonti."""
    conf = repo / "fonti" / "indice-raw" / "config.json"
    if not conf.exists():
        return []
    manifest = repo / ".indice" / "manifest.json"
    skill = "skill ie-aeo-indice-raw"
    if not manifest.exists():
        return [f"Indice dei materiali originali assente in questo computer (si scarica da GitLab): {skill}"]
    try:
        cfg = json.loads(conf.read_text(encoding="utf-8"))
        commit = json.loads(manifest.read_text(encoding="utf-8"))["commit"]
    except (OSError, ValueError, KeyError):
        return []
    cartelle = cfg.get("cartelle", ["raw"])
    escludi = cfg.get("escludi", INDICE_ESCLUDI)

    def git(*args):
        r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=4)
        return r.stdout if r.returncode == 0 else ""

    def sotto(nome, radici):
        return any(nome == c or nome.startswith(c.rstrip("/") + "/") for c in radici)

    nomi = git("diff", "--name-only", commit, "--", *cartelle).splitlines()
    nomi += git("ls-files", "--others", "--exclude-standard", "--", *cartelle).splitlines()
    cambiati = {n for n in nomi if n.lower().endswith(INDICE_ESTENSIONI) and not n.endswith(".link.md")
                and Path(n).name not in ("README.md", "indice.md") and sotto(n, cartelle) and not sotto(n, escludi)}
    if not cambiati:
        return []
    return [f"Indice dei materiali originali da aggiornare ({len(cambiati)} file di raw/ cambiati dopo l'indice): "
            f"{skill} (prima scarica l'ultima versione da GitLab, poi ricostruisci solo se serve)"]


# Revisioni periodiche: un report AAAA-MM-GG.md nella cartella della configurazione.
REVISIONI = [
    ("prompt-aeo", "Revisione dei prompt HubSpot AEO", "ie-aeo-prompt"),
    ("kb-advisor", "Analisi della knowledge base e piano per completarla", "ie-aeo-kb-advisor"),
]


def mese_dopo(oggi):
    return (oggi.replace(day=1) + dt.timedelta(days=32)).replace(day=1)


def lavori(repo, oggi):
    """Piano editoriale e revisione dei prompt da proporre."""
    voci = []
    conf = repo / "contenuti" / "piano-editoriale" / "config.json"
    if conf.exists():
        try:
            giorno = int(json.loads(conf.read_text(encoding="utf-8")).get("giorno_preparazione", 20))
        except (OSError, ValueError):
            giorno = 20
        mese = mese_dopo(oggi) if oggi.day >= giorno else oggi
        nome = f"{mese:%Y-%m}"
        if not (conf.parent / f"{nome}.md").exists():
            voci.append(f"Piano editoriale (manca il piano {nome}): skill ie-aeo-piano-editoriale")
    for cartella, nome, skill in REVISIONI:
        conf = repo / "analisi" / cartella / "config.json"
        if not conf.exists():
            continue
        try:
            frequenza = int(json.loads(conf.read_text(encoding="utf-8")).get("frequenza_giorni", 30))
        except (OSError, ValueError):
            frequenza = 30
        date = []
        for f in conf.parent.glob("*.md"):
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", f.stem):
                try:
                    date.append(dt.date.fromisoformat(f.stem))
                except ValueError:
                    pass
        ultima = max(date) if date else None
        if not ultima or (oggi - ultima).days >= frequenza:
            stato = f"ultima del {ultima}" if ultima else "nessuna revisione"
            voci.append(f"{nome} ({stato}): skill {skill}")
    return voci


def main():
    repo = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    oggi = dt.date.today()
    da_proporre, da_aggiornare = [], []
    for nome, conf_dir, raw_dir, skill, modo in FONTI:
        config = repo / "analisi" / conf_dir / "config.json"
        if not config.exists():
            continue
        try:
            cfg = json.loads(config.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        frequenza = int(cfg.get("frequenza_giorni", 30))
        ultima = ultima_data(repo / "raw" / raw_dir)
        if ultima and (oggi - ultima).days < frequenza:
            continue
        stato = f"ultima estrazione del {ultima}, {(oggi - ultima).days} giorni fa" if ultima else "nessuna estrazione"
        voce = f"{nome} ({stato}, frequenza {frequenza} giorni): skill {skill}"
        (da_aggiornare if modo == "aggiorna" else da_proporre).append(voce)
    da_proporre += lavori(repo, oggi) + mappa(repo) + indice_raw(repo)
    if not (da_proporre or da_aggiornare):
        return

    righe, contesto = [], ["[Promemoria IE-AEO]"]
    if da_aggiornare:
        righe.append("Da aggiornare ora: " + "; ".join(da_aggiornare) + ".")
        contesto.append(
            "Queste fonti sono in sola lettura e non consumano crediti: " + "; ".join(da_aggiornare)
            + ". Prima di rispondere alla prima richiesta dell'utente, avvisalo in una riga e lancia la skill indicata. "
            "Se la richiesta è urgente o la skill si ferma (connettore assente, permessi mancanti), rispondi prima e "
            "riproponi l'aggiornamento a fine turno. Non fare commit senza il suo ok.")
    if da_proporre:
        righe.append("Da proporre: " + "; ".join(da_proporre) + ".")
        contesto.append(
            "Queste fonti vanno solo proposte all'utente, una volta e senza bloccare la sua richiesta: "
            + "; ".join(da_proporre) + ". Semrush consuma crediti e Ahrefs unità API: le loro skill mostrano "
            "il preventivo e chiedono l'ok prima di estrarre."
            " Piano editoriale, prompt e analisi della knowledge base si propongono dopo gli aggiornamenti dei dati, perché li usano."
            " La mappa si rigenera e si ripubblica allo stesso link: con con_testo true nel suo config.json, "
            "con --con-testo. L'indice dei materiali originali si scarica da GitLab senza chiedere (è una lettura); "
            "ricostruirlo e caricarlo su GitLab si propone.")
    print(json.dumps({
        "systemMessage": "Promemoria IE-AEO. " + " ".join(righe),
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": " ".join(contesto)},
    }, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)  # un promemoria non deve mai bloccare la sessione
