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
