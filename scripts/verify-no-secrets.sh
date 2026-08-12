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
