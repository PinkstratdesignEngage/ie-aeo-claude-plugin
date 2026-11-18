---
name: ie-aeo-case-study
description: Scrive un case study in ottica AEO (Answer Engine Optimization) per un cliente, partendo dalla sua knowledge base: un progetto reale di un suo cliente raccontato come risposta a una domanda, con risultati misurati, fonte e base di confronto, citazione autorizzata, FAQ e Schema.org. Al primo uso per un cliente costruisce il registro dei casi (casi candidati, dati disponibili, permessi) e, dopo il primo case study approvato, il modello di struttura del cliente, entrambi nel suo repo; dai successivi li applica. Usa questa skill quando l'utente chiede un case study, una referenza, una storia di successo o il racconto di un progetto realizzato per un cliente, anche se dice solo "scriviamo il caso DEM" o "quali casi possiamo raccontare". Per un case study già pubblicato sul sito usa ie-aeo-ristruttura-contenuti.
---

# Case study AEO

Per gli assistenti AI un case study è una prova: un progetto reale, con un risultato misurato, che conferma ciò che il cliente dice di sé. Funziona se risponde a una domanda che i lettori fanno ("quanto si risparmia con…", "come ha fatto… a…") e se ogni numero ha una fonte, una base di confronto e un periodo di misura. Il collo di bottiglia, di solito, non è la scrittura ma i permessi e i dati: per questo la skill tiene un registro dei casi nel repo del cliente.

Il metodo è uguale per tutti i clienti. Ciò che è specifico di un cliente (quali casi ha, cosa si può nominare, quali metriche usa, come vuole le citazioni) sta nel suo repo, in due file che la skill crea al primo uso.

Riferimenti:
- `../../condivisi/lettura-kb.md`: allineamento, cosa leggere, regole sui dati, piano editoriale;
- `../../condivisi/content-brief.md`: il modello del brief;
- `../../condivisi/checklist-aeo.md`: i controlli prima della consegna;
- `../../condivisi/schema-org.md`: `Article` per i case study;
- `../../condivisi/archivio-contenuti.md`: dove salvare, stati, modelli di struttura;
- `../../condivisi/scripts/verifica_faq_schema.py`: FAQ e schema identici;
- `../ie-aeo-ristruttura-contenuti/SKILL.md`: per i case study già pubblicati, e per il formato del modello di struttura (passo 5);
- `../ie-aeo-traduzione/`, `../ie-aeo-pubblica-hubspot/`: dopo l'approvazione.

## I file del cliente

| File | Contenuto | Quando nasce |
|---|---|---|
| `contenuti/case-study/registro-casi.md` | I casi del cliente: candidati, in lavorazione, pubblicati, esclusi, con dati, fonti e permessi | Al primo uso, dalla knowledge base, confermato dal consulente |
| `contenuti/modelli/case-study.md` | Il modello di struttura dei case study del cliente, con le metriche standard e le regole su nomi e citazioni | Dopo il primo case study approvato |
| `contenuti/case-study/AAAA-MM-GG-slug.md` | Un case study | A ogni caso |

### Il registro dei casi

```markdown
---
titolo: "Registro dei casi: <cliente>"
stato: bozza
ultimo_aggiornamento: AAAA-MM-GG
fonti: [<codici>]
---

# Registro dei casi

| Id | Cliente finale | Paese | Anno | Soluzioni | Risultati con fonte | Citazione | Permesso | Pagina esistente | Contenuto | Note |
|---|---|---|---|---|---|---|---|---|---|---|
```

- **Id:** `CS01`, `CS02`… Restano uguali nel tempo.
- **Risultati con fonte:** solo numeri presenti nella knowledge base, con fonte, base di confronto e periodo, per esempio "-15% di energia rispetto a impianti HFC equivalenti, 2025 [E01]". Se mancano: "nessun dato".
- **Citazione:** "sì" con la fonte se esiste una dichiarazione del cliente finale, altrimenti "no".
- **Permesso**, cioè cosa si può dire del caso:

  | Stato | Significato |
  |---|---|
  | `pubblico` | Il caso è già pubblicato dal cliente con nome, per esempio nelle realizzazioni del sito: si può nominare con ciò che è già pubblico |
  | `concesso` | Il cliente finale ha autorizzato, con la fonte dell'autorizzazione |
  | `solo-anonimo` | Si può raccontare senza nome, per esempio "una catena di supermercati in Austria" |
  | `da-verificare` | Non si sa: va chiesto prima del brief |
  | `negato` | Non si racconta |

- **Pagina esistente:** l'URL, se il caso è già sul sito. In quel caso il lavoro è una ristrutturazione.

## 1. Prepara

1. **Allineamento:** segui "Prima di tutto" di `lettura-kb.md`.
2. **Piano editoriale:** se il caso è nel piano del mese, parti dalla sua voce, come dice `lettura-kb.md`.
3. **Registro:** leggi `contenuti/case-study/registro-casi.md`. Se non c'è, costruiscilo (passo 2) prima di scegliere il caso.
4. **Modello:** se c'è `contenuti/modelli/case-study.md`, vale come regola di struttura per questo caso.
5. **Caso già pubblicato?** Se il registro ha una pagina esistente per il caso, il lavoro passa a `ie-aeo-ristruttura-contenuti`, con la tipologia `case-study` e lo stesso modello. Questa skill scrive i casi nuovi.

## 2. Costruisci o aggiorna il registro

Cerca i casi in tutta la knowledge base, con `grep -n -i` sui nomi dei clienti finali e su parole come "referenze", "realizzazioni", "case study", "progetto":
- le sezioni sulle referenze nei file di `03-offerta/` e `01-azienda/`;
- `04-brand-voice/esempi/`: i case study che il cliente ha già scritto;
- `fonti/registro-fonti.md`: pagine delle realizzazioni, documenti di case study, articoli esterni su progetti del cliente;
- `raw/indice.md`: le pagine del sito sulle realizzazioni già salvate;
- `05-content-pillars/*/topic-cluster.md`: i casi pianificati o richiesti da un cluster;
- `domande-aperte.md`: permessi, dati e casi in preparazione;
- le news recenti, che spesso raccontano aperture e progetti.

Se il cliente ha l'indice di `raw/` (`fonti/indice-raw/config.json`), cerca anche lì, per significato: risultati e numeri di progetto, interviste, rassegne stampa e presentazioni spesso non contengono le parole "case study" o "referenza". Per esempio, in una chiamata sola, `indice.py cerca "risultati ottenuti dal cliente nel punto vendita" "risparmio energetico misurato dopo l'installazione" "intervista al cliente" -k 8`. Per ogni caso trovato apri il passaggio e cerca il documento nel registro fonti; un materiale non ancora analizzato va segnalato come tale.

Per ogni caso riporta solo fatti con fonte. Un caso il cui permesso non risulta da nessuna parte è `da-verificare`. Se il cliente ha molti progetti, per esempio un archivio di realizzazioni molto ampio, registra prima quelli con dati, citazioni o rilevanza per i pillar, e scrivilo nel file.

Mostra il registro al consulente e salvalo solo dopo il suo ok. Le domande sui permessi e sui dati mancanti vanno proposte per `domande-aperte.md`, sempre con il suo ok.

Il registro si aggiorna a ogni case study: stato del caso, contenuto collegato, permessi ottenuti.

## 3. Scegli il caso e la domanda

Un buon caso per l'AEO ha:
- **permesso** `pubblico`, `concesso` o `solo-anonimo`;
- **un risultato misurato**, con fonte e base di confronto. Un progetto senza numeri si può raccontare, ma come caso di progetto (cosa è stato fatto e perché), non come prova di un risultato: dillo al consulente;
- **coerenza** con un pillar, una persona e un mercato prioritari del cliente.

La **domanda principale** parte dal risultato, non dal nome del cliente finale: "Quanto si risparmia con…?", "Come si riduce… in un…?". Se c'è una domanda AEO del pillar che il caso prova, usa quella.

## 4. Prepara il brief e aspetta l'approvazione

Usa `content-brief.md` con `tipo: case-study` e aggiungi:

```markdown
## Il caso
Id del registro, cliente finale, paese e città, anno, formato o settore, soluzioni del cliente, partner coinvolti.

## Risultati
| Risultato | Base di confronto | Periodo di misura | Fonte |

## Citazioni
| Testo esatto | Persona e ruolo | Fonte | Autorizzata |

## Permessi
Cosa si può nominare: cliente finale, luogo, persone, foto, numeri. Stato nel registro e fonte del permesso.
```

Regole:
- **Numeri:** solo quelli della knowledge base, con fonte, base di confronto e periodo. Un risparmio in denaro solo con prezzi e ipotesi dichiarati, come prescrive `lettura-kb.md`.
- **Nomi:** il cliente finale si nomina solo con permesso `pubblico` o `concesso`. Con `solo-anonimo` si descrive (tipo di azienda, paese, dimensione) senza dettagli che lo rendano riconoscibile.
- **Citazioni:** solo testi esatti da una fonte, attribuiti a persona e ruolo, e autorizzati. Non si scrivono citazioni "verosimili": se manca, il brief propone di chiederla.
- **Chi ha fatto cosa:** se il progetto coinvolge società del gruppo o partner del cliente, attribuisci ogni parte a chi l'ha fatta, con la fonte.

**Fermati qui.** Si scrive solo dopo un'approvazione esplicita del brief. Se un permesso è `da-verificare`, il brief lo dice e propone come procedere: chiedere prima, scrivere in forma anonima, oppure aspettare.

## 5. Scrivi

Segui il modello del cliente se c'è; altrimenti questa struttura, che diventerà il modello:

1. **H1** con risultato e soluzione, per esempio "Come una catena di supermercati ha ridotto i consumi del 15% con…".
2. **Risposta breve**, 40-60 parole: chi, cosa ha fatto, quale risultato rispetto a cosa.
3. **Box "Il progetto in breve":** tabella con cliente finale, formato, paese, anno, soluzioni, risultato principale.
4. **H2 in forma di domanda**, per esempio:
   - Qual era il problema da risolvere?
   - Quale soluzione è stata scelta, e perché?
   - Quali risultati ha ottenuto? (tabella prima/dopo o confronto, con base e periodo)
   - Cosa dice il cliente? (la citazione autorizzata)
   - Cosa vale anche per altri progetti simili? (le lezioni generali, con il link al pillar)
5. **Link** alle pagine delle soluzioni usate, al pillar e ai contenuti collegati.
6. **FAQ**, 3-5 domande diverse dagli H2.
7. **Metadati:** meta title, meta description, slug, categoria.
8. **Schema.org:** un `@graph` con `Article` (`about` il cliente finale come `Organization`, solo se si può nominare; `mentions` con prodotti e tecnologie; `contentLocation` se il luogo è pubblico), `FAQPage` e `Organization` del cliente. Segui `schema-org.md`.

Tono: quello che `tone-of-voice.md` prevede per i case study, di solito narrativo. Le citazioni restano parola per parola.

## 6. Controlla e salva

1. **Checklist:** `checklist-aeo.md` punto per punto.
2. **Schema:** `python3 -m json.tool` sul JSON-LD, poi `python3 ../../condivisi/scripts/verifica_faq_schema.py <file>`.
3. **File:** `contenuti/case-study/AAAA-MM-GG-slug.md` con `stato: bozza` e, nel frontmatter, `caso` (id del registro), `cliente_finale` e `permesso`. In fondo, il brief approvato e le fonti per sezione.
4. **Registro:** aggiorna la riga del caso con il percorso del contenuto.

## 7. Il modello del cliente

**Dopo il primo case study approvato**, ricava `contenuti/modelli/case-study.md` con il formato del modello di `ie-aeo-ristruttura-contenuti` (passo 5) e queste sezioni in più:
- **Metriche standard:** i risultati che il cliente usa per misurare i suoi progetti, con unità e base di confronto, per esempio consumi in kWh al giorno rispetto a un impianto precedente;
- **Nomi e permessi:** come si chiede e si registra un permesso per questo cliente, chi lo dà;
- **Citazioni:** formato e chi le approva;
- **Varianti:** per esempio "caso con risultati" e "caso di progetto", senza numeri.

Mostralo in chat e salvalo con l'ok del consulente. Dai case study successivi il modello si applica senza ridiscuterlo; le modifiche si propongono con il motivo, come in `ie-aeo-ristruttura-contenuti`.

## 8. Consegna

- **In chat:** un riepilogo di 3-4 righe, i segnaposto, i permessi e i dati da chiedere, le domande da aggiungere a `domande-aperte.md` con l'ok del consulente.
- **Approvazione del cliente finale:** se il permesso lo prevede, il testo va approvato anche da lui prima della pubblicazione. Il registro lo segna nelle note.
- **Dopo l'approvazione:** segui `archivio-contenuti.md` (domande AEO coperte, commit), poi, se servono, `ie-aeo-traduzione` e `ie-aeo-pubblica-hubspot`. Aggiorna la voce del piano editoriale e proponi a `ie-aeo-prompt` un prompt sulla domanda che il caso prova.
- **Commit e push** solo con l'ok del consulente, dopo `git pull --rebase`.

Non scrivere nel registro o nel case study giudizi sul cliente o sui suoi clienti finali: i file stanno nel repo condiviso.
