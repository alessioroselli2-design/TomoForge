# Tasha: Spirito della Fiamma as creature and class feature

Original Italian Tasha PDF page 38 (printed p37) contains a full, named **Elementale Piccolo** creature statblock: AC 13 (natural armor), HP **5 + five times the druid level** (dynamic formula, not fixed), movement 9m and fly9m (hover).

An existing `class_feature/pending` source record `ref_ae3e94213cfa52be8a5ab76654b078ad` already owns the exact original short source text and source attributes, with the initial OCR only reading '5' as HP. Do **not** mark that historical OCR successful, and **do not** overwrite or delete the user's class feature. Per updated creature policy, represent the distinct creature in the `monster` index using new deterministic ID `ref_b48af5b5ccce202441ada1681016b71e` and independently visually verified source/HP formula, while retaining the original class-feature record unchanged.

The original feature full_text SHA256 is `42c51757bda965bad3cb9a738d6efa26182242eb1cd0b61aa97f6c21e6ee4c52`, exactly matching the manually rechecked statblock header. The original feature source checksum is `453c187dec611e54d7ac1c9c05572bc4eca08bb83c023ec93a1f465e63bf58e2`. Tasha source is active licensed `tce_2020_it`, physical original PDF 194 pages; historical import uses a suffixed filename. No fictitious slot level, druid level, or fixed HP value is supplied.

Protected audit checks original feature exact ID/name/status/OCR/provenance/raw and verifies no `monster` with the same normalized name already exists. No writes in CI. Backend/frontend CI and Vercel green plus squash merge into develop required before a **separate guarded new monster insert** and append-only verification history, checking the same original feature remains untouched.
