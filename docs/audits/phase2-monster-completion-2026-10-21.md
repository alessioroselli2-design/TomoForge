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

### Drago dell'End — completato

- Record `ref_c6742651dc8c628c4fd95762a17ed1e8`, Minecraft p.31/logica 4;
  fonte ufficiale p.5, immagine completa e testo nativo controllati da due agenti.
- Nome e relativa chiave normalizzata localizzati; descrizione completa, tutti
  i valori del blocco, due tratti e quattro azioni tradotti. Compreso l'intero
  riquadro dei Cristalli dell'End nella descrizione: nessun record mostro aggiunto
  per gli oggetti. Convertite tutte le distanze; nessuna reazione, azione bonus
  o azione leggendaria presente sulla pagina. Resistenza leggendaria resta tratto.
- Dry-run e EXPLAIN senza ANALYZE: PASS; unicità nel manuale: una riga.
- Audit indipendente 0,99; fingerprint
  `faee408b836fc2f58f2162bef812a1e47b028688eb7aa347a95e8e0eb302e561`.
- Scrittura condizionale: una riga `translated` / `ai_verified`, timestamp
  `2026-10-21T09:48:39.630902Z`. Nuova SELECT completa e ricalcolo: PASS;
  candidata corrispondente, `source_*` invariati, nessuna modifica estranea.
- Conteggio riletto: **3/1.500** verificati.

### Enderman — completato

- Record `ref_1469c9576e35d1b60b4b5171eb719aa9`, Minecraft p.32/logica 5;
  fonte ufficiale p.6 controllata integralmente su immagine e testo nativo.
- Integrati tre paragrafi descrittivi, statistiche, quattro tratti e due azioni;
  verificati in particolare tempi e soppressione del teletrasporto, equipaggiamento,
  tiro del d10 e condizioni della perla. Nessuna sezione assente inventata.
  Distanze in metri; nessun record aggiuntivo per la perla.
- Dry-run e EXPLAIN senza ANALYZE: PASS, zero blocchi. Revisione indipendente
  0,99; fingerprint
  `79bdf7033689f1c238162eeff4b83458d8fdc7c68743020a66dfb384c25c4308`.
- Scrittura condizionale: una riga `translated` / `ai_verified`, timestamp
  `2026-10-21T09:50:57.001467Z`. SELECT completa successiva: corrispondenza
  candidata e fingerprint PASS, tutti i `source_*` invariati, solo campi autorizzati.
- Conteggio riletto: **4/1.500** verificati.

### Lupo dell'Overworld — completato

- Record `ref_29d30d4700109e0c556c03e7f26438de`, Minecraft p.33/logica 6;
  esaminata pagina ufficiale 7, immagine completa e testo nativo.
- Tradotti nome, tre paragrafi descrittivi e statistiche, un tratto e un'azione.
  Nessuna capacità mutuata da altri lupi; assenza di reazioni, azioni bonus e
  leggendarie verificata. Convertite le distanze e aggiornata la chiave del nome.
- Dry-run e EXPLAIN senza ANALYZE: PASS, zero blocchi. Audit indipendente 0,99;
  fingerprint `f93d052a606a825543763f74c89e814dacfb9ccb95e3ca97d854de50815f2dcd`.
- Ripresa dopo pausa: nuovo controllo di versione, stato e assenza di lease prima
  dell'esecuzione. La prima chiamata dopo la ripresa era priva del SQL per perdita
  dello store di sessione: rifiutata dalla validazione del connettore, zero scritture.
  Recuperato il SQL locale e completata la scrittura condizionale su una sola riga.
- `translated` / `ai_verified`; audit timestamp `2026-10-21T09:52:30.245051Z`,
  scrittura eseguita dopo la ripresa alle 10:17 UTC. Il percorso originario usava
  il timestamp dell'audit anche per updated_at; corretto separatamente per usare
  il tempo della scrittura e mantenere distinta la data della revisione.
- SELECT completa successiva: candidata conforme, fingerprint valido,
  tutti i `source_*` invariati, nessun campo non autorizzato modificato.
- Conteggio riletto: **5/1.500** verificati.

### Riparazione del timestamp di scrittura

Il nuovo SQL conserva l'ora della revisione in `translation_reviewed_at` e usa
`statement_timestamp()` per `updated_at`, distinguendo audit e scrittura dopo
eventuali pause. Una regressione dedicata porta a 31 test passati. Applicata al
Lupo una riparazione con confronto dell'intera riga appena riletta e lo stesso
audit/fingerprint: nuova SELECT conferma che è cambiato soltanto `updated_at`,
ora `2026-10-21T10:20:10.552107Z`; tutti i contenuti e metadati di audit invariati.

### Revisione della fonte Minecraft — discrepanza risolta

Durante il ricontrollo di Creeper il PDF iniziale riportava danni da fulmine,
mentre la scheda esistente aveva danni da forza. Nessuna correzione basata sulla
plausibilità della regola è stata applicata. Recuperato dal publisher il
[PDF revisionato](https://www.minecraft.net/content/dam/minecraftnet/games/minecraft/software/Minecraft-Monstrous-Compendium-revised.pdf),
SHA256 `d4d0bbcd0efcc1fd7a714919379f25d8c51987b3ab8c9884c25ea95a6ea85119`.
Il file ha data di creazione 29 marzo 2023, successiva al 21 marzo del primo PDF.
Il confronto del testo delle otto pagine mostra la sola correzione dei tre
richiami al danno di Distruzione a p.4: da fulmine a forza. Le altre sette pagine
sono identiche nel testo nativo. La pagina revisionata è stata controllata anche
visivamente. Il nuovo audit di Creeper usa questa fonte; gli audit già completati
delle altre quattro creature restano coerenti con entrambe le versioni.

### Creeper — ricompletato e verificato

- Record `ref_4b4acc08abae1c6c51f54d1d91f4edd0`, Minecraft p.30/logica 3;
  nuova revisione completa della pagina 4 del PDF ufficiale revisionato.
- Lo stato precedente era già verificato, ma descrizione riassunta e full_text
  vuoto non bastavano alla completezza richiesta. Integrati tutti e quattro i
  paragrafi descrittivi, generato il testo italiano integrale e contabilizzate le
  sezioni assenti. Cinque tratti esistenti confrontati nuovamente con la fonte;
  danni da forza confermati dalla revisione ufficiale. Nessuna azione autonoma.
- Dry-run e EXPLAIN senza ANALYZE: PASS. Audit indipendente 0,99, fingerprint
  `f60911eb3513743b73a44b344e2f09cf4e5365ac0d19c5f7f715c63eeccd3a21`.
- Scrittura condizionale: una riga, `translated` / `ai_verified`, timestamp
  effettivo `2026-10-21T10:22:34.667820Z`. SELECT completa successiva: PASS,
  contenuto uguale alla candidata, fingerprint corrente, tutti i `source_*`
  invariati, soli campi autorizzati modificati.
- Conteggio invariato: **5/1.500** verificati. Non conteggiato come nuovo mostro.

## Verifica conclusiva Minecraft

Nuova lettura dei cinque record dopo tutte le operazioni: ciascuno ha descrizione
e testo integrali, completezza canonica `completa`, stato `translated` /
`ai_verified` e fingerprint ricalcolato corrispondente. **5/5** del manuale.
Nessun record inserito o duplicato; nessun campo `source_*` modificato.

Conteggio complessivo riletto: **5 verificati, 587 processing, 908 not_required**,
totale **1.500**. I restanti 1.495 non sono dichiarati completi.

Il percorso auditato aggiorna nome e chiave normalizzata nella stessa operazione.
Le coppie URL/digest delle due versioni ufficiali non sono intercambiabili;
per Creeper è obbligatoria la versione revisionata. Verifiche finali del codice:
**33 test passati**, Ruff, compilazione e diff-check superati.

## Blocco della fonte successiva — Eldraine

Proseguito al manuale successivo `mc_v4_eldraine_2023_en` (25 record).
Primo record in ordine alfabetico: **Archon of Boundaries**,
`ref_cbfe3da80a95745bb9243bbd6dccf007`, compilazione p.36/logica 3.

La SELECT conferma soltanto statistiche essenziali: source_description e
source_full_text vuoti. Questi dati non permettono di ricostruire descrizione,
tratti o azioni. Nessuna candidata completa inventata, nessun fingerprint di
approvazione prodotto, nessuna scrittura al record.

Fonte registrata riletto da Supabase: `701858566-RRN5YRR.pdf`, SHA256
`b7fb95c7519fb0936bb2cb37cfb6a5493134c86e0dc31196a4c62a67887e8ada`,
174.491.417 byte, 75 pagine, sezione Eldraine pp.34–60. Il PDF non è presente
nel workspace, nel tree Git o nei cinque puntatori LFS disponibili. Il file LFS
del Manuale dei Mostri è un altro artefatto e non sostituisce questa fonte.
L'ambiente non dispone di credenziali R2 configurate per recuperare la copia.

La [pagina ufficiale D&D Beyond](https://www.dndbeyond.com/sources/mcv4/eldraine-creatures)
reindirizza alla pagina commerciale del manuale e non rende disponibile il testo
completo necessario all'audit; non è stato trovato un PDF ufficiale pubblico.
La lavorazione si arresta per fonte insufficiente, come richiesto. Per riprendere
serve il PDF registrato oppure accesso autorizzato alla fonte ufficiale completa.
La PR #598 rimane aperta, senza merge né deploy di produzione.


## Ripresa Eldraine — fonte locale recuperata e verifica candidata (21 ottobre 2026)

Aggiornamento successivo al blocco documentato sopra: è disponibile nell'ambiente di lavoro una copia privata del PDF di ingestione `701858566-RRN5YRR(1).pdf`, 75 pagine, 174.491.417 byte, SHA256 `b7fb95c7519fb0936bb2cb37cfb6a5493134c86e0dc31196a4c62a67887e8ada`, corrispondente al digest nei `source_refs` Eldraine. Non è stato aggiunto il PDF al repository e la presenza locale non implica pubblicazione della fonte.

Per `High Fae Impostor` (`ref_5ac1ef374dbdd707cdcc395f7260ee25`, pagina fisica 45) è stata preparata una candidata italiana privata, confrontata manualmente con la pagina originale. La traduzione iniziale di `enthrall` come `charme su persone` è stata corretta in `intrattenere (enthrall)`, anche nelle sezioni strutturate. Una checklist locale riporta 18/18 verifiche mirate superate, ma NON costituisce un audit indipendente. I file di lavoro rimangono fuori dal repository; nessun testo integrale protetto è aggiunto qui.

Stato effettivo: `translation_review_status` non approvato; `independent_review_missing` resta un blocco del preflight. Non è stato eseguito alcun aggiornamento atomico di questa creatura, né sono stati modificati i suoi `source_*`. Le candidate Eldraine non devono essere conteggiate come `ai_verified` fino ad audit indipendente attestato, SQL condizionale e rilettura del record. Ultimo totale di completamenti confermati: **5/1.500**.

Per riprendere: richiedere a un revisore distinto il controllo della pagina 45 e delle sezioni, con evidenza verificabile e fingerprint della candidata corretta; quindi eseguire preflight reale, scrittura atomica e SELECT di verifica. Nessuna attestazione va prodotta automaticamente dal medesimo autore della traduzione.


## Controlli di fedeltà Eldraine: correzioni su database — 21 ottobre 2026

La copia PDF privata della compilazione `701858566-RRN5YRR(1).pdf` mantiene SHA-256 `b7fb95c7519fb0936bb2cb37cfb6a5493134c86e0dc31196a4c62a67887e8ada`, corrispondente a `source_refs[0].physical_sha256`. Le pagine fisiche Eldraine 36–60 sono state consultate visivamente, confrontando capacità, CD, trigger, distanze e danni con le righe Supabase. I file sorgente e testi integrali non sono aggiunti al repository.

Sono emerse **cinque correzioni semantiche in quattro record esistenti**, eseguite con UPDATE condizionali a riga unica e rilettura:
- `ref_cbfe3da80a95745bb9243bbd6dccf007`, **Archon of Boundaries**, p.36: `Radiosità Accecante`, corretto il verso del trigger (la creatura costringe l'arconte a un tiro salvezza, non viceversa).
- `ref_d67ea8e717d8e061c8f4054b26cfb77b`, **High Fae Kindguard**, p.46: `Spadone Fatato`, riduzione velocità **a 3 m** (non di 1,5 m); `Parata e Risposta`, attacco di risposta dopo che quello in arrivo **colpisce o manca** (non solo se manca).
- `ref_9f0982b73d37dc50aedb7f27f0649a7e`, **Nightmare Haunt**, p.50: danno `Viticci del Torpore` corretto a **11 (2d10)** da 7 (2d10).
- `ref_b1dd5fca9898c7e4d5aecd00d1e54c86`, **Witchstalker**, p.60: ripristinata **CD 15** nel tiro salvezza di Saggezza dell'ululato.

Per ciascuna scrittura: controllo dell'ID e `source_name`, `logical_source_id`, SHA e pagina della fonte, stato `translated/pending`, lease assente e timestamp dello snapshot; modificati solo `attributes` (sezione interessata), `full_text` e `updated_at`. Le letture successive attestano che tutti e quattro i record contengono il testo corretto in entrambe le rappresentazioni e conservano `translation_review_status=pending`; nessun inserimento effettuato.

**Rilettura complessiva Eldraine**: 25 righe, 25 ID unici, 25 `source_name` distinti, 25 `normalized_name` distinti, 25 SHA di fonte corrispondenti, zero lease attivi, 25 `translated/pending`, **0/25 `ai_verified`**.

Questa revisione di contenuto e coerenza non sostituisce la revisione indipendente della candidata completa e il percorso audit + dry-run fail-closed + fingerprint. Nessuna certificazione è stata fabbricata; nessun merge di PR, deploy o modifica a `main` o `develop`.
