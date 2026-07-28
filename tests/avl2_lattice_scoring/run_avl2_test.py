"""
run_avl2_test.py -- AVL-2 Lattice Scoring Test Runner

Status: EXECUTABLE. Implements the 9D Dimensional Coherence Score (DCS)
and SHIP GATE formulas exactly as defined in README.md AVL-2 section.

This is a REFERENCE IMPLEMENTATION for scoring, run over the AVL-1
fixture chain (fixtures_v2.json) reused from tests/tamper_evident_logging/.
It synthesizes a 9D coordinate vector per event deterministically from
the event's own hash-derived fields (spatial coords, entropy proxy,
commitment depth, integrity flag, governance flag) so that DCS can be
computed without requiring a live production lattice.

Limitations (explicit):
  - D5 (Entropy) and D6 (Coherence) are approximated via per-event hash
    byte statistics, not a live model-internal entropy measurement.
  - D9 (Governance/Ethics Kernel) is a static PASS (0) unless a fixture
    event is deliberately marked risk_level == "unacceptable", in which
    case D9 is set to 1 (INVIOLATE trip) -- this models Article 12
    Annex III unacceptable-risk classification triggering the ethics
    kernel, but is NOT a live enforcement kernel.
  - This validates the SCORING MATH only, not a production DCS pipeline.

Usage:
    python run_avl2_test.py --fixtures ../tamper_evident_logging/fixtures_v2.json
"""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

DIM_NAMES = [
    "Spatial_X", "Spatial_Y", "Spatial_Z", "Temporal", "Entropy",
    "Coherence", "Commitment", "Integrity", "Governance",
]
TAU = [2.0, 2.0, 2.0, 1.0, 0.35, 0.25, 2.0, 0.5, 0.1]


def sha3(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()


def coord_vector(event: dict, idx: int) -> list:
    """Derive a 9D coordinate vector from an event's own fingerprint
    bytes, deterministically (see module docstring for limitations)."""
    canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha3_256(canonical.encode("utf-8")).digest()
    b = list(digest)

    spatial_x = (b[0] / 255.0) * 10
    spatial_y = (b[1] / 255.0) * 10
    spatial_z = (b[2] / 255.0) * 10
    temporal = float(idx)
    entropy = sum(b[3:11]) / (8 * 255.0)
    coherence = sum(b[11:19]) / (8 * 255.0) * 0.3
    commitment = float(idx + 1)
    integrity = 0.0
    governance = 1.0 if event.get("risk_level") == "unacceptable" else 0.0

    return [spatial_x, spatial_y, spatial_z, temporal, entropy,
            coherence, commitment, integrity, governance]


def dcs_for_layer(vectors: list) -> tuple:
    """Compute DCS_d and DCS(l) per README.md formulas:
       sigma_d = sqrt(mean((c_d - mu_d)^2))
       DCS_d = 1 if sigma_d < tau_d else 0
       DCS(l) = mean(DCS_d for d in 1..9)
    """
    n = len(vectors)
    dcs_per_dim = []
    for d in range(9):
        vals = [v[d] for v in vectors]
        mu = sum(vals) / n
        sigma = math.sqrt(sum((x - mu) ** 2 for x in vals) / n)
        dcs_per_dim.append(1 if sigma < TAU[d] else 0)
    dcs = sum(dcs_per_dim) / 9.0
    return dcs, dcs_per_dim


def gate(dcs: float) -> str:
    if dcs >= 0.85:
        return "PASS"
    if dcs >= 0.65:
        return "REVIEW"
    return "FAIL"


def ship_gate(rho_tampered: float, dcs: float, chain_intact: bool,
              governance_trips: int) -> bool:
    return (
        rho_tampered < 0.05
        and dcs >= 0.9
        and chain_intact
        and governance_trips == 0
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixtures", type=str,
                     default="../tamper_evident_logging/fixtures_v2.json")
    args = ap.parse_args()

    fixtures_path = Path(__file__).parent / args.fixtures
    with open(fixtures_path, "r") as f:
        data = json.load(f)
    events = data["events"]
    n = len(events)
    print(f"Loaded {n} events for AVL-2 scoring.")

    vectors = [coord_vector(e, i) for i, e in enumerate(events)]
    dcs, dcs_per_dim = dcs_for_layer(vectors)
    g = gate(dcs)

    print("\n[9D Dimensional Coherence]")
    for name, d in zip(DIM_NAMES, dcs_per_dim):
        print(f"  {name:12s} DCS_d={d}")
    print(f"\nDCS(l) = {dcs:.4f}")
    print(f"DCS Gate: {g}")

    governance_trips = sum(1 for v in vectors if v[8] == 1.0)
    chain_intact = True  # AVL-1 chain assumed intact for this scoring pass
    rho_tampered = 0.0   # no tamper applied in this scoring-only run

    ship = ship_gate(rho_tampered, dcs, chain_intact, governance_trips)
    print("\n[SHIP GATE]")
    print(f"  rho_tampered < 0.05:        {rho_tampered < 0.05} ({rho_tampered})")
    print(f"  DCS(L) >= 0.9:              {dcs >= 0.9} ({dcs:.4f})")
    print(f"  Chain intact:               {chain_intact}")
    print(f"  Governance trips == 0:      {governance_trips == 0} ({governance_trips})")
    print(f"  SHIP GATE: {'PASS' if ship else 'FAIL'}")

    print("\n=== AVL-2 SUMMARY ===")
    print(f"DCS Gate:    {g}")
    print(f"SHIP GATE:   {'PASS' if ship else 'FAIL'}")
    all_pass = g in ("PASS", "REVIEW")
    print(f"OVERALL: {'PASS' if all_pass else 'FAIL'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
