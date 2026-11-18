---
name: ie-aeo-prompt
description: Progetta e tiene aggiornato l'insieme dei prompt tracciati in HubSpot AEO di un cliente, partendo dalla sua knowledge base (personas, ICP, offerta, domande AEO dei pillar) e dai dati di HubSpot AEO e Search Console salvati nel suo repo. Allinea ICP e prodotti di HubSpot con la knowledge base, propone quali prompt aggiungere, coprendo fasi del percorso d'acquisto, mercati e prodotti prioritari, e ogni mese propone quali tenere, cambiare o togliere. Crea i prompt in HubSpot solo dopo l'ok esplicito del consulente, con anteprima e avviso sui crediti, e tiene un registro dei prompt nel repo del cliente. Usa questa skill quando l'utente chiede di impostare, rivedere, aggiungere o ricalibrare i prompt di HubSpot AEO, di decidere cosa monitorare sugli assistenti AI, o dice solo "sistemiamo i prompt" o "quali domande tracciamo per il cliente".
---

# Prompt di HubSpot AEO

HubSpot AEO misura la visibilità del cliente solo sulle domande che traccia: con pochi prompt, o con prompt scelti male, visibilità e citazioni non dicono nulla. Questa skill decide **cosa misurare**, in modo che i prompt rispecchino le domande reali dei clienti del cliente e il suo piano dei contenuti. Lavora nel repo della knowledge base del cliente: ogni cliente ha il suo profilo, i suoi prompt e il suo registro.

Riferimenti:
- `scripts/stato_prompt.py`: capacità, rendimento dei prompt, copertura e domande AEO non ancora tracciate, dai dati già nel repo;
- `../ie-aeo-hubspot-aeo/SKILL.md`: l'estrazione mensile dei dati, da cui parte la revisione;
- `../ie-aeo-piano-editoriale/SKILL.md`: il piano dei contenuti, che usa i prompt scoperti e propone prompt per misurare i contenuti nuovi;
- `../../condivisi/lettura-kb.md`: allineamento del repo e regole della knowledge base.

## Cosa fa e cosa non fa

| Operazione | Come |
|---|---|
| Leggere dati, ICP, prodotti, risposte | Connettore HubSpot, sola lettura: `get_aeo_metrics`, `manage_aeo_prompts` `DETAIL` e `RESPONSES` |
| Creare prompt | Connettore, `manage_aeo_prompts` `CREATE`: sempre anteprima, ok esplicito del consulente, avviso sui crediti |
| Togliere dal tracciamento, modificare un prompt | Nel portale HubSpot, dal consulente: il connettore non lo permette. La skill dice quali e dà il link |
| Modificare ICP, prodotti, brand, competitor | Nel portale HubSpot, dal consulente. La skill dice cosa cambiare e perché |

I prompt si decidono con il cliente: la skill propone, il consulente approva, e ciò che entra in HubSpot è solo ciò che è stato approvato.

## File nel repo del cliente

| File | Contenuto |
|---|---|
| `analisi/prompt-aeo/config.json` | Regole del cliente per i prompt |
| `analisi/prompt-aeo/registro.md` | Tutti i prompt, proposti, tracciati e tolti, con origine e stato |
| `analisi/prompt-aeo/AAAA-MM-GG.md` | Una revisione per volta: analisi, proposte, decisioni |

`config.json`, da creare alla prima revisione con il consulente:

```json
{
  "obiettivo_prompt": 20,
  "riserva": 5,
  "mercati": [{"lingua": "it", "paese": "IT", "quota": 0.6}, {"lingua": "en", "paese": "GB", "quota": 0.4}],
  "quota_brand": 0.2,
  "giorni_minimi": 60,
  "frequenza_giorni": 30
}
```

- `obiettivo_prompt` e `riserva`: quanti prompt tenere tracciati e quanti posti lasciare liberi per i temi nuovi. Il totale non supera `promptsCapacity` di HubSpot. Se il portale è a crediti, l'obiettivo è un numero concordato con il cliente, perché ogni prompt costa.
- `mercati`: lingue e paesi in cui misurare, con la quota di prompt. Vengono dal mercato prioritario scritto in `CLAUDE.md` del cliente.
- `quota_brand`: la parte di prompt che nomina il cliente (`BRANDED`), di solito nelle fasi di valutazione e decisione. Il resto non lo nomina: misura se l'AI lo propone da sola.
- `giorni_minimi`: prima di questo tempo un prompt non si giudica e non si toglie.

## 1. Prepara

1. **Allineamento:** segui "Prima di tutto" di `lettura-kb.md`.
2. **Dati HubSpot:** l'ultima cartella in `raw/hubspot-aeo/`. Se manca o è più vecchia di `frequenza_giorni` di `analisi/hubspot-aeo/config.json`, lancia prima `ie-aeo-hubspot-aeo` (sono solo letture). Se quella skill si ferma per connettore o permessi, fermati anche tu.
3. **ICP e prodotti di HubSpot:** servono per creare i prompt. Se l'estrazione non contiene la sezione `ICPS_AND_PRODUCTS`, leggila: `get_aeo_metrics` con `include: ["ICPS_AND_PRODUCTS", "LIMITS"]` e il `businessUnitId` della configurazione di HubSpot AEO.
4. **Stato attuale:** dalla radice del repo del cliente

   ```bash
   python3 -I <percorso della skill>/scripts/stato_prompt.py --dominio <dominio del cliente>
   ```

   Lo script legge l'estrazione, il registro e le domande AEO dei pillar, e stampa capacità, rendimento, copertura e domande non ancora tracciate.
5. **Knowledge base:** `02-audience/icp.md` e le personas, `03-offerta/` (prodotti e servizi prioritari), `05-content-pillars/*/domande-aeo.md` e `topic-cluster.md`, `CLAUDE.md` per mercati e lingue. Se ci sono dati di Search Console, l'ultimo `raw/gsc/<data>/opportunita.csv`: le query con `domanda: sì` sono domande reali.

## 2. Allinea il profilo di HubSpot con la knowledge base

Ogni prompt in HubSpot è legato a un ICP e a un prodotto del profilo. Se il profilo è sbagliato, lo sono anche i prompt generati e i filtri dei report. Confronta:

| In HubSpot | Nella knowledge base | Cosa cercare |
|---|---|---|
| ICP | `02-audience/icp.md`, personas | ICP generati in automatico e mai rivisti, doppioni, paesi fuori dal mercato, segmenti che il cliente non serve |
| Prodotti | `03-offerta/` | Doppioni, nomi diversi dal glossario, prodotti prioritari mancanti |
| Brand e competitor | `01-azienda/`, competitor della knowledge base | Varianti del nome, competitor mancanti per lo share of voice |

Le correzioni si fanno nel portale: scrivi l'elenco nella revisione, con il motivo di ciascuna. Se il profilo è molto lontano dalla knowledge base, proponi di sistemarlo **prima** di creare prompt nuovi, e dillo chiaramente: i prompt nascono legati agli ICP e ai prodotti che esistono quel giorno.

## 3. Progetta l'insieme dei prompt

Un buon insieme di prompt è un campione delle domande che i clienti del cliente fanno agli assistenti AI. Regole:

- **Domande reali, non parole chiave.** Una domanda come la scriverebbe una persona, con un solo intento. Fonti, in quest'ordine:
  1. le domande AEO dei pillar, scritte apposta per diventare prompt;
  2. le query in forma di domanda di Search Console;
  3. le domande delle personas;
  4. le domande sui temi del piano editoriale, per misurare i contenuti pubblicati;
  5. le raccomandazioni di HubSpot.
- **Copertura.** Le quattro fasi del percorso d'acquisto (`AWARENESS`, `CONSIDERATION`, `EVALUATION`, `DECISION`), le personas principali, i prodotti e i pillar prioritari, i mercati con le quote di `config.json`. Più prompt dove il cliente vuole crescere, almeno uno per ogni tema prioritario.
- **Brand.** La maggior parte dei prompt non nomina il cliente. Quelli con il nome (`quota_brand`) servono per valutazione e decisione, per esempio i confronti con i competitor.
- **Lingua e paese coerenti.** Un prompt in italiano si misura in Italia, uno in inglese nel paese indicato: niente domande che hanno senso solo in un paese se il mercato è più largo.
- **Niente doppioni.** Due prompt che differiscono per una parola misurano la stessa cosa: tienine uno.
- **Stabilità.** Un nucleo di prompt resta uguale nel tempo, altrimenti non si vede l'andamento. Si cambia la parte restante.

**Due modi di creare i prompt in HubSpot**, come prevede il connettore:

| Modo | Quando | Come funziona |
|---|---|---|
| **Generati da HubSpot** | Per coprire combinazioni di ICP, prodotto e fase senza un testo preciso | Si scelgono ICP, prodotti, fasi e `numberOfPrompts`. HubSpot genera i testi, che si vedono in anteprima. Confermando si tracciano tutti quelli generati: non si possono scegliere uno per uno |
| **Testi approvati** | Per le domande AEO e le domande reali già scritte nella knowledge base | Si inviano i testi esatti. Solo testi che il consulente ha approvato parola per parola: Claude non inventa prompt da inviare. L'anteprima restituisce suggerimenti di qualità da mostrare |

Con i testi approvati la fase non si sceglie: la assegna HubSpot. Registra comunque la fase prevista, e confrontala dopo la creazione.

## 4. Proponi e aspetta l'approvazione

Scrivi la revisione in `analisi/prompt-aeo/AAAA-MM-GG.md` e mostrala in chat:

```markdown
---
titolo: "Prompt HubSpot AEO: <cliente>, revisione del <data>"
stato: proposta
ultimo_aggiornamento: AAAA-MM-GG
fonti: [<codici H e G usati>]
---

# Prompt HubSpot AEO: revisione del <data>

## In sintesi
Prompt tracciati su capacità, copertura per fase e mercato, cosa si propone.

## Profilo di HubSpot
| Elemento | Problema | Correzione da fare nel portale |

## Prompt da tenere
| ID | Prompt | Perché |

## Prompt da togliere nel portale
| ID | Prompt | Perché | Sostituito da |

## Prompt da aggiungere
| # | Prompt | Lingua e paese | Fase prevista | ICP | Prodotto | Origine | Modo |

## Copertura dopo le modifiche
Per fase, mercato, persona e tema prioritario.

## Decisione richiesta
Ok ai testi, ok alle combinazioni da far generare, correzioni del profilo, posti lasciati in riserva.
```

Per ogni prompt da aggiungere indica l'**origine**: il numero della domanda AEO, la query di Search Console con le impressioni, la persona, l'id della raccomandazione o il contenuto del piano editoriale che deve misurare.

**Fermati qui.** I prompt si creano solo dopo un ok esplicito sui testi e sulle combinazioni. Il consulente può modificarli: quello che entra è il testo approvato.

## 5. Crea i prompt in HubSpot

Solo dopo l'approvazione. Per ogni gruppo di prompt che condivide ICP e prodotti:

1. `manage_aeo_prompts` `CREATE` con `confirmed: false`, il `businessUnitId`, `icpIds`, `productIds` e, per i testi approvati, `promptTexts`; per i generati, `buyingJourneyPhases` e `numberOfPrompts`. Per i generati, ripeti con il `previewToken` finché arrivano i testi.
2. Mostra l'anteprima:
   - `promptsUsed` / `promptsCapacity` dopo la creazione;
   - i testi generati, o i suggerimenti di `promptQuality` sui testi approvati;
   - l'avviso sui crediti, se `onCredits` è vero.
3. Se l'anteprima dice che si supera il limite, **fermati**: proponi quali prompt togliere nel portale (con `managePromptsUrl`) o un piano più ampio.
4. Solo con un nuovo ok esplicito: `confirmed: true`, con gli stessi testi o lo stesso `previewToken`, e `creditsAcknowledged: true` solo se il consulente ha accettato il costo.
5. Controlla `RUN_STATUS` una o due volte: i primi risultati arrivano dopo il run, spesso il giorno dopo. Non restare in attesa.

Poi aggiorna il registro con gli id restituiti, `stato: tracciato` e la data.

## 6. Il registro

`analisi/prompt-aeo/registro.md` tiene la storia di ogni prompt, anche di quelli tolti, così il confronto tra mesi resta leggibile:

```markdown
---
titolo: "Registro dei prompt HubSpot AEO: <cliente>"
stato: bozza
ultimo_aggiornamento: AAAA-MM-GG
---

# Registro dei prompt HubSpot AEO

| ID HubSpot | Prompt | Lingua e paese | Fase | ICP | Prodotto | Brand | Origine | Stato | Dal | Note |
|---|---|---|---|---|---|---|---|---|---|---|
```

Stati: `proposto`, `approvato`, `tracciato`, `da-togliere`, `tolto`, `scartato`. Un prompt `da-togliere` diventa `tolto` quando la prossima estrazione conferma che non è più tracciato. Lo script segnala le differenze tra registro e HubSpot.

## 7. Revisione mensile

Dopo ogni estrazione di `ie-aeo-hubspot-aeo`, o quando lo chiede il consulente:

1. Lancia lo script e leggi il rendimento.
2. **Non giudicare** i prompt con meno di `giorni_minimi` giorni.
3. **Candidati da togliere:** prompt le cui risposte non riguardano il settore del cliente (controlla con `RESPONSES` una o due risposte), doppioni, temi usciti dalle priorità, prompt senza risposte per un intero periodo.
4. **Da tenere anche con visibilità 0:** sono i temi dove il cliente manca. Vanno al piano editoriale come "prompt scoperti", non tolti.
5. **Da aggiungere:** domande sui contenuti pubblicati nel mese (per misurarli), domande AEO ancora libere, fasi o mercati scoperti.
6. Scrivi la revisione come al passo 4 e fermati per l'approvazione.

## 8. Consegna

- **In chat:** la sintesi, le correzioni del profilo da fare nel portale, i prompt da togliere con il link, i prompt da aggiungere con l'origine.
- **Piano editoriale:** i prompt con visibilità bassa su temi senza contenuto vanno segnalati a `ie-aeo-piano-editoriale`.
- **Commit e push** di `analisi/prompt-aeo/` solo con l'ok del consulente, dopo `git pull --rebase`.

Non scrivere nel repo giudizi sul cliente: la revisione sta nel repo condiviso con lui.
