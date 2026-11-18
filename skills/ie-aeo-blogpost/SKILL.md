---
name: ie-aeo-blogpost
description: Scrive un articolo di blog in ottica AEO (Answer Engine Optimization) per un cliente, partendo dalla sua knowledge base. Il processo è brief del consulente, content brief da approvare, articolo con FAQ e Schema.org in JSON-LD. Usa questa skill quando l'utente chiede un blog post, un articolo, una news di approfondimento o un contenuto per il blog di un cliente, anche se non nomina l'AEO, per esempio "scriviamo un articolo sulla CO2 per il cliente" o "mi serve un post sul nuovo banco". Per ristrutturare in chiave AEO un articolo già esistente usa invece ie-aeo-ristruttura-contenuti.
---

# Blog post AEO

Scrivi articoli che gli assistenti AI (ChatGPT, Perplexity, Google AI Overview) possano trovare, capire e citare, e che restino utili per chi li legge sul sito. Il lavoro si fa nel repo della knowledge base del cliente.

I riferimenti comuni a tutte le skill di contenuto sono nella cartella `condivisi/` del plugin, due livelli sopra questa skill (`../../condivisi/`):
- `lettura-kb.md`: cosa leggere e le regole sui dati;
- `content-brief.md`: il modello del brief;
- `checklist-aeo.md`: i controlli prima della consegna;
- `schema-org.md`: i modelli JSON-LD;
- `archivio-contenuti.md`: dove salvare e come gestire gli stati;
- `../../condivisi/scripts/verifica_faq_schema.py`: controlla che FAQ e schema coincidano;
- `../../condivisi/scripts/analizza_gsc.py`: con `--tema`, le pagine e le query di Search Console già legate al tema.

## 1. Raccogli il brief del consulente

Ti serve solo il **tema**, cioè la domanda a cui l'articolo deve rispondere: se manca, chiedilo.

Tutto il resto è facoltativo:
- **materiali**: link, documenti, dati nuovi, citazioni;
- **vincoli**: lunghezza, prodotti da citare o evitare, scadenze, evento collegato.

Se i materiali non ci sono, non fermarti: lavora con la knowledge base e indica nel brief cosa ti servirebbe.

La categoria non la chiedi: la proponi tu nel brief. Le categorie del blog sono in `contenuti/categorie-blog.md` del repo. Se il file non esiste, chiedi quali categorie usa il blog del cliente e crealo, con una riga che spiega a cosa serve ciascuna. Le categorie cambiano da cliente a cliente: non assumerne nessuna.

## 2. Leggi la knowledge base

Segui `lettura-kb.md`. Poi:
- se il tema rientra in un pillar, parti dalle sue `domande-aeo.md` e dal `topic-cluster.md`;
- cerca in `contenuti/` articoli già scritti sullo stesso tema, per collegarli e non duplicarli;
- se esiste `contenuti/modelli/blog.md`, il modello di struttura approvato per gli articoli del cliente, segui la sua struttura nel brief e nell'articolo;
- **dati di Search Console:** segui la sezione omonima di `lettura-kb.md`. Lancia `analizza_gsc.py --tema` con le parole chiave del tema e controlla cannibalizzazioni e decisioni nell'ultimo report. Se una pagina esistente prende già le query del tema con lo stesso intento, l'articolo nuovo rischia di farle concorrenza: nel brief proponi di ristrutturarla con `ie-aeo-ristruttura-contenuti`, oppure un angolo diverso con link reciproci.

## 3. Prepara il content brief e aspetta l'approvazione

Usa il modello di `content-brief.md`, con `tipo: blogpost`.
- **Domanda principale:** scegli una domanda reale delle `domande-aeo.md`, oppure scrivine una nuova nello stesso stile e proponi di aggiungerla.
- **Domande aperte:** se una domanda aperta o un'incoerenza tocca un dato che vorresti usare, mettila nella sezione apposita del brief e proponi come procedere.
- **Dati di Search Console:** compila la sezione del brief con le query del tema, le pagine che le ricevono e la proposta (contenuto nuovo, ristrutturazione o angolo diverso). Le query del tema in forma di domanda sono buone candidate per gli H2 e le FAQ.
- **Link interni:** includi le pagine che i dati mostrano già forti sul tema, se hanno un intento diverso: il link chiarisce a Google quale pagina risponde a cosa.

Salva il file in `contenuti/blog/AAAA-MM-GG-<slug>.md` con `stato: brief`. Mostra il brief in chat e **fermati**: si scrive solo dopo un'approvazione esplicita. Se il consulente chiede modifiche, aggiorna il brief e richiedi l'ok.

## 4. Scrivi l'articolo

Nello stesso file, sopra la sezione "Brief", scrivi:
1. **H1** e **risposta breve** iniziale: 2-3 frasi che rispondono alla domanda principale.
2. **Corpo:** sezioni con H2 in forma di domanda.
   - Tabelle per confronti e dati.
   - Esempi concreti dalla knowledge base: case study, prodotti, tecnologie.
   - Link interni al pillar, alle pagine prodotto e agli articoli collegati, con l'URL quando è nel registro fonti.
3. **Lunghezza:** di norma 900-1.500 parole, salvo indicazione diversa. Meglio completo e chiaro che lungo.
4. **Chiusura:** riprende il messaggio chiave e propone un passo successivo, per esempio contatto, approfondimento o pagina prodotto, senza toni promozionali eccessivi.
5. **FAQ:** 3-6 domande con risposta breve, diverse dagli H2.
6. **Metadati:** meta title, meta description, slug, categoria.
7. **Schema.org:** un `@graph` con `BlogPosting`, `FAQPage` e `Organization`, e `Product` in `mentions` se l'articolo parla di prodotti specifici. Segui `schema-org.md`.

Scrivi nella lingua e nel tono indicati da `CLAUDE.md` e `tone-of-voice.md`. La persona grammaticale è quella che `tone-of-voice.md` indica per il blog. Se non la indica, usa quella del sito, di solito il "tu" al lettore con il cliente in terza persona, e dichiarala nel brief. Rispetta glossario e termini vietati. Se il mercato è più ampio di un paese, scrivi in modo che il testo si traduca bene e dichiara le ipotesi dei dati che cambiano per paese.

## 5. Controlla e consegna

1. **Checklist:** passa `checklist-aeo.md` punto per punto e correggi.
2. **Schema:** valida il JSON con `python3 -m json.tool`, poi controlla che le FAQ coincidano con lo schema con `python3 ../../condivisi/scripts/verifica_faq_schema.py <file>`.
3. **Stato:** aggiorna il frontmatter con `stato: bozza`, le domande AEO coperte e le fonti.
4. **In chat:**
   - un riepilogo di 3-4 righe;
   - i segnaposto `[DATO DA FORNIRE]`;
   - le eventuali nuove domande per il cliente, da aggiungere a `domande-aperte.md` con il suo ok;
   - se l'articolo tocca pagine esistenti (link da aggiungere, pagina da differenziare), le azioni su quelle pagine, che restano al consulente.

## 6. Dopo l'approvazione del testo

Segui `archivio-contenuti.md`:
- `stato: approvato`;
- domande AEO segnate come coperte;
- commit e push solo con l'ok del consulente.

Se il consulente lo chiede, la bozza si può caricare in HubSpot come post non pubblicato con lo strumento del blog di HubSpot, mostrando prima cosa verrà creato.
