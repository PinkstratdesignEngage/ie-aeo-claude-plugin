---
name: ie-aeo-rispondi-a-domande-aperte
description: Guida il consulente, o chi lavora con lui sul cliente, a chiudere le domande aperte della knowledge base AEO di un cliente, una domanda alla volta. Ordina le domande per peso (contenuti in lavorazione bloccati, dati contraddetti, file della knowledge base interessati), presenta ciascuna con il contesto e lascia scegliere tra rispondere, dare indicazioni, chiedere più informazioni, saltare o fermarsi. Per ogni risposta propone le modifiche ai file con la fonte, toglie i [DA VALIDARE], sposta la domanda tra le risolte e registra la fonte; a fine sessione riassume e prepara un solo commit. Usa questa skill quando l'utente vuole rispondere o lavorare sulle domande aperte, aggiornare o validare la knowledge base con le risposte del cliente, o dice solo "chiudiamo qualche domanda aperta", "ho le risposte del cliente" o "cosa manca da validare".
---

# Rispondere alle domande aperte

Le domande aperte sono ciò che la knowledge base non sa ancora: finché restano aperte, i contenuti usano segnaposto, evitano dati o li presentano come non certi. Questa skill è una guida: porta l'utente attraverso le domande **una alla volta**, nell'ordine in cui conviene chiuderle, e trasforma ogni risposta in modifiche precise e citate della knowledge base. Lavora nel repo del cliente aperto in Claude Code; le regole di quel repo (`CLAUDE.md`) valgono più di questo documento.

Riferimenti:
- `scripts/stato_domande.py`: ordina le domande, raccoglie il contesto di una domanda, la sposta tra le risolte, ne apre di nuove;
- `../../condivisi/lettura-kb.md`: allineamento del repo e regole sui dati;
- `../ie-aeo-indice-raw/`: l'indice di ricerca sui materiali originali, se il cliente ce l'ha (`fonti/indice-raw/config.json`).

## Regole

- **Una domanda per messaggio.** Mai un elenco di domande da compilare: l'utente risponde meglio a una cosa per volta, con il contesto davanti.
- **Nessuna risposta inventata.** La skill non risponde da sola alle domande. Può cercare la risposta nei materiali del repo (`raw/`, fonti registrate) e proporla, ma la propone come tale, con la fonte, e chiede la conferma.
- **Ogni risposta ha una fonte.** Chi ha risposto, quando e come (vedi "Fonti delle risposte"). Una risposta senza fonte non toglie un `[DA VALIDARE]`.
- **Le modifiche si approvano.** Per ogni risposta la skill mostra le modifiche ai file prima di farle. Niente commit né push senza l'ok.
- **Il repo è condiviso con il cliente.** Le risposte si scrivono come fatti, senza giudizi sul cliente né commenti interni.

## 1. Prepara

1. **Allineamento:** segui "Prima di tutto" di `lettura-kb.md`. Se ci sono modifiche locali di altri, lavora solo sui tuoi file.
2. **Stato delle domande:** dalla radice del repo del cliente

   ```bash
   python3 -I <percorso della skill>/scripts/stato_domande.py elenco
   ```

   Lo script legge `domande-aperte.md`, cerca dove ogni domanda è citata (file della knowledge base, contenuti in `contenuti/`, riepilogo di `fonti/incoerenze-cliente-sito.md`) e le ordina per peso:
   - contenuti in lavorazione che citano la domanda o sono nella colonna "File interessato";
   - incoerenze collegate, con più peso a quelle di gravità alta;
   - regole del `CLAUDE.md`, pillar, brand voice;
   - numero di file della knowledge base interessati.

   In fondo, "Da controllare" elenca i riferimenti rotti (domande citate che non esistono o sono già risolte) e le incoerenze che chiedono una domanda non ancora aperta.
3. **Scegli il percorso con l'utente.** Mostra in breve quante domande sono aperte, le prime cinque per peso con il motivo, e chiedi da dove partire:
   - **in ordine di peso** (proposta di default);
   - **per chi può rispondere**, quando l'utente ha davanti una persona o un reparto del cliente (`--chi "Tecnico"`): utile in riunione;
   - **per tema**, quando c'è un contenuto da sbloccare (`--tema "eco ring, chiller"`);
   - **domande precise** (`--numeri 6,8,47`).

   Se l'utente ha già risposte in mano (una email, un documento, un transcript), leggile prima: la sessione parte dalle domande a cui rispondono.

## 2. Una domanda alla volta

Per la domanda di turno lancia `stato_domande.py dettaglio <numero>` e leggi le righe dei file interessati. Poi presenta la domanda così:

> **Domanda 47** · 3 di 12 in questa sessione · Chi può rispondere: Tecnico / marketing
> Nei negozi DEM i 25 kWh al giorno risparmiati con il recupero di calore sono energia elettrica o termica? …
> **Perché conta:** l'articolo sulla centrale a CO2 è in bozza e il calcolo del risparmio dipende da questa risposta.
> **Cosa sappiamo oggi:** due o tre righe, con la fonte, dai file interessati.
>
> Puoi: rispondere · darmi indicazioni · chiedermi più informazioni · saltare · fermarci qui.

"Perché conta" e "Cosa sappiamo oggi" vengono dal dettaglio: contenuti bloccati, incoerenze, il testo marcato `[DA VALIDARE]` sullo stesso tema. Tieni la presentazione breve: il resto è per "più informazioni".

**Prima di presentarla, cerca nei materiali.** Se il cliente ha l'indice di `raw/`, cerca la domanda, riformulata in 1-3 modi brevi (anche in inglese, se i materiali sono in più lingue):

```bash
~/.cache/ie-aeo-indice/venv/bin/python <percorso del plugin>/skills/ie-aeo-indice-raw/scripts/indice.py cerca "<domanda riformulata>" "<variante>" -k 3
```

Apri la pagina dei risultati che sembrano rispondere. Se uno risponde davvero, aggiungi alla presentazione una riga **"Possibile risposta nei materiali:"** con il passaggio, il file e la pagina, e se il file non ha `-analizzato` nel nome dillo: è un materiale non ancora analizzato. Resta una proposta: la domanda si chiude solo con la conferma dell'utente, e la fonte è il documento (da registrare se manca). Se non trovi niente di pertinente, non dirlo: presenta la domanda come sempre. Cerca in un'unica chiamata le domande della sessione, se sono poche, per caricare il modello una volta.

Usa `AskUserQuestion` per la scelta solo se l'utente preferisce i pulsanti; altrimenti accetta la risposta scritta direttamente, che è il caso più comune.

### Rispondere

1. **Fonte.** Se l'utente non l'ha detto, chiedi in una riga chi ha dato la risposta e come (vedi sotto). Se la risposta è dell'utente stesso, va bene: la fonte è lui.
2. **Controllo.** Confronta la risposta con ciò che dice la knowledge base. Se la contraddice, o contraddice il sito o un documento, dillo prima di modificare: può essere una correzione voluta, o un equivoco da chiarire.
3. **Proposta di modifiche.** Elenca, file per file, cosa cambia:
   - il testo nuovo o corretto, con il codice fonte tra parentesi quadre;
   - i `[DA VALIDARE]` che la risposta scioglie, da togliere (solo quelli sullo stesso tema);
   - le voci di `fonti/incoerenze-cliente-sito.md` che la risposta chiude: segnale come risolte, con la fonte;
   - i contenuti in `contenuti/` che citano la domanda: aggiorna la sezione "Domande aperte che pesano", e, se il contenuto è in bozza, proponi la modifica del testo o del segnaposto `[DATO DA FORNIRE: ...]`. Un contenuto `approvato` o `pubblicato` non si cambia: annota il cambio e proponi `ie-aeo-ristruttura-contenuti`;
   - il frontmatter dei file toccati: `ultimo_aggiornamento`, il codice in `fonti`, e `stato` solo se l'utente lo chiede.
4. **Dopo l'ok:** applica le modifiche e sposta la domanda tra le risolte:

   ```bash
   python3 -I <percorso della skill>/scripts/stato_domande.py risolvi 47 --risposta "Energia termica: ... Aggiornati dati e fonti e l'articolo." --fonte R03
   ```

   Il comando mostra le differenze; rilancialo con `--scrivi`. La risposta nelle risolte è breve: cosa si è deciso e quali file sono stati aggiornati.
5. **Risposte parziali.** Se la risposta chiude solo una parte, aggiorna i file con quella parte e riformula la domanda nella tabella delle aperte con ciò che resta. Non spostarla.
6. **Domande nuove.** Se la risposta apre un dubbio nuovo, proponi di aprire una domanda:

   ```bash
   python3 -I <percorso della skill>/scripts/stato_domande.py nuova --domanda "..." --file "[nome](percorso.md)" --chi "Tecnico"
   ```

   Lo script usa il primo numero libero e non duplica una domanda già presente.

### Dare indicazioni

L'utente non ha la risposta ma sa cosa fare. Casi tipici, con l'azione:

| Indicazione | Cosa fa la skill |
|---|---|
| "È nel documento X" o "guarda il sito" | Cerca nei materiali del repo o nella pagina (con l'indice di `raw/`, se c'è: `--cartella` sulla cartella del documento), propone la risposta con la fonte trovata e chiede la conferma. Una fonte nuova va nel registro |
| "Lo sa Y" o "chiedilo al tecnico" | Aggiorna "Chi può rispondere" e la mette tra le domande da inviare (vedi "Fine sessione") |
| "Non è più rilevante" | La chiude tra le risolte come tolta, con il motivo e la fonte (chi l'ha deciso) |
| "Si fa così" (una decisione, non un fatto) | È una decisione di progetto: si registra come tale, con chi l'ha presa |
| "Riformula" o "dividila" | Propone il testo nuovo, o due domande, e lo applica dopo l'ok |
| "È uguale alla domanda N" | Unisce le due: tiene la più completa e chiude l'altra con il rimando |

### Più informazioni

Mostra ciò che il dettaglio ha trovato e non era nella presentazione: le righe che citano la domanda, i `[DA VALIDARE]` sullo stesso tema, il testo delle incoerenze, le fonti in conflitto con le loro parole. Se serve, apri la copia in `raw/` per la formulazione esatta. Poi ripresenta le scelte.

### Saltare

Passa alla domanda successiva senza toccare nulla. Tieni a mente le saltate per il riepilogo finale, senza scriverle nei file.

## 3. Fonti delle risposte

Ogni sessione con risposte ha **un codice `R`** nel registro (`fonti/registro-fonti.md`, sezione "Risposte e decisioni"), con il primo numero libero: `R03 | Risposte alle domande aperte del 29/10/2026 | <chi ha risposto> | <data> | Domande 7, 27 (...)`.

- **Chi:** la persona che ha dato la risposta, con il ruolo e l'azienda: per esempio "Ufficio tecnico del cliente, tramite il consulente". Se le risposte vengono da persone diverse, una riga `R` per persona.
- **Come:** nella colonna "Cosa riguarda" o nel testo: email, riunione, chiamata, documento. Se c'è un materiale (una email, un documento), salvalo in `raw/` come le altre fonti e indicane il percorso. Una riunione registrata ha già il suo codice `M`: usa quello, con il minuto.
- **Risposta a voce senza materiale:** va bene, con chi e quando. Nel testo della knowledge base il dato resta citato con il codice `R`.
- Una fonte nuova trovata con "dare indicazioni" (una pagina del sito, un documento) si registra con il suo prefisso, non con `R`.

## 4. Fine sessione

Quando l'utente si ferma, o le domande scelte sono finite:

1. **Riepilogo** in chat: domande risolte, parziali, nuove, saltate, e i file modificati.
2. **Domande da inviare al cliente.** Per le saltate e per quelle con un destinatario nuovo, proponi un testo da mandare, raggruppato per "Chi può rispondere": una domanda per punto, con una riga di contesto, scritta per il cliente (senza codici fonte né riferimenti interni). Non inviarlo: lo manda l'utente.
3. **Controlli:** rilancia `stato_domande.py elenco` e guarda "Da controllare": nessun riferimento rotto dovuto alle modifiche della sessione.
4. **Commit unico**, solo dopo l'ok: aggiungi solo i file toccati nella sessione, messaggio del tipo "Domande aperte: risolte 7 e 27, aperta la 50 (R03)". Prima del push, `git pull --rebase`; per il push o la merge request segui le regole del repo.

## Cosa non fa

- Non manda email né messaggi al cliente: prepara il testo.
- Non cambia contenuti approvati o pubblicati: propone la ristrutturazione.
- Non cambia `stato: validato` dei file da sola: lo decide il consulente.
