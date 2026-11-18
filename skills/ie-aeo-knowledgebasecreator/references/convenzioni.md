# Convenzioni

## Frontmatter

Ogni file `.md` del repo, fuori da `_privato/`, inizia così:

```yaml
---
titolo: Profilo dell'azienda
stato: bozza
ultimo_aggiornamento: 2026-10-21
fonti: [S01, S04, M01]
---
```

Il campo `stato` può valere:
- `bozza`: scritto da Claude o dall'agenzia, non ancora rivisto.
- `da-validare`: rivisto dall'agenzia, in attesa del cliente.
- `validato`: confermato dal cliente.

Un file non passa a `validato` senza conferma esplicita del cliente.

## Citazioni

- Ogni dato, numero, claim o affermazione sul cliente porta il codice della fonte tra parentesi quadre, subito dopo la frase: `L'azienda è stata fondata nel 1963 [S02].`
- I codici sono definiti in `fonti/registro-fonti.md`, con prefisso per tipo:
  - `S`: pagina del sito del cliente;
  - `D`: documento Drive;
  - `M`: riunione;
  - `C`: contenuto d'esempio;
  - `E`: fonte esterna.
- Un codice corrisponde a una pagina o a un documento. Un codice può anche raggruppare pagine omogenee, per esempio tutte le news o tutte le schede di una famiglia di prodotto. In quel caso nel testo aggiungi lo slug completo della pagina, es. `[S31 esempio-co2-systems]`, così chiunque può ricostruire l'URL. Spiega nel registro come si ricostruisce.
- Per una riunione basta un codice. Nel testo puoi aggiungere il minuto, es. `[M01 00:13]`.
- Quando due fonti sono in conflitto, registra la differenza anche in `fonti/incoerenze-cliente-sito.md` e riporta entrambe nel testo: `Produzione di circa 130-140 banchi al giorno [M01]; il Company Profile riporta un dato annuo diverso [S08]. [DA VALIDARE]`.

## Cosa non scrivere

- Definizioni tecniche prese da conoscenze generali e attribuite a una fonte del cliente. Se la fonte non le contiene, marcale `[DA RACCOGLIERE]` o cita una fonte esterna `E`.
- Claim "fino a X%" senza base di confronto. Riporta la base quando la fonte la dà, oppure cita il claim tra virgolette come formulazione del cliente.

## Marcatori

| Marcatore | Quando |
|---|---|
| `[DA VALIDARE]` | Deduzione, dato detto a voce, o conflitto tra fonti. Va aggiunto in `domande-aperte.md` |
| `[DA VERIFICARE]` | Interpretazione incerta: nome storpiato nel transcript, norma da controllare |
| `[DA RACCOGLIERE: ...]` | Informazione che manca del tutto |
| `[DATO DA FORNIRE: ...]` | Nei contenuti generati in seguito: segnaposto al posto di un dato che non c'è |

## Riservatezza

Il repo di norma è letto anche dal cliente. Nel repo non entrano:
- valutazioni interne dell'agenzia sul cliente, sulle persone o sulle opportunità commerciali;
- giudizi espressi off-record in riunione, anche dal cliente stesso, su suoi clienti, colleghi o competitor;
- nomi dei clienti del cliente, salvo che siano già pubblici sul sito, ad esempio in un case study;
- prezzi, condizioni contrattuali e dettagli commerciali non pubblici;
- debolezze ammesse in confidenza.

Queste informazioni restano in `_privato/note-interne/`. Nel repo si può riportarne una versione neutra e utile ai contenuti. Per esempio "EPTA ci batte sulle academy" diventa, in `mercato-e-competitor.md`, "La formazione dei frigoristi è un tema presidiato dai competitor [M01]".

## Cartella raw

- **Cosa contiene.** I materiali originali usati per la knowledge base, analizzati o no. Non è materiale di lavoro: gli estratti e le note restano in `_privato/`.
- **Nomi.** Si mantiene il nome originale. Il suffisso `-analizzato` prima dell'estensione indica che il materiale è stato letto per la knowledge base, anche se non ha aggiunto informazioni (nel registro delle fonti: "letto, nessuna informazione nuova"), per esempio `Brochure-CO2-IT-analizzato.pdf`. Senza suffisso, il materiale è disponibile ma non analizzato.
- **Segnaposto `<nome originale>.link.md`.** Sostituiscono i materiali che non entrano nel repo: video, cartelle di foto, file oltre 50 MB o oltre il limite di 10 MB del connettore Drive, contenuti riservati. Contengono titolo, link, dimensione, stato e motivo.
- **Riservatezza.** Valgono le stesse regole del resto del repo. Il transcript integrale di una riunione con commenti off-record non va mai in `raw/`.
- **Pagine del sito.** Stanno in `raw/sito/`, una per pagina, con in testa titolo, URL e data di lettura. Il nome ricalca il percorso della URL con `__` al posto delle `/`: `/case-study/air-dolomiti` diventa `case-study__air-dolomiti.md`. Le genera `scripts/sito_fetch.py` (passo 3); per una pagina sola c'è `scripts/snapshot_pagina.py`. Nascono `Stato: non analizzato` e lo restano finché una scheda non le cita.
- **Indice.** `raw/indice.md` si rigenera con `scripts/indice_raw.py`: non si modifica a mano.

## Stile dei file

- Scrivi file brevi e atomici: un argomento per file.
- Usa frasi fattuali; niente tono promozionale nella KB, che è materiale di lavoro e non contenuto pubblicabile.
- Preferisci le tabelle per elenchi con più attributi.
- Usa link relativi tra file, es. `[ICP](../02-audience/icp.md)`.
- Usa i nomi dei file in kebab-case, senza accenti.
