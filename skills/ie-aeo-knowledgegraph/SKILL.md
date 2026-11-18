---
name: ie-aeo-knowledgegraph
description: Genera la mappa navigabile della knowledge base di un cliente, come webapp in stile Obsidian pubblicata come artifact di Claude. Legge i file Markdown del repo, ne prende frontmatter e link, e disegna il grafo dei documenti: chi cita chi, quali prodotti, soluzioni e settori li tengono insieme, da quali fonti vengono. Dentro la mappa c'è una chat che risponde sulla knowledge base citando i documenti, con l'account claude.ai di chi la usa. Serve a vedere com'è messa la knowledge base — i documenti isolati, quelli dichiarati vuoti, i temi che fanno da perno — e a girarci dentro invece di aprire i file uno a uno. Usa questa skill quando l'utente chiede la mappa, il grafo o la rete della knowledge base, di vedere come sono collegati i contenuti, una vista tipo Obsidian del repo, o dice solo "fammi vedere la struttura della KB" o "dove sono i buchi", e quando vuole interrogare o chattare con la knowledge base.
---

# Knowledge graph della knowledge base

La knowledge base è fatta di file Markdown con un frontmatter regolare e link fra loro. Letti tutti insieme sono già un grafo: questa skill lo estrae e lo rende navigabile.

Serve a due cose diverse, e vale la pena tenerle distinte:
- **Girare dentro la knowledge base**: partire da un prodotto e vedere quali case study lo citano, da un pillar e vedere quali contenuti ne discendono, da una fonte e vedere cosa ci si è costruito sopra.
- **Vedere com'è messa**: quali documenti non li raggiunge nessun link, quali sono dichiarati `copertura: vuoto`, quali temi fanno da perno e quali restano scollegati. È una diagnosi che leggendo i file uno a uno non si fa.

Riferimenti:
- `scripts/costruisci_grafo.py`: dal repo scrive `grafo.json`;
- `assets/grafo.html`: la webapp, uguale per tutti i clienti;
- `../../condivisi/lettura-kb.md`: allineamento del repo e regole della knowledge base.

## Come è fatta

| Parte | Dove sta | Chi la scrive |
|---|---|---|
| Dati | `analisi/knowledge-graph/grafo.json` | Lo script, dai file del repo |
| Pagina | `analisi/knowledge-graph/index.html`, dal modello del plugin | La skill, alla pubblicazione |
| Configurazione | `analisi/knowledge-graph/config.json`: `grafo_url`, `con_testo` | Claude, alla prima pubblicazione |

**Nodi.** I documenti, e le voci che li tengono insieme: soluzioni, prodotti, settori (dai campi `soluzioni:`, `prodotti:`, `settore:` del frontmatter) e le fonti (dai codici di `fonti:`, gli stessi di `fonti/registro-fonti.md`).

**Archi.** Tre tipi:

| Arco | Da dove viene | Cosa dice |
|---|---|---|
| `cita` | un link Markdown fra due file del repo | un documento ne richiama un altro |
| `riguarda` | `soluzioni:`, `prodotti:`, `settore:` | due documenti parlano della stessa cosa |
| `fonte` | `fonti: [D01, S02]` | il documento viene da quel materiale |

**I tipi di nodo si distinguono per forma, non per colore**: cerchio il documento, quadrato la tassonomia, rombo la fonte. Il giallo resta solo per il nodo scelto e per l'azione principale. È il profilo «app» del design system dell'agenzia: il brand non ha colori semantici, e un grafo a dodici tinte sarebbe un'identità diversa.

**La chat.** Il pannello Chat fa domande a Claude con l'account claude.ai di chi guarda la pagina, tramite la capability `sample` degli artifact. Non serve nessuna chiave API, e una chiave non va mai messa nella pagina: la leggerebbe chiunque abbia il link. Ogni domanda consuma l'uso di chi la fa, e alla prima claude.ai chiede il consenso.
- Claude legge i documenti con tre funzioni della pagina, tutte in sola lettura: `cerca_testo`, `leggi_documento`, `collegamenti`. Se la vista non le permette, la pagina gli passa i documenti più pertinenti insieme alla domanda.
- Cita i file con `[[percorso]]`, che nella risposta diventano link al nodo.
- La conversazione vive solo nella pagina aperta: non si salva e non la vede nessun altro.
- Senza `--con-testo` risponde solo su titoli, estratti e sezioni, e lo dice.

## 1. Prepara

1. **Allineamento:** segui "Prima di tutto" di `lettura-kb.md`. Il grafo fotografa il repo com'è adesso: se ci sono modifiche non ancora tirate giù, la mappa è già vecchia.
2. **Niente da configurare alla prima volta.** Lo script legge la struttura standard della knowledge base. Se il cliente ha cartelle sue da lasciare fuori, si aggiungono con `--escludi`.

## 2. Costruisci il grafo

Dalla radice del repo del cliente:

```bash
python3 -I <percorso della skill>/scripts/costruisci_grafo.py
```

Se `config.json` ha `"con_testo": true`, aggiungi `--con-testo` (vedi sotto). Lo script scrive `analisi/knowledge-graph/grafo.json` e stampa i conteggi, i documenti non collegati e i link che non puntano a un file esistente. Quei due elenchi sono già un risultato: portali al consulente anche prima di pubblicare.

**Cosa resta fuori, sempre:** `_privato/`, `raw/`, `.git/`, `node_modules/`, `.claude/`, `app/`, `tools/`. `_privato/` perché è materiale riservato; `raw/` perché contiene i grezzi e i segnaposto, non i nodi della knowledge base.

**Testo completo o solo struttura.** Di default, di ogni file restano titolo, metadati, un estratto di poche righe e i titoli delle sezioni: quanto basta per navigare, e la chat risponde solo su questo. Con `--con-testo` il grafo include anche il corpo dei documenti e la chat risponde nel merito, ma chiunque apra il link legge tutta la knowledge base.
- **Chi decide:** il consulente, cliente per cliente. Chiediglielo alla prima pubblicazione, con questa conseguenza davanti.
- **Dove resta la scelta:** in `config.json` (`"con_testo": true`), così le rigenerazioni successive la rispettano.
- **Quando ha senso:** solo se la knowledge base è già condivisa con il cliente e la pagina resta tra consulenti e cliente.

`_privato/` e `raw/` restano fuori in ogni caso. Lo script ricorda a schermo che il grafo contiene il testo completo.

## 3. Pubblica

**Prima volta** (nessun `grafo_url` in `analisi/knowledge-graph/config.json`):
- copia `assets/grafo.html` in `analisi/knowledge-graph/index.html`, sostituendo `{{TITOLO}}` con `Knowledge graph <Nome cliente>`;
- pubblica con il tool Artifact:
  - `file_path`: `analisi/knowledge-graph/index.html`;
  - `files`: `{"grafo.json": "analisi/knowledge-graph/grafo.json"}`;
  - `icon`: `"map"`;
  - `capabilities`: `{"sample": {}}`, per la chat;
  - una `description` di una frase;
- salva l'URL in `config.json`.

L'unica capability è `sample`: la mappa non salva niente, né le domande né le risposte. Le decisioni stanno nella dashboard, che è un'altra cosa.

**Le volte successive:** leggi la pagina con `Artifact` `action: "read"` sull'URL, poi pubblica con `url` = `grafo_url`, lo stesso `file_path` e lo stesso `files`, senza `icon` e senza `capabilities`, che restano quelle salvate. Una mappa pubblicata prima della v0.17.0 non ha la chat: alla prima ripubblicazione passa `capabilities: {"sample": {}}` una volta. Il grafo si rigenera da zero a ogni giro: non ci sono decisioni da conservare.

Il grafo invecchia con il repo, e la chat risponde su quella fotografia. Rigeneralo quando la knowledge base cambia davvero — dopo una sessione di ingestione, dopo un blocco di contenuti nuovi — non a calendario. L'hook del plugin lo propone, all'avvio della sessione e a fine turno dopo una modifica alla knowledge base, quando un file Markdown della knowledge base è cambiato dopo l'ultimo commit di `grafo.json`: per questo `grafo.json` va committato insieme a `config.json`.

## 4. Cosa guardare

Lo script trova e conta; la lettura la fa il consulente. Tre cose che il grafo dice e i file da soli no:

- **Documenti non collegati.** Nessun link li raggiunge e non ne portano. Un case study isolato non verrà mai proposto da una skill di contenuto, perché nessuna pagina lo richiama. Di solito manca un link dal pillar o dalla scheda prodotto: è un lavoro di dieci minuti che cambia la vita al contenuto.
- **Documenti con `copertura: vuoto`.** Sono nella mappa ma dentro non c'è niente. La pagina li segna con un riquadro giallo quando li apri. Se un tema vuoto è anche molto collegato, è il primo da riempire.
- **Perni.** I nodi con più archi sono i temi su cui la knowledge base è davvero costruita. Se un prodotto importante per il cliente non è un perno, la knowledge base non lo racconta abbastanza: vale come segnale per il piano editoriale.

I link che non puntano a un file esistente sono refusi o file rinominati: si correggono nel repo, non nel grafo.

## 5. Consegna

In chat:
- il link;
- i conteggi: documenti, archi, citazioni fra documenti;
- i documenti non collegati e quelli vuoti, con la proposta su cosa fare;
- i link rotti, se ce ne sono;
- se la chat risponde sul testo completo o solo sulla struttura.

La pagina è privata finché il proprietario non la condivide dal menu Condividi. Vale come la dashboard: consulenti dell'organizzazione in lettura e scrittura, persone del cliente in sola consultazione.

Commit e push di `analisi/knowledge-graph/` solo con l'ok del consulente. `grafo.json` pesa qualche centinaio di KB e si rigenera da sé, ma va committato: è dal suo ultimo commit che l'hook capisce se la mappa è vecchia. Senza, il promemoria non scatta.
