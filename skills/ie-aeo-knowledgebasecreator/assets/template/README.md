# {{CLIENTE}} Brain

La knowledge base di {{CLIENTE}} per il progetto AEO (Answer Engine Optimization) curato dall'agenzia.

Qui teniamo, in un posto solo, quello che serve per scrivere contenuti su {{CLIENTE}} in modo corretto e coerente: chi è l'azienda, a chi si rivolge, cosa offre, come parla e su quali temi vuole farsi trovare dai motori di ricerca e dagli assistenti AI (ChatGPT, Perplexity, Google AI Overview).

La usano sia le persone (consulenti dell'agenzia, team marketing {{CLIENTE}}) sia Claude, che la legge per creare e revisionare contenuti.

## Come è organizzata

| Cartella | Cosa contiene |
|---|---|
| [01-azienda](01-azienda/) | Chi è {{CLIENTE}}, posizionamento, mercato e competitor |
| [02-audience](02-audience/) | ICP e buyer personas per il mercato di riferimento ({{MERCATO}}) |
| [03-offerta](03-offerta/) | Prodotti, servizi e tecnologie |
| [04-brand-voice](04-brand-voice/) | Tone of voice, messaggi chiave, glossario, esempi annotati |
| [05-content-pillars](05-content-pillars/) | I temi su cui produciamo contenuti, a partire da {{PILLAR}} |
| [fonti](fonti/) | Registro delle fonti citate nei file |
| `analisi/` | Analisi dei dati, per esempio i report mensili di Google Search Console (si crea alla prima analisi) |
| [domande-aperte.md](domande-aperte.md) | Cosa resta da chiarire o validare con {{CLIENTE}} |

Se è la prima volta, leggi in quest'ordine: `01-azienda/profilo.md`, `02-audience/icp.md`, `03-offerta/panoramica.md`, `04-brand-voice/tone-of-voice.md`.

## Regole del gioco

- **Ogni informazione ha una fonte.** I file citano le fonti con un codice tra parentesi quadre, ad esempio `[S03]`, che rimanda al [registro fonti](fonti/registro-fonti.md).
- **Quello che non è confermato si vede.** Le informazioni dedotte o da verificare sono marcate `[DA VALIDARE]` e compaiono in [domande-aperte.md](domande-aperte.md).
- **Ogni file dichiara il suo stato** nel frontmatter: `bozza`, `da-validare` o `validato`. Un file diventa `validato` solo dopo la revisione di {{CLIENTE}}.
- **File brevi, un argomento per file.** Meglio aggiungere un file nuovo che allungarne uno esistente.

## Come contribuire

Prima di iniziare, scarica le modifiche dei colleghi: `git pull --rebase`. Con Claude Code il controllo è automatico: all'avvio e dopo un'ora di pausa Claude verifica l'allineamento con GitLab e, se serve, propone di aggiornare.

Il repo attiva anche il plugin IE-AEO (skill per knowledge base e contenuti). Alla prima apertura in Claude Code viene proposto di installarlo; poi si aggiorna da solo a ogni avvio. Serve l'accesso al progetto GitLab `aeo/claudeplugin/IE-AEO` su `gitlab.example.com`.

1. Modifica o aggiungi il file nella cartella giusta, mantenendo il frontmatter.
2. Se aggiungi una fonte nuova, registrala in `fonti/registro-fonti.md` e citane il codice.
3. Aggiorna `ultimo_aggiornamento` e, se serve, `stato`.
4. Apri una merge request su GitLab (`glab mr create`) descrivendo cosa è cambiato e su quale fonte si basa.
