# TomoForge — completamento schede native italiane Eberron
Data audit: 2026-10-23. Manuale: `618795464-Eberron.pdf`, fonte registrata `erlw_2019_it`. Ambito: 5 **record esistenti** (nessuna nuova importazione), senza pubblicare o includere pagine PDF.

## Metodologia
- Fonte in lingua italiana: lettura del PDF privato registrato da Library e controllo visivo del blocco originale sulle pagine **292, 317, 318, 319** (numerazione fisica PDF; corrispondono a 291, 316, 317, 318 stampate). Le abbreviazioni OCR confondibili `l/1` e `O/0` sono state disambiguate sulla pagina resa a immagine.
- Gli UPDATE su Supabase `public.private_reference_records` sono stati eseguiti **solo** sui record con stesso ID, nome, source_key, source_language=it, `review_status=verified`, `translation_status=not_required`, `translation_review_status=pending`, `translation_lease_id=''`, vecchia descrizione o valori CA/PF/velocità e vecchi attributi esatti. `source_attributes` corrispondente quando presente; nel caso Corridore era storicamente `{}`, preservato.
- `source_*`, `source_refs`, `review_status`, `review_flags`, identificatori e provenienza **mai sovrascritti**. `translation_review_status=not_required` significa **traduzione non necessaria** per fonte italiana, non certificazione della traduzione inglese; non è stato impostato `ai_verified`.
- Campi di presentazione integrati senza introdurre `ft`; `attributes.completezza_scheda=completa`; descrizioni riformulate, non copia integrale del manuale. Effettuata SELECT finale indipendente sui cinque ID e controllo di CA, PF, velocità, GS, conteggio azioni e nomi fonte.

## Record completati e riletti
| Mostro | ID | Pagina PDF | CA | PF | Velocità | GS | Osservazioni |
|---|---|---|---|---|---|---|---|
| Artimago | `ref_16282dde96b4581991a15673a2f5f56a` | 317 | 11 | 9 (2d8) | 9 m | 0 | 6 caratteristiche, incantesimi, pugnale, **8 specialità** |
| Assassino Tarkanan | `ref_ab2cf767c3f25e00a1e4720ef6c01d44` | 318 | 15 | 45 (7d8 +14) | 9 m | 2 | Marchio Instabile, 4 azioni e tabella 6 varianti di incantesimi |
| Cangiante | `ref_bb6f6be4a1435773ae8f5b070d17fa83` | 318 | 13 | 22 (4d8 +4) | 9 m | 1/2 | Cambiare Aspetto, Multiattacco, Pugnale, Volto Inquietante |
| Cavaliere Delle Ossa | `ref_c63af3bbb73654edafadfc334ddfb500` | 319 | 20 | 84 (13d8 +26) | 9 m | 5 | Comando dei non morti, magia da paladino, spadone e arco |
| Corridore | `ref_8f2a5c4786b95df2bf4dbeb8462b1288` | 292 | 14 | 9 (2d8) | 15 m | 1/4 | Rapidità (ricarica 5–6), morso; narrazione esistente preservata |

Esito readback: **5/5 `review_status=verified`**, **5/5 `translation_review_status=not_required`**, **5/5 `attributes.completezza_scheda=completa`**, **5/5 sei caratteristiche**, **5/5 velocità in metri**, **5/5 CA/PF/velocità coerenti con i dati precedenti e con l'originale**. Le cinque `source_refs[0].filename` sono immutate.

## Checkpoint di continuazione
Supabase letto dopo il gruppo: bestiario **1501**; `ai_verified=593` (manuali tradotti dall'inglese), `pending=782`, `not_required=126`; `completezza_scheda=completa` su **312** schede (campo distinto dalla certificazione di traduzione). Eberron **5/40 schede complete con questo criterio; 35 pending**.

Procedere prima dagli altri record di Eberron ancora incompleti, sempre con fonte visiva e CAS per record. Gli aggiornamenti a contatori globali possono provenire da altri gruppi; il presente audit rivendica esclusivamente i cinque ID sopra.

**Branch di lavoro:** `codex/safe-monster-completion-pilot-20261021`, PR #598 contro `develop`. Nessun merge di PR, modifica di `main` o deploy di produzione effettuato qui.
