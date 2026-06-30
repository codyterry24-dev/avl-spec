# AVL Specification

> **Adaptive Verification Lattice (AVL)** — Formal specification for ZOE's four-tier AI verification compliance levels.  
> AXT Labs | [axtlabs.co](https://axtlabs.co) | June 2026

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Spec Version](https://img.shields.io/badge/AVL_Spec-v1.0--draft-yellow)](#versioning)
[![ZOE Engine](https://img.shields.io/badge/reference_impl-ZOE--Lattice--Benchmark-blue)](https://github.com/codyterry24-dev/ZOE-Lattice-Integrity-Benchmark---AXT-Labs)

---

## What Is AVL?

The **Adaptive Verification Lattice (AVL)** is the cryptographic and scoring architecture underlying the ZOE runtime AI verification engine. It defines the formal requirements for each tier of AI system integrity verification, from basic Merkle logging to fully anchored, policy-enforced, signed proof packets.

AVL is designed to be the **minimum verifiable unit** of EU AI Act Article 12 compliance for high-risk AI deployments.

---

## AVL Levels

| Level | Name | Core Capability | Article 12 Mapping |
|-------|------|-----------------|--------------------|
| **AVL-1** | Merkle Logging | SHA3-256 Merkle tree + temporal hash-chain | Art. 12(1)(2)(3)(a) |
| **AVL-2** | Lattice Scoring | AVL-1 + 9D tensor DCS scoring | Art. 12(3)(b)(c) |
| **AVL-3** | Signed Proofs | AVL-2 + Ed25519 proof packet signing | Art. 12(3)(d) + non-repudiation |
| **AVL-4** | Immutable Anchoring | AVL-3 + IPFS/Arweave + OPA policy enforcement | Full Art. 12 + audit sovereignty |

---

## AVL-1: Merkle Logging

**Minimum viable Article 12 logging layer.**

### Requirements

1. Every AI system event MUST be captured as a `ZoeEventBundle` with the following required fields:
   - `event_id` — UUID v4
   - `timestamp` — ISO 8601 with timezone
   - `model_id` — model identifier + version
   - `input_hash` — SHA3-256 of input data
   - `output_hash` — SHA3-256 of output data
   - `decision_class` — classification of the AI decision
   - `risk_level` — EU AI Act Annex III risk classification
   - `actor_id` — system or human actor identifier

2. Event bundles MUST be hashed into an append-only Merkle tree using **SHA3-256** (not SHA-256).

3. The Merkle tree MUST implement a temporal hash-chain:
   ```
   C_0 = SHA3-256(genesis_seed)
   M_l = SHA3-256(h_(l,0) || h_(l,1) || ... || h_(l,|N|-1))
   C_l = SHA3-256(C_(l-1) || M_l)
   ```

4. The commitment chain `C_l` MUST be append-only. Any tampering with a node at any layer invalidates all subsequent `C_(l+k)` for k ≥ 0.

5. The Merkle root MUST be exportable as a hex string for external verification.

### AVL-1 PASS Criteria

- [ ] `ZoeEventBundle` has all required fields
- [ ] SHA3-256 used throughout (no SHA-256)
- [ ] Commitment chain is intact (`C_l` matches recomputed value)
- [ ] Merkle root is a valid 64-character hex string

---

## AVL-2: Lattice Scoring

**9-dimensional tensor coherence scoring over the Merkle log.**

Builds on AVL-1. All AVL-1 requirements apply.

### The 9-Dimensional Coordinate Vector

Each node in the lattice carries a 9D coordinate vector:

```
c_(l,p) = [D1, D2, D3, D4, D5, D6, D7, D8, D9]
```

| Dim | Name | Coherence Threshold τ | Description |
|-----|------|-----------------------|-------------|
| D1 | Spatial_X | 2.0 | x-axis position in 3D lattice |
| D2 | Spatial_Y | 2.0 | y-axis position |
| D3 | Spatial_Z | 2.0 | z-axis position |
| D4 | Temporal | 1.0 | layer index (tick) |
| D5 | Entropy | 0.35 | local entropy of node neighborhood |
| D6 | Coherence | 0.25 | dimensional coherence score (self-referential) |
| D7 | Commitment | 2.0 | hash-chain depth |
| D8 | Integrity | 0.5 | INTACT(0) / TAMPERED(1) state |
| D9 | Governance | 0.1 | ethics kernel constraint (0=inactive, 1=INVIOLATE) |

### Dimensional Coherence Score (DCS)

For dimension d at layer l:

```
DCS_d(l) = 1[sigma_d(l) < tau_d]

sigma_d(l) = sqrt((1/|N|) * sum_{p in N} (c_(l,p)[d] - mu_d(l))^2)

DCS(l) = (1/9) * sum_{d=1}^{9} DCS_d(l)   in [0, 1]
```

### AVL-2 Gate

```
DCS PASS:    DCS(l) >= 0.85
DCS REVIEW:  0.65 <= DCS(l) < 0.85
DCS FAIL:    DCS(l) < 0.65
```

### SHIP GATE (AVL-2 terminal condition)

All four conditions must hold simultaneously:

```
(i)   rho_L < 0.05          -- less than 5% nodes tampered
(ii)  DCS(L) >= 0.9         -- at least 8/9 dimensions coherent
(iii) C_L == expected_C_L   -- commitment chain unbroken
(iv)  D9 == 0 for all nodes -- Ethics Kernel INVIOLATE
```

### AVL-2 PASS Criteria

- [ ] All AVL-1 criteria pass
- [ ] 9D DCS computed per layer
- [ ] DCS threshold enforced: ≥ 0.85 = PASS
- [ ] SHIP GATE evaluated at terminal layer
- [ ] Entropy balance tracked: |H(l) - H(l-1)| < ε_H (default 0.05)

---

## AVL-3: Signed Proofs

**Non-repudiable proof packets via Ed25519 digital signatures.**

Builds on AVL-2. All AVL-2 requirements apply.

### Requirements

1. Every `ProofPacket` output by the pipeline MUST be signed using **Ed25519** (via PyNaCl or equivalent).

2. A `ProofPacket` MUST contain:
   - `event_id` — source event UUID
   - `merkle_root` — SHA3-256 hex (64 chars)
   - `dcs_score` — float in [0, 1]
   - `gate` — `"PASS"` | `"REVIEW"` | `"FAIL"`
   - `signature` — Ed25519 signature over `merkle_root || dcs_score || timestamp`
   - `public_key` — Ed25519 public key (hex)
   - `timestamp` — ISO 8601 signing timestamp

3. Signature MUST be verifiable offline using only the `public_key` and `ProofPacket` fields.

4. The signing key MUST be stored securely (environment variable `ZOE_SIGNING_KEY`, never in source).

### AVL-3 PASS Criteria

- [ ] All AVL-2 criteria pass
- [ ] `ProofPacket` has all required fields
- [ ] Ed25519 signature verifies against `public_key`
- [ ] Round-trip sign/verify passes in < 100ms
- [ ] Signing key loaded from environment, not hardcoded

---

## AVL-4: Immutable Anchoring + Policy Enforcement

**Sovereign, immutable audit records with OPA-enforced Article 12 compliance.**

Builds on AVL-3. All AVL-3 requirements apply.

### Arweave Anchoring

1. Every `ProofPacket` MUST be anchored to Arweave (permanent, immutable storage) after signing.
2. The Arweave transaction ID MUST be appended to the `ProofPacket` as `anchor_tx_id`.
3. If `ARWEAVE_KEY` env var is not set, the pipeline MUST skip anchoring gracefully and write the proof packet to a local `.jsonl` log instead (offline mode).
4. IPFS CID MAY be used as an alternative or supplementary anchor.

### OPA Policy Enforcement

Three OPA policies MUST pass on every `ZoeEventBundle` before a `ProofPacket` is issued:

| Policy File | Description | Tests |
|-------------|-------------|-------|
| `article12_logging.rego` | Validates required Article 12 fields present | 10 tests |
| `article12_retention.rego` | Validates log retention metadata | 8 tests |
| `avl_gate.rego` | Enforces AVL level compliance (gate threshold) | 10 tests |

**Total: 28 OPA tests must pass via `opa test policies/ -v`**

### SLSA-3 Provenance

1. The `zoe-verifier` package build MUST produce SLSA Level 3 provenance.
2. Provenance MUST be generated via `slsa-framework/slsa-github-generator`.
3. The `.intoto.jsonl` provenance file MUST be attached to every GitHub release.

### AVL-4 PASS Criteria

- [ ] All AVL-3 criteria pass
- [ ] `ProofPacket` includes `anchor_tx_id` (or local log fallback active)
- [ ] 28 OPA policy tests pass: `opa test policies/ -v`
- [ ] SLSA-3 `.intoto.jsonl` generated on every release
- [ ] Offline mode graceful (no `ARWEAVE_KEY` → local `.jsonl` fallback)

---

## Mathematical Foundation

The full formal mathematics for the ZOE lattice, including SHA3-256 fingerprint construction, entropy balance, and SHIP GATE conditions, are defined in:

**[MATH.md — ZOE-Lattice-Integrity-Benchmark---AXT-Labs](https://github.com/codyterry24-dev/ZOE-Lattice-Integrity-Benchmark---AXT-Labs/blob/main/MATH.md)**

Key equations:

```
# Node fingerprint
f_(l,p) = SHA3-256(encode(c_(l,p)) || encode(salt_(l,p)))

# Temporal hash-chain
h_(l,p) = SHA3-256(h_(l-1,p) || f_(l,p))

# Merkle root of layer l
M_l = SHA3-256(h_(l,0) || h_(l,1) || ... || h_(l,|N|-1))

# Global commitment chain
C_l = SHA3-256(C_(l-1) || M_l)
C_0 = SHA3-256(genesis_seed)
```

---

## EU AI Act Article 12 Mapping

| Article 12 Requirement | AVL Level Satisfying It |
|------------------------|------------------------|
| Art. 12(1) — Automatic event logging | AVL-1 |
| Art. 12(2) — Logging proportionate to purpose | AVL-1 |
| Art. 12(3)(a) — Use period timestamps | AVL-1 |
| Art. 12(3)(b) — Reference database logged | AVL-2 |
| Art. 12(3)(c) — Input data traceability | AVL-2 |
| Art. 12(3)(d) — Human oversight facilitation | AVL-3 (signed actor_id) |
| Full audit sovereignty + immutability | AVL-4 |

**Enforcement deadline: August 2, 2026.**

---

## Implementation Status

| Component | Status | Repo |
|-----------|--------|------|
| AVL-1 + AVL-2 (SHA-256 variant) | ✅ Implemented | [ZOE-Lattice-Integrity-Benchmark](https://github.com/codyterry24-dev/ZOE-Lattice-Integrity-Benchmark---AXT-Labs) |
| AVL-1 + AVL-2 (SHA3-256, formal spec) | 🚧 In development | [zoe-verifier](https://github.com/codyterry24-dev/zoe-verifier) (Phase 1, due July 25) |
| AVL-3 (Ed25519 signing) | 🚧 Planned | [zoe-verifier](https://github.com/codyterry24-dev/zoe-verifier) (Phase 2, due August 1) |
| AVL-4 (Arweave + OPA + SLSA-3) | 🚧 Planned | [zoe-verifier](https://github.com/codyterry24-dev/zoe-verifier) (Phase 3, due August 15) |

---

## Versioning

This specification is **AVL-spec v1.0-draft**. Breaking changes to gate thresholds, dimension definitions, or hash algorithms will increment the major version. All changes are tracked in [CHANGELOG.md](CHANGELOG.md).

---

## Citation

```bibtex
@techreport{terry2026avl,
  author       = {Cody Terry},
  title        = {Adaptive Verification Lattice (AVL) Specification v1.0},
  institution  = {AXT Labs LLC},
  year         = {2026},
  month        = {June},
  url          = {https://github.com/codyterry24-dev/avl-spec}
}
```

---

## License

Copyright 2026 AXT Labs LLC

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for full terms.

---

*Part of the ZOE platform by AXT Labs. Built for the August 2, 2026 EU AI Act Article 12 enforcement deadline.*
