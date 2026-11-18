# Istruzioni per Claude

Questo repository è la knowledge base di {{CLIENTE}} per il progetto AEO. Lo leggono colleghi dell'agenzia e il team marketing di {{CLIENTE}}.

## Prima di scrivere qualsiasi contenuto su {{CLIENTE}}

1. Leggi `01-azienda/profilo.md` e `04-brand-voice/tone-of-voice.md`.
2. Leggi i file di audience e offerta pertinenti all'argomento (`02-audience/`, `03-offerta/`).
3. Se il contenuto riguarda un pillar, leggi tutta la sua cartella in `05-content-pillars/`.
4. Controlla `04-brand-voice/glossario.md` per i nomi prodotto e i termini da usare o evitare.
5. Controlla `domande-aperte.md` e cerca le domande ancora aperte che toccano il contenuto. Contano:
   - le domande sui file che hai letto;
   - quelle sui dati che pensi di usare;
   - quelle su termini e affermazioni che il contenuto conterrà.

## Domande aperte nel content brief

Prima di scrivere un contenuto prepara un content brief. Se una o più domande aperte possono cambiare il contenuto, segnalale nel brief **prima di iniziare a scrivere**, in una sezione "Domande aperte che pesano su questo contenuto". Per ciascuna indica:
- il numero e il testo breve della domanda;
- cosa cambia nel contenuto a seconda della risposta, per esempio "senza il dato del ritorno dell'investimento la sezione X resta qualitativa";
- come procedere se la risposta non arriva: scrivere senza quel punto, usare un segnaposto `[DATO DA FORNIRE: ...]` oppure aspettare.

Poi chiedi se procedere. Non scrivere la bozza aggirando in silenzio una domanda aperta importante.

Quando una domanda trova risposta:
1. aggiorna i file interessati con la nuova fonte;
2. togli il marcatore `[DA VALIDARE]`;
3. sposta la riga nella sezione "Risolte" di `domande-aperte.md`, con la risposta e la fonte.

## Allineamento con GitLab

Il repo è condiviso: più persone lo modificano.
- Prima di modificare qualsiasi file, verifica che la copia locale sia allineata con GitLab (`origin`, su `gitlab.example.com`): `git fetch` e `git status`.
- Se il controllo automatico (hook in `.claude/settings.json`) segnala commit da scaricare, avvisa l'utente e proponi `git pull --rebase` prima di lavorare. L'hook scatta all'avvio della sessione e dopo un'ora senza prompt.
- Se ci sono modifiche locali non salvate, proponi prima un commit.
- In caso di conflitto conserva le modifiche di tutti e chiedi: non usare mai `push --force` e non sovrascrivere il lavoro dei colleghi.
- Prima di ogni push, fai `git pull --rebase`.
- Per GitLab usa `glab` (con `GITLAB_HOST=gitlab.example.com`), mai `gh`. `main` è protetto: chi non è Maintainer apre una merge request (`glab mr create`).

## Regole

- **Non inventare dati.** Numeri, percentuali di risparmio, certificazioni, clienti e referenze si usano solo se presenti nella knowledge base con una fonte. Se mancano, scrivi un segnaposto esplicito (`[DATO DA FORNIRE: ...]`) invece di stimare.
- **Rispetta lo stato dei file.** Un'informazione marcata `[DA VALIDARE]` non va presentata come certa in un contenuto pubblicabile.
- **Mercato: {{MERCATO}}.**
- **Lingua: {{LINGUA}}.**
- **Riservatezza.** Questo repo è condiviso con il cliente. Non aggiungere valutazioni interne dell'agenzia, giudizi sul cliente o informazioni commerciali riservate. La cartella `_privato/` è esclusa da git e non va mai citata né copiata nei file del repo.

## Quando aggiorni la knowledge base

- Ogni file ha il frontmatter: `titolo`, `stato` (bozza / da-validare / validato), `ultimo_aggiornamento` (AAAA-MM-GG), `fonti` (codici del registro).
- Cita ogni fatto con il codice fonte tra parentesi quadre, ad esempio `[S03]`. Registra le fonti nuove in `fonti/registro-fonti.md`.
- Ciò che è dedotto va marcato `[DA VALIDARE]` e aggiunto a `domande-aperte.md`.
- Un argomento per file, file brevi. Link relativi tra file.
