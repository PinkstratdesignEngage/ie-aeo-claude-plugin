---
name: ie-aeo-traduzione
description: Traduce e localizza in un'altra lingua, di solito l'inglese, un contenuto AEO di un cliente già scritto nel suo repo (articolo, news, FAQ prodotto, case study, pagina ristrutturata), partendo dal master approvato e dalla knowledge base del cliente. Usa la terminologia ufficiale del glossario, adatta esempi, dati e riferimenti che dipendono dal mercato, riscrive le domande come le fanno gli utenti in quella lingua, traduce metadati e Schema.org e collega le versioni. Controlla con uno script che numeri, nomi di prodotto e struttura coincidano con il master. Usa questa skill quando l'utente chiede di tradurre, localizzare, fare la versione inglese (o in un'altra lingua) di un contenuto, anche se dice solo "facciamolo anche in inglese" o "serve la versione EN di questo articolo".
---

# Traduzione e localizzazione

Un contenuto AEO tradotto deve rispondere alle domande che gli utenti fanno **in quella lingua** agli assistenti AI, con i termini che il cliente usa nei suoi materiali in quella lingua. Una traduzione letterale perde entrambe le cose. Il master resta nella lingua della knowledge base; la traduzione sta accanto al master, nel repo del cliente, e segue le sue regole.

Riferimenti:
- `scripts/confronta_versioni.py`: confronta master e traduzione (numeri, nomi, struttura, link, segnaposto);
- `../../condivisi/lettura-kb.md`: allineamento del repo e regole sui dati;
- `../../condivisi/checklist-aeo.md`: i controlli, che valgono anche nella lingua di arrivo;
- `../../condivisi/schema-org.md`: lingua e collegamento tra versioni nello schema;
- `../../condivisi/archivio-contenuti.md`: dove salvare le traduzioni;
- `../../condivisi/scripts/verifica_faq_schema.py`: FAQ e schema identici;
- `../ie-aeo-pubblica-hubspot/`: per caricare la traduzione in HubSpot come variante di lingua.

## Configurazione del cliente

`contenuti/traduzioni/config.json`, da creare alla prima traduzione con il consulente, partendo da `CLAUDE.md` del cliente (mercati e lingue):

```json
{
  "lingue": [
    {"codice": "en", "variante": "en-GB", "mercati": ["GB", "IE"], "slug": "uguale"}
  ],
  "revisione_madrelingua": true
}
```

- `variante`: la forma della lingua (per esempio inglese britannico o americano). Si ricava dai materiali del cliente in quella lingua: se il glossario o i suoi testi la indicano, segui quelli.
- `mercati`: i paesi per cui si scrive. Determinano esempi, valute, normative e riferimenti.
- `slug`: `uguale` se il sito usa lo stesso slug in tutte le lingue, `tradotto` se lo traduce. Si guarda come fa oggi il sito del cliente.
- `revisione_madrelingua`: se un madrelingua del cliente rivede le traduzioni prima della pubblicazione.

Se il cliente ha domande aperte su lingue e mercati, il file lo dice e la skill lo ricorda.

## 1. Prepara

1. **Allineamento:** segui "Prima di tutto" di `lettura-kb.md`.
2. **Master:** il file da tradurre, in `contenuti/`. Di norma `stato: approvato`: tradurre una bozza raddoppia le revisioni. Se è in bozza, dillo e procedi solo se il consulente conferma. Se il contenuto esiste solo come pagina pubblicata, salvane la copia in `raw/sito/` come fa `ie-aeo-ristruttura-contenuti` e usala come master.
3. **Traduzione esistente:** se c'è già `<master>-<lingua>.md`, aggiornala invece di rifarla: confronta le date di aggiornamento e traduci solo le parti cambiate nel master.
4. **Knowledge base:** `04-brand-voice/glossario.md`, con la sezione dei termini nella lingua di arrivo (per esempio "Termini in inglese") e i termini da evitare; `tone-of-voice.md`, sezione sul pubblico internazionale; `CLAUDE.md`; il modello di struttura della tipologia in `contenuti/modelli/`, se c'è.
5. **Domande nella lingua di arrivo:** come le scrivono davvero gli utenti. Se ci sono dati di Search Console, lancia `analizza_gsc.py --tema` con le parole del tema in quella lingua, come in `lettura-kb.md`: le query nella cartella di quella lingua (per esempio `/en/`) dicono come si cerca. Se ci sono dati di Semrush, guarda il database del mercato.

## 2. Prepara la terminologia e le scelte di adattamento

**Termini dai materiali del cliente.** Se il cliente ha l'indice di `raw/` e materiali nella lingua di arrivo (per esempio cataloghi in inglese accanto a quelli in italiano), cerca le frasi del master che contengono termini tecnici fuori dal glossario, filtrando sulla lingua di arrivo: `indice.py cerca "<frase del master>" --lingua en -k 3`. I passaggi trovati sono spesso la versione del cliente dello stesso testo, con i termini che usa davvero: proponili con file e pagina come fonte. Restano proposte da approvare, e i termini nuovi entrano nel glossario solo con l'ok.

Prima di tradurre, prepara e mostra in chat:

| Cosa | Contenuto |
|---|---|
| **Termini** | I termini tecnici del master con la traduzione del glossario. Per quelli che il glossario non ha, una proposta con la fonte (un materiale del cliente in quella lingua) o "da confermare" |
| **Nomi che non si traducono** | Prodotti, tecnologie, marchi, come nel glossario |
| **Domanda principale e H2** | Riformulati come li scrive un utente in quella lingua, con le query reali se ci sono |
| **Adattamenti** | Ciò che dipende dal paese: valute e prezzi dell'energia, incentivi, normative, servizi disponibili solo in alcuni paesi, esempi e riferimenti locali. Per ognuno: cosa cambia, oppure perché resta |
| **Link** | Le pagine collegate che esistono nella lingua di arrivo, da usare al posto di quelle del master |
| **Slug** | Secondo `config.json` |

Se tutti i termini sono nel glossario e non ci sono adattamenti, dillo in una riga e procedi. Altrimenti **fermati** e aspetta l'ok sulle scelte: sono decisioni che valgono anche per le traduzioni successive.

## 3. Traduci

- **Tutto ciò che si pubblica:** titolo, risposta iniziale, testo, tabelle, FAQ, metadati, testi alternativi delle immagini, Schema.org.
- **Fedeltà ai dati:** numeri, unità, date e fonti restano quelli del master. Cambia solo la forma, per esempio i separatori delle migliaia e dei decimali o il formato delle date. Non aggiungere dati che il master non ha: se un adattamento richiede un dato per il mercato di arrivo, usa `[DATA TO BE PROVIDED: ...]` e segnalalo.
- **Citazioni:** si traducono fedelmente, senza accorciarle né completarle. Restano attribuite alla stessa persona.
- **Tono:** quello di `tone-of-voice.md`, con la persona grammaticale prevista per il canale. In inglese, per esempio, "you" al lettore e il cliente in terza persona, se il master fa così.
- **Struttura:** la stessa del master e del modello della tipologia. La domanda principale e gli H2 possono cambiare parola, non contenuto.
- **Metadati:** meta title fino a 60 caratteri e meta description fino a 155 nella lingua di arrivo, scritti per quella lingua, non accorciati dal master.
- **Schema.org:** `inLanguage` con la variante (per esempio `en-GB`), FAQ identiche a quelle del testo, `translationOfWork` con l'`@id` del master. Nel master si aggiunge `workTranslation` verso la traduzione: proponilo, non modificare il master senza ok.

## 4. Controlla

1. **Confronto con il master**, dalla radice del repo del cliente:

   ```bash
   python3 -I <percorso della skill>/scripts/confronta_versioni.py <master.md> <traduzione.md>
   ```

   Correggi ogni differenza nei numeri e nei nomi, o spiega perché è voluta. Lo script legge i numeri con i separatori della lingua di ciascun file: un "2.500" in un testo inglese vale 2,5.
2. **Schema:** `python3 -m json.tool` sul JSON-LD, poi `python3 ../../condivisi/scripts/verifica_faq_schema.py <traduzione.md>`.
3. **Checklist AEO:** passa `checklist-aeo.md` nella lingua di arrivo, compresi i termini da evitare: un termine vietato nella lingua del master lo è anche nella traduzione.

## 5. Salva e consegna

1. **File:** accanto al master, con il suffisso della lingua: `AAAA-MM-GG-slug-en.md`. Frontmatter come il master, con:
   - `lingua`: la variante, per esempio `en-GB`;
   - `traduzione_di`: il percorso del master;
   - `stato: bozza`;
   - `revisione_madrelingua: da-fare`, se `config.json` la prevede;
   - `url`: l'URL previsto nella lingua di arrivo.
2. **Note di traduzione:** in fondo al file, una sezione con termini scelti, adattamenti fatti e segnaposto.
3. **In chat:**
   - un riepilogo di 3-4 righe;
   - i termini nuovi da aggiungere al glossario, solo con l'ok del consulente;
   - i segnaposto e le domande per il cliente;
   - le pagine collegate che mancano nella lingua di arrivo;
   - per la pubblicazione: la versione tradotta va collegata al master come variante di lingua, così il sito genera gli `hreflang`. Con HubSpot lo fa `ie-aeo-pubblica-hubspot`.
4. **Piano editoriale:** se il contenuto è nel piano del mese, aggiorna la voce come dice `lettura-kb.md`.
5. **Prompt:** proponi a `ie-aeo-prompt` un prompt nella lingua di arrivo sul tema, se il mercato è tra quelli misurati.
6. **Commit e push** solo con l'ok del consulente, dopo `git pull --rebase`.

Dopo la revisione del madrelingua e l'ok del consulente: `stato: approvato`, `revisione_madrelingua: fatta`.
