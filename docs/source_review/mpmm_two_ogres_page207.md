# Two original MPMM Ogres misclassified as generic 'other'

The registered Italian `Mostri del multiverso 201-294.pdf` source p7/logical p207 visibly has *two independent same-page named statblocks*: **Ogre Bruto Con Catena** (AC11 hide, HP59 = 7d10+21, speed12m) and **Ogre Bunker** (AC15 breastplate+shield, HP59 = 7d10+21, speed12m). Both are Large giants, generally chaotic evil.

Existing imported ID `ref_31d363e7eba9573c99a78bb56a5805f9` is named `0Gre Bruto Con Catena`; `ref_6a7601e7bf0158bea76adf2919f70b3e` is `0Gre Bunker`, both incorrectly typed `other/needs_review`. The leading **zero instead of O** is a source OCR defect. Their original `source_name`, raw source descriptions, checksums and historical attributes must be preserved; display `name` and `normalized_name` corrected to `Ogre...` only after guarded source validation.

Bunker's original source has a section-continues review flag; its AC/HP/speed and its distinct boxed statblock are already visible on p7. When reclassifying, clear the operational flag with a provenance note that preserves the prior flag in append-only review history. `0Gre Di Guerra` is descriptive text on the page, **not an independent boxed statblock**; do not promote it simply because it has a heading. `Ogre Scoccadardi` and `Ogre Trebbiatore` are already verified, unchanged.

The PR must pass live **zero-write** exact-record no-duplicate audit, backend/frontend CI, exact-head Vercel READY/green, squash merge into `develop`. Only then two separate source-locked compare-and-set Supabase transitions, keeping original checksum/source fields and adding review history. No invented OCR success, no duplications.
