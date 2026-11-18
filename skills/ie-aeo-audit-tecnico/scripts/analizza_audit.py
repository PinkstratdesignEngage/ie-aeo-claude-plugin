#!/usr/bin/env python3
"""Dai dati grezzi dell'audit tecnico ricava gli indicatori, i giudizi e le azioni.

Uso, dalla radice del repo del cliente:
    python3 -I analizza_audit.py raw/audit-tecnico/<AAAA-MM-GG> [--config analisi/audit-tecnico/config.json]
        [--uscita analisi/audit-tecnico]

Scrive nella cartella dell'estrazione:
    risultati.json   gli indicatori raggruppati per domanda, con spiegazione e conseguenza
    azioni.json      le azioni tecniche, nella forma che ie-aeo-dashboard sa leggere
    elenchi.json     gli elenchi per intero, divisi in colonne, con la spiegazione
                     dell'indicatore, per il foglio di lavoro
    azioni-slide.json le stesse azioni, con quelle che hanno lo stesso rimedio raccolte
                     in una riga: serve alla slide, azioni.json resta piatto

Gli indicatori sono raggruppati per la domanda a cui rispondono, non per tecnologia:

    Ci vedono?                               accesso dei crawler, rendering, certificato, noindex
    Ci capiscono?                            dati strutturati, titoli, date, autore
    Trovano tutto all'interno del sito web?  sitemap, canonical, link rotti
    Quanto aspettano?                        tempo di risposta, peso delle pagine

Ogni indicatore porta con sé `spiegazione` (cosa misura) e `conseguenza` (cosa comporta
quel numero), scritte per una persona non tecnica: la dashboard le mostra nel tooltip.

Le soglie e il perché di ognuna stanno in references/verifiche.md.
"""
import argparse
import datetime as dt
import json
import re
import sys
import urllib.parse
from collections import Counter, defaultdict
from pathlib import Path

# Soglie. Quelle di TTFB sono le ufficiali dei Core Web Vitals; le altre sono nostre e
# motivate in references/verifiche.md.
TTFB_BUONO, TTFB_SCARSO = 800, 1800
TTFB_CRAWLER_BUONO = 1200
PAROLE_SERVE_H2 = 300          # sotto, una pagina senza H2 è legittima
HTML_PESANTE = 1_500_000       # oltre, diversi crawler troncano il documento
TESTO_SOSPETTO = 150           # parole nell'HTML grezzo sotto cui la pagina è quasi vuota
ALT_LUNGO = 125
CERT_IN_SCADENZA = 30

SEZIONI_ATTESE = {
    "blog": ["BlogPosting", "Article", "NewsArticle"],
    "news": ["NewsArticle", "Article", "BlogPosting"],
    "articoli": ["Article", "BlogPosting"],
    "approfondimenti": ["Article", "BlogPosting"],
    "case-study": ["Article", "CaseStudy", "BlogPosting"],
    "case-studies": ["Article", "CaseStudy", "BlogPosting"],
    "prodotti": ["Product", "Service", "Offer"],
    "products": ["Product", "Service", "Offer"],
    "servizi": ["Service", "Product"],
    "services": ["Service", "Product"],
    "soluzioni": ["Service", "Product"],
    "faq": ["FAQPage"],
}
CAMPI_ARTICOLO = ["headline", "datePublished", "author", "image"]
ORGANIZZAZIONE = {"Organization", "Corporation", "LocalBusiness", "OnlineBusiness", "NGO",
                  "EducationalOrganization", "GovernmentOrganization"}


def norm(u):
    u = re.sub(r"^https?://(www\.)?", "", (u or "").strip().lower())
    return u.split("#")[0].split("?")[0].rstrip("/")


def leggi(p, default=None):
    return json.loads(Path(p).read_text(encoding="utf-8")) if Path(p).exists() else default


def tipi_di(blocco):
    t = blocco.get("@type", "")
    return [str(x) for x in (t if isinstance(t, list) else [t]) if x]


def it(n_):
    """Numero in formato italiano: punto per le migliaia, come vuole la copia per i clienti."""
    try:
        return f"{int(n_):,}".replace(",", ".")
    except (TypeError, ValueError):
        return str(n_)


# Che cosa si fa per togliere il problema. E' diverso dalla conseguenza, che dice che cosa
# costa lasciarlo: la dashboard e le slide mostrano questo testo sotto un titolo che promette
# un intervento, e una conseguenza messa li' non dice a nessuno cosa fare lunedi' mattina.
# Sono rimedi generali: il consulente li riscrive per il cliente nella dashboard.
RIMEDI = {
    "crawler-citazione": "Togliere il blocco a questi crawler nel server, nel WAF o nella CDN, "
        "poi riprovare l'accesso. Se il blocco è voluto, metterlo per iscritto: così com'è, "
        "sta decidendo chi non sa che lo sta decidendo.",
    "crawler-ricerca": "Controllare in Search Console se Googlebot raggiunge il sito davvero. "
        "Se il blocco c'è, toglierlo a livello di server o di WAF: non basta il robots.txt.",
    "crawler-addestramento": "Decidere se il blocco è voluto. Se lo è, va bene così e si "
        "dichiara; se non lo è, toglierlo dal robots.txt.",
    "rendering": "Far arrivare il testo già nell'HTML della risposta, con rendering lato "
        "server o pre-rendering, almeno sulle pagine che contano.",
    "noindex": "Controllare che ogni pagina esclusa lo sia per scelta, e togliere il noindex "
        "dalle altre.",
    "ssl": "Servire tutto in HTTPS con un certificato valido, e rinnovarlo prima della scadenza.",
    "schema-organization": "Aggiungere un blocco Organization in JSON-LD su una pagina sola, "
        "con nome, logo, contatti e i profili ufficiali in sameAs.",
    "schema-website": "Aggiungere un blocco WebSite in JSON-LD con il nome del sito e l'URL.",
    "schema-sezione": "Dichiarare nei dati strutturati il tipo giusto sulle pagine della "
        "sezione che non lo hanno.",
    "schema-faq": "Marcare come FAQPage le domande e risposte che la pagina già contiene. "
        "Non inventarne per avere lo schema.",
    "schema-autore": "Dichiarare l'autore negli articoli con un blocco Person collegato, non "
        "solo il nome scritto nel testo.",
    "schema-date": "Dichiarare datePublished negli articoli, e dateModified quando il "
        "contenuto cambia davvero.",
    "h1": "Dare a ogni pagina un solo H1, che dica di cosa parla la pagina.",
    "h2": "Spezzare le pagine lunghe con sottotitoli H2 che seguano il filo del testo.",
    "alt": "Scrivere un alt che descriva l'immagine. Sulle immagini decorative l'alt vuoto "
        "è corretto e va lasciato vuoto.",
    "sitemap": "Pubblicare una sitemap XML e dichiararla nel robots.txt.",
    "sitemap-lastmod": "Far scrivere al CMS un lastmod vero, che cambi quando cambia la pagina.",
    "sitemap-coerenza": "Aggiungere alla sitemap le pagine che mancano, o toglierle dal sito "
        "se non servono più.",
    "link-rotti": "Correggere il link, o reindirizzare l'indirizzo rotto alla pagina che lo "
        "sostituisce.",
    "soft-404": "Far rispondere 404 alle pagine che non esistono, invece di 200 con un "
        "messaggio di errore.",
    "canonical": "Dichiarare un canonical su ogni pagina, che punti a un indirizzo che "
        "risponde 200.",
    "llms-txt": "Valutare se pubblicarlo: nessuno standard lo impone ancora, ma costa poco e "
        "dichiara che cosa si può usare.",
    "peso-html": "Alleggerire l'HTML delle pagine più pesanti: di solito sono dati inline o "
        "contenuto ripetuto.",
    "ttfb-campo": "Intervenire sul tempo di risposta del server: cache, query al database, "
        "dimensionamento dell'hosting.",
    "ttfb-crawler": "Far valere la cache anche per i crawler: spesso è esclusa per gli "
        "user-agent che il CDN non riconosce.",
    "ttfb-cache": "Allungare la durata della cache o scaldarla: oggi la prima richiesta paga "
        "troppo rispetto alle successive.",
}


def rimedio_per(id_):
    """Il rimedio dell'indicatore. Le sezioni hanno un id calcolato (`schema-blog`,
    `schema-catalogo`...): ricadono tutte sullo stesso rimedio."""
    if id_ in RIMEDI:
        return RIMEDI[id_]
    return RIMEDI["schema-sezione"] if id_.startswith("schema-") else ""


def plurale(n_, uno, molti):
    """«1 pagina», non «1 pagine». In un documento che legge il cliente si nota."""
    return uno if n_ == 1 else molti


def ind(id_, gruppo, titolo, stato, valore, spiegazione, conseguenza,
        dettaglio="", elenco=None, base=None, gravita=None, pagine=None,
        etichetta_elenco="Pagine interessate", descrizione_elenco="",
        rimedio="", unita="pagine"):
    """Un indicatore. `spiegazione` e `conseguenza` finiscono nel tooltip della dashboard.

    `elenco` e' quello che si mostra e puo' essere testo ("url — piu' H1"); `pagine` sono
    URL veri e basta, perche' la dashboard li usa per pesare l'azione con le impressioni di
    Search Console. Tenerli insieme faceva finire frasi intere fra le pagine del piano.

    `conseguenza` dice che cosa costa il problema, `rimedio` che cosa si fa per toglierlo:
    sono due cose diverse e vanno scritte separate, perche' la dashboard e le slide mostrano
    il rimedio sotto un titolo che promette un intervento.

    `unita` e' che cosa si sta contando: pagine, immagini, crawler. Senza, chi legge
    `occorrenze` scrive «360 pagine» dove sono 360 immagini su 9 pagine.

    Con una base vuota non si giudica: un campione di zero non e' ne' in linea ne' critico.
    """
    if base == 0:
        stato = "non-verificato"
    # Le righe dell'elenco finiscono in una cella di foglio e in un TSV negli appunti: un a
    # capo o un tab dentro un attributo src (capita, l'HTML lo permette) spezzerebbe la riga
    # in tre. Si normalizzano gli spazi una volta qui, non in ogni chiamante, e si buttano
    # le righe vuote, che nel foglio diventavano righe bianche.
    elenco = [" ".join(str(x).split()) for x in (elenco or []) if str(x).strip()]
    return {"id": id_, "gruppo": gruppo, "titolo": titolo, "stato": stato, "valore": valore,
            "dettaglio": dettaglio, "spiegazione": spiegazione, "conseguenza": conseguenza,
            "elenco": elenco[:200], "elenco_totale": len(elenco),
            # La dashboard si ferma a 200 righe perche' nessuno ne legge di piu' in una
            # finestra; il foglio invece deve contenerle tutte. La chiave con l'underscore
            # non arriva a risultati.json: main() la toglie prima di scriverlo.
            "_elenco_intero": elenco,
            "_descrizione_elenco": descrizione_elenco,
            "etichetta_elenco": etichetta_elenco, "unita": unita,
            "rimedio": rimedio or rimedio_per(id_),
            "pagine": [u for u in (pagine if pagine is not None else elenco)
                       if isinstance(u, str) and u.startswith("http") and " " not in u][:120],
            "base": base, "gravita": gravita or {"critico": "errore", "attenzione": "avviso"}.get(stato, "nota")}


RE_FRECCIA = re.compile(r"^(.*?) [\u2014\u2190\u2192] (.*)$")
RE_DUEPUNTI = re.compile(r"^([^\s:]+): (.*)$")

# Le righe degli elenchi sono testo da leggere ("url - nessun H1", "GPTBot: bloccato").
# Per il foglio le spezziamo sul separatore, cosi' URL e motivo finiscono in celle diverse.
# I due punti separano solo se li segue uno spazio: in "https://" li segue una barra,
# quindi un URL da solo resta in una colonna sola. E' lo stesso criterio della dashboard:
# se cambia uno, cambia l'altro, altrimenti il tasto Copia e il foglio non coincidono piu'.
INTESTAZIONI = {
    "Crawler provati": ["Crawler", "Esito"],
    "Immagini senza testo alternativo": ["Immagine", "Pagina"],
}


def colonne(s):
    m = RE_FRECCIA.match(s) or RE_DUEPUNTI.match(s)
    return [m.group(1), m.group(2)] if m else [s]


def nome_scheda(titolo, presi):
    """Un titolo di scheda valido per Google Sheets: niente : \\ / ? * [ ], max 90
    caratteri, e mai due uguali nello stesso foglio."""
    pulito = "".join(" " if c in ":\\/?*[]" else c for c in titolo).strip()[:90] or "Elenco"
    base, n = pulito, 2
    while pulito.lower() in presi:
        coda = f" ({n})"
        pulito, n = base[:90 - len(coda)] + coda, n + 1
    presi.add(pulito.lower())
    return pulito


def elenchi_da(indicatori):
    """Un elenco per ogni indicatore fuori linea che ha righe: e' il contenuto del foglio."""
    fuori, presi = [], set()
    for i in indicatori:
        righe = i.get("_elenco_intero") or []
        if i["stato"] not in ("critico", "attenzione") or not righe:
            continue
        spezzate = [colonne(r) for r in righe]
        larghezza = max(len(r) for r in spezzate)
        testate = INTESTAZIONI.get(i.get("etichetta_elenco", ""), ["URL", "Motivo"])[:larghezza]
        fuori.append({
            "id": i["id"], "titolo": i["titolo"], "stato": i["stato"], "gruppo": i["gruppo"],
            "etichetta": i.get("etichetta_elenco", "Pagine interessate"),
            "descrizione": (i.get("_descrizione_elenco")
                            or f"Le righe dell'indicatore \u00ab{i['titolo']}\u00bb."),
            "scheda": nome_scheda(i["titolo"], presi),
            "totale": len(righe), "intestazioni": testate,
            "righe": [r + [""] * (larghezza - len(r)) for r in spezzate],
        })
    return fuori


# --- Ci vedono? ------------------------------------------------------------

def gruppo_visibilita(crawler, robots, tls, pagine):
    out = []
    per_conseguenza = defaultdict(list)
    for c in crawler or []:
        bloccato = c["home_status"] in (401, 403, 429) or (c["home_status"] is None and c["home_errore"])
        robots_no = not robots["permessi"].get(c["crawler"], {}).get("robots_permette_home", True)
        per_conseguenza[c["conseguenza"]].append({
            "crawler": c["crawler"], "status": c["home_status"], "errore": c["home_errore"],
            "bloccato_dal_server": bool(bloccato), "bloccato_da_robots": robots_no,
            "perche": c["perche"],
        })

    citanti = per_conseguenza.get("citazione", [])
    fermi = [x for x in citanti if x["bloccato_dal_server"] or x["bloccato_da_robots"]]
    out.append(ind(
        "crawler-citazione", "visibilita", "Assistenti AI che possono citarvi",
        "critico" if fermi else "ok", f"{len(citanti) - len(fermi)} su {len(citanti)}",
        "Sono i crawler con cui ChatGPT, Claude e Perplexity leggono le pagine per poi citarle "
        "nelle risposte. Per ognuno abbiamo fatto una richiesta al sito presentandoci con il suo "
        "nome, e guardato come ha risposto il server. I controlli che verificano davvero "
        "l'identità di un crawler guardano l'indirizzo di rete, non il nome: qui vediamo come "
        "il sito tratta chi si presenta così, che è il primo filtro che incontra un assistente.",
        "Un assistente che non riesce a leggere una pagina non può citarla: il sito semplicemente "
        "non esiste in quella risposta." if fermi else
        "Tutti gli assistenti riescono a leggere il sito: la porta è aperta.",
        elenco=[f"{x['crawler']}: " + ("bloccato dal server" if x["bloccato_dal_server"]
                else "vietato dal robots.txt" if x["bloccato_da_robots"] else "ok") for x in citanti],
        base=len(citanti), pagine=[], etichetta_elenco="Crawler provati", unita="crawler",
        descrizione_elenco="Gli assistenti provati, uno per riga, con l'esito della richiesta."))

    ricerca = [x for s in ("ricerca-google", "ricerca-bing", "ricerca-apple") for x in per_conseguenza.get(s, [])]
    fermi_r = [x for x in ricerca if x["bloccato_dal_server"] or x["bloccato_da_robots"]]
    out.append(ind(
        "crawler-ricerca", "visibilita", "Motori di ricerca",
        "critico" if fermi_r else "ok", f"{len(ricerca) - len(fermi_r)} su {len(ricerca)}",
        "Googlebot, Bingbot e Applebot. Le AI Overviews e AI Mode di Google non hanno un crawler "
        "proprio: pescano dall'indice costruito da Googlebot.",
        "Bloccare Googlebot toglie il sito dalla ricerca e dalle risposte AI di Google insieme. "
        "Prima di dirlo al cliente va confrontato con Search Console: se ci sono impressioni, "
        "Googlebot entra e il blocco riguarda solo chi ne usa il nome."
        if fermi_r else "I motori leggono il sito regolarmente.",
        elenco=[f"{x['crawler']}: {x['status'] or x['errore']}" for x in ricerca], base=len(ricerca), pagine=[], etichetta_elenco="Crawler provati", unita="crawler",
        descrizione_elenco="I motori di ricerca provati, uno per riga, con la risposta del server."))

    addestr = per_conseguenza.get("addestramento", [])
    bloccati_a = [x for x in addestr if x["bloccato_dal_server"] or x["bloccato_da_robots"]]
    out.append(ind(
        "crawler-addestramento", "visibilita", "Crawler di addestramento",
        "ok", f"{len(bloccati_a)} bloccati su {len(addestr)}",
        "Raccolgono pagine per addestrare i modelli, non per citarvi. Fra questi c'è "
        "Google-Extended, che governa Gemini e non le AI Overviews: sono due cose diverse e "
        "vengono confuse spesso.",
        "Non è né giusto né sbagliato lasciarli entrare: è una scelta dell'azienda. "
        "L'importante è non confonderli con i crawler che portano citazioni.",
        elenco=[f"{x['crawler']}: " + ("bloccato" if x["bloccato_dal_server"] or x["bloccato_da_robots"]
                else "permesso") for x in addestr], base=len(addestr), pagine=[], etichetta_elenco="Crawler provati", unita="crawler",
        descrizione_elenco="I crawler di addestramento provati, uno per riga: bloccato o permesso."))

    vive_r = [p for p in pagine if p.get("status") == 200]
    magre = [p for p in vive_r if p.get("parole_testo", 0) < TESTO_SOSPETTO]
    # Un contenitore di root vuoto e' una prova: senza JavaScript la pagina non ha corpo.
    # __NEXT_DATA__ e simili da soli no: ci sono su ogni pagina Next.js o Nuxt resa lato
    # server, che per un crawler va benissimo. Valgono solo insieme a poco testo.
    vuote = [p for p in vive_r if p.get("root_vuoto")]
    sospette = [p for p in magre if p.get("framework_js")]
    quota = len(magre) / len(vive_r) if vive_r else 0
    stato = ("critico" if (vuote or (sospette and quota > .3))
             else "attenzione" if (sospette or quota > .15) else "ok")
    out.append(ind(
        "rendering", "visibilita", "Contenuto leggibile senza JavaScript",
        stato, f"{len(vive_r) - len(magre)} su {len(vive_r)}",
        "Abbiamo letto le pagine come le legge un assistente AI: scaricando l'HTML e basta, senza "
        "eseguire JavaScript. GPTBot, ClaudeBot e PerplexityBot funzionano così.",
        "Una pagina il cui testo compare solo dopo il JavaScript risulta vuota per gli assistenti. "
        "Può posizionarsi su Google, che il JavaScript lo esegue, ed essere invisibile su ChatGPT."
        if stato != "ok" else
        "Il testo è già nell'HTML: gli assistenti lo leggono tutto.",
        dettaglio=(f"{len(vuote)} pagine il cui contenuto arriva solo col JavaScript"
                   if vuote else
                   f"{len(sospette)} pagine fatte con un framework e con poco testo"
                   if sospette else ""),
        elenco=[p["url"] for p in (vuote or magre)], base=len(vive_r),
        descrizione_elenco="Le pagine il cui testo non c'\u00e8 nell'HTML grezzo, o che ne contengono troppo poco."))

    noindex_pag = [p for p in pagine
                   if "noindex" in (p.get("meta_robots", "") + " " + p.get("x_robots_tag", "")).lower()]
    noindex = [p["url"] for p in noindex_pag]
    # Quando le noindex stanno tutte nella stessa sezione la scelta e' quasi sempre
    # deliberata, e dirlo evita di far inseguire al cliente un problema che non c'e'.
    sezioni_ni = {p.get("sezione") or "" for p in noindex_pag}
    una_sola = sezioni_ni.pop() if len(sezioni_ni) == 1 and len(noindex) > 1 else ""
    fuori_sito = [p for p in noindex_pag
                  if p.get("url_finale") and urllib.parse.urlparse(p["url_finale"]).netloc
                  != urllib.parse.urlparse(p["url"]).netloc]
    concentrate = (f"tutte nella sezione «{una_sola}»" if una_sola else "")
    if una_sola and len(fuori_sito) == len(noindex):
        concentrate += ", e tutte reindirizzano fuori dal sito: la scelta è quasi certamente voluta"
    elif una_sola:
        concentrate += ": quando si concentrano così, di solito è voluto"
    out.append(ind(
        "noindex", "visibilita", "Pagine escluse dagli indici", "ok" if not noindex else "attenzione",
        str(len(noindex)),
        "Pagine che chiedono esplicitamente di non essere indicizzate, con un meta robots o "
        "un'intestazione HTTP.",
        "Di solito è voluto (pagine di servizio, ringraziamenti). Va controllato che non ci sia "
        "finita una pagina che dovrebbe essere trovata.",
        dettaglio=concentrate,
        elenco=noindex, base=len(pagine),
        descrizione_elenco="Le pagine che chiedono esplicitamente di non essere indicizzate"
        + (f", {concentrate.split(':')[0].split(', e tutte')[0]}." if una_sola else ".")))

    if tls:
        giorni = tls.get("giorni_alla_scadenza")
        problemi = []
        if not tls.get("valido"):
            problemi.append("certificato non valido")
        if giorni is not None and giorni < CERT_IN_SCADENZA:
            problemi.append(f"scade fra {giorni} giorni")
        if not tls.get("http_redirige_a_https"):
            problemi.append("http non reindirizza a https")
        misto = [p["url"] for p in pagine if p.get("risorse_http")]
        if misto:
            problemi.append(f"{len(misto)} pagine con risorse in http")
        out.append(ind(
            "ssl", "visibilita", "Certificato e connessione sicura",
            "critico" if (not tls.get("valido") or misto or (giorni is not None and giorni < 7))
            else "attenzione" if problemi else "ok",
            "sicuro" if not problemi else "da sistemare",
            "Verifichiamo che il certificato sia valido e non in scadenza, che chi arriva su http "
            "venga portato su https, e che dentro le pagine non restino risorse caricate in chiaro.",
            "Un certificato scaduto rende il sito irraggiungibile per tutti, persone e assistenti, "
            "da un momento all'altro. Le risorse in chiaro fanno comparire l'avviso «non sicuro».",
            dettaglio=" · ".join(problemi) if problemi else
            f"valido, scade fra {giorni} giorni" if giorni is not None else "valido",
            elenco=misto, base=len(pagine),
            descrizione_elenco="Le pagine che caricano ancora qualche risorsa in chiaro dentro una connessione sicura."))
    return out


# --- Ci capiscono? ---------------------------------------------------------

def gruppo_comprensione(pagine, config):
    out = []
    attese = {**SEZIONI_ATTESE, **(config.get("sezioni_attese") or {})}
    vive = [p for p in pagine if p.get("status") == 200]

    org = [p for p in vive if set(p.get("jsonld_tipi", [])) & ORGANIZZAZIONE]
    con_sameas = []
    for p in org:
        for b in p.get("jsonld", []):
            if set(tipi_di(b)) & ORGANIZZAZIONE and b.get("sameAs"):
                con_sameas.append(p["url"])
                break
    out.append(ind(
        "schema-organization", "comprensione", "Scheda dell'azienda nei dati strutturati",
        "ok" if (org and con_sameas) else "attenzione" if org else "critico",
        "presente" if org else "assente",
        "È il blocco che dice a un assistente chi siete: nome, logo, e con `sameAs` i collegamenti "
        "ai vostri profili ufficiali (LinkedIn, Wikidata).",
        "Senza, l'assistente non sa quale azienda siete fra le omonime, e fa fatica ad attribuirvi "
        "quello che legge." if not con_sameas else
        "L'assistente può collegare il sito all'azienda giusta.",
        dettaglio=("collegamenti ai profili ufficiali presenti" if con_sameas
                   else "mancano i collegamenti ai profili ufficiali (sameAs)")
        if org else "nessuna scheda azienda trovata nei dati strutturati",
        base=len(vive)))

    sito = [p for p in vive if "WebSite" in p.get("jsonld_tipi", [])]
    out.append(ind(
        "schema-website", "comprensione", "Scheda del sito", "ok" if sito else "attenzione",
        "presente" if sito else "assente",
        "Dichiara nome del sito e, se c'è, la ricerca interna.",
        "È un segnale minore ma gratuito: aiuta a mostrare il nome giusto del sito nei risultati.",
        base=len(vive)))

    per_sezione = defaultdict(list)
    for p in vive:
        per_sezione[p.get("sezione", "home")].append(p)
    for sezione, attesi in sorted(attese.items()):
        pag = per_sezione.get(sezione, [])
        if len(pag) < 3:
            continue   # sotto le tre pagine la percentuale non dice niente
        con = [p for p in pag if set(p.get("jsonld_tipi", [])) & set(attesi)]
        quota = len(con) / len(pag)
        completi = []
        for p in con:
            for b in p.get("jsonld", []):
                if set(tipi_di(b)) & set(attesi) and all(b.get(c) for c in CAMPI_ARTICOLO
                                                         if attesi[0] in ("BlogPosting", "Article", "NewsArticle")):
                    completi.append(p["url"]); break
                if set(tipi_di(b)) & set(attesi) and attesi[0] not in ("BlogPosting", "Article", "NewsArticle"):
                    completi.append(p["url"]); break
        out.append(ind(
            f"schema-{sezione}", "comprensione", f"Dati strutturati: {sezione}",
            "ok" if quota >= .9 else "attenzione" if quota >= .5 else "critico",
            f"{round(quota * 100)}%",
            f"Quante pagine della sezione «{sezione}» dichiarano il tipo giusto "
            f"({' o '.join(attesi[:2])}) nei dati strutturati.",
            "I dati strutturati dicono all'assistente che tipo di contenuto sta leggendo. Senza, "
            "deve dedurlo dal testo, e spesso sbaglia.",
            dettaglio=f"{it(len(con))} {plurale(len(con), 'pagina', 'pagine')} su {it(len(pag))}"
            + (f", di cui {len(completi)} con tutti i campi necessari" if con else ""),
            elenco=[p["url"] for p in pag if p not in con], base=len(pag),
            descrizione_elenco=f"Le pagine della sezione \u00ab{sezione}\u00bb che non dichiarano il tipo "
            f"atteso ({' o '.join(attesi[:2])}) nei dati strutturati."))

    articoli = [p for p in vive
                if set(p.get("jsonld_tipi", [])) & {"BlogPosting", "Article", "NewsArticle"}]
    if articoli:
        con_persona = []
        for p in articoli:
            # Yoast e molti plugin WordPress mettono l'autore come riferimento dentro @graph:
            # {"author": {"@id": "...#/schema/person/..."}}. Va risolto nella pagina stessa,
            # altrimenti su WordPress l'indicatore legge quasi zero e grida al lupo.
            per_id = {b.get("@id"): b for b in p.get("jsonld", []) if isinstance(b, dict) and b.get("@id")}
            for b in p.get("jsonld", []):
                a = b.get("author")
                a = a[0] if isinstance(a, list) and a else a
                if isinstance(a, dict) and list(a.keys()) == ["@id"]:
                    a = per_id.get(a["@id"], a)
                if isinstance(a, dict) and "Person" in tipi_di(a) and (a.get("url") or a.get("sameAs")):
                    con_persona.append(p["url"]); break
        quota = len(con_persona) / len(articoli)
        out.append(ind(
            "schema-autore", "comprensione", "Autore riconoscibile negli articoli",
            "ok" if quota >= .8 else "attenzione" if quota >= .3 else "critico",
            f"{round(quota * 100)}%",
            "Quanti articoli indicano l'autore come persona vera, con un collegamento al suo profilo, "
            "invece che come semplice testo.",
            "Gli assistenti attribuiscono più facilmente un contenuto a chi l'ha scritto, e la firma "
            "di una persona identificabile pesa nelle risposte che citano fonti.",
            dettaglio=f"{len(con_persona)} articoli su {len(articoli)}",
            elenco=[p["url"] for p in articoli if p["url"] not in con_persona], base=len(articoli),
            descrizione_elenco="Gli articoli che non indicano l'autore come persona con un collegamento al suo profilo."))

        senza_data = []
        for p in articoli:
            ok = False
            for b in p.get("jsonld", []):
                if b.get("datePublished"):
                    ok = True
                    break
            if not ok:
                senza_data.append(p["url"])
        out.append(ind(
            "schema-date", "comprensione", "Data di pubblicazione negli articoli",
            "ok" if not senza_data else "attenzione",
            f"{round((1 - len(senza_data) / len(articoli)) * 100)}%",
            "Quanti articoli dichiarano quando sono stati pubblicati, nei dati strutturati.",
            "Gli assistenti preferiscono fonti recenti e lo dicono nelle risposte. Un contenuto senza "
            "data viene trattato come se non si sapesse quanto vale ancora.",
            elenco=senza_data, base=len(articoli),
            descrizione_elenco="Gli articoli che non dichiarano la data di pubblicazione nei dati strutturati."))

    faq = [p for p in vive if "FAQPage" in p.get("jsonld_tipi", [])]
    out.append(ind(
        "schema-faq", "comprensione", "Pagine con domande e risposte strutturate",
        "ok" if faq else "attenzione", str(len(faq)),
        "Pagine che dichiarano le proprie FAQ in modo che una macchina possa estrarle.",
        "Google non mostra più i riquadri FAQ nei risultati, quindi per la SEO classica non rendono "
        "più. Per gli assistenti invece restano preziose: trovano la domanda e la risposta già "
        "separate e le riusano quasi testualmente.",
        elenco=[p["url"] for p in faq], base=len(vive),
        descrizione_elenco="Le pagine che gi\u00e0 dichiarano le proprie domande e risposte: qui l'elenco \u00e8 di chi ce l'ha, non di chi manca."))

    senza_h1 = [p["url"] for p in vive if not p.get("h1")]
    multi_h1 = [p["url"] for p in vive if len(p.get("h1", [])) > 1]
    h1_uguale = [p["url"] for p in vive
                 if p.get("h1") and p.get("titolo") and p["h1"][0].strip().lower() == p["titolo"].strip().lower()]
    out.append(ind(
        "h1", "comprensione", "Titolo principale delle pagine",
        "critico" if senza_h1 else "attenzione" if multi_h1 else "ok",
        f"{len(senza_h1)} senza, {len(multi_h1)} con più di uno",
        "Il titolo principale dice di cosa parla la pagina. Più di un H1 è tecnicamente lecito in "
        "HTML5 e Google dice che non è un problema: quello che conta è che ce ne sia uno chiaro.",
        "Una pagina senza titolo principale costringe l'assistente a dedurre l'argomento dal corpo "
        "del testo, e spesso sceglie la cosa sbagliata.",
        dettaglio=f"{len(h1_uguale)} pagine con H1 identico al titolo del browser" if h1_uguale else "",
        elenco=[f"{u} — nessun H1" for u in senza_h1] + [f"{u} — più H1" for u in multi_h1],
        pagine=senza_h1 + multi_h1, base=len(vive),
        descrizione_elenco="Le pagine senza titolo principale o con pi\u00f9 di uno, ognuna col suo motivo."))

    lunghe = [p for p in vive if p.get("parole_testo", 0) >= PAROLE_SERVE_H2]
    senza_h2 = [p["url"] for p in lunghe if not p.get("h2")]
    out.append(ind(
        "h2", "comprensione", "Sottotitoli nelle pagine lunghe",
        "attenzione" if senza_h2 else "ok", f"{len(senza_h2)} su {len(lunghe)}",
        f"Pagine sopra le {PAROLE_SERVE_H2} parole che non hanno nessun sottotitolo. Sotto quella "
        "soglia una pagina senza sottotitoli è normale.",
        "Gli assistenti spezzano il testo in blocchi seguendo i sottotitoli. Una pagina lunga senza "
        "sottotitoli è un blocco unico: o la citano tutta o niente, e di solito è niente.",
        elenco=senza_h2, base=len(lunghe),
        descrizione_elenco="Le pagine lunghe che non hanno nessun sottotitolo."))

    tot_img = sum(p.get("immagini", 0) for p in vive)
    senza_alt = sum(len(p.get("img_senza_alt", [])) for p in vive)
    nomefile = sum(len(p.get("img_alt_nomefile", [])) for p in vive)
    quota = 1 - (senza_alt / tot_img) if tot_img else 1
    out.append(ind(
        "alt", "comprensione", "Immagini con testo alternativo",
        "ok" if quota >= .9 else "attenzione" if quota >= .6 else "critico",
        f"{round(quota * 100)}%",
        "Quante immagini hanno un testo che le descrive. Le immagini decorative con `alt` vuoto sono "
        "corrette e non contano come errore: contiamo solo quelle senza alcun testo alternativo.",
        "È il modo in cui un'immagine entra in un indice testuale, e il modo in cui la legge chi usa "
        "uno screen reader. Senza, l'immagine per una macchina non esiste.",
        dettaglio=f"{it(senza_alt)} senza alt su {it(tot_img)}"
        + (f" · {nomefile} con un nome di file al posto della descrizione" if nomefile else ""),
        elenco=sorted({f"{u} \u2190 {p['url']}" for p in vive
                       for u in p.get("img_senza_alt", []) if u}), base=tot_img,
        pagine=[p["url"] for p in vive if p.get("img_senza_alt")],
        etichetta_elenco="Immagini senza testo alternativo", unita="immagini",
        descrizione_elenco="Le immagini senza alcun testo alternativo, una per riga."))
    return out


# --- Trovano tutto all'interno del sito web? -----------------------------------------------------

def gruppo_copertura(sitemap, robots, pagine, link=None):
    out = []
    sm = sitemap or {}
    voci = sm.get("voci", [])
    raggiungibili = [s for s in sm.get("sitemap", []) if s.get("status") == 200]
    out.append(ind(
        "sitemap", "copertura", "Mappa del sito",
        "ok" if raggiungibili else "critico",
        f"{sm.get('totale_url', 0)} URL" if raggiungibili else "non raggiungibile",
        "La sitemap è l'elenco delle pagine che il sito dichiara di avere. Controlliamo che esista, "
        "che risponda e che sia dichiarata nel robots.txt.",
        "Senza sitemap i motori e gli assistenti devono scoprire le pagine seguendo i link: le pagine "
        "poco collegate rischiano di non essere trovate mai.",
        dettaglio=("dichiarata nel robots.txt" if robots.get("sitemap_dichiarate")
                   else "non dichiarata nel robots.txt"),
        base=sm.get("totale_url", 0)))

    con = sm.get("con_lastmod", 0)
    tot = sm.get("totale_url", 0) or 1
    date = Counter(v["lastmod"][:10] for v in voci if v.get("lastmod"))
    tutte_uguali = bool(date) and date.most_common(1)[0][1] / max(1, sum(date.values())) > .9
    out.append(ind(
        "sitemap-lastmod", "copertura", "Data di ultima modifica nella mappa",
        "attenzione" if (con / tot < .9 or tutte_uguali) else "ok",
        f"{round(con / tot * 100)}%",
        "Quante pagine della sitemap dichiarano quando sono state modificate l'ultima volta.",
        "Serve a far ripassare per prime le pagine cambiate. Se però tutte le pagine riportano la "
        "stessa data, il segnale si annulla e vale meno che non averlo: succede quando il CMS "
        "riscrive la data a ogni pubblicazione." if tutte_uguali else
        "Serve a far ripassare per prime le pagine che sono cambiate davvero.",
        dettaglio="quasi tutte le pagine hanno la stessa data: il segnale non è attendibile"
        if tutte_uguali else f"{con} pagine su {tot}", base=tot))

    in_sitemap = {norm(v["url"]) for v in voci}
    vive = [p for p in pagine if p.get("status") == 200]
    fuori = [p["url"] for p in vive if norm(p["url_finale"] or p["url"]) not in in_sitemap]
    out.append(ind(
        "sitemap-coerenza", "copertura", "Pagine trovate ma non in mappa",
        "attenzione" if len(fuori) > len(vive) * .2 else "ok", str(len(fuori)),
        "Pagine raggiungibili navigando il sito che però non compaiono nella sitemap.",
        "Non è un errore grave, ma è il segno che la sitemap non rispecchia il sito: chi si fida "
        "solo di quella si perde quelle pagine.",
        elenco=fuori, base=len(vive),
        descrizione_elenco="Le pagine raggiungibili navigando il sito che non compaiono nella sitemap."))

    # Gli status vengono dalle pagine scansionate E dai bersagli controllati a parte:
    # senza i secondi, su un sito piu' grande del tetto di pagine questo indicatore non
    # puo' strutturalmente trovare niente, perche' i bersagli rotti non stanno in sitemap.
    stato_per_url = {norm(p["url_finale"] or p["url"]): p.get("status") for p in pagine}
    for e in (link or {}).get("esiti", []):
        stato_per_url.setdefault(norm(e["url"]), e.get("status"))
    # Solo 404 e 410 sono "non esiste". 403, 429 e 5xx vogliono dire che la scansione e'
    # stata respinta: segnalarli come link rotti darebbe la colpa al sito sbagliato.
    rotti, respinti = defaultdict(list), 0
    for p in pagine:
        for l in p.get("link_interni", []):
            s = stato_per_url.get(norm(l))
            if s in (404, 410):
                rotti[l].append(p["url"])
            elif s in (403, 429) or (s or 0) >= 500:
                respinti += 1
    controllati = (link or {}).get("controllati", 0)
    out.append(ind(
        "link-rotti", "copertura", "Link interni che portano a una pagina inesistente",
        "critico" if rotti else "ok", str(len(rotti)),
        "Link dentro il sito che puntano a una pagina che non esiste (404 o 410). Li troviamo "
        "seguendo i link e controllando anche i bersagli che la scansione non ha raggiunto, "
        "non indovinando gli indirizzi.",
        "Interrompono il percorso di chi legge e quello del crawler, che si ferma lì invece di "
        "proseguire verso il resto del sito.",
        dettaglio=(f"{it(controllati)} bersagli controllati oltre le pagine scansionate"
                   + (f" · {respinti} link verso pagine che hanno respinto la richiesta, non contati"
                      if respinti else "")),
        elenco=[f"{u} \u2190 da {it(len(da))} {plurale(len(da), 'pagina', 'pagine')}, "
                f"per esempio {da[0]}"
                for u, da in sorted(rotti.items(), key=lambda x: -len(x[1]))],
        pagine=list(rotti),
        base=sum(len(p.get("link_interni", [])) for p in pagine),
        descrizione_elenco="Gli indirizzi che non esistono pi\u00f9, con quante pagine del sito li collegano."))

    soft = [p["url"] for p in pagine if p.get("possibile_soft404")]
    out.append(ind(
        "soft-404", "copertura", "Pagine «non trovato» che rispondono come se esistessero",
        "attenzione" if soft else "ok", str(len(soft)),
        "Pagine che mostrano un messaggio di errore ma rispondono al crawler con un codice di "
        "successo, invece che con un 404.",
        "Il motore le tratta come pagine vere e le tiene nell'indice: si finisce con pagine vuote "
        "fra i risultati.",
        elenco=soft, base=len(pagine),
        descrizione_elenco="Le pagine che mostrano un errore ma rispondono come se esistessero."))

    senza_can, can_strano = [], []
    for p in (x for x in pagine if x.get("status") == 200):
        c = p.get("canonical", "")
        if not c:
            senza_can.append(p["url"])
        elif norm(c) != norm(p["url_finale"] or p["url"]):
            s = stato_per_url.get(norm(c))
            if s is not None and s >= 300:
                can_strano.append(f"{p['url']} → {c} ({s})")
    out.append(ind(
        "canonical", "copertura", "Indirizzo ufficiale di ogni pagina",
        "critico" if can_strano else "attenzione" if senza_can else "ok",
        f"{len(senza_can)} senza, {len(can_strano)} che puntano male",
        "Il canonical dice qual è l'indirizzo ufficiale di una pagina quando ne esistono più versioni.",
        "Se manca o punta a una pagina che non risponde, il motore sceglie da solo quale versione "
        "tenere, e può scartare quella giusta.",
        elenco=can_strano + senza_can, pagine=senza_can, base=len(pagine),
        descrizione_elenco="Le pagine senza indirizzo ufficiale, e quelle il cui canonical punta a una pagina che non risponde."))

    out.append(ind(
        "llms-txt", "copertura", "File llms.txt",
        "ok" if (robots.get("llms_txt", {}).get("status") == 200) else "attenzione",
        "presente" if robots.get("llms_txt", {}).get("status") == 200 else "assente",
        "Un file che indica agli assistenti quali pagine contano e come è fatto il sito. È una "
        "convenzione recente, non uno standard: alcuni assistenti la leggono, altri no.",
        "Costa poco e non fa danni. Dove viene letto, aiuta l'assistente a scegliere le pagine "
        "giuste invece di girare a caso.", base=1))
    return out


# --- Quanto aspettano? --------------------------------------------------

def gruppo_velocita(velocita, pagine):
    out = []
    v = velocita or {}
    campo = v.get("ttfb_campo_ms")
    nostro = v.get("ttfb_crawler_ms")
    if campo is not None:
        # Il giudizio e' quello di Google (category), non il nostro: la soglia ufficiale degli
        # 800 ms e' definita al 75esimo percentile, e quale percentile restituisca PSI non e'
        # documentato in modo coerente. Le nostre soglie restano solo come ripiego.
        per_categoria = {"FAST": "ok", "AVERAGE": "attenzione", "SLOW": "critico"}
        categoria = (velocita or {}).get("ttfb_campo_categoria")
        stato = per_categoria.get(categoria) or (
            "ok" if campo <= TTFB_BUONO else "attenzione" if campo <= TTFB_SCARSO else "critico")
        out.append(ind(
            "ttfb-campo", "velocita", "Attesa prima del primo byte, utenti veri",
            stato, f"{it(campo)} ms",
            "Quanto aspetta chi apre il sito prima che arrivi il primo pezzo di risposta, misurato "
            "da Google su utenti Chrome reali negli ultimi 28 giorni.",
            f"Google considera buono sotto {it(TTFB_BUONO)} ms e scarso oltre {it(TTFB_SCARSO)} ms. È il "
            "tempo che precede tutto il resto: finché non arriva, la pagina è bianca.",
            dettaglio=(f"giudizio di Google: {categoria}" if categoria else
                       f"nostre soglie: {it(TTFB_BUONO)} ms o meno buono, oltre {it(TTFB_SCARSO)} ms scarso")))
    else:
        senza_chiave = v.get("psi") == "nessuna chiave"
        errore = v.get("psi_errore")
        if senza_chiave:
            perche = ("Non abbiamo interrogato PageSpeed Insights: manca la chiave di accesso. "
                      "Non dice nulla sul sito, solo che quel dato non è stato chiesto.")
        elif errore:
            perche = "PageSpeed Insights non ha risposto. Il dato va richiesto di nuovo."
        else:
            perche = ("Google raccoglie i dati reali di Chrome solo sui siti con traffico "
                      "sufficiente: su questo sito non ce n'è abbastanza per una misura "
                      "statisticamente valida. Non è un difetto del sito.")
        out.append(ind(
            "ttfb-campo", "velocita", "Attesa prima del primo byte, utenti veri",
            "non-verificato", "non misurato",
            "Si legge dai dati reali di Chrome degli ultimi 28 giorni, al 75° percentile.",
            perche + " Vale la misura fatta da noi.",
            dettaglio=errore[:160] if errore else ""))
    if nostro is not None:
        stato = "ok" if nostro <= TTFB_CRAWLER_BUONO else "attenzione" if nostro <= TTFB_SCARSO else "critico"
        scarto = f" · gli utenti veri aspettano {campo} ms" if campo is not None else ""
        out.append(ind(
            "ttfb-crawler", "velocita", "Attesa per un assistente AI",
            stato, f"{it(nostro)} ms",
            "La stessa attesa, misurata presentandoci come un assistente e senza nessuna delle "
            "ottimizzazioni che aiutano un browser (niente cache del browser, niente precaricamento). "
            "È la mediana di più richieste di fila: la prima, a cache fredda, è spesso molto più lenta.",
            "È la misura che conta per l'AEO. Diversi crawler rinunciano se il sito tarda troppo, e "
            "una cache che lavora bene per le persone può non lavorare affatto per loro.",
            dettaglio=f"mediana di {v.get('misure', '?')} richieste{scarto}"))
    if v.get("ttfb_crawler_min") is not None and v.get("ttfb_crawler_max") is not None \
            and v["ttfb_crawler_max"] > v["ttfb_crawler_min"] * 3:
        out.append(ind(
            "ttfb-cache", "velocita", "Differenza fra prima richiesta e successive",
            "attenzione", f"da {it(v['ttfb_crawler_min'])} a {it(v['ttfb_crawler_max'])} ms",
            "La stessa pagina chiesta più volte di fila: la prima volta la risposta si costruisce, "
            "dopo arriva da una copia già pronta.",
            "Un assistente passa una volta sola e trova quasi sempre la situazione della prima "
            "richiesta, cioè la più lenta. Una cache che si scalda solo con le visite ripetute "
            "aiuta le persone e non aiuta lui."))

    pesanti = [p["url"] for p in pagine if p.get("byte_html", 0) > HTML_PESANTE]
    out.append(ind(
        "peso-html", "velocita", "Pagine troppo pesanti da leggere",
        "attenzione" if pesanti else "ok", str(len(pesanti)),
        f"Pagine il cui HTML supera {it(HTML_PESANTE // 1000)} KB, senza contare immagini e script.",
        "Diversi assistenti leggono solo i primi blocchi di un documento lungo: il contenuto in "
        "fondo a una pagina pesante rischia di non essere mai letto.",
        elenco=pesanti, base=len(pagine),
        descrizione_elenco="Le pagine il cui HTML supera la soglia di peso."))
    return out


# --- Punteggio di sintesi --------------------------------------------------

# Il punteggio sta sui TEMI, non sulle singole verifiche, e la differenza non e' cosmetica.
# I dati strutturati sono misurati da una verifica per sezione del sito: su un sito con
# quindici sezioni peserebbero quindici volte, e un problema solo deciderebbe il voto. Su
# Su un sito di prova, contate una per una le 33 verifiche danno 46; contate per tema danno 66. La seconda
# dice quanti problemi DIVERSI ci sono, la prima quante righe ha il referto.
#
# I pesi sono una scelta, non una misura. Si discutono una volta e poi si lasciano fermi:
# un punteggio serve solo se confrontato con se stesso alla scansione dopo.
TEMI_PUNTEGGIO = [
    ("accesso", "Accesso dei crawler", 20),
    ("rendering", "Leggibilità senza JavaScript", 15),
    ("strutturati", "Dati strutturati", 25),
    ("struttura", "Struttura del contenuto", 15),
    ("copertura", "Copertura e sitemap", 10),
    ("velocita", "Velocità", 8),
    ("indicizzabilita", "Indicizzabilità", 5),
    ("llms", "Indirizzo per gli assistenti", 2),
]

# Quanto vale una verifica dentro al suo tema. Un «non verificato» non e' ne' promosso ne'
# bocciato: esce dal conto, e il peso del tema si ridistribuisce sugli altri.
VALORE_STATO = {"ok": 1.0, "attenzione": 0.5, "critico": 0.0}

# A quale mondo serve la verifica. Serve a dire dove stanno i problemi, non a dare due voti:
# la maggior parte vale per tutti e due, e due punteggi costruiti su quelli si muoverebbero
# sempre insieme. Su un sito di prova, 22 verifiche su 33 sono in comune: due quadranti separati davano
# 46 e 44, due punti di differenza che qualcuno avrebbe letto come un giudizio.
MONDO = {
    "crawler-citazione": "assistenti", "crawler-addestramento": "assistenti",
    "llms-txt": "assistenti", "schema-faq": "assistenti", "rendering": "assistenti",
    "crawler-ricerca": "motori", "noindex": "motori", "canonical": "motori",
    "sitemap": "motori", "sitemap-lastmod": "motori", "sitemap-coerenza": "motori",
}


def tema_di(id_):
    """A quale tema del punteggio appartiene una verifica. None se non si riconosce."""
    if id_.startswith("crawler-"):
        return "accesso"
    if id_ == "rendering":
        return "rendering"
    if id_.startswith("schema-"):
        return "strutturati"
    if id_ in ("h1", "h2", "alt", "title"):
        return "struttura"
    if id_.startswith("sitemap") or id_ in ("link-rotti", "soft-404", "canonical"):
        return "copertura"
    if id_ in ("noindex", "ssl"):
        return "indicizzabilita"
    if id_ == "llms-txt":
        return "llms"
    if id_.startswith("ttfb") or id_ == "peso-html":
        return "velocita"
    return None


def punteggio_da(indicatori):
    """Il sommario: un punteggio da 0 a 100 e i temi che lo compongono.

    Una verifica che `tema_di` non riconosce **non entra nel punteggio** e viene elencata in
    `non_pesati`: chi aggiunge una verifica nuova se ne accorge e la classifica, invece di
    vedere il voto muoversi da solo senza sapere perche'.
    """
    per_tema, non_pesati = {}, []
    for i in indicatori:
        t = tema_di(i["id"])
        if t is None:
            non_pesati.append(i["id"])
            continue
        per_tema.setdefault(t, []).append(i)

    # I temi che non hanno nulla di misurato escono, e il loro peso va agli altri in
    # proporzione: cosi' il totale resta su 100 anche dove una verifica non si e' potuta fare.
    vivi = []
    for chiave, nome, peso in TEMI_PUNTEGGIO:
        voci = [i for i in per_tema.get(chiave, []) if i["stato"] in VALORE_STATO]
        if voci:
            vivi.append((chiave, nome, peso, voci))
    peso_vivo = sum(p for _, _, p, _ in vivi)
    if not peso_vivo:
        return {"punteggio": None, "temi": [], "non_pesati": non_pesati,
                "copertura": 0, "mondi": {}, "prima_mossa": None}

    temi, totale = [], 0.0
    for chiave, nome, peso, voci in vivi:
        peso_reale = peso / peso_vivo * 100
        media = sum(VALORE_STATO[i["stato"]] for i in voci) / len(voci)
        punti = peso_reale * media
        totale += punti
        stati = [i["stato"] for i in voci]
        temi.append({
            "chiave": chiave, "nome": nome,
            "peso": round(peso_reale, 1), "punti": round(punti, 1),
            "verifiche": len(voci),
            "stato": ("critico" if "critico" in stati
                      else "attenzione" if "attenzione" in stati else "ok"),
            "persi": round(peso_reale - punti, 1),
        })

    # Il tema che costa di piu': e' da li' che si comincia, ed e' la riga che la dashboard
    # mette in evidenza sotto il quadrante.
    prima = max(temi, key=lambda t: t["persi"])
    mondi = {"assistenti": 0, "motori": 0, "entrambi": 0}
    for i in indicatori:
        if i["stato"] in ("critico", "attenzione"):
            mondi[MONDO.get(i["id"], "entrambi")] += 1

    misurate = sum(len(v) for _, _, _, v in vivi)
    return {
        "punteggio": round(totale),
        "temi": sorted(temi, key=lambda t: -t["persi"]),
        "non_pesati": non_pesati,
        "copertura": round(misurate / max(len(indicatori), 1) * 100),
        "mondi": mondi,
        "prima_mossa": {"tema": prima["nome"], "vale": round(prima["persi"])},
    }


# --- Azioni per la dashboard ----------------------------------------------

ORDINE_GRUPPI = {"visibilita": 0, "comprensione": 1, "copertura": 2, "velocita": 3}


def azioni_da(indicatori):
    """Le azioni che ie-aeo-dashboard mette nel piano di lavoro, accanto a Semrush e Ahrefs."""
    fuori = []
    for i in indicatori:
        if i["stato"] in ("ok", "non-verificato"):
            continue
        fuori.append({
            "id": "sa-ie-" + i["id"], "titolo": i["titolo"], "gravita": i["gravita"],
            "gruppo": i["gruppo"], "valore": i["valore"], "dettaglio": i["dettaglio"],
            # Finche' un indicatore non ha un rimedio scritto si ripiega sulla conseguenza,
            # ma `ha_rimedio` dice che cos'e': chi la mostra sotto «cosa fare» deve saperlo.
            "rimedio": i["rimedio"] or i["conseguenza"], "ha_rimedio": bool(i["rimedio"]),
            "conseguenza": i["conseguenza"],
            "occorrenze": i["elenco_totale"], "unita": i["unita"],
            "pagine": i["pagine"][:60],
        })
    ordine = {"errore": 0, "avviso": 1, "nota": 2}
    # Si ordina per gravita' e poi per gruppo, nell'ordine in cui si raccontano. NON per
    # numero di occorrenze: confronterebbe immagini, pagine e crawler fra loro, e metterebbe
    # 360 immagini senza alt davanti a Googlebot respinto dal server.
    #
    # A parita' di gravita', gruppo E unita' il confronto invece e' legittimo, e serve: su un
    # sito con undici sezioni di prodotto le azioni sullo schema sono undici copie della
    # stessa frase, e in ordine alfabetico la slide ne mostra cinque da tre o quattro pagine
    # lasciando fuori quelle da quarantacinque e sessanta.
    fuori.sort(key=lambda a: (ordine.get(a["gravita"], 3),
                              ORDINE_GRUPPI.get(a["gruppo"], 9),
                              a.get("unita") or "",
                              -(a.get("occorrenze") or 0),
                              a["titolo"]))
    return fuori


def azioni_per_slide(azioni):
    """Le stesse azioni, con quelle che condividono il rimedio raccolte in una riga sola.

    Serve al deck e basta. `azioni.json` resta un elenco piatto perche' i suoi id tengono
    attaccate le decisioni del team da un audit all'altro: accorparli le staccherebbe.
    Qui invece undici sezioni senza dati strutturati, che ripetono la stessa frase, devono
    diventare una riga che dice quali sono e quanto pesano.
    """
    insieme, ordine = {}, []
    for a in azioni:
        chiave = (a["gruppo"], a.get("unita") or "", a["rimedio"])
        if chiave not in insieme:
            insieme[chiave] = []
            ordine.append(chiave)
        insieme[chiave].append(a)

    fuori = []
    for chiave in ordine:
        membri = insieme[chiave]
        if len(membri) == 1:
            fuori.append({**membri[0], "ids": [membri[0]["id"]]})
            continue
        # Il titolo comune e' quello che sta prima dei due punti: «Dati strutturati: newsroom»
        # e «Dati strutturati: lasertube» diventano «Dati strutturati».
        testa = membri[0]["titolo"].split(":")[0]
        voci = sorted(membri, key=lambda m: -(m.get("occorrenze") or 0))
        coda = ", ".join(f"{m['titolo'].split(': ', 1)[-1]} ({it(m['occorrenze'])})"
                         for m in voci if m.get("occorrenze"))
        fuori.append({
            "ids": [m["id"] for m in membri],
            "titolo": f"{testa}, {it(len(membri))} sezioni",
            "gravita": membri[0]["gravita"], "gruppo": membri[0]["gruppo"],
            "valore": "", "dettaglio": coda,
            "rimedio": membri[0]["rimedio"], "ha_rimedio": membri[0]["ha_rimedio"],
            "conseguenza": membri[0]["conseguenza"],
            "occorrenze": sum(m.get("occorrenze") or 0 for m in membri),
            "unita": membri[0].get("unita", ""),
            "pagine": sorted({u for m in membri for u in (m.get("pagine") or [])}),
        })

    ordine_g = {"errore": 0, "avviso": 1, "nota": 2}
    fuori.sort(key=lambda a: (ordine_g.get(a["gravita"], 3),
                              ORDINE_GRUPPI.get(a["gruppo"], 9),
                              a.get("unita") or "",
                              -(a.get("occorrenze") or 0),
                              a["titolo"]))
    return fuori


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("cartella")
    p.add_argument("--config", default="analisi/audit-tecnico/config.json")
    a = p.parse_args()

    c = Path(a.cartella)
    if not (c / "scansione.json").exists():
        sys.exit(f"Manca {c}/scansione.json: lancia prima scansiona_sito.py.")
    scansione = leggi(c / "scansione.json")
    robots = leggi(c / "robots.json", {})
    crawler = leggi(c / "crawler.json", [])
    tls = leggi(c / "tls.json", {})
    sitemap = leggi(c / "sitemap.json", {})
    velocita = leggi(c / "velocita.json", {})
    link = leggi(c / "link.json", {})
    config = leggi(a.config, {}) or {}
    pagine = []
    if (c / "pagine.jsonl").exists():
        for riga in open(c / "pagine.jsonl", encoding="utf-8"):
            try:
                pagine.append(json.loads(riga))
            except ValueError:
                pass

    # Con --solo-aeo si tengono solo le verifiche che il Site Audit di Semrush o di Ahrefs
    # non fa. La scansione c'e' stata lo stesso: rendering e schema per sezione hanno
    # bisogno delle pagine, e dichiararle "in linea" senza averle lette sarebbe peggio.
    SOVRAPPOSTI = {"h1", "h2", "alt", "link-rotti", "soft-404", "canonical", "ssl", "peso-html"}

    indicatori = (gruppo_visibilita(crawler, robots, tls, pagine)
                  + gruppo_comprensione(pagine, config)
                  + gruppo_copertura(sitemap, robots, pagine, link)
                  + gruppo_velocita(velocita, pagine))
    if scansione.get("solo_aeo"):
        indicatori = [i for i in indicatori if i["id"] not in SOVRAPPOSTI]

    gruppi = {}
    for g, nome, domanda in (
        ("visibilita", "Ci vedono?", "Gli assistenti e i motori riescono a leggere il sito"),
        ("comprensione", "Ci capiscono?", "Quello che leggono è organizzato in modo che lo capiscano"),
        ("copertura", "Trovano tutto all'interno del sito web?", "Arrivano a tutte le pagine che contano"),
        ("velocita", "Quanto aspettano?", "Il sito risponde prima che rinuncino"),
    ):
        voci = [i for i in indicatori if i["gruppo"] == g]
        critici = sum(1 for i in voci if i["stato"] == "critico")
        attenzioni = sum(1 for i in voci if i["stato"] == "attenzione")
        # Un gruppo dove non si e' misurato niente non e' «tutto in linea»: e' non misurato.
        # Succedeva a «Quanto mi aspettano?» senza velocita.json, e la slide lo dava per sano.
        non_verificati = sum(1 for i in voci if i["stato"] == "non-verificato")
        stato = ("critico" if critici else "attenzione" if attenzioni
                 else "non-verificato" if voci and non_verificati == len(voci) else "ok")
        gruppi[g] = {"nome": nome, "domanda": domanda, "indicatori": len(voci),
                     "critici": critici, "attenzioni": attenzioni,
                     "non_verificati": non_verificati, "stato": stato}

    risultati = {
        "versione": 1, "sito": scansione["sito"], "data": scansione["data"],
        "pagine_scansionate": scansione.get("pagine_scansionate", 0),
        "max_pagine": scansione.get("max_pagine"),
        "sitemap_url": sitemap.get("totale_url", 0),
        "gruppi": gruppi, "indicatori": indicatori,
        "sommario": punteggio_da(indicatori),
        "limiti": {
            "campione": f"{it(scansione.get('pagine_scansionate', 0))} pagine su "
                        f"{it(sitemap.get('totale_url', 0))} dichiarate nella sitemap",
            "rendering": "Le pagine sono lette senza eseguire JavaScript, come fanno GPTBot, "
                         "ClaudeBot e PerplexityBot.",
            "crawler": "L'accesso dei crawler è provato con una richiesta per ogni nome, non "
                       "dedotto dal robots.txt. I controlli che verificano l'identità guardano "
                       "l'indirizzo di rete: qui si vede come il sito tratta chi si presenta così.",
        },
    }
    elenchi = elenchi_da(indicatori)
    (c / "elenchi.json").write_text(json.dumps(
        {"sito": scansione["sito"], "data": scansione["data"], "elenchi": elenchi},
        ensure_ascii=False, indent=1), encoding="utf-8")
    for i in indicatori:
        i.pop("_elenco_intero", None)
        i.pop("_descrizione_elenco", None)

    (c / "risultati.json").write_text(json.dumps(risultati, ensure_ascii=False, separators=(",", ":")),
                                      encoding="utf-8")
    azioni = azioni_da(indicatori)
    (c / "azioni.json").write_text(json.dumps(azioni, ensure_ascii=False, indent=1), encoding="utf-8")
    (c / "azioni-slide.json").write_text(
        json.dumps(azioni_per_slide(azioni), ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"Audit tecnico di {scansione['sito']}, {scansione['data']}")
    print(f"{len(indicatori)} indicatori su {scansione.get('pagine_scansionate', 0)} pagine\n")
    for g in gruppi.values():
        segno = {"ok": "●", "attenzione": "■", "critico": "▼",
                 "non-verificato": "○"}[g["stato"]]
        print(f"  {segno} {g['nome']:22} {g['critici']} critici, {g['attenzioni']} da guardare")
    print()
    for i in indicatori:
        if i["stato"] in ("critico", "attenzione"):
            print(f"  {'▼' if i['stato'] == 'critico' else '■'} {i['titolo'][:48]:50} {i['valore']}"
                  + (f"  ({i['dettaglio'][:60]})" if i["dettaglio"] else ""))
    righe_tot = sum(e["totale"] for e in elenchi)
    print(f"\nrisultati.json, azioni.json ed elenchi.json in {c}")
    print(f"{len(elenchi)} elenchi, {righe_tot} righe in tutto per il foglio di lavoro")


if __name__ == "__main__":
    main()
