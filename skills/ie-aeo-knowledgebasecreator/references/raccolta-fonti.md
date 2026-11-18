# Prompt dei subagent per la raccolta delle fonti

Lancia un subagent `general-purpose` per ogni fonte disponibile, tutti nello stesso messaggio e in background. Sostituisci i segnaposto `<...>` con gli input del passo 1.

Gli estratti devono essere **fedeli**, non riassunti creativi: la sintesi la fai tu al passo 4, con tutte le fonti davanti. Un subagent che interpreta troppo nasconde i conflitti tra fonti.

---

## Download per raw/

Il connettore Drive scarica con `download_file_content`, che restituisce il file in base64:
- **File grandi.** Il risultato viene salvato in un file di `tool-results`: si decodifica con python (`json.load` → `base64.b64decode`).
- **File piccoli.** Il base64 arriva direttamente nella risposta.
- **Limite.** Oltre 10 MB il download fallisce: al posto del file va un segnaposto `.link.md`.
- **File nativi Google.** Si esportano con `exportMimeType` (DOCX per i Docs, PDF per le Slides).

Affida i download a subagent, divisi per gruppi di file (per esempio documenti e cataloghi), e chiedi un registro dei file scaricati per poter riprendere.

## Sito web

```
Stiamo costruendo una knowledge base in <LINGUA> su <CLIENTE>, per un progetto AEO. Raccogli i contenuti del sito <URL_SITO> e salvali come estratti Markdown fedeli: riporta i fatti come li dice il sito, senza sintesi creative.

Come lavorare:
1. **Se `<CARTELLA>/raw/sito/` contiene già delle copie di testo**, il sito è stato scaricato al passo 3 nel perimetro concordato col consulente: lavora su quelle e non rileggere il sito dalla rete. Leggile tutte prima di scrivere; vai in rete solo per una pagina che manca o che risulta vuota, e dillo nel messaggio finale.
   **Se invece `raw/sito/` è vuota**, parti dalla home e dalla navigazione per mappare le sezioni; guarda anche la sitemap (/sitemap.xml). Usa WebFetch (caricalo con ToolSearch "select:WebFetch"); se una pagina è renderizzata in JS e WebFetch non basta, usa `curl -sL` e leggi l'HTML.
2. Copri: azienda (storia, gruppo, numeri, sedi, mission/vision/valori, certificazioni, R&S); tutte le famiglie di prodotto e le tecnologie (la pagina di famiglia più 1-2 prodotti rappresentativi, non l'intero catalogo); servizi; sostenibilità; settori e clienti serviti; case study e referenze; news e press degli ultimi 12 mesi.
3. Il primo pillar di contenuto è "<PILLAR>": raccogli con particolare cura tutto ciò che lo riguarda. Annota ogni claim numerico (percentuali, kWh, anni, quantità) con la pagina esatta. Segnala i claim che si contraddicono tra pagine diverse.
4. Osserva come scrive il cliente (registro, persona grammaticale, lunghezza delle frasi, parole ricorrenti, claim e payoff, formattazione) e annotalo con esempi citati.
5. Se trovi dati solo in PDF, immagini o animazioni, segnalalo: non sono indicizzabili dai motori AI ed è un'informazione utile per il progetto.

Output in `<CARTELLA>/_privato/estratti/sito/`:
- `azienda.md`, `prodotti.md`, `servizi.md`, `sostenibilita.md`, `clienti-settori-referenze.md`, `news.md`, `stile-di-scrittura.md`, più `<pillar>.md` se il pillar non coincide con sostenibilità.
- Ogni fatto ha l'URL tra parentesi. In testa a ogni file: data di estrazione e URL letti. Se una sezione non esiste, scrivilo.

Messaggio finale: (a) file scritti; (b) tabella `URL | titolo pagina | cosa contiene` per il registro fonti; (c) 5-10 righe su fatti chiave, claim incoerenti e lacune.
```

---

## Google Drive

```
Stiamo costruendo una knowledge base in <LINGUA> su <CLIENTE>, per un progetto AEO. Leggi tutti i documenti di una cartella Google Drive e salvane estratti Markdown fedeli.

Strumenti: il connettore Google Drive. Trovalo con ToolSearch "google drive search files read file content". Solo lettura: non modificare, spostare, condividere né cancellare nulla.

1. Elenca la cartella con search_files e query `parentId = '<ID_CARTELLA>'` (pagina con next_page_token). Entra nelle sottocartelle.
2. Leggi ogni file supportato. Se un file non è leggibile (video, zip, immagini senza testo), annota nome, tipo e motivo. Il connettore restituisce testo vuoto per i file molto grandi, oltre circa 100 MB: segnalali, il consulente può esportarli in PDF più leggero. Se lo stesso documento esiste in più lingue o in più copie, leggi la versione nella lingua della KB ed elenca le altre nell'intestazione dell'estratto.
3. Per ogni file scrivi un estratto in `<CARTELLA>/_privato/estratti/drive/` con:
   - in testa titolo, link, tipo e data di modifica;
   - un riassunto di 5-10 righe;
   - i fatti utili riportati fedelmente e organizzati per tema: chi è il cliente, mercati/clienti/ICP, prodotti e servizi, posizionamento, tone of voice e brand, <PILLAR>, dati numerici, competitor, obiettivi del progetto.
4. Il repo finale <SARÀ / NON SARÀ> letto dal cliente. Se un documento contiene valutazioni interne dell'agenzia, offerte o prezzi, giudizi sul cliente, spostali in fondo all'estratto in una sezione "RISERVATO – non per il repo". Fai lo stesso con le risposte nominative di survey interne del cliente: riporta gli insight in forma aggregata, senza i nomi.
5. Per i cataloghi prodotto (spesso decine di PDF), basta un estratto breve per famiglia: nome, tipologia, caratteristiche distintive, claim numerici, classe energetica.
6. Scrivi `_indice.md` con la tabella `file estratto | titolo originale | link | tipo | data | contenuto in una riga | leggibile sì/no`.

Messaggio finale: (a) la tabella dell'indice; (b) 5-10 righe sui fatti chiave e su cosa manca; (c) gli eventuali esempi di contenuti esistenti trovati (articoli, post, brochure, linee guida di brand o ToV).
```

---

## Transcript delle riunioni

Se il consulente ha incollato il testo o passato file, salta il connettore e salva il transcript così com'è in `_privato/estratti/meeting/`. Poi fai produrre al subagent solo l'estratto strutturato.

```
Stiamo costruendo una knowledge base in <LINGUA> su <CLIENTE>, per un progetto AEO. Recupera il transcript della riunione "<TITOLO_RIUNIONE>" del <DATA> e ricavane un estratto strutturato.

Strumenti: il connettore delle riunioni (Bluedot o simile). Trovalo con ToolSearch "search meetings get meeting transcript". Solo lettura. Se la riunione non si trova (prova anche solo con il nome del cliente e un intervallo di date), fermati e riporta cosa hai trovato: non inventare contenuti.

Produci in `<CARTELLA>/_privato/estratti/meeting/`:
1. `<slug-riunione>-transcript.md`: transcript integrale, con titolo, data, durata e partecipanti.
2. `<slug-riunione>-estratto.md`: citazioni brevi con speaker e timestamp, in queste sezioni:
   - Chi è il cliente
   - Posizionamento e differenzianti
   - Clienti e ICP: segmenti, chi decide, chi influenza
   - Offerta: cosa spingere e cosa no
   - Tono di voce e brand: parole da usare ed evitare
   - <PILLAR>
   - Competitor
   - Obiettivi del progetto
   - Decisioni e punti aperti

Il riconoscimento vocale storpia i nomi propri. Lascia la parola trascritta e scrivi la tua interpretazione tra parentesi quadre, es. "Hepta" [= EPTA?]. Segnala quando l'attribuzione degli speaker sembra sbagliata. I numeri detti a voce sono `[DA VALIDARE]`.

Il repo finale <SARÀ / NON SARÀ> letto dal cliente. In fondo all'estratto crea una sezione "RISERVATO – non per il repo" con:
- valutazioni interne dell'agenzia e opportunità commerciali;
- giudizi su persone;
- commenti off-record;
- nomi di clienti del cliente;
- dettagli contrattuali;
- debolezze ammesse in confidenza.

Messaggio finale: (a) titolo, data, durata e partecipanti; (b) 10-15 righe di punti chiave condivisibili; (c) 3-5 righe sui temi riservati, senza riportare giudizi su persone; (d) decisioni e punti aperti.
```

---

## Documenti locali

```
Stiamo costruendo una knowledge base in <LINGUA> su <CLIENTE>, per un progetto AEO. Leggi questi documenti locali e salvane estratti Markdown fedeli: <ELENCO_PERCORSI>.

Leggi i PDF con Read (parametro pages, a blocchi di 20 pagine), i DOCX, i PPTX e gli XLSX con gli strumenti disponibili (le skill docx, pptx e xlsx, oppure python3 -I con le librerie installate). Non eseguire file e non aprire macro.

Per ogni documento scrivi un estratto in `<CARTELLA>/_privato/estratti/documenti/`, con la stessa struttura degli estratti Drive: testata, riassunto, fatti per tema, sezione RISERVATO se serve. Scrivi anche `_indice.md`.

Messaggio finale: la tabella dell'indice e 5-10 righe sui fatti chiave e su cosa manca.
```
