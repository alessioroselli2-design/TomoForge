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


## Avvio completamento Mordenkainen's Fiendish Folio Volume 1 — 21 ottobre 2026

Fonte privata `1064688926-9-D-D-5e-Mordenkainen-s-Fiendish-Folio-Vol-1.pdf`, 22 pagine fisiche, SHA-256 `e84ea509258d5d96dbb5d5253accc694f658b1985d66257a1be913b54faeec4a`. PDF scansionato (non testuale); ogni pagina della sequenza seguente è stata confrontata visivamente con il relativo record parziale presente in `private_reference_records`. Il sorgente non è copiato nel repository.

Sei schede esistenti hanno ricevuto una **candidata italiana di descrizione, caratteristiche, capacità e regole**, mantenendo gli ID originali e tutte le `source_*` immutate:
- p.5 `ref_88dab46b800b8d09309a41f52d82c753`, **Assassin Bug → Insetto Assassino**: 3 azioni, 1 tratto; velocità 3 m/volare 15 m.
- p.6 `ref_e6c665dba50c33773cb20132f97c39d7`, **Blindheim**: 2 azioni, 1 tratto; 9 m.
- p.7 `ref_dcabd5d19108957d4d127974bd016be6`, **Crab Folk → Uomo Granchio**: 2 azioni, 1 tratto; 12 m/nuotare 12 m.
- p.8 `ref_ac54f6dc6a0e7b0654e3d216c24687b5`, **Dire Corby → Corbo Feroce**: 2 azioni, 2 tratti; 12 m/scalare 12 m.
- p.9 `ref_d56e3be9d500c0523048e493c6d10c05`, **Eye of Fear and Flame → Occhio di Paura e Fiamma**: 3 azioni, 2 tratti; 9 m.
- p.10 `ref_8b441b9817e1892baebc5eee85942f49`, **Forlarren**: 4 azioni, 2 tratti; 12 m.

Ogni aggiornamento è un solo `UPDATE` protetto da ID, nome originale, manuale, SHA-256 fonte, numero pagina, versione `updated_at`, stato `processing/pending`, assenza di lease e controllo di assenza del nuovo nome nel manuale. La rilettura ha confermato tutte e sei le righe `translated/pending`, campi dei tratti/azioni presenti, velocità in metri e fonte originale conservata. **Conteggio MFF1 6/18 translated, 12/18 processing, 0/18 ai_verified, 18 ID/source_name unici.**

Questo è un checkpoint, **non un certificato**: le sei candidate richiedono ancora controllo indipendente completo, dry-run e procedura fail-closed prima di qualunque `ai_verified`. Restano da preparare p.11–22 (`Fog Giant`, `Jermlaine`, `Khargra`, `Killmoulis`, `Mite`, `Needle Lord`, `Needle Spawn`, `Norker`, `Norker War Leader`, `Screaming Devilkin`, `Ygorl, Lord of Entropy`, `Xill`). Non eseguito merge né deploy e non modificati `main`/`develop`.


## Chiusura fase di traduzione MFF1 — 22 ottobre 2026

Controllate le pagine fisiche 11–22 del PDF scansionato `1064688926-9-D-D-5e-Mordenkainen-s-Fiendish-Folio-Vol-1.pdf`, già registrato con SHA-256 `e84ea509258d5d96dbb5d5253accc694f658b1985d66257a1be913b54faeec4a`.

Le dodici schede prima in `processing` (pp.11–22) sono state aggiornate direttamente in Supabase come candidate italiane **`translated/pending`** con la stessa procedura condizionale di ID/provenienza/pagina/versione/lease e assenza di collisioni: **Fog Giant → Gigante della Nebbia**, **Jermlaine**, **Khargra**, **Killmoulis**, **Mite**, **Needle Lord → Signore degli Aghi**, **Needle Spawn → Progenie degli Aghi**, **Norker**, **Norker War Leader → Condottiero Norker**, **Screaming Devilkin → Diavoletto Urlante**, **Ygorl, Lord of Entropy → Ygorl, Signore dell'Entropia**, **Xill**. Rispettate le velocità in metri e mantenuti `source_*` e gli ID originali; per i mostri con capacità, preservate sezioni tratti/azioni/reazioni/leggendarie presenti sulla pagina.

Rilettura indipendente in sola lettura del DB: **MFF1 18/18 translated, 0 processing, 18/18 pending, 0 ai_verified**, 18 ID univoci, 18 nomi originali univoci, 18 nomi italiani normalizzati univoci, 18 source SHA conformi, zero lease, 18 schede con testo lungo e `attributes.completezza_scheda=completa`, zero velocità `ft`. Per tutte le 18 schede le sei caratteristiche numeriche e la formula dei punti ferita coincidono con `source_attributes`.

**Limite di questo checkpoint:** il controllo sulle pagine della fonte e sui valori registrati non è un attestato di seconda revisione da un revisore distinto; è ancora necessario un audit indipendente di fedeltà, dry-run di approvazione, firma/fingerprint e readback prima di assegnare `ai_verified`. Zero merge o deploy, PDF e traduzioni integrali non sono committati.


## Avvio manuale successivo: Minsc & Boo's Journal of Villainy — 22 ottobre 2026

Fonte originale privata `536195827-Minsc-and-Boo-s-Journal-of-Villainy.pdf`, digest registrato `3371a24a16f9f2549f269fe5d0515b0f19456816c2f34da5014268c4b18af649`. Il file ha testo nativo e le pagine originali sono state controllate senza aggiungere il PDF al repository.

Dopo i sette record `translated/pending` già esistenti, sono state predisposte e registrate sei ulteriori schede italiane sui soli ID preesistenti:
- `ref_7c1b0b5db7ad35744480a67c44bc3429`, **Faldorn**, p.51–52: caratteristiche, incantesimi, mutaforma, bastone magico e sei opzioni di contatto dell'Enclave
- `ref_6ca58e23981d646499ce9de4b4481521`, **Nauk**, p.55: attacchi, inventario di pozioni, incidente delle pozioni, reazione e listino
- `ref_63b03bc3af5a143dbd0b2d5ad6024764`, **Borivik Windheim**, p.57: incantesimi, quadrelli anti-non morti, compagni e listino equipaggiamento
- `ref_363983714a742c5646c8d2b7f427e4f7`, **Jaheira**, p.61: incantesimi, evocazioni, ascendenza e opzioni di contatto degli Arpisti
- `ref_867ee8b2f75c9e57770f6563f67d3212`, **Vellin Farstride**, p.63: compagni animali e cavalcature disponibili
- `ref_709b621cc55d1d986b870dd771cd9388`, **Minsc and Boo! → Minsc e Boo!**, p.69: regole della furia, protezione di Boo e lista dei compagni; non sono stati creati record duplicati per Boo

Ciascuna scrittura è protetta da ID, fonte/sha/pagina, stato `processing/pending`, `updated_at` antecedente, lease assente e collision-check sul nome normalizzato. I campi `source_*` e gli ID sono preservati; ciascun UPDATE ha restituito una singola riga `translated/pending`. Conteggi live: **13/56 translated, 43 processing, 0 ai_verified, 56 ID distinti**. La revisione indipendente e il percorso atomico di certificazione sono ancora necessari.

Il passo successivo, rispettando l'ordine delle pagine, è **Jon Irenicus (p.74)**. Globale dopo gli aggiornamenti: **339 translated, 253 processing, 908 not_required, 5 certificati su 1.500**. Nessun merge o deploy.


## Minsc & Boo — sette ulteriori schede italiane, checkpoint 22 ottobre 2026

Ripresa operativa dalla PR già in bozza #598 sul branch `codex/safe-monster-completion-pilot-20261021`. Connettività con Supabase verificata tramite `SELECT 1`, inventario e stato reali del manuale riletto prima di qualsiasi modifica. PDF privato `536195827-Minsc-and-Boo-s-Journal-of-Villainy.pdf`, SHA-256 attestato nei `source_refs[0]` `3371a24a16f9f2549f269fe5d0515b0f19456816c2f34da5014268c4b18af649`; consultate direttamente le pagine pertinenti del PDF testuale. **Non è stato duplicato, importato su GitHub o pubblicato il testo integrale del PDF.**

Sulle sette righe già esistenti sono state inserite candidate italiane con identità, statistiche, sezioni tratti/azioni e allegati strutturati relativi alle capacità di contatto. Tutte le scritture hanno restituito esattamente un ID esistente come `translated/pending`, con vincoli `id`, `source_name`, `logical_source_id`, SHA, pagina, timestamp precedente, `processing/pending`, assenza di lease e controllo collisione `normalized_name`.

| Pagina fisica | Nome originale / italiano | ID | Elementi particolari |
| --- | --- | --- | --- |
| 67 | Suldil Baldoriel | `ref_e552247d0497edb2ce14cd207545533c` | Cavaliere draconico, incantesimi, 8 potenziamenti degli oggetti |
| 74 | Jon Irenicus | `ref_9b88f5769c2f99c11fde0a9c5ca3249b` | 4 azioni leggendarie, incantesimi di 20° livello, 10 trasmutazioni |
| 78 | Bodhi Irenicus | `ref_f5363785aace52fa86637e057d2767a9` | Forma di pantera, 3 azioni leggendarie, 6 doni soprannaturali |
| 81 | Lothar | `ref_71510ea405311371d352038959c9b4ce` | Forma di corvo, furia, incantesimi, 8 viaggi tra mondi |
| 83 | Viktor → Viktor Kuhn | `ref_1c7b5a422edbf643557828d6f5bd4c7d` | Lama Solare, drago d'ombra, 5 amuleti della memoria |
| 87 | Montaron and the Laughing Skull → Montaron e il Teschio Ridente | `ref_df4a9087638b203989ef9eaba8667b34` | Xzar demilich dentro la **stessa** scheda, 7 opzioni di scambio |
| 89 | Imoen | `ref_9260b3bf340e177c81bb93d1531d9361` | Tratti di ascendenza vampirica, 5 opzioni di trasformazione |

**Audit live dopo le scritture**: MBJV `20/56 translated`, `36 processing`, `0 ai_verified`; `56/56` ID, `source_name` e `normalized_name` distinti; `56/56` hash fonte coerenti; 0 lease attivi. Per tutte le 20 schede `translated`: `20/20` punteggi delle 6 caratteristiche, formule HP e grado sfida confrontati con `source_attributes`, senza discrepanze. Le sette schede appena aggiornate hanno `attributes.completezza_scheda=completa`, velocità in metri e contengono descrizioni estese. Totale globale: `1500` mostri, `346 translated`, `246 processing`, `908 not_required`, `5 ai_verified`.

**Il prossimo record in ordine è Baalzebul (pagina fisica 93)**. Rimangono 36 traduzioni MBJV e l'audit indipendente dei 56 record, senza promuovere schede `translated` a `ai_verified` impropriamente. Nessun merge né deploy, nessuna modifica a `main` o `develop`.


## Minsc & Boo — tre avversari di campagna, checkpoint 22 ottobre 2026

Proseguita la consultazione diretta del PDF privato Minsc & Boo, `536195827-Minsc-and-Boo-s-Journal-of-Villainy.pdf`, SHA registrato `3371a24a16f9f2549f269fe5d0515b0f19456816c2f34da5014268c4b18af649`. Sono stati aggiornati altri **tre record esistenti** mediante le stesse guardie fail-closed per ID, fonte, pagina, SHA, stato, lease, `updated_at` e collisioni:
- **Baalzebul**, p.93, `ref_74f299d300676a3502cb21e53093bf1a`: 5 azioni, capacità innata, 2 opzioni leggendarie, 3 azioni di tana e 2 effetti regionali.
- **Bhaal, Slayer → Bhaal, l'Assassino**, p.94, `ref_92996df8d72bad85694e3d2f6fb03a83`: tratto Preda, azione bonus, 3 opzioni leggendarie e requisito di trasformazione.
- **Bhaal, Ravager → Bhaal, il Devastatore**, p.96, `ref_e5593f9940d640c24d4c557b0ce75380`: attacchi, difese, 3 opzioni leggendarie e ricomparsa della forma Assassino. Le due forme rimangono **due ID distinti preesistenti**, non duplicati dello stesso record.

Le tre scritture hanno restituito una singola riga `translated/pending` ciascuna; il readback sui tre record ha confermato pagina, sezioni strutturate e velocità in metri. Nel controllo globale del manuale, **MBJV 23/56 translated, 33 processing, 0 ai_verified**; 56 ID, `source_name`, `normalized_name` univoci, zero lease attivi, 56 SHA corrispondenti; **23/23** punteggi delle sei caratteristiche, HP e GS coincidenti con i dati di sorgente conservati. Sul progetto, **349/1500 translated, 243 processing, 908 not_required, 5 ai_verified**.

**La fase di trascrizione non equivale a certificazione:** contenuto ancora in `translation_review_status=pending` fino a revisione indipendente fonte-verso-candidata, dry-run e attestazione atomica. Prossimo mostro nell'ordine dei documenti: **Cryonax**, p.99. Nessun merge o deploy.


## Completamento fase di traduzione MBJV — 22 ottobre 2026, 56/56

Fonte riservata: `536195827-Minsc-and-Boo-s-Journal-of-Villainy.pdf`, 158 pagine fisiche, `source_refs[0].physical_sha256=3371a24a16f9f2549f269fe5d0515b0f19456816c2f34da5014268c4b18af649`. Il PDF e i testi integrali sono rimasti fuori dal repository pubblico. Le pagine native sono state consultate separatamente per blocchi caratteristiche, descrizioni e sezioni di regole, senza OCR di massa.

**33 nuove schede `translated/pending`** su ID già esistenti, ordinate per pagina:
- p.99 Cryonax; p.102 Mephistopheles → Mefistofele; p.105 Pazuzu; p.108 Ssendam, Lord of Madness → Ssendam, Signora della Follia;
- p.109 Aribeth de Tylmarande; p.111 Dagryn; p.113 Darien → Darien, la Strega di Ghiaccio; p.115 Edwin Odesseiron; p.117 Eo Ashmajiir;
- p.119 Kagain → Kagain, Cacciatore di Urla; p.121 Pelyious Avhoste; p.123 Saemon Havarian; p.125 Sarevok → Sarevok Anchev; p.127 Viconia DeVir; p.129 Xzar the Chaos Clone → Xzar, Clone del Caos;
- p.132 Achaierai; p.134 Bebilith; p.136 Demodand, Farastu → Demodand Farastu; p.137 Demodand, Kelubar → Demodand Kelubar; p.138 Demodand, Shator → Demodand Shator;
- p.140 Dread Doppelganger → Doppelganger Terrificante; p.142 Gibberling; p.144 Hamadryad → Amadriade Corrotta; p.146 Sirene → Sirena Fatata; p.148 Phaerimm; p.149 Skeleton Lord → Signore Scheletrico; p.150 Skeleton Warrior → Guerriero Scheletrico;
- p.152 Deep Spider → Ragno delle Profondità e Sword Spider → Ragno Spada; p.154 Tasloi e Tasloi Sniper → Tasloi Cecchino; p.155 Wolfwere Alpha → Wolfwere Alfa; p.156 Wolfwere.

Tutte le scritture hanno aggiornato **solo un record esistente per operazione** mediante condizioni `id`, nome originale, `logical_source_id`, SHA, pagina fisica, `updated_at` precedente, `processing/pending`, assenza di lease e assenza di collisione su `normalized_name`. `source_attributes` e `source_refs` sono rimasti intatti, senza INSERT o duplicati. `attributes`, `description`, `full_text` sono candidati localizzati in italiano; distanze convertite in metri. Le schede con magie, reazioni, bonus, azioni leggendarie, di tana e regionali riportano le sezioni pertinenti.

**Rilettura in sola lettura dopo le 33 scritture:** MBJV **56/56 translated, 0 processing, 56 pending, 0 ai_verified**; 56/56 identificativi, nomi originali e nomi normalizzati distinti; 56/56 SHA conformi; 0 lease attivi; 56/56 formule punti ferita, grado di sfida e tutti e sei i punteggi di caratteristica coerenti con `source_attributes`; 0 velocità ancora in `ft`; 56/56 `full_text` di oltre 900 caratteri. Globale **1.500 mostri, 382 translated, 210 processing, 908 not_required, 5 ai_verified**.

**Anomalie dell'originale (5 schede, verificare prima della certificazione):**
1. Kagain p.119 `ref_b6c26a58208884db794cb10003075761`: testo afferma che l'ascia aumenta il massimo HP di uno per livello/Dado Vita e mostra **176 HP**, ma il blocco dice **152 HP = 16d8+80**; 152+16=168. Non alterato arbitrariamente il blocco HP.
2. Demodand Kelubar p.137 `ref_9b35dd384f50edf5c935e9fb75363ebc` e Shator p.138 `ref_e2bbe4cce4d75e2900f010500bbba038`: `Summon Reinforcements` indica risultati di 1d6 soltanto per 1–2 e 3–4; tace 5–6. Non inventato esito.
3. Wolfwere Alpha p.155 `ref_135a8aa700861a6d4c06221a57cfda2e` e Wolfwere p.156 `ref_5cc6e0a9f3d2220badf4cee071972a6c`: i danni della spada lunga a due mani riportano un modificatore superiore di 1 rispetto all'uso a una mano; conservati i dati stampati e segnalati.
Una sesta nota linguistica non elevata a blocco `completezza`: Pazuzu p.105 descrive soffio in una *linea* lunga 100 ft e larga 5 ft, poi menziona impropriamente «cone»; il testo candidato riporta linea con tracciamento dell'ambiguità.

**Distinzione obbligatoria:** `translated` certifica solo l'esistenza della candidatura, **non** la revisione indipendente fonte-verso-output. Tutti e 56 i `translation_review_status` rimangono `pending`. Le 5 anomalie sono registrate in `attributes.anomalie_fonte`, `completezza_scheda='completa_con_anomalia_fonte'` e note. Prima di qualsiasi `ai_verified` servono riconciliazione fonte/errata dove disponibile, audit indipendente, dry-run condizionale, fingerprint e rilettura atomica. Nessun merge/deploy su main o develop.

Prossimi manuali con `processing` da snapshot: Spelljammer Boo's Astral Menagerie `sjbam_2022_en` 72; Planescape Morte's Planar Parade `ps_mpp_2023_en` 53; Mythic Odysseys of Theros `mot_2020_en` 49; The Book of Many Things `bomt_2023_en` 36. Da trattare **uno alla volta** e soltanto con PDF originale verificato.


## Ripresa post-interruzione streaming — checkpoint 22 ottobre 2026

La query `SELECT 1` su Supabase ha avuto esito positivo e l'inventario in sola lettura di `private_reference_records` ha accertato un avanzamento ulteriore rispetto all'ultimo messaggio visibile prima dell'interruzione. **Minsc & Boo's Journal of Villainy (MBJV) è ora 56/56 `translated`, 0 `processing`, 56/56 `translation_review_status=pending`, 0 `ai_verified`**. `count(distinct id)=count(distinct source_name)=count(distinct normalized_name)=56`; nessun duplicato. Hash ufficiale della copia utente `3371a24a16f9f2549f269fe5d0515b0f19456816c2f34da5014268c4b18af649`, PDF confermato in locale a 158 pagine.

Verifica strutturale dei 56: **56/56 formule HP, 56/56 GS e 56/56 sestine caratteristiche** coincidono con `source_attributes` di importazione; zero `ft` nelle velocità; zero lease attivi; zero descrizioni sotto 300 caratteri; zero `full_text` sotto 600 caratteri; le sette traduzioni più antiche non riportano `attributes.completezza_scheda` pur possedendo descrizioni estese e array tratti/azioni.

**Cinque anomalie del testo originale confermate direttamente sul PDF e già esplicitate nelle relative schede** (non inventare correzioni e non certificare senza decisione sul trattamento):
- `Kagain`, p.119, il potenziamento dell'ascia parla di +1 HP per livello o Dado Vita e dà 176 mentre il blocco usa 152 HP e 16 Dadi Vita (il calcolo dà 168);
- `Demodand, Kelubar`, p.137, `Summon Reinforcements` su 1d6 descrive solo gli esiti 1–2 e 3–4, non il caso 5–6;
- `Demodand, Shator`, p.138, analoga lacuna sugli esiti 5–6 di `Summon Reinforcements`;
- `Wolfwere Alpha`, p.155, Spada Lunga a due mani nell'originale usa 1d10+6 contro la versione a una mano 1d8+5, benché il modificatore di Forza sia +5;
- `Wolfwere`, p.156, Spada Lunga a due mani 1d10+5 contro la versione a una mano 1d8+4 e modificatore di Forza +4.

La fedeltà locale delle **eccezioni** è confermata dalla fonte, ma le incongruenze editoriali richiedono un criterio di trattamento esplicito; fino ad allora mantenere `pending` e `completa_con_anomalia_fonte`, non modificare numeri tacitamente. **Tutte le 56 schede necessitano comunque della seconda verifica indipendente** prima della certificazione `ai_verified`. Lo stato `translated` non attesta una revisione semantica indipendente di ogni caratteristica o incantesimo.

Conteggio globale Supabase al checkpoint: 1.500 mostri, 391 `translated`, 201 `processing`, 908 `not_required`, solo 5 `ai_verified` (Minecraft). I manuali ancora in `processing` sono `bomt_2023_en` (27), `mot_2020_en` (49), `ps_mpp_2023_en` (53), `sjbam_2022_en` (72). La prossima fase di traduzione è **The Book of Many Things**, i cui primi nove record sono già in `translated/pending`. Nessun merge, deploy o aggiornamento a `main`.


## Book of Many Things — 36/36 translated, 22 ottobre 2026

Manutenzione post-interruzione completata in lettura/scrittura condizionale sui **27 record** ancora `processing` del manuale `The Book of Many Things`, identificatore logico `bomt_2023_en`. Originale utente **privato** `1016064385-The-Book-of-Many-Things-Unknown-Z-library-sk-1lib-sk-Z-lib-sk.pdf`, 195 pagine, SHA256 `6dd24843c9766ad10d3a6098afb90de0680bf285efc0f73b9fa281085b946146`. PDF e testi estesi NON inseriti nel repository pubblico.

Un unico ciclo in questo turno ha aggiornato come `translated/pending` i 27 ID esistenti, sulle pagine 92–190 e mantenendo intatti `source_*`, ID, user ID e `translation_review_status=pending`: Aspirante della Cometa, Ierofante della Cometa, Iniziato della Cometa, Oddlewin, Pazrodine, Fantasma di Gremorly, Minotauro Archeologo, Minotauro Infiltrato, Brusipha, Divoratore del Respiro, tre Campioni Tetri (Massacro, Desolazione, Pestilenza), Segugio della Schiera Tetra, Aurnozci, Hulgaz, Malaxxix, Megalera del Destino, Falco della Schiera Tetra, Medusa Ierofante, Presagio Vivente, Riffler, Ragno della Rovina, Bestia dagli Artigli, Avvoltoio Mannaro, Asteria, Euriale. Conservate le abilità, resistenze, azioni, bonus, reazioni, capacità leggendarie e di tana dove presenti; `velocita` metriche.

Tutti i 27 UPDATE erano guardati con ID, `source_name`, logical ID, SHA, pagina fisica, stato `processing/pending`, assenza di lease, `updated_at` atteso e anti-collision check del nome normalizzato. Ognuno ha restituito **esattamente una riga** aggiornata.

Readback SQL sul **manuale intero 36/36**:
- 36 ID distinti, 36 nomi sorgente distinti, 36 nomi italiani normalizzati distinti, 36 hash origine coerenti, zero lease
- `translated=36`, `processing=0`, `translation_review_status=pending=36`, `ai_verified=0`
- 36/36 GS e sei caratteristiche coerenti con `source_attributes`; 35/36 HP testualmente identici, **unica eccezione `Deck Defender` (p.73), formula dinamica `5 + five times your level` tradotta `5 + 5 × il livello` e mantenuta, non fabbricata**
- zero `ft` nel campo `velocita`, zero descrizioni sotto 160 caratteri o testo completo sotto 650

Questa verifica **strutturale e di coerenza con i dati di importazione non è la seconda lettura indipendente della fonte per tutte e 36 le schede**. Non promuovere a `ai_verified` senza audit semantico completo, traccia della fonte, fingerprint, dry-run e readback atomico. Situazione globale al checkpoint: **1.500 mostri, 418 `translated`, 174 `processing`, 908 `not_required`, 5 `ai_verified`**. I manuali con traduzioni ancora necessarie sono `mot_2020_en` (49), `ps_mpp_2023_en` (53) e `sjbam_2022_en` (72). Nessun merge né deploy; `main` e `develop` restano separati.


## Mythic Odysseys of Theros — avvio traduzioni dalla scansione, 22 ottobre 2026

Fonte utente: `953338587-Mythic-Odysseys-of-Theros.pdf`, 262 pagine e PDF immagine **senza text layer digitale**, identificatore `mot_2020_en`, SHA256 `0047c3322ca592c5833861a816d4404311c30165ecd4b4e70cc697de30d3a757`. Sono state renderizzate e **lette visivamente** le pagine 209–213. Non sono stati impiegati OCR automatici né create schede da pagine non consultate.

**Sei candidate italiane registrate su sei ID esistenti**:
- p209 `ref_44d9234311b4f98209cb43c66d89d0a6` — Amphisbaena → **Anfisbena**, con entrambi i morsi e i due capi;
- p210 `ref_c6ea7f3b25c21834da0af974041d5325` — Anvilwrought Raptor → **Rapace Forgiato sull'Incudine**, variante famiglio;
- p211 `ref_c3e3117cb0a57bc25d768ed962d1706b` — Bronze Sable → **Zibellino di Bronzo**, falsa apparenza e attacco sorpresa;
- p212 `ref_07a398c1df82be51adbcaff530463f64` — Burnished Hart → **Cervo Brunito**, carica e corpo incandescente;
- p212 `ref_b21f68764e8761f887cb8cc3be852ec2` — Gold-Forged Sentinel → **Sentinella Forgiata d'Oro**, Carica e Ritorsione agli Incantesimi;
- p213 `ref_ea80ec3e876675a6a1aea68cdbe50bae` — Archon of Falling Stars → **Arconte delle Stelle Cadenti**, incantesimi e tre azioni leggendarie.

Ogni UPDATE era vincolato da ID, nome originale, fonte, SHA, pagina, timestamp `2026-10-20 20:19:59.166948+00`, `processing/pending`, lease vuoto e controllo anticollisione; ciascuno ha restituito **una sola riga aggiornata**. Nessuna alterazione di `source_*` o di `ai_verified`.

**Readback:** Theros `6/49 translated`, `43 processing`, `0 ai_verified`, 49 nomi normalizzati univoci. Per le sei candidate: HP `6/6`, GS `6/6`, sestine caratteristiche `6/6` e SHA `6/6` coerenti con `source_attributes`; zero velocità ancora in piedi. Nessuna certificazione di seconda revisione è stata simulata. Situazione globale: `1500` mostri, `424 translated`, `168 processing`, `908 not_required`, `5 ai_verified`. Nessun merge né deploy, manuali `main` e `develop` separati.

**Prossima pagina da esaminare visivamente**: 214 e seguenti di Mythic Odysseys of Theros.


## Theros, secondo gruppo scansioni 214–218 — 22 ottobre 2026

La lettura visiva del PDF fonte privato `953338587-Mythic-Odysseys-of-Theros.pdf`, SHA256 `0047c3322ca592c5833861a816d4404311c30165ecd4b4e70cc697de30d3a757`, è proseguita sulle pagine 214–218. Sei ulteriori record **già esistenti** sono stati aggiornati condizionalmente come `translated/pending`, senza creare duplicati:
- p214 `ref_412d16d07ef1c70669a15a1c3b4dd86e` Ashen Rider → **Cavaliere delle Ceneri**, inclusa cavalcatura, aura, 3 opzioni leggendarie;
- p215 `ref_7fb391ead63eb7daefdae87a8450626a` Winged Bull → **Toro Alato**;
- p215 `ref_176ac9c4861e8223127aff6988dcefc2` Winged Lion → **Leone Alato**;
- p216 `ref_7f2482b2acf438e676e54f01b6778164` Two-Headed Cerberus → **Cerbero a Due Teste**;
- p216 `ref_ce0b0d476c8dacb2ddf8753d7056e9af` Underworld Cerberus → **Cerbero del Regno dei Morti**;
- pp217–218 `ref_9a4388bb4f2f1925ca5506c5a4ccb456` Theran Chimera → **Chimera di Theros**, incluse le **quattro tabelle da 1d4** (`varianti_chimera` con 4 opzioni ciascuna: corpo, testa, coda e soffio).

Ogni UPDATE era condizionato da ID, nome originale, logical source, hash PDF, pagina, stato `processing/pending`, timestamp precedente, lease assente e controllo anticollisione; ciascuno ha restituito un singolo ID `translated/pending`. **Readback nuovo stato Theros: 12/49 translated, 37 processing, 0 ai_verified; 49 ID, nomi originali e norm univoci.** Controllati tutti i 12 candidati: **12/12 HP, GS, sei punteggi caratteristiche, SHA coerenti** con i campi fonte importati; 0 velocità in piedi. Globale: 1500 mostri, 430 tradotti, 162 ancora processing, 908 not_required, 5 ai_verified. Restano 37 schede di Theros da trascrivere dalla scansione; la revisione semantica indipendente è separata dalla traduzione, non forzata.

Nessun merge, deploy o modifica a `main`; PR #598 rimane draft verso `develop`.


## Theros, pages 219–224, 22 ottobre 2026

Sette nuove candidate italiane importate sui **record preesistenti** con ogni UPDATE condizionato a ID, `source_name`, pagina, SHA, `updated_at`, lease non attivo, `processing/pending` e anti-duplicazione; ciascuno ha restituito un singolo ID.

- p219 Colossus of Akros (`ref_7d34b586d6f9b730a76661e65c5c545d`) → **Colosso di Akros** (crollo distruttivo, assorbimento del fuoco, spada, lancia, Fiamme di Akros).
- p220 Abhorrent Overlord (`ref_4087a786f6d2fade70211cb88721f731`) → **Signore Abominevole** (avidità dell'oro, incantesimi innati, Tempesta di Corvi).
- p221 Eater of Hope (`ref_c1490aa057e696f84d84eb984454975e`) → **Divoratore di Speranza** (Soffio di Disperazione e durata della maledizione).
- p222 Nightmare Shepherd (`ref_e4d18aaf610ce430ba5dcaca92b471fb`) → **Pastore degli Incubi** (aura +5 ai Non morti; evoca 1d6 Ombre **senza Debolezza alla Luce Solare**).
- p223 Flitterstep Eidolon (`ref_ad5c934b2663923e488c038e0d920afb`) → **Eidolon Passo Guizzante**, incluso teletrasporto in Multiattacco.
- p223 Ghostblade Eidolon (`ref_15c04a095d4e6a625cd22a799e8ffb6b`) → **Eidolon Lama Spettrale**.
- p224 Fleecemane Lion (`ref_76f1b0062a391268023a256f216a85c5`) → **Leone dal Vello d'Oro** (2 azioni leggendarie e ruggito).

Originale scansito `953338587-Mythic-Odysseys-of-Theros.pdf`, pagine controllate visivamente, SHA `0047c3322ca592c5833861a816d4404311c30165ecd4b4e70cc697de30d3a757`.

Readback Supabase: **Theros 19/49 translated, 30 processing; 49/49 ID e nomi normalizzati distinti; 19/19 HP, GS e 6 caratteristiche coincidono con i `source_attributes` originali; 19/19 SHA coerenti; zero velocità in ft; 19/19 `translation_review_status=pending`**. Global: 1500 mostri, 437 `translated`, 155 `processing`, 908 `not_required`, 5 `ai_verified`. Nessun merge né deploy. Prossimo record `Doomwake Giant`, p225.


## Theros, pagine 225–230 — avanzamento 27/49

Otto ulteriori schede italiane `translated/pending` generate dalla lettura visiva del PDF ufficiale utente `953338587-Mythic-Odysseys-of-Theros.pdf`, SHA `0047c3322ca592c5833861a816d4404311c30165ecd4b4e70cc697de30d3a757`, con UPDATE guarded su ID già esistenti (nessun inserimento e nessuna modifica a `source_*`):

- p225 Doomwake Giant → **Gigante del Risveglio Funesto** `ref_8ab9f4bc75ca53d5566dc50b9594424b`: aura CD18, soffio, danni.
- p226 Hundred-Handed One → **Centimane** `ref_12bc281a83b0e7a07a2db562c974f689`: più reazioni per round, Deviare Attacco +5 CA.
- p227 Aphemia → **Aphemia, il Canto Dissonante** `ref_50c513d2afe6fe191462960143212f37`: canti distinti per Umanoidi e Non morti, mantenimento con azione bonus, tiri salvezza e immunità temporanea.
- p228 Blood-Toll Harpy → **Arpia del Tributo di Sangue** `ref_3b2d9f141b6be50554ed31abafb40ebf`.
- p228 Hippocamp → **Ippocampo** `ref_a0dce6847dd47c14de650caf35ccc88b`.
- p229 Akroan Hoplite → **Oplita di Akros** `ref_57f6772ddbb7c14dacad6ff16dc8df25`, incluso Tenere la Linea e tabella nomi unità d8.
- p230 Meletian Hoplite → **Oplita di Meletis** `ref_c7028a6e3a2e672f21180856f2b9c72d`, inclusi incantesimi di 3° livello e nomi unità. **L'originale definisce la Lancia un attacco "Melee or Ranged" senza fornire la gittata**: l'omissione è segnalata in `attributes.anomalie_fonte` senza inventare metri, resta `pending`.
- p230 Setessan Hoplite → **Oplita di Setessa** `ref_c9b35222793d8516960c946558d50e3a`, incluso bonus Tattiche di Branco quando l'alleato è entro 1,5 m dall'oplita (non dal bersaglio) e nomi unità.

Readback SQL: **Theros 27/49 `translated`, 22 `processing`, 49/49 ID e nomi normalizzati univoci, 0 `ai_verified`**; dei 27 tradotti **27/27** HP, GS, sei caratteristiche e hash sorgente coerenti con i `source_attributes` importati; **0 ft** nel campo velocità. Globale 1500 mostri, 445 `translated`, 147 `processing`, 908 `not_required`, 5 `ai_verified`. Prossimo `Ironscale Hydra` e `Polukranos`, p232. La seconda verifica indipendente non è stata eseguita su questi record, non segnalarli come certificati.


## Theros, pagine 232–240 — checkpoint 37/49 translated

Dieci candidate italiane `translated/pending` aggiunte tramite UPDATE condizionali ai record preesistenti, da PDF `953338587-Mythic-Odysseys-of-Theros.pdf` visualizzato pagina per pagina, hash `0047c3322ca592c5833861a816d4404311c30165ecd4b4e70cc697de30d3a757`:
- p232 Ironscale Hydra → **Idra dalle Scaglie di Ferro** (`ref_7271362f13e614322e676708029d121c`), ricrescita delle teste interrotta da qualsiasi danno da fuoco;
- p232 Polukranos → **Polukranos, Divoratore del Mondo** (`ref_830a91b291dda38ebd9f2a150d4e528c`), ricrescita interrotta solo da **40 o più danni da fuoco** e 3 azioni leggendarie;
- p233 Leonin Iconoclast → **Leonin Iconoclasta** (`ref_a363bebf2344e04dac58fd4727c2f1c9`);
- p234 Nyx-Fleece Ram → **Montone dal Vello di Nyx** (`ref_28598e0c63a83cdfac607594f725fb91`), con intera tabella dei **sei poteri del vello magico**;
- p236 Alseid → **Alseide** (`ref_96dd8703818a4c623f66258af5a57593`);
- p236 Lampad → **Lampade** (`ref_7f747e4167d875628b2d047fcae0a7eb`), **anomalia fonte**: Tocco Necrotico riporta **19 (1d10+4)**, incongruenza aritmetica non corretta arbitrariamente;
- p237 Naiad → **Naiade** (`ref_5e32f9fc27350dfb98708b4de19faf27`);
- p238 Oread → **Oreiade** (`ref_2054a8e18016c6bf244a80f3c8d83d0e`), **anomalia fonte**: Dardo di Fuoco riporta **15 (1d10)**, matematicamente incompatibile, da risolvere con fonte ufficiale o errata;
- p239 Oracle → **Oracolo** (`ref_96c29562cee6a4499dd93aa2c1477ed1`);
- p240 Phylaskia → **Filaschia** (`ref_a6624ad953cbc60cfeb20fc86d452b85`).

Readback SQL **37/49 translated**, 12 `processing`, 0 `ai_verified`. 49 ID, 49 nomi originali e 49 nomi normalizzati univoci. Per i 37 tradotti **37/37** hash fonte, HP, GS e sei caratteristiche coerenti, zero `ft` nelle velocità. Tutte le eccezioni editoriali segnalate rimangono `pending` come le altre schede, nessuna certificazione fittizia. Le 12 restanti sono Returned Drifter, Returned Palamnite, Returned Sentry, Satyr Reveler, Satyr Thornbearer, Triton Shorestalker, Triton Master of Waves, Typhon, Woe Strider, Arasta, Hythonia, Tromokratis. Nessun merge né deploy.


## Theros 49/49 — chiusura della traduzione, 22 ottobre 2026

L'ultimo gruppo di dodici candidate già importate, pagine 241–255 del PDF privato `953338587-Mythic-Odysseys-of-Theros.pdf`, SHA256 `0047c3322ca592c5833861a816d4404311c30165ecd4b4e70cc697de30d3a757`, è stato completato usando UPDATE guarded su ID, origine, pagina e timestamp preesistenti, con blocco su lease attivo e omonimi:

- p241 Returned Drifter → **Reincarnato Errante** `ref_98f5653044a6916953f50a8c51c299bf`;
- p242 Returned Palamnite → **Reincarnato Palamnita** `ref_f6198bdbf194a2bb176f1d9eb3316294`, inclusa variante **Kakomantis**;
- p242 Returned Sentry → **Reincarnato Sentinella** `ref_08183a99917530a976a43732bb88c550`;
- p243 Satyr Reveler → **Satiro Festaiolo** `ref_6405cd278dd637c0a031ed1f47dc1350`;
- p244 Satyr Thornbearer → **Satiro Portaspine** `ref_f2a865ed9fbc173b8a948e8984e875bf`;
- p245 Triton Shorestalker → **Tritone Predatore Costiero** `ref_a327d944a06bb32c5d02d4815f636046`;
- p246 Triton Master of Waves → **Tritone Maestro delle Onde** `ref_34d7068064faa765243c06b59eedddfe`;
- p247 Typhon → **Tifone** `ref_582b8918332d5b1bb638db125916b75d`;
- p248 Woe Strider → **Camminatore del Dolore** `ref_14c02f8852754566701d885d0595aca7`, con cono antimagia;
- pp249–251 Arasta → **Arasta** `ref_7aa6ace61abf9d22afc9fe323e70fc3c`, tratto mitico Armatura di Ragni (+200 PF recuperati, +100 PF temporanei), tre azioni mitiche, due azioni di tana, due effetti regionali; 66.000 PE come incontro mitico;
- pp252–254 Hythonia → **Hythonia** `ref_e1cfb9e677fbd2c45232da2d933edb44`, tratto mitico Cambio di Pelle (+199 PF), due azioni mitiche, due azioni di tana, tre effetti regionali; 36.000 PE come incontro mitico;
- pp255–256 Tromokratis → **Tromokratis** `ref_5c3ba5fe2e46bc15a2ef1b698b382949`, quattro cuori indipendenti CA22, 100 PF ciascuno, due azioni mitiche, 180.000 PE come incontro mitico.

**Readback strutturale finale di Supabase**: `mot_2020_en=49/49 translated`, `0 processing`, `49 pending`, `0 ai_verified`; 49 IDs/nominativi originali/nomi normalizzati univoci; 49/49 formula HP, GS, sei caratteristiche, hash PDF coincidono con source data; 0 velocità in feet, 0 translation lease attive. Alcune anomalie editoriali dell'originale, già segnalate in singole schede, vanno risolte nella **seconda revisione semantica indipendente prima della certificazione**. Questo checkpoint non certifica contenuti semantici al di là della prima traduzione e verifiche strutturali.

**Progetto complessivo al readback finale: 1.500 mostri; 467 translated, 125 processing, 908 not_required; soltanto 5 ai_verified preesistenti (Minecraft).** Gli unici manuali con `processing` rimasti sono `sjbam_2022_en` **72** e `ps_mpp_2023_en` **53**. Nessun merge, deploy, cambio a main o promozione forzata dei record.


## Avvio Boo's Astral Menagerie, pp.8–13; controllo di seconda lettura Aartuk

Manuale privato `645286721-Spelljammer-Boo-s-Astral-Menagerie-5e-pdf.pdf`, 66 pagine, SHA256 **`24c0025969bbeb09e01fbf7ed7969ce2e21d2926a6f4e5f4b1c566d0597e067e`** verificato sui byte materializzati. Font embedded con estrazione di testo non affidabile; fonte verificata mediante rendering delle pagine 8, 9, 11, 12, 13.

Al readback, già **8/72 schede `translated/pending`** nel manuale `sjbam_2022_en` e 64 `processing`: Aartuk elder, priest, warrior; Astral elf aristocrat, commander, honor guard, star priest, warrior. **72 ID, 72 nomi normalizzati univoci, 8/8 HP e GS coerenti con `source_attributes`**. Non sono state sovrascritte le schede già aggiornate: gli UPDATE protetti hanno restituito 0 righe quando lo stato era nel frattempo diventato `translated`.

**Correzione effettiva da seconda lettura indipendente**: scheda `Aartuk priest` `ref_8b1d8cda85854db22cfd36aa018cac78`, PDF p.9, azione bonus `Lingua (Ricarica 6)`. Il testo italiano già salvato riportava **CD di fuga 12**, mentre l'originale del sacerdote riporta **escape DC 11**, a differenza del guerriero che riporta 12. Riparata in modo condizionale **CD 12 → 11** nella struttura `attributes.azioni_bonus[1].descrizione` e in `full_text`, con readback che conferma il nuovo valore. Separatamente aggiornato il nome di incantesimo `revivify` da `rinascita (revivify)` a `rianimare` nella scheda del sacerdote, per coerenza terminologica italiana. Nessuna modifica al campo di provenienza o al `translation_review_status=pending`, poiché il secondo controllo complessivo di tutte le capacità della scheda non è ancora concluso.

**Globale al readback:** 1.500 mostri, 475 `translated`, 117 `processing`, 908 `not_required`, 5 `ai_verified`. Theros resta **49/49 translated/pending**. Dopo Boo restano 53 record `processing` in Morte's Planar Parade, per cui occorre ancora individuare un PDF sorgente accessibile. Nessun merge o deploy, `main` invariato.


## Boo's Astral Menagerie, pp.14–21: checkpoint 16/72 (22 ottobre)

Dopo le prime otto schede, otto ulteriori `UPDATE` guarded completati da PDF sorgente privato `645286721-Spelljammer-Boo-s-Astral-Menagerie-5e-pdf.pdf`, SHA256 `24c0025969bbeb09e01fbf7ed7969ce2e21d2926a6f4e5f4b1c566d0597e067e`, rendering visuale delle pagine, senza OCR e senza nuovi record:
- p14 Autognome `ref_a7955b4d908b218ce543ada79c52c69a`: tabella completa Malfunzionamenti 1d20 (5 intervalli, inclusi 15–16 testa e 17–20 esplosione);
- p15 Braxat `ref_bb6ce244a1a45065451f3885ec51ecb9`: CA include Intellect Fortress, Psionic Shield contro attacchi e dardo incantato;
- p16 B'rogh `ref_fb9918a26afbde3db919aeda108e939d`: 4 attacchi pugno, 2 rocce, squarciamento con CD di fuga 16;
- p17 Chwinga astronaut → **Chwinga Astronauta** `ref_b1305e5629c979f739f0881ff5eaed3e`: due doni speciali opzionali, rifugio e incantesimi;
- p18 Cosmic horror → **Orrore Cosmico** `ref_3c73b994a8d5fe437bcb81542d2957e7`: 3 azioni leggendarie, sussurri psichici e attacchi multipli;
- p19 Dohwar `ref_6435efdcf85f80c75631d41aa4429c4e`: Fusione telepatica, magie e morso;
- p20 Esthetic → **Estetico** `ref_afcd38fa7410e5a9fb11b130e94b4778`: nave vivente, Urlo Inibitore sui timoni spelljammer con 2d10 giorni/minuti a seconda del tiro, proprietà della nave;
- p21 Eye monger → **Mercante Oculare** `ref_defa479dd177a812d58be36fea8416c2`: Stomaco Antimagico e Morso con conseguenze dell'essere inghiottiti.

Tutti gli UPDATE hanno restituito un singolo ID già esistente `translated/pending`. Il readback sull'intero manuale segnala **16/72 translated**, **56 processing**, 72 ID unici, 72 nomi normalizzati univoci, 0 `ai_verified`; sui 16 tradotti **16/16 HP, GS, sei caratteristiche e hash PDF coerenti con source_attributes**, 0 velocità residue in piedi. Tutte le nuove schede restano `translation_review_status=pending`: la seconda lettura semantica completa e la certificazione sono operazioni distinte. Per `Aartuk priest` p9 è stata corretta in precedenza una CD di fuga da 12 a 11 sulla base dell'originale.

Global: **1500 mostri, 483 translated, 109 processing, 908 not_required, 5 ai_verified**. Prossima pagina e scheda **Feyr**, p22; una volta completato questo manuale resta `ps_mpp_2023_en` con 53 `processing`. Nessun merge o deploy, `main` separato da `develop`.


## Boo's Astral Menagerie, p22 — checkpoint di interruzione protetto

Il record esistente `Feyr` `ref_6b5686bffec51d79ebea1c9a0b74a560` (p22, fonte SHA256 `24c0025969bbeb09e01fbf7ed7969ce2e21d2926a6f4e5f4b1c566d0597e067e`) è stato convertito in italiano come `translated/pending` con UPDATE condizionale a ID, hash, pagina, timestamp iniziale, fonte, lease vuoto e assenza di duplicati; UPDATE ha restituito una sola riga. Completati Morso Terrificante, Tentacolo con presa, Invisibilità e Nutrimento d'Incubo. **Readback Boo: 17/72 translated, 55 processing, 72 ID e normalized_name distinti**.

Esaminata anche la fonte di `Gaj`, PDF p23, ma una successiva richiesta di scrittura è stata bloccata dai controlli del connettore **prima dell'UPDATE**; query in sola lettura conferma `Gaj` ancora `processing`, senza modifiche. **Prossimo record** `Gaj`, p23. Nessuna certificazione aggiuntiva né merge/deploy; i testi privati restano soltanto in Supabase, non su GitHub pubblico.


## Boo's Astral Menagerie pp23–25 — checkpoint 21/72

- PDF p23 `Gaj` (`ref_de1e220d135cde37d713360389901e33`) è stato aggiornato **una volta** con guarded UPDATE `processing/pending → translated/pending`, includendo Mandibole, Antenne Psichiche e Paralizzare (Ricarica 6), dopo un tentativo di scrittura bloccato dai controlli connettore. La successiva esecuzione protetta ha restituito l'ID aggiornato.
- Durante la prosecuzione risultano `translated/pending` anche p24 `Giff shipmate` → **Marinaio Giff** e p25 `Giff shock trooper` e `Giff warlord`. **Non sovrascritti**: verificato in sola lettura che la scheda del Marinaio Giff riproduce le formule e CD del PDF per moschetto, spada lunga, granata a forza con 1d6 per la disponibilità, Conoscenza delle Armi da Fuoco e Fermo come una Roccia.

**Readback Supabase Boo**: 72 record, 21 `translated`, 51 `processing`, 0 `ai_verified`, 72 ID e 72 nomi normalizzati distinti; 21/21 HP, GS e sei punteggi caratteristiche coincidono con `source_attributes`; 0 ft nel campo velocità. **Globale**: 1500 mostri, 488 `translated`, 104 `processing`, 908 `not_required`, 5 `ai_verified`. Prossimo record da cercare dopo la pagina 25, con priorità all'ordine delle pagine. Non procedere a certificazioni automatiche, merge o deploy; seconda verifica indipendente `pending` su tutte le nuove candidate.



## Boo's Astral Menagerie — pp14–43, avanzamento traduzione 43/72

Conservato il manuale originale in Biblioteca, `645286721-Spelljammer-Boo-s-Astral-Menagerie-5e-pdf.pdf`, SHA-256 `24c0025969bbeb09e01fbf7ed7969ce2e21d2926a6f4e5f4b1c566d0597e067e`. Pagine visualizzate direttamente, PDF con text layer non affidabile. Dall'ultimo audit a 8/72, tradotti tramite `UPDATE` condizionali, singola riga restituita per record e zero duplicazioni:

- p14 `Autognome` → **Autognomo** (presso `ref_a7955b4d908b218ce543ada79c52c69a`), incluse 5 uscite dei malfunzionamenti 1d20.
- p15 `Braxat` → **Braxat**; p16 `B’rogh` → **B’rogh**.
- p17 `Chwinga astronaut` → **Chwinga Astronauta** con doni opzionali.
- p18 `Cosmic horror` → **Orrore Cosmico** con 3 opzioni leggendarie.
- p19 `Dohwar` → **Dohwar**; p20 `Esthetic` → **Estetico**.
- p21 `Eye monger` → **Mercante Oculare**; p22 `Feyr` → **Feyr**. Queste due schede risultavano già tradotte da altri step al readback, non riscritte.
- p23 `Gaj` → **Gaj**, già scritto quando UPDATE guardato è stato eseguito; non sovrascritto.
- p24 `Giff shipmate` → **Marinaio Giff**; p25 `Giff shock trooper` → **Assaltatore Giff**; p25 `Giff warlord` → **Signore della Guerra Giff**.
- p27 `Githyanki buccaneer` → **Bucaniere Githyanki**, `Githyanki star seer` → **Veggente delle Stelle Githyanki**, `Githyanki xenomancer` → **Xenomante Githyanki**.
- p28 `Hadozee explorer` → **Esploratore Hadozee**; p29 `Hadozee shipmate` → **Marinaio Hadozee**, `Hadozee warrior` → **Guerriero Hadozee**; incluse planata e reazioni di riduzione danni.
- p30 `Jammer leech` → **Sanguisuga Spelljammer**, incluse penalità al timone e reazione; p31 `Kindori` → **Kindori**.
- pp32–35 `Ancient lunar dragon` → **Drago Lunare Antico**, `Adult lunar dragon` → **Drago Lunare Adulto**, `Young lunar dragon` → **Drago Lunare Giovane**, `Lunar dragon wyrmling` → **Cucciolo di Drago Lunare**. Incluse azioni leggendarie ed effetti regionali per antico/adulto. **Anomalia fonte adulta**: attacco Coda +14 nella stampa p34 mentre gli altri attacchi mostrano +11; conservato e marcato `completa_con_anomalia_fonte`, seconda lettura ancora necessaria.
- p36 `Megapede` → **Megapede**, p37 `Mercane` → **Mercane**, p38 `Murder comet` → **Cometa Assassina** (variante col creatore), p39 `Neh-thalggu` → **Neh-thalggu** (tabella 12 incantesimi secondo numero di cervelli), p40 `Neogi hatchling swarm` → **Sciame di Cuccioli Neogi**, p41 `Neogi pirate` → **Pirata Neogi**, `Neogi void hunter` → **Cacciatore del Vuoto Neogi**, pp42–43 `Plasmoid boss` → **Capo Plasmoide**, `Plasmoid explorer` → **Esploratore Plasmoide**, `Plasmoid warrior` → **Guerriero Plasmoide**.

**Readback verificato**: `sjbam_2022_en` 72 record, 43 `translated`, 29 `processing`, 72 nomi normalizzati e ID unici, 72 `translation_review_status=pending`, 0 `ai_verified`. Sui 43 tradotti 43/43 formule PF, GS e caratteristiche coerenti con importazione, 0 velocità in piedi. Totale globale 1500 mostri, 510 tradotti, 82 processing, 908 `not_required`, 5 `ai_verified` (Minecraft). Prossimo `Psurlon` p44. Gli UPDATE hanno richiesto match di ID, nome originale, fonte, pagina, hash e stato `processing/pending`, `updated_at` preesistente, lease vuoto, nessuna collisione di nome. Questi audit sono strutturali: **non equivalgono a certificazione indipendente di tutte le regole**, per cui resta `pending`. Nessun merge, deploy o cambiamento a `main`.


## Boo's Astral Menagerie — 72/72 tradotti, controllo finale 22 ottobre 2026

Dopo il precedente checkpoint 43/72, verificati e tradotti i rimanenti 29 record dei blocchi pp44–64 nel PDF privato `645286721-Spelljammer-Boo-s-Astral-Menagerie-5e-pdf.pdf`, logical source `sjbam_2022_en`, SHA `24c0025969bbeb09e01fbf7ed7969ce2e21d2926a6f4e5f4b1c566d0597e067e`. Aggiornamenti **solo su ID esistenti**, condizionati da ID/nome originale/logical source/SHA/pagina/updated_at/stato `processing/pending`/lease vuoto/assenza collisioni del normalized_name. Nessuna aggiunta di fonte privata o traduzioni complete a GitHub pubblico.

- p44 `Psurlon`; p45 `Capo Psurlon`, `Psurlon Impostore` (inclusa imitazione).
- p47 `Reigar` (incluso `talarith`, golem ed evocazione).
- p49 `Scavver Bruno`, `Scavver Grigio`, `Scavver Notturno`, `Scavver del Vuoto` (varianti di Morso e ingestione).
- pp50–53 `Drago Solare Antico`, `Drago Solare Adulto`, `Drago Solare Giovane`, `Cucciolo di Drago Solare` (soffio fotonico, leggendarie e qualità del nucleo stellare, dove previste).
- p54 `Pagliaccio Spaziale` (Pistola a Raggi, Forma Fantasmatica); p55 `Anguilla Spaziale`, `Guppy Spaziale`; p56 `Criceto Spaziale Gigante`, `Criceto Spaziale`.
- p57 `Mollymawk Spaziale`, `Suino Spaziale` (CA con/senza bardatura); p58 `Ssurran Profanatore`, `Ssurran Avvelenatore`; p59 `Apparizione di Luce Stellare` (Possessione limitata all'Astrale).
- p60 `Gladiatore Thri-kreen`, p61 `Cacciatore Thri-kreen`, `Mistico Thri-kreen`; p62 `Vampirata`; p63 `Capitano Vampirata`, `Mago Vampirata`; p64 `Zodar` (Desiderio con autodistruzione).

**Readback SQL conclusivo**: 72/72 `translated`; zero `processing`; 72/72 ID, nomi sorgente, nomi italiani normalizzati, hash PDF univoci/coerenti; zero lease; 72/72 PF, GS, sei caratteristiche coincidenti con `source_attributes`; zero `ft` nel campo `velocita`, zero descrizioni `full_text` inferiori a 150 caratteri. Tutte le 72 **translation_review_status=pending**, **0 ai_verified**: il controllo strutturale non dimostra una seconda revisione semantica completa di tutto il manuale e non autorizza la certificazione. Nel riepilogo globale: **1500 record**, `translated=539`, `processing=53`, `not_required=908`, `ai_verified=5`. **L'unica fonte con `processing` rimasta è `ps_mpp_2023_en` (Morte's Planar Parade, 53 schede)**.

PR #598 rimane una bozza verso `develop` e non è stata mergiata; `main` invariato; nessun deploy.


## Boo's Astral Menagerie — conferma 72/72 e ripartenza Morte's Planar Parade 12/53

**Boo**, logical source `sjbam_2022_en` e SHA256 `24c0025969bbeb09e01fbf7ed7969ce2e21d2926a6f4e5f4b1c566d0597e067e`: finale **72/72 `translated`**, **0 `processing`**, **72/72** ID, `source_name` e `normalized_name` univoci; HP/GS/6 caratteristiche **72/72** coerenti con lo snapshot di provenienza; zero velocità in `ft`; **72 `translation_review_status=pending`**, 0 `ai_verified`. Ultime schede `Vampirate` `ref_de14a53574a6c98d19d31a4d58ff6b59`, `Vampirate captain` `ref_cc0eac0e4581be4bcf3e11166116a9fb`, `Vampirate mage` `ref_7503296202e5245e7805602adf60a4d4` e `Zodar` `ref_1d2b5c82e32478b973b513a4a9d85c45` tutte lette in DB come `translated/pending` (p62–64).

Recuperata da Library dell'utente, **senza rete**, la sorgente Planescape `762692978-D-D-5e-Planescape-Adventure-in-the-Multiverse.pdf` (262 pagine), SHA256 **`61392d7a3ab2241dce67b1027c4830e0b3e9431d224f5a1619c6f5257bd427b1`**, hash che corrisponde esattamente a `source_refs[0].physical_sha256` dei 53 mostri `ps_mpp_2023_en`.

**Morte 12/53** `translated/pending`, 41 `processing/pending`, zero certificati: p213 **Arconte Segugio** `ref_2088ec695258e26b73a3df3b35158164`; p214 **Arconte Lanterna** `ref_5e8fa3b84e6abfec9b768f2b0a19d08e`; p215 **Arconte Guardiano** `ref_e0356b3a567d02e2cee2e8281b75c127`; pp216-17 **Baernaloth** `ref_448550fe8862f3132518d3a96b869d8c`, 3 azioni di tana, 2 effetti regionali, fino a 3 reazioni/round; p218 **Bariaur Vagabondo** `ref_bf1636d6cdbbc6c67f71113ec9951308`; p219 **Ratto Cranico Strillante** `ref_09256e429b25fd2520c6e7da9f1b143b`, **Sciame di Ratti Cranici Strillanti** `ref_ad6091062ceb7a9938940aa681c12690`; p220 **Dabus** `ref_797ffcd0e4c87d14e18b430dd0851d3a`; pp221-22 **Tessitore Oscuro** `ref_1c81faa5a49cba4d91b36bd7d36cfafc` con tana e tabella 1d6 bozzoli; pp223–25 **Demodand Farastu** `ref_47ad88e788e4ad7be56af070334c8af8`, **Demodand Kelubar** `ref_c019ed05646a4966b5ec8b95117d0403`, **Demodand Shator** `ref_a997d670eff54bb80f5bd9828338af9d`. Tutte inserite con UPDATE condizionale per ID, nome originale, logical source, SHA, pagina, lease vuoto, `updated_at` e assenza duplicati. Nessuna promozione a `ai_verified` finché non c'è una seconda revisione indipendente delle regole.

**Readback SQL 12/53**: 12/12 HP/GS/6 caratteristiche/hash coerenti, zero `ft` nella velocità, 53 nomi univoci. **Globale**: 1.500 mostri, 551 tradotti, 41 in lavorazione (tutti Morte), 908 `not_required`, 5 certificati. Documentazione di audit sulla PR #598; nessun merge, deploy o modifica `main`.




## Morte's Planar Parade: 54/54 tradotte, inventario corretto (2026-10-22)

**Sorgente privata**: `762692978-D-D-5e-Planescape-Adventure-in-the-Multiverse.pdf` (262 pagine fisiche), SHA-256 `61392d7a3ab2241dce67b1027c4830e0b3e9431d224f5a1619c6f5257bd427b1`, logical source `ps_mpp_2023_en`. La verifica del TOC ufficiale D&D Beyond `https://www.dndbeyond.com/sources/dnd/paitm/mpp` ha fatto individuare **una scheda mancante** dalle 53 originarie: `Mercykiller Bloodhound`, pagina fisica 257 / stampata 60.

Le 53 schede preesistenti sono ora `translated`, con ultima `Doomguard Rot Blade` (`ref_00b963b30582fa1dc639d50ce5a1f12e`) tradotta e salvata dopo una richiesta precedentemente bloccata. Ordine pagine finali: p251 Bleak Cabal Void Soother, Doomguard Doom Lord; p253 Doomguard Rot Blade, Fated Shaker; p254 Fraternity of Order Law Bender; p255 Hands of Havoc Fire Starter, Harmonium Captain; p256 Harmonium Peacekeeper, Heralds of Dust Remnant; p257 Mind's Eye Matter Smith; p258 Society of Sensation Muse; p259 Transcendent Order Conduit, Transcendent Order Instinct. Statblock descrittivi, azioni, bonus e reazioni in italiano, misure metriche, salvati ciascuno con update strettamente condizionale per source, pagina, SHA, status pending e lease libero, readback positivo.

**Fonte incerta non occultata**: `Mercykiller Bloodhound` è un mostro reale nel manuale p257. Stampa originale (e riproduzioni concordi): `Hit Points 104 (16d8 + 48)`, benché la media aritmetica sia `floor(16*4.5 + 48)=120`. Non è stato individuato un erratum ufficiale verificabile. Preservate fedelmente le due cifre stampate; creata una sola scheda `ref_b0374024422a1bab0b63412ba9c1b135`, **Segugio dei Mercykiller**, con ID deterministico, provenance completa, attributi fonte separati dagli attributi tradotti, `translation_status='translated'`, **`review_status='pending'`**, **`translation_review_status='pending'`**, `review_flags=['source_hp_dice_average_conflict']`, `completezza_scheda='completa_con_anomalia_fonte'`. Evitato ogni inserimento duplicato con guardie `NOT EXISTS`; non vi è promozione `ai_verified`. Non usare questo record come certificato finché non è documentata una risoluzione autorizzata dalla fonte.

**Risultati verificati Supabase**: *Morte* 54 record, **54 tradotti**, 0 `processing`, 54 ID e nomi italiani unici, **54/54** corrispondenza PF/GS/6 caratteristiche rispetto allo snapshot fonte, **54/54** SHA corretto, 0 velocità in `ft`, 1 anomalia fonte marcata, 53 `review_status='verified'` e 1 `review_status='pending'`; tutti e 54 `translation_review_status='pending'`, zero `ai_verified`. Audit indipendente di regole e capacità ancora necessario per certificazione. Calcolo del valore medio dei dadi per 48 blocchi a formula esplicita: 47 coerenti, **solo Mercykiller Bloodhound non coerente**; sei blocchi con dadi senza modificatore aritmetico non risultano in quel sottoinsieme, non rappresentano una discrepanza.

**Database globale dopo l'inserimento nuovo**: 1.501 mostri registrati, 593 `translated`, **0 `processing`**, 908 `not_required`, 5 `translation_review_status='ai_verified'` (Minecraft). **Zero processing non è sinonimo di tutte le schede completamente certificate**. Conservata la separazione `develop`/`main`, nessun merge né deploy.

Non inserire il testo integrale della fonte privata nei documenti pubblici del repository.



## Fiendish Folio Vol. 1 — 18/18 completamento seconda revisione (2026-10-22)

Fonte effettiva: PDF privato dell'utente `1064688926-9-D-D-5e-Mordenkainen-s-Fiendish-Folio-Vol-1.pdf`, 22 pagine, SHA256 **`e84ea509258d5d96dbb5d5253accc694f658b1985d66257a1be913b54faeec4a`** calcolato sul file materializzato. Logical source `mff1_2019_en`, `source_refs` originale invariato. Catalogo pubblicazione su D&D Beyond: `https://marketplace.dndbeyond.com/expanded-rules-1/SRC-00057`.

La seconda revisione ha consultato le pagine renderizzate del manuale, distinta dalla trascrizione/traduzione della prima passata, controllando statblock completi (azione, tratto, reazione, altre sezioni se previste), dati fonte, conversioni, durata, portate, CD, danni e descrizioni. Sono state **rilevate e corrette due discrepanze reali** prima della certificazione:
- **Needle Lord**, record `ref_7dc4e48a8e7dbb33522663a06154f784`, pagina PDF 17: in `attributes.immunita_condizioni` mancava la voce italiana **assordato** prevista dal blocco originale `blinded, deafened, exhaustion`. Il valore corretto è `accecato, assordato, indebolimento`.
- **Xill**, record `ref_015d946d6a61eb0bbb9e0d288b54c2cc`, pagina PDF 22: **Escursione Eterea** era presente soltanto in `tratti`, benché richieda espressamente un'azione bonus. Ricollocata in `azioni_bonus` e nella sezione omonima di `full_text`, lasciandone invariata la meccanica; conservato Pungiglione Avvelenato come tratto.

Per tutte e 18 le schede tradotte: PF, GS, sei caratteristiche e hash fonte **18/18** corrispondenti agli originali; **18/18** formule di dadi dei PF coerenti con il valore medio; 0 velocità ancora in `ft`; 18 `completezza_scheda=completa`; nessun duplicato di `normalized_name` nel manuale. Controlli numerici *non* impiegati in sostituzione della seconda lettura degli effetti speciali.

Il passaggio a `ai_verified` è stato eseguito **solo dopo** seconda verifica della pagina originale e preflight individuale di tutte le sezioni. Ogni conferma contiene una ricevuta strutturata in `translation_review_notes`: `record_id`, pagina, SHA256, revisore, periodo, sezioni esaminate e fingerprint; la scrittura atomica è vincolata a `md5(to_jsonb(record)::text)` dello snapshot completo precedente, stato `translated/pending`, `review_status='verified'`, lease vuoto e provenance SHA/pagina. Nessun cambiamento alle `source_*`. Dopo ciascuna scrittura, una nuova SELECT ha confrontato il fingerprint calcolato da capo e gli attributi di fonte. L'implementazione del fingerprint è stata verificata indipendentemente contro il digest `4f47b113...` del Blaze, certificato in precedenza dal backend.

**Readback definitivo:** `mff1_2019_en` **18 record**, **18 `translation_status=translated` / `translation_review_status=ai_verified`**, **zero pending**, 18 ID e nomi univoci, 18 hash review compilati. La certificazione riguarda le 18 schede presenti nell'inventario della fonte, non un'approvazione generica di eventuali altre edizioni.

**Stato globale dopo questo passaggio:** 1.501 mostri, 593 tradotti, 908 `not_required`, 0 in `processing`, **23 `ai_verified`** (5 Minecraft + 18 Fiendish Folio), **570 tradotti ancora `translation_review_status=pending`**. Nessun merge, deploy o modifica a `main`.

Prossimo manuale sottoposto a revisione approfondita: `dsotdq_2022_en` — *Dragonlance: Shadow of the Dragon Queen* (28 schede tradotte), fonte privata disponibile e SHA da ricontrollare. Conservare separate prove di traduzione e certificazione.


## Dragonlance — seconda passata, 12/28 certificati (2026-10-22)

Fonte PDF privata `682072052-5e-DnD-Dragonlance-Shadow-of-the-Dragon-Queen-Mong-IcYPD5.pdf`, SHA-256 `d867631c2344fbc8b1274478f01ad64e2f22989bf340b6b5ed8e001e63ce53a8`, logical source `dsotdq_2022_en`. Verificate visualmente le pagine fisiche 194–208 dell'appendice *Friends and Foes* e 210–215 dell'appendice *Sidekicks*, confrontando con le schede localizzate su Supabase. Nessuna copia integrale del PDF o delle traduzioni è stata inserita nel repository.

**Certificazioni confermate da lettura Supabase: 12 su 28**, 16 `translation_review_status=pending`. Pagine 194 e 195: Anhkolox e Caradoc; p197 entrambi i Death Dragon; p198 Aurak; p199 Baaz; p200 Bozak; p201 Sivak; p202 Dragon Army Officer e Soldier; p203 Dragon Army Dragonnel e Wasteland Dragonnel. Le certificazioni hanno ricevute di verifica della fonte, impronta SHA-256 del contenuto, aggiornamento condizionale allo snapshot precedente e readback della firma; nei readback completati i campi `source_*` risultano invariati. **Kapak** p200 è rimasto `pending` perché la richiesta di certificazione è stata respinta dai controlli di sicurezza del connettore: non simulare una verifica riuscita.

**Due correzioni di significato effettivamente applicate alla riga e riscontrate nella RETURNING SQL**:
- `Lohezet`, `ref_3777d0895dd027a8365d24de4daf977e`, p207, azione `Miasma`: errata la condizione italiana "finché Lohezet non muore" al posto dell'originale "until Lohezet ends it early (no action required)". Nuovo testo: può terminare volontariamente la nube senza usare un'azione, oltre a scadenza di 1 minuto o riutilizzo. Modificati sia `attributes.azioni[2].descrizione` sia `full_text`. Stato conservato `translated/pending`.
- `Lord Soth`, `ref_4fb498e409565537ff476718a27b2055`, p208, tratto `Maresciallo dei Non Morti`: l'originale protegge Soth e gli Undead **da lui scelti**, non solo quelli alleati; nuovo testo "i non morti di sua scelta entro 18 m". Modificati sia `attributes.tratti[2].descrizione` sia `full_text`. Stato conservato `translated/pending`.

**Anomalia fonte identificata, non corretta arbitrariamente**: `Kalaman Soldier` p204, fonte stampata `STR 13 (+1)`, attacco spada lunga `+3` e danno `6 (1d8 + 2)`. Il modificatore indicato nell'espressione di danno `+2` non coincide con il modificatore di FOR `+1`; la scheda locale conserva correttamente i valori stampati e resta in revisione fino a chiarimento della fonte/errata. Questo non autorizza modificare il dato originale.

I controlli di batch eseguiti dopo il checkpoint 12/28 hanno prodotto un blocco di sicurezza lato connettore; nessuna delle successive cinque schede (Istarian Drone, Kansaldi Fire-Eyes, Kender Skirmisher, Lohezet, Lord Soth) è stata dichiarata certificata. Ristabilire l'accesso alle scritture e verificare ogni risultato prima di proseguire. Nessun merge o deploy, `main` invariato.

### Riscontro errata ufficiale Dragonlance

L'errata ufficiale pubblicata su `https://media.dndbeyond.com/compendium-images/errata/DSotDQ/DSotDQ-errata.pdf` (v1.0, 2022, Appendice C) corregge espressamente `Tem Temble` (pagina stampata 213, fisica del PDF privato 215) da `Sleight of Hand +6` a **`Sleight of Hand +4`**. Il record `ref_bb19cf336e2e4fa11df25194204f8794` conserva attualmente nella traduzione il valore `Rapidità di mano +6`, conforme alla stampa ma **non all'errata**. La prima richiesta di correzione diretta è stata bloccata dal connettore: NON registrare la modifica come eseguita, verificare con SELECT prima di qualsiasi nuova scrittura. Il PDF ufficiale non menziona l'anomalia aritmetica del `Kalaman Soldier`, per cui quella resta indeterminata. Le ulteriori correzioni elencate dall'errata alle tabelle di avanzamento dei comprimari (non alle schede base di livello 1) devono essere gestite separatamente se tali tabelle entreranno nell'app.

Ultima SELECT conteggi confermata: Dragonlance 12/28 `ai_verified`, 16 pending; globale 1.501 mostri, 35 `ai_verified`, 558 schede tradotte pending.


## Dragonlance seconda revisione completata — 28/28 ai_verified (2026-10-22)

Origine privata `682072052-5e-DnD-Dragonlance-Shadow-of-the-Dragon-Queen-Mong-IcYPD5.pdf`; SHA256 `d867631c2344fbc8b1274478f01ad64e2f22989bf340b6b5ed8e001e63ce53a8`; `logical_source_id=dsotdq_2022_en`.

**Readback definitivo reale**: 28/28 `translation_status=translated`, 28/28 `translation_review_status=ai_verified`, **28/28 fingerprint SHA256 riprodotti** sul contenuto normalizzato dai record attuali (non solo dalla ricevuta), 28/28 PDF SHA di provenienza corretto, 28/28 PF originali coerenti, 28/28 sei caratteristiche coincidenti con `source_attributes`, 28/28 GS coerenti o correttamente **non applicabili ai 6 comprimari di primo livello**; zero velocità `ft`, zero `normalized_name` duplicati. Le annotazioni di revisione contengono ID, SHA di provenienza, pagina PDF e riferimenti alle capacità controllate. Nessuna duplicazione o modifica delle fonti.

**Casi risolti**:
- **Kapak Draconian**: prima richiesta connettore bloccata, poi certificazione transazionale riuscita e fingerprint a 64 caratteri verificato su `ref_d1c4d19bbe3ec2cb841a47ef519bb6ae`.
- **Tem Temble** `ref_bb19cf336e2e4fa11df25194204f8794`, p215: errata ufficiale Wizards `https://media.dndbeyond.com/compendium-images/errata/DSotDQ/DSotDQ-errata.pdf` cambia `Sleight of Hand +6` in `+4`. Correzione applicata **effettivamente** a `attributes.abilita` e `full_text` con UPDATE condizionale, poi `ai_verified`; `source_attributes` e stampa originale invariati.
- **Kalaman Soldier** `ref_97fef1bb7f4a7730147a3fb4d47472dc`, p204: stampa mostra FOR 13 (+1), attacco +3 e danni longsword **6 (1d8+2) / 7 (1d10+2)**; questi numeri sono anche riportati in trascrizioni esterne concordi e non sono modificati dall'errata ufficiale. Non inferire erroneamente il danno dalla FOR: nella scheda sono conservati come valori espliciti dello statblock e una `nota_fonte` illustra la peculiarità; ricevuta di certificazione con spiegazione, confidence 0.96.
- **Lohezet** `ref_3777d0895dd027a8365d24de4daf977e`: `Miasma` può essere concluso a scelta senza azione, non termina per morte; rettifica aggiornata e certificata.
- **Lord Soth** `ref_4fb498e409565537ff476718a27b2055`: `Maresciallo dei Non Morti` comprende non morti *a sua scelta*, non esclusivamente alleati; rettifica aggiornata e certificata.

Durante un gruppo di quattro certificazioni era stata emessa una firma in esadecimale da 512 caratteri anziché i 64 previsti dalla SHA256. **Corretto immediatamente** il campo e la ricevuta nello stesso record, limitando le firme alle prime 64 cifre. **Ricalcolo indipendente post-fix** mediante algoritmo SHA256 testato contro il vettore standard `abc`: tutti e quattro i record hanno la firma corretta, e nell'audit complessivo **28/28 validi**.

**Checkpoint globale verificato** dopo il completamento: 1.501 `monster` registrati, 593 tradotti, 908 `not_required`, **51 `ai_verified`** (5 Minecraft, 18 Fiendish Folio, 28 Dragonlance), 542 tradotti pendenti.

Ora prossimo manuale: `mc_v4_eldraine_2023_en`, 25/25 tradotti, 25 pending al passaggio. Fonte PDF privata Eldraine SHA `b7fb95c7519fb0936bb2cb37cfb6a5493134c86e0dc31196a4c62a67887e8ada`. Nessun merge automatico su main.


## Monstrous Compendium Vol. 4: Eldraine — 25/25 ai_verified (2026-10-22)

**Fonte privata:** `701858566-RRN5YRR(1).pdf`, pagine fisiche 36–60, SHA-256 del PDF originale `b7fb95c7519fb0936bb2cb37cfb6a5493134c86e0dc31196a4c62a67887e8ada`, logical source `mc_v4_eldraine_2023_en`.

Confronto di seconda passata tra immagini delle 25 pagine originali e le 25 schede già tradotte. Verificati descrizione, CA, PF, GS, caratteristiche, velocità in metri, immunità e vulnerabilità, tratti, azioni, reazioni, azioni bonus, ricariche, danni e tiri salvezza; il confronto è stato distinto dalla prima traduzione. Le 25 certificazioni sono state salvate mediante UPDATE condizionali su row snapshot MD5, provenienza SHA e pagina, lease vuoto, status `translated/pending` e `review_status=verified`, ciascuna con ricevuta JSON contenente pagina, hash fonte e SHA-256 dei contenuti. Per gli ultimi cinque record delle pagine 56–60, ogni UPDATE ha avuto readback diretto positivo, fingerprint ricalcolato e `source_attributes`/`source_refs` immutati.

**Correzione semantica nella seconda passata:** `Knight of Eldraine` / Cavaliere di Eldraine p49, ID `ref_969d8b76b0759a78896c06c4ebf9d611`: eliminata dagli attributi l'abilità inesistente `Percezione +10` (la fonte reca solo `passive Perception 10`). Correzione guardata sulla data `updated_at` e comprovata dalla RETURNING: `attributes ? 'abilita' = false`, `attributes.sensi = 'Percezione passiva 10'`. Il testo integrale non conteneva l'errore.

Confermate prima della certificazione le rettifiche pregresse: Arconte dei Confini, trigger corretto di `Radiosità Accecante`; Guardiano Fatato Supremo, velocità fissata a 3 m (min 1,5 m) e reazione su hit/miss; Incubo Persecutore, viticci 11 (2d10); Segugio delle Streghe, `Ululato Straziante` CD15.

**Readback indipendente conclusivo** da tutti i record Supabase e hash SHA-256 ricalcolato dal contenuto italiano e dagli attributi: **25 record totali, 25 `translated`, 25 `ai_verified`, zero `pending`; 25/25 fingerprint coincidenti; 25/25 SHA provenienza corretti; 25/25 PF, GS, sei caratteristiche corrispondenti; zero nomi normalizzati duplicati; nessuna velocità rimasta in piedi**. Sono state rispettate anche le schede il cui campo `velocita` usa un oggetto JSON di sottocampi invece di una stringa, senza alterarne inutilmente lo schema.

**Checkpoint globale**: 1.501 mostri, 593 `translated`, 908 `not_required`, zero `processing`, **76 `ai_verified`**, 517 traduzioni in attesa di seconda certificazione. Certificati: 5 Minecraft, 18 Fiendish Folio, 28 Dragonlance, 25 Eldraine.

Successivo manuale per seconda passata: *Morte's Planar Parade* (`ps_mpp_2023_en`), 54 tradotti, zero `ai_verified`, con la singola anomalia dei PF stampati `Mercykiller Bloodhound 104 (16d8 + 48)` e dei relativi controlli di provenienza. Nessun merge su `main`, nessun deploy.


## Morte's Planar Parade — checkpoint seconda revisione 12/54 (2026-10-22)

**Fonte privata** `762692978-D-D-5e-Planescape-Adventure-in-the-Multiverse.pdf` (262 pagine fisiche), SHA256 `61392d7a3ab2241dce67b1027c4830e0b3e9431d224f5a1619c6f5257bd427b1`, logical source `ps_mpp_2023_en`.

Dopo Eldraine 25/25 completato sono state lette le scansioni effettive del PDF di Morte, pagine fisiche **213–225** (incluse pagine introduttive 216 e 221), confrontate singolarmente con attributi e testo in italiano. Certificati i seguenti **12 record** (tutti verificati via UPDATE condizionale e readback, 12/54 `ai_verified`; 42 pending):
- **Hound Archon**, p213 `ref_2088ec695258e26b73a3df3b35158164`; **Lantern Archon**, p214 `ref_5e8fa3b84e6abfec9b768f2b0a19d08e`; **Warden Archon**, p215 `ref_e0356b3a567d02e2cee2e8281b75c127`.
- **Baernaloth** p217 `ref_448550fe8862f3132518d3a96b869d8c`: inclusi tre poteri della tana, due effetti regionali, GS nella tana 18 differenziato dal GS17 base e fino a tre reazioni per round.
- **Bariaur Wanderer** p218 `ref_bf1636d6cdbbc6c67f71113ec9951308`; **Cranium Rat Squeaker** p219 `ref_09256e429b25fd2520c6e7da9f1b143b`; **Cranium Rat Squeaker Swarm** p219 `ref_ad6091062ceb7a9938940aa681c12690`; **Dabus** p220 `ref_797ffcd0e4c87d14e18b430dd0851d3a`.
- **Darkweaver** p222 `ref_1c81faa5a49cba4d91b36bd7d36cfafc`, pagine 221–222: verificati statblock, tana, due azioni di tana e tabella sei contenuti di bozzolo.
- **Farastu Demodand** p223 `ref_47ad88e788e4ad7be56af070334c8af8`; **Kelubar Demodand** p224 `ref_c019ed05646a4966b5ec8b95117d0403`; **Shator Demodand** p225 `ref_a997d670eff54bb80f5bd9828338af9d`, controllati effetti persistenti, probabilità di evocazione, immunità e CD.

**Rettifica source-backed, prima della certificazione**: sul `Darkweaver`, la `regole_azioni_tana` italiana dichiarava falsamente `può utilizzare la stessa opzione per due round consecutivi`; il PDF p221 stabilisce invece `can't take the same lair action two rounds in a row`. Un UPDATE SQL protetto da timestamp originale/provenienza/status libero ha modificato gli attributi e `full_text` in **`non può utilizzare la stessa azione di tana per due round consecutivi`**, ricevendo esattamente una riga RETURNING. Solo successivamente il record ha ricevuto `ai_verified`, con SHA256 fingerprint ricalcolato correttamente.

**Interruzione gestita**: l'update o readback dell'Arconte Lanterna ha dato un errore intermittente di connettore; una SELECT successiva mostrava `ai_verified`. Un nuovo prelievo completo del record ha confermato la **corrispondenza esatta del fingerprint SHA256** sulla versione corrente e la ricevuta della stessa pagina, evitando duplicazioni o false riapprovazioni.

Per tutte le certificazioni del blocco, la scrittura richiede MD5 dello snapshot completo, fonte, pagina, SHA, status e lease libero; viene salvata ricevuta JSON con hash, pagina e capacità controllate. Le SELECT post-salvataggio hanno verificato SHA256 di ciascun record e assenza di cambiamenti nei riferimenti alle fonti.

**Nota di inventario importante**: `Mercykiller Bloodhound` p257 è presente come record aggiunto, `ref_b0374024422a1bab0b63412ba9c1b135`, ma rimane `pending` per la discrepanza testuale **104 (16d8 + 48)** rispetto alla media **120**. Non promuovere tale record senza il relativo controllo puntuale e la dichiarazione di discrepanza.

Non sono stati effettuati merge o deploy; `main` invariato. **Prossima pagina da verificare: 226 `Eater of Knowledge`**; successivamente p227–228 i tre githzerai.
