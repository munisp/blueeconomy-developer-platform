#!/usr/bin/env python3
"""Validate marketplace/api-registry.json structure (CI gate, fail-closed)."""
import json
import sys
from pathlib import Path

REQUIRED_ENTRY = {"apiId", "repo", "title", "owner", "classification", "version", "sla", "openapiRef", "sandboxAvailable"}
REQUIRED_SLA = {"availabilityPct", "maxLatencyMs", "support"}
CLASSIFICATIONS = {"PUBLIC", "PARTNER", "RESTRICTED"}


def main() -> int:
    path = Path(__file__).resolve().parent.parent / "marketplace" / "api-registry.json"
    reg = json.loads(path.read_text())
    errors: list[str] = []
    seen: set[str] = set()
    for i, entry in enumerate(reg.get("apis", [])):
        missing = REQUIRED_ENTRY - entry.keys()
        if missing:
            errors.append(f"apis[{i}] missing fields: {sorted(missing)}")
            continue
        if entry["apiId"] in seen:
            errors.append(f"duplicate apiId: {entry['apiId']}")
        seen.add(entry["apiId"])
        if entry["classification"] not in CLASSIFICATIONS:
            errors.append(f"{entry['apiId']}: bad classification {entry['classification']}")
        if not entry["repo"].startswith("munisp/"):
            errors.append(f"{entry['apiId']}: repo must be munisp/*")
        sla_missing = REQUIRED_SLA - entry["sla"].keys()
        if sla_missing:
            errors.append(f"{entry['apiId']}: sla missing {sorted(sla_missing)}")
        elif not (0 < float(entry["sla"]["availabilityPct"]) <= 100):
            errors.append(f"{entry['apiId']}: availabilityPct out of range")
    if not reg.get("apis"):
        errors.append("registry has no APIs")
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"OK: {len(seen)} APIs registered, registry v{reg['registryVersion']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
