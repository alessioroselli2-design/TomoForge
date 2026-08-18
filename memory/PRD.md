# TomeForge — PRD

## Problem Statement
Web app (public browser link) to create Dungeons & Dragons cards. Card types: Magie, Classi, Razze, Armi, Talenti, Mostri/Nemici, Personaggi, and custom types. AI content + artwork generation, collection with filters/search, trading-card detail with front/back, edit/delete, share as image and PDF, monster stat blocks, character sheets with spell-slot tracking, login/registration, dark-fantasy "ancient tome" aesthetic.

## Architecture
- Frontend: React 19 + React Router + Tailwind + shadcn/ui + framer-motion. Dark grimoire theme (obsidian/antique gold/crimson, Cormorant Garamond + Spectral + Cinzel).
- Backend: FastAPI (single server.py, /api prefix) + MongoDB (motor).
- Auth: dual — Email/Password (JWT) + Emergent-managed Google OAuth. Unified `get_current_user` (cookie session_token or Bearer; validates Google sessions then JWT).
- AI: emergentintegrations + EMERGENT_LLM_KEY. Text = Gemini `gemini-3-flash-preview`; Image = Gemini Nano Banana `gemini-3.1-flash-image-preview`.
- Storage: Emergent Object Storage for uploaded + AI artwork; served via `/api/files/{path}?auth=<token>`.

## User Personas
- DM/Player creating custom D&D content and collectible cards.

## Core Requirements (static)
All 8 card types, IT/EN AI content w/ manual edit, AI artwork + device upload, collection grid + type filter + name search, trading-card front(image+stats+desc+QR)/customizable back(style/color/emblem/motto), edit/delete, share image + PDF front+back, monster full stat block, character sheet + trackable spell slots + A4 PDF, auth + DB persistence.

## Implemented (2026-06)
- Auth: register/login (JWT) + Google OAuth session flow. [DONE]
- Cards CRUD with type filter + name search. [DONE]
- AI content generation (Gemini 3 Flash, per-type schema, IT/EN). [DONE]
- AI artwork generation (Nano Banana) + device upload -> object storage. [DONE]
- Trading card front (image, stats, description, QR) + customizable back (style/color/emblem/motto) with 3D flip. [DONE]
- Generic AttributeEditor for all types incl. object-lists (azioni, slot). [DONE]
- Monster stat block, Character spell-slot tracker (+/- + Riposo Lungo, persisted). [DONE]
- Share as PNG, front/back trading-card PDF, Character A4 PDF sheet. [DONE]
- Full dark-fantasy tome UI. [DONE]
- Verified end-to-end by testing agent (100% backend, all critical frontend flows).

## Backlog / Next
- P1: Public share links (read-only card view without auth).
- P1: Decks / collezioni grouping.
- P2: Batch/PDF export of multiple cards, print sheet of 9.
- P2: Server-side split into routers as feature set grows.
