# Tasha — original Servitore Possente di Leuk-O statblock

Original physical user-provided Tasha PDF confirmed **194 actual pages** by inspecting the original bytes; the Library text/image-preview pipeline indexes only pages 1-150. In particular, the full named boxed Huge Construct statblock for `Servitore Possente di Leuk-O` is visible on original physical page 131.

Original CA 22 (natural armor), HP 310 (27d12 + 135), speed 18m. The original arithmetic is coherent (floor(27 x 6.5 + 135) = 310), and original global numeric sanity gates are unchanged. This is an independently boxed statblock of a creature even though the surrounding feature describes an artifact. It counts as a monster by the user's category rule. There is no corresponding name or ID in the existing Tasha source database preflight.

The new record should retain a brief **manual visual source excerpt** distinctly marked as such; do not falsely claim successful automated OCR of the full copyrighted statblock. Registered licensed Tasha original source `tce_2020_it`, catalog filename `Calderone-Omnicomprensivo-di-TASHA.pdf`, physical pages 194, imported historical source key `Calderone-Omnicomprensivo-di-TASHA_1787259976040.pdf`, active authority. Both 194-page physical source and p131 boxed statblock have been directly inspected.

PR adds **no database writes**; require green backend Ruff/pytest, frontend production checks, Vercel READY exact-head, successful source-locked no-duplicate live preflight and squash merge to develop. Then one guarded source-specific new record insert with append-only review history; no duplicate entry or lost source.
