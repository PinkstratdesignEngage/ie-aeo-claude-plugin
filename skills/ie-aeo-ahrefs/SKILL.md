---
name: ie-aeo-ahrefs
description: Scarica i dati di Ahrefs di un cliente, dall'API v3 o dagli export, e li salva in formato grezzo nel repo della sua knowledge base, poi li incrocia con l'ultima estrazione di Google Search Console. È l'alternativa a ie-aeo-semrush per i clienti senza Semrush: trova keyword vicine alla prima pagina, keyword in calo, gap rispetto ai competitor, ricerche che mostrano un AI Overview e problemi del Site Audit pesati con il traffico delle pagine, e in più conta quante volte gli assistenti AI citano le pagine del sito. Scrive un report con le azioni proposte, che alimenta la dashboard e le skill di contenuto. Usa questa skill quando l'utente chiede di scaricare, aggiornare o analizzare i dati di Ahrefs, il Site Audit, i competitor organici o il keyword gap di un cliente, anche se dice solo "vediamo cosa dice Ahrefs", "aggiorniamo i dati SEO" o "questo cliente non ha Semrush".
---

# Ahrefs: estrazione e analisi

Search Console dice come va il sito sulle ricerche dove compare già. Ahrefs aggiunge:
- la domanda di mercato (volumi per paese);
- la difficoltà e l'intento delle keyword;
- quali ricerche mostrano un AI Overview;
- dove i competitor sono posizionati e il cliente no;
- lo stato tecnico del sito, dal Site Audit;
- quante volte gli assistenti AI citano le pagine del sito.

È l'alternativa a `ie-aeo-semrush`: **si usa uno solo dei due per cliente**, perché la dashboard legge un solo strumento di ricerca per volta. I file che produce hanno gli stessi nomi e le stesse colonne di quelli di Semrush, quindi analisi, report e dashboard sono gli stessi.

Il lavoro si fa nel repo della knowledge base del cliente: i dati grezzi vanno in `raw/ahrefs/`, il report in `analisi/ahrefs/`.

Riferimenti:
- `references/acquisizione.md`: API, chiave, unità, endpoint, export dall'interfaccia;
- `scripts/estrai_ahrefs.py`: preventivo ed estrazione dall'API v3;
- `scripts/salva_risposte.py`: salva su disco le risposte del connettore MCP;
- `scripts/normalizza_ahrefs.py`: porta i dati nelle colonne fisse e calcola il gap;
- `../../condivisi/scripts/analizza_ricerche.py`: incrocia con Search Console e ordina le azioni (lo stesso che usa Semrush);
- `../ie-aeo-search-console/SKILL.md`: l'estrazione di Search Console con cui si incrocia;
- `../../condivisi/lettura-kb.md`: allineamento del repo e regole della knowledge base.

## Cosa cambia rispetto a Semrush

| | Semrush | Ahrefs |
|---|---|---|
| Accesso | connettore MCP, o export | connettore MCP, API v3 con chiave, o export |
| Costo | crediti API | unità API, almeno 50 per chiamata più il costo per riga |
| Conteggio del costo | si legge in `metadata.usage` | il connettore lo dichiara a ogni risposta in `apiUsageCosts` |
| Keyword gap | report dedicato | **non esiste**: lo calcola `normalizza_ahrefs.py` confrontando le keyword scaricate |
| Site Audit | problemi numerati | problemi con un nome (`issue_id` testuale) |
| Citazioni negli assistenti AI | no | sì, per assistente; **per pagina solo su alcuni piani** |
| Monitoraggio dei prompt AI | no | sì, con Brand Radar, che questa skill non usa ancora: i prompt restano su HubSpot AEO |

**Il connettore tronca a 250 righe per risposta**, qualunque `limit` si chieda. È il limite che conta di più: opportunità e gap valgono entro quelle righe, e va detto nel report.

Backlink, referring domain e Domain Rating si prendono da Ahrefs, ma non entrano in questo flusso perché nessuna skill a valle li usa: il Domain Rating dei competitor arriva comunque, gratis, nel report dei competitor. Se servono, vanno aggiunti prima a chi li deve leggere.

## 1. Prepara

1. **Allineamento:** segui "Prima di tutto" di `lettura-kb.md`.
2. **Chiave API:** controlla che ci sia, senza stamparla: `test -s ~/.config/ie-aeo-ahrefs/chiave.txt && echo ok`. Se manca, segui `references/acquisizione.md` e fermati: la chiave la mette il consulente, non Claude.
3. **Configurazione:** leggi `analisi/ahrefs/config.json`. Se non c'è, crealo con il consulente:

   ```json
   {
     "dominio": "esempio.com",
     "paesi": ["it", "es", "de", "fr", "gb"],
     "competitor": ["competitor1.com", "competitor2.com"],
     "brand": ["esempio"],
     "progetto_id": 1234567,
     "termini_settore": ["banc", "frigo", "refrigera"],
     "max_unita": 150000,
     "righe_posizioni": 500,
     "righe_gap": 500,
     "righe_competitor": 10,
     "righe_top_pages": 100,
     "ai": true,
     "frequenza_giorni": 30
   }
   ```

   - `paesi`: codici ISO a due lettere dei mercati del cliente, da `CLAUDE.md` e `01-azienda/mercato-e-competitor.md`. **Il Regno Unito è `gb`, non `uk`**: Ahrefs usa i codici ISO, Semrush no.
   - `competitor`: da `mercato-e-competitor.md`. Se l'elenco è incompleto, aggiungi i domini che Ahrefs trova nel report dei competitor, segnati come da validare, e proponi la domanda al cliente. Ogni competitor in più costa un'estrazione di keyword per paese: tienine due o tre.
   - `brand`: come in `analisi/search-console/config.json`, se c'è.
   - `termini_settore`: radici delle parole del settore del cliente, nelle lingue dei mercati, prese dal glossario e dal catalogo. Servono a scartare le ricerche estranee quando i nomi dei prodotti coincidono con nomi di luoghi o persone.
   - `progetto_id`: l'id del progetto Site Audit del cliente, da `python3 -I <skill>/scripts/estrai_ahrefs.py progetti`. Senza progetto, il Site Audit resta fuori finché il consulente non lo crea in Ahrefs.
   - `ai`: `false` toglie le citazioni negli assistenti AI, che sono la parte più cara dell'estrazione.
4. **Search Console:** controlla l'ultima cartella in `raw/gsc/`. Se manca, o ha più di 30 giorni, proponi di lanciare prima `ie-aeo-search-console`: senza, l'incrocio perde metà del valore. Si può procedere anche senza, dicendolo nel report.
5. **Niente doppioni:** se il repo ha anche `analisi/semrush/config.json`, chiedi al consulente quale dei due strumenti resta. La dashboard ne legge uno solo.

## 2. Raccogli i dati

Due strade, in `references/acquisizione.md`. **Il preventivo viene sempre prima della spesa**, qualunque strada si prenda: si mostra al consulente il piano delle chiamate con le unità stimate, e si aspetta l'ok.

```bash
python3 -I <percorso della skill>/scripts/estrai_ahrefs.py estrai   # preventivo, non scarica nulla
```

**Strada 1: il connettore MCP**, se è collegato (`ToolSearch` con `ahrefs`). È quella da preferire: non serve nessuna chiave, e ogni risposta dichiara il costo reale in `apiUsageCosts`, che si confronta con la stima subito, senza una seconda chiamata.

1. `subscription-info-limits-and-usage`, che è **gratuito**, dice quante unità restano sulla chiave e quando si azzerano. Si fa sempre per primo.
2. `site-audit-projects`, anch'esso senza costo, dà l'id del progetto del cliente e **la data dell'ultima scansione**: se è vecchia, dillo al consulente prima di leggere il Site Audit, perché finirebbero nel piano problemi tecnici non più attuali.
3. Le chiamate di estrazione, **una alla volta**, confrontando `units-cost-total-actual` con la stima. Se una costa molto più del previsto, fermati e chiedi.
4. Alla fine, dalla radice del repo:

   ```bash
   python3 -I <percorso della skill>/scripts/salva_risposte.py raw/ahrefs/<data> --dominio <dominio> \
       --dal <istante della prima chiamata vera> [--sessione <registro .jsonl>]
   ```

   Lo script legge le risposte dal registro della sessione e le scrive in `originali/`, senza ricopiare niente a mano. `--dal` serve a lasciare fuori le chiamate di prova; `--sessione` quando Claude Code gira in una cartella diversa dal repo del cliente.

**Prova gratis prima di spendere.** Le chiamate con `target` `ahrefs.com` o `wordcount.com` non consumano unità: servono a verificare la forma delle risposte, e il costo per riga che il connettore dichiara è comunque quello vero.

**Strada 2: l'API v3 con la chiave**, quando il connettore non c'è. `estrai_ahrefs.py --conferma` scarica diretto su disco, una chiamata alla volta, rileggendo il consumo reale dopo ognuna, e si ferma da solo se supera la stima o `max_unita`.

I file finiscono in `raw/ahrefs/<data di oggi>/originali/`. L'elenco dei progetti Site Audit contiene anche gli altri clienti dell'agenzia: nel repo del cliente resta solo la riga del suo progetto, che gli script salvano da soli.

## 3. Normalizza e analizza

```bash
python3 -I <percorso della skill>/scripts/normalizza_ahrefs.py raw/ahrefs/<data> --dominio <dominio>
python3 -I <percorso del plugin>/condivisi/scripts/analizza_ricerche.py raw/ahrefs/<data> --strumento Ahrefs \
    --gsc raw/gsc/<ultima data> --brand "<brand>" --termini "<termini_settore>"
```

Il primo script scrive `posizioni.csv`, `competitor.csv`, `gap.csv`, `site_audit.csv`, `site_audit_riepilogo.json`, `ai_pagine.csv` e `ai_citazioni.csv`. Il secondo aggiunge:
- `opportunita_keyword.csv`;
- `in_calo.csv`;
- `gap_contenuti.csv`;
- `aio.csv`;
- `site_audit_pesato.csv`;
- `ai_visibilita.csv`.

Poi stampa un riepilogo. Gli script trovano e ordinano, non decidono.

**Opportunità.** Partono dalle confermate (`confermata_gsc: sì`): quelle dove anche Search Console vede il sito, con almeno 100 impressioni (`--min-gsc`). Le altre possono essere ricerche dove il sito compare per caso: si guardano solo se il tema è chiaramente del cliente. Per ogni keyword controlla la pagina che si posiziona (`url`) e quella che Search Console vede per la stessa query (`gsc_pagina`):
- **coincidono e l'intento è coerente:** l'azione è migliorare la pagina (`ie-aeo-ristruttura-contenuti`, o `ie-aeo-faq-prodotto` per una pagina prodotto);
- **sono diverse:** controlla la dashboard delle cannibalizzazioni prima di proporre qualunque cosa.

**Gap con i competitor.** Ahrefs non ha un report di keyword gap: lo script lo calcola confrontando le keyword scaricate dei competitor con quelle scaricate del cliente. Vale quindi **solo entro il limite di righe per paese**, che sta in `riepilogo_fonti.json`: una keyword assente dal file del cliente può semplicemente essere oltre il limite. Dillo nel report e, se un tema sembra importante, verifica la singola keyword in Ahrefs prima di proporre un contenuto.

Raggruppa le keyword del gap per tema e collega ogni tema a un pillar di `05-content-pillars/` e alle sue `domande-aeo.md`:
- un tema senza pagina del cliente è un contenuto nuovo (`ie-aeo-blogpost`);
- un tema con una pagina debole è una ristrutturazione.

Le keyword con `aio: sì` sono le più adatte a contenuti in forma di risposta.

**Keyword in calo.** Prima di proporre un intervento escludi stagionalità, cambi di URL e calo di tutto il sito, confrontando con `andamento_giornaliero.csv` di Search Console.

**Site Audit.** L'ordine è per gravità, poi per impressioni delle pagine coinvolte. Un problema con `legato_a_cannibalizzazione: sì` (hreflang, canonical, contenuti duplicati, lingua) conferma o spiega un'azione della dashboard delle cannibalizzazioni: indicalo nel report come seconda fonte di quella azione, non come azione separata.

**Citazioni negli assistenti AI.** `ai_citazioni.csv` dice quante volte, in totale e per assistente, le pagine del sito sono citate nelle risposte; `ai_visibilita.csv` dice quali pagine, con le impressioni di Search Console.

Il dettaglio per pagina arriva dalle colonne `ai_responses_*` di `top-pages`, che **non sono disponibili su tutti i piani**: con il piano Standard l'API risponde 400 ed elenca le colonne che ci sono. In quel caso restano i totali per assistente, `ai_pagine.csv` e `ai_visibilita.csv` restano vuoti, e va detto nel report. Attenzione anche a `all_platforms`: è il totale deduplicato su tutte le piattaforme che Ahrefs osserva, quindi è più alto della somma di quelle chieste, non uguale. Sono due cose diverse da HubSpot AEO, e vanno tenute separate anche nel report:
- **Ahrefs** conta le citazioni sulle risposte che osserva, senza sapere quali domande interessano al cliente: dice **quali pagine gli assistenti usano come fonte**;
- **HubSpot AEO** misura la visibilità del brand sui prompt che il cliente ha scelto di tracciare.

Una pagina molto citata va protetta nelle ristrutturazioni, come quelle citate in HubSpot. Una pagina citata che Search Console non vede quasi è un contenuto che lavora per gli assistenti e non per la ricerca: vale la pena guardarla.

## 4. Scrivi il report

Salva `analisi/ahrefs/AAAA-MM-GG.md`:

```markdown
---
titolo: "Ahrefs: <dominio>, <data>"
stato: bozza
ultimo_aggiornamento: AAAA-MM-GG
fonti: [<codice X dell'estrazione>, <codice G di Search Console>]
estrazione: raw/ahrefs/AAAA-MM-GG/
---

# Ahrefs: <dominio>

## In sintesi
3-5 punti, con le azioni prioritarie collegate alle skill che le realizzano.

## Opportunità sulle keyword
| Keyword | Paese | Posizione | Volume | Intento | AI Overview | Pagina | Azione |

## Gap con i competitor
| Tema | Keyword principali | Volume totale | Competitor | Pillar | Azione: contenuto nuovo / ristrutturazione |

## Keyword in calo
| Keyword | Posizione prima / ora | Volume | Pagina | Causa probabile |

## Site Audit
| Problema | Gravità | Pagine | Impressioni delle pagine | Legato a cannibalizzazioni | Azione |

## Citazioni negli assistenti AI
| Assistente | Citazioni | Pagine citate |
| Pagina | Risposte | Assistenti | Impressioni GSC |

## Limiti dei dati
Fonte dei dati (API o export), unità usate, righe per paese, il limite del gap calcolato,
volumi stimati, pesi delle opportunità, e che le citazioni sono il campione osservato da Ahrefs.
```

Non scrivere giudizi sul cliente o sul suo sito: il report sta nel repo condiviso.

## 5. Registra e consegna

1. **Registro fonti:** aggiungi l'estrazione in `fonti/registro-fonti.md` con il prefisso `X`, per esempio `X01 | Ahrefs esempio.com | raw/ahrefs/2026-11-02/ | paesi it, es, de, fr, gb`. Se la sezione o il prefisso mancano, aggiungili.
2. **Domande per il cliente:** competitor da validare e cambi del sito che spiegano i cali vanno in `domande-aperte.md`, solo con l'ok del consulente.
3. **In chat:**
   - la sintesi;
   - le unità usate e quelle rimaste;
   - cosa è arrivato dall'API e cosa dagli export;
   - le decisioni richieste.
4. **Dashboard:** se il cliente ha `analisi/dashboard/config.json`, proponi di aggiornarla con `ie-aeo-dashboard`, che va lanciata con `--ahrefs raw/ahrefs/<data>` al posto di `--semrush`.
5. **Commit e push** di `raw/ahrefs/<data>/`, del report, del registro fonti e della configurazione solo con l'ok del consulente, dopo `git pull --rebase`. La chiave API non entra mai nel repo.
