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


## Ripresa operativa dopo il checkpoint — 21 ottobre 2026, 21:53–21:56 UTC

Questo aggiornamento è **successivo** alle dichiarazioni di sola preparazione sopra riportate; non modifica retroattivamente il contenuto del checkpoint originario.

### Censimento live e fonte

- Riscontrati **28/28** record del manuale `dsotdq_2022_en` nel database Supabase di TomoForge: all'inizio della ripresa 22 `translated`, 6 `processing`, nessuno con `translation_review_status=ai_verified`.
- Recuperati il PDF originale in Library privata e la bozza aggregata dei 28 record. Impronta SHA-256 della fonte `d867631c2344fbc8b1274478f01ad64e2f22989bf340b6b5ed8e001e63ce53a8`, corrispondente alla provenienza registrata.
- Le sei schede residue sono comprimari di primo livello alle pagine fisiche 212–215, **senza grado di sfida stampato**: il campo resta nullo; velocità convertite in metri. La fonte stampa `Andir Valmakos` e `Ayik Ur`, mentre le chiavi originali di sorgente restano rispettivamente `Andir` e `Ayikur`.

### Aggiornamenti realmente eseguiti e controllati

Le sei righe esistenti sono state aggiornate **individualmente**, senza `INSERT` o eliminazioni. Per ogni scrittura: corrispondenza di ID, provenienza logica, hash PDF e pagina, stato originale `processing/pending`, lease assente, hash MD5 dello snapshot completo, unicità sorgente e assenza di collisione sul nome normalizzato. Modificati esclusivamente nome localizzato, chiave normalizzata, descrizione, testo italiano strutturato, attributi di destinazione, `translation_status`, nota della revisione e `updated_at`. I campi `source_*` sono rimasti invariati. Eseguite nuove `SELECT` per verificare testo, attributi, identificativi, fonte e stato; nessuna certificazione finale automatica.

| Sorgente/identità | Record ID | Esito |
|---|---|---|
| Andir → Andir Valmakos | `ref_7502bd584c09436f4d809e98eab7e13f` | una riga aggiornata, readback conforme |
| Ayikur → Ayik Ur | `ref_9e27048fc42051eed502fe3d9735792b` | una riga aggiornata, readback conforme |
| Hrigg Roundrook | `ref_a765852bea1f119275068ef6f373647e` | una riga aggiornata, readback conforme |
| Iriad | `ref_bb69fe51877263b6d77403027a1525ce` | una riga aggiornata, readback conforme |
| Levna Drakehorn | `ref_f480924ac8990dfe8c43365de4037fe3` | una riga aggiornata, readback conforme |
| Tem Temble | `ref_bb19cf336e2e4fa11df25194204f8794` | una riga aggiornata, readback conforme |

La prima query di controllo di Ayik Ur ha generato un errore di precedenza degli operatori SQL; la *scrittura era già riuscita*. La query di readback è stata corretta e ha verificato integralmente lo stesso record **prima** di procedere con gli altri quattro.

### Nuova rilettura aggregata e prossimi gate

- **Dragonlance 28/28 `translation_status=translated`**, 0 `processing`, **0/28 `translation_review_status=ai_verified`**.
- Il gruppo delle sei schede è `translated/pending` con `translation_review_fingerprint` vuoto e nessun lease attivo; tutte con testo esteso e identificativi originali conservati.
- Nessuna collisione per `source_name` o `normalized_name` all'interno dei 28 record.
- Rilettura globale Supabase: **1.500 mostri**, **315 `translated`**, **277 `processing`**, **908 `not_required`**, soltanto **5 certificati `translation_review_status=ai_verified`** (Minecraft).
- Per le 28 schede Dragonlance manca **ancora** una revisione indipendente documentata della fedeltà al PDF e il percorso di certificazione completo con audit, dry-run fail-closed, aggiornamento atomico e readback di approvazione. Il conteggio `translated` non significa `ai_verified`.
- Nessuna operazione di merge, deploy o modifica di `main`; PDF e traduzioni integrali rimangono esclusivamente nei materiali privati.
