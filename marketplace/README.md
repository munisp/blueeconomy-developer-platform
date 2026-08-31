# BlueEconomy API Marketplace

This repository holds the **canonical cross-repo API registry** (`api-registry.json`)
for the OCEANS-X-style open API marketplace, plus the CI validation gate.

- Runtime catalogue, signing, developer onboarding (org registration, scoped/hashed
  API keys, metering, maker-checker production elevation), and sandbox routing are
  implemented in `munisp/singlewindow` (`server/marketplace/`, `server/middleware/apiKeyAuth.ts`,
  routes under `/api/marketplace/*`, `/api/kpis/*`, `/api/status`).
- Every registered API carries owner, classification (PUBLIC/PARTNER/RESTRICTED),
  version, SLA, and an OpenAPI reference. The runtime catalogue publishes a sha256
  digest per spec (JCS-canonical) and serves the catalogue signed under envelope v1.0
  (JCS + Ed25519 JWS) — tamper-evident by construction.
- Signing keys are environment-only. Deployments without keys serve catalogues
  honestly marked `UNSIGNED_NO_KEY`; signed KPI snapshot exports refuse to emit
  unsigned output (503).

Validate the registry:

    python3 scripts/validate-api-registry.py
