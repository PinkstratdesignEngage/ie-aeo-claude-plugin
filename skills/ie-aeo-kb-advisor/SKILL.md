---
name: ie-aeo-kb-advisor
description: Analizza la knowledge base AEO di un cliente e scrive un report con un piano per completarla. Prima dice cosa funziona, con le prove; poi dà il livello di ogni area (solida, parziale, scoperta) con criteri contati dai file; poi elenca cosa manca, per tipo (materiali da recuperare, domande da porre, fonti da collegare, decisioni, lavori sulla knowledge base, coerenza); infine propone un piano con chi fa cosa, priorità, tempi e cosa sblocca. Pesa i gap con la domanda reale: ricerche di Search Console, visite AI di GA4, raccomandazioni di HubSpot AEO, contenuti bloccati da dati mancanti. Il report sta nel repo del cliente e diventa una pagina condivisibile; domande e materiali nuovi entrano nella knowledge base solo dopo l'ok. Usa questa skill quando l'utente chiede cosa manca alla knowledge base, come completarla, un check-up o un piano per la KB, o dice solo "com'è messa la knowledge base?" o "cosa chiediamo al cliente questo mese?". Va rilanciata ogni mese: un hook del plugin lo ricorda.
---

# Analisi della knowledge base e piano per completarla

La knowledge base regge tutto il lavoro AEO: un dato che manca diventa un segnaposto in un contenuto, un dato non confermato diventa una frase prudente. Questa skill guarda la knowledge base del cliente dall'esterno, dice cosa funziona e cosa manca, e propone un piano concreto per il cliente e per l'agenzia. Il formato è quello di un report di valutazione: prima i punti di forza, poi i gap, poi le azioni. Lavora nel repo del cliente aperto in Claude Code; le regole di quel repo (`CLAUDE.md`) valgono più di questo documento.

Riferimenti:
- `scripts/analizza_kb.py`: raccoglie i segnali (struttura, aree, fonti, domande, domanda reale, contenuti bloccati);
- `scripts/rendi_report.py`: controlla il JSON del report e compone la pagina da `assets/report.html`;
- `../ie-aeo-rispondi-a-domande-aperte/scripts/stato_domande.py`: apre le domande nuove;
- `../../condivisi/lettura-kb.md`: allineamento del repo e regole sui dati.

## File nel repo del cliente

| File | Contenuto |
|---|---|
| `analisi/kb-advisor/config.json` | `{"report_url": "", "frequenza_giorni": 30}`: il link della pagina, da riusare ogni mese, e la frequenza del promemoria |
| `analisi/kb-advisor/AAAA-MM-GG.md` | Il report in testo, leggibile nel repo |
| `analisi/kb-advisor/AAAA-MM-GG.json` | Gli stessi contenuti in forma strutturata: fanno la pagina e il confronto del mese dopo |
| `analisi/kb-advisor/index.html` | La pagina composta dal modello, pubblicata come artifact |

## 1. Prepara

1. **Allineamento:** segui "Prima di tutto" di `lettura-kb.md`.
2. **Dati:** guarda la data delle ultime estrazioni in `raw/gsc/`, `raw/ga4/`, `raw/hubspot-aeo/`. Se sono più vecchie della loro frequenza, dillo e proponi di aggiornarle prima, perché pesano i gap. Non bloccare: senza dati l'analisi si fa lo stesso, sulla sola struttura.
3. **Segnali:** dalla radice del repo del cliente

   ```bash
   python3 -I <percorso della skill>/scripts/analizza_kb.py --json <cartella temporanea>/segnali.json [--precedente analisi/kb-advisor/<ultima data>.json]
   ```

   Con `--precedente` lo script elenca le voci del piano del mese prima, da verificare.

## 2. Leggi e giudica

Lo script conta; il giudizio è tuo. Leggi:
- `CLAUDE.md`, `01-azienda/profilo.md`, `04-brand-voice/messaggi-chiave.md` (ogni messaggio ha una prova?), `dati-e-fonti.md` di ogni pillar;
- `domande-aperte.md`, `fonti/incoerenze-cliente-sito.md`, `fonti/materiali-non-analizzati.md` (cerca con `grep`, non leggerli interi);
- gli ultimi report in `analisi/` e, se c'è, il piano editoriale del mese.

Poi valuta:

| Domanda | Dove guardare |
|---|---|
| Cosa è solido e si può usare subito? | Aree "solida", file con molte citazioni, fonti recenti, domande già risolte |
| Quali informazioni mancano del tutto? | I `[DA RACCOGLIERE]`: quali hanno già una domanda o un materiale richiesto, quali no |
| Cosa blocca i contenuti in lavorazione? | Contenuti con `[DATO DA FORNIRE]` e le domande che citano |
| Cosa cercano le persone che la KB non sa? | Ricerche e pagine con copertura bassa. **La copertura è un indizio**: traduci le ricerche in altre lingue e cerca nella KB con `grep` prima di dire che un tema manca. Se c'è l'indice di `raw/`, cerca il tema anche lì (`indice.py cerca`, più temi in una chiamata): un tema assente dalla KB ma presente nei materiali è un lavoro sulla KB (analizzare il materiale), non un'informazione da chiedere al cliente |
| Quali materiali aspettano? | `fonti/materiali-non-analizzati.md` e, con l'indice, i file senza `-analizzato` che rispondono ai temi deboli: sono i materiali da analizzare per primi |
| Quali prove mancano? | Messaggi chiave senza dati, case study senza risultati misurati, competitor e mercati senza fonte |
| Cosa è incoerente o superato? | Riferimenti rotti, incoerenze senza domanda, righe dei registri superate dai fatti |
| Cosa è stato fatto dal mese scorso? | Le voci del piano precedente: verifica nel repo (domanda chiusa, file validato, fonte registrata) |

Ogni gap ha una **prova**: un file con la riga, un codice fonte, un numero dell'estrazione. Senza prova non entra nel report.

## 3. Scrivi il report

Il JSON (`AAAA-MM-GG.json`) ha questi campi; il Markdown (`AAAA-MM-GG.md`) ha le stesse sezioni, in testo.

| Campo | Contenuto |
|---|---|
| `cliente`, `data` | Nome del cliente, data del report |
| `sintesi` | Tre frasi: com'è la KB, il limite principale, da dove partire |
| `numeri` | Al massimo quattro numeri, calcolati dai segnali: file, fonti, domande aperte, file validati |
| `funziona` | 3-6 punti: `titolo`, `testo`, `prova`. Fatti, non complimenti |
| `criteri`, `aree` | I criteri dei livelli e, per area, i numeri dello script con `livello` e `perche`. Puoi cambiare un livello solo spiegando perché nel `perche` |
| `gap` | `id` (G1…), `titolo`, `tipo`, `testo`, `prova`, `piano` (le voci che lo risolvono) |
| `piano` | `id` (P1…), `azione`, `dettaglio`, `tipo`, `chi`, `priorita`, `orizzonte`, `sblocca`, `sforzo`, `gap` |
| `avanzamento` | Dal secondo mese: `id`, `azione`, `stato` (fatto, in corso, da fare, superato), `nota` |
| `metodo`, `fonti` | Come è stata fatta l'analisi e su quali estrazioni |

Valori ammessi:
- `tipo`: `materiale` (da recuperare), `domanda` (da porre), `fonte` (da collegare o leggere), `decisione` (da prendere), `task` (lavoro sulla KB), `coerenza` (da sistemare);
- `chi`: `<Cliente> · <reparto>` oppure `Agenzia`. Il reparto viene da "Chi può rispondere" delle domande;
- `priorita`: **alta** se blocca un contenuto in lavorazione o tocca un dato pubblicabile contraddetto; **media** se rafforza un tema con domanda reale o un pillar; **bassa** il resto;
- `orizzonte`: `subito` (entro due settimane), `questo mese`, `prossimi mesi`.

Regole:
- **Piano corto:** 8-15 voci. Ciò che non entra resta nel Markdown, in "Altre voci".
- **Niente dati inventati:** numeri solo dai segnali o dai file, in formato it-IT. Lo sforzo è un ordine di grandezza ("1 riunione", "mezza giornata"), non una stima di costo.
- **Il repo è condiviso con il cliente:** nessun giudizio sulle persone, nessuna informazione commerciale riservata, niente di `_privato/`. Non citare AirOps e non usare la parola "roadmap": lo script di composizione si ferma se le trova.

## 4. Presenta e fai approvare

In chat mostra sintesi, cosa funziona, livelli delle aree e il piano, e chiedi l'ok. Dopo l'ok:

1. Scrivi `AAAA-MM-GG.md` e `AAAA-MM-GG.json` in `analisi/kb-advisor/`; crea `config.json` se manca.
2. Componi la pagina:

   ```bash
   python3 -I <percorso della skill>/scripts/rendi_report.py analisi/kb-advisor/AAAA-MM-GG.json --out analisi/kb-advisor/index.html
   ```

   Se lo script segnala errori, correggi il JSON. La pagina viene dal modello: non riscriverla a mano.
3. Pubblica `index.html` come artifact. La prima volta con `icon` "checklist" e una descrizione di una frase; salva l'URL in `report_url`. Dal mese dopo ripubblica allo stesso `report_url`, così il link condiviso resta lo stesso.

## 5. Porta il piano nella knowledge base

Per ogni voce che si traduce in una scrittura, proponi e scrivi dopo l'ok, una voce alla volta o a gruppi:
- **domande:** aprile con `stato_domande.py nuova` (anteprima, poi `--scrivi`); per chiuderle c'è `ie-aeo-rispondi-a-domande-aperte`;
- **materiali:** aggiungili a `fonti/materiali-non-analizzati.md` con dove sono, perché servono e priorità;
- **coerenza:** le correzioni piccole (un riferimento rotto, una riga superata) si fanno subito, mostrando la modifica;
- **fonti da collegare:** leggerle e integrarle è un lavoro a parte; proponi la skill adatta (per una realizzazione, `ie-aeo-case-study`).

Poi un solo commit, dopo l'ok, con i file toccati: "KB advisor AAAA-MM-GG: report e piano". Prima del push, `git pull --rebase`.

## Ogni mese

Lancia lo script con `--precedente` e riempi `avanzamento`: le voci fatte escono dal piano, quelle ancora valide restano con lo stesso id, le nuove prendono il primo id libero. Nella sintesi dì cosa è cambiato dal mese prima.
