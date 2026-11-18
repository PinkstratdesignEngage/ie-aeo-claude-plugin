---
name: ie-aeo-hubspot-aeo
description: Scarica i dati di HubSpot AEO di un cliente e li salva in formato grezzo nel repo della sua knowledge base, in sola lettura. Legge visibilità e menzioni per prompt e assistente AI, citazioni, share of voice rispetto ai competitor e raccomandazioni, li confronta con il periodo precedente e scrive un breve report. I dati alimentano la dashboard SEO e AEO. Usa questa skill quando l'utente chiede di aggiornare, scaricare o leggere i dati di HubSpot AEO, la visibilità di un cliente su ChatGPT, Gemini, Perplexity o Google AI, le citazioni o le raccomandazioni AEO, anche se dice solo "aggiorniamo i dati AEO". Va rilanciata ogni 30 giorni: un hook del plugin la avvia quando i dati sono più vecchi.
---

# HubSpot AEO: estrazione

HubSpot AEO misura come gli assistenti AI rispondono ai prompt tracciati del cliente: se nominano il brand, quali pagine citano, quanto pesano i competitor. Questa skill salva quei dati nel repo della knowledge base, in `raw/hubspot-aeo/<data>/`, così il confronto tra mesi resta nel repo e la dashboard li può incrociare con Search Console e Semrush.

Riferimenti:
- `scripts/salva_hubspot.py`: salva le risposte del connettore dal registro della sessione, senza trascrizioni;
- `../ie-aeo-dashboard/SKILL.md`: la dashboard che usa questi dati;
- `../ie-aeo-prompt/SKILL.md`: progetta e rivede i prompt tracciati, partendo da questi dati;
- `../../condivisi/lettura-kb.md`: allineamento del repo.

**Solo letture.** La skill usa solo:
- `get_aeo_metrics`;
- `manage_aeo_prompts` con `DETAIL`;
- `manage_aeo_recommendations` con `LIST` e `DETAIL`.

Le letture non consumano crediti HubSpot. Non crea prompt (`CREATE` consuma crediti e i prompt si decidono con il cliente) e non avvia raccomandazioni (`START_ACTION` rimanda comunque a HubSpot).

## 1. Prepara

1. **Allineamento:** segui "Prima di tutto" di `lettura-kb.md`.
2. **Connettore:** carica gli strumenti HubSpot (`ToolSearch` con `aeo`). Se non ci sono, il connettore non è collegato: rimanda alla guida per i consulenti e fermati.
3. **Verifica:** `get_aeo_metrics` con `include: ["BUSINESS_UNITS", "RUN_STATUS", "LIMITS"]`.

   | Risposta | Cosa fare |
   |---|---|
   | "You need access to additional permissions" | L'utente HubSpot collegato non ha i permessi AEO. Fermati e indica a chi chiederli: un Super Admin del portale del cliente |
   | Business unit di un altro portale | Il connettore è legato al portale sbagliato. Fermati: va scollegato e ricollegato scegliendo il portale del cliente |
   | Nessun run o 0 prompt | Non ci sono dati da scaricare. Dillo e fermati |
4. **Configurazione:** `analisi/hubspot-aeo/config.json`. Se non c'è, crealo dopo la prima verifica riuscita, con la business unit letta:

   ```json
   {
     "portale_id": 1234567,
     "business_unit_id": 123,
     "giorni_finestra": 30,
     "frequenza_giorni": 30
   }
   ```

   Il file serve anche all'hook del plugin: finché non esiste, il promemoria per questa fonte non parte. L'id del portale si legge dalla risposta o si chiede al consulente.

## 2. Scarica

Annota l'istante di inizio (`date -u +%Y-%m-%dT%H:%M`), poi fai, nell'ordine:

1. `get_aeo_metrics`, sezioni `SUMMARY`, `ASSISTANT_BREAKDOWN`, `COMPETITORS`, `CITATIONS`, `RUN_STATUS`, `LIMITS`, con `compareToPreviousPeriod: true`, `businessUnitId` della configurazione, `startDate` e `endDate` sugli ultimi `giorni_finestra` giorni.
2. `get_aeo_metrics`, sezione `ICPS_AND_PRODUCTS`: ICP e prodotti del profilo, che `ie-aeo-prompt` usa per proporre e creare i prompt.
3. `get_aeo_metrics`, sezione `PROMPTS` con `maxPrompts: 250`, `promptSortBy: "VISIBILITY_SCORE"`. Se `hasMore` è vero, ripeti con `promptsCursor` uguale al `nextCursor` ricevuto.
4. `manage_aeo_prompts` `DETAIL` per ogni prompt tracciato (`maxRuns: 25`, stessa finestra): dà gli URL citati da ogni risposta, che servono per incrociare le pagine con Search Console. Con molti prompt, parti da quelli con più citazioni.
5. `manage_aeo_recommendations` `LIST` con `limit: 100`, tutti gli stati, finché `hasMore` è vero.

Poi salva le risposte, senza ricopiarle:

```bash
python3 -I <percorso della skill>/scripts/salva_hubspot.py raw/hubspot-aeo/<data di oggi> --dal <istante annotato>
```

Lo script scrive in `raw/hubspot-aeo/<data>/`:
- `metriche.json`;
- `prompt/<id>.json`;
- `raccomandazioni.json`;
- `risposte.jsonl` con tutte le chiamate;
- `indice.json`.

## 3. Scrivi il report

Leggi i file salvati e scrivi `analisi/hubspot-aeo/AAAA-MM-GG.md`:

```markdown
---
titolo: "HubSpot AEO: <cliente>, <periodo>"
stato: bozza
ultimo_aggiornamento: AAAA-MM-GG
fonti: [<codice H dell'estrazione>]
estrazione: raw/hubspot-aeo/AAAA-MM-GG/
---

# HubSpot AEO: <cliente>

## In sintesi
3-5 punti: visibilità e variazione sul periodo precedente, assistenti dove il cliente è più e meno presente, competitor più citati, raccomandazioni nuove.

## Prompt
| Prompt | Fase | Visibilità | Menzioni | Citazioni del cliente |

## Pagine del cliente citate
| URL | Citazioni | Assistenti |

## Competitor
| Competitor | Share of voice | Variazione |

## Raccomandazioni
| Raccomandazione | Priorità | Stato |

## Limiti dei dati
Prompt tracciati (quanti su quanti disponibili), finestra, run mancanti, assistenti coperti.
```

Usa i nomi dei campi come arrivano nelle risposte. Se un dato non c'è, scrivilo in "Limiti dei dati": non stimarlo. Non scrivere giudizi sul cliente: il report sta nel repo condiviso.

## 4. Registra e consegna

1. **Registro fonti:** aggiungi l'estrazione in `fonti/registro-fonti.md` con il prefisso `H`, per esempio `H01 | HubSpot AEO portale 1234567 | raw/hubspot-aeo/2026-11-12/ | 2026-10-13 – 2026-11-12`. Se la sezione o il prefisso mancano, aggiungili.
2. **Riservatezza:** prima del commit controlla che nei file non ci siano dati di altri portali o clienti.
3. **Dashboard:** se il cliente ha `analisi/dashboard/config.json`, proponi di aggiornare la dashboard con `ie-aeo-dashboard`. La dashboard legge `metriche.json`, `prompt/` e `raccomandazioni.json` come li scrive `salva_hubspot.py`: la scheda AEO si riempie e le raccomandazioni entrano nel piano di lavoro.
4. **Prompt:** se i prompt tracciati sono meno dell'obiettivo, o se il cliente ha `analisi/prompt-aeo/config.json` e l'ultima revisione ha più di un mese, proponi `ie-aeo-prompt`. Senza un insieme di prompt pensato, i dati di questa estrazione dicono poco.
5. **In chat:** la sintesi, cosa è cambiato dal mese prima, le raccomandazioni nuove.
6. **Commit e push** di `raw/hubspot-aeo/<data>/`, del report, del registro e della configurazione solo con l'ok del consulente, dopo `git pull --rebase`.

## Aggiornamento ogni 30 giorni

All'avvio di ogni sessione l'hook del plugin controlla `analisi/hubspot-aeo/config.json` e la data dell'ultima cartella in `raw/hubspot-aeo/`. Oltre `frequenza_giorni` chiede a Claude di lanciare questa skill: le letture non consumano crediti e non cambiano nulla in HubSpot. Claude avvisa l'utente prima di partire; il commit resta da approvare.

Per un aggiornamento che parta anche senza aprire una sessione si può creare un'attività pianificata dell'app desktop di Claude. Gira solo con il Mac acceso e l'app aperta, e con un account HubSpot che abbia i permessi AEO.
