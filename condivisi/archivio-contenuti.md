# Archivio dei contenuti nel repo del cliente

I contenuti prodotti dalle skill IE-AEO restano nel repo della knowledge base. Così il team li ritrova, li aggiorna e non li duplica.

## Struttura

```
contenuti/
├── README.md               regole e stato dei contenuti (da template)
├── categorie-blog.md       categorie del blog del cliente, con l'uso di ciascuna
├── blog/                   AAAA-MM-GG-slug.md
├── faq-prodotto/           <slug-prodotto>.md
├── case-study/             AAAA-MM-GG-slug.md e registro-casi.md (skill ie-aeo-case-study)
├── glossario/              <termine>.md e indice.md
├── modelli/                <tipologia>.md, i modelli di struttura approvati
├── piano-editoriale/       config.json e AAAA-MM.md, un piano per mese (skill ie-aeo-piano-editoriale)
├── traduzioni/             config.json: lingue, varianti, mercati e slug (skill ie-aeo-traduzione)
└── pubblicazione/          config.json: dove va ogni tipo di contenuto in HubSpot (skill ie-aeo-pubblica-hubspot)
```

Le traduzioni stanno accanto all'originale, con il suffisso della lingua: `AAAA-MM-GG-slug-en.md`. Nel frontmatter hanno `lingua` con la variante (per esempio `en-GB`), `traduzione_di` con il percorso del master e, se il cliente la prevede, `revisione_madrelingua` (`da-fare` o `fatta`).

Altre tipologie, per esempio `news/` o `pagina/`, si aggiungono quando servono, con lo stesso schema di nome dei file.

## Modelli di struttura

`contenuti/modelli/<tipologia>.md` fissa le regole di forma di una tipologia di contenuto per il cliente: blocchi e ordine, lunghezza, FAQ, Schema.org, metadati. Lo crea la skill `ie-aeo-ristruttura-contenuti` dal primo piano approvato di quella tipologia, con il formato descritto nella skill.

- Le skill di contenuto lo leggono e lo seguono per tutti i contenuti dello stesso tipo, nuovi o ristrutturati.
- Si modifica solo con l'ok del consulente: si aumenta `versione` e si aggiunge una riga al registro delle modifiche in fondo al file.
- Contiene regole di forma, non dati di un singolo contenuto.

I contenuti ristrutturati hanno nel frontmatter anche `origine` (URL o file dell'originale) e `modello` (file e versione del modello applicato).

## Ciclo di vita (campo `stato` nel frontmatter)

| Stato | Significato |
|---|---|
| `brief` | Il content brief aspetta l'approvazione del consulente |
| `bozza` | Il testo è scritto e aspetta la revisione |
| `approvato` | Rivisto, pronto per la pubblicazione o la traduzione |
| `pubblicato` | Online. Il campo `url` contiene l'indirizzo |

## Struttura del file

Per blog post, case study e glossario:

1. **Frontmatter**, come nel content brief.
2. **Testo pubblicabile**: titolo, testo, FAQ.
3. **Metadati per il CMS**: meta title, meta description, slug.
4. **Schema.org** in un blocco di codice `json`.
5. **Brief**, in fondo: il content brief approvato, con le fonti. Nei contenuti ristrutturati, al suo posto ci sono il report prima/dopo e l'analisi con il piano approvato.

Le FAQ prodotto non hanno un brief: il modello del file è nella skill `ie-aeo-faq-prodotto` (frontmatter, FAQ, fonti per risposta, punti mancanti, domande aperte che pesano, Schema.org).

## Dopo l'approvazione

- In `05-content-pillars/<pillar>/domande-aeo.md` segna quali domande il contenuto copre, con il link al file.
- Le nuove domande per il cliente emerse durante il lavoro vanno in `domande-aperte.md`; le nuove incoerenze in `fonti/incoerenze-cliente-sito.md`.
- Commit con un messaggio che dice tipo e titolo. Push dopo l'ok del consulente.
- **Traduzione:** se il contenuto va anche in un'altra lingua, `ie-aeo-traduzione` parte dal master approvato.
- **HubSpot:** `ie-aeo-pubblica-hubspot` carica il contenuto approvato come bozza e aggiunge al frontmatter `hubspot_id`, `hubspot_oggetto`, `hubspot_editor_url` e `caricato_il`. La pubblicazione la fa il consulente o il cliente; dopo, `stato: pubblicato` e `url`.
