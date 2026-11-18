# Le verifiche, le soglie e il perché

Le soglie stanno in cima a `analizza_audit.py`. Qui c'è il motivo di ognuna: serve quando un cliente chiede «perché 800 millisecondi e non mille», e serve a noi per non cambiarle a sentimento.

## Ci vedono?

### Accesso dei crawler

La verifica si fa **con una richiesta per ogni nome di crawler**, non leggendo il `robots.txt`. Il motivo è che sono due cose diverse: il `robots.txt` è una richiesta di cortesia che il crawler può rispettare, il WAF o la CDN sono un muro. Moltissimi siti oggi rispondono 403 a GPTBot o ClaudeBot con un `robots.txt` perfettamente permissivo, perché il blocco è stato acceso con un interruttore nel pannello di Cloudflare e nessuno se lo ricorda. Un audit che legge solo il `robots.txt` dà tutto verde su un sito chiuso.

**Il limite, che va dichiarato al cliente.** I controlli sui bot verificati non si fidano del nome: verificano l'indirizzo di rete o il DNS inverso. Una richiesta che si presenta come Googlebot da una rete qualunque può quindi essere respinta proprio perché fallisce quella verifica, mentre il Googlebot autentico passa. Quello che misuriamo è **come il sito tratta chi si presenta con quel nome**: è il primo filtro che incontra un assistente, ed è informativo, ma non è la prova che il crawler vero sia bloccato. Per Googlebot il controincrocio è Search Console: con impressioni recenti, Googlebot entra.

I crawler sono raggruppati per **conseguenza**, non per azienda, perché è così che si decide:

| Gruppo | Chi | Cosa comporta bloccarli |
|---|---|---|
| Citazione | OAI-SearchBot, ChatGPT-User, Claude-SearchBot, Claude-User, PerplexityBot, Perplexity-User, Amazonbot | Non si viene citati in quelle risposte. È il gruppo che conta per l'AEO |
| Ricerca | Googlebot, Bingbot, Applebot | Si esce dalla ricerca, e da Google anche dalle AI Overviews |
| Addestramento | GPTBot, ClaudeBot, Google-Extended, Applebot-Extended, Meta-ExternalAgent, CCBot, Bytespider | Non si entra nei dati di addestramento. È una scelta aziendale, non un difetto |

**Google-Extended non governa le AI Overviews.** Governa addestramento e grounding di Gemini. Le AI Overviews e AI Mode pescano dall'indice costruito dal normale Googlebot: l'unico modo di uscirne è uscire da Google. È l'equivoco più diffuso che incontriamo, e va chiarito in call prima che qualcuno dica «ma noi Google-Extended l'avevamo bloccato».

Distinguere **GPTBot** da **OAI-SearchBot** permette una posizione sensata: «non addestrate sui miei contenuti, ma citatemi». Bloccare tutto OpenAI perché si confondono i due è una perdita secca.

### Contenuto leggibile senza JavaScript

I crawler AI principali — GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, PerplexityBot, Bytespider, Meta-ExternalAgent — **scaricano l'HTML e non eseguono JavaScript**. L'eccezione nota è Gemini, che riusa la pipeline di rendering di Googlebot. La fonte principale è l'analisi di traffico di Vercel e MERJ; i vendor non dichiarano capacità di rendering nella propria documentazione, il che è coerente.

La conseguenza è la cosa più importante di tutto l'audit: **un sito in client-side rendering può posizionarsi benissimo su Google ed essere invisibile su ChatGPT.** Google il JavaScript lo esegue, gli assistenti no.

Lo script legge l'HTML grezzo e conta le parole di testo visibile; segnala le pagine sotto le **150 parole**. La soglia è bassa di proposito: vuole prendere le pagine *vuote*, non quelle corte.

Sui segnali di framework va fatta una distinzione che all'inizio avevamo sbagliato. Un contenitore di root vuoto (`<div id="root"></div>`) è una **prova**: senza JavaScript quella pagina non ha corpo. `__NEXT_DATA__`, `window.__NUXT__`, `ng-version` e `data-reactroot` invece dicono soltanto «è fatta con un framework», e compaiono su ogni pagina Next.js o Nuxt resa lato server, che per un crawler va benissimo. Da soli non valgono: contano solo insieme a poco testo. Trattarli come prova avrebbe segnalato come critico mezzo web moderno.

Lo script non può distinguere da solo una pagina vuota per colpa del JavaScript da una pagina povera di contenuto. Quella distinzione la fa il consulente aprendo due o tre pagine nel browser: è il passo 4 della skill, e non va saltato.

### Certificato

Si segnala sotto i **30 giorni** alla scadenza. Non è una soglia tecnica, è operativa: trenta giorni bastano a far passare un rinnovo dentro un processo IT aziendale. Sotto i **7 giorni** diventa critico. Un certificato scaduto non degrada il sito: lo spegne, per le persone e per gli assistenti insieme.

Il **mixed content** è l'unico dei controlli sul certificato che rompe qualcosa oggi: risorse in `http://` dentro una pagina `https://` fanno comparire l'avviso «non sicuro» e spesso vengono bloccate dal browser.

## Ci capiscono?

### Dati strutturati

La percentuale di copertura per sezione è un buon indicatore, con tre avvertenze che cambiano come si misura.

**Presente non vuol dire valido.** Un blocco JSON-LD senza `headline`, `datePublished`, `author` e `image` c'è ma non serve. Lo script conta la copertura e, per gli articoli, quanti hanno tutti i campi: il secondo numero è quello vero.

**Non tutto è una percentuale.** `Organization` e `WebSite` sono **singoletti**: devono esserci, una volta, fatti bene. Lì il 100% di copertura non è un obiettivo. Per l'Organization il controllo che conta è `sameAs`, cioè i collegamenti ai profili ufficiali: è il segnale con cui un assistente capisce *quale* azienda siete fra le omonime. Per un gruppo con più società che si chiamano in modo simile non è un dettaglio.

**Una sezione sotto le 3 pagine non produce indicatore.** Una percentuale su due pagine è rumore.

**FAQPage va misurata sapendo perché.** Google ha tolto i rich result FAQ alla quasi totalità dei siti nel 2023: in ottica SEO non rendono più niente. Per gli assistenti restano preziose, perché trovano domanda e risposta già separate e le riusano quasi testualmente. Senza questa nota nel report, qualcuno le toglie dal sito pensando che siano morte.

**L'autore come `Person` con `url` o `sameAs`**, non come stringa. Gli assistenti attribuiscono il contenuto a chi l'ha scritto, e una firma identificabile pesa nelle risposte che citano le fonti. Soglia: buono sopra l'**80%** degli articoli.

### Titoli

**H1.** Più di un H1 è lecito in HTML5 e Google ha detto più volte che non è un problema: è la verifica di minor valore della lista, e nel punteggio non pesa. Quello che conta davvero è il contrario: **nessun H1** (critico) e **H1 identico al title** (nota, è un'occasione sprecata di dire due cose invece di una).

**H2.** Si guardano solo le pagine sopra le **300 parole**. Sotto, una pagina senza sottotitoli è normale e segnalarla produce solo falsi positivi su ringraziamenti e pagine di servizio. La ragione AEO è che gli assistenti spezzano il testo in blocchi seguendo i titoli: una pagina lunga senza sottotitoli è un blocco unico, e o la citano tutta o niente.

### Immagini

Si contano **solo le immagini senza attributo `alt`**. Un `alt=""` su un'immagine decorativa è corretto e segnalarlo è un falso positivo: è l'errore che fanno quasi tutti gli strumenti automatici. Si segnala a parte l'`alt` che è un nome di file (`IMG_1234.jpg`) e quello oltre i **125 caratteri**. Soglia: buono sopra il **90%** di immagini descritte.

## Trovano tutto all'interno del sito web?

### Sitemap e `lastmod`

La presenza del `lastmod` conta, ma la sua **attendibilità** conta di più. Se oltre il 90% delle pagine riporta la stessa data, il segnale si annulla: succede quando il CMS riscrive la data di tutte le pagine a ogni pubblicazione. In quel caso il `lastmod` vale meno che non averlo, perché insegna al crawler a ignorarlo. Lo script lo rileva guardando la distribuzione delle date.

### Link rotti e soft 404

I 404 non si possono elencare indovinando gli indirizzi: si trovano **seguendo i link interni**. Non basta però confrontarli con le pagine scansionate: un bersaglio rotto quasi mai compare in sitemap, quindi su un sito più grande del tetto di pagine non verrebbe mai scaricato e l'indicatore direbbe zero per costruzione. Per questo i bersagli non raggiunti si controllano a parte, con una richiesta leggera.

Contano come rotti **solo 404 e 410**. Un 403, un 429 o un 5xx vogliono dire che la richiesta è stata respinta o che il server era in difficoltà: attribuirli al sito come link rotti darebbe la colpa alla cosa sbagliata. Vengono contati a parte e dichiarati.

Il numero utile non è «quante pagine danno 404» ma «quanti link interni ci portano», perché è lì che si interrompe il percorso del crawler.

I **soft 404** — status 200 con un contenuto che dice «pagina non trovata» — sono peggio dei 404 veri: il motore li tiene nell'indice e si finisce con pagine vuote fra i risultati.

### `llms.txt`

Convenzione recente, non uno standard: alcuni assistenti la leggono, altri la ignorano. Costa poco e non fa danni, quindi la segnaliamo come opportunità, non come errore. HubSpot la raccomanda fra le sue azioni AEO, quindi sui clienti HubSpot la richiesta arriva comunque.

## Quanto aspettano?

### TTFB

Due numeri diversi, e non vanno mescolati.

**Campo (CrUX).** Il tempo misurato sugli utenti Chrome reali sugli ultimi 28 giorni. Le soglie ufficiali dei Core Web Vitals sono **buono ≤ 800 ms, da migliorare fino a 1.800 ms, scarso oltre**, e sono definite **al 75° percentile**.

Qui c'è un punto aperto che vale la pena conoscere. Il nome del campo nella risposta di PageSpeed (`EXPERIMENTAL_TIME_TO_FIRST_BYTE` dentro `loadingExperience.metrics`) è confermato, ma **quale percentile contenga non lo è**: la documentazione di discovery dell'API v5 dice novantesimo, la CrUX API documenta settantacinquesimo, e fonti di terze parti sostengono che il testo di discovery sia rimasto indietro. Applicare una soglia definita sul settantacinquesimo a un numero che potrebbe essere il novantesimo farebbe sembrare peggiori siti che vanno bene.

Per questo il giudizio lo prendiamo da `category` (FAST, AVERAGE, SLOW), che è il verdetto di Google calcolato da Google sul proprio dato, qualunque percentile usi; le nostre soglie restano solo come ripiego quando la categoria manca, e il report non afferma un percentile che non sappiamo. Se un giorno serve il dato con il percentile dichiarato, la strada è interrogare direttamente la CrUX API invece di PageSpeed.

Esiste solo sui siti con traffico sufficiente: su un sito piccolo manca, e va dichiarato invece di sostituirlo di nascosto col dato di laboratorio, che è un'altra cosa (una singola esecuzione sintetica).

**Crawler.** La stessa attesa misurata da noi, con lo user-agent di un assistente, da un server. Soglia nostra: **≤ 1.200 ms**, più larga di quella di Google perché il confronto non è con l'impazienza di una persona ma col timeout di un crawler.

**Lo scarto fra i due numeri è esso stesso un risultato.** CrUX misura persone su Chrome, con cache calda e CDN all'edge; un crawler arriva a freddo da un datacenter. Un sito può essere verde su PSI e lento per gli assistenti. Nella prima misura che abbiamo fatto su esempio.com la prima richiesta a freddo ha dato 1.928 ms e le successive 289 e 461: la mediana su cinque richieste serve proprio a non farsi ingannare né dal picco né dalla cache.

### Peso dell'HTML

Oltre **1,5 MB** di solo HTML si segnala, perché diversi crawler leggono i primi blocchi di un documento lungo e troncano il resto: il contenuto in fondo a una pagina pesante rischia di non essere letto mai. Non contano immagini e script, che il crawler non scarica comunque.

## Cosa questo audit non fa

Non rifà quello che fanno bene Semrush e Ahrefs: analisi dei backlink, posizionamenti, volumi, Core Web Vitals completi. Con `--solo-aeo` salta anche titoli, immagini e link rotti, che il loro Site Audit copre già, e tiene solo le verifiche che nessuno dei due fa: accesso dei crawler provato sul campo, rendering senza JavaScript, copertura dello schema per sezione, `llms.txt`.

## Fonti

Documentazione di Google sui Core Web Vitals per le soglie TTFB; documentazione di OpenAI, Anthropic e Perplexity per i nomi dei crawler; analisi di traffico Vercel/MERJ e rassegne successive per il comportamento sul JavaScript, consultate il 2026-11-12. Le misure su esempio.com citate sopra vengono dalla prima esecuzione reale, lo stesso giorno.
