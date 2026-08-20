---
name: Segmind model availability
description: Provider model listings do not guarantee that a specific account can use a model.
---

Use Flux Dev for TomeForge artwork unless a replacement has been tested successfully with the project's Segmind account.

**Why:** Segmind returned an upstream model-not-found/access error for Imagen 4 Fast despite listing it publicly, while Flux Dev accepted the same account and returned an image successfully.

**How to apply:** Before changing `SEGMIND_IMAGE_MODEL`, make one live generation request with the intended model and its model-specific parameters. Keep the environment override so a verified model can be changed without exposing credentials.