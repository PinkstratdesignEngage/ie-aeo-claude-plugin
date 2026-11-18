# Struttura della knowledge base

I nomi dei file sono fissi e uguali per tutti i clienti. Così le altre skill del plugin IE-AEO (creazione e revisione contenuti, gap AEO da HubSpot) sanno dove trovare ogni informazione senza doverla cercare.

```
<repo>/
├── README.md                    navigazione e regole (da template)
├── CLAUDE.md                    istruzioni per Claude (da template)
├── domande-aperte.md            lacune da validare con il cliente
├── .gitignore                   esclude _privato/
├── fonti/
│   ├── registro-fonti.md        codici fonte S/D/M/C/E/R/G/X/H/A
│   ├── incoerenze-cliente-sito.md   differenze tra fonti, con gravità (da template)
│   └── materiali-non-analizzati.md  cosa resta da leggere e perché (da template)
├── 01-azienda/
│   ├── profilo.md
│   ├── posizionamento.md
│   └── mercato-e-competitor.md
├── 02-audience/
│   ├── icp.md
│   └── personas/<ruolo>.md      una persona per file
├── 03-offerta/
│   ├── panoramica.md
│   ├── prodotti/<famiglia>.md   una macro-famiglia per file
│   ├── prodotti/catalogo-<famiglia>.md   tabella completa: un modello per riga
│   ├── servizi.md
│   └── tecnologie.md
├── 04-brand-voice/
│   ├── tone-of-voice.md
│   ├── messaggi-chiave.md
│   ├── glossario.md
│   └── esempi/<contenuto>.md    un esempio annotato per file
├── 05-content-pillars/
│   ├── README.md                (da template)
│   └── <slug-pillar>/
│       ├── pillar.md
│       ├── topic-cluster.md
│       ├── domande-aeo.md
│       └── dati-e-fonti.md
├── contenuti/                   contenuti prodotti con le skill IE-AEO (README da template)
│   ├── categorie-blog.md        categorie del blog del cliente
│   ├── piano-editoriale/        config.json e un piano per mese (skill ie-aeo-piano-editoriale)
│   ├── traduzioni/              config.json: lingue, varianti, mercati (skill ie-aeo-traduzione)
│   └── pubblicazione/           config.json: destinazioni in HubSpot (skill ie-aeo-pubblica-hubspot)
├── analisi/
│   ├── search-console/          config.json e un report per estrazione (skill ie-aeo-search-console)
│   ├── dashboard/               config.json, azioni.json, index.html e dati.json della dashboard (skill ie-aeo-dashboard)
│   ├── semrush/                 config.json e un report per estrazione (skill ie-aeo-semrush)
│   ├── hubspot-aeo/             config.json e un report per download (skill ie-aeo-hubspot-aeo)
│   ├── ga4/                     config.json e un report per estrazione (skill ie-aeo-ga4)
│   ├── prompt-aeo/              config.json, registro.md e una revisione per volta dei prompt (skill ie-aeo-prompt)
│   └── kb-advisor/              config.json, report e piano mensili sulla knowledge base, index.html (skill ie-aeo-kb-advisor)
├── raw/                         materiali originali (vedi convenzioni)
│   ├── README.md                (da template)
│   ├── indice.md                generato da scripts/indice_raw.py
│   ├── sito/  drive/  riunioni/  esterni/  gsc/  semrush/  hubspot-aeo/
└── _privato/                    escluso da git
    ├── stato-lavori.md
    ├── estratti/{sito,drive,meeting,documenti}/
    └── note-interne/
```

Se un file non ha contenuto sufficiente, crealo comunque con le sezioni vuote e una riga `[DA RACCOGLIERE: ...]`. Un buco visibile è meglio di un file mancante.

## Cosa va in ogni file

### fonti/incoerenze-cliente-sito.md
Tutte le differenze tra materiali del cliente, riunioni, sito e fonti esterne. Per ogni voce indica:
- cosa dice ciascuna fonte, con citazione testuale e codice;
- la gravità: **alta** se un dato pubblicabile è contraddetto, **media** se perimetro o nome non sono chiari, **bassa** per refusi e varianti;
- l'effetto sui contenuti;
- la domanda aperta collegata.

In testa c'è una tabella di riepilogo. Le discrepanze di dettaglio sui prodotti restano nei file `catalogo-*.md`, con un rimando. In fondo vanno tre sezioni: cosa è coerente, cosa resta da verificare, cosa non è stato confrontato.

### fonti/materiali-non-analizzati.md
Il registro dei materiali noti ma non ancora entrati nella knowledge base, in quattro gruppi:
1. letti ma non integrati;
2. non leggibili con gli strumenti attuali;
3. accessibili ma non letti;
4. citati ma non ricevuti.

Per ognuno indica il motivo, cosa serve per sbloccarlo e la priorità.

Le sezioni elencate sono quelle attese. Puoi aggiungerne se le fonti lo giustificano, ma non toglierle: le altre skill le cercano per nome.

### 01-azienda/profilo.md
- **In breve**: 3-4 righe che rispondono a "chi è <cliente>". È il paragrafo che un assistente AI dovrebbe poter citare.
- **Storia**: anno di fondazione, tappe principali.
- **Gruppo e struttura**: società, brand, sedi, stabilimenti.
- **Numeri chiave**: fatturato, dipendenti, produzione, presenza geografica, ciascuno con anno di riferimento e fonte.
- **Mission, vision e valori**.
- **Certificazioni**.
- **Ricerca e sviluppo**.

### 01-azienda/posizionamento.md
- **Come si descrive il cliente**: le formule usate dal cliente stesso, con fonte.
- **Differenzianti**: perché sceglierlo rispetto ai competitor, ciascuno con la sua prova (proof point).
- **Percezione da correggere**: es. "visto come bello ma poco tecnologico".
- **Cosa non dire**: promesse da evitare e perché, es. "chiavi in mano".

### 01-azienda/mercato-e-competitor.md
- **Trend comuni** a tutti i mercati, e una sezione per ciascuna area o paese prioritario.
- **Competitor**: per ciascuno come si posiziona, dove è più forte o più debole sul piano dei contenuti, se gli assistenti AI lo citano.
- **Normative e fattori esterni** che muovono la domanda.

### 02-audience/icp.md
- **Come compra il cliente, per area**: vendita diretta o tramite dealer, solo se ci sono più mercati.
- **Segmenti**: chi compra, per dimensione e tipologia.
- **Criteri di fit**: quando un'azienda è un buon cliente e quando no.
- **Chi decide e chi influenza**: buying committee e ruoli esterni (progettisti, installatori, consulenti).
- **Differenze per area**: cosa conta nella scelta in ciascun mercato, solo se ci sono più mercati.
- **Trigger d'acquisto**: cosa fa partire un progetto.
- **Obiezioni ricorrenti**.
- **Personas**: elenco con link ai file.

### 02-audience/personas/<ruolo>.md
- **Chi è**: ruolo, contesto, in cosa consiste il suo lavoro.
- **Obiettivi**.
- **Problemi e timori**.
- **Domande che fa**: formulate come le scriverebbe a un assistente AI. Alimentano `domande-aeo.md`.
- **Cosa lo convince**: dati, prove, formati.
- **Dove si informa**: canali, fonti, eventi.

### 03-offerta/panoramica.md
- **Mappa dell'offerta**: tabella famiglia → per chi → problema che risolve → link al file.
- **Come si compra**: modello di vendita, fasi, chi incontra il cliente.
- **Valore complessivo**: la promessa dell'offerta nel suo insieme.

### 03-offerta/prodotti/<famiglia>.md
- **Cos'è e a cosa serve**.
- **Per chi**: segmenti e personas.
- **Gamma**: modelli principali con nome corretto.
- **Caratteristiche e prestazioni**: solo dati con fonte.
- **Efficienza e sostenibilità**, se pertinente.
- **Referenze**: casi in cui è stato usato.

### 03-offerta/prodotti/catalogo-<famiglia>.md
Tabella con **tutti** i prodotti del cliente, non solo gli esempi: una riga per modello o famiglia e tipologia. Colonne tipiche:
- nome esatto e tipologia;
- dati di efficienza (classe energetica, consumi);
- caratteristiche tecniche chiave (temperatura, refrigerante, alimentazione);
- per chi è pensato e tratti distintivi;
- claim numerici con base di confronto;
- link alla scheda o al catalogo;
- fonti.

Sotto la tabella, le discrepanze tra fonti (listino, cataloghi, sito) e i prodotti con dati insufficienti. Le skill di contenuto la usano per non citare modelli inesistenti e per scegliere quelli giusti per un argomento.

### 03-offerta/servizi.md
Un paragrafo per servizio: cosa include, per chi, come si attiva, livelli e pacchetti.

### 03-offerta/tecnologie.md
Le tecnologie proprietarie o distintive: come funzionano in parole semplici, quale beneficio danno, su quali prodotti sono presenti, con quali dati.

### 04-brand-voice/tone-of-voice.md
- **In sintesi**: 3-5 aggettivi con una frase di spiegazione ciascuno.
- **Principi**: cosa fare, con un esempio "così sì / così no" per ciascun principio.
- **Registro e persona grammaticale**: noi/tu/impersonale, e quando si usa cosa.
- **Per canale**: sito, blog, LinkedIn, newsletter, documenti tecnici.
- **Formattazione**: titoli, elenchi, lunghezza delle frasi.

### 04-brand-voice/messaggi-chiave.md
3-5 messaging pillars. Per ciascuno: messaggio, a chi parla, proof point con fonte.

### 04-brand-voice/glossario.md
- **Nomi corretti**: nomi prodotto, brand e tecnologie con la grafia esatta.
- **Termini da usare**, con definizione breve.
- **Termini da evitare**, e perché.

### 04-brand-voice/esempi/<contenuto>.md
Frontmatter con codice fonte `C`. Contiene il testo o il link del contenuto e un'annotazione su cosa rispecchia il ToV, cosa no e cosa manca per l'AEO.

### 05-content-pillars/<slug-pillar>/
Vedi `sessione-pillar.md` per le domande. Contenuto dei file:
- **pillar.md**: definizione, perimetro (cosa include e cosa no), perché conta per il cliente e per l'ICP, angolo distintivo del cliente, messaggi chiave, personas principali.
- **topic-cluster.md**: tabella con sottotema, domande che copre, persona, formato consigliato, contenuti esistenti da aggiornare, priorità.
- **domande-aeo.md**: 20-40 domande raggruppate per fase del percorso d'acquisto (scoperta, valutazione, decisione), scritte come le scriverebbe l'utente. Per ciascuna indica la persona e il contenuto che dovrebbe rispondere.
- **dati-e-fonti.md**: claim utilizzabili con fonte e anno, claim da non usare (incoerenti o non verificati) con il motivo, riferimenti normativi.
