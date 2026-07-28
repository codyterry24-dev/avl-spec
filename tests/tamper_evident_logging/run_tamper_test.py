"""
run_tamper_test.py -- AVL-1 Tamper-Evident Logging Test Runner

Status: DRAFTED, UNEXECUTED as of commit time. This script has not been run
in a live Python environment by the author or an automated CI job as of this
commit. Do not cite pass/fail results from this file until it has actually
been executed and RESULTS.md has been populated with real output.

Implements the protocol defined in PROTOCOL.md against fixtures.json.
Follows AVL-1 spec formulas exactly (see ../../README.md):

    f = SHA3-256(event_bytes)                       # node fingerprint
    M_l = SHA3-256(h_0 || h_1 || ... || h_n)         # Merkle root of layer
    C_l = SHA3-256(C_(l-1) || M_l)                   # commitment chain
    C_0 = SHA3-256(genesis_seed)

Usage:
    python run_tamper_test.py

Requires: Python 3.6+ (hashlib.sha3_256 is stdlib, no external deps).
"""

import hashlib
import json
import copy
import sys
from pathlib import Path

GENESIS_SEED = b"AXT-LABS-AVL-1-GENESIS-SEED-v1.0-draft"
REQUIRED_FIELDS = [
    "event_id", "timestamp", "model_id", "input_hash",
    "output_hash", "decision_class", "risk_level", "actor_id",
]


def sha3(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()


def event_fingerprint(event: dict) -> str:
    """Canonical, order-independent fingerprint of a single event."""
    canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
    return sha3(canonical.encode("utf-8"))


def build_chain(events: list) -> tuple:
    """
    Build the temporal hash-chain over a list of events.
    Returns (final_commitment_hex, merkle_root_hex, per_event_fingerprints).
    """
    fingerprints = [event_fingerprint(e) for e in events]
    concatenated = "".join(fingerprints).encode("utf-8")
    merkle_root = sha3(concatenated)

    c = sha3(GENESIS_SEED)  # C_0
    c = sha3((c + merkle_root).encode("utf-8"))  # C_1 (single-layer tree here)

    return c, merkle_root, fingerprints


def validate_schema(events: list) -> list:
    """Return list of validation errors, empty if all events conform."""
    errors = []
    for i, e in enumerate(events):
        missing = [f for f in REQUIRED_FIELDS if f not in e]
        if missing:
            errors.append(f"event index {i} missing fields: {missing}")
    return errors


def apply_tamper(events: list, scenario: str) -> list:
    """Return a tampered COPY of events per scenario id T1-T10."""
    tampered = copy.deepcopy(events)

    if scenario == "T1":  # mutate output_hash early (index 3)
        tampered[3]["output_hash"] = "0" * 64
    elif scenario == "T2":  # mutate output_hash late (index 47)
        tampered[47]["output_hash"] = "0" * 64
    elif scenario == "T3":  # delete one event (index 25)
        del tampered[25]
    elif scenario == "T4":  # insert one unlogged event
        injected = copy.deepcopy(tampered[25])
        injected["event_id"] = "injected-0000-0000-0000-000000000000"
        tampered.insert(26, injected)
    elif scenario == "T5":  # reorder two adjacent events
        tampered[10], tampered[11] = tampered[11], tampered[10]
    elif scenario == "T6":  # mutate timestamp only
        tampered[5]["timestamp"] = "2099-01-01T00:00:00+00:00"
    elif scenario == "T7":  # mutate actor_id only
        tampered[5]["actor_id"] = "tampered-actor"
    elif scenario == "T8":  # duplicate one event record
        tampered.append(copy.deepcopy(tampered[12]))
    elif scenario == "T9":  # truncate dataset to 49 events
        tampered = tampered[:49]
    elif scenario == "T10":  # flip single hex char in one input_hash
        h = tampered[8]["input_hash"]
        flipped_char = "0" if h[0] != "0" else "1"
        tampered[8]["input_hash"] = flipped_char + h[1:]
    else:
        raise ValueError(f"Unknown scenario: {scenario}")

    return tampered


def main():
    fixtures_path = Path(__file__).parent / "fixtures.json"
    with open(fixtures_path, "r") as f:
        data = json.load(f)
    events = data["events"]

    print(f"Loaded {len(events)} fixture events.")
    if len(events) != 50:
        print(f"WARNING: expected 50 events, found {len(events)}")

    schema_errors = validate_schema(events)
    print(f"\n[Schema Validation] {'PASS' if not schema_errors else 'FAIL'}")
    for err in schema_errors:
        print(f"  - {err}")

    baseline_c1, baseline_root, _ = build_chain(events)
    baseline_c2, _, _ = build_chain(events)
    reproducible = baseline_c1 == baseline_c2
    print(f"\n[Reproducibility Check] {'PASS' if reproducible else 'FAIL'}")
    print(f"  Baseline commitment: {baseline_c1}")
    print(f"  Merkle root:         {baseline_root}")

    scenarios = [f"T{i}" for i in range(1, 11)]
    detected = 0
    print("\n[Tamper Detection Scenarios]")
    for s in scenarios:
        tampered_events = apply_tamper(events, s)
        tampered_c, _, _ = build_chain(tampered_events)
        mismatch = tampered_c != baseline_c1
        detected += int(mismatch)
        status = "DETECTED" if mismatch else "MISSED (FAIL)"
        print(f"  {s}: {status}")

    print(f"\n  Tamper detection rate: {detected}/10")

    false_positives = 0
    print("\n[False-Positive Check] (5 repeated runs on untampered data)")
    for i in range(5):
        c, _, _ = build_chain(events)
        mismatch = c != baseline_c1
        false_positives += int(mismatch)
        print(f"  Run {i+1}: {'MISMATCH (false positive)' if mismatch else 'match (correct)'}")

    print(f"\n  False positives: {false_positives}/5")

    print("\n=== SUMMARY ===")
    print(f"Schema valid:        {'YES' if not schema_errors else 'NO'}")
    print(f"Reproducible:        {'YES' if reproducible else 'NO'}")
    print(f"Tamper detection:    {detected}/10")
    print(f"False positives:     {false_positives}/5")
    all_pass = (not schema_errors) and reproducible and detected == 10 and false_positives == 0
    print(f"OVERALL:             {'PASS' if all_pass else 'FAIL - see details above'}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
