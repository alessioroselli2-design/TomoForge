---
name: React Router Jest compatibility
description: Compatibility constraints for importing React Router v7 in this project's CRA/Jest page tests.
---

Route-based page tests must resolve React Router v7 to its CommonJS builds and initialize `TextEncoder`/`TextDecoder` before importing the router.

**Why:** CRA’s Jest 27 resolver does not consistently select Router v7 conditional exports, and its JSDOM environment lacks the encoding globals that Router initializes at module load.

**How to apply:** Keep these test-environment shims in place when upgrading React Router or adding page tests that use `MemoryRouter`, `Routes`, or `Route`. Re-evaluate them only alongside a deliberate test-runner upgrade.