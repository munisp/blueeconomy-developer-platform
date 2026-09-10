# Marketplace Webhook Subscriptions (Phase 17, innovation #19)

This document is the **governance contract** for webhook subscriptions on
marketplace products. The canonical registry declares *which products publish
which event topics* (`webhookEvents` in `api-registry.json`); subscriptions
themselves are runtime state, registered through the marketplace runtime
(`munisp/singlewindow`, `server/marketplace/`) and scoped to the caller's API
key. Like Phase-16 products, webhook-capable event topics are part of the
signed catalogue surface: adding an event topic is a governed registry change
(CI-validated, maker-checker reviewed, digest-covered).

## Registration (fail-closed)

- `POST /api/marketplace/webhooks` with a scoped API key. Body:
  `{ "apiId": "<catalogue apiId>", "events": [...], "callbackUrl": "https://..." }`.
- The caller's key must carry a scope covering `apiId`; sandbox keys receive
  only sandbox-marked deliveries (`X-Sandbox: true`), matching the onboarding
  doctrine in `api-registry.json`.
- `callbackUrl` must be HTTPS without credentials/query/fragment; plain HTTP
  is refused.
- `events` must be a non-empty subset of the product's declared
  `webhookEvents`; unknown topics are refused.
- On registration the runtime issues a **signing secret exactly once**
  (returned in the creation response, stored hashed at rest, env-only at the
  platform layer). If the platform has no webhook signing capability
  configured, registration is refused honestly (`503 WEBHOOKS_NOT_CONFIGURED`)
  rather than delivering unsigned webhooks.

## Delivery

Each delivery is an HTTP POST to `callbackUrl` with:

| Header | Meaning |
| --- | --- |
| `Content-Type: application/json` | Envelope body (see below). |
| `X-BlueEconomy-Delivery-Id` | UUID; idempotency key — receivers MUST dedupe on it. |
| `X-BlueEconomy-Event` | Event topic, e.g. `declarations.status_changed`. |
| `X-BlueEconomy-Timestamp` | Unix seconds at signing time. Receivers should reject skew > 300 s. |
| `X-BlueEconomy-Signature` | `sha256=<hex>` — HMAC-SHA256 over `<deliveryId>.<timestamp>.<raw body>` keyed by the per-subscription secret. |
| `X-Sandbox: true` | Present on sandbox deliveries only. |

Body envelope:

```json
{
  "deliveryId": "…uuid…",
  "apiId": "singlewindow.declarations",
  "event": "declarations.status_changed",
  "occurredAt": "RFC3339",
  "data": { "…": "event payload, never fabricated" }
}
```

Receivers verify the HMAC before processing; constant-time comparison is
mandatory. A delivery whose signature cannot be verified MUST be dropped.

## Retry / backoff

Failed deliveries (non-2xx, timeout 10 s, TLS error) retry on a fixed
schedule: **1 min, 5 min, 30 min, 2 h, 12 h — at most 5 retries** after the
initial attempt. Retries reuse the same `X-BlueEconomy-Delivery-Id`. After
the final attempt the delivery is marked `EXHAUSTED`; the subscription is NOT
silently disabled — repeated exhaustion is surfaced in the delivery log and
the subscription's `health` field degrades to `FAILING`.

## Honest delivery log

`GET /api/marketplace/webhooks/{id}/deliveries` returns the real delivery
record: `deliveryId`, `event`, `attemptCount`, `lastAttemptAt`, `status`
(`PENDING | DELIVERED | RETRYING | EXHAUSTED`), `lastHttpStatus` (or null on
network failure) and `nextRetryAt`. Undelivered webhooks are never reported
as delivered; clock and status come from the delivery worker only.

## Governance of event topics

Event topics are declared per product in `api-registry.json` under
`webhookEvents` and validated by `scripts/validate-api-registry.py`
(fail-closed CI gate): topic names must be namespaced `<product-suffix>.<verb>`
lowercase, the product must exist in the same registry, and RESTRICTED-class
products may not declare PUBLIC webhook topics.
