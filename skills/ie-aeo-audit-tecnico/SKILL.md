---
name: ie-aeo-audit-tecnico
description: Audit tecnico AEO del sito di un cliente, consegnato come dashboard condivisibile dove ogni indicatore si apre e si spiega da solo a una persona non tecnica. Verifica sul campo che gli assistenti AI riescano a leggere il sito (richiesta vera con lo user-agent di ogni crawler, non solo lettura del robots.txt), che il contenuto esista nell'HTML senza JavaScript, la copertura dei dati strutturati per sezione, titoli, immagini, sitemap, link rotti, certificato e tempo di risposta misurato come lo misura un crawler. Vale per qualunque tipo di sito: vetrina, corporate, e-commerce, landing. Le azioni che trova entrano nel piano di lavoro della dashboard SEO e AEO. Usa questa skill quando l'utente chiede un audit o un'analisi tecnica del sito, di verificare se gli assistenti AI riescono a leggere un sito, i blocchi ai crawler, lo stato dello schema.org, la salute tecnica di un sito cliente, o dice solo "com'è messo tecnicamente il sito" o "ChatGPT riesce a leggerci?". Finita la dashboard propone di preparare la presentazione di restituzione su Google Slides, dal template dell'agenzia, e il foglio con tutti gli URL da correggere, nella cartella di progetto del cliente su Drive: usala anche quando l'utente chiede le slide dell'audit, il deck o il foglio degli URL da sistemare.
---

# Audit tecnico AEO

Tre script e una dashboard. Gli indicatori sono raggruppati per la domanda a cui rispondono, non per tecnologia, perché è l'ordine in cui si raccontano in call:

| Gruppo | La domanda | Cosa guarda |
|---|---|---|
| **Ci vedono?** | Gli assistenti riescono a leggere il sito | accesso dei crawler provato sul campo, contenuto senza JavaScript, noindex, certificato |
| **Ci capiscono?** | Quello che leggono è organizzato bene | dati strutturati per sezione, autore, date, titoli, immagini |
| **Trovano tutto all'interno del sito web?** | Arrivano a tutte le pagine che contano | sitemap e `lastmod`, canonical, link rotti, soft 404, `llms.txt` |
| **Quanto aspettano?** | Il sito risponde prima che rinuncino | tempo di risposta per gli utenti e per un crawler, peso delle pagine |

Riferimenti:
- `references/verifiche.md`: ogni verifica, la soglia e perché quella soglia;
- `scripts/scansiona_sito.py`: raccoglie i dati grezzi;
- `scripts/misura_velocita.py`: PageSpeed Insights e misura da crawler;
- `scripts/analizza_audit.py`: indicatori, giudizi e azioni per la dashboard;
- `assets/audit.html`: la dashboard, uguale per tutti i clienti;
- `references/slide.md`: il template Google Slides, la mappa dei segnaposto e il foglio degli elenchi;
- `../../condivisi/lettura-kb.md`: allineamento del repo.

## Prima di cominciare

**Il mandato.** Lo script chiede le pagine presentandosi con il nome di ogni crawler AI, perché il `robots.txt` da solo non dice se il WAF o la CDN li respingono. Si fa **sul sito del cliente, con il suo mandato**. Non è uno strumento per aggirare i blocchi di siti di terzi, e non va puntato su un sito che non stiamo seguendo.

**Cosa misura davvero questa verifica.** I controlli seri sui bot verificati non guardano il nome che il crawler si dà: guardano l'indirizzo di rete o il DNS inverso. Quindi una richiesta che si presenta come Googlebot dal portatile del consulente può essere respinta **proprio perché** non supera quella verifica, mentre il Googlebot vero passa. La verifica dice come il sito tratta chi si presenta con quel nome — il primo filtro che incontra un assistente — non se il crawler autentico sia bloccato. Prima di dire a un cliente che è fuori da Google, incrocia con Search Console: se ci sono impressioni, Googlebot entra.

**Se il cliente ha già Semrush o Ahrefs**, il loro Site Audit copre già titoli, immagini, link rotti e certificato. In quel caso usa `--solo-aeo`: scansiona molte meno pagine e, in analisi, tiene solo le verifiche che gli altri non fanno (accesso dei crawler, rendering, schema per sezione, `llms.txt`). **Non salta la scansione**: rendering e copertura dello schema hanno bisogno delle pagine, e dichiararli in linea senza averle lette sarebbe peggio che non misurarli. La dashboard dichiara cosa è rimasto fuori.

Le azioni che l'audit manda in dashboard si accorgono se Semrush o Ahrefs segnalano già lo stesso problema: in quel caso non si duplicano, si aggiungono come seconda fonte di quella azione.

## 1. Prepara

1. **Allineamento:** segui "Prima di tutto" di `lettura-kb.md`.
2. **Configurazione**, solo se le sezioni del sito non sono quelle tipiche. `analisi/audit-tecnico/config.json`:

   ```json
   {
     "sito": "https://www.esempio.com",
     "max_pagine": 400,
     "sezioni_attese": { "realizzazioni": ["Article"], "catalogo": ["Product"] }
   }
   ```

   `sezioni_attese` dice quale tipo di dati strutturati ci si aspetta in ogni sezione, e serve quando le cartelle del sito hanno nomi loro. Le sezioni tipiche (`blog`, `prodotti`, `servizi`, `case-study`, `faq`…) sono già previste.
3. **Chiave PageSpeed**, facoltativa, in `~/.config/ie-aeo-psi/chiave.txt`. È gratuita e dà i dati reali di Chrome. Senza, resta la misura fatta da noi e la dashboard lo dichiara.

## 2. Scansiona

```bash
python3 -I <percorso della skill>/scripts/scansiona_sito.py https://www.esempio.com
```

**Senza `--max-pagine` si legge tutta la sitemap.** È il comportamento giusto e va lasciato così: la coda parte già da tutti gli URL che il cliente dichiara, e un tetto più basso non sceglie quali pagine leggere, taglia dove capita. Un audit su un campione non dice quante pagine hanno un problema, dice quante ne hanno fra quelle che abbiamo guardato, e il cliente legge il primo numero anche quando scriviamo il secondo. Il tetto scende a 400 solo quando la sitemap è più piccola o non c'è.

Conta mezzo secondo di pausa più la risposta per ogni pagina, quindi circa dieci minuti ogni 500: su un sito da tremila pagine è un'ora e mezza, e lo script lo stampa prima di partire. Se il tempo non c'è, `--max-pagine` esiste ancora, ma allora dillo al cliente insieme al numero: il limite dichiarato in «Come abbiamo misurato» serve a questo.

Scrive un file per fase in `raw/audit-tecnico/<data>/`, **appena la fase finisce**: una scansione interrotta non si perde.

Dopo le pagine, lo script controlla con una richiesta leggera i **bersagli dei link interni che la scansione non ha raggiunto** (`--max-link`, 400 di default). Senza questo passo l'indicatore sui link rotti non troverebbe niente ogni volta che il sito ha più pagine del tetto, perché un bersaglio rotto quasi mai compare in sitemap: è un vuoto che non si vede, non un numero basso.

Le sonde con il nome dei crawler sono **l'ultima fase**, non la prima: se un WAF le segna, una scansione fatta dopo tornerebbe piena di 403 che non raccontano niente del sito.

Lo script stampa già a schermo l'esito del controllo sui crawler, uno per uno: è la parte che di solito vale la riunione.

## 3. Misura la velocità

```bash
python3 -I <percorso della skill>/scripts/misura_velocita.py https://www.esempio.com raw/audit-tecnico/<data>
```

È separata dalla scansione perché la velocità cambia di giorno in giorno mentre la struttura no: si rimisura senza riscansionare.

## 4. Analizza

```bash
python3 -I <percorso della skill>/scripts/analizza_audit.py raw/audit-tecnico/<data>
```

Scrive `risultati.json` (gli indicatori, con spiegazione e conseguenza di ognuno), `azioni.json` (quelle che vanno in dashboard) ed `elenchi.json` (gli elenchi **per intero**, divisi in colonne, per il foglio di lavoro: `risultati.json` si ferma a 200 righe per indicatore, che è quanto serve alla dashboard). Stampa i gruppi e tutto ciò che non è in linea.

**Il punteggio di sintesi.** `risultati.json` contiene anche `sommario`: un numero da 0 a 100 («Prontezza tecnica»), i temi che lo compongono e il tema che costa di più. La dashboard lo mostra in cima, con un quadrante e le barre dei temi.

Due cose da sapere prima di discuterlo con un cliente:

- **Il punteggio sta sugli otto temi, non sulle singole verifiche.** I dati strutturati sono misurati da una verifica per sezione del sito: contate una per una peserebbero quanto tutto il resto, e un problema solo deciderebbe il voto. Su un sito di prova le 33 verifiche contate a una a una davano 46, contate per tema danno 66. La seconda dice quanti problemi **diversi** ci sono.
- **Un punteggio solo, non uno SEO e uno AEO.** Provati sugli stessi dati davano 46 e 44: due punti, perché 22 verifiche su 33 valgono per tutti e due i mondi. Due quadranti costruiti sugli stessi dati si muovono sempre insieme, e la differenza che resta qualcuno la legge come un giudizio. Dove stanno i problemi lo dice `sommario.mondi`, che conta quanti indicatori aperti toccano solo gli assistenti, solo i motori o entrambi.

I pesi sono in `TEMI_PUNTEGGIO`, in testa a `analizza_audit.py`. Sono una scelta, non una misura: si discutono una volta e poi si lasciano fermi, perché un punteggio serve solo se confrontato con sé stesso alla scansione dopo. Una verifica nuova che nessuno classifica in `tema_di()` **resta fuori dal punteggio** e finisce in `sommario.non_pesati`: così il voto non si muove da solo.

**Il controllo che lo script non può fare da solo.** Se l'indicatore «Contenuto leggibile senza JavaScript» non è in linea, aprile davvero: prendi due o tre delle pagine elencate, aprile nel browser (che il JavaScript lo esegue) e confronta con quello che ha visto lo script. Se il testo c'è nel browser e non nell'HTML grezzo, il problema è confermato ed è il titolo di tutto l'audit. Se invece la pagina è magra anche nel browser, è una pagina povera di contenuto: un problema diverso, che si risolve scrivendo.

## 5. Pubblica la dashboard

**Prima volta** (nessun `audit_url` in `analisi/audit-tecnico/config.json`):
- copia `assets/audit.html` in `analisi/audit-tecnico/index.html`, sostituendo `{{TITOLO}}` con `Audit tecnico <dominio>`;
- pubblica con il tool Artifact:
  - `file_path`: `analisi/audit-tecnico/index.html`;
  - `files`: `{"risultati.json": "raw/audit-tecnico/<data>/risultati.json"}`;
  - `icon`: `"shield"`;
  - una `description` di una frase;
- salva l'URL in `config.json`.

Niente `capabilities`: è una fotografia da leggere, non un posto dove si decide. Le decisioni stanno nella dashboard SEO e AEO.

**Le volte successive:** leggi la pagina con `Artifact` `action: "read"` sull'URL, poi pubblica con `url` = `audit_url`, lo stesso `file_path` e lo stesso `files`, senza `icon`.

Ogni indicatore si apre con un clic e mostra **cosa misura** e **cosa comporta**, scritti per chi non è tecnico. Il testo sta in `analizza_audit.py`, non nella pagina: si corregge lì ed è uguale per tutti i clienti.

## 6. Porta le azioni nella dashboard SEO e AEO

```bash
python3 -I <percorso di ie-aeo-dashboard>/scripts/prepara_dashboard.py raw/gsc/<data> \
    --cliente "<Nome>" --audit-tecnico raw/audit-tecnico/<data> [altre fonti…]
```

Le azioni entrano nel piano di lavoro con id `sa-ie-<verifica>`, categoria tecnica, accanto a quelle di Semrush e Ahrefs, e vengono pesate con le impressioni di Search Console delle pagine coinvolte: un problema su pagine che nessuno visita resta in fondo. Gli id non dipendono dalla data, quindi le decisioni del team restano attaccate da un audit all'altro.

## 7. Consegna

In chat:
- il link della dashboard;
- i gruppi con il loro stato, e i due o tre indicatori che contano davvero;
- cosa è rimasto fuori: pagine non scansionate rispetto alla sitemap, dati di campo assenti, verifiche saltate con `--solo-aeo`;
- le azioni finite in dashboard.

**Il tono.** La dashboard la legge il cliente. Si scrive cosa si può migliorare e cosa comporta, non cosa è stato sbagliato: molte di queste cose le ha fatte un fornitore che magari è ancora al tavolo. Gli indicatori in linea si mostrano quanto quelli fuori — un audit che elenca solo problemi non è una diagnosi, è una requisitoria.

## 8. Proponi le slide e il foglio

Dopo aver consegnato la dashboard, **proponilo**, in una riga: dalla stessa analisi puoi
preparare la presentazione di restituzione e il foglio con tutti gli URL da correggere.
Non partire senza un sì: sono file che finiscono nella cartella del cliente.

Se il consulente accetta:

1. **La cartella del cliente su Drive.** Leggi `drive_folder_id` da
   `analisi/audit-tecnico/config.json`. Se non c'è, **chiedi l'URL della cartella di
   progetto** e ricavane l'id; salvalo, così non lo chiedi più.
2. **La sottocartella.** Cerca `Audit Tecnico` dentro quella cartella; se manca, creala
   (`create_file`, mimeType `application/vnd.google-apps.folder`). Salva `audit_folder_id`.
3. **Il foglio, per primo.** `Audit tecnico <Cliente> <AAAA-MM-GG> — URL`, dagli
   `elenchi.json`. Prima del deck, perché l'ultima slide ne porta il link.
4. **Il deck.** Copia il master in quella cartella, intitolato
   `Audit tecnico <Cliente> <AAAA-MM-GG>`, poi montalo come dice `references/slide.md`.
   Due cose le chiedi al consulente, perché non stanno in nessun file: **chi fa cosa** per
   la slide «Prossimi passi», e **i suoi contatti** per la slide di chiusura.
5. **Rileggi il deck e cerca `{{`, note del relatore comprese.** Se ne resta
   uno, non è finita.
6. **Cerca il cliente precedente.** Il master nasce da un deck di vendita di un altro
   cliente: la pulizia è stata fatta una volta, ma se qualcuno ha rimesso mano al template
   nel frattempo, il residuo arriva al cliente. Costa una ricerca.
7. Salva `deck_id` e `sheet_id` in `config.json` e dai i due link in chat.

**Un deck nuovo a ogni audit**, datato. La dashboard si aggiorna sul posto, il deck no:
quello mostrato al cliente a marzo deve continuare a dire quello che diceva a marzo.

Commit e push di `raw/audit-tecnico/<data>/` e `analisi/audit-tecnico/` solo con l'ok del consulente.
