# Modelli Schema.org

Ogni contenuto si consegna con il suo markup in JSON-LD, da inserire nella pagina (in HubSpot: nell'HTML della pagina o del modulo). Lo schema descrive le stesse cose del testo, con gli stessi dati: niente informazioni che il lettore non vede.

## Regole

- **Dati.** Prendi i dati dalla knowledge base. Logo, URL dei profili social, URL delle pagine: se non sono nella knowledge base, usa il segnaposto `"[DATO DA FORNIRE: ...]"` e segnalalo.
- **Immagine del prodotto.** Puoi usare l'URL di un'immagine letta sulla pagina del prodotto, segnalandolo, perché il cliente confermi quale immagine ufficiale usare.
- **Più tipi in una pagina.** Usa un unico blocco `<script type="application/ld+json">` con `@graph`, e collega le entità con `@id`, per esempio `"@id": "https://www.cliente.com/#organization"`.
- **Lingua.** `inLanguage` è "it-IT" o "en-GB" secondo la lingua del contenuto.
- **FAQPage.** Google mostra i risultati arricchiti delle FAQ solo per pochi tipi di siti. Il markup resta utile perché rende domande e risposte leggibili dalle macchine. Le domande e le risposte nello schema devono essere identiche a quelle sulla pagina: controllalo con `python3 scripts/verifica_faq_schema.py <file>` (percorso relativo a `condivisi/`).
- **Verifica.** Il JSON deve essere valido: controllalo con `python3 -m json.tool`. Ricorda al consulente di provarlo sul validatore di Schema.org prima della pubblicazione.

## Organization (da includere in ogni pagina, o una volta a livello di sito)

```json
{
  "@type": "Organization",
  "@id": "https://www.cliente.com/#organization",
  "name": "Nome del cliente",
  "url": "https://www.cliente.com/",
  "logo": "[DATO DA FORNIRE: URL del logo]",
  "foundingDate": "AAAA",
  "address": {"@type": "PostalAddress", "streetAddress": "", "postalCode": "", "addressLocality": "", "addressCountry": "IT"},
  "sameAs": ["[DATO DA FORNIRE: LinkedIn]", "[DATO DA FORNIRE: YouTube]"]
}
```

## BlogPosting

```json
{
  "@type": "BlogPosting",
  "@id": "https://www.cliente.com/blog/slug/#article",
  "headline": "H1 dell'articolo, massimo 110 caratteri",
  "description": "Meta description",
  "inLanguage": "it-IT",
  "articleSection": "Categoria del blog",
  "keywords": ["tema", "prodotto", "tecnologia"],
  "datePublished": "AAAA-MM-GG",
  "dateModified": "AAAA-MM-GG",
  "author": {"@id": "https://www.cliente.com/#organization"},
  "publisher": {"@id": "https://www.cliente.com/#organization"},
  "mainEntityOfPage": "https://www.cliente.com/blog/slug/",
  "about": [{"@type": "Thing", "name": "Tema principale"}],
  "mentions": [{"@type": "Product", "name": "NOME PRODOTTO", "url": "https://www.cliente.com/prodotti/slug"}]
}
```

Cosa mettere in `mentions`:
- **prodotti** citati: `Product`, con nome e URL;
- **tecnologie** proprietarie: `Product`, se si vendono o si scelgono come opzione, altrimenti `Thing`; con URL se hanno una pagina;
- **clienti** citati come caso (per esempio una catena di supermercati): `Organization`, solo con nome e URL pubblico del caso.

Non mettere in `mentions` cose che il testo cita solo di passaggio.

Se l'autore è una persona del cliente, usa `{"@type": "Person", "name": "", "jobTitle": "", "worksFor": {"@id": "...#organization"}}`: rafforza l'autorevolezza (E-E-A-T).

## FAQPage

```json
{
  "@type": "FAQPage",
  "@id": "https://www.cliente.com/pagina/#faq",
  "mainEntity": [
    {"@type": "Question", "name": "Domanda?", "acceptedAnswer": {"@type": "Answer", "text": "Risposta identica a quella sulla pagina."}}
  ]
}
```

## Product (pagine prodotto e FAQ prodotto)

```json
{
  "@type": "Product",
  "@id": "https://www.cliente.com/prodotti/slug/#product",
  "name": "NOME PRODOTTO",
  "description": "Descrizione breve, coerente con la pagina",
  "brand": {"@type": "Brand", "name": "Nome del cliente"},
  "manufacturer": {"@id": "https://www.cliente.com/#organization"},
  "category": "Tipologia, es. Banchi refrigerati verticali",
  "url": "https://www.cliente.com/prodotti/slug",
  "image": "URL di un'immagine della pagina prodotto, da confermare, oppure [DATO DA FORNIRE: URL immagine]",
  "additionalProperty": [
    {"@type": "PropertyValue", "name": "Temperatura di conservazione", "value": "-22/-25", "unitCode": "CEL"},
    {"@type": "PropertyValue", "name": "Lunghezza", "minValue": 1562, "maxValue": 3905, "unitCode": "MMT"}
  ],
  "hasEnergyConsumptionDetails": {
    "@type": "EnergyConsumptionDetails",
    "hasEnergyEfficiencyCategory": "https://schema.org/EUEnergyEfficiencyCategoryD",
    "energyEfficiencyScaleMin": "https://schema.org/EUEnergyEfficiencyCategoryG",
    "energyEfficiencyScaleMax": "https://schema.org/EUEnergyEfficiencyCategoryA"
  }
}
```

Note:
- **Classe energetica.** `hasEnergyConsumptionDetails` va solo se la classe è certa per la configurazione descritta. Se cambia per versione, descrivi le versioni con `ProductModel` collegati tramite `isVariantOf`, oppure ometti la classe.
- **Prezzo.** Non aggiungere `offers` senza un prezzo pubblico: per prodotti B2B su preventivo si omette.
- **Codici UN/CEFACT di `unitCode`:** CEL °C, MMT mm, CMT cm, MTK m², KWT kW.

## Article (case study)

Come `BlogPosting` ma con `"@type": "Article"`. In più:
- `about` con il cliente del caso come `Organization`;
- `mentions` con prodotti e tecnologie;
- `contentLocation` con un `Place` e il suo indirizzo, se pubblico.

## NewsArticle (news e comunicati)

Come `BlogPosting` ma con `"@type": "NewsArticle"`. In più:
- `dateline` con il luogo della notizia, se il testo lo dice;
- `about` con l'organizzazione o l'evento di cui parla la news;
- per un'intervista, la persona intervistata in `mentions` o in `about`, come `Person` con `name`, `jobTitle` e `worksFor`. L'autore resta l'organizzazione che pubblica, salvo che la news sia firmata.

Una società del gruppo del cliente si descrive come `Organization` collegata alla capogruppo:

```json
{
  "@type": "Organization",
  "@id": "https://www.cliente.com/#societa-slug",
  "name": "Nome della società",
  "url": "https://www.societa.com/",
  "foundingDate": "AAAA",
  "description": "Cosa fa, con la formula della knowledge base",
  "parentOrganization": {"@id": "https://www.cliente.com/#organization"}
}
```

Usa l'URL del sito della società solo se è nella knowledge base.

## Traduzioni

La versione in un'altra lingua ha lo stesso schema del master, tradotto, con:
- `inLanguage` con la variante della lingua, per esempio `"en-GB"`;
- `@id` con il suo URL;
- `translationOfWork` con l'`@id` del contenuto master: `"translationOfWork": {"@id": "https://www.cliente.com/it/blog/slug/#article"}`.

Nel master si aggiunge `workTranslation` con l'`@id` della traduzione, quando la traduzione è online. Le FAQ della traduzione devono essere identiche al suo testo: controllale con lo script.

## DefinedTerm e DefinedTermSet (glossario)

```json
{
  "@type": "DefinedTerm",
  "@id": "https://www.cliente.com/glossario/termine/#term",
  "name": "Termine",
  "description": "Definizione breve, identica a quella sulla pagina",
  "inDefinedTermSet": {"@type": "DefinedTermSet", "@id": "https://www.cliente.com/glossario/#set", "name": "Glossario di Nome cliente"}
}
```
