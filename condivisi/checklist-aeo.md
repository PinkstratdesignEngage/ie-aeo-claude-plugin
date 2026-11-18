# Checklist AEO

Un contenuto AEO deve poter essere letto, capito e citato da un assistente AI: dà una risposta chiara e verificabile a una domanda precisa. Controlla ogni punto prima di consegnare la bozza.

## Struttura
- [ ] **H1** chiaro, che contiene il tema o la domanda principale.
- [ ] **Risposta nelle prime due o tre frasi**, citabile da sola, in 40-60 parole circa. Il resto approfondisce.
- [ ] **Sottotitoli H2 in forma di domanda**, scritti come le domande reali dell'utente.
- [ ] **Paragrafi brevi**, un'idea ciascuno, ciascuno comprensibile anche estratto dal resto.
- [ ] **Tabelle o liste** per confronti, dati tecnici e passaggi.
- [ ] **FAQ finale** di 3-6 domande con risposta breve, identiche allo schema `FAQPage` (controllo: `scripts/verifica_faq_schema.py`).

## Contenuto
- [ ] **Entità nominate:** nome del cliente, dei prodotti e delle tecnologie con la grafia del glossario. Niente pronomi vaghi al posto dei nomi.
- [ ] **Numeri** sempre con la base di confronto ("rispetto a…"), l'anno o il contesto, e coerenti con la knowledge base.
- [ ] **Nessun claim vietato:** termini da evitare del glossario, superlativi non dimostrabili, dati segnati da validare presentati come certi.
- [ ] **Prove:** almeno un caso reale, un dato o un riferimento verificabile per il messaggio principale.
- [ ] **Mercato:** se il mercato non è un solo paese, niente riferimenti validi solo in un paese senza dirlo.
- [ ] **Tono:** quello di `tone-of-voice.md`, compresa la persona grammaticale.

## Collegamenti e metadati
- [ ] **Link interni** al pillar e ai contenuti collegati.
- [ ] **Nessuna cannibalizzazione nuova:** la domanda principale non è già presidiata, con lo stesso intento, da un'altra pagina del sito, secondo i dati di Search Console (`lettura-kb.md`) o, senza dati, i contenuti del repo e del sito.
- [ ] **Meta title** (massimo 60 caratteri) e **meta description** (massimo 155) proposti.
- [ ] **Slug** breve, in minuscolo, con trattini.
- [ ] **Data di aggiornamento** visibile, se il CMS la mostra.
- [ ] **Schema.org** in JSON-LD valido (vedi `schema-org.md`), con dati identici a quelli del testo.

## Consegna
- [ ] **Frontmatter** del file aggiornato: stato, domande AEO coperte, fonti.
- [ ] **Segnaposto** `[DATO DA FORNIRE: ...]` elencati in chat, se ce ne sono.

## FAQ prodotto
Per le FAQ di una pagina prodotto non valgono H1, risposta iniziale, H2, meta title, meta description, slug e link interni: le FAQ sono un box dentro una pagina che esiste già. Valgono:
- [ ] **Domande** che nominano il prodotto, come le farebbe un utente a un assistente AI.
- [ ] **Risposta nella prima frase**, in 2-4 frasi in tutto.
- [ ] Tutti i punti di **Contenuto** qui sopra.
- [ ] **Schema.org** valido, con FAQ identiche al testo: lancia `scripts/verifica_faq_schema.py`.
- [ ] **Consegna**: frontmatter e segnaposto.

