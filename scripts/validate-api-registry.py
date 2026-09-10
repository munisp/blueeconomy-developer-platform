#!/usr/bin/env python3
"""Validate marketplace/api-registry.json structure (CI gate, fail-closed)."""
import json
import re
import sys
from pathlib import Path

REQUIRED_ENTRY = {"apiId", "repo", "title", "owner", "classification", "version", "sla", "openapiRef", "sandboxAvailable"}
REQUIRED_SLA = {"availabilityPct", "maxLatencyMs", "support"}
CLASSIFICATIONS = {"PUBLIC", "PARTNER", "RESTRICTED"}
REQUIRED_WEBHOOK_GOVERNANCE = {"contract", "registration", "signature", "retryPolicy", "deliveryLog", "failClosed"}

EVENT_TOPIC = re.compile(r"^[a-z0-9][a-z0-9-]*\.[a-z0-9][a-z0-9_]*$")


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
        # Phase 17 (#19): webhook event topics are governed catalogue surface.
        topics = entry.get("webhookEvents")
        if topics is not None:
            if not isinstance(topics, list) or not topics:
                errors.append(f"{entry['apiId']}: webhookEvents must be a non-empty array")
            else:
                if entry["classification"] == "RESTRICTED":
                    errors.append(f"{entry['apiId']}: RESTRICTED products may not declare webhook topics")
                product_ns = entry["apiId"].split(".")[1]  # first token after the service name
                for topic in topics:
                    if not isinstance(topic, str) or not EVENT_TOPIC.match(topic):
                        errors.append(f"{entry['apiId']}: bad webhook topic {topic!r} (want <namespace>.<verb_snake>)")
                    elif topic.split(".", 1)[0] != product_ns:
                        errors.append(f"{entry['apiId']}: webhook topic {topic!r} outside the product namespace {product_ns!r}")
                    if topics.count(topic) > 1:
                        errors.append(f"{entry['apiId']}: duplicate webhook topic {topic!r}")
    if not reg.get("apis"):
        errors.append("registry has no APIs")
    if any("webhookEvents" in e for e in reg.get("apis", [])):
        governance = reg.get("webhooks")
        if not isinstance(governance, dict) or REQUIRED_WEBHOOK_GOVERNANCE - governance.keys():
            errors.append("webhook topics declared but the webhooks governance block is missing/incomplete")
    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        return 1
    topics_total = sum(len(e.get("webhookEvents", [])) for e in reg["apis"])
    print(f"OK: {len(seen)} APIs registered ({topics_total} webhook topics), registry v{reg['registryVersion']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
