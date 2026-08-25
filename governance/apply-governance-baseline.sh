#!/usr/bin/env bash
set -euo pipefail

root="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
template_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for repo in "$root"/blueeconomy*; do
  [ -d "$repo/.git" ] || continue
  [ "$(basename "$repo")" = "blueeconomy-developer-platform" ] && continue
  mkdir -p "$repo/.github/workflows" "$repo/governance"
  cp "$template_root/branch-protection-main.json" "$repo/.github/branch-protection.main.json"
  cp "$template_root/repository-governance.yml" "$repo/.github/workflows/repository-governance.yml"
  cp "$template_root/STRICT_REVIEW_POLICY.md" "$repo/governance/STRICT_REVIEW_POLICY.md"
  if [ ! -e "$repo/.github/CODEOWNERS" ]; then
    cp "$template_root/CODEOWNERS" "$repo/.github/CODEOWNERS"
  fi
done

printf '%s\n' 'Installed version-controlled governance baseline in every sibling Blue Economy repository.'
