---
name: ie-aeo-pubblica-hubspot
description: Carica in HubSpot, come bozza da rivedere e pubblicare a mano, un contenuto AEO approvato di un cliente scritto nel suo repo: un articolo nuovo come blog post, un contenuto ristrutturato sul post o sulla pagina che già esiste, una traduzione come variante di lingua del master. Converte il file in HTML con titolo, metadati e JSON-LD, blocca il caricamento se ci sono segnaposto o FAQ diverse dallo schema, mostra cosa crea o cambia e procede solo dopo l'ok. Non pubblica mai. Registra nel repo l'id di HubSpot e lascia l'elenco di ciò che resta da fare nell'editor. Usa questa skill quando l'utente chiede di caricare, mettere in bozza, portare o pubblicare in HubSpot un contenuto del repo, anche se dice solo "mettiamolo su HubSpot" o "carica la versione inglese".
---

# Caricamento in HubSpot come bozza

Ogni skill di contenuto finisce con un file approvato nel repo del cliente. Questa lo porta in HubSpot senza ricopiarlo a mano, dove si perdono titoli, FAQ e dati strutturati, e lo lascia **in bozza**: rivedere l'anteprima e pubblicare restano al consulente o al cliente. Funziona per qualsiasi cliente: dove caricare lo dice la configurazione nel suo repo.

Riferimenti:
- `scripts/prepara_pubblicazione.py`: dal file Markdown al pacchetto per HubSpot (titolo, HTML, metadati, JSON-LD) con i controlli che bloccano;
- `../../condivisi/archivio-contenuti.md`: formato e stati dei contenuti;
- `../ie-aeo-traduzione/SKILL.md`: le traduzioni da caricare come varianti di lingua;
- `../../condivisi/lettura-kb.md`: allineamento del repo.

## Cosa fa il connettore e cosa resta nell'editor

| Oggetto | Con il connettore | Nell'editor di HubSpot, a mano |
|---|---|---|
| **Blog post** (`manage_blog_post`) | Creare una bozza; aggiornare titolo, corpo HTML, meta description e tag; assegnare l'autore; leggere post, blog, tag e autori | Slug, codice nel `<head>` (il JSON-LD), immagine in evidenza, testi alternativi, lingua e collegamento tra varianti di lingua, data di pubblicazione |
| **Pagina del sito** (`manage_website_page`) | Leggere i moduli; cambiare i campi dei moduli nella bozza; metadati: titolo HTML, meta description, slug, lingua, codice nel `<head>` | Collegamento tra varianti di lingua, immagini, moduli nuovi complessi |
| **Landing page** (`manage_landing_page`) | Come le pagine del sito | Come le pagine del sito |

**Mai, con questa skill:** `PUBLISH`, `UNPUBLISH`, `RESTORE_REVISION`, modifiche a menu, template o moduli personalizzati. Il codice nel `<head>` di una pagina si sostituisce per intero e il connettore non permette di leggerlo prima: si scrive solo se il consulente conferma che la pagina non ne ha altro, altrimenti si incolla a mano.

## Configurazione del cliente

`contenuti/pubblicazione/config.json`, da creare al primo caricamento con il consulente:

```json
{
  "portale_id": 1234567,
  "destinazioni": {
    "blogpost": {"oggetto": "blog_post", "blog_id": {"it": 111, "en": 222}},
    "news": {"oggetto": "blog_post", "blog_id": {"it": 333, "en": 444}},
    "faq-prodotto": {"oggetto": "website_page", "nota": "box FAQ della pagina prodotto"},
    "pagina": {"oggetto": "website_page"}
  },
  "autore": {"blog_author_id": 0},
  "tag": "categoria",
  "varianti_lingua": "editor"
}
```

- `destinazioni`: per ogni tipo di contenuto (il campo `tipo` del frontmatter), l'oggetto di HubSpot e, per i blog, il blog di ogni lingua. Gli id si leggono con `LIST_BLOGS`.
- `autore`: l'autore dei blog post, letto con `GET_AUTHOR`. Serve per pubblicare.
- `tag`: `categoria` per usare come tag la categoria del contenuto, se esiste già tra i tag del blog; `nessuno` per non metterne.
- `varianti_lingua`: `editor` se le traduzioni sono varianti di lingua collegate al master, create dall'editor; `blog-separati` se ogni lingua ha il suo blog senza collegamento.

## 1. Prepara

1. **Allineamento:** segui "Prima di tutto" di `lettura-kb.md`.
2. **Contenuto:** il file in `contenuti/`. Deve essere `stato: approvato`. Per una traduzione anche `revisione_madrelingua: fatta`, se il cliente la prevede.
3. **Connettore e portale:** carica gli strumenti HubSpot (`ToolSearch` con `blog post` o `website page`) e leggi `LIST_BLOGS`. I blog devono essere quelli del sito del cliente e il portale quello di `config.json` (o di `analisi/hubspot-aeo/config.json`). Se il connettore è legato a un altro portale, fermati.
4. **Configurazione:** se manca, creala con il consulente partendo da `LIST_BLOGS` e `LIST_TAGS`.

## 2. Prepara il pacchetto

Dalla radice del repo del cliente, con il pacchetto fuori dal repo:

```bash
python3 -I <percorso della skill>/scripts/prepara_pubblicazione.py <file.md> --out <cartella temporanea>/pacchetto.json --html <cartella temporanea>/anteprima.html
```

Lo script stampa titolo, metadati, struttura e due elenchi:
- **Blocchi:** stato non approvato, segnaposto (`[DATO DA FORNIRE]`, `[DA CONFERMARE]`, `[DA VALIDARE]`) nel testo, nei metadati o nello schema, JSON-LD non valido, FAQ diverse dallo schema. **Con un blocco non si carica**: elenca cosa manca e fermati.
- **Avvisi:** meta title o description troppo lunghi o assenti, JSON-LD assente. Si possono accettare, dicendolo.

## 3. Trova la destinazione

| Caso | Destinazione |
|---|---|
| Contenuto nuovo | Un blog post nuovo nel blog della lingua, oppure una pagina indicata dal consulente |
| Contenuto ristrutturato o aggiornato | L'oggetto che c'è già. Se il frontmatter ha `hubspot_id`, usalo. Altrimenti, per un blog post, cercalo con `LIST_BLOG_POSTS` (gli ultimi 25); per una pagina, o un post più vecchio, chiedi al consulente l'URL dell'editor, che contiene l'id |
| FAQ prodotto | Il modulo della pagina prodotto che deve contenerle. Leggi `MODULES` e proponi in quale modulo vanno |
| Traduzione | La variante di lingua del master. Il master deve essere già in HubSpot (`hubspot_id` nel suo frontmatter). Con `varianti_lingua: editor` il consulente crea la variante dall'editor del master, così HubSpot collega le lingue e scrive gli `hreflang`, e poi ti dà l'id. Con `blog-separati` si crea un post nel blog della lingua, e il collegamento si fa a mano |

## 4. Proponi e aspetta l'ok

Mostra in chat, prima di qualsiasi scrittura:
- **oggetto e destinazione:** blog o pagina, nuovo o esistente, con il suo stato (bozza o pubblicato);
- **titolo, meta title, meta description, slug, lingua, tag, autore;**
- **cosa cambia**, se l'oggetto esiste: leggi prima il contenuto attuale (`GET_POST`, oppure `MODULES`) e riassumi le differenze: titolo, sottotitoli, sezioni nuove o tolte;
- **cosa resta da fare nell'editor**, dalla tabella iniziale;
- per un oggetto **già pubblicato:** le modifiche vanno nella bozza e diventano visibili solo con la pubblicazione. Dopo la scrittura controlli che la pagina online non sia cambiata.

**Fermati qui.** Si scrive in HubSpot solo dopo un ok esplicito.

## 5. Carica

Le scritture modificano la stessa bozza: una alla volta, mai in parallelo.

**Blog post nuovo:**
1. `LIST_TAGS` e scelta del tag esistente che corrisponde alla categoria. Non creare tag nuovi senza ok.
2. `CREATE` con `title`, `postBody` (il `corpo_html` del pacchetto), `metaDescription`, `tags`, `blogId` e `createdByAgent: "IE-AEO"`, seguendo il flusso di conferma del connettore.
3. `SET_AUTHOR` con l'autore della configurazione.

**Blog post esistente:**
1. `GET_POST` e salva il corpo attuale in un file temporaneo, fuori dal repo, per poterlo ripristinare.
2. `UPDATE` con `postBody`, `title`, `metaDescription` e, se cambiano, `tags`.

**Pagina del sito o landing page:**
1. `MODULES`: individua i moduli che contengono il testo da sostituire.
2. `SET_MODULE_FIELDS` per ogni modulo, con i valori esatti, o `BATCH` fino a 10 modifiche. Solo moduli già presenti: se ne serve uno nuovo, proponi dove e come, e aspetta un altro ok.
3. `SET_METADATA` con `htmlTitle`, `metaDescription`, `language` e, solo se il consulente conferma che la pagina non ne ha altro, `headHtml` con il JSON-LD del pacchetto.

**Traduzione:** come sopra, sull'id della variante di lingua. Per una pagina imposta anche `language` con il codice della lingua.

## 6. Verifica

1. Rileggi l'oggetto (`GET_POST` o `MODULES`) e confronta titolo, numero di sottotitoli, FAQ e meta description con il pacchetto.
2. Per un oggetto già pubblicato, scarica la pagina online (`curl -sL`) e controlla che sia quella di prima: le modifiche devono stare solo nella bozza. Se la pagina online è cambiata, dillo subito al consulente.
3. Mostra la bozza con `render_asset` (`BLOG_POST` o `WEBSITE_PAGE`).

## 7. Registra e consegna

1. **Frontmatter del contenuto:** aggiungi `hubspot_id`, `hubspot_oggetto`, `hubspot_editor_url` e `caricato_il`. Lo stato resta `approvato` finché qualcuno pubblica.
2. **Sezione "Pubblicazione in HubSpot"** in fondo al file: cosa è stato caricato, quando, e la lista delle operazioni da fare nell'editor, con il JSON-LD pronto da incollare se non è stato scritto dal connettore.
3. **In chat:** il link all'editor, cosa è stato caricato, la lista per l'editor (slug, JSON-LD, immagine in evidenza, testi alternativi, varianti di lingua, redirect se l'URL è cambiato con un ok precedente), e chi deve pubblicare.
4. **Dopo la pubblicazione**, quando il consulente lo dice o alla prossima esecuzione: `GET_POST` per lo stato; se è online, `stato: pubblicato` e `url` nel frontmatter, e la voce del piano editoriale aggiornata come dice `lettura-kb.md`.
5. **Commit e push** delle modifiche al repo solo con l'ok del consulente, dopo `git pull --rebase`.
