"""
run_avl3_test.py -- AVL-3 Signed Proofs Test Runner

Status: EXECUTABLE (requires `cryptography` package -- see
requirements-avl3.txt / installed in CI). Implements Ed25519 signing
and verification of ProofPacket objects per README.md AVL-3 section.

Builds on AVL-1 (commitment chain) and AVL-2 (DCS score) outputs to
construct a ProofPacket:
  event_id, merkle_root, dcs_score, gate, signature, public_key, timestamp

Requirements validated:
  - Ed25519 signature over merkle_root || dcs_score || timestamp
  - Signature verifiable offline using only public_key + packet fields
  - Signing key loaded from ZOE_SIGNING_KEY env var, never hardcoded
    (falls back to an ephemeral generated key ONLY for this test run,
    clearly logged as such -- never used for production signing)

Usage:
    python run_avl3_test.py
"""

import base64
import json
import os
import sys
import time

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )
    from cryptography.hazmat.primitives import serialization
    from cryptography.exceptions import InvalidSignature
except ImportError:
    print("FATAL: `cryptography` package not installed. "
          "Run: pip install cryptography")
    sys.exit(2)


def load_or_generate_key():
    env_key = os.environ.get("ZOE_SIGNING_KEY")
    if env_key:
        print("[Key Source] Loaded ZOE_SIGNING_KEY from environment.")
        raw = base64.b64decode(env_key)
        return Ed25519PrivateKey.from_private_bytes(raw), "env"
    print("[Key Source] WARNING: ZOE_SIGNING_KEY not set. Generating an "
          "EPHEMERAL test-only key. This key is NOT persisted and MUST "
          "NEVER be used for production signing.")
    return Ed25519PrivateKey.generate(), "ephemeral-test-only"


def sign_packet(priv_key, merkle_root: str, dcs_score: float, ts: str) -> bytes:
    message = f"{merkle_root}||{dcs_score}||{ts}".encode("utf-8")
    return priv_key.sign(message)


def verify_packet(pub_key, merkle_root: str, dcs_score: float, ts: str,
                   signature: bytes) -> bool:
    message = f"{merkle_root}||{dcs_score}||{ts}".encode("utf-8")
    try:
        pub_key.verify(signature, message)
        return True
    except InvalidSignature:
        return False


def main():
    priv_key, key_source = load_or_generate_key()
    pub_key = priv_key.public_key()
    pub_hex = pub_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()

    # Representative AVL-1/AVL-2 outputs for this test packet.
    merkle_root = "4e593bb9309cc3ecf5439e38fe9bb306a785d9c42fb8da5d2146e61f4bc5313"
    dcs_score = 0.9167
    gate = "PASS"
    event_id = "avl3-test-event-0001"
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    t0 = time.perf_counter()
    signature = sign_packet(priv_key, merkle_root, dcs_score, ts)
    t1 = time.perf_counter()
    verified = verify_packet(pub_key, merkle_root, dcs_score, ts, signature)
    t2 = time.perf_counter()

    packet = {
        "event_id": event_id,
        "merkle_root": merkle_root,
        "dcs_score": dcs_score,
        "gate": gate,
        "signature": signature.hex(),
        "public_key": pub_hex,
        "timestamp": ts,
    }

    print("[ProofPacket]")
    print(json.dumps(packet, indent=2))

    sign_ms = (t1 - t0) * 1000
    verify_ms = (t2 - t1) * 1000
    roundtrip_ms = (t2 - t0) * 1000

    print(f"\n[Timing] sign={sign_ms:.3f}ms verify={verify_ms:.3f}ms "
          f"roundtrip={roundtrip_ms:.3f}ms")
    print(f"[Key Source] {key_source}")

    # Tamper check: mutate one field and confirm verify fails.
    tampered_verified = verify_packet(
        pub_key, merkle_root, dcs_score + 0.0001, ts, signature
    )

    required_fields = ["event_id", "merkle_root", "dcs_score", "gate",
                        "signature", "public_key", "timestamp"]
    has_all_fields = all(f in packet for f in required_fields)

    print("\n=== AVL-3 SUMMARY ===")
    print(f"ProofPacket has all required fields: {has_all_fields}")
    print(f"Signature verifies (correct data):   {verified}")
    print(f"Signature rejects tampered data:     {not tampered_verified}")
    print(f"Round-trip < 100ms:                  {roundtrip_ms < 100} ({roundtrip_ms:.3f}ms)")
    print(f"Key loaded from env (not hardcoded): {key_source == 'env'}")

    all_pass = (
        has_all_fields and verified and not tampered_verified
        and roundtrip_ms < 100
    )
    print(f"OVERALL: {'PASS' if all_pass else 'FAIL'}")
    if key_source != "env":
        print("NOTE: key-from-env criterion not met in this run because "
              "ZOE_SIGNING_KEY was not set; set it in CI secrets for a "
              "fully compliant run.")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
