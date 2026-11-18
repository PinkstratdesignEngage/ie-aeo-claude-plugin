#!/usr/bin/env python3
"""Indice di ricerca sui materiali originali (raw/) della knowledge base di un cliente.

Gira nell'ambiente della skill (~/.cache/ie-aeo-indice/venv, creato da ambiente.py), dalla
radice del repo del cliente:

    indice.py costruisci [--da-zero]       estrae i file nuovi o cambiati, calcola gli embedding, scrive .indice/
    indice.py stato [--json]               confronta l'indice con raw/ e con l'ambiente
    indice.py cerca "domanda" [...]        ricerca ibrida (default), vettoriale o per parola
    indice.py carica                       pubblica .indice/ come nuova versione nel Package Registry di GitLab
    indice.py scarica [--versione V]       scarica l'ultima versione (o quella indicata) dal Package Registry

L'indice sta in .indice/ (fuori da git) e contiene:
    manifest.json   commit di raw/, impronta di ogni file, versioni di modello e librerie, chi e quando
    blocchi/        un JSONL per documento: i blocchi estratti, riusati quando il file non cambia
    raw.lance/      la tabella LanceDB con testo, metadati, vettore e indice per parola (BM25)

Le versioni caricate non si sovrascrivono mai: ogni caricamento è una versione nuova del pacchetto.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.parse
from importlib import metadata
from pathlib import Path

BASE = Path.home() / ".cache" / "ie-aeo-indice"
os.environ.setdefault("HF_HOME", str(BASE / "modelli"))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# Cambiare FORMATO quando cambiano estrazione, divisione o tabella: gli indici vecchi vanno ricostruiti.
FORMATO = 2
MODELLO = "BAAI/bge-m3"
REVISIONE_MODELLO = "5617a9f61b028005a4858fdac845db406aefb181"
MAX_TOKEN = 512

DIR = Path(".indice")
CONFIG = Path("fonti/indice-raw/config.json")
CONFIG_DEFAULT = {
    "cartelle": ["raw"],
    # dati di analytics: si interrogano con SQL o con gli script delle loro skill, non per somiglianza
    "escludi": ["raw/gsc", "raw/ga4", "raw/semrush", "raw/ahrefs", "raw/hubspot-aeo"],
    "pacchetto": "indice-raw",
}
ESTENSIONI = {".pdf", ".docx", ".pptx", ".xlsx", ".md", ".html"}
NOMI_ESCLUSI = {"README.md", "indice.md"}
FILE_PACCHETTO = "indice.tar.gz"
CAMPI = ["id", "file", "pagine", "sezione", "lingua", "analizzato", "testo"]


# --- configurazione, file e git ---------------------------------------------------------------

def config() -> dict:
    cfg = dict(CONFIG_DEFAULT)
    if CONFIG.exists():
        cfg.update(json.loads(CONFIG.read_text(encoding="utf-8")))
    return cfg


def da_indicizzare(percorso: str, cfg: dict) -> bool:
    p = Path(percorso)
    if p.suffix.lower() not in ESTENSIONI or p.name in NOMI_ESCLUSI or p.name.endswith(".link.md"):
        return False
    dentro = any(percorso == c or percorso.startswith(c.rstrip("/") + "/") for c in cfg["cartelle"])
    fuori = any(percorso == e or percorso.startswith(e.rstrip("/") + "/") for e in cfg["escludi"])
    return dentro and not fuori


def elenco_file(cfg: dict) -> list[str]:
    trovati = set()
    for cartella in cfg["cartelle"]:
        for f in Path(cartella).rglob("*"):
            if f.is_file() and da_indicizzare(f.as_posix(), cfg):
                trovati.add(f.as_posix())
    return sorted(trovati)


def impronta(percorso: str) -> str:
    h = hashlib.sha1()
    with open(percorso, "rb") as f:
        for pezzo in iter(lambda: f.read(1 << 20), b""):
            h.update(pezzo)
    return h.hexdigest()


def git(*args: str, ok_errore: bool = False) -> str:
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    if r.returncode != 0 and not ok_errore:
        sys.exit(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip() if r.returncode == 0 else ""


def cambiati_dopo(commit: str, cfg: dict) -> list[str]:
    """File da indicizzare cambiati dopo il commit dell'indice: committati dopo, modificati o nuovi in locale."""
    nomi = git("diff", "--name-only", commit, "--", *cfg["cartelle"], ok_errore=True).splitlines()
    nomi += git("ls-files", "--others", "--exclude-standard", "--", *cfg["cartelle"]).splitlines()
    return sorted({n for n in nomi if da_indicizzare(n, cfg)})


def lingua(percorso: str) -> str:
    p = percorso.lower()
    if re.search(r"(^|[_\-/.])(en|en-gb|en-us)([_\-/.]|$)", p):
        return "en"
    if re.search(r"(^|[_\-/.])(it|it-it)([_\-/.]|$)", p):
        return "it"
    return ""


def versioni_ambiente() -> dict:
    def v(nome):
        try:
            return metadata.version(nome)
        except metadata.PackageNotFoundError:
            return None
    return {"modello": MODELLO, "revisione_modello": REVISIONE_MODELLO, "formato": FORMATO,
            "docling": v("docling"), "lancedb": v("lancedb"), "sentence_transformers": v("sentence-transformers")}


def leggi_manifest(cartella: Path = DIR) -> dict | None:
    f = cartella / "manifest.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def incompatibilita(manifest: dict, per_costruire: bool) -> list[str]:
    """Cosa impedisce di aggiornare (o di usare per la ricerca vettoriale) un indice con l'ambiente locale."""
    locale = versioni_ambiente()
    chiavi = ["formato", "modello", "revisione_modello"] + (["docling"] if per_costruire else [])
    return [f"{k}: indice {manifest['ambiente'].get(k)}, locale {locale.get(k)}"
            for k in chiavi if manifest["ambiente"].get(k) != locale.get(k)]


# --- estrazione ---------------------------------------------------------------------------------

def nome_blocchi(percorso: str) -> str:
    return hashlib.sha1(percorso.encode()).hexdigest()[:12] + ".jsonl"


def estrattore():
    """Docling: tabelle in Markdown (non righe 'chiave = valore'), blocchi di al massimo MAX_TOKEN token di bge-m3."""
    from docling.chunking import HybridChunker
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling_core.transforms.chunker.hierarchical_chunker import ChunkingDocSerializer, ChunkingSerializerProvider
    from docling_core.transforms.serializer.markdown import MarkdownTableSerializer
    from transformers import AutoTokenizer

    class TabelleMarkdown(ChunkingSerializerProvider):
        def get_serializer(self, doc):
            return ChunkingDocSerializer(doc=doc, table_serializer=MarkdownTableSerializer())

    opzioni = PdfPipelineOptions(do_ocr=False, do_table_structure=True, generate_page_images=False)
    convertitore = DocumentConverter(
        allowed_formats=[InputFormat.PDF, InputFormat.DOCX, InputFormat.PPTX, InputFormat.XLSX, InputFormat.MD, InputFormat.HTML],
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=opzioni)})
    tokenizer = AutoTokenizer.from_pretrained(MODELLO, revision=REVISIONE_MODELLO)
    chunker = HybridChunker(tokenizer=tokenizer, max_tokens=MAX_TOKEN, merge_peers=True,
                            serializer_provider=TabelleMarkdown())

    def estrai(percorso: str, hash_file: str) -> list[dict]:
        doc = convertitore.convert(Path(percorso)).document
        righe = []
        for i, blocco in enumerate(chunker.chunk(doc)):
            pagine = sorted({p.page_no for item in blocco.meta.doc_items for p in getattr(item, "prov", [])})
            righe.append({
                "id": f"{percorso}#{i}",
                "file": percorso,
                "hash": hash_file,
                "pagine": pagine,
                "sezione": " › ".join(blocco.meta.headings or []),
                "lingua": lingua(percorso),
                "analizzato": "-analizzato" in Path(percorso).name,
                "testo": blocco.text,
                # con titolo del documento e sezione: è il testo che va negli embedding e nell'indice per parola.
                # Senza "-analizzato", così rinominare il file non cambia i vettori.
                "testo_contesto": f"{Path(percorso).stem.replace('-analizzato', '')}\n{chunker.contextualize(blocco)}",
            })
        return righe

    return estrai


# --- modello e tabella ----------------------------------------------------------------------------

_modello = None


def modello():
    global _modello
    if _modello is None:
        import torch
        from sentence_transformers import SentenceTransformer
        dispositivo = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
        _modello = SentenceTransformer(MODELLO, revision=REVISIONE_MODELLO, device=dispositivo)
        _modello.max_seq_length = 1024
    return _modello


def tabella():
    import lancedb
    return lancedb.connect(DIR).open_table("raw")


# --- comandi ----------------------------------------------------------------------------------------

def costruisci(args) -> None:
    cfg = config()
    precedente = leggi_manifest()
    if precedente and not args.da_zero:
        problemi = incompatibilita(precedente, per_costruire=True)
        if problemi:
            sys.exit("L'indice esistente è stato costruito con un ambiente diverso (" + "; ".join(problemi) + ").\n"
                     "Aggiorna l'ambiente con ambiente.py, oppure ricostruisci tutto con --da-zero.")
    vecchi_file = {} if (args.da_zero or not precedente) else precedente["file"]

    t0 = time.time()
    file = elenco_file(cfg)
    impronte = {f: impronta(f) for f in file}
    da_estrarre = [f for f in file if vecchi_file.get(f, {}).get("hash") != impronte[f]]
    tolti = sorted(set(vecchi_file) - set(file))

    cartella_blocchi = DIR / "blocchi"
    cartella_blocchi.mkdir(parents=True, exist_ok=True)
    # File rinominati (per esempio con -analizzato): stesso contenuto, blocchi riusati con il nome nuovo
    tolti_per_hash = {vecchi_file[f]["hash"]: f for f in tolti}
    rinominati = 0
    for f in list(da_estrarre):
        vecchio = tolti_per_hash.get(impronte[f])
        sorgente = cartella_blocchi / nome_blocchi(vecchio) if vecchio else None
        if not sorgente or not sorgente.exists():
            continue
        with (cartella_blocchi / nome_blocchi(f)).open("w", encoding="utf-8") as out:
            for l in sorgente.open(encoding="utf-8"):
                r = json.loads(l)
                r.update(id=f"{f}#{r['id'].rsplit('#', 1)[1]}", file=f, lingua=lingua(f),
                         analizzato="-analizzato" in Path(f).name)
                out.write(json.dumps(r, ensure_ascii=False) + "\n")
        da_estrarre.remove(f)
        rinominati += 1
    print(f"{len(file)} file da indicizzare: {len(file) - len(da_estrarre) - rinominati} invariati, "
          f"{rinominati} rinominati, {len(da_estrarre)} nuovi o cambiati, {len(tolti) - rinominati} tolti", flush=True)
    for f in tolti:
        (cartella_blocchi / nome_blocchi(f)).unlink(missing_ok=True)

    errori = {}
    if da_estrarre:
        estrai = estrattore()
        for n, f in enumerate(da_estrarre, 1):
            t = time.time()
            try:
                righe = estrai(f, impronte[f])
                with (cartella_blocchi / nome_blocchi(f)).open("w", encoding="utf-8") as out:
                    for r in righe:
                        out.write(json.dumps(r, ensure_ascii=False) + "\n")
                stato = f"{len(righe)} blocchi"
            except Exception as e:  # un file rotto non deve fermare gli altri
                errori[f] = repr(e)[:300]
                (cartella_blocchi / nome_blocchi(f)).unlink(missing_ok=True)
                stato = f"ERRORE {e!r}"[:200]
            print(f"[{n}/{len(da_estrarre)}] {f}: {stato} ({time.time() - t:.0f}s)", flush=True)

    righe, blocchi_per_file = [], {}
    for f in file:
        percorso = cartella_blocchi / nome_blocchi(f)
        if f in errori or not percorso.exists():
            continue
        rs = [json.loads(l) for l in percorso.open(encoding="utf-8")]
        righe += rs
        blocchi_per_file[f] = len(rs)

    # vettori già calcolati: si riusano per i blocchi dei file invariati o rinominati.
    # La chiave è contenuto + posizione del blocco, non il percorso: il testo degli embedding non contiene "-analizzato".
    def chiave(r):
        return r["hash"], r["id"].rsplit("#", 1)[1]

    vettori = {}
    if not args.da_zero and (DIR / "raw.lance").exists():
        vecchia = tabella().to_arrow().select(["id", "hash", "vector"]).to_pylist()
        vettori = {chiave(r): r["vector"] for r in vecchia}
    mancanti = [r for r in righe if chiave(r) not in vettori]
    if mancanti:
        print(f"embedding di {len(mancanti)} blocchi...", flush=True)
        calcolati = modello().encode([r["testo_contesto"] for r in mancanti], batch_size=8,
                                     normalize_embeddings=True, show_progress_bar=False)
        for r, v in zip(mancanti, calcolati):
            vettori[chiave(r)] = v.tolist()

    import lancedb
    db = lancedb.connect(DIR)
    if righe:
        t = db.create_table("raw", data=[{**r, "vector": vettori[chiave(r)]} for r in righe], mode="overwrite")
        t.create_fts_index("testo_contesto", replace=True)

    commit = git("rev-parse", "HEAD")
    sporchi = [l[3:] for l in git("status", "--porcelain", "--", *cfg["cartelle"]).splitlines()]
    manifest = {
        "versione": None,  # la scrive `carica`
        "creato": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "da": git("config", "user.name", ok_errore=True) or os.environ.get("USER", ""),
        "commit": commit,
        "raw_pulito": not any(da_indicizzare(s, cfg) for s in sporchi),
        "config": {k: cfg[k] for k in ("cartelle", "escludi")},
        "ambiente": versioni_ambiente(),
        "blocchi": len(righe),
        "file": {f: {"hash": impronte[f], "blocchi": blocchi_per_file.get(f, 0)} for f in file},
        "errori": errori,
    }
    (DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"indice pronto: {len(righe)} blocchi da {len(blocchi_per_file)} file, commit {commit[:7]}"
          f"{'' if manifest['raw_pulito'] else ' + modifiche locali non committate'}, "
          f"{len(errori)} errori, {time.time() - t0:.0f}s", flush=True)


def stato(args) -> None:
    cfg = config()
    m = leggi_manifest()
    if not m:
        risultato = {"indice": False, "messaggio": "Nessun indice in .indice/: scaricalo (scarica) o costruiscilo (costruisci)."}
    else:
        file = elenco_file(cfg)
        cambiati = [f for f in file if m["file"].get(f, {}).get("hash") != impronta(f)]
        risultato = {
            "indice": True,
            "versione": m.get("versione"),
            "creato": m["creato"], "da": m["da"], "commit": m["commit"][:7], "raw_pulito": m["raw_pulito"],
            "file": len(m["file"]), "blocchi": m["blocchi"], "errori": list(m.get("errori", {})),
            "nuovi_o_cambiati": cambiati,
            "tolti": sorted(set(m["file"]) - set(file)),
            "incompatibile_per_costruire": incompatibilita(m, per_costruire=True),
            "incompatibile_per_ricerca_vettoriale": incompatibilita(m, per_costruire=False),
        }
    if args.json:
        print(json.dumps(risultato, ensure_ascii=False, indent=1))
        return
    if not risultato["indice"]:
        print(risultato["messaggio"])
        return
    r = risultato
    print(f"Indice {r['versione'] or '(locale, non caricato)'}: {r['file']} file, {r['blocchi']} blocchi, "
          f"commit {r['commit']}, creato {r['creato']} da {r['da']}")
    print(f"Da aggiornare: {len(r['nuovi_o_cambiati'])} file nuovi o cambiati, {len(r['tolti'])} tolti")
    for f in r["nuovi_o_cambiati"][:20] + r["tolti"][:20]:
        print(f"  {f}")
    if r["errori"]:
        print(f"File non estratti: {', '.join(r['errori'])}")
    if r["incompatibile_per_costruire"]:
        print("Ambiente diverso da quello dell'indice: " + "; ".join(r["incompatibile_per_costruire"]))


def _condizione(cartella: str | None, lingua_: str | None) -> str | None:
    parti = []
    if cartella:
        parti.append("file LIKE '" + cartella.rstrip("/").replace("'", "''") + "/%'")
    if lingua_:
        parti.append("lingua = '" + lingua_.replace("'", "''") + "'")
    return " AND ".join(parti) or None


def _vettoriale(t, domanda, n, cond):
    v = modello().encode(domanda, normalize_embeddings=True)
    q = t.search(v).metric("cosine").select(CAMPI + ["_distance"]).limit(n)
    return (q.where(cond, prefilter=True) if cond else q).to_list()


def _parole(t, domanda, n, cond):
    q = t.search(domanda, query_type="fts", fts_columns="testo_contesto").select(CAMPI + ["_score"]).limit(n)
    return (q.where(cond, prefilter=True) if cond else q).to_list()


def _ibrida(t, domanda, n, cond, profondita=50, k_rrf=60):
    """Fusione per rango (RRF) dei due elenchi: conta la posizione, non il punteggio, che non è confrontabile."""
    punteggi, righe = {}, {}
    for elenco in (_vettoriale(t, domanda, profondita, cond), _parole(t, domanda, profondita, cond)):
        for rango, r in enumerate(elenco):
            punteggi[r["id"]] = punteggi.get(r["id"], 0) + 1 / (k_rrf + rango + 1)
            righe[r["id"]] = r
    return [righe[i] for i in sorted(punteggi, key=punteggi.get, reverse=True)[:n]]


def cerca(args) -> None:
    m = leggi_manifest()
    if not m:
        sys.exit("Nessun indice in .indice/: lancia prima `scarica` o `costruisci`.")
    avvisi = []
    cambiati = cambiati_dopo(m["commit"], config())
    if cambiati:
        avvisi.append(f"{len(cambiati)} file di raw/ sono cambiati dopo l'indice (commit {m['commit'][:7]}): "
                      "per questi i risultati possono mancare o essere vecchi.")
    modo = args.modo
    if modo != "parole":
        problema = incompatibilita(m, per_costruire=False)
        try:
            import sentence_transformers  # noqa: F401
        except ImportError:
            problema = ["librerie per la ricerca vettoriale non installate (ambiente solo ricerca)"]
        if problema:
            avvisi.append("Ricerca per parola al posto della " + modo + ": " + "; ".join(problema) + ".")
            modo = "parole"
    funzione = {"ibrida": _ibrida, "vettoriale": _vettoriale, "parole": _parole}[modo]
    t, cond = tabella(), _condizione(args.cartella, args.lingua)

    risultati = {d: funzione(t, d, args.k, cond) for d in args.domande}
    if args.json:
        print(json.dumps({"modo": modo, "avvisi": avvisi, "risultati": {
            d: [{k: r[k] for k in CAMPI} for r in rs] for d, rs in risultati.items()}}, ensure_ascii=False, indent=1))
        return
    for a in avvisi:
        print(f"> Attenzione: {a}")
    for d, rs in risultati.items():
        print(f"\n## {d}  ({modo}, {len(rs)} risultati)")
        for i, r in enumerate(rs, 1):
            pagine = f" · pagine {', '.join(map(str, r['pagine']))}" if r["pagine"] else ""
            sezione = f" · {r['sezione']}" if r["sezione"] else ""
            print(f"\n### {i}. {r['file']}{pagine}{sezione}\n{r['testo']}")


# --- GitLab: Package Registry -------------------------------------------------------------------------

def progetto() -> tuple[str, str]:
    """Host e percorso codificato del progetto GitLab, dal remoto origin."""
    url = git("remote", "get-url", "origin")
    m = re.match(r"^(?:https?://(?:[^@/]+@)?|git@)([^/:]+)[/:](.+?)(?:\.git)?/?$", url)
    if not m:
        sys.exit(f"Remoto origin non riconosciuto: {url}")
    return m.group(1), urllib.parse.quote(m.group(2), safe="")


def glab(host: str, *args: str, binario: bool = False):
    r = subprocess.run(["glab", "api", *args], capture_output=True, env={**os.environ, "GITLAB_HOST": host})
    if r.returncode != 0:
        sys.exit(f"glab api {args[0]}: {r.stderr.decode(errors='replace').strip() or r.stdout[:300]}")
    return r.stdout if binario else json.loads(r.stdout or b"null")


def versioni_remote(host: str, prog: str, pacchetto: str) -> list[dict]:
    pacchetti = glab(host, f"projects/{prog}/packages?package_type=generic&package_name={pacchetto}"
                           "&order_by=created_at&sort=desc&per_page=100")
    return [p for p in pacchetti if p["name"] == pacchetto]


def carica(args) -> None:
    m = leggi_manifest()
    if not m or not (DIR / "raw.lance").exists():
        sys.exit("Nessun indice da caricare: lancia prima `costruisci`.")
    if not m["raw_pulito"]:
        sys.exit("L'indice contiene modifiche di raw/ non committate: committale e pushale, poi ricostruisci.")
    git("fetch", "-q", "origin")
    # basta che il commit sia su un ramo di GitLab (anche quello di una merge request): i colleghi
    # possono scaricare gli stessi materiali. Il manifest dice quale ramo.
    rami = [r.strip() for r in git("branch", "-r", "--contains", m["commit"], ok_errore=True).splitlines()
            if r.strip().startswith("origin/") and "->" not in r]
    if not rami:
        sys.exit(f"Il commit dell'indice ({m['commit'][:7]}) non è su nessun ramo di GitLab: "
                 "l'indice deve corrispondere a materiali che i colleghi possono scaricare. Fai push, poi ricarica.")
    principale = git("rev-parse", "--abbrev-ref", "origin/HEAD", ok_errore=True) or "origin/main"
    m["rami"] = rami
    if principale not in rami:
        print(f"Nota: il commit è su {', '.join(rami)}, non ancora su {principale}. "
              "Dopo il merge l'hook segnalerà l'indice da aggiornare: basterà ricostruirlo e caricarlo di nuovo.")
    if cambiati_dopo(m["commit"], config()):
        sys.exit("raw/ è cambiato dopo l'indice: ricostruiscilo prima di caricarlo.")

    host, prog = progetto()
    pacchetto = config()["pacchetto"]
    esistenti = {p["version"] for p in versioni_remote(host, prog, pacchetto)}
    base = f"{dt.date.today():%Y.%m.%d}-{m['commit'][:7]}"
    versione = base
    n = 2
    while versione in esistenti:  # mai sovrascrivere una versione già caricata
        versione, n = f"{base}-{n}", n + 1

    m["versione"] = versione
    (DIR / "manifest.json").write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        archivio = Path(tmp) / FILE_PACCHETTO
        with tarfile.open(archivio, "w:gz") as tar:
            for nome in ("manifest.json", "blocchi", "raw.lance"):
                tar.add(DIR / nome, arcname=nome)
        mb = archivio.stat().st_size / 1e6
        for nome, percorso in (("manifest.json", DIR / "manifest.json"), (FILE_PACCHETTO, archivio)):
            glab(host, "-X", "PUT", f"projects/{prog}/packages/generic/{pacchetto}/{versione}/{nome}",
                 "--input", str(percorso), "--header", "Content-Type: application/octet-stream")
    print(f"Caricata la versione {versione} del pacchetto {pacchetto} ({mb:.1f} MB): "
          f"{m['blocchi']} blocchi, commit {m['commit'][:7]}.")


def scarica(args) -> None:
    host, prog = progetto()
    pacchetto = config()["pacchetto"]
    versioni = versioni_remote(host, prog, pacchetto)
    if not versioni:
        sys.exit(f"Nessuna versione del pacchetto {pacchetto} nel Package Registry: costruisci l'indice e caricalo.")
    scelta = next((v for v in versioni if v["version"] == args.versione), None) if args.versione else versioni[0]
    if not scelta:
        sys.exit(f"Versione {args.versione} non trovata. Disponibili: {', '.join(v['version'] for v in versioni[:10])}")
    versione = scelta["version"]
    locale = leggi_manifest()
    if locale and locale.get("versione") == versione and not args.forza:
        print(f"L'indice locale è già la versione {versione}.")
        return

    base = f"projects/{prog}/packages/generic/{pacchetto}/{versione}"
    nuovo, vecchio = Path(".indice.nuovo"), Path(".indice.vecchio")
    for p in (nuovo, vecchio):
        if p.exists():
            shutil.rmtree(p)
    nuovo.mkdir()
    archivio = nuovo / FILE_PACCHETTO
    archivio.write_bytes(glab(host, f"{base}/{FILE_PACCHETTO}", binario=True))
    with tarfile.open(archivio) as tar:
        tar.extractall(nuovo, filter="data")
    archivio.unlink()
    m = leggi_manifest(nuovo)
    if not m or m.get("versione") != versione:
        shutil.rmtree(nuovo)
        sys.exit(f"Il pacchetto {versione} non contiene un manifest valido: indice locale lasciato com'era.")
    if DIR.exists():
        DIR.rename(vecchio)
    nuovo.rename(DIR)
    if vecchio.exists():
        shutil.rmtree(vecchio)

    print(f"Scaricata la versione {versione}: {m['blocchi']} blocchi, commit {m['commit'][:7]}, "
          f"creata {m['creato']} da {m['da']}.")
    cambiati = cambiati_dopo(m["commit"], config())
    if cambiati:
        print(f"{len(cambiati)} file di raw/ sono cambiati dopo questa versione: per includerli lancia `costruisci`.")
    problemi = incompatibilita(m, per_costruire=False)
    if problemi:
        print("La ricerca vettoriale non è disponibile con questo ambiente (" + "; ".join(problemi) + "): resta quella per parola.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="comando", required=True)
    p = sub.add_parser("costruisci", help="estrae i file nuovi o cambiati e aggiorna l'indice")
    p.add_argument("--da-zero", action="store_true", help="ignora l'indice esistente e rielabora tutto")
    p = sub.add_parser("stato", help="confronta l'indice con raw/ e con l'ambiente")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("cerca", help="cerca una o più domande")
    p.add_argument("domande", nargs="+")
    p.add_argument("-k", type=int, default=5, help="risultati per domanda (default 5)")
    p.add_argument("--modo", choices=["ibrida", "vettoriale", "parole"], default="ibrida")
    p.add_argument("--cartella", help="solo i file sotto questa cartella, per esempio raw/drive/prodotti")
    p.add_argument("--lingua", help="solo i file in questa lingua (it, en), riconosciuta dal nome del file")
    p.add_argument("--json", action="store_true")
    sub.add_parser("carica", help="carica .indice/ come nuova versione nel Package Registry")
    p = sub.add_parser("scarica", help="scarica una versione dal Package Registry")
    p.add_argument("--versione", help="default: la più recente")
    p.add_argument("--forza", action="store_true", help="scarica anche se è la versione già presente")
    args = parser.parse_args()

    if not Path(".git").exists():
        sys.exit("Lancia lo script dalla radice del repo della knowledge base del cliente.")
    {"costruisci": costruisci, "stato": stato, "cerca": cerca, "carica": carica, "scarica": scarica}[args.comando](args)


if __name__ == "__main__":
    main()
