---
name: Translation review history
description: Privacy and retention rules for manual-translation verification decisions.
---

Keep the complete review trail in an append-only, owner-scoped table linked to the private reference record, including the reviewer identity, UTC decision time, outcome, and note; show it newest first in the authenticated owner-review projection only.

**Why:** The latest review note is useful operationally, but it cannot replace prior verification context. The audit trail must remain available after a record is confirmed without exposing it in normal browsing or card APIs.

**How to apply:** Insert one row for every explicit review decision; never read, edit, and rewrite a JSON history array. Keep all history access constrained by the same owner `user_id` query used for the private record. Do not put source text, PDF data, or page images in history entries.