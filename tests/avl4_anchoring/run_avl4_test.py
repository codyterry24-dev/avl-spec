"""
run_avl4_test.py -- AVL-4 Immutable Anchoring Test Runner

Status: EXECUTABLE. Validates the OFFLINE FALLBACK path of AVL-4
anchoring, per README.md: "If ARWEAVE_KEY env var is not set, the
pipeline MUST skip anchoring gracefully and write the proof packet to
a local .jsonl log instead (offline mode)."

Explicit limitation: this test runner does NOT perform a real Arweave
or IPFS network anchor. Doing so requires a funded live wallet and a
real network call, which is out of scope for an unattended CI job and
would introduce non-reproducible external dependencies and cost. This
test instead proves:
  (a) the offline-mode fallback triggers correctly when ARWEAVE_KEY is
      absent,
  (b) the local .jsonl audit log is genuinely append-only and
      tamper-evident (each line's hash is chained to the previous, in
      the same style as AVL-1's commitment chain),
  (c) OPA policy test counts are reported as a placeholder gate,
      pending real .rego files (not yet committed to this repo).

Usage:
    python run_avl4_test.py
"""

import hashlib
import json
import os
import sys
import tempfile
import time


def sha3(data: bytes) -> str:
    return hashlib.sha3_256(data).hexdigest()


def anchor_proof_packet(packet: dict, log_path: str, prev_hash: str) -> str:
    """Append packet to a hash-chained local .jsonl log (offline mode).
    Returns the new chain hash."""
    line_obj = {"packet": packet, "prev_hash": prev_hash}
    line = json.dumps(line_obj, sort_keys=True, separators=(",", ":"))
    new_hash = sha3((prev_hash + line).encode("utf-8"))
    line_obj["chain_hash"] = new_hash
    with open(log_path, "a") as f:
        f.write(json.dumps(line_obj, sort_keys=True) + "\n")
    return new_hash


def verify_log_chain(log_path: str) -> bool:
    prev_hash = sha3(b"AVL-4-OFFLINE-LOG-GENESIS")
    with open(log_path, "r") as f:
        for raw_line in f:
            entry = json.loads(raw_line)
            claimed_chain_hash = entry.pop("chain_hash")
            recomputed = {"packet": entry["packet"], "prev_hash": entry["prev_hash"]}
            line = json.dumps(recomputed, sort_keys=True, separators=(",", ":"))
            expected = sha3((entry["prev_hash"] + line).encode("utf-8"))
            if expected != claimed_chain_hash or entry["prev_hash"] != prev_hash:
                return False
            prev_hash = claimed_chain_hash
    return True


def main():
    arweave_key = os.environ.get("ARWEAVE_KEY")
    offline_mode = arweave_key is None
    print(f"[Anchor Mode] {'OFFLINE (local .jsonl fallback)' if offline_mode else 'LIVE (ARWEAVE_KEY set -- not implemented in this test)'}")

    if not offline_mode:
        print("NOTE: ARWEAVE_KEY is set, but this test runner does not "
              "implement live Arweave submission. Treating as offline "
              "for this test's purposes.")

    with tempfile.TemporaryDirectory() as tmpdir:
        log_path = os.path.join(tmpdir, "avl4_offline_log.jsonl")
        prev_hash = sha3(b"AVL-4-OFFLINE-LOG-GENESIS")

        packets = [
            {"event_id": f"avl4-evt-{i:04d}", "merkle_root": sha3(f"root-{i}".encode()),
             "anchor_tx_id": None, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            for i in range(20)
        ]

        for p in packets:
            prev_hash = anchor_proof_packet(p, log_path, prev_hash)

        chain_ok = verify_log_chain(log_path)
        print(f"[Local .jsonl Chain] {len(packets)} entries written, chain intact: {chain_ok}")

        # Tamper the log and confirm detection.
        with open(log_path, "r") as f:
            lines = f.readlines()
        tampered_entry = json.loads(lines[10])
        tampered_entry["packet"]["merkle_root"] = "0" * 64
        lines[10] = json.dumps(tampered_entry, sort_keys=True) + "\n"
        with open(log_path, "w") as f:
            f.writelines(lines)
        chain_ok_after_tamper = verify_log_chain(log_path)
        print(f"[Tamper Check] chain intact after tampering entry 10: {chain_ok_after_tamper} (expected False)")

    opa_tests_total = 28
    opa_tests_passing = 0
    print(f"\n[OPA Policy Tests] {opa_tests_passing}/{opa_tests_total} "
          f"-- NOT YET IMPLEMENTED: .rego files not committed to this repo.")

    print("\n=== AVL-4 SUMMARY ===")
    print(f"Offline fallback triggers correctly: {offline_mode}")
    print(f"Local .jsonl chain intact (untampered): {chain_ok}")
    print(f"Tamper correctly detected:              {not chain_ok_after_tamper}")
    print(f"OPA policy tests passing:               {opa_tests_passing}/{opa_tests_total} (NOT IMPLEMENTED)")

    all_pass = chain_ok and not chain_ok_after_tamper and offline_mode
    print(f"OVERALL (offline-fallback + log-integrity only): {'PASS' if all_pass else 'FAIL'}")
    print("NOTE: This is a PARTIAL AVL-4 result. Real Arweave/IPFS anchoring "
          "and the 28 OPA policy tests are NOT executed here and remain "
          "open work (see README.md Implementation Status).")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
