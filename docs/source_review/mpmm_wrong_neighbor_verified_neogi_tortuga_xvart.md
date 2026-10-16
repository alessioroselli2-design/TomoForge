# Correct three source-confirmed wrong-neighbor statblocks already marked verified

The following Italian MPMM monster entries are already `monster/verified`, but they inherited statistics of a *different adjacent creature*. These are correctness defects, not missing creatures. Verified status must never be treated as sufficient evidence by itself.

| Existing monster | PDF page(s) | Wrong current values | Original named statblock correct values |
| --- | --- | --- | --- |
| Neogi | physical pp99 and **100** in segment 101–200 | AC11, HP7(3d4), speed6m/climb6m of **Cucciolo di Neogi** | **Neogi** p100 AC15 natural, HP33(6d6+12), 9m/climb9m |
| Tortuga | physical p58 in segment 201–294 | HP33(6d8+6) of **Tortuga Druido** | **Tortuga** p58 AC17 natural, HP22(4d8+4), 9m |
| Xvart Warlock di Raxivort | physical p71 in segment 201–294 | AC13, HP7(2d6) of **Xvart** | **Xvart Warlock** p71 AC12 (15 con armatura magica), HP22(5d6+5), 9m |

All originals were examined directly in their Italian licensed PDF page images; full statblock values differ despite neighboring same-page descriptions. Preserve all IDs, names, original `source_attributes`, original prose fields, registered checksum/SHA256, source refs and prior review histories. Only correct live `attributes` and annotate `review_notes`, appending a new source-specific verified review history entry, never deleting earlier history.

The read-only source audit **pins both erroneous current values and corrected original named-statblock values**, rejecting drift. It must pass unchanged global semantic numeric gate and hit-dice math; backend/frontend CI and exact-head Vercel must be green, then squash merge to `develop`, then run **three separate compare-and-set transactions**, each comparing the complete original source snapshot, current attributes and prior update timestamp. If any check fails, the individual correction stops.

After correction, rerun targeted and broad same-page contamination searches before declaring MPMM fully verified. No new records, no published PDF reproduction, no forced status changes.
