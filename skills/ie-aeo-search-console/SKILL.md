---
name: ie-aeo-search-console
description: Scarica i dati di Google Search Console di una proprietà di un cliente e li salva in formato grezzo (CSV) nel repo della sua knowledge base, poi li analizza. Trova quali pagine portano traffico organico, quali query portano click a quali pagine, le cannibalizzazioni tra pagine, le pagine in calo da ristrutturare e le query dove serve un contenuto nuovo, e scrive un report con le azioni proposte. Il report e i CSV sono letti dalle skill di contenuto (blog post, FAQ prodotto, ristrutturazione). Usa questa skill quando l'utente chiede di leggere, scaricare, aggiornare o analizzare i dati di Search Console o GSC, di capire quali pagine o query performano, di trovare cannibalizzazioni o contenuti da recuperare, anche se dice solo "aggiorniamo i dati di ricerca" o "vediamo come va il sito su Google". Va rilanciata ogni mese: un hook del plugin lo ricorda all'avvio della sessione.
---

# Search Console: estrazione e analisi

I dati di Search Console dicono cosa funziona già: quali pagine Google mostra, per quali ricerche, con quanti click. Servono a decidere se un tema merita un contenuto nuovo o l'aggiornamento di uno esistente, e a non mettere due pagine dello stesso sito in concorrenza sulla stessa domanda. Il lavoro si fa nel repo della knowledge base del cliente: i dati grezzi vanno in `raw/gsc/`, il report in `analisi/search-console/`.

Riferimenti:
- `references/accesso.md`: credenziali, testo per chiedere l'accesso al cliente, problemi frequenti;
- `scripts/estrai_gsc.py`: scarica i report in CSV;
- `scripts/analizza_estrazione.py`: trova cannibalizzazioni, pagine in calo e opportunità;
- `../../condivisi/lettura-kb.md`: allineamento del repo e regole della knowledge base;
- `../../condivisi/scripts/analizza_gsc.py`: analisi di una singola pagina o di un tema, usata dalle skill di contenuto;
- `../ie-aeo-dashboard/SKILL.md`: la dashboard SEO e AEO del cliente, creata o aggiornata alla fine di ogni estrazione.

## Cosa Search Console non dice

Dillo al consulente la prima volta e scrivilo nel report:
- **Il traffico da AI Overviews e AI Mode di Google non è separato** dal resto della ricerca web.
- **ChatGPT, Perplexity, Copilot e Gemini non ci sono**: quel traffico si legge in Google Analytics 4, come referral.
- **Le query rare sono anonimizzate**: contano nei totali ma non compaiono riga per riga. `metadati.json` riporta la quota di click che non si vede.
- **Ogni richiesta restituisce al massimo circa 50.000 righe per giorno**: sui siti grandi la coda lunga delle coppie query-pagina può mancare.

## 1. Prepara

1. **Allineamento del repo:** segui "Prima di tutto" di `lettura-kb.md`.
2. **Configurazione del cliente:** leggi `analisi/search-console/config.json`. Se non c'è, è la prima estrazione: crealo con il consulente.

   ```json
   {
     "sito": "sc-domain:esempio.com",
     "brand": ["esempio", "nome del prodotto di punta"],
     "frequenza_giorni": 30,
     "tipo": "web"
   }
   ```

   - `sito`: il nome esatto della proprietà, come lo stampa il comando `proprieta`. Se il cliente ha più proprietà (per lingua, paese o marchio), chiedi quale analizzare: una configurazione per repo, le altre si estraggono a mano con `--sito`.
   - `brand`: i nomi del cliente e dei suoi marchi, in minuscolo. Le query di brand si separano dalle altre: lì più pagine sulla stessa query sono normali.
   - `frequenza_giorni`: ogni quanto l'hook del plugin ricorda di rilanciare la skill.
3. **Credenziali e accesso:** lancia dalla radice del repo

   ```bash
   python3 <percorso della skill>/scripts/estrai_gsc.py proprieta
   ```

   Se mancano credenziali o librerie, o la proprietà non compare, segui `references/accesso.md` e fermati: senza accesso non c'è niente da analizzare. Il testo per il cliente è lì, pronto da adattare.

## 2. Estrai

```bash
python3 <percorso della skill>/scripts/estrai_gsc.py estrai --sito "<sito>" --tipo <tipo>
```

Scarica gli ultimi 16 mesi, fino a tre giorni fa, in `raw/gsc/<data di oggi>/`:

| File | Contenuto |
|---|---|
| `andamento_giornaliero.csv` | Click e impressioni per giorno |
| `pagine.csv`, `query.csv` | Totali per pagina e per query |
| `query_pagina.csv` | Coppie query-pagina sul periodo: la base delle analisi |
| `query_pagina_mensile.csv` | Coppie query-pagina mese per mese |
| `pagine_mensile.csv` | Pagine mese per mese, per il confronto anno su anno |
| `pagine_paese.csv` | Pagine per paese |
| `metadati.json` | Sito, periodo, totali, quota di query anonime, righe per file |

Le colonne `pagina` hanno accanto `lingua`, ricavata dalla cartella dell'URL (`/it/`, `/en/`...).

## 3. Analizza

```bash
python3 -I <percorso della skill>/scripts/analizza_estrazione.py raw/gsc/<data> --brand "<brand separati da virgola>"
```

Lo script aggiunge alla cartella `cannibalizzazioni.csv`, `pagine_in_calo.csv` e `opportunita.csv`, e stampa un riepilogo. Le soglie si cambiano con `--quota` (quota minima della pagina concorrente, default 20%), `--min-impressioni` (default 100) e `--min-click-calo` (default 20).

Lo script trova i casi, ma non decide. Per ciascun caso rilevante:

**Cannibalizzazioni.** Apri le due pagine (`curl -sL`, oppure la copia in `raw/sito/` se c'è) e valuta l'intento:
- **query di brand o lingue diverse** (`stessa_lingua: no`): di solito non è cannibalizzazione. Per le lingue diverse controlla solo che gli `hreflang` siano corretti;
- **intento diverso**, per esempio una pagina prodotto e un articolo che spiega la tecnologia: basta un link interno tra le due;
- **stesso intento:** il rimedio più leggero che risolve, nell'ordine **differenziare**, **consolidare** con redirect 301 nella pagina più forte, **canonical** solo per pagine quasi identiche che restano entrambe online.

Il segnale più forte è `cambi_di_pagina` alto: Google alterna le due pagine da un mese all'altro perché non sa quale scegliere.

**Pagine in calo.** Confronto degli ultimi tre mesi completi con gli stessi mesi dell'anno prima. Prima di proporre una ristrutturazione escludi le cause esterne: stagionalità, cambi di URL o del sito (chiedi al consulente), calo di tutto il sito nello stesso periodo (`andamento_giornaliero.csv`). Una pagina in calo con un tema ancora rilevante è candidata per `ie-aeo-ristruttura-contenuti`.

**Opportunità.** Query con molte impressioni e posizione tra 5 e 20. Per ciascuna guarda `pagina_principale`:
- se è una pagina coerente con la query, l'azione è migliorarla (`ie-aeo-ristruttura-contenuti`, o `ie-aeo-faq-prodotto` per una pagina prodotto);
- se è una pagina poco coerente o non c'è, è un tema per un contenuto nuovo (`ie-aeo-blogpost`). Le query in forma di domanda (`domanda: sì`) sono le più adatte all'AEO: controlla se sono già in `domande-aeo.md` di un pillar.

**Collegamento con la knowledge base.** Associa le pagine principali ai pillar di `05-content-pillars/` e ai contenuti di `contenuti/` (cerca l'URL nel frontmatter `url` e `origine`). Se c'è un report precedente in `analisi/search-console/`, confronta: cannibalizzazioni risolte o nuove, pagine che hanno recuperato dopo una ristrutturazione.

## 4. Scrivi il report

Salva `analisi/search-console/AAAA-MM-GG.md`, con la data dell'estrazione:

```markdown
---
titolo: "Search Console: <sito>, <periodo>"
stato: bozza
ultimo_aggiornamento: AAAA-MM-GG
fonti: [<codice G dell'estrazione>]
estrazione: raw/gsc/AAAA-MM-GG/
---

# Search Console: <sito>

## In sintesi
3-5 punti: andamento, pagine più forti, problemi principali, azioni prioritarie.

## Pagine che portano traffico
| Pagina | Click | Impressioni | Posizione | Pillar o contenuto collegato |

## Cannibalizzazioni
| # | Query | Pagine coinvolte | Quote | Cambi di pagina | Intento | Rimedio proposto | Decisione |

## Pagine da ristrutturare
| Pagina | Click ora / anno prima | Causa probabile | Azione |

## Opportunità di contenuto
| Query | Impressioni | Posizione | Pagina attuale | Azione: migliorare <pagina> / nuovo contenuto / domanda AEO |

## Confronto con l'estrazione precedente

## Limiti dei dati
Traffico AI non separato, query anonime (quota), righe massime, ipotesi usate.
```

La colonna **Decisione** del report fotografa lo stato al momento dell'estrazione. Le decisioni si prendono e si aggiornano nella dashboard (passo 6), che le skill di contenuto leggono: un rimedio deciso, per esempio "consolidare in X", vale anche per i contenuti futuri sullo stesso tema.

## 5. Registra e consegna

1. **Registro fonti:** aggiungi l'estrazione in `fonti/registro-fonti.md` con il prefisso `G`, per esempio `G01 | Search Console sc-domain:esempio.com | raw/gsc/2026-10-26/ | 2025-06-24 – 2026-10-23`. Se la sezione o il prefisso mancano, aggiungili.
2. **Dimensioni:** controlla con `du -sh raw/gsc/<data>`. I file oltre 50 MB non vanno nel repo: se succede, proponi di non committare `query_pagina_mensile.csv` e di segnarlo con un `.link.md`, come da convenzioni di `raw/README.md`.
3. **In chat:**
   - la sintesi e le prime azioni, collegate alle skill che le realizzano;
   - le decisioni richieste sulle cannibalizzazioni;
   - le nuove domande per il cliente (cambi di URL, stagionalità), da aggiungere a `domande-aperte.md` solo con il suo ok.
4. **Commit e push** di `raw/gsc/<data>/`, del report, del registro fonti, della configurazione e della dashboard solo con l'ok del consulente, dopo `git pull --rebase`.

Non modificare pagine del sito né contenuti esistenti: le azioni le esegue il consulente o le altre skill, dopo la sua decisione.

## 6. Dashboard

Alla fine di ogni estrazione segui `../ie-aeo-dashboard/SKILL.md`, senza chiedere un nuovo ok per partire:
- se non c'è `analisi/dashboard/config.json` con `dashboard_url`, la skill crea la dashboard;
- se ce l'ha, la aggiorna allo stesso link con i dati nuovi, e le decisioni già prese restano.

Le revisioni dei titoli delle azioni e la pubblicazione seguono gli stop di quella skill.

## Promemoria mensile

L'hook del plugin (`hooks/controlla_aggiornamenti.py`) controlla all'avvio di ogni sessione `analisi/search-console/config.json` e la data dell'ultima cartella in `raw/gsc/`. Se sono passati più di `frequenza_giorni`, Claude propone di rilanciare questa skill. Lo stesso hook controlla Semrush e HubSpot AEO.

Per un'estrazione del tutto automatica si può creare un'attività pianificata dell'app desktop di Claude che lancia la skill nel repo del cliente. Gira solo con il Mac acceso e l'app aperta; con l'account personale il primo consenso va dato a mano, poi il token si rinnova da solo.
