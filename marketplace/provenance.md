# Signed Catalogue Provenance — Portal Display Contract (Phase 17, #13 developer side)

The marketplace runtime (`munisp/singlewindow`, `server/marketplace/apiCatalogue.ts`)
serves the API catalogue **signed** under envelope v1.0 (JCS + Ed25519 JWS).
This document fixes what any developer-facing portal UI MUST surface so the
signing is verifiable by consumers instead of decorative.

## What the runtime publishes

`GET /api/marketplace/catalogue` returns:

```json
{
  "envelopeVersion": "1.0",
  "catalogue": { "entries": [ { "apiId": "…", "specDigest": "<sha256 hex of the JCS-canonical spec fragment>", "…": "…" } ] },
  "catalogueDigest": "<sha256 hex of the JCS-canonical catalogue>",
  "signatureStatus": "SIGNED | UNSIGNED_NO_KEY",
  "jws": "<compact JWS, present only when SIGNED>",
  "kid": "<producer>-<epoch>, e.g. singlewindow-0"
}
```

## Display contract (honest provenance)

For every API shown in the portal, the UI MUST display:

1. **Spec digest** — the entry's `specDigest` (sha256, JCS-canonical), with a
   copy affordance. Any change to the published spec invalidates the digest.
2. **Signature state** — one of:
   - `SIGNED — kid <kid>` (show the JWS `kid` so key rotation is visible), or
   - `UNSIGNED_NO_KEY` rendered as a warning state. An unsigned catalogue is
     honest, but MUST NOT be styled as if verified.
3. **Catalogue digest + generatedAt** in an envelope-level footer.

The UI MUST NOT claim "verified" — verification is a client-side operation
performed by consumers (see below). The portal displays provenance; consumers
verify it.

## Verifying (fail-closed)

`scripts/verify-catalogue-provenance.py` recomputes the catalogue digest over
the JCS-canonical catalogue and verifies the JWS against the Ed25519 public
key supplied via the `MARKETPLACE_SIGNING_PUBLIC_KEY` environment variable
(base64url raw 32-byte key). Any mismatch, missing key, or unsigned catalogue
exits non-zero — a caller can therefore gate a release on catalogue integrity:

```bash
MARKETPLACE_CATALOGUE_URL=https://<gateway>/api/marketplace/catalogue \
MARKETPLACE_SIGNING_PUBLIC_KEY=<base64url-ed25519-public-key> \
python3 scripts/verify-catalogue-provenance.py

# Offline / CI fixture mode:
python3 scripts/verify-catalogue-provenance.py --catalogue fixture.json \
  --public-key-env MARKETPLACE_SIGNING_PUBLIC_KEY
```

Keys are environment-only; no key material is ever committed to this
repository.
