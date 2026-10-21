# Dragonlance — fase 2, checkpoint di preparazione privata (2026-10-21)

> **Stato: 28/28 bozze italiane predisposte; 0/28 nuove certificazioni Supabase attestate in questa sessione.**
> Questo documento non contiene estrazioni di regole, pagine PDF, traduzioni integrali o credenziali. Non autorizza alcuna promozione a `ai_verified`.

## Provenienza
- Manuale: **Dragonlance: Shadow of the Dragon Queen**.
- Logical source: `dsotdq_2022_en`.
- File fisico di riferimento: `682072052-5e-DnD-Dragonlance-Shadow-of-the-Dragon-Queen-Mong-IcYPD5.pdf`.
- SHA-256 della copia privata realmente esaminata: `d867631c2344fbc8b1274478f01ad64e2f22989bf340b6b5ed8e001e63ce53a8` (coincide col registro del repository).
- Il PDF privato non è stato caricato sul repository; le bozze complete in italiano sono conservate come allegati privati della conversazione, non pubblicate in GitHub.

## Censimento e controlli strutturali

- **28** schede originali: **22** blocchi dell'appendice B (mostri e PNG) e **6** comprimari dell'appendice C.
- Lotti privati: 6 (5+5+5+5+5+3).
- Confronto automatico di tutte le 28 schede con il censimento `backend/data/dsotdq_2022_en_source_review_core_28.json`: identità logica, pagine fisiche e stampate, CA numerica, punti ferita/espressione dadi, sei caratteristiche, GS, velocità principale presentata in metri, conteggio delle sezioni strutturate.
- **0 errori di coerenza numerica e strutturale** emersi nel confronto di preparazione; **0 nomi originali duplicati** e **0 nomi italiani duplicati** nei lotti.
- Sezioni descritte nei lotti: 50 tratti, 81 azioni, 5 azioni bonus, 5 azioni leggendarie, 4 reazioni.
- Questi controlli non attestano fedeltà indipendente di ogni traduzione e non sostituiscono un audit sul database reale.

## Eccezioni di identità da risolvere prima dell'importazione

1. **Andir**: il censimento usa `Andir`; sul PDF originale, scheda p.212, figura `Andir Valmakos`.
2. **Ayikur**: il censimento usa `Ayikur`; sul PDF originale, scheda p.213, figura `Ayik Ur`.

I lotti mantengono la chiave logica originale separata dal nome mostrato. Prima di qualsiasi modifica canonica, confrontare ID e nomi esistenti nello stesso `logical_source_id`, preservando il record unico ed evitando nuovi inserimenti. Nessuna chiave è stata cambiata in Supabase durante questa attività.

## Stato e blocchi

- **Traduzione:** bozze `draft`; **revisione traduzione:** `pending`.
- **Revisione indipendente:** non ottenuta; non attestare falsamente una seconda verifica.
- **Dry-run su snapshot reali Supabase:** non eseguito.
- **Scritture, readback, fingerprint su Supabase in questa sessione:** nessuna; stato corrente dei 28 record nel DB non riletto.
- Nessuna modifica a `main`, `develop`, dati canonici, manuali o R2.

## Passaggi obbligatori per proseguire sullo stesso manuale

1. Revisore distinto confronta pagina per pagina la bozza privata con la fonte completa, sezioni e testi inclusi, e attesta gli esiti individuali.
2. Verificare in sola lettura record-ID, esistenza, stato, impronte, lease, collisioni e campi `source_*`, con attenzione agli alias di Andir e Ayik Ur.
3. Eseguire dry-run fail-closed con snapshot completo e candidata audita.
4. Solo dopo gate superati, eventuale scrittura atomica condizionale della singola scheda, con collision/lease/version checks e `source_*` invariati.
5. Rileggere ogni record, ricalcolare fingerprint, accertare nessun duplicato e aggiornare i contatori live. Passare al manuale seguente soltanto al superamento dei gate reali.

**Nota:** la PR #598 riguarda un pilota distinto (Minecraft e completamento atomico) e rimane indipendente da questo checkpoint. Questo checkpoint non comporta merge o deploy.
