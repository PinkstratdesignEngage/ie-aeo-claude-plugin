# Come si prendono i dati di Semrush

Due strade, che si possono mescolare: il connettore per quello che espone, gli export dall'interfaccia per il resto. Tutto finisce in `raw/semrush/<AAAA-MM-GG>/originali/`, con i nomi di file che `normalizza_semrush.py` riconosce.

| File | Report di Semrush | Una riga è |
|---|---|---|
| `posizioni-<db>.csv` o `.json` | Organic Research > Positions, database `<db>` (it, es, de, fr, uk...) | una keyword per cui il dominio è posizionato |
| `competitor-<db>.csv` o `.json` | Organic Research > Competitors | un dominio concorrente |
| `gap-<db>.csv` o `.json` | Keyword Gap: dominio del cliente contro i competitor | una keyword, con una colonna di posizione per ogni dominio |
| `site-audit-problemi.csv` o `.json` | Site Audit, problemi con le pagine coinvolte | una coppia pagina-problema, con la gravità |

## Il piano SEO + AI Search

Il Position Tracking non si usa: l'agenzia non lo ha attivo sui progetti.

| Fascia | Cosa cambia per questa skill |
|---|---|
| SEO | Site Audit nel progetto; il connettore non è indicato tra le funzioni: i dati arrivano dagli export |
| Starter, Pro+ | Accesso al connettore, con almeno 50.000 crediti API al mese, che si azzerano a ogni ciclo di fatturazione |
| Advanced | Integrazione API avanzata; i crediti si comprano a pacchetti |

Fonti: la pagina prezzi di Semrush (semrush.com/pricing/seo-ai-search) e la pagina del connettore (semrush.com/mcp), consultate il 2026-10-26. Il monitoraggio dei prompt AI di Semrush non si usa: i prompt li segue HubSpot AEO.

## Strada 1: connettore

Strumenti verificati il 2026-10-27 sul connettore collegato all'account dell'agenzia. Ogni strumento di area restituisce l'elenco dei report; `get_report_schema` ne dà i parametri; `execute_report` li esegue. Le prime due chiamate non sono report e non estraggono dati; ogni `execute_report` consuma crediti in base alle righe.

| Serve per | Strumento → report | Parametri chiave | File in `originali/` |
|---|---|---|---|
| Progetti del cliente (id per il Site Audit) | `projects` → `list_projects` | `filter: all` | `progetti.json` (solo consultazione) |
| Posizioni | `organic_research` → `resource_organic` | `target` dominio, `database`, `display_limit`, `display_sort: traffic_desc`, `export_columns`: keyword, position, previous_position, volume, keyword_difficulty, intent, url, traffic_share, triggered_serp_features | `posizioni-<db>.json` |
| Competitor | `competitors_research` → `domain_organic_organic` | `domain`, `database`, `display_limit` 10 | `competitor-<db>.json` |
| Keyword gap | `competitors_research` → `domain_domains` | `domains`: prima il cliente, poi fino a 4 competitor, con `type: organic` e i segni che definiscono il gap; `display_filter` per tenere le keyword dove il cliente non è nei primi 20 | `gap-<db>.json`, poi `--gap-domini` con i competitor nello stesso ordine |
| Site Audit | `site_audit` → `snapshots` (id progetto), `meta_issues` (problemi e id), `issue_details` (pagine per problema, con `snapshot_id` e `issueid`) | per i problemi di tipo errore e avviso, le pagine coinvolte | `site-audit-problemi.json`, una riga `{url, issue, type}` per ogni pagina e problema |

Note sui dati del connettore:
- **AI Overview:** nei report di analisi, come `resource_organic`, gli elementi della SERP sono numeri, e l'AI Overview è il **52**, secondo la tabella "SERP Features" della documentazione dell'API (developer.semrush.com/api/v3/seo/overview). Nei report dei progetti è il codice `aio`. Il default di `--codici-aio` è `52,aio`.
- **Intento:** 0 commerciale, 1 informativo, 2 navigazionale, 3 transazionale, dalla stessa documentazione.
- **Keyword gap:** le posizioni arrivano come `position_domain_1…5` nell'ordine dei domini passati. Per questo `normalizza_semrush.py` vuole i competitor in `--gap-domini`, nello stesso ordine.
- **Site Audit:** funziona solo se il cliente ha un progetto Semrush con il Site Audit attivo e almeno una scansione. Senza progetto, export o niente. Costi osservati: `snapshots`, `info` e `meta_issues` 100 crediti ciascuno; `issue_details` 0 crediti.
- **Position Tracking:** l'agenzia non lo usa. Lo strumento esiste nel connettore, ma la skill non lo chiama: le posizioni arrivano da `resource_organic`.
- **Costo osservato:** `list_projects` ha consumato 100 crediti il 2026-10-27; la risposta riporta i crediti usati in `metadata.usage.api_units`. L'elenco dei progetti contiene anche gli altri clienti dell'agenzia: nel repo del cliente salva solo l'id del suo progetto, in `config.json` (`progetto_id`), non l'elenco.
- **Paginazione:** `display_limit` è la riga finale, non il numero di righe. La seconda pagina da 100 è `display_offset: 100, display_limit: 200`; `display_offset` maggiore o uguale a `display_limit` dà errore 605.
- **Costi reali** di una prima estrazione su un sito medio:

  | Chiamata | Righe | Crediti |
  |---|---|---|
  | `resource_organic` it per traffico, due pagine | 100 + 100 | 1.000 + 1.000 |
  | `resource_organic` it con `display_filter` su posizione e volume | 100 | 5.000 |
  | `resource_organic` es | 100 | 1.970 |
  | `resource_organic` de | 30 | 3.970 |
  | `resource_organic` fr | 100 | 5.000 |
  | `resource_organic` uk | 67 | 1.970 |

  Il costo per riga non è fisso: 10 crediti nei casi più semplici, fino a 50 con i filtri e in alcuni database. Per questo si chiama **un report alla volta** e, dopo ognuno, si confronta `metadata.usage.api_units` con la stima. Se il costo per riga è più alto del previsto, ci si ferma e si chiede al consulente prima di proseguire, anche dentro un piano già approvato. Niente chiamate in parallelo.
- **Rumore:** le keyword per traffico contengono ricerche estranee quando i nomi dei prodotti coincidono con luoghi o persone. Per una seconda pagina rende di più un filtro mirato (posizione 4-20, volume minimo) che altre righe per traffico, ma costa di più per riga.
- **Saldo dei crediti:** il connettore non ha uno strumento che lo legge. Si controlla nel proprio account Semrush, alla voce API units.

Prima di qualunque `execute_report` mostra al consulente report, database, righe e stima dei crediti, e aspetta l'ok. Il tetto è `max_crediti` di `analisi/semrush/config.json`. Le fonti pubbliche indicano circa 10 crediti per riga di keyword organiche. Valori di partenza per 5 database:

| Report | Righe | Crediti stimati |
|---|---|---|
| Posizioni | 500 per database | circa 25.000 |
| Competitor | 10 per database | pochi |
| Gap | 300 per database | da verificare alla prima chiamata |
| Site Audit | errori e avvisi | da verificare alla prima chiamata |

**Salvataggio.** Le risposte arrivano nella conversazione, non su disco, e non vanno ricopiate a mano. Dopo le chiamate lancia dalla radice del repo:

```bash
python3 -I <percorso della skill>/scripts/salva_risposte.py raw/semrush/<data> --dal <AAAA-MM-GG>
```

Lo script legge le risposte dal registro della sessione di Claude Code e scrive in `originali/`:
- `risposte.jsonl`, una riga per chiamata con parametri, metadati e risposta;
- i CSV `posizioni-<db>.csv`, `competitor-<db>.csv` e `gap-<db>.csv`, con le pagine unite;
- `crediti.json`, il dettaglio dei crediti usati.

Il Site Audit, che arriva in più risposte (`meta_issues` più una `issue_details` per problema), si ricompone in `site-audit-problemi.json` dalle righe di `risposte.jsonl`.

## Strada 2: export dall'interfaccia

Per ciò che il connettore non dà, o con la fascia SEO, chiedi al consulente gli export. Indica il percorso e il nome da dare al file:

1. **Posizioni:** Organic Research > inserisci il dominio > scegli il database > Positions > Export > CSV. Salva come `posizioni-<db>.csv`. Lascia le colonne predefinite, che comprendono "SERP Features by Keyword" e "Keyword Intents".
2. **Competitor:** Organic Research > Competitors > Export. Salva come `competitor-<db>.csv`.
3. **Gap:** Keyword Gap > dominio del cliente come primo dominio, poi i competitor > Missing o Weak > Export. Salva come `gap-<db>.csv`.
4. **Site Audit:** Projects > progetto del cliente > Site Audit > Issues > esporta i problemi con le pagine coinvolte. Salva come `site-audit-problemi.csv`. Servono, una riga per coppia, l'URL della pagina, il nome del problema e il tipo (errore, avviso, nota). Se l'export ha un'altra forma, lo script si ferma ed elenca le colonne: adatta lì la mappa dei nomi.

Gli export sono limitati a 1.000 righe e a 10 per utente al giorno, secondo fonti di terze parti.

## Note sui dati

- **AI Overview negli export:** lo script segna `aio: sì` anche quando gli elementi della SERP contengono il testo "AI Overview" o "AI Mode".
- **Volumi:** sono stime di Semrush per database, non ricerche misurate. Search Console misura le impressioni reali del sito: quando i due numeri divergono, vale Search Console per il sito e Semrush per la domanda di mercato.
- **Site Audit:** esiste solo se il progetto Semrush del cliente è configurato e ha fatto almeno una scansione.
