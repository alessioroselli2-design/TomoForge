# Quattro master approvati — collaudo
Asset originali dai due ZIP dell'utente, nessuna modifica, nessun ricampionamento. I quattro master sono 1024×1434 (5:7); i tre simboli sono le versioni normali PNG RGBA 640×640. Hash Git blob confrontati byte per byte:
- `frontend/public/card-art/master-talento-5x7.png` — `5f6f8397c4364df55606b02b5ba7fa6052ae8546`
- `frontend/public/card-art/master-oggetto-magico-5x7.png` — `1bedebb23bb784573b77b8d957adadb3c4f55903`
- `frontend/public/card-art/master-arma-5x7.png` — `c7e61138cb7ed9aff6699e74b59fc8aa843f0ebb`
- `frontend/public/card-art/master-armatura-5x7.png` — `b0d0d54624b7d3eb1c89bd4587b09ca12f749a68`
- `frontend/public/emblemi/categorie/simbolo-talenti.png` — `e2545b5d37cc085a2e1ef17327f9e14efeac6864`
- `frontend/public/emblemi/categorie/simbolo-oggetti-magici.png` — `4cf79c23ce18c64c395056c2cb0764f9cdfc2156`
- `frontend/public/emblemi/categorie/simbolo-armi-armature.png` — `e3c1ef80c024795319f85300d67daf22667d29a6`
## Dati
Lettura SELECT su private_reference_records: confermati categoria_arma, categoria_armatura, peso_kg, tempo_indossare, tempo_togliere, aumento_caratteristica, cariche_massime, prerequisito_sintonia, recupero_cariche. Campioni: Maestro D’Armi, Spada Lunga, Cotta di Maglia, Scudo, Bastone dei Boschi. Nessun Bastone del Guardiano trovato con ricerca per nome. Nessuna scrittura al database.
Test mapper eseguiti con le stesse asserzioni dei sei test della suite: 6/6, inclusi i cinque campioni reali. La CI e la verifica browser sono distinte.
Il master Armatura allegato riporta correttamente Requisiti. Non effettuare il merge prima del collaudo visivo e della CI.
