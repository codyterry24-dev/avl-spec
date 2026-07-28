# Tamper-Evident Logging Test Protocol (AVL-1)

Status: DRAFTED - NOT YET EXECUTED. This document defines the protocol and fixture set. Results are only valid once run and reported; do not cite as a completed benchmark until an execution log is attached.

## 1. Purpose
Validate AVL-1 (Merkle Logging) tamper-detection guarantees defined in the AVL spec README against a fixed set of 50 representative ZoeEventBundle records.

## 2. Scope
- In scope: AVL-1 tamper-evidence only (Merkle root + commitment chain integrity).
- Out of scope: AVL-2 lattice scoring, AVL-3 signing, AVL-4 anchoring.
- Tests detection, not prevention.

## 3. Test Corpus: 50 Representative Agent Actions
5 categories x 10 events:
- Data retrieval (query_execution)
- Content generation (text_generation)
- Classification/scoring (risk_classification)
- Tool/API invocation (external_tool_call)
- Human-escalation (human_handoff)

Each record contains required AVL-1 fields: event_id, timestamp, model_id, input_hash, output_hash, decision_class, risk_level, actor_id.

## 4. Protocol Steps
1. Baseline construction: build Merkle tree + temporal hash-chain over all 50 fixtures per AVL-1 formulas. Record final commitment C_50 and Merkle root.
2. Reproducibility check: rebuild independently; C_50 must match exactly.
3. Tamper injection (10 scenarios T1-T10): mutate a copy, rebuild, compare to baseline C_50.
   - T1: mutate output_hash early (index 3)
   - T2: mutate output_hash late (index 47)
   - T3: delete one event (index 25)
   - T4: insert one unlogged event
   - T5: reorder two adjacent events
   - T6: mutate timestamp only
   - T7: mutate actor_id only
   - T8: duplicate one event record
   - T9: truncate dataset to 49 events
   - T10: flip single hex char in one input_hash
4. Detection scoring: expect chain mismatch on all 10/10 scenarios.
5. False-positive check: run untampered baseline 5 additional times; expect 0 false positives.

## 5. Pass Criteria
- [ ] All 50 fixtures conform to ZoeEventBundle schema
- [ ] SHA3-256 used throughout (no SHA-256)
- [ ] Baseline C_50 reproducible across 2 independent runs
- [ ] 10/10 tamper scenarios correctly detected
- [ ] 0/5 false positives on untampered data
- [ ] Merkle root exportable as valid 64-char hex string

## 6. Explicit Limitations
- N=50 is an illustrative sample, not a statistically powered benchmark.
- Single-machine, single-run, non-adversarial beyond the 10 scripted mutations.
- Does not test AVL-2/3/4.
- Not a completed benchmark until executed and results logged in RESULTS.md.

## 7. Execution
Run via `python run_tamper_test.py` against `fixtures.json`. Requires Python 3.10+ (hashlib has native SHA3-256 support in 3.6+). Output must be logged to RESULTS.md with timestamp, environment, and raw pass/fail per scenario before any claim of verification is made.
