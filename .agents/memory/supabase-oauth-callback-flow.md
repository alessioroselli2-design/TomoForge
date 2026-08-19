---
name: Supabase OAuth callback flow
description: Guidance for TomeForge's server-initiated Google OAuth callback and user-visible failures.
---

Use Supabase's browser-compatible implicit OAuth authorization flow when the FastAPI server starts Google login and the React callback exchanges the returned access token.

**Why:** The Python Supabase client's OAuth helper creates a PKCE verifier in its own client storage. A later browser callback cannot recover that verifier, so Supabase returns a code the React callback cannot exchange and users are silently returned to the login screen.

**How to apply:** Keep the authorization URL free of a PKCE `code_challenge` unless the verifier is explicitly persisted and exchanged. The React callback should retain and show provider/backend errors rather than immediately navigating away.