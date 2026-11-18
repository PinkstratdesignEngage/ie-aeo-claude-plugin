---
name: ie-aeo-semrush
description: Scarica i dati di Semrush di un cliente, tramite il connettore o dagli export, e li salva in formato grezzo nel repo della sua knowledge base, poi li incrocia con l'ultima estrazione di Google Search Console. Trova keyword vicine alla prima pagina da migliorare, keyword in calo, gap rispetto ai competitor, ricerche che mostrano un AI Overview e problemi del Site Audit pesati con il traffico delle pagine. Scrive un report con le azioni proposte, che alimenta la dashboard e le skill di contenuto. Usa questa skill quando l'utente chiede di scaricare, aggiornare o analizzare i dati di Semrush, il Site Audit, i competitor organici o il keyword gap di un cliente, anche se dice solo "vediamo cosa dice Semrush" o "aggiorniamo i dati SEO".
---

# Semrush: estrazione e analisi

Search Console dice come va il sito sulle ricerche dove compare già. Semrush aggiunge:
- la domanda di mercato (volumi per paese);
- la difficoltà e l'intento delle keyword;
- quali ricerche mostrano un AI Overview;
- dove i competitor sono posizionati e il cliente no;
- lo stato tecnico del sito, dal Site Audit.

Il lavoro si fa nel repo della knowledge base del cliente: i dati grezzi vanno in `raw/semrush/`, il report in `analisi/semrush/`.

Riferimenti:
- `references/acquisizione.md`: connettore o export, crediti, nomi dei file, cosa offre ciascuna fascia del piano;
- `scripts/normalizza_semrush.py`: porta report e export in CSV con colonne fisse;
- `scripts/analizza_semrush.py`: incrocia con Search Console e ordina le azioni;
- `../ie-aeo-search-console/SKILL.md`: l'estrazione di Search Console con cui si incrocia;
- `../../condivisi/lettura-kb.md`: allineamento del repo e regole della knowledge base.

Il monitoraggio dei prompt AI non si fa con Semrush: lo segue HubSpot AEO.

## 1. Prepara

1. **Allineamento:** segui "Prima di tutto" di `lettura-kb.md`.
2. **Configurazione:** leggi `analisi/semrush/config.json`. Se non c'è, crealo con il consulente:

   ```json
   {
     "dominio": "esempio.com",
     "database": ["it", "es", "de", "fr", "uk"],
     "competitor": ["competitor1.com", "competitor2.com"],
     "brand": ["esempio"],
     "progetto_id": 12345678,
     "termini_settore": ["banc", "frigo", "refrigera"],
     "max_crediti": 30000,
     "righe_posizioni": 500,
     "frequenza_giorni": 30
   }
   ```

   - `database`: i paesi dei mercati del cliente, da `CLAUDE.md` e `01-azienda/mercato-e-competitor.md`.
   - `competitor`: da `mercato-e-competitor.md`. Se l'elenco è incompleto, aggiungi i domini che Semrush trova nel report Competitors, segnati come da validare, e proponi la domanda al cliente.
   - `brand`: come in `analisi/search-console/config.json`, se c'è.
   - `termini_settore`: radici delle parole del settore del cliente, nelle lingue dei mercati, prese dal glossario e dal catalogo. Servono a scartare le ricerche estranee quando i nomi dei prodotti coincidono con nomi di luoghi o persone.
   - `progetto_id`: l'id del progetto Semrush del dominio, da `list_projects`, con il Site Audit attivo. Se il progetto non c'è, il Site Audit resta fuori finché il consulente non lo crea in Semrush. Il Position Tracking non si usa.
3. **Search Console:** controlla l'ultima cartella in `raw/gsc/`. Se manca, o ha più di 30 giorni, proponi di lanciare prima `ie-aeo-search-console`: senza, l'incrocio perde metà del valore. Si può procedere anche senza, dicendolo nel report.

## 2. Raccogli i dati

Segui `references/acquisizione.md`:
- **connettore**, se è collegato e la fascia lo permette, con la stima dei crediti approvata dal consulente prima di ogni chiamata;
- **export dall'interfaccia** per il resto.

I file vanno in `raw/semrush/<data di oggi>/originali/`. Le risposte del connettore si salvano con `salva_risposte.py`, mai ricopiandole a mano.

**Una chiamata alla volta.** Dopo ogni `execute_report` confronta i crediti usati (`metadata.usage.api_units`) con la stima. Se il costo per riga supera la stima, fermati e chiedi al consulente prima della chiamata successiva, anche dentro un piano approvato.

## 3. Normalizza e analizza

```bash
python3 -I <percorso della skill>/scripts/normalizza_semrush.py raw/semrush/<data> --dominio <dominio>
python3 -I <percorso della skill>/scripts/analizza_semrush.py raw/semrush/<data> --gsc raw/gsc/<ultima data> --brand "<brand>" --termini "<termini_settore>"
```

Il primo script scrive `posizioni.csv`, `competitor.csv`, `gap.csv` e `site_audit.csv`. Il secondo aggiunge:
- `opportunita_keyword.csv`;
- `in_calo.csv`;
- `gap_contenuti.csv`;
- `aio.csv`;
- `site_audit_pesato.csv`.

Poi stampa un riepilogo. Gli script trovano e ordinano, non decidono.

**Opportunità.** Partono dalle confermate (`confermata_gsc: sì`): quelle dove anche Search Console vede il sito, con almeno 100 impressioni (`--min-gsc`). Le altre possono essere ricerche dove il sito compare per caso: si guardano solo se il tema è chiaramente del cliente. Per ogni keyword controlla la pagina che si posiziona (`url`) e quella che Search Console vede per la stessa query (`gsc_pagina`):
- **coincidono e l'intento è coerente:** l'azione è migliorare la pagina (`ie-aeo-ristruttura-contenuti`, o `ie-aeo-faq-prodotto` per una pagina prodotto);
- **sono diverse:** controlla la dashboard delle cannibalizzazioni prima di proporre qualunque cosa.

**Gap con i competitor.** Raggruppa le keyword per tema e collega ogni tema a un pillar di `05-content-pillars/` e alle sue `domande-aeo.md`:
- un tema senza pagina del cliente è un contenuto nuovo (`ie-aeo-blogpost`);
- un tema con una pagina debole è una ristrutturazione.

Le keyword con `aio: sì` sono le più adatte a contenuti in forma di risposta.

**Keyword in calo.** Prima di proporre un intervento escludi stagionalità, cambi di URL e calo di tutto il sito, confrontando con `andamento_giornaliero.csv` di Search Console.

**Site Audit.** L'ordine è per gravità, poi per impressioni delle pagine coinvolte. Un problema con `legato_a_cannibalizzazione: sì` (`hreflang`, canonical, contenuti duplicati, lingua) conferma o spiega un'azione della dashboard delle cannibalizzazioni: indicalo nel report come seconda fonte di quella azione, non come azione separata.

## 4. Scrivi il report

Salva `analisi/semrush/AAAA-MM-GG.md`:

```markdown
---
titolo: "Semrush: <dominio>, <data>"
stato: bozza
ultimo_aggiornamento: AAAA-MM-GG
fonti: [<codice X dell'estrazione>, <codice G di Search Console>]
estrazione: raw/semrush/AAAA-MM-GG/
---

# Semrush: <dominio>

## In sintesi
3-5 punti, con le azioni prioritarie collegate alle skill che le realizzano.

## Opportunità sulle keyword
| Keyword | Database | Posizione | Volume | Intento | AI Overview | Pagina | Azione |

## Gap con i competitor
| Tema | Keyword principali | Volume totale | Competitor | Pillar | Azione: contenuto nuovo / ristrutturazione |

## Keyword in calo
| Keyword | Posizione prima / ora | Volume | Pagina | Causa probabile |

## Site Audit
| Problema | Gravità | Pagine | Impressioni delle pagine | Legato a cannibalizzazioni | Azione |

## Limiti dei dati
Fonte dei dati (connettore o export), crediti usati, righe per report, volumi stimati, pesi delle opportunità.
```

Non scrivere giudizi sul cliente o sul suo sito: il report sta nel repo condiviso.

## 5. Registra e consegna

1. **Registro fonti:** aggiungi l'estrazione in `fonti/registro-fonti.md` con il prefisso `X`, per esempio `X01 | Semrush esempio.com | raw/semrush/2026-11-02/ | database it, es, de, fr, uk`. Se la sezione o il prefisso mancano, aggiungili.
2. **Domande per il cliente:** competitor da validare e cambi del sito che spiegano i cali vanno in `domande-aperte.md`, solo con l'ok del consulente.
3. **In chat:**
   - la sintesi;
   - i crediti usati;
   - cosa è arrivato dal connettore e cosa dagli export;
   - le decisioni richieste.
4. **Commit e push** di `raw/semrush/<data>/`, del report, del registro fonti e della configurazione solo con l'ok del consulente, dopo `git pull --rebase`.
