---
name: ie-aeo-indice-raw
description: Indice di ricerca sui materiali originali (raw/) della knowledge base di un cliente — cataloghi e schede PDF, documenti Word e PowerPoint, pagine del sito salvate — per trovare un passaggio per significato e non solo per parola esatta, anche tra lingue diverse, con file e pagina. Lo costruisce il consulente sul suo computer (Docling, bge-m3, LanceDB), lo carica come pacchetto versionato nel Package Registry del progetto GitLab del cliente, e gli altri lo scaricano senza ricostruirlo. Usa questa skill quando l'utente chiede di cercare nei materiali originali, nei cataloghi o nei documenti del cliente ("dove si parla di…", "c'è nei PDF un dato su…", "quale prodotto ha…"), di costruire, aggiornare, scaricare o caricare l'indice di raw/, o quando un'altra skill del plugin deve verificare se un'informazione è già nei materiali. Un hook del plugin lo propone quando l'indice manca o raw/ è cambiato.
---

# Indice di ricerca sui materiali originali

`raw/` contiene i materiali da cui nasce la knowledge base: cataloghi, schede tecniche, presentazioni, documenti Drive, pagine del sito. Spesso sono molti più della knowledge base curata (in un repo cliente tipico circa il 76% del testo). Con `grep` si trova solo la parola esatta, nella lingua giusta; i PDF vanno aperti pagina per pagina. L'indice trova i passaggi per significato, anche in un'altra lingua, e restituisce **file e pagina**.

Cosa non è:
- **Non è una fonte.** Un dato trovato in `raw/` entra in un contenuto solo passando dalla knowledge base, con fonte e stato, come sempre. L'indice serve a trovare, non a citare.
- **Non sostituisce `grep`.** Per un nome di prodotto, una sigla o un numero, la ricerca per parola è precisa quanto quella vettoriale o di più. Nella prova su un repo cliente (10 domande sui cataloghi) la ricerca per parola ha trovato il catalogo giusto tra i primi 5 in 10 casi su 10, quella vettoriale in 8: per questo il modo predefinito è ibrido.
- **Non contiene i dati di analytics.** `raw/gsc/`, `raw/ga4/`, `raw/semrush/`, `raw/ahrefs/`, `raw/hubspot-aeo/` restano fuori: si leggono con le loro skill.

Riferimenti:
- `scripts/ambiente.py`: prepara l'ambiente Python in `~/.cache/ie-aeo-indice/`;
- `scripts/indice.py`: costruisce, controlla, cerca, carica e scarica l'indice;
- `scripts/requirements.txt`, `scripts/requirements-ricerca.txt`: versioni bloccate;
- `../../condivisi/lettura-kb.md`: allineamento del repo e regole sui dati.

## Come funziona

1. **Si costruisce in locale**, sul computer del consulente, non su un server: Docling estrae il testo e le tabelle (in Markdown), lo divide in blocchi per sezione, bge-m3 calcola i vettori, LanceDB li salva con un indice per parola (BM25). Tutto in `.indice/` alla radice del repo del cliente, che git ignora.
2. **Si carica su GitLab** come pacchetto generico `indice-raw` nel Package Registry del progetto del cliente: stessa visibilità privata del repo. Ogni caricamento è una **versione nuova** (`AAAA.MM.GG-<commit>`): nessuno sovrascrive il lavoro di un altro.
3. **Gli altri lo scaricano** e cercano subito. Per aggiornarlo, chi ha l'ambiente completo scarica l'ultima versione e rielabora solo i file nuovi o cambiati.

Il `manifest.json` dentro ogni indice dice su quale commit di `raw/` è costruito, l'impronta di ogni file, le versioni di modello e librerie, chi l'ha fatto e quando. Indici costruiti con versioni diverse non si mescolano: lo script lo controlla e chiede di aggiornare l'ambiente o di ricostruire da zero.

## 1. Prepara

1. **Allineamento:** segui "Prima di tutto" di `lettura-kb.md`.
2. **Ambiente.** Controlla cosa c'è:
   ```bash
   python3 <percorso della skill>/scripts/ambiente.py --verifica
   ```
   | Chi | Ambiente | Spazio | Comando |
   |---|---|---|---|
   | Chi costruisce e aggiorna l'indice (uno o due consulenti per cliente) | completo: estrazione e ricerca ibrida | circa 4 GB | `python3 <percorso della skill>/scripts/ambiente.py` |
   | Chi cerca soltanto | leggero: ricerca per parola | circa 0,5 GB | `python3 <percorso della skill>/scripts/ambiente.py --solo-ricerca` |

   Lo script controlla lo spazio libero e si ferma se non basta: dillo all'utente con i numeri che stampa, non forzare. Installa Python 3.12 con uv dentro `~/.cache/ie-aeo-indice/`, senza toccare il sistema. Per togliere tutto basta cancellare quella cartella.
3. **Configurazione del cliente**, la prima volta: se manca `fonti/indice-raw/config.json`, crealo:
   ```json
   {
     "cartelle": ["raw"],
     "escludi": ["raw/gsc", "raw/ga4", "raw/semrush", "raw/ahrefs", "raw/hubspot-aeo"],
     "pacchetto": "indice-raw"
   }
   ```
   e aggiungi al `.gitignore` del repo `.indice/`, `.indice.nuovo/` e `.indice.vecchio/`. Configurazione e `.gitignore` si committano con l'ok del consulente: la configurazione serve all'hook per sapere che il cliente usa l'indice.

Tutti i comandi qui sotto si lanciano dalla radice del repo del cliente, con il Python dell'ambiente:

```bash
~/.cache/ie-aeo-indice/venv/bin/python <percorso della skill>/scripts/indice.py <comando>
```

## 2. Scarica (sempre prima di costruire)

```bash
... indice.py scarica
```

È una lettura: non serve chiedere. Scarica l'ultima versione, sostituisce `.indice/` solo se il pacchetto è valido, e dice se `raw/` è cambiato dopo quella versione. Se il Package Registry è vuoto, si passa a costruire. `--versione` scarica una versione precisa; l'elenco delle versioni si vede nel progetto GitLab, in Deploy › Package Registry.

## 3. Costruisci (solo con l'ambiente completo)

Quando: l'indice non esiste da nessuna parte, oppure `stato` dice che ci sono file nuovi o cambiati che l'ultima versione non copre.

```bash
... indice.py stato
... indice.py costruisci
```

- Rielabora solo i file nuovi o cambiati e riusa blocchi e vettori degli altri. `--da-zero` rifà tutto: serve dopo un cambio di versioni o quando lo script lo chiede.
- Tempi di riferimento su un Mac M1: circa 10 secondi per un catalogo PDF di 15 pagine, 3 minuti di embedding ogni 1.200 blocchi. La prima costruzione di un repo da 285 file (3.023 blocchi) ha richiesto 27 minuti: lanciala in background e avvisa l'utente. I tempi crescono se il Mac ha poca memoria libera.
- Un file che non si estrae non ferma gli altri: finisce in `errori` nel manifest. Dillo all'utente, con il nome del file.
- Se `raw/` ha modifiche non committate, l'indice le include ma non si può caricare: prima vanno committate e pushate.

## 4. Carica (con l'ok del consulente)

```bash
... indice.py carica
```

Proponilo dopo una costruzione, e carica solo dopo l'ok: è una pubblicazione nel progetto GitLab del cliente, che i colleghi vedono. Lo script si ferma se:
- `raw/` ha modifiche non committate, o il commit dell'indice non è su nessun ramo di GitLab (i colleghi devono poter scaricare gli stessi materiali);
- `raw/` è cambiato dopo l'indice.

Basta un ramo qualsiasi, anche quello di una merge request: il manifest registra su quali rami è il commit. Se non è ancora su `main`, lo script lo dice: dopo il merge l'hook segnalerà l'indice da aggiornare, e la nuova costruzione riusa blocchi e vettori, quindi richiede pochi minuti.

Serve `glab` autenticato su GitLab con almeno il ruolo Developer sul progetto. Il nome della versione lo sceglie lo script; se esiste già, ne crea una nuova con un suffisso. Non si cancellano versioni: se una è sbagliata, se ne carica una nuova e si avvisa chi la usa.

## 5. Cerca

```bash
... indice.py cerca "prima domanda" "seconda domanda" [-k 5] [--modo ibrida|vettoriale|parole] [--cartella raw/drive/prodotti] [--lingua it|en] [--json]
```

- **Più domande in una chiamata:** il modello si carica una volta sola (qualche secondo).
- **Modo:** `ibrida` (predefinito) unisce i due elenchi per posizione. `parole` per nomi di prodotto, sigle, codici e numeri esatti. `vettoriale` per domande descrittive, sinonimi, o quando i materiali sono in un'altra lingua. Con l'ambiente leggero, o se l'indice è stato costruito con un modello diverso, lo script passa da solo alla ricerca per parola e lo dice.
- **Filtri:** `--cartella` per restringere (per esempio ai cataloghi), `--lingua` per i file la cui lingua si riconosce dal nome (`_en-GB`, `it-IT`).
- Se `raw/` è cambiato dopo l'indice, lo script lo dice in testa ai risultati: i file nuovi non ci sono.

Come usare i risultati:
1. **Apri la pagina indicata** prima di usare un dato: il blocco è un estratto e l'estrazione dei PDF può sbagliare (vedi i limiti).
2. **Cerca il documento nel registro fonti** (`grep -n -i "<nome del file o del documento>" fonti/registro-fonti.md`) per il codice fonte. Se il dato non è nella knowledge base, proponi di aggiungerlo con la fonte, non usarlo direttamente.
3. **Materiali non analizzati:** un file senza `-analizzato` nel nome non è ancora stato letto per la knowledge base. Se risponde alla domanda, dillo: è un materiale da analizzare (`fonti/materiali-non-analizzati.md`).
4. Più file con la stessa risposta (per esempio la stessa tecnologia in due famiglie di prodotto) sono un'informazione utile: riportali tutti.

## Limiti noti

- **Icone e immagini non diventano testo.** Nei cataloghi la classe energetica è spesso un'icona: nelle tabelle estratte la riga c'è ma è vuota. Non dedurre che il dato manca.
- **Impaginazioni a più colonne** possono uscire con le frasi in ordine sbagliato: per questo si apre la pagina.
- **Niente OCR:** un PDF scansionato, senza testo, produce zero blocchi. Lo si vede in `stato` (file con 0 blocchi).
- **Video, foto e transcript riservati** restano fuori: in `raw/` sono segnaposto `.link.md`, che non si indicizzano.
- **La lingua** si riconosce dal nome del file e dal percorso; per gli altri file resta vuota e il filtro `--lingua` li esclude.

## Riservatezza

L'indice contiene il testo di `raw/`. Ha la stessa visibilità del repo del cliente e non va copiato altrove: non va negli artifact, nelle pagine pubblicate né in chat oltre ai passaggi che servono. `_privato/` non è mai indicizzato.

## Aggiornamento

All'avvio di ogni sessione l'hook del plugin controlla, nei repo con `fonti/indice-raw/config.json`:
- **indice assente in locale:** Claude lo scarica dopo averlo detto in una riga (è una lettura);
- **file di `raw/` cambiati dopo il commit dell'indice:** Claude prima scarica l'ultima versione, che può già comprenderli; se non basta, propone di ricostruire e poi di caricare.
