# Come si prendono i dati di Ahrefs

Tre strade, che si possono mescolare: il **connettore MCP**, da preferire; l'**API v3** con una chiave, quando il connettore non c'è; gli **export** dall'interfaccia per ciò che manca. Tutto finisce in `raw/ahrefs/<AAAA-MM-GG>/originali/`, con i nomi di file che `normalizza_ahrefs.py` riconosce.

| File | Report di Ahrefs | Una riga è |
|---|---|---|
| `posizioni-<paese>.json` o `.csv` | Site Explorer > Organic keywords, dominio del cliente | una keyword per cui il dominio è posizionato |
| `competitor-<paese>.json` o `.csv` | Site Explorer > Organic competitors | un dominio concorrente |
| `keyword-<paese>-<dominio>.json` o `.csv` | Organic keywords di un competitor | una keyword del competitor, per calcolare il gap |
| `top-pages.json` o `.csv` | Site Explorer > Top pages, con le colonne AI | una pagina, con le citazioni per assistente |
| `ai-risposte.json` | Site Explorer > AI responses count | un oggetto: citazioni e pagine per assistente |
| `site-audit-problemi.json` o `.csv` | Site Audit > Issues | un problema, con gravità e occorrenze |
| `site-audit-pagine.json` o `.csv` | Site Audit > pagine di ogni problema | una coppia pagina-problema |
| `progetto.json` | Site Audit > il progetto del cliente | solo la sua riga, non l'elenco |

## La chiave API

L'API v3 vuole una chiave personale, che si crea nel proprio account Ahrefs (Account settings > API keys). Mettila in `~/.config/ie-aeo-ahrefs/chiave.txt`, una riga sola, oppure nella variabile `AHREFS_API_KEY`. **Non entra mai nel repo del cliente**, che è condiviso.

```bash
mkdir -p ~/.config/ie-aeo-ahrefs
chmod 700 ~/.config/ie-aeo-ahrefs
# incolla la chiave nel file, poi:
chmod 600 ~/.config/ie-aeo-ahrefs/chiave.txt
```

L'autenticazione è `Authorization: Bearer <chiave>`, l'indirizzo di base `https://api.ahrefs.com/v3`.

## Le unità

Ahrefs non conta le chiamate ma le unità. Secondo la documentazione, consultata il 2026-10-28:

- ogni richiesta costa **almeno 50 unità**;
- oltre il minimo, il costo è **righe × costo per riga**, e il costo per riga è la somma delle colonne citate in `select`, `where` e `order_by`;
- la gran parte delle colonne costa 1 unità; `volume`, `keyword_difficulty`, `sum_traffic`, `value` e `traffic` ne costano **10 ciascuna**, `all_positions` e `referring_domains` 5;
- ogni piattaforma chiesta a `ai-responses-count` costa **15 unità**;
- `site-audit/page-explorer` ha un costo fisso di 50 unità a richiesta;
- il limite è **60 richieste al minuto**: oltre, l'API risponde 429.

`/v3/subscription-info/limits-and-usage` **è gratuito** e dice quante unità ha consumato la chiave nel mese (`units_usage_api_key`, `units_limit_api_key`, `usage_reset_date`). Per questo `estrai_ahrefs.py` lo chiama prima e dopo ogni estrazione: il costo che scrive in `unita.json` è quello reale, non una stima. Col connettore non serve: ogni risposta porta già `apiUsageCosts`.

**Costi misurati** sul connettore il 2026-10-28, piano Standard, che confermano il listino:

| Chiamata | Colonne chieste | Unità per riga | Righe | Unità |
|---|---|---|---|---|
| `organic-keywords`, 12 colonne con volume e KD | keyword, posizioni, url, volume, KD, serp_features, 5 intenti | **30** | 250 | 7.500 |
| `organic-keywords` di un competitor, 4 colonne | keyword, best_position, volume, serp_features | **13** | 250 | 3.250 |
| `organic-competitors`, 6 colonne | dominio, keyword comuni, share, DR | **6** | 10 | 60 |
| `top-pages`, 7 colonne con sum_traffic | url, keywords, top keyword, traffico | **25** | 100 | 2.500 |
| `ai-responses-count`, 8 piattaforme | — | **120** a risposta | 1 | 120 |
| `limits-and-usage`, `site-audit-projects` | — | **0** | — | 0 |

Una prima estrazione completa di un dominio italiano di medie dimensioni, con un competitor, è costata **13.430 unità**: molto meno del preventivo, perché il dominio aveva meno keyword indicizzate del limite di righe chiesto. Il preventivo resta il tetto da far approvare, non la previsione.

**Prova gratis.** Le chiamate che hanno `ahrefs.com` o `wordcount.com` come `target` **non consumano unità**, ma dichiarano lo stesso il costo per riga che avrebbero avuto. Servono a verificare la forma delle risposte e la stima prima di spendere sul dominio del cliente.

Le unità del mese si azzerano alla data di `usage_reset_date`. Quante ne dia il piano dipende dal contratto: controlla con `estrai_ahrefs.py limiti` prima di pianificare, non fidarti di un numero di listino.

**Ordine di grandezza.** Con 500 righe per paese, 5 paesi e 2 competitor, l'estrazione costa indicativamente:

| Report | Colonne a 10 unità | Costo per riga | Righe | Unità |
|---|---|---|---|---|
| Posizioni del cliente, per paese | `volume`, `keyword_difficulty` | circa 30 | 500 | circa 15.000 |
| Keyword di un competitor, per paese | `volume` | circa 13 | 500 | circa 6.500 |
| Competitor, per paese | nessuna | 6 | 10 | poche decine |
| Top pages con le colonne AI | `sum_traffic` e 7 colonne AI | circa 83 | 100 | circa 8.300 |
| AI responses count | 8 piattaforme a 15 | — | 1 | circa 170 |
| Site Audit: problemi e pagine | — | — | — | 50 per problema |

Cioè circa **150.000 unità** per cinque paesi e due competitor. È tanto: il preventivo dello script serve proprio a far scegliere al consulente quanti paesi, quanti competitor e quante righe tenere. Le leve, in ordine di efficacia: togliere paesi, togliere competitor, abbassare `righe_posizioni` e `righe_gap`, mettere `"ai": false`.

## Strada 1: API v3

Endpoint usati, verificati sulla documentazione il 2026-10-28. Tutti in GET.

| Serve per | Endpoint | Parametri chiave |
|---|---|---|
| Unità della chiave | `/subscription-info/limits-and-usage` | nessuno; è gratuito |
| Progetti Site Audit | `/site-audit/projects` | nessuno; dà l'id da mettere in `progetto_id` |
| Posizioni | `/site-explorer/organic-keywords` | `target`, `country`, `date`, `select`, `limit`, `order_by=volume:desc`, `date_compared` per le posizioni precedenti |
| Competitor | `/site-explorer/organic-competitors` | `target`, `country`, `date`, `select`, `limit` |
| Keyword gap | **non esiste**: si scaricano le keyword di ogni competitor con `organic-keywords` e il confronto lo fa `normalizza_ahrefs.py` | |
| Pagine e citazioni AI | `/site-explorer/top-pages` | `select` con `ai_responses_chatgpt`, `ai_responses_perplexity`, `ai_responses_google_ai_overviews`, `ai_responses_google_ai_mode`, `ai_responses_gemini`, `ai_responses_copilot`, `ai_responses_grok` |
| Citazioni per assistente | `/site-explorer/ai-responses-count` | `select` con `all_platforms` e le piattaforme; ogni oggetto ha `citations` e `pages` |
| Problemi del Site Audit | `/site-audit/issues` | `project_id`; dà `issue_id`, `name`, `category`, `importance` (`Error`, `Warning`, `Notice`), `crawled` |
| Pagine di un problema | `/site-audit/page-explorer` | `project_id`, `issue_id`, `select=url`, `limit` |

Note sui dati:

- **Paesi:** Ahrefs usa i codici ISO 3166-1 a due lettere. Il Regno Unito è `gb`, non `uk` come in Semrush. Un codice sbagliato non dà errore: dà zero righe.
- **AI Overview:** sta in `serp_features`, come valore `ai_overview` (e `ai_overview_sitelink`). Il default di `--codici-aio` è `ai_overview,ai_overview_sitelink,ai_mode`; lo script segna `aio: sì` anche quando il testo contiene "AI Overview" o "AI Mode", così funziona pure sugli export.
- **Intento:** Ahrefs non dà un codice ma cinque booleani, `is_commercial`, `is_informational`, `is_navigational`, `is_transactional`, `is_branded`. Lo script li traduce nelle stesse parole che usa la skill Semrush.
- **Posizione:** `best_position` è la posizione migliore della keyword; `best_position_prev` arriva solo se si passa `date_compared`, che lo script imposta a 30 giorni prima (`--confronto-giorni`).
- **Filtri:** lo script non usa `where`. Le colonne citate in `where` si sommano al costo per riga, e la sintassi dei filtri è diversa da quella di `select`: è più semplice e più economico scaricare per volume decrescente e filtrare dopo, in Python.
- **Citazioni AI:** sono il campione di risposte che Ahrefs osserva, non tutte le risposte che gli assistenti danno. Dicono quali pagine vengono usate come fonte. La visibilità del brand sui prompt che interessano al cliente resta quella di HubSpot AEO.
- **Site Audit:** esiste solo se il cliente ha un progetto Ahrefs con almeno una scansione. `/site-audit/issues` dà i problemi, non le pagine: le pagine costano una chiamata da 50 unità per problema, e lo script ne legge al massimo `--max-problemi` (40 di default), solo errori e avvisi.
- **Elenco dei progetti:** contiene gli altri clienti dell'agenzia. Nel repo del cliente resta solo la riga del suo progetto, in `progetto.json`, e l'id in `config.json`.
- **Paginazione e tetto di righe:** `limit` è il numero di righe, con 1.000 di default. Il **connettore però tronca a 250 righe per risposta**, qualunque `limit` si chieda: verificato il 2026-10-28 chiedendo 600 e 1.000 e ricevendo 250 in entrambi i casi, con il costo calcolato sulle 250 effettive. È il limite che pesa di più sul gap, che vale solo entro le righe scaricate: va scritto nel report. L'API con la chiave non ha questo tetto. `organic-keywords` non documenta `offset`: per avere più righe conviene alzare `limit`, non impaginare.
- **Colonne che dipendono dal piano:** le `ai_responses_*` di `top-pages` sono documentate ma **non esistono sul piano Standard**: l'API risponde 400 e, utilmente, elenca le colonne disponibili. Quando mancano, le citazioni restano solo per assistente, da `ai-responses-count`, e `ai_pagine.csv` resta vuoto. Prima di dare per scontata una colonna, provala con un `target` gratuito.
- **`all_platforms`:** è il totale deduplicato su tutte le piattaforme che Ahrefs osserva, non la somma di quelle chieste. Su esempio.com, 355 citazioni contro 92 sommando le sette piattaforme selezionate. Nel report si dichiarano le due cose separatamente.
- **Risposte troppo grandi:** quando una risposta non entra nel contesto, Claude Code la salva in un file e lascia nel registro solo il percorso. `salva_risposte.py` lo segue e recupera il contenuto: sono le risposte più grandi, cioè le più care, e perderle vorrebbe dire pagarle due volte.

## Strada 2: export dall'interfaccia

Per ciò che l'API non dà, o quando il piano non la comprende, chiedi al consulente gli export. Indica il percorso e il nome da dare al file:

1. **Posizioni:** Site Explorer > inserisci il dominio > scegli il paese > Organic keywords > Export. Salva come `posizioni-<paese>.csv`. Lascia le colonne predefinite, che comprendono SERP features e Intents.
2. **Competitor:** Site Explorer > Organic competitors > Export. Salva come `competitor-<paese>.csv`.
3. **Keyword dei competitor:** lo stesso report Organic keywords, con il dominio del competitor. Salva come `keyword-<paese>-<dominio del competitor>.csv`. Il gap lo calcola lo script.
4. **Top pages:** Site Explorer > Top pages > Export. Salva come `top-pages.csv`. Le colonne delle citazioni AI ci sono solo se il piano le comprende.
5. **Site Audit:** Site Audit > progetto del cliente > All issues > Export. Salva come `site-audit-problemi.csv`. Per le pagine, esporta la vista di ogni problema e uniscile in `site-audit-pagine.csv`: servono, una riga per coppia, l'URL della pagina, il nome del problema e la gravità. Se l'export ha un'altra forma, lo script si ferma ed elenca le colonne: adatta lì la mappa dei nomi, in `SINONIMI`.

Gli export non danno le citazioni per assistente di `ai-responses-count`: con i soli export, la parte AI del report resta fuori.

## Strada 0: il connettore MCP, da preferire

Ahrefs ha un connettore MCP ufficiale (`https://api.ahrefs.com/mcp/mcp`), raggruppato per categorie di strumenti. Quando è collegato è la strada migliore, per tre motivi: non serve creare e custodire una chiave; ogni risposta dichiara il costo reale in `apiUsageCosts`, quindi il confronto con la stima è immediato e non costa una seconda chiamata; e le due letture che servono a pianificare, `subscription-info-limits-and-usage` e `site-audit-projects`, sono gratuite.

Gli strumenti hanno gli stessi nomi degli endpoint, con il prefisso dell'area: `site-explorer-organic-keywords`, `site-explorer-organic-competitors`, `site-explorer-top-pages`, `site-explorer-ai-responses-count`, `site-audit-issues`, `site-audit-page-explorer`, `site-audit-projects`, `subscription-info-limits-and-usage`. I parametri sono quelli dell'API.

Le risposte arrivano nella conversazione, non su disco: si salvano con `salva_risposte.py`, mai ricopiandole a mano. Lo script riconosce gli strumenti dal nome, qualunque sia l'id del server MCP, e recupera anche le risposte che l'harness ha salvato in un file perché troppo grandi.

Due limiti rispetto all'API con la chiave: il **tetto di 250 righe per risposta** e il fatto che le risposte passano comunque dal contesto della conversazione. Per un'estrazione molto grande la chiave resta più comoda.

### Brand Radar

Il connettore espone anche la famiglia `brand-radar-*`: risposte degli assistenti AI, menzioni, share of voice, domini e **pagine citate**, più la gestione dei prompt tracciati (`management-brand-radar-prompts`, anche in creazione e modifica). È il prodotto AEO di Ahrefs, e si sovrappone a ciò per cui oggi usiamo HubSpot AEO.

Questa skill **non lo usa ancora**: i prompt del cliente restano su HubSpot, dove c'è già il registro delle revisioni e la dashboard li legge. Ma è la strada da valutare quando servono le citazioni per pagina e il piano non espone le `ai_responses_*` di `top-pages`, e prima di comprare prompt aggiuntivi su HubSpot. La decisione è del consulente, non della skill.

Fonti: la documentazione dell'API di Ahrefs (docs.ahrefs.com/en/api), le pagine dei singoli endpoint e quella delle categorie del connettore MCP, consultate il 2026-10-28. I costi per riga, il tetto di 250 righe e le colonne mancanti su `top-pages` non vengono dalla documentazione ma dalla prima estrazione reale, fatta lo stesso giorno su esempio.com.
