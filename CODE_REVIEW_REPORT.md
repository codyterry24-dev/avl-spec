# Full Codebase Audit — avl-spec

**Reviewed at:** commit `4ae7bfe` (branch `claude/code-reviews-reports-ir3cym`)
**Date:** 2026-08-20
**Scope:** Every tracked file in the repository (no `node_modules`, no build output, no lockfiles present to skip).

---

## 1. Summary

**Repo purpose.** `avl-spec` is AXT Labs' specification and evidence repository for the "Adaptive Verification Lattice" (AVL) — a four-tier scheme (Merkle logging → lattice scoring → signed proofs → immutable anchoring) pitched as the minimum verifiable unit of EU AI Act Article 12 compliance. The repo is mostly Markdown spec/marketing content (`README.md`, `SANDBOXING.md`, `TRUST.md`, `CITATIONS.md`, `ARTICLE12_HOMEPAGE_COPY.md`), a set of Python reference/test scripts that implement and exercise the AVL-1 → AVL-4 formulas (`tests/**`), one asserted JSON "proof packet" (`proof-packets/`), two GitHub Actions workflows, and a nascent Next.js + Supabase dashboard (`axt-compliance-monitor/`) intended to visualize AI-audit-log compliance.

**What was reviewed.** All 20 tracked files, read in full: 5 root Markdown specs, 2 GitHub Actions workflow YAMLs, 1 JSON proof packet, 5 Python test/protocol files (plus their Markdown protocol/results docs and JSON fixtures), and all 7 files of the `axt-compliance-monitor` Next.js app (package.json, next.config.js, tailwind.config.ts, `.env.example`, `layout.tsx`, `globals.css`, `page.tsx`, `lib/supabase.ts`). Findings were verified by direct reproduction where practical (see Medium-1 and the hex-length checks below), not just by inspection.

**Overall risk assessment.** The Python/Merkle side of the repo (AVL-1/AVL-2 test runners) is small, careful, and mostly does what it says — including candidly documenting its own limitations, which is unusual and good practice. The two real problems are (a) the **`axt-compliance-monitor` app is committed in a non-functional, syntactically-incomplete state** (Critical — this is the literal, current state of `main`/this branch, not a hypothetical), and (b) **the compliance/trust narrative that this repo exists to support is not fully backed by its own code**: a stated AVL-3 PASS criterion isn't actually enforced by the test's exit code, and there is no visible authentication/authorization layer protecting what would be sensitive AI-audit data once the dashboard is finished. Given this repo's whole purpose is to be *the* credibility artifact for regulatory compliance claims, these gaps are more consequential than they'd be in an ordinary app repo. No secrets, injection sinks, or unsafe deserialization were found anywhere in the tracked files.

**Findings:** 1 Critical, 3 High (incl. one architectural), 5 Medium, 5 Low.

---

## 2. Findings

### Critical

#### C-1. `axt-compliance-monitor/src/app/page.tsx` is committed in a syntactically incomplete state — the app cannot build or run
**File:** `axt-compliance-monitor/src/app/page.tsx:1-125`

The file ends mid-function, inside `seedData`, with **no closing brace for the `ComplianceMonitor` component, no `return` statement, and no JSX**. Brace-balance check on the file: 44 `{` vs. 43 `}` (verified with a script, not eyeballing). The component declares seven pieces of state (`tab`, `events`, `flags`, `loading`, `lastRefresh`, `selectedEvent`, `filterSeverity`, `search`, `useSeed`) and a `seedData` callback, but never calls `seedData()`, never fetches from `supabase`, and never renders anything — the file simply stops. The commit that introduced it is explicitly titled `feat(axt): add src/app/page.tsx — ComplianceMonitor dashboard pt.1`, confirming this was intentionally a partial commit, but no follow-up "pt.2" commit exists on this branch.

**Concrete failure scenario:** Anyone running `npm install && npm run dev` or `npm run build` against this repo today gets a hard TypeScript/JSX parse error ("Unexpected end of file" / unbalanced braces). The flagship deliverable this task specifically asked to be reviewed (the "ComplianceMonitor dashboard") does not currently exist as a working artifact — it's an unclosed function.

**Suggested fix:** Either finish the component (add the data-fetching `useEffect`, wire `useSeed`/`seedData` as the demo fallback, add the tab-switched render body using the already-imported `recharts`/`lucide-react` pieces) or, if it must stay partial, mark it clearly (e.g., rename to `page.tsx.wip` or gate the route) so a broken build isn't sitting on a branch that looks otherwise finished. At minimum, do not label it as if it merges cleanly.

---

### High

#### H-1. No authentication/authorization boundary in front of AI audit data
**Files:** `axt-compliance-monitor/src/lib/supabase.ts:1-6`, `axt-compliance-monitor/src/app/page.tsx` (entire component), `axt-compliance-monitor/.env.example:1-4`

The Supabase client is built with only `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` (correctly — the anon key, not the service-role key, is used client-side) and instantiated inside a `'use client'` component. There is **no `middleware.ts`, no login route, no session/user check anywhere in the repo**, and no schema/migration/RLS-policy files checked in to verify how `ai_audit_events` / `ai_flagged_incidents` are locked down server-side. Those tables (per the typed schema in `supabase.ts:25-59`) contain `user_prompt`, `response`, `pii_detected`, `jailbreak_confidence`, etc. — exactly the sensitive data an AI-compliance dashboard exists to protect.

**Concrete failure scenario:** `NEXT_PUBLIC_*` values are, by design, embedded in the shipped JS bundle and visible to anyone who opens devtools. If Supabase Row Level Security on these two tables is ever left at a permissive default (a very common misconfiguration, and nothing in this repo enforces or even documents the expected policy), any visitor to the deployed dashboard — or anyone who simply extracts the anon key from the bundle — can query the full audit log, including raw prompts/responses and PII flags, directly via the Supabase REST/JS client, with zero additional gate. This is inherent to the anon-key + RLS pattern, but the repo currently gives a reviewer nothing to check that RLS is actually configured correctly, and provides no defense-in-depth (e.g., a server route / API layer) in front of it.

**Suggested fix:** Add the RLS policy SQL to the repo (even if applied via Supabase migrations) so it's reviewable, and/or move audit-data reads behind a Next.js Route Handler that checks an authenticated session before querying Supabase with a server-side key, rather than querying Supabase directly from client code.

#### H-2. AVL-3 test's pass/fail exit code doesn't actually enforce one of its five documented PASS criteria
**File:** `tests/avl3_signed_proofs/run_avl3_test.py:127-136`; spec cross-reference `README.md:159-165`

`README.md`'s AVL-3 PASS Criteria list five bullets, including "Signing key loaded from environment, not hardcoded." The test correctly *detects and prints* whether the key came from `ZOE_SIGNING_KEY` (`key_source == 'env'` vs. `'ephemeral-test-only'`), but:

```python
all_pass = (
    has_all_fields and verified and not tampered_verified
    and roundtrip_ms < 100
)
```

`key_source` is never included in `all_pass`. When `ZOE_SIGNING_KEY` isn't set (the likely state for this public repo unless the maintainer configured a GitHub Actions secret), the script prints a `NOTE:` line but still returns exit code 0 → **CI shows a green check / "OVERALL: PASS"** for a run that used a throwaway ephemeral key and did not satisfy a criterion the spec itself calls a pass/fail gate.

**Concrete failure scenario:** A reviewer or prospective customer sees the AVL-3 workflow passing in GitHub Actions and reasonably infers all five AVL-3 PASS criteria hold. In fact one may be silently unmet every single run. For a repo whose entire value proposition is "proof, not paperwork" (see `ARTICLE12_HOMEPAGE_COPY.md`) and self-verification claims (`TRUST.md`'s "Dogfood Result"), a CI check that can overstate compliance is a credibility risk, not just a code nit.

**Suggested fix:** Fold `key_source == 'env'` into `all_pass` (or fail loudly/exit non-zero when `ZOE_SIGNING_KEY` is absent in CI specifically, while still allowing the ephemeral fallback for local dev), so the badge only turns green when the actual spec criterion is met.

#### H-3. (Architectural) The repo's compliance/"dogfood" claims are not reproducible from anything checked into the repo
**Files:** `proof-packets/zoe-axtlabs-dogfood-001.json`, `TRUST.md:60-76`, `CITATIONS.md:43-53`

`TRUST.md` and `CITATIONS.md` present a specific, numerically precise "self-verification" result (DCS 0.9767, Merkle root, commitment-chain head, 847ms duration, etc.) as AXT Labs having "run ZOE on its own infrastructure" against this very repository. Nothing in this repository — no script, no `zoe-verifier` code, no CLI — actually computes a DCS score, Merkle root, or commitment chain *over the avl-spec repo itself*. The `commit_sha` field inside the proof packet does correctly resolve to a real commit in this repo's history (`2e4a87f`, verified directly), which is a nice touch, but the DCS/merkle/timing numbers are hand-authored JSON, not generator output present anywhere in this checkout.

**Concrete failure scenario:** Anyone asked to independently reproduce the "Dogfood Result" table in `TRUST.md` (as the document itself invites — "View full proof packet →") has no way to do so from this repo alone; the actual scoring/anchoring engine (`zoe-verifier`) lives in a separate, mostly-unimplemented repo per the Implementation Status table (`README.md:251-258`). This isn't a coding bug, but it is the kind of gap that, if surfaced by an outside auditor rather than caught in an internal review, undermines the exact "not a claimed certification, methodology transparency" posture the sandboxing spec itself calls for (`SANDBOXING.md:113`, "credibility rests on methodology transparency rather than a claimed certification").

**Suggested fix:** Either check in the generator that produced this specific packet (so it's re-run-able against this commit) or soften the claim/labeling until it is (e.g., "illustrative packet" vs. "Dogfood Result... AXT Labs runs ZOE on its own infrastructure").

---

### Medium

#### M-1. `reorder_pair` adversarial mutation can silently no-op, undermining the claimed 100% detection rate
**File:** `tests/tamper_evident_logging/run_tamper_test_v2.py:122-125`

```python
elif kind == "reorder_pair":
    j = min(idx + 1, len(tampered) - 1)
    tampered[idx], tampered[j] = tampered[j], tampered[idx]
```

When the randomly chosen `idx` equals the last index (`len(tampered) - 1`), `j = min(idx+1, len-1) == idx`, so the "swap" exchanges an element with itself — a genuine no-op. The module docstring explicitly claims: *"All mutation branches are guaranteed to change state -- no-op collisions are excluded by construction... This ensures 200/200 adversarial detection deterministically across all OS platforms."* That guarantee is false for this branch. Notably, commit `2e4a87f` ("fix: eliminate no-op collisions in mutate_risk_level and mutate_decision_class") fixed exactly this class of bug for two *other* mutation kinds but missed `reorder_pair`. Reproduced directly:

```
idx 49 j 49 same index (no-op)? True
Chain unchanged (bug confirmed) -> True
```

**Concrete failure scenario:** With `n=500` fixtures and 10 equally-likely mutation kinds, this triggers with probability ≈ 1/(10·500) ≈ 0.02% per adversarial round. Across 200 rounds × 3 OSes in `avl-full-matrix.yml`, it's individually rare but not zero, and will manifest as an unexplained, non-reproducible ("flaky") CI failure — a round logged in `missed_log` as "MISSED (collision or no-op mutation)" — that has nothing to do with a real detection gap in the Merkle chain, but will look like one to whoever triages it.

**Suggested fix:** Guard the branch the same way the two already-fixed kinds are guarded, e.g. pick `idx` from `range(len(tampered) - 1)` for this kind, or pick two distinct random indices instead of adjacent-only.

#### M-2. Hardcoded "representative" Merkle root in the AVL-3 test is the wrong length (63 hex chars, not 64)
**File:** `tests/avl3_signed_proofs/run_avl3_test.py:78`

```python
merkle_root = "4e593bb9309cc3ecf5439e38fe9bb306a785d9c42fb8da5d2146e61f4bc5313"
```

This is 63 hex characters. AVL-1's own PASS criteria (`README.md:65`) require "Merkle root is a valid 64-character hex string." Compare to `tests/tamper_evident_logging/RESULTS.md:22`, which records the real, correctly-64-char root for the same scoring run: `...f4bc53313` (one extra trailing `3`). This looks like a transcription/copy-paste error when the value was carried from `RESULTS.md` into this test file.

**Concrete failure scenario:** The script itself doesn't validate the length, so it runs fine — the string is only used as opaque signable bytes. The risk is someone copying this "representative" packet as a template for a real `ProofPacket` and propagating a malformed, non-64-char root into something that *does* get length-checked downstream (the spec explicitly makes 64-char-hex a pass/fail gate elsewhere).

**Suggested fix:** Fix the typo to match `RESULTS.md`, and consider adding an assertion (`assert len(merkle_root) == 64`) to this test so a future regression like this fails loudly.

#### M-3. No canonical serialization defined for the AVL-3 signed message, creating a cross-implementation verification risk
**File:** `tests/avl3_signed_proofs/run_avl3_test.py:54-61`; spec cross-reference `README.md:151`

```python
def sign_packet(priv_key, merkle_root: str, dcs_score: float, ts: str) -> bytes:
    message = f"{merkle_root}||{dcs_score}||{ts}".encode("utf-8")
```

`dcs_score` is a Python `float`, embedded via default `str()`/f-string formatting. Neither the spec (`README.md`'s "signature — Ed25519 signature over `merkle_root || dcs_score || timestamp`") nor the code pins down a canonical decimal representation (fixed precision, trailing zeros, locale, etc.).

**Concrete failure scenario:** Two conformant implementations that agree on the *value* `dcs_score = 0.90` can disagree on its *string form* (`"0.9"` vs `"0.90"` vs `"0.900000"`), producing different signed byte strings and therefore signatures that fail to verify against each other's output — despite both being spec-compliant per the current wording. This is exactly the kind of gap AVL-3's "verifiable offline using only public_key and ProofPacket fields" promise (`README.md:155`) depends on not existing.

**Suggested fix:** Pin the serialization in the spec (e.g., "`dcs_score` formatted to exactly 4 decimal places" or "sign over the canonical JSON encoding of the full ProofPacket minus the signature field") and update the reference implementation to match.

#### M-4. AVL-2 SHIP GATE test hardcodes two of its four gate conditions rather than computing them
**File:** `tests/avl2_lattice_scoring/run_avl2_test.py:126-127`

```python
chain_intact = True  # AVL-1 chain assumed intact for this scoring pass
rho_tampered = 0.0   # no tamper applied in this scoring-only run
```

This is disclosed in the module docstring as a stated limitation ("validates the SCORING MATH only, not a production DCS pipeline"), so it isn't a hidden bug — but it means the `[SHIP GATE]` block, which prints all four named conditions `(i)-(iv)` as if independently evaluated, always reports `rho_tampered < 0.05: True` and `Chain intact: True` regardless of any actual AVL-1 chain state, because those two are constants, not measurements.

**Concrete failure scenario:** Read in isolation (e.g., pasted into a report or CI summary without the docstring context), the printed SHIP GATE block reads as a real 4-condition pass, potentially overstating what was actually verified in that run.

**Suggested fix:** Either wire this runner to actually consume the AVL-1 chain-intact/tamper-rate output from `run_tamper_test_v2.py` (both already operate on the same `fixtures_v2.json`), or clearly label the two constants in the printed output itself (not just the docstring), e.g. `f"Chain intact (ASSUMED, not measured): {chain_intact}"`.

#### M-5. `axt-compliance-monitor` is missing `postcss.config.js`, so Tailwind likely never compiles
**Files:** `axt-compliance-monitor/package.json:27-29` (declares `postcss`, `autoprefixer`, `tailwindcss` as devDependencies), `axt-compliance-monitor/src/app/globals.css:1-3` (`@tailwind base/components/utilities`), `axt-compliance-monitor/tailwind.config.ts`

There is a `tailwind.config.ts` but no `postcss.config.js` anywhere in `axt-compliance-monitor/`. Outside the `create-next-app --tailwind` scaffold (which generates this file automatically), Next.js needs an explicit PostCSS config registering the `tailwindcss`/`autoprefixer` plugins for the `@tailwind` directives to be processed at all.

**Concrete failure scenario:** Once C-1 is fixed and the app actually builds, the dashboard would very likely render with all of its Tailwind utility classes (`bg-[#0a0a0f]`, `text-red-400`, the whole `axt.*` custom palette, etc.) inert — an unstyled page — because nothing tells Next's build pipeline to run Tailwind's PostCSS transform.

**Suggested fix:** Add the standard `postcss.config.js`:
```js
module.exports = { plugins: { tailwindcss: {}, autoprefixer: {} } }
```

---

### Low

#### L-1. README/TRUST.md reference files that don't exist in the repository
**Files:** `README.md:6,283-287` (License badge + "See [LICENSE](LICENSE)"; "Versioning... tracked in [CHANGELOG.md](CHANGELOG.md)"), `TRUST.md:81` ("see SECURITY.md")

None of `LICENSE`, `CHANGELOG.md`, or `SECURITY.md` exist in the repo. `README.md` asserts "Copyright 2026 AXT Labs LLC / Licensed under the Apache License, Version 2.0" and links a badge to a `LICENSE` file that isn't there. For a repo positioning itself as a compliance/legal reference artifact, an explicit license claim with no actual license file is a real (if trivially fixable) documentation gap — and the broken relative links degrade trust in a repo whose whole pitch is trustworthiness.

**Suggested fix:** Add the actual `LICENSE` file (Apache-2.0 text), or remove/soften the claims and links until it's added.

#### L-2. GitHub Actions steps pin third-party actions by mutable tag, not commit SHA
**Files:** `.github/workflows/avl-full-matrix.yml` (`actions/checkout@v4`, `actions/setup-python@v5`, `actions/upload-artifact@v4`), `.github/workflows/tamper-evident-logging.yml` (same)

These are official GitHub-maintained actions, so risk is low, but pinning to a mutable tag rather than a commit SHA is a standard supply-chain hardening gap worth calling out given the repo's own `SANDBOXING.md` spec (Section 3, 5.3) explicitly cares about build/provenance integrity (SLSA-3) elsewhere.

**Suggested fix:** Pin to commit SHAs (`actions/checkout@<sha> # v4.x.x`) if/when this repo's CI posture is tightened toward the SLSA-3 goal already stated in the spec.

#### L-3. Overlapping CI triggers between the two workflows
**Files:** `.github/workflows/avl-full-matrix.yml:4-11`, `.github/workflows/tamper-evident-logging.yml:3-11`

Both workflows trigger on `push`/`pull_request` touching files under `tests/tamper_evident_logging/**` (the older workflow's own path filter, and the newer matrix workflow's broader `tests/**` filter). A change to `run_tamper_test.py` or `fixtures.json` fires both, running the older `run_tamper_test.py` a second time redundantly alongside the newer v2 pipeline. Not a correctness issue, just wasted CI minutes and a confusing pair of check runs on every PR.

**Suggested fix:** Either fold `tamper-evident-logging.yml`'s job into the matrix workflow, or narrow one workflow's path filter so they're mutually exclusive.

#### L-4. Dead/unused imports and state in the incomplete dashboard component
**File:** `axt-compliance-monitor/src/app/page.tsx:1-7, 76-84`

All of `AlertTriangle, CheckCircle, Shield, Activity, Eye, Download, RefreshCw, ChevronRight, X, Zap` (lucide-react), `BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell` (recharts), and `format, subDays` (date-fns) are imported but never referenced in the file as committed; `selectedEvent`, `filterSeverity`, `search`, and `useSeed` state is declared but never read or set beyond `useState`. This is a direct symptom of C-1 (the file is unfinished) rather than an independent bug, but worth tracking as its own cleanup item once the component is completed, since a partial-but-compiling version of this file would still trip `next lint`/`tsc --noUnusedLocals` on every one of these.

#### L-5. `SUPABASE_SERVICE_ROLE_KEY` is declared in `.env.example` but never referenced anywhere in the code
**Files:** `axt-compliance-monitor/.env.example:4`, whole `axt-compliance-monitor/src` tree (grepped, zero hits)

Not a leak (it's a placeholder value, `your-service-role-key`), and arguably safer than the alternative (a service-role key actually wired into client code would be Critical). But its presence with no corresponding server-side usage anywhere in the repo suggests either a planned-but-missing server route (the natural fix for H-1) or leftover scaffolding from a template. Worth resolving one way or the other so a future contributor doesn't assume server-side privileged access already exists.

---

## 3. Areas checked and found clean (no comments needed)

- **`tests/tamper_evident_logging/generate_fixtures.py`** — deterministic, seeded, uses real `hashlib.sha3_256` over well-formed JSON payloads exactly as documented; no issues found.
- **`tests/tamper_evident_logging/run_tamper_test.py` (v1, scripted T1–T10 scenarios)** — traced each of the 10 mutation branches by hand; all genuinely alter the serialized event set (the `reorder_pair`-style scenario here, T5, swaps fixed indices 10/11, which are never the last index in the 50-record fixture set, so it does not share M-1's bug).
- **`tests/avl4_anchoring/run_avl4_test.py`** — hash-chain construction/verification and the deliberate single-entry tamper-and-detect flow were traced end-to-end and are logically sound; the documented "partial AVL-4 result" framing (no live Arweave call, no `.rego` files yet) accurately matches what the code actually does.
- **Secrets hygiene** — no API keys, credentials, or tokens are committed anywhere in the repository (including git history for `.env.example`); `ZOE_SIGNING_KEY` and `ARWEAVE_KEY` are correctly sourced from environment variables / GitHub Actions secrets in every code path, never hardcoded, consistent with the spec's own requirement (`README.md:157`).
- **No injection or unsafe-deserialization sinks** — repo-wide search for `dangerouslySetInnerHTML`, `eval`, `innerHTML`, `subprocess`/`os.system`, `pickle.load`, `yaml.load` (unsafe form) turned up zero matches.
- **`src/lib/supabase.ts`** — correctly uses the public anon key (not the service-role key) for the client-side Supabase client; the one issue found (H-1/L-5) is about what's *missing* around it (auth, RLS visibility), not misuse of this file itself.
- **GitHub Actions workflow YAML** — no interpolation of untrusted `github.event.*` fields into `run:` shell steps in either workflow, so no obvious Actions script-injection vector.
- **Markdown formula consistency** — the SHA3-256 Merkle/commitment-chain formulas as stated in `README.md` (`f`, `M_l`, `C_l`, `C_0`) match, term for term, what `run_tamper_test.py`/`run_tamper_test_v2.py`/`run_avl4_test.py` actually implement.

---

*Report generated as a full-repository review of the current tree, not a diff against a prior state.*
