---
name: ie-aeo-ristruttura-contenuti
description: Ristruttura in chiave AEO (Answer Engine Optimization) un contenuto esistente di un cliente (articolo, case study, news, pagina) dal suo URL, da un file o dal testo incollato. Analizza i gap AEO, controlla i dati sulla knowledge base, valuta l'URL e, con i dati di Google Search Console, query da proteggere e cannibalizzazione. Propone un piano da approvare, poi riscrive. La prima ristrutturazione approvata di una tipologia diventa un modello di struttura nel repo del cliente, applicato ai contenuti successivi dello stesso tipo. Usa questa skill quando l'utente chiede di ristrutturare, riscrivere, aggiornare o ottimizzare per l'AI un contenuto esistente, anche se dice solo "sistemami questo vecchio post" o "rendi questo case study citabile da ChatGPT". Per un contenuto nuovo usa ie-aeo-blogpost, per le FAQ di una pagina prodotto ie-aeo-faq-prodotto.
---

# Ristrutturazione AEO di contenuti esistenti

Un contenuto vecchio ha spesso una base valida: un caso reale, dati, un URL che ha già posizionamento e citazioni. Il lavoro non è riscriverlo da zero, ma dargli la forma che gli assistenti AI (ChatGPT, Perplexity, Google AI Overview) riescono a capire e citare, senza perdere ciò che funziona e senza aggiungere fatti senza fonte. Il lavoro si fa nel repo della knowledge base del cliente: ogni cliente ha il suo repo, e lì restano contenuti e modelli.

I riferimenti comuni sono in `../../condivisi/`:
- `lettura-kb.md`: allineamento del repo, cosa leggere e regole sui dati;
- `checklist-aeo.md`: i criteri dell'analisi e i controlli prima della consegna;
- `schema-org.md`;
- `archivio-contenuti.md`: dove salvare, stati e modelli di struttura;
- `../../condivisi/scripts/verifica_faq_schema.py`: controlla che FAQ e schema coincidano;
- `../../condivisi/scripts/analizza_gsc.py`: incrocia le coppie query-pagina di Google Search Console e trova le query da proteggere e le possibili cannibalizzazioni.

Il processo ha due punti di arresto: il piano e il modello si applicano solo dopo un'approvazione esplicita del consulente.

## 1. Raccogli il contenuto

1. **Contenuto.** Accetti un URL, un file o un testo incollato. Se è un URL, scarica l'HTML con `curl -sL "<url>"` e leggilo dal file, non con WebFetch: WebFetch riassume e perde titoli, link, testi alternativi delle immagini e dati strutturati già presenti. Annota H1, sottotitoli, link interni, immagini, data di pubblicazione, eventuale JSON-LD.
2. **Copia dell'originale in `raw/`.** Serve per il confronto prima/dopo e resta come fonte. Per un URL usa lo script della skill di knowledge base, dalla radice del repo del cliente:
   ```bash
   python3 -I <percorso del plugin>/skills/ie-aeo-knowledgebasecreator/scripts/snapshot_pagina.py "<url>" "raw/sito/<percorso-con-__>-analizzato.md"
   ```
   Per un file o un testo incollato segui le convenzioni di `raw/README.md`.
   Se l'originale è pubblicato dal cliente, è anche una fonte: controlla che sia nel registro fonti, spesso sotto un codice che raggruppa più pagine con lo slug (per esempio `[S31 <slug>]` per le news). Se manca, proponi di registrarlo.
3. **Tipologia.** Deducila dal contenuto (per esempio `blog`, `case-study`, `news`, `pagina`) e falla confermare. La tipologia coincide con la cartella di `contenuti/` e ha un solo modello. I formati diversi della stessa tipologia, per esempio intervista, evento o annuncio per le news, sono **varianti** dentro quel modello, non tipologie nuove. Se la tipologia è nuova, proponi il nome della cartella.
4. **Modello esistente.** Controlla se c'è `contenuti/modelli/<tipologia>.md`. Se c'è, leggilo: vale come regola di struttura per questo contenuto (vedi il passo 5).
5. **Dati di Google Search Console (GSC).** Segui la sezione omonima di `lettura-kb.md`: l'estrazione di riferimento è `raw/gsc/<data più recente>/query_pagina.csv`, prodotta dalla skill `ie-aeo-search-console`, con il report in `analisi/search-console/`. Dalla stessa cartella leggi anche:
   - `pagine_in_calo.csv`: se la pagina c'è, il calo di click rispetto all'anno prima entra nella diagnosi;
   - `cannibalizzazioni.csv` e la sezione "Cannibalizzazioni" del report: casi e decisioni già prese che riguardano la pagina;
   - `opportunita.csv`: query vicine alla prima pagina di Google che la versione ristrutturata può conquistare.
   Se l'estrazione non c'è, proponi di lanciare `ie-aeo-search-console`. Va bene anche un export del consulente con le coppie query-pagina (Looker Studio, Search Analytics for Sheets: l'export dell'interfaccia web non basta), salvato come `raw/gsc/gsc-query-pagina-AAAA-MM-GG.csv`. Se i dati non ci sono, procedi lo stesso e scrivi nella diagnosi che la cannibalizzazione è stata valutata solo sui contenuti del repo e del sito.

## 2. Leggi la knowledge base

Segui `lettura-kb.md`. In più:
- cerca in `contenuti/` se esiste già una versione ristrutturata o un contenuto nuovo sullo stesso tema, per non duplicarlo;
- cerca il contenuto nel registro fonti (`grep -n -i` sull'URL o sul titolo): spesso è già stato letto come esempio o come fonte;
- se il tema rientra in un pillar, leggi le sue `domande-aeo.md` per scegliere la domanda principale.

## 3. Analizza

Valuta il contenuto su cinque fronti.

**Da conservare.** Cosa funziona già: un caso reale, dati con fonte, citazioni, una struttura chiara, link che portano traffico. La ristrutturazione non deve perderlo.

**Citazioni.** Le parole attribuite a una persona (le risposte di un'intervista, una dichiarazione di un manager o di un cliente) non si riscrivono. Si possono dividere in paragrafi e correggere refusi evidenti, ma non parafrasare, accorciare o completare. Gli interventi AEO stanno intorno alle citazioni: domande, titoli, risposta iniziale, riepiloghi, FAQ, schema. Se una citazione contiene un dato da correggere o un riferimento poco chiaro fuori dall'Italia, segnalalo nel piano: si chiarisce nel testo intorno, non dentro la citazione.

**Gap AEO.** Passa `checklist-aeo.md` punto per punto, sezioni Struttura, Contenuto e Collegamenti e metadati. Per ogni punto indica: soddisfatto, in parte, mancante. Aggiungi i criteri del modello, se esiste.

**Dati.** Confronta ogni numero, nome di prodotto e affermazione verificabile con la knowledge base, con `domande-aperte.md` e con `fonti/incoerenze-cliente-sito.md`. Classifica ciascuno:

| Esito | Significato | Cosa proponi |
|---|---|---|
| Confermato | Nella knowledge base con una fonte | Si tiene |
| Fonte unica | Solo nel contenuto originale, pubblicato dal cliente | Si tiene, con l'originale come fonte. Nelle FAQ e nello schema si riporta con la stessa formulazione e le stesse limitazioni (per esempio "nelle configurazioni compatibili") |
| Superato | La knowledge base ha un valore più recente | Si aggiorna, citando la fonte nuova |
| In contrasto | Contraddetto da un'altra fonte o in una voce delle incoerenze | Non si presenta come certo: segnaposto o domanda al cliente |
| Trovato nei materiali | Assente dalla knowledge base, ma presente in un materiale di `raw/` (con l'indice: "Ricerca nei materiali originali" di `lettura-kb.md`) | Si tiene con file e pagina come fonte, dopo l'ok del consulente, e si propone di aggiungerlo alla knowledge base |
| Non verificabile | Assente dalla knowledge base e, se c'è l'indice, dai materiali | Si tiene solo con l'ok del consulente, oppure segnaposto `[DATO DA FORNIRE: ...]` |

Usa la grafia del glossario per i nomi e segnala i termini vietati.

**Query e cannibalizzazione.** Con i dati GSC, lancia dalla radice del repo del cliente:
```bash
python3 -I <percorso del plugin>/condivisi/scripts/analizza_gsc.py raw/gsc/<data>/query_pagina.csv "<url della pagina>"
```
Lo script restituisce due tabelle.
- **Query da proteggere:** le query che portano clic alla pagina. La versione ristrutturata deve continuare a rispondere a ciascuna, nella risposta iniziale, in un H2 o in una FAQ. La domanda principale va scelta in modo coerente con le query che portano più clic: se la domanda AEO più vicina è diversa, dillo nel piano.
- **Possibili cannibalizzazioni:** le query su cui un'altra pagina del sito prende almeno il 20% dei clic, o delle impressioni se i clic sono pochi. La soglia si cambia con `--quota`.

Lo script trova le sovrapposizioni, ma non decide. Se il report di `ie-aeo-search-console` ha già una decisione su una di queste query, applicala e dillo nel piano. Per le altre valuta l'intento:
- **Intento diverso** (per esempio una pagina prodotto e un articolo che spiega la tecnologia): la sovrapposizione è normale. Basta un link interno tra le due pagine, con un testo del link chiaro.
- **Stesso intento:** le pagine si fanno concorrenza. Proponi il rimedio più leggero che risolve:
  1. **differenziare:** ciascuna pagina risponde a una domanda diversa, si aggiorna l'angolo del contenuto ristrutturato e le due pagine si collegano;
  2. **consolidare:** si uniscono i contenuti nella pagina più forte, quella con più clic e link, e si mette un redirect 301 dalla più debole. È un cambio di URL, quindi vale la moderazione del punto URL;
  3. **canonical:** solo per pagine quasi identiche che devono restare entrambe online.

Anche senza GSC, controlla che la domanda principale non sia già quella di un altro contenuto in `contenuti/` o di un'altra pagina del sito: la ristrutturazione non deve creare una cannibalizzazione nuova.

**URL.** Il punto di partenza è tenere l'URL: ha già posizionamento, link in entrata e citazioni, e ogni cambio ne fa perdere una parte. Più la pagina riceve clic nei dati GSC, più forte deve essere il motivo per cambiarlo. Proponi un nuovo slug solo se quello attuale crea un problema concreto, per esempio:
- contiene una data, un ID o parole senza significato;
- descrive un tema diverso da quello del contenuto ristrutturato;
- è in una lingua diversa da quella della pagina;
- è molto lungo o contiene termini vietati dal glossario.

Al massimo una proposta, con il motivo. Se proponi un cambio, indica il redirect 301 dal vecchio al nuovo URL e cosa aggiornare: link interni, URL canonico, sitemap. Se l'URL va bene, scrivilo in una riga.

## 4. Proponi il piano e aspetta l'approvazione

Mostra in chat, nello stesso messaggio, la diagnosi e il piano:

```markdown
## Diagnosi
**Da conservare:** ...
**Gap AEO:** tabella | Punto della checklist | Esito | Nota |
**Dati:** tabella | Dato | Esito | Fonte | Proposta |
**Query da proteggere:** tabella | Query | Clic | Dove risponderà nella nuova versione |
**Cannibalizzazione:** tabella | Query | Altra pagina | Quota | Intento | Rimedio proposto |, oppure "dati GSC non disponibili: controllo fatto solo sui contenuti"
**URL:** tenere / proposta di cambio, con redirect

## Piano
**Domanda principale:** la domanda AEO a cui il contenuto risponderà, da domande-aeo.md se c'è.
**Interventi:** tabella | # | Intervento | Perché | Priorità (alta, media, bassa) |
**Nuova struttura:** H1, risposta breve iniziale, H2 in forma di domanda, tabelle, FAQ, Schema.org previsto.
**Cosa resta invariato:** messaggi, dati, sezioni, URL.
**Modello:** "nessun modello per questa tipologia: il piano approvato diventerà il modello" oppure "applico il modello <tipologia> versione N", con le eventuali modifiche proposte.

## Domande aperte che pesano su questo contenuto
| Domanda | Cosa cambia | Come procedere se non arriva risposta |

## Decisione richiesta
Ok al piano, scelta sui dati non confermati, ok all'eventuale cambio di URL e al rimedio per ogni cannibalizzazione.
```

**Fermati qui.** Si riscrive solo dopo un'approvazione esplicita. Se il consulente chiede modifiche, aggiorna il piano e richiedi l'ok.

## 5. Il modello di struttura

Il modello fissa le regole di struttura di una tipologia di contenuto per quel cliente, così ogni contenuto dello stesso tipo esce coerente, in questa chat e nelle prossime, anche per i colleghi. Sta nel repo del cliente, in `contenuti/modelli/<tipologia>.md`.

**Prima ristrutturazione di una tipologia.** Dopo l'approvazione del piano, ricava il modello dalle regole di struttura approvate e salvalo con `stato: approvato`. Mostralo in chat in poche righe. Contiene solo regole di forma, non dati del singolo contenuto:

```markdown
---
titolo: "Modello di struttura: <tipologia>"
tipologia: <tipologia>
versione: 1
stato: approvato
derivato_da: [<file del primo contenuto ristrutturato>]
ultimo_aggiornamento: AAAA-MM-GG
---

# Modello di struttura: <tipologia>

## Struttura
Blocchi in ordine, con le regole di ciascuno: H1, risposta breve (lunghezza), sezioni obbligatorie, H2 in forma di domanda, tabelle, chiusura.

## Lunghezza e tono
Parole indicative, persona grammaticale, eccezioni rispetto a tone-of-voice.md.

## FAQ e Schema.org
Numero di FAQ, tipi Schema.org da usare.

## Metadati e URL
Regole per meta title, meta description e slug.

## Varianti
Per ogni formato della tipologia (per esempio intervista, evento, annuncio): cosa cambia rispetto alla struttura comune. Si aggiunge una variante quando arriva il primo contenuto di quel formato.

## Cosa non fare
Errori emersi nelle ristrutturazioni.

## Registro delle modifiche
| Versione | Data | Modifica | Perché |
```

**Ristrutturazioni successive.** Il modello si applica senza ridiscuterlo: il piano si riduce a diagnosi, dati, URL e alle sole differenze rispetto al modello. Se un contenuto non ci sta dentro, per esempio un case study senza risultati numerici o il primo evento in un modello di news nato da un'intervista, proponi una modifica al modello con il motivo, di solito una variante nuova. La applichi, aumentando `versione` e aggiungendo una riga al registro, solo con l'ok del consulente. Se l'ok non arriva, la deviazione vale per quel contenuto e il modello resta com'è.

## 6. Riscrivi

1. **Testo:** segui il piano approvato e il modello. Conserva ciò che il piano tiene; nei dati applica le decisioni prese. Non aggiungere fatti senza fonte nella knowledge base. Le citazioni restano parola per parola. Ogni query da proteggere deve trovare risposta dove indicato nel piano.
2. **Cannibalizzazione:** applica i rimedi approvati. Se il rimedio tocca un'altra pagina (un link da aggiungere, contenuti da unire, un redirect), non modificarla: elencalo nella consegna come azione per il consulente.
3. **Lingua e tono:** come indicano `CLAUDE.md` e `tone-of-voice.md`, con la grafia del glossario. Se il mercato è più ampio di un paese, scrivi in modo che il testo si traduca bene e dichiara le ipotesi dei dati che cambiano per paese.
4. **Metadati:** meta title, meta description, slug (quello attuale, salvo cambio approvato).
5. **Schema.org:** i tipi del piano, seguendo `schema-org.md`. Se la pagina aveva già un JSON-LD, tieni ciò che è corretto. La data di pubblicazione resta quella originale; la data di modifica è quella della nuova versione.

## 7. Controlla e consegna

1. **Checklist:** passa `checklist-aeo.md` e i criteri del modello, e correggi.
2. **Schema:** valida il JSON con `python3 -m json.tool`, poi lancia `python3 ../../condivisi/scripts/verifica_faq_schema.py <file>`.
3. **File:** salva in `contenuti/<tipologia>/AAAA-MM-GG-<slug>.md` con `stato: bozza`, seguendo `archivio-contenuti.md`. Nel frontmatter aggiungi `origine` (URL o file dell'originale), `url` (l'URL di pubblicazione, nuovo solo se il cambio è approvato) e `modello` (file e versione). Sotto il testo pubblicabile, i metadati e lo schema, metti:
   - **Report prima/dopo:** tabella | Punto della checklist | Prima | Dopo |, più i dati aggiornati o tolti, le query protette con il punto in cui rispondono, i rimedi alla cannibalizzazione e la decisione sull'URL;
   - **Analisi e piano approvati**, al posto del brief.
4. **In chat:**
   - un riepilogo di 3-4 righe e il report prima/dopo;
   - i segnaposto `[DATO DA FORNIRE]`;
   - se l'URL cambia, il redirect da impostare e i link da aggiornare;
   - le azioni sulle altre pagine per i rimedi alla cannibalizzazione;
   - se ci sono dati GSC, il suggerimento di confrontare i clic delle query protette 4-6 settimane dopo la pubblicazione, con la successiva estrazione di `ie-aeo-search-console`;
   - le nuove domande per il cliente e le nuove incoerenze, da aggiungere ai file solo con l'ok del consulente.

## 8. Dopo l'approvazione del testo

Segui `archivio-contenuti.md`: `stato: approvato`, domande AEO segnate come coperte, commit e push solo con l'ok del consulente.

Se il consulente lo chiede, la nuova versione si può caricare in HubSpot come bozza del contenuto esistente, mostrando prima cosa cambia. Pubblicazione e redirect restano al consulente.
