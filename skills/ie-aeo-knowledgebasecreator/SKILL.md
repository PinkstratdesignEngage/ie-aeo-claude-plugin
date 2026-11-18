---
name: ie-aeo-knowledgebasecreator
description: Guida passo passo un consulente nella costruzione della knowledge base AEO ("company brain") di un nuovo cliente. Chiede nome del cliente, sito web, cartella Google Drive, transcript delle riunioni e altri documenti. Raccoglie le fonti, scrive azienda, ICP e personas, offerta, tone of voice, glossario e il primo content pillar in file Markdown con fonti citate, e pubblica tutto in un nuovo progetto privato sul GitLab dell'agenzia. Usa questa skill ogni volta che l'utente vuole avviare un progetto AEO o di content per un cliente, creare o impostare la knowledge base o il "brain" di un'azienda, raccogliere in un repo le informazioni di un cliente per scrivere contenuti, oppure riprendere una knowledge base cliente lasciata a metà. Vale anche se non dice "knowledge base", per esempio "partiamo con il nuovo cliente X per l'AEO" o "prepariamo il materiale di base su X per i contenuti".
---

# IE-AEO Knowledge Base Creator

Costruisci con il consulente la knowledge base di un cliente: un repo GitLab di file Markdown che descrive chi è l'azienda, a chi si rivolge, cosa offre, come parla e su quali temi vuole farsi trovare dai motori AI. La leggono i consulenti dell'agenzia, il team marketing del cliente e Claude, che la userà per creare e revisionare contenuti.

Il valore della knowledge base sta in due cose: **ogni informazione ha una fonte** e **ciò che non è confermato si vede**. Un contenuto AEO con un dato inventato danneggia il cliente più di un contenuto che non esiste. Per questo ogni passo separa i fatti con fonte dalle deduzioni da validare.

## Come procedere

Il lavoro dura in genere più sessioni: gli esempi di contenuto e le risposte del cliente arrivano dopo. Per questo il progresso si salva in `_privato/stato-lavori.md` dentro il repo locale del cliente.

All'avvio:
1. Chiedi se è un cliente nuovo o una knowledge base da riprendere.
2. Se è da riprendere, chiedi la cartella. Leggi `_privato/stato-lavori.md` e riparti dal primo passo non completato.

Procedi un passo alla volta. Alla fine di ogni passo:
1. aggiorna `stato-lavori.md`;
2. di' al consulente in due o tre righe cosa hai prodotto e cosa resta aperto;
3. chiedi conferma prima di andare avanti.

Per le domande usa lo strumento di domande a scelta multipla quando ci sono opzioni chiare, la conversazione libera per i dati (URL, nomi).

Scrivi tutto in italiano, salvo che il consulente scelga un'altra lingua al passo 1.

## Passo 1: Raccolta degli input

Chiedi, in un massimo di due giri di domande:

| Input | Note |
|---|---|
| Nome del cliente | Ne ricavi lo slug in kebab-case, es. `esempio` |
| Sito web | L'URL della versione nella lingua della KB, es. `https://www.esempio.com/it/` |
| Cartella Google Drive | Link o ID. Opzionale |
| Transcript delle riunioni | Titolo e data delle riunioni su Bluedot, oppure file o testo incollato. Opzionale ma molto utile: è lì che emerge il posizionamento |
| Altri documenti | Percorsi di file locali (PDF, DOCX, PPTX, ecc.) che non stanno su Drive. Opzionale |
| Lingua della KB | Default italiano |
| Lingue dei contenuti | La lingua master in cui si scrivono e quelle in cui verranno tradotti, es. "italiano ora, inglese dopo" |
| Mercati e priorità | Es. "Italia" oppure "mondiale, priorità Europa". È separato dalla lingua: si può scrivere in italiano per un mercato mondiale. Determina ICP, personas, domande AEO e quali servizi o dati sono validi |
| Chi leggerà il repo | Solo l'agenzia, oppure anche il cliente. Se lo legge il cliente (il caso normale), le note interne non entrano nel repo |
| Primo content pillar | Il tema su cui partire, es. "Efficienza energetica". Si può decidere più avanti |
| Gruppo e nome del progetto GitLab | Default: gruppo `aeo/clienti/<Cliente>AEO` su `gitlab.example.com` (es. `aeo/clienti/esempioAEO`), nome `<slug>-brain`, privato |
| Cartella locale | Default: `~/<Nome cliente> - AEO Project/` |

Prima di andare avanti riepiloga gli input in una tabella e fatti confermare.

## Passo 2: Setup del repo locale

1. Crea la cartella locale ed esegui `git init`.
2. Copia lo scheletro da `assets/template/` nella cartella, compresa la cartella nascosta `.claude/`, e rinomina `gitignore` in `.gitignore`. Controlla che `.claude/hooks/controlla-allineamento.sh` sia eseguibile (`chmod +x`). L'hook verifica l'allineamento con GitLab all'avvio della sessione e dopo un'ora senza prompt, per tutti i collaboratori.
3. Sostituisci i segnaposto in tutti i file copiati:

   | Segnaposto | Valore |
   |---|---|
   | `{{CLIENTE}}` | nome del cliente |
   | `{{DATA}}` | data odierna, formato AAAA-MM-GG |
   | `{{MERCATO}}` | mercati e priorità, es. "mondiale, con priorità all'Europa" |
   | `{{LINGUA}}` | lingue dei contenuti, es. "italiano come versione master, poi inglese" |
   | `{{PILLAR}}` | nome del primo pillar |
   | `{{SLUG_PILLAR}}` | slug del primo pillar |

   Se il pillar non è ancora deciso, sostituisci `{{PILLAR}}` con "da definire" e togli la riga del pillar da `05-content-pillars/README.md`.
4. Se il repo non sarà letto dal cliente, adatta la sezione "Riservatezza" di `CLAUDE.md`. Se il mercato è più ampio di un paese, aggiungi in `CLAUDE.md` le regole per un pubblico internazionale: dati con le ipotesi per paese, servizi locali indicati come tali, testo scritto per essere tradotto.
5. Crea le cartelle vuote della struttura descritta in `references/struttura-kb.md`.
6. Crea `_privato/estratti/{sito,drive,meeting,documenti}/` e `_privato/note-interne/`.
7. Scrivi `_privato/stato-lavori.md` con gli input del passo 1 e la checklist dei passi.
8. Esegui `grep -rn "{{" <cartella>` e verifica che non resti nessun segnaposto.

`_privato/` è nel `.gitignore`: lì vanno il materiale grezzo e le note interne. Il repo pubblicato contiene solo sintesi condivisibili.

## Passo 3: Fondamenta dal sito (opzionale)

Il sito è la sola fonte sempre disponibile, completa e verificabile. Scaricarlo prima di
tutto il resto dà ai passi successivi un corpus locale su cui lavorare, invece di far
navigare un subagent pagina per pagina: è deterministico, costa zero token e si può
rilanciare fra un mese per vedere cosa è cambiato.

Proponilo quando il sito ha una certa consistenza. Saltalo se è di poche pagine: in quel
caso basta il subagent del passo 4.

**Non è "scaricare tutto il sito".** Il valore sta nel perimetro, e il perimetro si decide
col consulente, non nello script.

1. **Proponi il perimetro.**

   ```bash
   python3 -I scripts/sito_fetch.py elenco --repo <cartella-repo> --sito <URL_SITO> --lingua <codice>
   ```

   Legge `robots.txt` e la sitemap — anche gli indici di sitemap, e se la sitemap non c'è
   passa a un crawl dei link interni — e stampa la tabella delle sezioni col numero di
   pagine. Le sezioni troppo grandi (blog, news, archivi) restano fuori dalle copie pagina
   per pagina: di un archivio serve l'inventario, non trecento file di prosa. Su un sito
   multilingua `--lingua` tiene un ramo solo; senza, la tabella mostra tutte le lingue.

2. **Fatti confermare la tabella.** Chiedi al consulente quali sezioni servono, quali no, e
   se un archivio escluso va invece incluso. Si corregge con `--escludi <prefisso>` e
   `--solo <prefisso>`. È qui che il lavoro si taglia sul cliente: **non scrivere mai i nomi
   delle sezioni di un cliente dentro lo script.**

3. **Scarica ed estrai.**

   ```bash
   python3 -I scripts/sito_fetch.py fetch --repo <cartella-repo>
   ```

   ```bash
   python3 -I scripts/sito_fetch.py estrai --repo <cartella-repo> --lingua <codice>
   ```

   Le copie finiscono in `raw/sito/<percorso>.md` con `Stato: non analizzato`. La cache HTML
   sta in `_privato/`, già escluso da git. Rilanciare non cambia nulla: il download salta ciò
   che è in cache, e l'estrazione riscrive un file solo se il testo è cambiato davvero.

4. **Leggi gli avvisi.** Se lo script segnala pagine sotto i 200 caratteri, il sito
   probabilmente renderizza in JavaScript e il testo non è stato preso: controllane una a
   mano prima di proseguire, e dillo al consulente, perché è a sua volta un'informazione sul
   cliente — quelle pagine i motori AI non le leggono. Se segnala molti 404, la sitemap del
   cliente è vecchia: va detto anche quello.

Riferisci quante pagine hai scaricato per sezione e cosa è rimasto fuori.

**Cosa questo passo non fa.** Non assegna codici fonte e non scrive schede. I file sono
grezzi: il codice `S` si assegna al passo 4, quando una scheda li cita. Scaricare non è
analizzare — e una knowledge base che ricopia il sito produce contenuti che ricopiano il
sito, cioè esattamente quelli che i motori AI non citano.

## Passo 4: Raccolta delle fonti

Lancia in parallelo un subagent per ciascuna fonte disponibile (sito, Drive, transcript, documenti locali). Usa i prompt di `references/raccolta-fonti.md`, compilati con gli input del cliente. Se hai fatto il passo 3, il subagent del sito legge le copie in `raw/sito/` invece di navigare: è più veloce, più completo e non rischia di saltare pagine. Ogni subagent scrive estratti fedeli in `_privato/estratti/<fonte>/` e restituisce l'elenco delle fonti lette.

Mentre lavorano non duplicare il loro lavoro. Puoi preparare il registro fonti.

Quando tornano:
1. Compila `fonti/registro-fonti.md`, con un codice per fonte: `S01…` sito, `D01…` Drive, `M01…` riunioni, `C01…` contenuti d'esempio, `E01…` fonti esterne.
2. Leggi gli estratti.
3. Riporta al consulente in poche righe:
   - cosa hai trovato;
   - cosa manca;
   - eventuali problemi, come pagine non leggibili, file non supportati o transcript rumorosi.

Se un connettore non è disponibile (Drive o Bluedot non collegati), dillo e chiedi di esportare o incollare il materiale. Non saltare la fonte in silenzio.

### Copiare gli originali in `raw/`

La cartella `raw/` del repo contiene i materiali originali, così chi legge la knowledge base può verificare una fonte senza cercarla altrove. Ci vanno anche i materiali non ancora analizzati. Le regole sono in `references/convenzioni.md` (sezione "Cartella raw"). In sintesi:

- **Documenti del Drive.** Una copia per lingua, senza duplicati, nella stessa organizzazione per argomento. Il connettore scarica solo file fino a 10 MB: per volumi grandi affida i download a uno o due subagent (vedi `references/raccolta-fonti.md`).
- **Pagine del sito.** Una copia di testo per ogni pagina letta, con `scripts/snapshot_pagina.py`.
- **Nomi.** Aggiungi `-analizzato` prima dell'estensione dei materiali letti, anche di quelli che non aggiungono informazioni: nel registro delle fonti si scrive "letto, nessuna informazione nuova".
- **Segnaposto `.link.md`.** Li usi per video, cartelle di foto, file oltre 50 MB o oltre il limite del connettore, e contenuti riservati. Contengono link e motivo.
- **Riunioni.** Il transcript integrale non va mai in `raw/` se il repo è condiviso con il cliente: metti solo il segnaposto.
- **Indice.** Alla fine genera `raw/indice.md` con `scripts/indice_raw.py <cartella-repo>`.

## Passo 5: Sintesi di azienda, audience e offerta

Inizia solo quando sono tornati tutti gli estratti. Spesso il Drive del cliente contiene già buyer personas, linee guida di tono di voce o presentazioni aziendali: scrivere prima di averle lette significa rifare il lavoro.

Scrivi i file di `01-azienda/`, `02-audience/` e `03-offerta/` seguendo `references/struttura-kb.md` (sezioni, frontmatter, cosa mettere in ciascun file) e `references/convenzioni.md` (citazioni, stati, riservatezza).

Puoi lanciare `scripts/verifica_kb.py` già durante la scrittura: trova subito citazioni sbagliate e link rotti.

Alcuni criteri:
- **Fonti in conflitto.** Quando due fonti dicono cose diverse (sito, documenti, riunioni, fonti esterne), riporta entrambe con le rispettive fonti nel file tematico. Registra la differenza in `fonti/incoerenze-cliente-sito.md`, con gravità ed effetto sui contenuti, e apri una domanda in `domande-aperte.md`. Non scegliere tu quale ha ragione. Il file delle incoerenze si aggiorna per tutta la durata del progetto, ogni volta che un nuovo materiale contraddice uno già letto.
- **Materiali non analizzati.** Tieni aggiornato `fonti/materiali-non-analizzati.md`: cosa non hai letto, perché (non leggibile, troppo grande, non ricevuto) e cosa serve per sbloccarlo.
- **Personas del cliente.** Se il cliente ha già definito le sue buyer personas, parti da quelle: stessi ruoli, stessi nomi, citate con la loro fonte. Integrale con quanto emerge dalle riunioni. Aggiungi ruoli nuovi, per esempio un influencer come l'installatore, solo se le fonti li giustificano, e segnalali come aggiunta.
- **Deduzioni.** Le personas e l'ICP sono quasi sempre in parte dedotte: marca `[DA VALIDARE]` ciò che non è detto esplicitamente.
- **Materiale interno del cliente.** Survey interne, questionari della rete vendita e presentazioni riservate si possono usare nella KB in forma aggregata, senza nomi di persone. Nel registro fonti segnale come "uso interno: non citare in contenuti pubblici senza consenso".
- **Transcript.** Il riconoscimento vocale storpia i nomi propri (marchi, competitor, località). Usa il nome corretto solo se lo conferma un'altra fonte; altrimenti marcalo `[DA VERIFICARE]`.
- **Più mercati.** Se il mercato non è un solo paese, separa ciò che vale ovunque da ciò che vale solo in un'area: modello di vendita, servizi, incentivi, normative, etichette energetiche, prezzi dell'energia. Le priorità e i criteri d'acquisto cambiano per area: riportali in `icp.md`.
- **Catalogo completo.** Oltre ai file descrittivi per macro-famiglia, costruisci la tabella completa dei prodotti (`catalogo-<famiglia>.md`) partendo dal listino o dall'elenco prodotti del cliente e dai cataloghi. Per volumi grandi affidala a un subagent. Un catalogo con solo i modelli d'esempio non basta: chi scrive contenuti deve poter verificare ogni modello.
- **Lacune.** Ogni lacuna diventa una riga in `domande-aperte.md`, con il file interessato e chi può rispondere.

## Passo 6: Tone of voice

1. **Prima bozza.** Scrivi `04-brand-voice/tone-of-voice.md`, `messaggi-chiave.md` e `glossario.md` partendo da:
   - come scrive il sito (l'estratto `stile-di-scrittura.md`);
   - le indicazioni emerse nelle riunioni: parole da usare ed evitare, claim, payoff;
   - eventuali linee guida di brand trovate su Drive. Se esiste un documento di ToV del cliente, è la fonte principale.
2. **Esempi.** Chiedi al consulente gli esempi di contenuti esistenti: articoli, post, newsletter, case study. Per ognuno:
   - crea un file in `04-brand-voice/esempi/` con il testo, o il link, e un'annotazione su cosa rispecchia il ToV e cosa no;
   - registralo come fonte `C`.
3. **Revisione.** Rifinisci il ToV alla luce degli esempi.

Se gli esempi non sono ancora disponibili, lascia il ToV in stato `bozza`, segna il passo come "in attesa di esempi" in `stato-lavori.md` e prosegui.

## Passo 7: Primo content pillar

Conduci una sessione di domande e risposte con il consulente, seguendo `references/sessione-pillar.md`. Poi scrivi i quattro file del pillar in `05-content-pillars/<slug-pillar>/`.

Il file più importante per l'AEO è `domande-aeo.md`. Contiene le domande che l'ICP fa davvero agli assistenti AI e diventerà la base dei prompt monitorati in HubSpot. Scrivile come le scriverebbe un cliente, non come titoli di articoli.

Se il consulente non ha ancora scelto il pillar, salta il passo e annotalo.

## Passo 8: Verifica

1. Esegui `python3 scripts/verifica_kb.py <cartella-repo> --allinea-fonti` (il percorso è relativo alla cartella di questa skill). L'opzione `--allinea-fonti` aggiorna il campo `fonti` del frontmatter con i codici citati nel testo. Lo script controlla:
   - frontmatter e stati;
   - che le citazioni esistano nel registro fonti;
   - i link relativi;
   - che `_privato/` sia escluso da git e non venga citato;
   - il conteggio dei `[DA VALIDARE]`.

   Correggi gli errori e rilancia finché non ne restano.
2. **Test di lettura.** Lancia un subagent che risponde *solo* leggendo la KB a 8-10 domande: chi è il cliente, a chi vende, cosa offre, come parla, cosa dice sul pillar, cosa non va detto. Confronta le risposte con gli estratti: le risposte sbagliate o vaghe indicano file da migliorare. Chiedi al subagent anche una sezione "Problemi della knowledge base": contraddizioni tra file, termini non spiegati, riferimenti che non tornano. Di solito trova:
   - claim "fino a" senza base;
   - dati che compaiono solo in `domande-aperte.md`;
   - termini tecnici assenti dal glossario.
3. **Incoerenze.** Rileggi `fonti/incoerenze-cliente-sito.md`. Ogni voce di gravità alta deve avere una domanda aperta, e i file tematici non devono presentare come certo un dato contraddetto.
4. **Controllo di riservatezza.** Se il repo è condiviso con il cliente, rileggi i file che derivano dai transcript, cioè posizionamento, competitor e mercato. Cerca giudizi su persone, valutazioni interne dell'agenzia, nomi di clienti del cliente non autorizzati, prezzi e condizioni commerciali.

## Passo 9: Pubblicazione su GitLab

Creare il progetto e invitare persone sono azioni visibili all'esterno: mostra al consulente cosa stai per fare e aspetta il suo sì. I comandi `glab` vanno sull'istanza dell'agenzia: imposta `GITLAB_HOST=gitlab.example.com` in ogni comando. I remoti sono in HTTPS: SSH non risponde da tutte le reti.

1. **Commit.** `git add -A && git commit` con un messaggio descrittivo. Prima controlla due cose:
   - con `git status`, che `_privato/` non compaia;
   - che in `raw/` non ci siano file oltre 50 MB: `find raw -size +50M`.
2. **Gruppo.** Controlla che esista il gruppo del cliente:

   ```bash
   GITLAB_HOST=gitlab.example.com glab api "groups/aeo%2Fclienti%2F<Cliente>AEO"
   ```

   Se non esiste, chiedi al consulente di crearlo in GitLab o di indicarne un altro: non crearlo tu.
3. **Progetto.** Dalla cartella del repo:

   ```bash
   GITLAB_HOST=gitlab.example.com glab repo create aeo/clienti/<Cliente>AEO/<nome> --private --defaultBranch main
   ```

   Poi collega `origin` in HTTPS e fai il primo push:

   ```bash
   git remote add origin https://gitlab.example.com/aeo/clienti/<Cliente>AEO/<nome>.git
   ```

   ```bash
   git push -u origin main
   ```

   Se `glab repo create` ha già aggiunto `origin`, controlla con `git remote -v` che sia in HTTPS e salta il primo comando.
4. **Membri**, solo se il consulente li indica. Per prima cosa leggi l'id dell'utente:

   ```bash
   GITLAB_HOST=gitlab.example.com glab api "users?username=<username>"
   ```

   Poi aggiungilo al progetto:

   ```bash
   GITLAB_HOST=gitlab.example.com glab api -X POST "projects/aeo%2Fclienti%2F<Cliente>AEO%2F<nome>/members" -f user_id=<id> -f access_level=<livello>
   ```

   I livelli sono 30 (Developer) e 40 (Maintainer). `main` è protetto: lo aggiornano solo i Maintainer; un Developer lavora con le merge request.
5. **Chiusura.** Dai al consulente il link del progetto e un riepilogo di:
   - file prodotti e loro stato;
   - numero di domande aperte;
   - passi rimasti in attesa, per esempio gli esempi di contenuto.
6. **Indice di ricerca su `raw/`.** Proponi al consulente di costruirlo con `ie-aeo-indice-raw`, soprattutto se `raw/` ha cataloghi, schede tecniche o documenti lunghi: le altre skill lo usano per trovare un'informazione nei materiali originali per significato e in più lingue. Si costruisce in background e si carica nel Package Registry del progetto appena creato, con l'ok del consulente.

Dopo la pubblicazione, ogni modifica successiva passa da commit e push. Se il cliente collabora sul repo, meglio una merge request (`glab mr create`).

## Riferimenti

- `references/struttura-kb.md`: cartelle, file e sezioni di ciascun file. Leggilo prima dei passi 2 e 5.
- `references/convenzioni.md`: frontmatter, citazioni, stati, riservatezza. Leggilo prima del passo 5.
- `references/raccolta-fonti.md`: i prompt dei subagent per il passo 4.
- `references/sessione-pillar.md`: le domande per definire il pillar al passo 7.
- `assets/template/`: lo scheletro del repo, con i segnaposto `{{...}}`.
- `scripts/verifica_kb.py`: i controlli automatici del passo 8.
- `scripts/sito_fetch.py`: le fondamenta dal sito del passo 3 — perimetro, download, copie di testo in `raw/sito/`.
- `scripts/snapshot_pagina.py`: salva in `raw/` la copia di testo di una singola pagina, quando ne serve una sola.
- `scripts/indice_raw.py`: genera `raw/indice.md`.
