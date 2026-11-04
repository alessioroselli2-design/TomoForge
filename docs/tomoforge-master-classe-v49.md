# TomoForge — Master Classe v49 (anteprima, NON pubblicata)
Data: 04/11/2026 — Ambito: soltanto categoria **Classe**.
## Fonti definitive e non sostituibili
- Master vuoto unico: `/card-art/master-classe-pulito-v49.webp` (864×1210); la cornice inferiore è completa, nessuna seconda mezza cornice, nessun dado o testo fisso.
- Emblemi: **CLS-01–CLS-13**, ritagli dalla tavola di 13 stemmi approvata il 04/11; 256×256 px per file, mai sprite da 44px o interpretazioni AI. Il **Guerriero è CLS-05**.
- Dado vita: **asset premium v29 preesistenti**, `/card-art/class-dice/{d6|d8|d10|d12}-premium-v29.webp`; la classe decide il tipo tramite `dado_vita` validato. Nessun nuovo dado nel raster.
- Icone riquadri: SVG originali `class-stats/primary-v33.svg`, `saves-v33.svg`, `proficiencies-v33.svg`. Non modificare.
- Titolo: font originale **Cormorant Garamond**; sottotitolo, etichette, valori e descrizione: **EB Garamond** e colore #261a0f con `mix-blend-mode:multiply`, nessuno sfondo o bordo CSS.
## Mappa classi
CLS-01 Barbaro d12; CLS-02 Bardo d8; CLS-03 Chierico d8; CLS-04 Druido d8; CLS-05 Guerriero d10; CLS-06 Monaco d8; CLS-07 Paladino d10; CLS-08 Ranger d10; CLS-09 Ladro d8; CLS-10 Stregone d6; CLS-11 Warlock d8; CLS-12 Mago d6; CLS-13 Artefice d8.
## Dimensioni e sovrapposizioni
- Carta: `aspect-ratio: 340/476`, grafica originale 864×1210, bordo unico. NON creare altre cornici né livelli decorativi.
- Medaglione sinistro: asset 256px di classe nel riquadro approvato; CSS `left:1.9%;top:1.1%;width:24.4%` senza ritagli diagonali né duplicazione di cerchi, medesima resa in canvas di export.
- Medaglione destro superiore: rimane rosso, NON rimpiazzato da un dado.
- Illustrazione centrale: vuota sino al caricamento utente; nessun testo o placeholder per Classe.
- Tre caselle: Abilità Primaria, Tiri Salvezza e Competenze; etichette fisse e valori dinamici. Non inventare dati per classi prive di record.
- Descrizione in basso: dinamica, senza scroll e rispettando la fine delle frasi.
- Dado a destra nel riquadro finale, UNO SOLO; nessun alone/patch visibile.
## Accettazione e regressioni
Confronto **Master vuoto / Guerriero CLS-05 + d10 / Druido CLS-04 + d8 / Mago CLS-12 + d6 / Barbaro CLS-01 + d12**, più verifica menu 13 classi. Test frontend e build; esportazione PNG/PDF allineata al browser. **Non eseguire merge né pubblicare su main prima dell'approvazione visiva esplicita.** Il master Mostro v17 è intoccabile.
