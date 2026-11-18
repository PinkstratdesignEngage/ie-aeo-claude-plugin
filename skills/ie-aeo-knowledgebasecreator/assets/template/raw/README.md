# raw: i materiali originali

Qui ci sono i documenti originali usati per costruire la knowledge base, o disponibili per farlo. Servono a due cose:
- verificare una fonte senza andarla a cercare su Drive o sul sito;
- riprendere il lavoro sui materiali non ancora analizzati.

L'elenco completo, con stato e dimensioni, è in [indice.md](indice.md). Si rigenera con lo script `indice_raw.py` della skill IE-AEO.

## Convenzioni

- **`-analizzato` prima dell'estensione**: il materiale è stato letto per la knowledge base, anche se non ha aggiunto informazioni, per esempio `Profilo aziendale-analizzato.pdf`. Senza suffisso: è disponibile ma non ancora analizzato, per esempio le versioni inglesi dei cataloghi.
- **`.link.md`**: segnaposto per un materiale che non sta nel repo. Contiene il link all'originale e il motivo:
  - file oltre i limiti di dimensione del repo (50 MB);
  - video o cartelle di foto;
  - file oltre il limite di 10 MB del connettore Drive;
  - contenuto riservato, come il transcript integrale delle riunioni.
- **Pagine del sito**: sono salvate come copia di testo (`sito/<percorso-della-pagina>-analizzato.md`, senza suffisso se non ancora lette), con URL e data di salvataggio in testa. I `__` nel nome sostituiscono le `/` dell'URL.

## Cartelle

| Cartella | Contenuto | Codici fonte |
|---|---|---|
| `sito/` | Copie di testo delle pagine del sito del cliente lette | S |
| `drive/` | Documenti della cartella Drive di progetto, con la stessa organizzazione per argomento | D |
| `riunioni/` | Segnaposto dei transcript delle riunioni | M |
| `assessment/` | Assessment e analisi preliminari dell'agenzia | — |
| `esterni/` | Copie di fonti esterne (articoli, studi) | E |
| `gsc/` | Estrazioni di Google Search Console, una cartella per data (`AAAA-MM-GG/`), fatte con la skill `ie-aeo-search-console` | G |
| `semrush/` | Estrazioni di Semrush, una cartella per data (`AAAA-MM-GG/`), con gli originali in `originali/`, fatte con la skill `ie-aeo-semrush` | X |
| `hubspot-aeo/` | Download di HubSpot AEO, una cartella per data (`AAAA-MM-GG/`), fatti con la skill `ie-aeo-hubspot-aeo` | H |

## Come aggiungere un materiale

1. Mettilo nella cartella giusta, con il nome originale.
2. Quando lo analizzi, aggiungi `-analizzato` al nome e registralo in [registro-fonti.md](../fonti/registro-fonti.md). Vale anche quando il materiale non ha aggiunto nulla: nel registro delle fonti si scrive "letto, nessuna informazione nuova".
3. Rigenera l'indice:

   ```
   python3 <percorso-skill>/scripts/indice_raw.py .
   ```
