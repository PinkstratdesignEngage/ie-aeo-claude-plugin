# Accesso a Google Analytics 4

Servono tre cose: l'API attiva nel progetto Google Cloud dell'agenzia, le credenziali del consulente (le stesse di Search Console) e l'accesso del cliente alla sua proprietà GA4.

## 1. API nel progetto Google Cloud (una volta)

Il comando `verifica` dice se mancano e stampa il link diretto per attivarle.

Nel progetto Google Cloud delle credenziali di `ie-aeo-search-console` attiva:
- **Google Analytics Data API**: legge i report;
- **Google Analytics Admin API**: elenca le proprietà visibili (comando `proprieta`).

Da *API e servizi → Libreria*, cercandole per nome. Se il progetto usa un client OAuth in modalità di test, l'account Google del consulente deve essere tra gli utenti di test della *schermata di consenso OAuth*.

## 2. Credenziali (una volta per consulente)

Sono quelle di Search Console: `~/.config/ie-aeo-gsc/credenziali.json` (o `--credenziali`, o la variabile `GA4_CREDENZIALI`). Mai nel repo del cliente.

| Tipo | Cosa succede |
|---|---|
| **Client OAuth "Desktop app"** (account Google personale) | Al primo `proprieta` si apre il browser: accedi con l'account a cui il cliente ha dato accesso e accetta la lettura di Google Analytics. Il token va in `~/.config/ie-aeo-gsc/token-ga4.json`, separato da quello di Search Console |
| **Account di servizio** | Nessun browser: è l'indirizzo `...@...iam.gserviceaccount.com` che il cliente deve aggiungere alla proprietà |

Librerie, una volta: `pip3 install -r <percorso della skill>/scripts/requirements.txt`.

## 3. Accesso del cliente (una volta per cliente)

Il cliente aggiunge l'account del consulente, o l'account di servizio, alla sua proprietà GA4:

> Ciao [nome],
> per misurare le visite che arrivano al vostro sito da ChatGPT, Perplexity, Gemini e dagli altri assistenti AI abbiamo bisogno di leggere i dati di Google Analytics 4. In **Amministrazione → Gestione accessi alla proprietà → + → Aggiungi utenti**, aggiungete `<indirizzo>` con ruolo **Visualizzatore** (solo lettura). Serve un utente con ruolo Amministratore sulla proprietà.
> Se avete più proprietà GA4 (per paese, lingua o sito), diteci quali sono quelle del sito principale.
> Grazie!

Poi, dalla radice del repo del cliente:

```bash
python3 <percorso della skill>/scripts/estrai_ga4.py trova --dominio <dominio del cliente>
```

Il comando trova la proprietà che misura davvero il sito, guardando le visite e non il nome, e propone il contenuto di `analisi/ga4/config.json`. Il percorso completo, passo per passo, è nel "Collegamento guidato" della SKILL.md.

## Problemi frequenti

| Messaggio | Causa | Cosa fare |
|---|---|---|
| `Nessuna proprietà GA4 visibile` | Il cliente non ha ancora aggiunto l'indirizzo, o l'ha aggiunto a un'altra proprietà o a un altro account Google | Verifica con il cliente l'indirizzo esatto e la proprietà |
| `403 ... has not been used in project` o `is disabled` | API non attiva nel progetto Google Cloud | Attiva le due API del punto 1 |
| `403 ... does not have sufficient permissions for this property` | L'id della proprietà è sbagliato o l'accesso è a un'altra proprietà | Copia l'id dal comando `proprieta` |
| `access_denied` nel browser | L'account non è tra gli utenti di test della schermata di consenso | Aggiungilo nel progetto Google Cloud |
| Token scaduto o revocato | Il consenso è stato tolto o è passato troppo tempo | Cancella `~/.config/ie-aeo-gsc/token-ga4.json` e rilancia |
