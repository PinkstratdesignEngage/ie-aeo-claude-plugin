---
name: ie-aeo-ga4
description: Misura con Google Analytics 4 le visite che arrivano al sito di un cliente dagli assistenti AI (ChatGPT, Perplexity, Gemini, Copilot, Claude e simili), che Search Console non separa e HubSpot AEO non conta. Scarica i dati grezzi nel repo della knowledge base del cliente, calcola sessioni, quota sul totale, andamento, coinvolgimento ed eventi chiave per assistente e le pagine su cui arrivano, e scrive un report con le azioni proposte per la dashboard e le skill di contenuto. Usa questa skill quando l'utente chiede del traffico da ChatGPT o dagli assistenti AI, di GA4 o Google Analytics, dei risultati AEO in termini di visite, o dice solo "quante visite ci portano gli AI?" o "aggiorniamo i dati di Analytics". Va rilanciata ogni mese: un hook del plugin lo ricorda.
---

# Google Analytics 4: traffico dagli assistenti AI

HubSpot AEO dice se gli assistenti AI nominano e citano il cliente; Search Console dice come lo trova Google, senza separare AI Overviews e AI Mode. Solo GA4 dice **quante persone arrivano davvero sul sito da un assistente AI**, su quali pagine e cosa fanno dopo. È la misura del risultato del lavoro AEO. Il metodo è uguale per tutti i clienti; proprietà, dati e report stanno nel repo di ciascuno.

Riferimenti:
- `references/accesso.md`: API, credenziali, testo per chiedere l'accesso al cliente, problemi frequenti;
- `scripts/estrai_ga4.py`: elenca le proprietà e scarica i report in CSV;
- `scripts/analizza_ga4.py`: calcola i numeri del report;
- `../../condivisi/lettura-kb.md`: allineamento del repo;
- `../ie-aeo-dashboard/`, `../ie-aeo-piano-editoriale/`, `../ie-aeo-ristruttura-contenuti/`: chi usa questi dati.

## Cosa GA4 non dice

Dillo al consulente la prima volta e scrivilo nel report:
- **Una parte delle visite dagli assistenti AI non si vede:** le app e alcuni browser non passano la sorgente, e quelle visite finiscono tra le dirette. I numeri sono un minimo, non il totale.
- **AI Overviews e AI Mode di Google** arrivano come ricerca organica da Google: non si separano.
- **Le sorgenti si riconoscono dal nome** (per esempio `chatgpt.com`, `perplexity.ai`). L'elenco è nello script e si allarga con `--sorgenti-extra` quando compaiono assistenti nuovi.
- **Le soglie di GA4** possono nascondere righe con pochi utenti, se nella proprietà sono attivi i Google Signals.

## 1. Prepara

1. **Allineamento:** segui "Prima di tutto" di `lettura-kb.md`.
2. **Configurazione:** se c'è `analisi/ga4/config.json`, il collegamento è già fatto: vai al passo 2. Se non c'è, fai il collegamento guidato qui sotto.

### Collegamento guidato (la prima volta per un cliente)

Chi usa la skill può non essere un tecnico. Guidalo **un passo alla volta**: fai tu i comandi, spiega in una frase cosa succede, dagli una sola cosa da fare per volta e aspetta che l'abbia fatta. Non chiedere mai di copiare id, aprire menu tecnici o scegliere tra elenchi di proprietà: ci pensa lo script.

**Passo A. Controllo automatico.** Lancia dalla radice del repo del cliente:

```bash
python3 <percorso della skill>/scripts/estrai_ga4.py verifica
```

Lo script controlla librerie, credenziali, consenso e API, e si ferma al primo problema con un messaggio chiaro. Per ogni caso, cosa dire all'utente:

| Lo script dice | Cosa fai tu | Cosa chiedi all'utente |
|---|---|---|
| Mancano le librerie | Lancia `pip3 install -r <percorso della skill>/scripts/requirements.txt` e rilancia `verifica` | Niente |
| Mancano le credenziali Google | Spiega che sono le stesse di Search Console, uguali per tutti i consulenti | "Chiedi il file delle credenziali al referente tecnico e dimmi quando ce l'hai." Poi aiutalo a metterlo in `~/.config/ie-aeo-gsc/credenziali.json` |
| Si apre il browser | Avvisa prima che succederà | "Ora si apre una pagina di Google: entra con l'account a cui il cliente ha dato o darà l'accesso ad Analytics, e premi Consenti. Serve solo a leggere i dati." |
| Una API non è attiva | Dai il link stampato dallo script | "Apri questo link, premi il pulsante blu Abilita, e dimmi quando hai fatto." Poi rilancia `verifica` |
| Nessuna proprietà visibile | Il cliente non ha ancora dato l'accesso | Prepara il messaggio per il cliente (passo C) |
| Tutto pronto | Vai al passo B | Niente |

**Passo B. Trova la proprietà del cliente.** Con il dominio del sito, preso da `analisi/search-console/config.json` o da `CLAUDE.md`:

```bash
python3 <percorso della skill>/scripts/estrai_ga4.py trova --dominio <dominio del cliente>
```

Lo script cerca, tra le proprietà visibili, quelle che misurano il dominio, mostra le sessioni reali degli ultimi 30 giorni e gli host, e **consiglia** la proprietà e il filtro sull'host. Spiega all'utente la scelta in una frase ("I dati del sito sono nella proprietà *Sito*, che negli ultimi 30 giorni ha 12.400 visite su www.esempio.com; la proprietà *TEST* non ha visite.") e chiedi solo una conferma.

Attenzione ai casi in cui la proprietà da usare non è quella che il cliente indica: una proprietà "TEST" o di staging spesso non ha dati, e una proprietà può raccogliere più siti del gruppo. Fidati delle sessioni, non del nome.

Se lo script non trova proprietà del dominio, il cliente non ha dato l'accesso a quella giusta: passo C.

**Passo C. Accesso del cliente.** Prepara il messaggio da mandare al cliente con il testo di `references/accesso.md`, già compilato con l'indirizzo email dell'account usato al consenso (chiedilo all'utente se non lo sai). Fermati finché il cliente non risponde; quando ha dato l'accesso, riparti dal passo B.

**Passo D. Configurazione.** Con la conferma dell'utente, salva in `analisi/ga4/config.json` la proposta stampata da `trova`:

```json
{
  "proprieta": "123456789",
  "nome": "www.esempio.com",
  "host": "^www\\.esempio\\.com$",
  "mesi": 16,
  "sorgenti_extra": "",
  "frequenza_giorni": 30
}
```

- `proprieta`: l'id numerico consigliato da `trova`. Una configurazione per repo; altre proprietà del cliente si estraggono a mano con `--proprieta`.
- `host`: un'espressione regolare sull'host, facoltativa. Serve quando la proprietà raccoglie anche altri siti o domini del gruppo: tiene solo il sito principale, come la proprietà di Search Console, così i numeri si confrontano. Vuota per tenere tutto.
- `sorgenti_extra`: domini o nomi di assistenti da aggiungere all'elenco standard, separati da `|`.
- `frequenza_giorni`: ogni quanto l'hook del plugin ricorda di rilanciare la skill.

Nel repo va solo l'id della proprietà del cliente: l'elenco delle proprietà visibili può contenere altri clienti, e non va copiato.

## 2. Estrai

```bash
python3 <percorso della skill>/scripts/estrai_ga4.py estrai --proprieta <id> --host "<host>" --mesi <mesi> --sorgenti-extra "<sorgenti_extra>"
```

Scarica in `raw/ga4/<data di oggi>/`:

| File | Contenuto |
|---|---|
| `ai_mensile.csv` | Sessioni dagli assistenti AI per mese, sorgente e mezzo |
| `ai_pagine.csv` | Pagine di arrivo delle sessioni AI, per sorgente |
| `ai_paesi.csv` | Paesi delle sessioni AI |
| `canali_mensile.csv` | Sessioni di tutti i canali per mese, per la quota AI |
| `metadati.json` | Proprietà, periodo, espressione usata, totali |

Le letture non costano nulla e non cambiano niente in GA4.

## 3. Analizza

```bash
python3 -I <percorso della skill>/scripts/analizza_ga4.py raw/ga4/<data>
```

Lo script stampa totali e quota AI, il confronto degli ultimi tre mesi completi con i tre precedenti e con l'anno prima, i numeri per assistente, il mese per mese, le pagine di arrivo e le sorgenti riconosciute.

Poi leggi i numeri:
1. **Sorgenti:** controlla l'elenco delle sorgenti riconosciute. Una sorgente estranea presa per errore va esclusa: dillo nel report e proponi di correggere l'elenco.
2. **Pagine di arrivo:** sono le pagine che gli assistenti AI già citano e mandano ai lettori. Incrociale con:
   - `prompt/` dell'ultima estrazione HubSpot AEO, per vedere da quali domande arrivano;
   - `query_pagina.csv` di Search Console, per le query della stessa pagina;
   - `contenuti/`, per sapere se sono contenuti ristrutturati o scritti con il plugin, e da quando.
3. **Effetto dei contenuti:** per i contenuti pubblicati con il plugin (frontmatter `url` e `stato: pubblicato`), confronta le sessioni AI della pagina prima e dopo la pubblicazione, solo se ci sono almeno due mesi di dati dopo.
4. **Qualità delle visite:** coinvolgimento ed eventi chiave delle sessioni AI rispetto alla ricerca organica. Se gli eventi chiave non sono configurati nella proprietà, scrivilo.

## 4. Scrivi il report

`analisi/ga4/AAAA-MM-GG.md`, con la data dell'estrazione:

```markdown
---
titolo: "GA4, traffico dagli assistenti AI: <sito>, <periodo>"
stato: bozza
ultimo_aggiornamento: AAAA-MM-GG
fonti: [<codice A dell'estrazione>]
estrazione: raw/ga4/AAAA-MM-GG/
---

# Traffico dagli assistenti AI: <sito>

## In sintesi
3-5 punti: sessioni AI e quota, andamento, assistenti principali, pagine di arrivo, azioni.

## Andamento
| Mese | Sessioni AI | Quota AI |

## Per assistente
| Assistente | Sessioni | Coinvolgimento | Eventi chiave | Andamento |

## Pagine di arrivo
| Pagina | Sessioni AI | Assistente principale | Prompt o query collegati | Azione |

## Contenuti del plugin
Effetto dei contenuti pubblicati, quando ci sono abbastanza dati.

## Limiti dei dati
Visite non attribuite, AI di Google dentro la ricerca organica, soglie, sorgenti escluse.
```

I numeri si prendono dalla stampa dello script, non si ricalcolano a mano. Formato italiano: virgola per i decimali, punto per le migliaia. Non scrivere giudizi sul cliente: il report sta nel repo condiviso.

**Azioni da proporre:**
- pagine con molte visite AI e poca risposta AEO (senza risposta iniziale, FAQ o schema): `ie-aeo-ristruttura-contenuti`, proteggendo ciò che già funziona;
- pagine che ricevono visite AI ma non convertono: verifica con il consulente le chiamate all'azione;
- assistenti in crescita senza prompt tracciati in HubSpot AEO: `ie-aeo-prompt`;
- temi con visite AI e nessun contenuto dedicato: `ie-aeo-piano-editoriale`.

## 5. Registra e consegna

1. **Registro fonti:** aggiungi l'estrazione in `fonti/registro-fonti.md` con il prefisso `A`, per esempio `A01 | GA4 proprietà 123456789 | raw/ga4/2026-11-02/ | 2025-07-01 – 2026-11-01`. Se il prefisso è già usato da un'altra fonte, scegline uno libero e dillo.
2. **Riservatezza:** i dati di GA4 sono del cliente. Prima del commit controlla che non ci siano dati personali (non dovrebbero: lo script scarica solo dati aggregati).
3. **In chat:** la sintesi, le pagine di arrivo principali, le azioni collegate alle skill che le realizzano.
4. **Commit e push** di `raw/ga4/<data>/`, del report, del registro e della configurazione solo con l'ok del consulente, dopo `git pull --rebase`.

## Aggiornamento ogni 30 giorni

All'avvio di ogni sessione l'hook del plugin controlla `analisi/ga4/config.json` e la data dell'ultima cartella in `raw/ga4/`. Oltre `frequenza_giorni` chiede a Claude di rilanciare questa skill senza aspettare una richiesta: sono solo letture, senza costi, e non cambiano nulla in GA4. Claude avvisa l'utente in una riga prima di partire; il commit resta da approvare.

Di solito il consenso dato la prima volta si rinnova da solo. Se Google lo chiede di nuovo, si apre il browser: avvisa l'utente ("si apre una pagina di Google: entra con lo stesso account e premi Consenti") e, se non può farlo in quel momento, rimanda l'aggiornamento.
