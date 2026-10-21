# Fase 2 — registro operativo del completamento

Unico branch: `codex/safe-monster-completion-pilot-20261021`, PR #598 verso
`develop`. Nessun merge, modifica di `main` o deploy di produzione autorizzato.
Questo registro contiene solo metadati di audit; PDF, estrazioni e traduzioni
integrali rimangono fuori dal repository.

## Censimento iniziale riletto

1.500 mostri: 1 `translated` / `ai_verified`, 591 `processing` / `pending`,
802 `not_required` / `pending`, 106 `not_required` / `not_required`.
`not_required` non costituisce prova di completezza.

## Correzione della scrittura condizionale

Ispezionato lo schema effettivo di `public.private_reference_records`.
Oltre a `translation_error`, anche `translation_review_fingerprint`,
`translation_review_notes`, `translation_review_confidence` e
`translation_review_model` sono NOT NULL. Ripristinati i rispettivi valori
vuoti/zero; soltanto `translation_reviewed_at` viene azzerato a NULL.
Commit `ea6d8ef`; 16 test pertinenti passati con configurazione pytest/xdist
del repository e Ruff superato. Nessuna scrittura Supabase per testare l'accesso.

## Fonte Minecraft recuperata

La candidata precedente di Blaze e la compilazione fisica non sono presenti
nel workspace, negli asset LFS o nei metadati accessibili. Recuperato direttamente
il [PDF del publisher](https://www.minecraft.net/content/dam/minecraftnet/games/minecraft/software/Minecraft-Monstrous-Compendium.pdf),
SHA256 `559802923408bb57ccea250e6806603ee20b1ad4ed28e58c2e1608bf5ba79521`.

Il registro `backend/reference_sources.py` assegna priorità alla fonte ufficiale
autonoma rispetto alla copia di ingestione. Titolo, volume, anno, ordine delle
cinque creature e statistiche corroborano l'identità della pubblicazione logica
`mc_v3_minecraft_2023_en`: pagine ufficiali 2–7 corrispondono alle pagine 28–33
della compilazione registrata, con copertina e retro esclusi. Questa evidenza non
attesta nuovamente l'hash né l'identità byte per byte della compilazione.
I campi `source_*` e i riferimenti registrati devono restare invariati; hash,
URL e pagina della fonte effettivamente esaminata sono conservati nell'audit.

## Operazioni per record

Le righe seguenti vengono completate soltanto dopo dry-run, aggiornamento
atomico condizionale e nuova lettura indipendente da Supabase.

### Blaze — completato

- Record `ref_b875e1102ae8528373d4e6501baf2d30`.
- Manuale Minecraft, compilazione p.29/logica 2; esaminata pagina 3 del PDF
  ufficiale indicato sopra, immagine completa e testo nativo, con seconda revisione.
- Ricostruita la candidata privata dalla fonte: descrizione completa, statistiche,
  quattro tratti, due azioni; assenza di reazioni, azioni bonus e leggendarie
  riscontrata sulla pagina. Integrato il volo stazionario omesso nell'estrazione;
  convertite le distanze secondo 5 ft = 1,5 m. Fonte e riferimenti invariati.
- Dry-run: PASS, zero blocchi, zero scritture. `EXPLAIN` senza `ANALYZE`: PASS
  sullo schema Supabase effettivo. Unicità del record nel manuale: un risultato.
- Audit indipendente completo, confidenza 0,99; fingerprint
  `4f47b1138f774d7964b8540e4ebc5559a545cae25ea318b0049601c9aadaa28d`.
- Scrittura atomica con confronto dell'intera riga originale: una riga aggiornata
  a `translated` / `ai_verified`, audit completo incluso nei metadati Supabase.
  Timestamp `2026-10-21T09:44:37.986916Z`.
- Nuova SELECT completa: contenuto uguale alla candidata, fingerprint ricalcolato
  valido, tutti i `source_*` invariati, nessun campo estraneo modificato.
- Conteggio Supabase: **2/1.500** `translated` / `ai_verified`; 590 processing,
  908 not_required. Nessun nuovo record inserito.

### Strumento di aggiornamento dopo audit

Il nuovo percorso richiede un audit esterno completo vincolato al fingerprint
della candidata e alla fonte effettivamente esaminata. La sostituzione Minecraft
è limitata al PDF ufficiale, ai digest e alla mappatura registrata; richiede una
ricevuta esplicita, senza dichiarare ricalcolato il digest della compilazione.
Il confronto tipizzato dell'intera riga e delle chiavi dello snapshot blocca
modifiche concorrenti o letture parziali. I valori vengono serializzati come
JSON, mantenuti separati dal codice SQL. Il modulo genera proposte e non si
connette al database. 29 test pertinenti, Ruff e compilazione superati;
revisione indipendente del codice e pilot reale di Blaze completati.
