# Accesso a Search Console

Per estrarre i dati servono due cose: le credenziali dell'agenzia, uguali per tutti i clienti, e l'accesso del cliente alla sua proprietà.

## 1. Credenziali (una volta per consulente)

Nel progetto Google Cloud dell'agenzia deve essere attiva la *Google Search Console API*. Poi scegli uno dei due modi.

| Modo | Quando | Cosa scaricare |
|---|---|---|
| **Account di servizio** | Estrazioni periodiche, anche automatiche; un solo indirizzo da far aggiungere a tutti i clienti | La chiave JSON dell'account di servizio (`...@...iam.gserviceaccount.com`) |
| **Account Google personale** | Se le policy di Google Cloud non permettono di creare chiavi, o il cliente preferisce dare accesso a una persona | Il JSON di un client OAuth di tipo *Desktop app*. Al primo avvio si apre il browser per il consenso |

Salva il JSON in `~/.config/ie-aeo-gsc/credenziali.json`, **mai nel repo del cliente**. Per un percorso diverso usa `--credenziali` o la variabile `GSC_CREDENZIALI`. Il token OAuth viene salvato in `~/.config/ie-aeo-gsc/token.json`.

Installa le librerie una volta:

```bash
pip3 install -r <percorso della skill>/scripts/requirements.txt
```

Il controllo finale è il comando `proprieta`: elenca le proprietà visibili e il livello di permesso.

## 2. Cosa chiedere al cliente

Testo pronto da adattare, sostituendo l'indirizzo con quello dell'account di servizio o del consulente:

> Ciao [nome],
> per l'analisi SEO/AEO dei contenuti abbiamo bisogno di leggere i dati di Google Search Console e Google Analytics del vostro sito. Ci servono:
>
> 1. **Accesso a Google Search Console.** In *Impostazioni → Utenti e autorizzazioni → Aggiungi utente*, aggiungete `<indirizzo>` con autorizzazione **"Con limitazioni"** (solo lettura). Solo il proprietario della proprietà può aggiungere utenti.
> 2. **Quali proprietà esistono.** È configurata una proprietà di dominio o una per prefisso URL? Ci sono proprietà separate per lingue, paesi o altri siti del gruppo che è utile includere?
> 3. **Accesso a Google Analytics 4** con ruolo **"Visualizzatore"**, da *Amministrazione → Gestione accessi alla proprietà*. Serve per misurare le visite che arrivano da ChatGPT, Perplexity e gli altri assistenti AI, che Search Console non mostra.
> 4. **Cambiamenti al sito negli ultimi 16 mesi:** nuove versioni del sito, cambi di URL, redirect, nuove lingue. Servono a leggere correttamente gli andamenti.
> 5. **Facoltativo:** se usate Bing Webmaster Tools, l'accesso anche lì.
>
> Grazie!

Le risposte ai punti 2 e 4 sono informazioni sul cliente: registrale in `domande-aperte.md` come risolte, con la fonte.

## Problemi frequenti

| Messaggio | Causa | Cosa fare |
|---|---|---|
| `Nessuna proprietà visibile` | L'indirizzo non è stato aggiunto, o è stato aggiunto a un'altra proprietà | Verifica con il cliente l'indirizzo esatto e la proprietà |
| `403 ... User does not have sufficient permission` | Il valore di `--sito` non coincide con la proprietà | Copia il nome esatto dal comando `proprieta`, compreso `sc-domain:` o la `/` finale |
| `403 ... API has not been used in project` | API non attiva nel progetto Google Cloud | Attiva la *Google Search Console API* |
| Avvisi `FutureWarning` su Python 3.9 | Python di sistema di macOS | Non bloccano; per toglierli usa Python 3.11 o successivo |
