# Agent Sandboxing & Runtime Enforcement Specification

> Extension of the AVL Specification — defines isolation, containment, and runtime-enforcement requirements for AI agents operating under ZOE/AVL verification. This document maps sandboxing architecture and enforcement controls to AVL-1 through AVL-4 and to EU AI Act Article 12 traceability requirements.

Status: v0.1-draft | AXT Labs | August 2026

---

## 1. Purpose

AVL defines how AI system behavior is cryptographically logged, scored, signed, and anchored. This document defines the companion requirement: how the agent's execution environment is isolated (sandboxing) and how policy is enforced at runtime (runtime enforcement), so that what AVL proves is actually true of a contained, tamper-resistant execution surface.

Without sandboxing + runtime enforcement, AVL proof packets can faithfully log a compromised or out-of-policy execution. This spec closes that gap.

---

## 2. Isolation Tiers (Sandboxing Primitives)

| Tier | Primitive | Isolation Strength | Boot Overhead | AVL Mapping |
|------|-----------|--------------------|----------------|-------------|
| S-0 | Namespace/cgroup container (e.g. runc) | Process-level, shared kernel | ~10ms | Not sufficient alone for AVL-3/4 |
| S-1 | gVisor (userspace kernel interception) | Syscall-filtered, shared host kernel | ~50ms | Minimum for AVL-2 |
| S-2 | Firecracker / Kata microVM | Hardware-virtualized, dedicated kernel | ~100-125ms | Required for AVL-3 |
| S-3 | Confidential computing (SEV-SNP / TDX) | Memory-encrypted, attestable | ~150-300ms | Required for AVL-4 (regulated/high-risk deployments) |

**Rule:** the sandboxing tier used for a given agent run MUST be recorded in the AVL proof packet metadata (`sandbox_tier`) so that verification consumers can assess isolation strength alongside the cryptographic proof.

---

## 3. Build Requirements

### 3.1 Isolation
- [ ] Agent execution MUST occur inside an isolation boundary at or above the tier declared in the deployment's compliance profile.
- [ ] No agent process may share a PID, network, or mount namespace with the host or with another tenant's agent.
- [ ] Nested isolation (sandbox-within-sandbox) MUST be supported for high-assurance deployments (AVL-4), enabling defense-in-depth escape testing.

### 3.2 Filesystem
- [ ] Root filesystem MUST be read-only except for an explicitly declared writable scratch path.
- [ ] No bind-mounts of host credential stores, SSH keys, or cloud metadata directories.
- [ ] All filesystem writes during a session MUST be diffable and included in the proof packet's `fs_diff_hash`.

### 3.3 Network Egress
- [ ] Default-deny egress; allowlist only.
- [ ] Cloud metadata endpoints (`169.254.169.254`, GCP/AWS/Azure equivalents) MUST be blocked unconditionally.
- [ ] RFC 1918 private ranges blocked unless explicitly required and declared.
- [ ] DNS rebinding protection: resolved IPs must be re-validated against the allowlist post-resolution.

### 3.4 Resource Ceilings
- [ ] CPU, memory, and PID limits enforced via cgroup v2; violations trigger immediate suspension, not throttling-only.
- [ ] Wall-clock execution timeout enforced per task; timeout event MUST be logged as a proof packet entry, not silently dropped.

### 3.5 Credential Hygiene
- [ ] No long-lived credentials injected into the sandbox. Use short-TTL, scoped tokens issued per-session.
- [ ] Secrets MUST NOT appear in the sandbox's environment variables in plaintext; use an in-memory secret broker with audit logging on every read.

### 3.6 Control-Plane / Workload-Plane Separation
- [ ] The component issuing policy decisions (control plane) MUST run outside the sandbox boundary of the agent it governs.
- [ ] Control-plane compromise must not be achievable via any channel exposed to the workload plane.

---

## 4. Runtime Enforcement Model

Runtime enforcement is staged, not binary, to avoid false-positive lockouts while still building an auditable behavioral baseline.

### Stage 1 — Discovery
Passive observation only. All agent actions logged (AVL-1 Merkle logging) with zero blocking. Establishes the behavioral baseline.

### Stage 2 — Observe
Policy rules drafted from Stage 1 data but run in shadow/dry-run mode. Violations are scored (AVL-2 DCS) but not enforced.

### Stage 3 — Selective Enforcement
High-confidence rules (low false-positive rate) begin blocking in real time. Each block event generates a signed proof packet (AVL-3).

### Stage 4 — Full Enforcement
All validated policy rules enforced inline via OPA (Open Policy Agent) at the syscall/API boundary. Enforcement decisions are anchored immutably (AVL-4).

**Requirement:** every transition between stages for a given agent/policy pair MUST itself be a signed, timestamped event in the audit trail.

---

## 5. Testing Methodology

### 5.1 Containment / Escape Testing
- Use a sandbox-escape benchmark suite (nested sandbox-within-sandbox scenarios) covering at minimum:
  - Filesystem escape (symlink traversal, mount namespace abuse)
  - Network egress bypass (DNS rebinding, IPv6 fallback, metadata endpoint access)
  - Resource exhaustion / fork-bomb containment
  - Credential exfiltration attempts (env var scraping, memory inspection)
  - Privilege escalation via crafted syscalls
- Target: 0% successful escapes across all scenarios at the declared isolation tier before promotion to Stage 3/4 enforcement.

### 5.2 Enforcement Layer Testing
Five core metrics, tracked per policy rule and in aggregate:

| Metric | Definition | Target |
|--------|------------|--------|
| Detection rate | % of policy-violating actions correctly flagged | >99% before Stage 3 promotion |
| False positive rate | % of compliant actions incorrectly flagged | <1% before Stage 3 promotion |
| Bypass rate | % of adversarial test cases that evade enforcement | 0% at Stage 4 |
| Latency overhead | Added latency per enforced action | <10ms p95 |
| Attack-vector coverage | % of OWASP LLM Top 10 / MITRE ATLAS techniques with a corresponding test case | 100% |

### 5.3 Regression & Provenance
- All test corpora MUST be versioned; a policy change is not shippable unless it passes the full versioned adversarial corpus in CI.
- Test runs MUST themselves emit AVL proof packets (dogfooding AVL-1 through AVL-3 on the test harness), so that test *results* are also tamper-evident.
- SLSA-3 provenance required for the sandboxing/enforcement engine build artifacts, consistent with existing AVL provenance requirements.

---

## 6. Showing Results (Reporting Format)

Since no external standards body currently sets pass/fail thresholds for AI agent sandboxing, credibility rests on methodology transparency rather than a claimed certification. Each test run MUST produce:

1. **Isolation tier declaration** — which S-tier was tested (Section 2).
2. **Escape test matrix** — pass/fail per scenario category (Section 5.1), with 0% escape rate required for the claimed tier.
3. **Enforcement metrics table** — the five metrics from Section 5.2, with before/after comparison across enforcement stages.
4. **Taxonomy mapping** — each test case mapped to an OWASP LLM Top 10 or MITRE ATLAS technique ID.
5. **Signed proof packet reference** — hash/signature of the AVL proof packet covering the test run itself, so results are independently re-verifiable.
6. **CI badge** — pass/fail status surfaced in repo README, generated from the latest scheduled run, not a manually-asserted claim.

---

## 7. Relationship to AVL Levels

| AVL Level | Sandboxing Requirement | Enforcement Stage Required |
|-----------|------------------------|------------------------------|
| AVL-1 | S-0 minimum, logging only | Stage 1 (Discovery) |
| AVL-2 | S-1 minimum | Stage 2 (Observe) |
| AVL-3 | S-2 minimum | Stage 3 (Selective Enforcement) |
| AVL-4 | S-3 required for high-risk/regulated | Stage 4 (Full Enforcement) |

---

## 8. Open Items

- [ ] Formal `.rego` policy files for OPA enforcement (currently placeholder gate per AVL-4 test runner notes).
- [ ] Live escape-test harness implementation (this spec defines requirements; executable test runner to be added under `tests/sandboxing_enforcement/`).
- [ ] Confidential computing (SEV-SNP/TDX) attestation format for `sandbox_tier: S-3` proof packets.

---

## Citation

See `CITATIONS.md` for sourcing on isolation primitives, enforcement staging model, and benchmark methodology referenced in this document.

## License

Apache 2.0 — consistent with root AVL Specification.
