# Vercel preview retry after transient build-rate limit

The protected, original-source review for Somiero Gigante, Tanarukk, Terrore Gigante di Fuoco, and Venator already passed its live read-only audit and backend/frontend CI. The first exact-head Vercel preview returned a build-rate-limit error, not an application source error. This benign documentation update triggers a new preview on a new commit. Do not merge until that exact new head has Vercel READY/success as well as fresh backend/frontend CI green. No database changes or altered source evidence in this retry.
