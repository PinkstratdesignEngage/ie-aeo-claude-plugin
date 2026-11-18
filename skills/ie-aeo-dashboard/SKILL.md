---
name: ie-aeo-dashboard
description: Crea o aggiorna la dashboard SEO e AEO di un cliente, come artifact di Claude condivisibile, incrociando le ultime estrazioni di Google Search Console, dello strumento di ricerca del cliente (Semrush o Ahrefs: posizioni e Site Audit) e di HubSpot AEO salvate nel repo della sua knowledge base. Prima controlla che i dati ci siano e siano recenti, e lancia le skill di estrazione che servono; poi costruisce un unico piano di lavoro (cannibalizzazioni, opportunità sulle ricerche, problemi tecnici, AEO) dove il team registra decisione e nota di ogni azione, che le skill di contenuto leggono. Usa questa skill quando l'utente chiede la dashboard SEO/AEO, il piano di lavoro delle ottimizzazioni, la dashboard delle cannibalizzazioni, di aggiornare o condividere la dashboard di un cliente. Parte anche alla fine di ie-aeo-search-console.
---

# Dashboard SEO e AEO

La dashboard trasforma i dati di tre strumenti in un solo elenco di azioni, in ordine di priorità, con la decisione del team su ciascuna. Una sola dashboard per cliente, sempre allo stesso link: ogni mese si ripubblica con i dati nuovi e le decisioni restano.

Riferimenti:
- `scripts/prepara_dashboard.py`: dalle estrazioni prepara `dati.json` e la pagina;
- `assets/dashboard.html`: il modello della pagina, uguale per tutti i clienti;
- `../ie-aeo-search-console/SKILL.md`, `../ie-aeo-semrush/SKILL.md`, `../ie-aeo-ahrefs/SKILL.md`: le estrazioni da cui parte;
- `../../condivisi/lettura-kb.md`: allineamento del repo.

## Come è fatta

| Parte | Dove sta | Chi la scrive |
|---|---|---|
| Configurazione | `analisi/dashboard/config.json`: `cliente`, `dashboard_url`, `fonti`, `frequenza_giorni` | Claude, alla prima pubblicazione |
| Strumento di ricerca | Semrush o Ahrefs, mai tutti e due: la cartella passata allo script | Il consulente, scegliendo la skill di estrazione |
| Pagina | `analisi/dashboard/index.html`, dal modello del plugin | Lo script |
| Dati | `analisi/dashboard/dati.json`, pubblicato accanto alla pagina | Lo script, dalle ultime estrazioni |
| Revisioni | `analisi/dashboard/azioni.json`: `titolo`, `rimedio`, `skill`, `priorita` per id di azione | Claude, con l'ok del consulente |
| Decisioni | Database della dashboard, collezione `decisioni`, un documento per id di azione: `{stato, nota, aggiornato_il, aggiornato_da, estrazione}` | Il team, dalla dashboard |

Stati possibili: `da-decidere` (anche quando il documento non c'è), `approvata`, `in-corso`, `fatta`, `scartata`.

**Sezioni della pagina:**
- **Piano di lavoro:** tutte le azioni, filtrabili per categoria e per stato.
- **Cannibalizzazioni:** i casi, con l'alternanza delle pagine mese per mese.
- **Opportunità:** le ricerche confermate da Search Console.
- **Site Audit:** i problemi tecnici.
- **AEO:** dai dati di HubSpot AEO, e da Ahrefs quando c'è:
  - visibilità, menzioni, citazioni e prompt tracciati;
  - tabella dei prompt;
  - dettaglio per assistente;
  - domini più citati;
  - pagine citate dagli assistenti, con le impressioni di Search Console: quelle del cliente vanno protette nelle ristrutturazioni;
  - raccomandazioni di HubSpot con il loro stato e l'azione del piano in cui sono finite;
  - con GA4, la sezione "Dalle risposte al sito": visite dagli assistenti AI mese per mese, per assistente (accanto alle menzioni di HubSpot) e per pagina di arrivo, con citazioni HubSpot, impressioni di Search Console e l'azione aperta sulla pagina;
  - con Ahrefs, le citazioni negli assistenti AI: quante in totale e per assistente, e quali pagine del sito vengono usate come fonte, con le impressioni di Search Console. Sono una cosa diversa dalla visibilità di HubSpot, che misura i prompt scelti dal cliente: la pagina le tiene separate e anche il report deve farlo.

**Categorie di azione e id:**

| Categoria | Fonte | Una azione per | Id |
|---|---|---|---|
| Cannibalizzazione | Search Console | Gruppo di pagine nella stessa lingua (più di 6 pagine: per pagina principale), oppure tipo di contenuto tra lingue diverse | `sl-…`, `ln-…` |
| Opportunità | Semrush o Ahrefs, confermata da Search Console (almeno 100 impressioni) | Pagina, con le ricerche in posizione 4-20 | `op-…` |
| Tecnico | Site Audit di Semrush o di Ahrefs | Problema | `sa-<id>` con Semrush, `sa-ah-<nome>` con Ahrefs |
| AEO | HubSpot AEO | Raccomandazione di HubSpot che non coincide con un'azione esistente | `hs-<id della raccomandazione>` |

Gli id dipendono dalla pagina o dal problema, non dalla data: restano uguali da un mese all'altro e le decisioni restano attaccate. Le opportunità dipendono dalla pagina e non dallo strumento, quindi sopravvivono a un passaggio da Semrush ad Ahrefs; i problemi tecnici no, perché i due strumenti numerano e nominano i problemi in modo diverso. Se il cliente cambia strumento, dillo al consulente: le decisioni prese sulle azioni `sa-…` restano orfane e il controllo del punto 4 le segnala.

**Collegamenti tra azioni.** Un problema tecnico che spiega una cannibalizzazione (`hreflang`, contenuti duplicati, lingua) e tocca le sue pagine diventa una seconda fonte di quella azione, e le due azioni si collegano. Lo stesso vale per un'opportunità sulle pagine di una cannibalizzazione.

**Raccomandazioni di HubSpot AEO.** Una raccomandazione che coincide con un problema del Site Audit diventa una sua seconda fonte. La tabella `COLLEGAMENTI_HUBSPOT` dello script riconosce i titoli inglesi standard di HubSpot e li lega agli id dei problemi di Semrush; con Ahrefs, che i problemi li chiama per nome, il legame si cerca nel titolo del problema, con `COLLEGAMENTI_HUBSPOT_NOME`:

| Raccomandazione HubSpot | Problema del Site Audit |
|---|---|
| Schema.org Product | dati strutturati, 45 |
| Un solo H1 | 104, 103 |
| Titoli e meta description | 15, 106, 6 |
| Peso delle pagine | 135 |
| `llms.txt` | 137 |

Un'azione confermata anche da HubSpot sale di un livello di priorità, se il consulente non l'ha rivista. Lo stesso vale per un'azione su pagine con visite dagli assistenti AI in GA4 (almeno `--soglia-visite-ai` sessioni nel periodo, default 10): prende GA4 tra le fonti e mostra le visite. Le due conferme insieme valgono un livello solo. Le altre raccomandazioni diventano azioni AEO con la priorità di HubSpot (HIGH alta, MEDIUM media, LOW bassa).

Lo stato della raccomandazione si aggiorna in HubSpot e la dashboard lo mostra in sola lettura, con un link al portale. La decisione del team resta nella dashboard. Quando HubSpot introduce titoli nuovi che coincidono con un problema già nel piano, si aggiunge una riga alla tabella.

**Priorità.** Si calcola dentro ogni categoria, dal traffico in gioco:
- cannibalizzazioni: impressioni contese, aumentate dai cambi di pagina;
- opportunità: volume delle ricerche confermate;
- problemi tecnici: impressioni delle pagine lette.

È alta dal 25% dell'azione più pesante della categoria, media dal 5%. Un errore tecnico senza pagine lette è media, un avviso bassa. Le revisioni in `azioni.json` hanno la precedenza.

## 1. Controlla le fonti

1. Segui "Prima di tutto" di `lettura-kb.md`.
2. **Search Console** (obbligatoria): l'ultima cartella in `raw/gsc/`. Se manca o ha più di `frequenza_giorni`, lancia `ie-aeo-search-console`.
3. **Strumento di ricerca, Semrush o Ahrefs:** guarda quale dei due ha una configurazione, `analisi/semrush/config.json` o `analisi/ahrefs/config.json`, e l'ultima cartella in `raw/semrush/` o `raw/ahrefs/`. Se mancano dati recenti, proponi la skill corrispondente, `ie-aeo-semrush` o `ie-aeo-ahrefs`: tutte e due chiedono l'ok sul costo prima di estrarre. Senza nessuno dei due la dashboard si fa lo stesso, e le schede Opportunità e Site Audit restano in attesa. Se il repo ha le configurazioni di entrambi, chiedi al consulente quale usare: la dashboard ne legge uno solo.
4. **HubSpot AEO:** l'ultima cartella in `raw/hubspot-aeo/`. Se manca o è vecchia, lancia `ie-aeo-hubspot-aeo`: sono solo letture, senza crediti. Senza dati, la scheda AEO resta in attesa.
5. **GA4:** se il cliente ha `analisi/ga4/config.json`, l'ultima cartella in `raw/ga4/`. Se è vecchia, lancia `ie-aeo-ga4`: sono solo letture, senza costi. Se il cliente non ha ancora collegato GA4, la dashboard si fa lo stesso e l'indicatore delle visite AI resta in attesa; proponi il collegamento guidato di `ie-aeo-ga4`.

## 2. Prepara dati e pagina

Dalla radice del repo del cliente:

```bash
python3 -I <percorso della skill>/scripts/prepara_dashboard.py raw/gsc/<data> --cliente "<Nome>" --brand "<brand>" --semrush raw/semrush/<data> --hubspot raw/hubspot-aeo/<data> --ga4 raw/ga4/<data> --azioni analisi/dashboard/azioni.json --frequenza <giorni>
```

Con Ahrefs, `--ahrefs raw/ahrefs/<data>` al posto di `--semrush`: passarli tutti e due è un errore e lo script si ferma. I parametri dello strumento di ricerca, `--hubspot` e `--ga4` si omettono se la fonte manca. Lo script stampa le azioni per categoria e priorità e le prime 15.

## 3. Rivedi le azioni principali

Lo script dà titoli e rimedi generici. Per le azioni nuove ad alta e media priorità:
1. apri le pagine coinvolte e valuta l'intento, come descrive "Analizza" di `ie-aeo-search-console`;
2. riusa le letture dei report del mese (`analisi/search-console/`, `analisi/semrush/`);
3. scrivi in `azioni.json`, per id, un `titolo` che dica l'intervento, un `rimedio` di 2-3 frasi, la `skill` e, se serve, la `priorita` con il motivo nel rimedio.

Le azioni tecniche di Ahrefs (`sa-ah-…`) arrivano con il nome inglese del problema e un rimedio generico: trattale come le altre, e per quelle ad alta e media priorità scrivi titolo e rimedio in italiano.

Le azioni AEO (`hs-…`) arrivano con il titolo inglese di HubSpot: per tutte, non solo per le prioritarie, scrivi titolo e rimedio in italiano, specifici per il cliente. Per esempio, collega una raccomandazione di contenuto a una bozza che c'è già in `contenuti/`, o a una pagina esistente da ristrutturare invece di crearne una nuova. Il titolo originale resta visibile nella dashboard.

Mostra le revisioni al consulente prima di pubblicare e rilancia lo script. Le revisioni restano valide finché l'id non cambia. Non scrivere nel file giudizi sul cliente: è nel repo condiviso.

## 4. Pubblica

**Prima volta** (nessun `dashboard_url`):
- pubblica con il tool Artifact:
  - `file_path`: `analisi/dashboard/index.html`;
  - `files`: `{"dati.json": "analisi/dashboard/dati.json"}`;
  - `capabilities`: `{"db": {}, "user": {}}`;
  - `icon`: `"chart"`;
  - una `description` di una frase;
- salva l'URL in `analisi/dashboard/config.json`.

Non usare il tipo "Dashboard" di Claude: la sua pagina non può salvare dati, e qui le decisioni si scrivono dalla dashboard.

**Le volte successive:**
1. leggi la dashboard con `Artifact` `action: "read"` sull'URL, poi elenca i file pubblicati (`action: "list"`, `scope: "files"`);
2. pubblica con `url` = `dashboard_url`, gli stessi `file_path` e `files`, senza `capabilities` né `icon`.

Le decisioni stanno nel database e sopravvivono alla ripubblicazione.

**Controllo, una volta, dopo la pubblicazione:** `ArtifactData` `list` della collezione `decisioni`, e confronto degli id delle azioni con quelli della versione precedente di `dati.json`, perché nessuna decisione resti orfana. Se un id è sparito e aveva una decisione, dillo al consulente.

## 5. Condivisione e consegna

La dashboard è privata finché il proprietario non la condivide dal menu Condividi.

| Chi | Ruolo | Cosa può fare |
|---|---|---|
| Consulenti dell'organizzazione | Contributor | Cambia decisioni e note |
| Persone del cliente, solo consultazione | Viewer | Vede tutto, non modifica |
| Persone del cliente che decidono | Editor, con invito per email | Cambia decisioni e note |

In chat:
- il link;
- le prime azioni per categoria;
- le fonti in attesa;
- le revisioni fatte.

Commit e push di `analisi/dashboard/` solo con l'ok del consulente.

## Come le altre skill leggono le decisioni

`../../condivisi/lettura-kb.md` dice alle skill di contenuto di leggere:
- `analisi/dashboard/dati.json`, per le azioni e le loro pagine;
- la collezione `decisioni` con `ArtifactData` `list` sull'URL di `analisi/dashboard/config.json`.

Una decisione `approvata` o `in-corso` vale come indicazione per il contenuto. Una `scartata` vuol dire che quella azione non si fa.
