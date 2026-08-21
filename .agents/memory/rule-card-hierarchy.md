---
name: Rule card hierarchy
description: Product decision for representing manual-backed character and gameplay rules as linked cards.
---

The canonical manual-backed database is the source of truth; cards are focused, linked views of that data. Keep races, classes, subclasses, level features, spells, equipment, and similar rules as separate related records/cards rather than duplicating every rule into one oversized card.

**Why:** The user confirmed this structure because it keeps cards readable at the table while still allowing character creation and progression to use complete, source-faithful rules.

**How to apply:** Character creation should resolve links from a class or race to its subclass, level features, spells, and equipment. Full source text can remain available in the detail view, while printable cards show the focused portion needed for play.

The character sheet must support two entry points: generate a polished, printable sheet from an existing saved character without overwriting user-entered rolls or choices, and create a new character with the same database-assisted flow.

**Why:** The user wants existing characters to become nicer complete sheets, while still allowing the same source-backed assistance when starting a new character.

**How to apply:** Treat saved character values as authoritative; fill only deterministic or missing rule fields from the canonical database, leave rolled/choice-dependent fields editable, and offer PDF/print output for both paths.