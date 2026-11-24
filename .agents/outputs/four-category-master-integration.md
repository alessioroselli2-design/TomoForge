# Quattro master approvati — PR in bozza
I sette PNG approvati sono nei due ZIP forniti dall'utente. **Non fare merge prima del caricamento effettivo e del collaudo visivo.**
Percorsi esatti:
- frontend/public/card-art/master-talento-5x7.png
- frontend/public/card-art/master-oggetto-magico-5x7.png
- frontend/public/card-art/master-arma-5x7.png
- frontend/public/card-art/master-armatura-5x7.png
- frontend/public/emblemi/categorie/simbolo-talenti.png
- frontend/public/emblemi/categorie/simbolo-oggetti-magici.png
- frontend/public/emblemi/categorie/simbolo-armi-armature.png
Il connettore non dispone di trasferimento diretto dei byte dai file allegati. Non sostituire con immagini inventate o altri master.
Il master Armatura allegato riporta correttamente Requisiti.
I test del mapper usano fixture sintetiche e non certificano i record reali della biblioteca.

Lettura SELECT su private_reference_records: confermati categoria_arma, categoria_armatura, peso_kg, tempo_indossare, tempo_togliere, aumento_caratteristica, cariche_massime, prerequisito_sintonia, recupero_cariche. Campioni: Maestro D’Armi, Spada Lunga, Cotta di Maglia, Scudo, Bastone dei Boschi. Nessun Bastone del Guardiano trovato con ricerca per nome. Nessuna scrittura al database.
