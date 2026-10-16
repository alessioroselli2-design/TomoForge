# Four existing MPMM creatures wrongly classified other/ability

Distinct original **named creature statblocks** in registered Italian PDF `Mostri del multiverso 201-294.pdf`, visually inspected:

| Registered monster name | Physical PDF (logical) | Type originally assigned | AC | HP | Speed |
| --- | --- | --- | --- | --- | --- |
| Somiero Gigante | 47 (247) | other | 14 (armatura naturale) | 22 (3d10+6) | 15m |
| Tanarukk | 50 (250) | other | 14 (armatura naturale) | 95 (10d8+50) | 9m |
| Terrore Gigante Di Fuoco | 53 (253) | other | 21 (piastre, duplice scudo) | 187 (15d12+90) | 9m |
| Venator | 67 (267) | ability | 13 (armatura naturale) | 68 (8d10+24) | 6m, scalare6m |

All are independent boxed AC/HP/speed creature sources that the DM can use directly. Do not create new duplicates. Somiero's existing source description and empty historical `review_corrections={}` remain as they are; the other three existing records have `_source_changed=true`. Original section-continues review flags for Somiero and Terrore need to be preserved as history after visual confirmation the boxed numeric statblock itself is complete on that page. Venator was erroneously typed as ability, not a class feature; its standalone box is visibly present p67. All existing raw text, source_name, source_attributes={}, hash/checksum and source refs remain immutable.

PR is source-only read-only audit + negative tests; after exact-record live audit, backend/frontend CI and exact-head Vercel green, squash merge into `develop`, use **four separately guarded CAS transitions** with append-only verified review histories. Do not force generic verified statuses or assume OCR succeeded.
