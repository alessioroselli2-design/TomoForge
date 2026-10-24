# Audit di copertura razze e sottorazze — 2026-10-24

> **Stato**: inventario diagnostico; non è una sorgente canonica di regole.
> I riferimenti ai manuali sono nomi di file già presenti nel database TomoForge.
> Non contiene pagine OCR, testi privati dei manuali o credenziali.

## Esito della verifica sul database

Query su `public.private_reference_records` dopo la correzione del Manuale del Giocatore italiano:

- `race`: 58 record, tutti `verified`;
- `subrace`: 22 record, tutti `verified`;
- totale: **80 record**;
- duplicati per (`source_key`, `reference_type`, `normalized_name`): **0**.

Le nuove schede `Dragonide` e `Elfo Alto` sono state aggiunte al
`Manuale_del_giocatore__1787259882002.pdf` come sintesi meccaniche italiane
2014, con fonti incrociate e note di provenienza che esplicitano la mancanza
del testo integrale OCR italiano. La fonte italiana p. 32 per Dragonide è
**contesto narrativo**, non evidenza della totalità delle regole. Non inferire
da `review_status='verified'` la presenza di OCR italiano originale.

## Manuali con bestiario ma senza razze/sottorazze classificate

| `source_key` | Mostri | Razze/sottorazze | Voci razziali da verificare nel manuale |
|---|---:|---:|---|
| `Guildmasters’ Guide to Ravnica.2 .pdf` | 78 | 0 | Loxodon, Ibrido Simic, Vedalken; distinguere eventuali varianti di Centauro/Goblin/Minotauro dalle altre fonti |
| `953338587-Mythic-Odysseys-of-Theros.pdf` | 49 | 0 | Leonin; controllare varianti di Satiro, Minotauro, Centauro e Tritone |
| `950799222-D-D-5e-Il-Tesoro-dei-Draghi-di-Fizban.pdf` | 73 | 0 | Dragonide Cromatico, Dragonide delle Gemme, Dragonide Metallico (varianti delle regole, non copie del Dragonide PHB 2014) |
| `682072052-5e-DnD-Dragonlance-Shadow-of-the-Dragon-Queen-Mong-IcYPD5.pdf` | 28 | 0 | Kender |

La lista è un **insieme minimo di lacune note**, non la certificazione che
questi libri o l'intera libreria abbiano solo tali lacune. Sorgenti ufficiali
per la presenza delle opzioni, **non** per attribuire campi numerici:

- [Ravnica — indice ufficiale](https://www.dndbeyond.com/sources/dnd/ggtr)
- [Theros — indice ufficiale](https://www.dndbeyond.com/sources/dnd/moot)
- [Fizban — indice ufficiale](https://www.dndbeyond.com/sources/dnd/ftod)
- [Dragonlance — descrizione ufficiale Kender](https://marketplace.dndbeyond.com/settings/dragonlance-shadow-of-the-dragon-queen)

## Recupero fail-closed

1. Verificare accessibilità e integrità del PDF dell'utente, tramite il suo
   storage R2 nel processo backend autorizzato; non caricare i PDF su GitHub.
2. Individuare le pagine effettive delle opzioni razziali nella **stessa
   versione** del manuale presente in R2. Mai supporre numeri di pagina da
   versioni online, indici o record di altre edizioni.
3. Estrarre testo con finestre OCR di **al massimo 12 pagine**, applicando i
   controlli del repository su provenienza e continuità delle sezioni.
4. Registrare prima le voci candidate con evidenza originale. Se tratti,
   conversioni in metri, prerequisiti, sottorazze o varianti divergono o sono
   incompleti, mantenere `pending`/`needs_review` finché non risolti.
5. Distinguere voci con lo stesso nome ma **meccaniche diverse per manuale**;
   evitare duplicazioni *nella stessa versione e fonte*.
6. Solo dopo verifica testuale completa e confronto dei campi, applicare
   `verified`. Non riempire attributi dal solo nome o da sommari online.
7. Eseguire query di controllo e ripetere l'audit manuale per manuale.

## Query di controllo (sola lettura)

```sql
SELECT source_key, reference_type, review_status, count(*) AS numero
FROM public.private_reference_records
WHERE reference_type IN ('race', 'subrace')
GROUP BY source_key, reference_type, review_status
ORDER BY source_key, reference_type, review_status;
```

```sql
SELECT source_key, reference_type, normalized_name, count(*) AS duplicati
FROM public.private_reference_records
WHERE reference_type IN ('race', 'subrace')
GROUP BY source_key, reference_type, normalized_name
HAVING count(*) > 1;
```

L'ordine successivo suggerito è Ravnica → Theros → Fizban → Dragonlance,
seguendo il processo con documentazione dei valori e tracciabilità della fonte.
Nessun dato incompleto va promosso automaticamente.
