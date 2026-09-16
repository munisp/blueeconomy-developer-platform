#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

for forbidden in '.env' '.env.production' 'id_rsa' 'kubeconfig' 'credentials.json'; do
  if git ls-files | grep -Eq "(^|/)${forbidden}$"; then
    echo "Forbidden tracked secret/configuration filename: ${forbidden}" >&2
    exit 1
  fi
done

if git grep -nEI '(BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,})' -- ':!docs/' >/dev/null 2>&1; then
  echo "Potential credential material detected in tracked source." >&2
  exit 1
fi

echo "Tracked-file secret baseline check passed."

# ── Phase 19 (F1/M6): marketplace registry CI gate ───────────────────────────
# The "fail-closed CI gate" claimed by marketplace/webhooks.md is wired HERE:
# the workflow file itself cannot be modified without the `workflow` OAuth
# scope, so the existing baseline job (which runs this script on every PR and
# push to main) also validates the API registry and the catalogue-provenance
# verifier. Any registry/topic/namespace or provenance error fails the build.
if command -v python3 >/dev/null 2>&1; then
  python3 scripts/validate-api-registry.py
  python3 scripts/verify-catalogue-provenance.py --selftest >/dev/null
  echo "API registry + catalogue provenance checks passed."
else
  echo "python3 unavailable — refusing to skip the registry gate (fail-closed)." >&2
  exit 1
fi
