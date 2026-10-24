# Audit razze e sottorazze — 24 ottobre 2026

> Diagnostica, non sorgente canonica delle regole. Il contenuto di questo file
> non include trascrizioni dei manuali, immagini, PDF o dati di accesso.
> Origine dei numeri: query live `public.private_reference_records`.

## Contatori effettivi

| Criterio | Record |
|---|---:|
| Schede razze + sottorazze | **148** |
| Razze | **93** |
| Sottorazze | **55** |
| `review_status = verified` (revisione generale) | **148** |
| `ai_review_status = verified` (controllo indipendente AI) | **86** |
| Verifiche AI ancora `pending` | **62** |
| Testo originale OCR mancante nel record (`source_full_text`) | **58** |
| Taglia, velocità, lingue o array dei tratti mancanti | **0** |
| Duplicati `source_key + reference_type + normalized_name` | **0** |
| Sottorazze prive di riferimento alla razza madre | **0** |

**Stato complessivo: copertura delle opzioni identificate molto avanzata,
ma convalida fonte-per-fonte NON completa.** L'assenza di `pending` nella
revisione generale **non** equivale a `fully_validated = true`.

Il report amministrativo di `backend/verify_reference_library.py` ora
include `race_catalog_validation`, che risulta `fully_validated=false`
finché mancano OCR originali, verifiche AI, riferimenti o unicità. La
revisione ordinaria delle carte rimane invariata; non sono cambiati
autenticazione, RLS né servizi di produzione.

## Copertura per pubblicazione

| Manuale nel database | Razze | Sottorazze | Nota |
|---|---:|---:|---|
| Manuale del Giocatore italiano 2014 | 9 | 9 | Elfo Alto e Dragonide ricostruiti con controfonti; 2 OCR originali mancanti |
| Manuale del Giocatore spagnolo 2014 | 9 | 8 | Trascrizioni originali e traduzioni già verificate |
| Eberron: Rising from the Last War 2019 | 8 | 16 | 12 Marchi del Drago e 4 Morfici. Cangiante riclassificato dal frammento italiano completo |
| Monsters of the Multiverse 2022 | 33 | 0 | Raccolta originale verificata |
| Guildmasters' Guide to Ravnica 2018 | 6 | 0 | Centauro, Goblin, Ibrido Simic, Loxodon, Minotauro, Vedalken |
| Mythic Odysseys of Theros 2020 | 2 | 0 | Leonin e Satiro; Centauro, Minotauro e Tritone sono ristampe equivalenti collegate alle schede preesistenti |
| Volo's Guide to Monsters 2016 | 13 | 3 | Razze giocabili e tre sottorazze Aasimar; errata applicate |
| Mordenkainen's Tome of Foes 2018 | 1 | 15 | Gith + 2 sottorazze; 8 Tiefling, 3 elfiche, Duergar, Gnomo delle Profondità |
| Explorer's Guide to Wildemount 2020 | 1 | 4 | Orco di Exandria; 2 Dragonidi, Elfo Pallido, Halfling Lotusden |
| Fizban's Treasury of Dragons 2021 | 3 | 0 | Varianti draconiche Cromatica, Gemmata, Metallica |
| Van Richten's Guide to Ravenloft 2021 | 3 | 0 | Dhampir, Sangue Strigo, Rinato |
| Dragonlance: Shadow of the Dragon Queen 2022 | 1 | 0 | Kender |
| Strixhaven: A Curriculum of Chaos 2021 | 1 | 0 | Owlin |
| Acquisitions Incorporated 2019 | 1 | 0 | Verdan |
| Locathah Rising 2019 | 1 | 0 | Locathah |
| The Tortle Package 2017 | 1 | 0 | Tortle legacy 2017, distinta da MPMM |

**Attenzione:** `source_refs` è un indice della provenienza, non il
contenuto del testo fonte. Le schede nuove possono essere sintesi delle
regole confrontate con fonti dell'edizione, pur avendo `review_status=verified`.
La certificazione AI e la fonte testuale originale restano richieste per
completamento totale.

## Ristampe senza duplicati

Nella fonte Theros compaiono cinque popoli non umani: Leonin, Satiro, Centauro,
Minotauro, Tritone. I tre ultimi **non** sono schede aggiuntive: Centauro e
Minotauro ripropongono Ravnica; Tritone coincide con le regole di Volo dopo
errata (tra cui visione scura). A questi tre record sono stati aggiunti
riferimenti `also_published_in` a Theros, senza creare altre righe.

- [D&D Beyond — Sommario ufficiale Theros](https://www.dndbeyond.com/sources/dnd/moot)
- [D&D Beyond — Discussione regole di Theros](https://www.dndbeyond.com/forums/d-d-beyond-general/release-issues-support/69382-mythic-odysseys-of-theros-issues-and-support)
- [D&D Beyond — Volo Errata](https://www.dndbeyond.com/sources/dnd/sae/volos-guide-to-monsters)
- [D&D Beyond — Eberron Errata](https://www.dndbeyond.com/sources/dnd/sae/eberron-rising-from-the-last-war)

## Rimanenze vincolanti, prima di proclamare tutto completo

1. **62 verifiche AI** ancora pendenti; controllare meccaniche e provenienza
   individualmente, senza cambiare semplicemente lo stato nel database.
2. **58 schede senza `source_full_text` e checksum originale**; recuperare la
   sezione corretta dalle versioni realmente disponibili nei PDF R2, in
   gruppi OCR di massimo 12 pagine, senza pubblicare trascrizioni su GitHub.
   Dove il PDF non consente verifica, dichiarare la lacuna.
3. Controllare versioni e traduzioni italiane — non sovrascrivere regole
   legacy 2016–2020 con MPMM 2022 né bozze Unearthed Arcana.
4. Continuare a controllare copertura quando nuovi manuali vengono inseriti.
   `Boo's Astral Menagerie` è un bestiario: non equivale ad
   `Astral Adventurer's Guide` con le sei razze Spelljammer; non attribuire
   a un file la sezione di un altro PDF.
5. Non fare merge di `develop` su `main` né attivare una release prima
   delle validazioni di rilascio concordate.

## Query finale di verifica (sola lettura)

```sql
SELECT reference_type, review_status, ai_review_status,
       count(*) AS schede,
       count(*) FILTER (WHERE coalesce(source_full_text, '') = '') AS ocr_mancanti
FROM public.private_reference_records
WHERE reference_type IN ('race', 'subrace')
GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;

SELECT source_key, reference_type, normalized_name, count(*) AS duplicati
FROM public.private_reference_records
WHERE reference_type IN ('race', 'subrace')
GROUP BY 1, 2, 3 HAVING count(*) > 1;
```
