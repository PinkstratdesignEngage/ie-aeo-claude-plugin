# Content brief

Ogni contenuto parte da un content brief che il consulente approva prima della scrittura. Il brief serve a mettersi d'accordo su domanda, struttura e dati prima di scrivere, e a far emergere subito cosa manca.

Salvalo in `contenuti/<tipo>/AAAA-MM-GG-<slug>.md` con `stato: brief` e mostralo in chat. Dopo l'approvazione lo stesso file diventa la bozza: il brief resta in fondo, nella sezione "Brief".

## Modello

```markdown
---
titolo: <titolo provvisorio>
tipo: blogpost | faq-prodotto | case-study | glossario
stato: brief
lingua: it
slug: <slug-del-contenuto>
categoria: <dal file contenuti/categorie-blog.md, solo per i blog post>
persona: <nome del file della persona, es. proprietario-supermercato>
pillar: <slug del pillar, se c'è>
cluster: <id del cluster in topic-cluster.md, se c'è>
domande_aeo: [<numeri da domande-aeo.md: previste nel brief, coperte dopo l'approvazione>]
parole_obiettivo: <numero indicativo>
fonti: [<codici fonte usati>]
url: 
ultimo_aggiornamento: AAAA-MM-GG
---

# Brief: <titolo provvisorio>

## Domanda AEO principale
La domanda, scritta come la digiterebbe l'utente in un assistente AI.

## Domande collegate
3-6 domande che il contenuto copre, con il numero di domande-aeo.md se c'è.

## Persona e intento
Chi legge, in quale fase del percorso d'acquisto, cosa deve poter fare dopo.

## Angolo e messaggio
Il punto di vista del cliente sul tema e il messaggio chiave usato, dal file messaggi-chiave.

## Struttura proposta
Titolo (H1), risposta breve iniziale, sottotitoli H2 in forma di domanda, tabelle previste, FAQ finale.

## Dati e fonti che userò
| Dato | Base di confronto | Fonte |

## Dati di Search Console
Estrazione usata (`raw/gsc/<data>/`) oppure "non disponibili".
| Query del tema | Click | Impressioni | Pagina che le riceve | Posizione |
**Cannibalizzazione:** pagine esistenti sul tema, decisioni già prese nel report, rischio del nuovo contenuto.
**Proposta:** contenuto nuovo / ristrutturare <pagina> / angolo diverso da <pagina>, con il motivo.

## Domande aperte che pesano su questo contenuto
| Domanda | Cosa cambia | Come procedere se non arriva risposta |
Elenca le domande aperte e le voci delle incoerenze rilevanti. Se non ce ne sono, scrivilo.

## Nuove domande AEO proposte
Domande utili che non sono ancora in domande-aeo.md. Si aggiungono solo con l'ok del consulente.

## Nuove domande aperte proposte
Domande per il cliente emerse preparando il brief. Si aggiungono a domande-aperte.md solo con l'ok del consulente.

## Ipotesi e calcoli
Operazioni sui dati (annualizzazioni, conversioni, esempi economici) con le ipotesi dichiarate. Scrivi "nessuno" se non ce ne sono.

## Link interni
Pillar, contenuti collegati, pagine prodotto. Usa gli URL del registro fonti; se manca, metti un segnaposto.

## Schema.org previsto
I tipi che userai, dal file schema-org.md del plugin.

## Decisione richiesta
Cosa serve dal consulente per partire: ok al brief ed eventuali scelte, ciascuna con le opzioni (scrivere senza il dato, usare un segnaposto, aspettare la risposta).
```

## Regole

- La sezione "Dati di Search Console" segue `lettura-kb.md`. Se i dati dicono che una pagina esistente risponde già al tema con lo stesso intento, la proposta di ristrutturarla va nel brief **prima** di scrivere, come scelta per il consulente.
- Le domande aperte vanno nel brief **prima** di scrivere. Se ce n'è una importante, chiedi come procedere: scrivere senza quel punto, usare un segnaposto o aspettare la risposta.
- Non passare alla scrittura senza un'approvazione esplicita del brief.
- Dopo l'approvazione aggiorna `stato: bozza`.
- La data nel nome del file è quella di creazione del brief e non cambia con la pubblicazione: la data di pubblicazione va nel frontmatter e nello schema.
- Se il tema è un "come" e la domanda AEO più vicina è un "quanto" (o viceversa), scegli come principale quella esistente in domande-aeo.md e copri l'altra nella risposta breve. Proponi la nuova domanda tra le "Nuove domande AEO proposte".
