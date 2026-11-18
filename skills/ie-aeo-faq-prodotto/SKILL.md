---
name: ie-aeo-faq-prodotto
description: Genera le FAQ verticali di una pagina prodotto in ottica AEO, partendo dall'URL della pagina e dalla knowledge base del cliente. Segnala i punti mancanti, con le domande da fare al cliente, e produce lo Schema.org Product + FAQPage in JSON-LD. Usa questa skill quando l'utente dà il link di una pagina prodotto o di categoria e chiede FAQ, domande e risposte, un box FAQ, dati strutturati o schema per quel prodotto, anche se dice solo "fammi le FAQ di questo banco" o "ottimizza questa pagina prodotto per l'AI".
---

# FAQ prodotto AEO

Le FAQ di una pagina prodotto rispondono alle domande concrete che un buyer, un tecnico o un progettista fa su quel prodotto. Gli assistenti AI le usano spesso come fonte. Devono essere specifiche del prodotto e basate solo su dati verificati.

I riferimenti comuni sono in `../../condivisi/`:
- `lettura-kb.md`: allineamento del repo e regole sui dati;
- `checklist-aeo.md`: la sezione "FAQ prodotto" dice quali punti valgono qui;
- `schema-org.md`;
- `archivio-contenuti.md`;
- `../../condivisi/scripts/verifica_faq_schema.py`: controlla che FAQ e schema coincidano;
- `../../condivisi/scripts/analizza_gsc.py`: le query di Search Console della pagina prodotto e le altre pagine che le contendono.

**Niente content brief.** Le FAQ sono un contenuto breve e verificabile riga per riga: si scrivono subito e il consulente rivede la bozza. Le domande aperte che pesano sulle risposte stanno nel file, in una sezione apposita. Nuove domande per il cliente e nuove incoerenze si propongono, ma si aggiungono ai file del repo solo con l'ok del consulente.

## 1. Leggi la pagina e la knowledge base

Prima di tutto segui la parte "Prima di tutto" di `lettura-kb.md`: allineamento del repo e `CLAUDE.md`.

1. **Pagina.** Scarica l'HTML con `curl -sL "<url>"` e leggilo dal file, non con WebFetch: WebFetch riassume, e nelle pagine prodotto molti dati sono negli attributi `alt` delle immagini e delle icone (classi energetiche, alimenti, refrigeranti) o in elenchi di versioni che il riassunto perde. Cerca con `grep -o 'alt="[^"]*"'` e leggi il testo visibile. Annota descrizione, versioni, dati tecnici, classe energetica per versione, icone, accessori, documenti scaricabili, immagini.
2. **Copia in `raw/`.** Se la pagina non ha ancora una copia in `raw/sito/`, salvala con lo script della skill di knowledge base, dalla radice del repo del cliente:
   ```bash
   python3 -I <percorso del plugin>/skills/ie-aeo-knowledgebasecreator/scripts/snapshot_pagina.py "<url>" "raw/sito/<percorso-con-__>-analizzato.md"
   ```
   Il nome del file segue le regole di `raw/`: il percorso dell'URL con `__` al posto di `/`, più il suffisso `-analizzato`.
3. **Cosa leggere della knowledge base.** Per un singolo prodotto non serve tutto:
   - `CLAUDE.md`, `04-brand-voice/glossario.md` e `tone-of-voice.md`;
   - la riga del prodotto e le sue discrepanze nel catalogo: `grep -n -i "<nome prodotto>" 03-offerta/prodotti/catalogo-*.md`;
   - le tecnologie che il prodotto usa, in `03-offerta/tecnologie.md`;
   - `grep -n -i` sul nome del prodotto e delle sue tecnologie in `domande-aperte.md`, `fonti/incoerenze-cliente-sito.md` e `fonti/registro-fonti.md`;
   - `03-offerta/servizi.md` per installazione e assistenza;
   - le domande AEO del pillar e le domande delle personas, per scegliere le FAQ.
4. **Cataloghi PDF.** Usa i dati già estratti nel catalogo della knowledge base. Per controllare un dato nei PDF di `raw/`, o cercare un dato che la knowledge base non ha prima di segnarlo come mancante:
   - **con l'indice di `raw/`** (se c'è `fonti/indice-raw/config.json`): cerca il prodotto e il dato, per esempio `indice.py cerca "<prodotto> superficie espositiva" "<prodotto> temperatura di conservazione" --cartella raw/drive/prodotti`, come in "Ricerca nei materiali originali" di `lettura-kb.md`. Restituisce file e pagina, anche dal catalogo nell'altra lingua, e le tabelle tecniche in Markdown. Le classi energetiche nei cataloghi sono spesso icone: nelle tabelle estratte la riga è vuota, e questo non vuol dire che il dato manchi;
   - **senza indice**, o per leggere la pagina trovata: PyMuPDF (`import fitz`) con un normale `python3`, senza `-I`: con `-I` la libreria non si carica.

   Un dato trovato nel PDF e assente dalla knowledge base va tra i punti da confermare, con file e pagina, e si propone di aggiungerlo al catalogo della knowledge base.
5. **Contenuti esistenti.** Se esiste già `contenuti/faq-prodotto/<slug>.md`, aggiorni quel file, non lo riscrivi da zero.
6. **Dati di Search Console.** Segui la sezione omonima di `lettura-kb.md` e lancia `analizza_gsc.py` con l'URL della pagina prodotto. Ottieni:
   - le **query della pagina**: le ricerche reali con cui le persone arrivano al prodotto, da usare per scegliere e formulare le FAQ;
   - le **cannibalizzazioni**: altre pagine che prendono le query del prodotto, per esempio un articolo, una pagina di categoria o la versione in un'altra lingua. Controlla anche l'ultimo report in `analisi/search-console/` per le decisioni già prese sulla pagina.

## 2. Scegli le domande

Prepara 6-10 FAQ, verticali sul prodotto, che coprano più angoli:
- **Uso:** per quali reparti, alimenti, formati e superfici di negozio.
- **Prestazioni:** temperature, classi energetiche per versione, consumi, tecnologie di risparmio.
- **Versioni:** remoto o plug-in, porte o aperto, lunghezze e altezze, accessori.
- **Installazione e servizio:** cosa serve per installarlo, assistenza, ricambi, dove sono disponibili i servizi.
- **Confronto:** quando sceglierlo rispetto a un altro prodotto dello stesso cliente.

Scrivi le domande come le farebbe un utente a un assistente AI, nominando il prodotto: "Quanto consuma ASTANA P?" e non "Consumi". Escludi le domande a cui la knowledge base non permette di rispondere con una fonte: diventano punti mancanti.

Con i dati di Search Console, parti dalle query reali della pagina: ogni query con click o impressioni rilevanti, se la knowledge base permette di rispondere, deve trovare risposta in una FAQ o nel testo della pagina. Non scrivere FAQ che rispondono alla domanda principale di un'altra pagina del sito con lo stesso intento: segnalala tra le cose da migliorare.

## 3. Scrivi le risposte

- **Forma:** 2-4 frasi, con la risposta nella prima. Numeri con unità e base di confronto, nomi con la grafia del glossario.
- **Versioni:** se un dato cambia per versione (per esempio la classe energetica tra remoto e plug-in), dillo esplicitamente.
- **Dati controversi:** non vanno in una risposta, ma tra i punti mancanti. Un dato è controverso quando:
  - fonti diverse lo danno in modo diverso (pagina, catalogo della knowledge base, PDF);
  - la stessa pagina lo dà in due modi, per esempio la scheda tecnica dice una cosa e la descrizione o le icone un'altra;
  - è segnato `[DA VALIDARE]` o compare in una voce aperta di `fonti/incoerenze-cliente-sito.md`.
  Se una parte del dato è certa, puoi usare solo quella e dirlo nella sezione "Domande aperte che pesano su queste FAQ".
- **Tono:** quello di `tone-of-voice.md`, ma più asciutto, perché le FAQ sono informative.
- **Testo pulito:** nelle risposte niente codici fonte né marcatori: le fonti vanno nella tabella apposita.

## 4. Punti mancanti e domande per il cliente

Elenca in una tabella cosa manca per rispondere bene a domande utili:
- dati assenti dalla pagina o dalla knowledge base;
- dati controversi, come definiti sopra;
- informazioni che andrebbero aggiunte alla pagina, per esempio consumi in kWh/24h o refrigerante.

Per ogni punto scrivi la domanda pronta da fare al cliente e dove andrebbe: `domande-aperte.md`, `fonti/incoerenze-cliente-sito.md` o entrambi. Numera le proposte proseguendo dall'ultimo numero di ciascun file, così il consulente le copia senza rinumerare. Se una domanda esiste già, collegala invece di duplicarla.

## 5. Schema.org

Un `@graph` con:
- **`Product`:** nome, descrizione, brand, produttore, categoria, URL, caratteristiche tecniche in `additionalProperty`, classe energetica solo se certa per la versione descritta. Se la classe cambia per versione, usa `ProductModel` con `isVariantOf`;
- **`FAQPage`:** domande e risposte identiche a quelle in pagina;
- **`Organization`.**

Segui `schema-org.md`. Per l'immagine puoi usare l'URL di un'immagine letta sulla pagina del prodotto: segnalalo nei punti mancanti, perché il cliente confermi quale immagine ufficiale usare.

Poi controlla:
1. `python3 -m json.tool` sul blocco JSON;
2. `python3 ../../condivisi/scripts/verifica_faq_schema.py <file>`: verifica che domande e risposte nello schema siano identiche a quelle del testo. Se le cambi, rilancia il controllo.

## 6. Il file

Salva in `contenuti/faq-prodotto/<slug-prodotto>.md` con questa struttura:

```markdown
---
tipo: faq-prodotto
titolo: FAQ <NOME PRODOTTO>
prodotto: <NOME PRODOTTO>
stato: bozza
lingua: it-IT
url: <URL della pagina prodotto>
persone: [<nomi dei file delle personas a cui rispondono le FAQ>]
domande_aeo: [<numeri da domande-aeo.md del pillar, con "(in parte)" se coperte solo in parte>]
fonti: [<codici fonte usati>]
ultimo_aggiornamento: AAAA-MM-GG
---

# FAQ <NOME PRODOTTO>

Una riga: per quale pagina è il box e che il testo deve restare identico allo schema.

## Domande frequenti

### <Domanda 1, che nomina il prodotto>?
<Risposta di 2-4 frasi.>

## Fonti per risposta
| # | Domanda | Fonti |

## Punti mancanti e domande per il cliente
| # | Punto | Cosa dicono le fonti | Domanda per il cliente | Dove andrebbe |

**Cosa migliorare nella pagina prodotto per l'AEO**
- 2-4 punti.

## Query di Search Console
Estrazione usata (`raw/gsc/<data>/`) oppure "dati non disponibili".
| Query | Click | Impressioni | Dove risponde (FAQ n. o testo della pagina) |
**Cannibalizzazioni:** | Query | Altra pagina | Quota | Rimedio proposto |, oppure "nessuna".

## Domande aperte che pesano su queste FAQ
Per ogni domanda aperta o incoerenza rilevante: quale FAQ tocca e come l'hai gestita.

## Schema.org
```json
{ "@context": "https://schema.org", "@graph": [ ... ] }
```
```

## 7. Consegna

1. **Checklist.** Passa i punti di `checklist-aeo.md` indicati nella sezione "FAQ prodotto".
2. **In chat:**
   - le FAQ;
   - i punti mancanti con le domande per il cliente, chiedendo l'ok prima di aggiungerle ai file;
   - lo schema, o il percorso del file se è lungo;
   - due righe su cosa migliorare nella pagina prodotto per l'AEO;
   - le cannibalizzazioni trovate, con il rimedio proposto: le azioni sulle altre pagine restano al consulente.
3. **Dopo l'approvazione:** segui `archivio-contenuti.md`.
