# Bigby IT: Lince Gigante — registered-source adjudication

- Exact target `ref_63424c86d98354efb93e1c6f03edad15`, pending with flags `ocr_da_verificare` and `source_guided_repair`, no canonical link.
- Registered Italian licensed translation: `bgg_2023_it`, physical p167, file `760692359-D-D-5e-ITA-Bigby-Presenta-La-Gloria-Dei-Giganti.pdf`, fingerprint `f393d3802ceff6e2fc00f8239d9a603e280ee15a6b6c76587c568ae19e10f875`.
- Stored original structured core: CA14, PF22 (4d8 + 4), walk9m and climb9m. The raw Italian `full_text` contains a known OCR-space artifact `Classe Armatura 1 4` and must be preserved verbatim, not silently rewritten.
- Original English *Bigby Presents: Glory of the Giants*, printed p151, has Giant Lynx AC14, HP22 (4d8+4), 30ft walking and 30ft climbing: https://anyflip.com/fmtsi/jmxv/basic/101-150 and https://onyx5e.com/en/bestiary/giant-lynx/ .
- Global HP arithmetic: floor(4 * 4.5)+4 = 22. Conversion: 30ft ≈ 9m.
- Original paired-OCR PR #432 returned `review_required/attribute_change_required` for speed rendering. That audit is **not** positive and is **not** the acceptance basis. This separate exact-source status review verifies the immutable stored source and corroborated edition with strict fail-closed tests.
- Do not merge/promote unless the new live read-only audit, Ruff/pytest and frontend build, Vercel, and a separate guarded Supabase UPDATE plus history are successful.
