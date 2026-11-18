# Le slide dell'audit e il foglio degli elenchi

Come si costruiscono la presentazione e il foglio di lavoro su Google, a partire da
`risultati.json`, `azioni.json` ed `elenchi.json`.

Questo passo **non è uno script**: Drive, Slides e Sheets sono connettori di sessione, non
librerie. Lo esegue Claude con i suoi strumenti. Se un connettore non risponde, dillo e
fermati: non c'è un ripiego che produca lo stesso risultato.

Quello che c'è scritto qui è stato provato montando un deck vero e un foglio vero, non
dedotto dalla documentazione.

---

## Il master

**`IE_Template_Audit Tecnico AEO`** — id `<ID DEL VOSTRO TEMPLATE SU DRIVE>`.
Il template dell'agenzia e' un file privato: chi riusa il plugin ne crea uno suo,
con le stesse dieci slide-scheletro descritte qui sotto.

Dieci slide-scheletro, ognuna con i suoi segnaposto `{{...}}` e, nelle note del relatore,
le istruzioni d'uso. **Non si modifica mai**: si copia.

I layout del tema sono 299 e sono brandizzati, ma **quasi nessuno ha segnaposto**: sono
sfondi, e il testo vive in caselle libere sulle slide. Per questo si duplicano le slide
scheletro e si sostituisce il testo dentro, invece di creare slide dai layout.

| Scheletro | Object id | A cosa serve |
|---|---|---|
| Copertina | `g32d2e0723a4_0_5826` | grafica, nessun testo |
| Titolo | `g308e6f32978_0_585` | `{{CLIENTE}}`, `{{DATA}}`, `{{VERSIONE}}` |
| Riservatezza | `g3821393dc92_0_1282` | testo legale fisso |
| Sommario | `g344a0fdf90a_1_3011` | cinque sezioni fisse |
| Divisore | `g409ac58fad2_0_1682` | `{{DIV_DOMANDA}}`, `{{DIV_SOTTOTITOLO}}` |
| Riquadri | `g33d6c2f2a17_0_4078` | vedi sotto |
| Elenco | `g409af0e6c37_0_1128` | `{{ELENCO_TITOLO}}`, poi 1-5 × `{{ELENCO_n_TITOLO}}` e `{{ELENCO_n_TESTO}}` |
| Dettaglio | `g409ac58fad2_0_1687` | **fuori dal deck generato**, vedi sotto |
| Matrice | `g409ac58fad2_0_1788` | **fuori dal deck generato**, vedi sotto |
| Chiusura | `g4099324c5fc_0_1517` | `{{CONSULENTE}}`, `{{RUOLO}}`, `{{EMAIL}}`, `{{TELEFONO}}`, `{{LINKEDIN}}` |

**Riquadri** porta: `{{RIQ_TITOLO}}`, `{{RIQ_OCCHIELLO}}` e `{{RIQ_OCCHIELLO_2}}` (due righe
di occhiello); per ogni riquadro da 1 a 4 `{{RIQ_n_ETICHETTA}}`, `{{RIQ_n_VALORE}}`,
`{{RIQ_n_NOTA}}`; la fascia gialla in basso `{{RIQ_FASCIA_TITOLO}}` e `{{RIQ_FASCIA_1..3}}`.
Il riquadro 1 ha due valori in più (`{{RIQ_1_VALORE_B}}`, `{{RIQ_1_NOTA_B}}`) perché
nell'originale portava due numeri: **vanno sempre svuotati**, altrimenti restano a vista.

I nomi dei segnaposto possono essere uno il prefisso dell'altro senza rischio: le parentesi
di chiusura li rendono comunque distinti, quindi `{{RIQ_1_VALORE}}` non tocca mai
`{{RIQ_1_VALORE_B}}`.

### Le due slide che restano fuori

Sono nel master perché un consulente le compili a mano, ma **il deck generato non le usa**.
Non è prudenza: provate, fanno danno.

**Matrice.** I cartellini `{{MAT_01}}`..`{{MAT_10}}` stanno in posizioni fisse sul quadrante,
ereditate da un altro progetto. Rinominarli senza spostarli produce un grafico che **dice il
falso**: le azioni dell'audit apparirebbero dove stavano iniziative che non c'entrano nulla.
Spostarle davvero vorrebbe dire dare a ogni azione una coordinata di impatto e una di
sforzo, e **lo sforzo l'audit non lo misura**.

**Dettaglio.** Sembra la slide giusta per un indicatore critico, e non lo è. Le barre grigie
sono 24 `ROUND_RECTANGLE` vuote — dodici sotto «Insight», otto sotto «Attività da svolgere»,
quattro sotto «Opportunità» — dimensionate per frammenti di tre o quattro parole. Provata
con frasi vere, **il testo si accavalla fino a diventare illeggibile e sborda dalla slide**.
In più le tre file da cinque `RECTANGLE` (Impatto, Velocità a Impatto, Semplicità) sono
scale di valutazione che arrivano già piene di valori di un altro progetto, e l'audit non
misura nulla che le possa riempire onestamente.

Il dettaglio di un indicatore, nel deck, sta nella slide del suo gruppo e nell'elenco delle
azioni. Il resto sta nella dashboard, che è fatta apposta e si apre con un clic.

---

## Come si monta il deck

Quindici slide, sempre le stesse: niente dipende dal numero di indicatori critici.

| # | Scheletro | Contenuto |
|---|---|---|
| 1 | Copertina | — |
| 2 | Titolo | `{{CLIENTE}}`, `{{DATA}}` in it-IT, `{{VERSIONE}}` = `1.0` |
| 3 | Riservatezza | — |
| 4 | Sommario | — |
| 5 | Riquadri | **In una pagina** |
| 6 | Divisore | `Le quattro domande` / `Come il sito risponde a ognuna` |
| 7-10 | Riquadri ×4 | una per gruppo |
| 11 | Divisore | `Da dove partire` / `Le cose che pesano di più` |
| 12 | Elenco | **Le azioni in ordine** |
| 13 | Elenco | **Come abbiamo misurato** |
| 14 | Elenco | **Prossimi passi** |
| 15 | Chiusura | il consulente che firma |

Il Sommario promette cinque sezioni e il deck le mantiene tutte, **Prossimi passi compresa**:
se la togli, il sommario promette una pagina che non c'è.

**In una pagina** (5): `{{RIQ_TITOLO}}` è il verdetto, lo stesso che calcola la dashboard,
ma **accorciato sotto i 60 caratteri** — «2 cose bloccano la lettura» — perché la casella è
alta una riga sola e oltre quella misura il titolo va a capo e finisce addosso all'occhiello.
La frase intera va nell'occhiello, che di righe ne ha due. I quattro riquadri sono i quattro
gruppi: etichetta = `gruppi[g].nome`, valore = il segno ● ■ ▼ ○, nota = «N da sistemare», «N
da guardare» o «tutto in linea». **Mai «tutto in linea» quando `non_verificati` è maggiore di
zero**: lì si scrive «N non misurati», altrimenti la slide dichiara sano quello che non è
stato guardato. La fascia gialla porta le prime tre azioni di `azioni.json`.

**Una per gruppo** (7-10): `{{RIQ_TITOLO}}` = il nome del gruppo, occhiello = la sua
`domanda`. I quattro riquadri sono i suoi indicatori peggiori — prima i critici, poi quelli da
guardare, poi i non misurati: etichetta = `titolo`, valore = `valore`, nota = `dettaglio`. Se
il gruppo ha più di quattro indicatori, i restanti vanno nella fascia in fondo, per nome; se
ne ha meno, i riquadri in più si cancellano.

Un gruppo dove non c'è niente fuori linea **non si salta**: la regola di casa è che gli
indicatori in linea si mostrano quanto gli altri, quindi i riquadri portano i quattro più
importanti comunque, e la fascia dice in una riga che qui il sito è a posto.

**Le azioni in ordine** (12): fino a cinque righe di **`azioni-slide.json`**, non di
`azioni.json`. Sono le stesse azioni, ma quelle che condividono il rimedio arrivano già
raccolte in una riga: su un sito con undici sezioni di prodotto senza dati strutturati,
`azioni.json` ha undici voci con la stessa identica frase e la slide ne mostrerebbe cinque,
tutte uguali. La riga raccolta dice «Dati strutturati, 11 sezioni», somma le pagine e nel
`dettaglio` elenca le sezioni dalla più grossa alla più piccola.

`azioni.json` resta piatto e con un id per verifica, perché quegli id tengono attaccate le
decisioni del team da un audit all'altro nel piano di lavoro della dashboard SEO e AEO:
accorparli le staccherebbe. La riga raccolta porta `ids`, l'elenco delle azioni che ha dentro.

L'ordine è per gravità e poi per gruppo — **non** per numero di occorrenze, che metterebbe a
confronto immagini, pagine e crawler. A parità di gravità, gruppo e unità vengono prima le
più grosse. `{{ELENCO_n_TITOLO}}` = il `titolo`, `{{ELENCO_n_TESTO}}` = il `rimedio`,
che è un intervento vero e non la conseguenza (`ha_rimedio` lo conferma).

Il conteggio si scrive **con l'unità che l'azione dichiara**: `occorrenze` più `unita`, che
vale `pagine`, `immagini` o `crawler`. Scrivere «360 pagine» dove sono 360 immagini su 9
pagine è il tipo di errore che il cliente nota e che toglie fiducia a tutto il resto. Quando
`occorrenze` è 0 il conteggio si omette del tutto.

Se le azioni sono più di cinque, l'ultima riga dice quante restano e rimanda alla dashboard:
una slide che ne mostra cinque senza dirlo fa credere che siano tutte.

**Come abbiamo misurato** (13): i tre `limiti` di `risultati.json` — campione, rendering,
crawler — più una quarta voce se i dati di campo di PageSpeed mancano. È la slide che tiene
in piedi tutto il resto: senza, il cliente non sa quanto vale quello che ha appena visto.

**Prossimi passi** (14): **chiedi al consulente** chi fa cosa e con quali tempi, e scrivi
quello che dice. Non c'è un campo da cui ricavarlo, e inventare responsabili e date su una
slide che va al cliente è il modo più rapido per farsi smentire in call. Sotto, i due link:
la dashboard e il foglio. Il foglio quindi **si crea prima del deck**, o il link non esiste
ancora.

### La meccanica

1. **Duplica** gli scheletri che servono: `duplicateObject` con l'`objectId` dello scheletro
   e `objectIds: {"<id scheletro>": "deck_NN"}`, che **assegna tu l'id alla slide nuova**
   invece di leggerlo dalla risposta. Da lì in poi sai già come si chiama ogni slide. Gli id
   vogliono almeno 5 caratteri: `deck_01`, non `s1`.
2. **Riempi** ogni slide con `replaceAllText`, **sempre con `pageObjectIds` limitato a quella
   slide**: senza, la stessa sostituzione colpisce tutte le copie.
3. **Cancella i dieci scheletri** con `deleteObject`. Se li lasci, il deck consegnato mostra
   le slide con i `{{...}}` a vista.
4. **Svuota le note del relatore** di ogni slide, con `deleteText` sul
   `speakerNotesObjectId`. Questo passo non si salta: `duplicateObject` copia anche le note,
   e `replaceAllText` **non le raggiunge**, nemmeno con `pageObjectIds`. Senza, il deck
   arriva al cliente con dentro le istruzioni del template.
5. **Riordina** con `updateSlidesPosition`, **una slide per richiesta**: l'API pretende che
   gli id arrivino già nell'ordine in cui stanno nel documento, quindi non si può passare
   l'ordine finale tutto insieme. Quindici richieste da una slide, ognuna col suo
   `insertionIndex`, mettono tutto a posto.

Un segnaposto rimasto senza valore va sostituito con stringa vuota, non lasciato lì. Ma
**svuotare non basta quando la casella ha una cornice**: un riquadro o una riga numerata
svuotati restano come rettangolo vuoto a vista. Vanno cancellati come gruppo di primo
livello — quello che tiene insieme testo e numero — e lo si trova leggendo la slide
duplicata.

Il lotto di `batchUpdate` è **atomico**: se una richiesta è invalida non viene applicato
nulla, e si può correggere e rimandare senza aver lasciato il deck a metà.

Alla fine **rileggi la presentazione e cerca `{{`**, note comprese: se ne trovi uno, non è
finita.

---

## Il foglio

Un foglio per audit, accanto al deck. Lo alimenta `elenchi.json`, che contiene le liste
**intere** — `risultati.json` si ferma a 200 righe per indicatore perché è quello che serve
alla dashboard, il foglio invece le vuole tutte — e, per ogni elenco, una `descrizione`
che dice che cosa contiene.

- **Indice**, la prima scheda: una riga per elenco — indicatore, **descrizione**, gruppo,
  stato, quante righe, e un collegamento alla sua scheda. La descrizione è il campo
  `descrizione` dell'elenco: dice che cosa c'è *nella scheda*, che non è la stessa cosa di
  quello che misura l'indicatore. «Dati strutturati: curvatubi» misura quante pagine
  dichiarano il tipo giusto, ma la scheda elenca quelle che **non** lo dichiarano, e la
  descrizione deve dire quello. Non riusare la `spiegazione` dell'indicatore al suo posto:
  descrive la verifica, non la lista, e in quasi tutti gli elenchi dice il contrario.
  Qualche elenco fa eccezione e raccoglie chi la verifica la passa — le pagine che le FAQ
  ce l'hanno, i crawler provati con il loro esito — e lì la descrizione lo dichiara.
- **Una scheda per elenco**, intitolata con il campo `scheda` (già ripulito dei caratteri che
  Sheets rifiuta e reso unico: non ricalcolarlo). Prima riga le `intestazioni`, poi le
  `righe`, già divise in colonne.
- **Zero elenchi è un caso possibile**, anche con un indicatore critico: ci sono problemi che
  non hanno una lista di URL. Allora il foglio non si crea, e si dice perché.

La ricetta, provata:

1. `create_file` con `contentMimeType: "application/vnd.google-apps.spreadsheet"` e
   `parentId` la cartella dell'audit. Funziona anche su un Drive condiviso.
2. Il foglio **nasce già con `locale: it_IT`**: numeri e date si comportano come devono senza
   bisogno di `updateSpreadsheetProperties`. Ma attenzione, in un foglio italiano **il
   separatore degli argomenti delle formule è il punto e virgola**, non la virgola.
3. `update_spreadsheet` con un `addSheet` per scheda, `index` esplicito e
   `gridProperties.frozenRowCount: 1`. **La risposta di ogni `addSheet` porta il suo
   `sheetId`**: serve per i collegamenti, quindi annotalo mentre arriva.
4. `update_values` per le righe, una chiamata per scheda, col nome fra apici singoli se
   contiene spazi: `'Crawler di citazione'!A1:B6`. Interpreta il contenuto come se fosse
   digitato, quindi **le formule funzionano**: nell'Indice il collegamento alla scheda si
   scrive `=HYPERLINK("#gid=<sheetId>";"<nome scheda>")`.
5. **Per ultima**, cancella la scheda vuota che il foglio si porta dietro dalla nascita: si
   chiama `Foglio1` e ha `sheetId: 0`. Per ultima, perché un foglio senza schede non è valido.

Le righe sono già spezzate in colonne dallo stesso criterio del tasto «Copia» della
dashboard (`colonne()` in `analizza_audit.py`, gemella di quella in `assets/audit.html`): se
cambia uno dei due, vanno cambiati entrambi, altrimenti chi copia dalla dashboard e chi
scarica il foglio ottengono cose diverse.

---

## Dove si tiene il conto

In `analisi/audit-tecnico/config.json`, accanto ad `audit_url`:

```json
{
  "drive_folder_id": "...",
  "audit_folder_id": "...",
  "deck_id": "...",
  "sheet_id": "..."
}
```

`drive_folder_id` è la cartella di progetto del cliente su Drive, chiesta una volta sola.
`audit_folder_id` è la sottocartella `Audit Tecnico` dentro di essa. `deck_id` e `sheet_id`
sono l'**ultimo** deck e foglio prodotti: ogni audit ne crea di nuovi, datati, e i vecchi
restano. Un deck mostrato al cliente a marzo deve continuare a dire quello che diceva a
marzo, mentre la dashboard si aggiorna sul posto.
