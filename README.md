# IE-AEO

Plugin di Claude Code per i progetti AEO (Answer Engine Optimization).

## Skill incluse

| Skill | Cosa fa |
|---|---|
| `ie-aeo-knowledgebasecreator` | Ti guida passo passo nella costruzione della knowledge base di un nuovo cliente: raccoglie sito, Drive, transcript e documenti, scrive azienda, ICP, offerta, tone of voice e primo content pillar, e pubblica tutto in un nuovo progetto privato su GitLab. |
| `ie-aeo-blogpost` | Articolo del blog in ottica AEO: brief del consulente, content brief da approvare, articolo con FAQ e Schema.org. Le categorie del blog le legge dalla knowledge base del cliente. |
| `ie-aeo-faq-prodotto` | FAQ verticali di una pagina prodotto a partire dal suo URL e dalla knowledge base, con i punti mancanti, le domande per il cliente e lo Schema.org Product + FAQPage. |
| `ie-aeo-case-study` | Case study in formato AEO: un progetto reale raccontato come risposta a una domanda, con risultati con fonte e base di confronto, citazione autorizzata, FAQ e Schema.org. Al primo uso costruisce il registro dei casi del cliente (`contenuti/case-study/registro-casi.md`: candidati, dati, permessi) e, dopo il primo caso approvato, il modello di struttura (`contenuti/modelli/case-study.md`). |
| `ie-aeo-ristruttura-contenuti` | Ristruttura in chiave AEO un contenuto esistente (blog post, case study, news, pagine): analisi dei gap AEO, controllo dei dati sulla knowledge base, valutazione dell'URL e, con i dati di Google Search Console, delle query da proteggere e della cannibalizzazione. Propone un piano da approvare, poi riscrive. Il primo piano approvato di una tipologia diventa un modello di struttura salvato nel repo del cliente (`contenuti/modelli/`). |
| `ie-aeo-kb-advisor` | Analizza la knowledge base del cliente e scrive un report con un piano per completarla: prima cosa funziona, con le prove; poi il livello di ogni area (solida, parziale, scoperta) con criteri contati dai file; poi cosa manca, per tipo (materiali, domande, fonti, decisioni, lavori sulla KB, coerenza), pesato con le ricerche di Search Console, le visite AI di GA4 e i contenuti bloccati; infine il piano con chi fa cosa, priorità e tempi. Report in `analisi/kb-advisor/` e pagina condivisibile; domande e materiali entrano nella KB dopo l'ok. Un hook la ripropone ogni mese. |
| `ie-aeo-rispondi-a-domande-aperte` | Guida l'utente a chiudere le domande aperte della knowledge base, una alla volta: le ordina per peso (contenuti bloccati, incoerenze, file interessati), presenta ciascuna con il contesto e lascia rispondere, dare indicazioni, chiedere più informazioni, saltare o fermarsi. Per ogni risposta propone le modifiche ai file con la fonte (un codice `R` per sessione nel registro), toglie i `[DA VALIDARE]`, sposta la domanda tra le risolte; a fine sessione prepara le domande da mandare al cliente e un solo commit. |
| `ie-aeo-search-console` | Scarica i dati di Google Search Console di una proprietà del cliente in `raw/gsc/<data>/` e li analizza: pagine che portano traffico, query per pagina, cannibalizzazioni, pagine in calo e opportunità. Scrive un report in `analisi/search-console/` che le skill di contenuto leggono prima di proporre un contenuto nuovo o una ristrutturazione. Un hook ricorda di rilanciarla ogni 30 giorni. |
| `ie-aeo-hubspot-aeo` | Scarica in sola lettura i dati di HubSpot AEO del cliente (visibilità per prompt e assistente, citazioni, share of voice, raccomandazioni) in `raw/hubspot-aeo/<data>/` e scrive un report in `analisi/hubspot-aeo/`. Si aggiorna da sola ogni 30 giorni tramite l'hook del plugin. |
| `ie-aeo-ga4` | Misura con Google Analytics 4 le visite dagli assistenti AI (ChatGPT, Perplexity, Gemini, Copilot, Claude…), che Search Console non separa e HubSpot AEO non conta: sessioni, quota, andamento, coinvolgimento ed eventi chiave per assistente, pagine di arrivo. Usa le stesse credenziali Google di Search Console; dati in `raw/ga4/<data>/`, report in `analisi/ga4/`, proprietà in `analisi/ga4/config.json` del cliente. |
| `ie-aeo-audit-tecnico` | Audit tecnico AEO del sito del cliente, consegnato come dashboard condivisibile dove ogni indicatore si apre e si spiega da solo a chi non è tecnico. Raggruppa per la domanda a cui risponde: *Mi vedono?* (accesso dei crawler provato con una richiesta vera, contenuto leggibile senza JavaScript, certificato), *Mi capiscono?* (dati strutturati per sezione, autore, titoli, immagini), *Mi trovano tutto?* (sitemap, canonical, link rotti, llms.txt), *Quanto mi aspettano?* (tempo di risposta per utenti e per crawler, peso delle pagine). Vale per qualunque tipo di sito. Le azioni entrano nel piano della dashboard SEO e AEO. |
| `ie-aeo-dashboard` | Crea alla prima estrazione, e aggiorna ogni mese, la dashboard SEO e AEO del cliente come artifact di Claude condivisibile: un unico piano di lavoro con cannibalizzazioni (Search Console), opportunità sulle ricerche (Semrush o Ahrefs, confermate da Search Console), problemi tecnici (Site Audit) e AEO (HubSpot: visibilità, citazioni, raccomandazioni unite alle azioni del Site Audit quando coincidono; con Ahrefs anche le pagine citate dagli assistenti). Con GA4, anche le visite dagli assistenti AI: un indicatore, la sezione "Dalle risposte al sito" e le visite sulle pagine delle azioni. Decisione e nota di ogni azione si salvano nella dashboard e le leggono le skill di contenuto. |
| `ie-aeo-semrush` | Lo strumento di ricerca del cliente, quando ha Semrush. Scarica i dati dal connettore o dagli export in `raw/semrush/<data>/` e li incrocia con Search Console: keyword vicine alla prima pagina, keyword in calo, gap con i competitor, ricerche con AI Overview e problemi del Site Audit pesati con il traffico. Le opportunità confermate da Search Console vengono prima, e un filtro sui termini di settore scarta le ricerche estranee. Scrive un report in `analisi/semrush/`. I prompt AI non si monitorano con Semrush: li segue HubSpot AEO. |
| `ie-aeo-ahrefs` | Lo strumento di ricerca del cliente, quando non ha Semrush. Scarica i dati di Ahrefs dal connettore MCP, dall'API v3 con chiave o dagli export, in `raw/ahrefs/<data>/` e li incrocia con Search Console, con gli stessi file e la stessa analisi di Semrush: keyword vicine alla prima pagina, keyword in calo, gap con i competitor, ricerche con AI Overview e problemi del Site Audit pesati con il traffico. In più conta le citazioni che gli assistenti AI fanno delle pagine del sito, per assistente e per pagina. Mostra il preventivo in unità API e scarica solo dopo l'ok, una chiamata alla volta, confrontando ogni volta il costo reale con la stima. Scrive un report in `analisi/ahrefs/`. |
| `ie-aeo-prompt` | Progetta e rivede ogni mese i prompt tracciati in HubSpot AEO del cliente: allinea ICP e prodotti di HubSpot con la knowledge base, propone i prompt partendo dalle domande AEO dei pillar, dalle query di Search Console e dal piano editoriale, coprendo fasi del percorso d'acquisto e mercati, e dice quali tenere o togliere. Crea i prompt in HubSpot solo dopo l'ok, con anteprima e avviso sui crediti; tiene il registro in `analisi/prompt-aeo/`. Toglierli o modificarli resta un'operazione da fare nel portale. |
| `ie-aeo-indice-raw` | Indice di ricerca sui materiali originali del cliente in `raw/` (cataloghi e schede PDF, Word, PowerPoint, pagine del sito): trova i passaggi per significato e non solo per parola esatta, anche tra lingue diverse, con file e pagina. Lo costruisce un consulente sul suo computer (Docling, bge-m3, LanceDB) e lo carica come pacchetto versionato nel Package Registry del progetto GitLab del cliente; gli altri lo scaricano. Ricerca ibrida (vettoriale + per parola); con l'ambiente leggero, solo per parola. Le skill di contenuto e quelle sulla knowledge base la usano per verificare se un'informazione è già nei materiali. |
| `ie-aeo-knowledgegraph` | La mappa navigabile della knowledge base, come artifact in stile Obsidian. Legge i file Markdown del repo e ne estrae il grafo: chi cita chi, quali prodotti, soluzioni e settori tengono insieme i documenti, da quali fonti vengono. Serve a girare dentro la KB e a vedere com'è messa — documenti isolati, documenti dichiarati vuoti, temi che fanno da perno. Una chat dentro la mappa risponde sulla knowledge base citando i documenti, con l'account claude.ai di chi la usa (nessuna chiave API). Di default il testo dei documenti non entra nel grafo e la chat risponde sulla struttura; con il testo completo risponde anche nel merito, ma chi ha il link legge tutta la knowledge base: lo decide il consulente. |
| `ie-aeo-piano-editoriale` | Prepara il piano del mese: incrocia decisioni della dashboard, raccomandazioni e prompt di HubSpot AEO, opportunità e pagine in calo di Search Console, AI Overview di Semrush, domande AEO non coperte, bozze ferme e piano precedente, chiede all'editor i temi nuovi da inserire a prescindere dai dati e li valuta (coerenza, domanda reale, prove, tracce nei dati, sovrapposizioni, tempestività, rischi), e propone il numero di contenuti fissato per il cliente, con skill, domanda, persona, dati mancanti, priorità motivata e calendario. Il piano sta in `contenuti/piano-editoriale/` e le skill di contenuto ne aggiornano lo stato. |
| `ie-aeo-traduzione` | Traduce e localizza un contenuto approvato, di solito in inglese: terminologia dal glossario del cliente, adattamenti di mercato, domande riscritte come le cercano gli utenti in quella lingua, metadati e Schema.org con il collegamento al master. Uno script confronta master e traduzione (numeri, nomi di prodotto, struttura, link). Lingue, varianti e mercati stanno in `contenuti/traduzioni/config.json` del cliente. |
| `ie-aeo-pubblica-hubspot` | Carica in HubSpot come bozza un contenuto approvato: blog post nuovo, post o pagina esistente da ristrutturare, traduzione come variante di lingua. Converte il file in HTML con metadati e JSON-LD, blocca se ci sono segnaposto, procede solo dopo l'ok, non pubblica mai e lascia l'elenco di ciò che resta da fare nell'editor. Le destinazioni stanno in `contenuti/pubblicazione/config.json` del cliente. |

Le skill di contenuto condividono i riferimenti in `condivisi/`: lettura della knowledge base, modello di content brief, checklist AEO, modelli Schema.org, archivio dei contenuti nel repo del cliente (`contenuti/`) e gli script `verifica_faq_schema.py`, che controlla che FAQ e schema coincidano, e `analizza_gsc.py`, che trova nelle coppie query-pagina di Search Console le query da proteggere e le cannibalizzazioni di una pagina, o le pagine che già ricevono traffico su un tema. Lì sta anche `analizza_ricerche.py`, l'incrocio con Search Console che Semrush e Ahrefs usano entrambi.

## Hook

All'avvio di ogni sessione il plugin controlla, nel repo del cliente, quanti giorni sono passati dall'ultima estrazione di ogni fonte configurata (`analisi/<fonte>/config.json`). Oltre la frequenza configurata, di default 30 giorni:

- **HubSpot AEO e GA4:** Claude lancia `ie-aeo-hubspot-aeo` e `ie-aeo-ga4` dopo averlo detto all'utente. Sono solo letture, senza crediti.
- **Search Console e lo strumento di ricerca:** Claude propone `ie-aeo-search-console` e, secondo la configurazione del cliente, `ie-aeo-semrush` o `ie-aeo-ahrefs`. Semrush consuma crediti e Ahrefs unità API: tutte e due mostrano il preventivo e chiedono l'ok prima di estrarre.

Propone anche, nei repo dei clienti che li hanno configurati:
- **Piano editoriale** (`contenuti/piano-editoriale/config.json`): quando manca il piano del mese, dal `giorno_preparazione` quello del mese successivo.
- **Prompt di HubSpot AEO** (`analisi/prompt-aeo/config.json`): quando l'ultima revisione ha più di `frequenza_giorni`.
- **Analisi della knowledge base** (`analisi/kb-advisor/config.json`): quando l'ultimo report ha più di `frequenza_giorni`.
- **Mappa della knowledge base** (`analisi/knowledge-graph/config.json`): quando un file Markdown della knowledge base è cambiato dopo l'ultimo commit di `grafo.json`, anche solo in locale. Lo chiede anche a fine turno, quando in una sessione Claude modifica la knowledge base: una volta per gruppo di modifiche, non a ogni turno.

- **Indice dei materiali originali** (`fonti/indice-raw/config.json`): lo fa scaricare da GitLab quando manca sul computer, e propone di aggiornarlo quando un file di `raw/` è cambiato dopo il commit dell'indice.

Il commit dei dati resta sempre da approvare.

In arrivo: glossario pubblico.

## Installazione

In Claude Code:

```
/plugin marketplace add https://gitlab.example.com/aeo/claudeplugin/IE-AEO.git
/plugin install ie-aeo@ie-aeo
```

Gli aggiornamenti arrivano da soli, all'avvio di Claude Code, se il marketplace è registrato con `autoUpdate: true`, e se git riesce a leggere il repo privato su GitLab con le credenziali HTTPS salvate. Il repo di ogni cliente lo fa già nel suo `.claude/settings.json`. In alternativa, per aggiornare a mano: `/plugin marketplace update ie-aeo`.

## Pubblicare una nuova versione

1. Modifica skill, script o template.
2. Aumenta `version` in `.claude-plugin/plugin.json` e in `.claude-plugin/marketplace.json`: 0.2.0 → 0.2.1 per correzioni, 0.3.0 per funzioni nuove. Claude Code riconosce una nuova versione da questo numero: senza cambiarlo, gli aggiornamenti automatici non partono.
3. Fai commit e push su GitLab (`origin`, `gitlab.example.com`). Il ramo `main` è protetto: lo aggiornano i Maintainer del progetto; gli altri aprono una merge request con `glab mr create`.
4. Se il plugin è anche nella libreria dell'organizzazione su claude.ai, ripubblicalo da Claude Code chiedendo di aggiornare il plugin nella libreria.

## Uso

Scrivi per esempio "creiamo la knowledge base AEO per un nuovo cliente", oppure invoca `/ie-aeo:ie-aeo-knowledgebasecreator`.

## Cosa serve

- **GitLab CLI** (`glab`) autenticato su `gitlab.example.com` (`glab auth login --hostname gitlab.example.com`), per creare il repo del cliente. I remoti sono in HTTPS.
- **Connettore Google Drive**, se i materiali del cliente sono su Drive.
- **Connettore Bluedot**, se i transcript delle riunioni sono lì. In alternativa basta incollarli o passare i file.
- **Connettore Semrush** (fascia Starter o superiore del piano SEO + AI Search) per `ie-aeo-semrush`; senza, la skill lavora sugli export dall'interfaccia.
- **Connettore Ahrefs**, oppure una **chiave API** in `~/.config/ie-aeo-ahrefs/chiave.txt`, per `ie-aeo-ahrefs`, sui clienti senza Semrush; senza nessuno dei due, la skill lavora sugli export. Non va mai nel repo del cliente: vedi `skills/ie-aeo-ahrefs/references/acquisizione.md`.
- **Ambiente Python della skill `ie-aeo-indice-raw`**, in `~/.cache/ie-aeo-indice/`, preparato da `skills/ie-aeo-indice-raw/scripts/ambiente.py`: completo (circa 4 GB, per costruire l'indice) per uno o due consulenti per cliente, leggero (circa 0,5 GB, ricerca per parola) per gli altri. Per caricare l'indice serve il ruolo Developer sul progetto GitLab del cliente.
- **Credenziali Google Cloud con la Search Console API** e l'accesso del cliente alla sua proprietà, per `ie-aeo-search-console`: vedi `skills/ie-aeo-search-console/references/accesso.md`.
