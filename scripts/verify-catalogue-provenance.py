#!/usr/bin/env python3
"""Verify signed marketplace catalogue provenance (Phase 17, #13). Fail-closed.

Recomputes sha256 over the RFC 8785 (JCS) canonical catalogue and verifies the
Ed25519 JWS (envelope v1.0) against the public key from the
MARKETPLACE_SIGNING_PUBLIC_KEY env var (base64url, raw 32 bytes). Prints the
per-entry provenance table (apiId, specDigest) plus kid — the exact fields the
developer portal UI surfaces per marketplace/provenance.md.

Usage:
  MARKETPLACE_CATALOGUE_URL=https://.../api/marketplace/catalogue \
  MARKETPLACE_SIGNING_PUBLIC_KEY=... python3 scripts/verify-catalogue-provenance.py
  python3 scripts/verify-catalogue-provenance.py --catalogue fixture.json   # offline
  python3 scripts/verify-catalogue-provenance.py --selftest                 # ephemeral key round-trip
"""
import argparse
import base64
import hashlib
import json
import os
import sys
import urllib.request


def b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def jcs_canonicalize(value) -> str:
    """RFC 8785 JSON Canonicalization Scheme (the subset JSON can express)."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, (int, float)):
        # JCS uses ECMAScript number serialization; Python's repr of the
        # shortest round-trip float matches for the JSON value range used here.
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        return repr(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(jcs_canonicalize(item) for item in value) + "]"
    if isinstance(value, dict):
        parts = []
        for key in sorted(value.keys(), key=lambda k: k.encode("utf-16-be", "surrogatepass")):
            parts.append(json.dumps(key, ensure_ascii=False) + ":" + jcs_canonicalize(value[key]))
        return "{" + ",".join(parts) + "}"
    raise TypeError(f"not JSON-canonicalizable: {type(value)}")


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def verify_jws(jws: str, public_key_b64url: str) -> dict:
    """Verify a compact EdDSA (Ed25519) JWS and return its payload."""
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError:
        raise RuntimeError("cryptography package required for JWS verification (fail-closed)")
    parts = jws.split(".")
    if len(parts) != 3:
        raise RuntimeError("JWS must have three segments")
    header = json.loads(b64url_decode(parts[0]))
    if header.get("alg") != "EdDSA":
        raise RuntimeError(f"unsupported JWS alg {header.get('alg')!r} (want EdDSA)")
    key = Ed25519PublicKey.from_public_bytes(b64url_decode(public_key_b64url))
    key.verify(b64url_decode(parts[2]), f"{parts[0]}.{parts[1]}".encode("ascii"))
    return json.loads(b64url_decode(parts[1]))


def load_catalogue(args) -> dict:
    if args.catalogue is not None:
        with open(args.catalogue, "r", encoding="utf-8") as handle:
            return json.load(handle)
    url = os.environ.get("MARKETPLACE_CATALOGUE_URL")
    if not url:
        raise RuntimeError("MARKETPLACE_CATALOGUE_URL is required without --catalogue (fail-closed)")
    if not url.startswith("https://") and not url.startswith("http://127.0.0.1") and not url.startswith("http://localhost"):
        raise RuntimeError("catalogue URL must be HTTPS (loopback allowed for local verification)")
    with urllib.request.urlopen(url, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def run(envelope: dict, public_key: str | None) -> int:
    errors: list[str] = []
    catalogue = envelope.get("catalogue")
    if not isinstance(catalogue, dict):
        errors.append("envelope.catalogue missing")
        catalogue = {}
    recomputed = sha256_hex(jcs_canonicalize(catalogue))
    published = envelope.get("catalogueDigest")
    if published != recomputed:
        errors.append(f"catalogueDigest mismatch: published {published} != recomputed {recomputed}")

    status = envelope.get("signatureStatus")
    kid = envelope.get("kid")
    if status == "SIGNED":
        if not envelope.get("jws") or not kid:
            errors.append("SIGNED but jws/kid missing")
        elif public_key is None:
            errors.append("MARKETPLACE_SIGNING_PUBLIC_KEY not set — cannot verify (fail-closed)")
        else:
            try:
                payload = verify_jws(envelope["jws"], public_key)
                if payload.get("catalogueDigest") != published:
                    errors.append("JWS payload catalogueDigest does not match the envelope digest")
                if payload.get("producer") != catalogue.get("producer"):
                    errors.append("JWS payload producer does not match the catalogue producer")
            except Exception as exc:  # signature failure must fail closed
                errors.append(f"JWS verification failed: {exc}")
    elif status == "UNSIGNED_NO_KEY":
        errors.append("catalogue is UNSIGNED_NO_KEY — honest but unverifiable; refusing to pass")
    else:
        errors.append(f"unknown signatureStatus {status!r}")

    entries = catalogue.get("entries", [])
    print(f"producer={catalogue.get('producer')} kid={kid or '—'} status={status} entries={len(entries)}")
    for entry in entries:
        print(f"  {entry.get('apiId'):50s} spec sha256(JCS)={entry.get('specDigest')}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OK: catalogue digest {recomputed} verified (kid={kid})")
    return 0


def selftest() -> int:
    """Round-trip with an ephemeral Ed25519 key: sign a fixture, then verify."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    catalogue = {
        "catalogueVersion": "1.0.0",
        "generatedAt": "2026-01-01T00:00:00.000Z",
        "producer": "singlewindow",
        "entryCount": 1,
        "entries": [{"apiId": "singlewindow.verify", "specDigest": sha256_hex('{"fixture":true}'), "version": "1.0.0"}],
    }
    digest = sha256_hex(jcs_canonicalize(catalogue))
    private = Ed25519PrivateKey.generate()
    header = b64url_encode(json.dumps({"alg": "EdDSA", "typ": "JWT", "kid": "singlewindow-0"}, separators=(",", ":")).encode())
    body = b64url_encode(jcs_canonicalize({"catalogueDigest": digest, "catalogueVersion": "1.0.0", "generatedAt": catalogue["generatedAt"], "producer": "singlewindow"}).encode())
    signature = b64url_encode(private.sign(f"{header}.{body}".encode("ascii")))
    envelope = {"envelopeVersion": "1.0", "catalogue": catalogue, "catalogueDigest": digest,
                "signatureStatus": "SIGNED", "jws": f"{header}.{body}.{signature}", "kid": "singlewindow-0"}
    public_b64 = b64url_encode(private.public_key().public_bytes_raw())
    ok = run(envelope, public_b64)
    if ok != 0:
        return 1
    # Tamper must fail closed.
    envelope["catalogue"]["entries"][0]["specDigest"] = "0" * 64
    return 0 if run(envelope, public_b64) != 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalogue", help="read the envelope from a local file instead of MARKETPLACE_CATALOGUE_URL")
    parser.add_argument("--selftest", action="store_true", help="ephemeral-key sign/verify/tamper round-trip")
    args = parser.parse_args()
    if args.selftest:
        print("selftest: sign → verify (expect OK) → tamper (expect failure)")
        result = selftest()
        print("selftest:", "OK" if result == 0 else "FAILED")
        return result
    try:
        envelope = load_catalogue(args)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return run(envelope, os.environ.get("MARKETPLACE_SIGNING_PUBLIC_KEY"))


if __name__ == "__main__":
    sys.exit(main())
