---
name: Manual preload lease ownership
description: Rules for safely resuming the per-account automatic manual indexing queue.
---

Every automatic-manual worker must include its claimed lease ID in each checkpoint or terminal update, renew that lease while a chunk is running, and only reclaim expired processing leases on startup.

**Why:** A process-local worker registry cannot prevent an old worker from writing stale progress after another process has recovered the same job. Without lease ownership, a resume can duplicate or overwrite queue state.

**How to apply:** Preserve this protocol whenever the import queue is refactored, new worker hosts are added, or job retry logic changes. Treat a failed lease-owned update as a lost claim and do not write another checkpoint.