# AXT Labs Trust Page

> This page is the single source of truth for all ZOE verification claims, proof surfaces, and Article 12 compliance documentation.
> Hosted mirror: https://axtlabs.ai/trust

---

## ⚡ EU AI Act Article 12 — Enforcement: August 2, 2026

Article 12 of the EU AI Act mandates that providers of high-risk AI systems implement automatic logging capable of:

- Recording events throughout the operational lifetime of the system (Art. 12.1)
- Ensuring logs are appropriately sequenced with timestamps (Art. 12.3a)
- Recording reference database inputs (Art. 12.3b)
- Enabling input data traceability (Art. 12.3c)
- Facilitating human oversight and post-hoc investigation (Art. 12.3d)

**ZOE satisfies Article 12 at AVL-2 and above.** The per-inference Merkle log with SHA3-256 commitment chain is purpose-built to satisfy these requirements natively — not via documentation retrofit.

[Full Article 12 text →](https://artificialintelligenceact.eu/article/12)

---

## ZOE vs. Document Audit — The Critical Distinction

| Capability | Document Audit Layer | ZOE Runtime Layer |
|---|---|---|
| Verifies documentation exists | ✅ | ✅ |
| Proves what the AI actually did per inference | ❌ | ✅ |
| Runtime inference log integrity check | ❌ | ✅ |
| Continuous drift detection | ❌ | ✅ |
| Cryptographic non-repudiation | ❌ | ✅ (AVL-3+) |
| Immutable audit record | ❌ | ✅ (AVL-4) |

---

## Live Proof Assets

| Asset | URL | Status |
|---|---|---|
| AVL Specification v1.0 | https://github.com/codyterry24-dev/avl-spec | ✅ LIVE |
| Dogfood Proof Packet | https://raw.githubusercontent.com/codyterry24-dev/avl-spec/main/proof-packets/zoe-axtlabs-dogfood-001.json | ✅ LIVE |
| ZOE Benchmark (102 tasks) | https://github.com/codyterry24-dev/ZOE-Lattice-Integrity-Benchmark---AXT-Labs | ✅ LIVE |
| arXiv Paper | *(submission pending — add URL once confirmed)* | 🟡 PENDING |
| ZOE Demo | https://demo.zoe.axtlabs.co | ✅ LIVE |

---

## AVL Verification Levels

| Level | Capability | Article 12 Coverage | Pricing |
|---|---|---|---|
| AVL-1 | Merkle logging, SHA3-256 hash chain | Art. 12(1)(2)(3a) | Free scan |
| AVL-2 | + 9D tensor DCS scoring, SHIP GATE | + Art. 12(3b)(3c) | $250/mo or $1,500 one-time |
| AVL-3 | + Ed25519 signed proof packets | + Art. 12(3d), non-repudiation | $2,500/mo |
| AVL-4 | + Arweave/IPFS anchoring, OPA policies, SLSA-3 | Full Art. 12 + audit sovereignty | Enterprise ($25K–$100K) |

---

## Dogfood Result — AXT Labs Self-Verification

AXT Labs runs ZOE on its own infrastructure. The avl-spec repository was verified on July 30, 2026:

```
Gate:              PASS
AVL Level:         AVL-2
DCS Score:         0.9767  (threshold: 0.85)
Tamper Rate:       0.0%
Commitment Chain:  INTACT
Ethics Kernel:     INVIOLATE
Art. 12 Posture:   COMPLIANT at AVL-2
Duration:          847ms
```

[View full proof packet →](./proof-packets/zoe-axtlabs-dogfood-001.json)

---

## SOC 2 Status

**Current:** Security posture document published (see SECURITY.md).  
**Planned:** SOC 2 Type II audit engagement — Q4 2026.  
**Honest note:** SOC 2 Type II certification is not yet issued. The posture document reflects controls currently in place.

---

## Contact

**Cody Terry** — Founder, AXT Labs  
Email: cody@axtlabs.co  
Demo: https://demo.zoe.axtlabs.co  
LinkedIn: https://linkedin.com/in/codyterry  

---

*AXT Labs — Runtime verification for the AI agent era.*
