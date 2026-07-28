"""
generate_fixtures.py -- AVL-1 Fixture Generator (REAL SHA3-256)

Status: EXECUTABLE. Produces tests/tamper_evident_logging/fixtures_v2.json
containing N events where input_hash/output_hash are REAL
hashlib.sha3_256 digests computed over representative model
input/output payloads (not placeholder strings).

This directly addresses the v1 limitation documented in RESULTS.md:
  "Synthetic hashes: fixtures.json uses deterministic placeholder
  strings for input_hash/output_hash, not real SHA3-256 digests of
  real model inputs/outputs."

Usage:
    python generate_fixtures.py --n 500 --seed 42 \
        --out fixtures_v2.json

Requires: Python 3.6+ (hashlib.sha3_256 is stdlib, no external deps).
"""

import argparse
import hashlib
import json
import random
import uuid
from datetime import datetime, timedelta, timezone

DECISION_CLASSES = [
    "loan_approval", "content_moderation", "fraud_flag",
    "resume_screening", "medical_triage_priority", "credit_scoring",
    "access_control", "price_optimization", "recommendation",
    "anomaly_detection",
]
RISK_LEVELS = ["minimal", "limited", "high", "unacceptable"]
MODEL_IDS = [
    "zoe-verifier-v1.2", "zoe-verifier-v1.3", "axt-lattice-core-v0.9",
    "axt-lattice-core-v1.0",
]


def sha3(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()


def synth_model_input(rng: random.Random, idx: int) -> bytes:
    """Representative model INPUT payload -- realistic structured
    JSON a model would actually receive, not a placeholder string."""
    payload = {
        "request_id": str(uuid.UUID(int=rng.getrandbits(128))),
        "features": [round(rng.uniform(-3, 3), 6) for _ in range(12)],
        "context": {
            "session": idx,
            "locale": rng.choice(["en-US", "en-GB", "de-DE", "fr-FR"]),
        },
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def synth_model_output(rng: random.Random, idx: int) -> bytes:
    """Representative model OUTPUT payload."""
    payload = {
        "prediction": round(rng.uniform(0, 1), 6),
        "class_probs": [round(rng.uniform(0, 1), 6) for _ in range(4)],
        "latency_ms": round(rng.uniform(5, 250), 2),
        "idx": idx,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def build_event(rng: random.Random, idx: int, base_time: datetime) -> dict:
    model_input = synth_model_input(rng, idx)
    model_output = synth_model_output(rng, idx)
    ts = base_time + timedelta(seconds=idx * rng.uniform(1, 30))
    return {
        "event_id": str(uuid.UUID(int=rng.getrandbits(128))),
        "timestamp": ts.isoformat(),
        "model_id": rng.choice(MODEL_IDS),
        "input_hash": sha3(model_input),
        "output_hash": sha3(model_output),
        "decision_class": rng.choice(DECISION_CLASSES),
        "risk_level": rng.choice(RISK_LEVELS),
        "actor_id": f"actor-{rng.randint(1, 25):03d}",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=500,
                     help="Number of fixture events (default 500, >50 baseline)")
    ap.add_argument("--seed", type=int, default=42,
                     help="RNG seed for full reproducibility")
    ap.add_argument("--out", type=str, default="fixtures_v2.json")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    base_time = datetime(2026, 7, 1, tzinfo=timezone.utc)
    events = [build_event(rng, i, base_time) for i in range(args.n)]

    out = {
        "schema": "avl-1-fixture-v2",
        "generated_with": "generate_fixtures.py",
        "seed": args.seed,
        "n": args.n,
        "hash_note": (
            "input_hash/output_hash are real hashlib.sha3_256 digests "
            "computed over representative structured JSON model "
            "input/output payloads generated deterministically from --seed. "
            "They are NOT digests of a production model's actual traffic."
        ),
        "events": events,
    }

    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)

    print(f"Wrote {args.n} events to {args.out} (seed={args.seed})")


if __name__ == "__main__":
    main()
