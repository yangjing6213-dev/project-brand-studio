# BrandLoom release-blocker remediation

## Original Goal
Close the final BrandLoom Critical and Important release blockers under the user-approved "方案 2", then evaluate and, only after explicit rights authorization, integrate four newly supplied exact brand assets.

## Task Contract
- Requirements: fix affirmative confirmation semantics and state ordering; make production manifest validation fail closed; bind cover generation to the exact user-accepted logo hash; require an explicit no-project-mark choice when no mark resolves; sort manifest versions numerically; isolate the collision regression test; verify the complete package and two workspace flows.
- Authority: `docs/superpowers/specs/2026-08-31-brandloom-design.md`, the existing BrandLoom implementation plan, the final scoped-review findings recorded in `docs/exec-plans/active/brandloom-implementation.md`, and the user-approved方案 2.
- Constraints: Python >=3.12; only runtime dependency `Pillow==12.3.0`; JSON runtime state; deterministic Pillow text/logo composition; no company-logo redraw or geometry change; no Push, merge, release, deployment, paid/external image call, secret access, or tracked staging/runtime outputs.
- Asset constraint: the new four exact files may be inspected read-only, but their earlier three-file authorization and provenance do not transfer. No file may enter `brandloom/assets/defaults/` or the public ZIP until the user explicitly authorizes these four exact hashes for `public_skill_package` distribution.
- Acceptance Criteria: each code task has observed RED then GREEN evidence, focused and full unittest, diff/status checks, a commit, and an independent task review; final verification includes full unittest, compileall, deterministic double build, ZIP audit, negative exploit reproduction, two offline workspaces, and an independent whole-branch review.
- Deliverables: strict confirmation schema and transition enforcement; strict manifest/logo/mark/version behavior; tests and docs; optionally updated authorized default assets/provenance; deterministic `dist/brandloom.zip`.
- Non-goals: new image provider, AI redraw, custom-dimension/variant CLI expansion, public publishing, or migration that silently blesses legacy ambiguous confirmations.
- Risks: public state JSON compatibility; existing tests that intentionally use incomplete manifests; inconsistent 2D front and 3D five-view IP appearance; new-file licensing scope; white logo visibility on light compositions.
- Testing Strategy: minimum behavioral TDD per bounded task; real temporary workspaces; mutation/tamper cases; full 106+ unittest discovery; package hash and exclusion checks; read-only reviewers.

## Global Constraints
- `GENERATION_READY` is the only generation gate; negative, ambiguous, missing, unknown, out-of-order, or invalidated confirmations must fail closed.
- Confirmation is an explicit affirmative event, not truthiness. Fields whose selected content already lives in `BrandBrief` require the exact boolean `true`; raw strings do not count as acceptance. The state-routing `ip_cast` and custom-IP `rights` fields use their existing documented canonical IDs.
- Confirmation keys are accepted only in their corresponding pending QA state. Leaving a pending state requires that state's valid confirmation.
- Existing ambiguous legacy sessions are not silently migrated to ready; users must reconfirm through the strict path.
- Generated-output validation always requires the complete production manifest. Compatibility fixtures must be upgraded, not exempted.
- Cover composition must compare the current logo bytes to the hash recorded when the logo was reviewed and delivered.
- A project mark may be absent only when the brief explicitly records the confirmed absence; an unresolved requested/default mark hard-stops.
- Every new output and manifest remains non-overwriting and numerically versioned.
- No incoming asset is copied, transformed, or packaged without exact-file public distribution authorization and truthful provenance.

## Current Repository State
- Worktree: linked isolated worktree `F:/Projects/project-brand-studio/.worktrees/brandloom-implementation`, branch `brandloom-implementation`; main remains at `dacbeeef2b869691443618fb5e486ac76104eb02`.
- Starting HEAD: `53d3fa1f24fc20df6ea5396692608599085ee0a7`; tracked status clean.
- Runtime: Python 3.12.13 and Pillow 12.3.0.
- Baseline: full discovery 106/106 passed before this remediation.
- Incoming ignored files exist under `staging/brand-assets/incoming/`; hashes and visual inspection are recorded in the plan ledger. Public-package authorization is pending.

## Preflight Rulings
- R1: use exact boolean `true` for confirmation-only keys instead of a negative-string denylist or a new envelope API. The selected/custom content remains in `BrandBrief`, while the QA session records only the affirmative event. Cost if wrong: legacy sessions that stored descriptive strings must reconfirm, but no ambiguous string is silently trusted.
- R2: retain canonical values only where the state machine actually branches: `ip_cast` accepts the three built-in profile IDs or `custom`; custom-IP `rights` accepts documented `RightsStatus` values and only `user_authorized` is generation-ready. `ip_combination` and all other selected content stay in `BrandBrief` and receive a boolean confirmation. Cost if wrong: an undocumented routing alias may be rejected until normalized.
- R3: public validation has no fail-open legacy mode. Test fixtures are upgraded to production-complete manifests. Cost if wrong: callers relying on incomplete internal fixtures must update rather than validate old records.
- R4: record accepted-logo evidence in the persisted QA session and clear it on upstream invalidation. Cost if wrong: the session schema grows, but cover integrity cannot otherwise survive file replacement.
- R5: code remediation proceeds while new-asset authorization is pending; Task 3 stops before any public copy. Cost if wrong: no asset is published, and the code fixes remain independently useful.
- R6: keep the established output rule that RGB/RGBA PNGs without an embedded ICC profile are treated as sRGB-compatible. The residual review did not identify missing ICC metadata as a blocker, and all four incoming files lack ICC metadata; requiring embedded ICC now would be an unrelated breaking change. Explicitly incompatible profiles still fail.

## Task Plan
| ID | Objective | Files likely affected | Acceptance criteria | Verification | Dependencies | Status |
|---|---|---|---|---|---|---|
| T1 | Enforce affirmative, state-bound QA confirmations | `state_machine.py`, `models.py`, CLI, state/pipeline tests, workflow docs | `"no"` and raw strings fail; unknown/out-of-order keys fail; legal confirmed flow reaches ready; invalidation still works | focused state/pipeline RED→GREEN, full unittest, diff/status, review | none | pending |
| T2 | Close manifest, accepted-logo, project-mark, and version gaps | validation/manifests/prompt/CLI/models, localization/pipeline tests | incomplete manifests fail; tampered accepted logo blocks cover; unresolved requested mark blocks; v100 wins; collision test isolated | focused localization/pipeline RED→GREEN, full unittest, diff/status, review | T1 | pending |
| T3 | Integrate the four new exact assets with truthful provenance | default asset profiles, prompt references, package/profile tests, NOTICE | only after explicit authorization; all four exact hashes represented without redraw/overwrite; appearance vs geometry roles explicit; package builder accepts truthful provenance | image/hash/provenance tests, visual inspection, full unittest, package audit, review | T2 + explicit new-file authorization | blocked |
| T4 | Re-run acceptance, package, and final review | tests, ignored workspaces, active plan/ledger, dist | negative exploit fails, two workspaces satisfy code-level flows, package deterministic, final reviewer finds no Critical/Important | full verification, double build, ZIP audit, manual views, final review | T1–T3 | pending |

### Task 1: Enforce affirmative, state-bound QA confirmations

- Write focused failing tests before production changes for: raw negative/descriptive strings; unknown keys; a valid key submitted in the wrong pending state; advancing out of a pending state without its matching valid confirmation; malformed built-in/custom routing values; legacy ambiguous ready sessions; and a complete legal built-in/custom flow.
- Confirmation-only keys accept only the exact JSON boolean `true`. `ip_cast` accepts only `author-anime`, `tuotuo`, `xingbi`, or `custom`; `rights` accepts documented `RightsStatus` values, while only `user_authorized` reaches generation-ready.
- Map every pending state to its single expected confirmation key. `advance()` must enforce that mapping before leaving the state, except transitions to `CANCELLED`.
- Revalidate the complete persisted confirmation set in `assert_generation_ready()`; never trust truthiness or state alone.
- Keep downstream invalidation behavior and the custom-IP branch intact. Upgrade CLI/workflow documentation and fixtures without silently converting legacy raw values.
- Run focused state/pipeline tests, the full suite, `git diff --check`, and `git status --short`; commit; then undergo independent specification/code/test/scope review.

### Task 2: Close manifest, accepted-logo, project-mark, and version gaps

- Write focused failing tests before production changes for: a manifest missing each required production section; a logo file changed after explicit logo acceptance; a requested/default project mark that cannot resolve; manifest versions `v99` and `v100`; and an isolated output-collision case.
- Remove the incomplete-manifest compatibility path from public validation and upgrade fixtures to full production manifests.
- Persist the exact accepted logo output path/hash evidence at logo delivery, clear it when relevant upstream state is invalidated, and require a match before cover composition.
- Treat project-mark omission as valid only for an explicit confirmed none/false/empty selection; malformed or unresolved requested/default values hard-stop.
- Sort generation manifests by parsed numeric version and isolate the collision regression test.
- Preserve the established RGB/RGBA-without-ICC sRGB-compatible rule from R6.
- Run focused localization/pipeline tests, the full suite, `git diff --check`, and `git status --short`; commit; then undergo independent review.

### Task 3: Integrate the four newly supplied exact assets

- This task is blocked until the user explicitly authorizes the four recorded exact hashes for public Skill distribution. Mere placement in ignored staging is not authorization.
- After authorization, write failing hash/layout/provenance/package tests first. Define primary appearance versus supplemental geometry references so the shared 2D pair image and two 3D five-view sheets are not treated as interchangeable visual truth.
- Copy exact authorized bytes only; do not redraw, crop, recolor, overwrite, or invent provenance. Record truthful filename, SHA-256, confirmation source/time, scope, and reference roles.
- Assess the white ENHE transparency edge artifact without modifying logo geometry. If exact bytes are unsuitable, stop this asset replacement rather than silently cleaning or substituting it.
- Run focused asset/profile/package tests, full tests, ZIP audit, visual inspection, diff/status checks; commit; then undergo independent review.

### Task 4: Re-run acceptance, package, and final review

- Reproduce and verify rejection of the original all-`"no"` exploit.
- Run complete unittest and compile checks; build the ZIP twice and compare hashes; inspect ZIP contents/exclusions and provenance.
- Execute the two specified offline workspace acceptance flows. If the host image tool is absent, mark visual generation acceptance `PARTIAL` without inventing a pass.
- Use the strongest available independent reviewer for a whole-branch review. Perform at most one concentrated fix round and one scope re-review, then rule on every residual finding.
- Apply verification-before-completion, update plan/ledger with exact evidence and SHAs, and use finishing-a-development-branch to present merge/keep options without merging, pushing, releasing, or publishing.

## Completed + Verified
- Baseline only: 106/106 tests passed; worktree and runtime verified.

## Current Work
- Preflight reconciliation and Task 1 dispatch preparation.

## Remaining Work
- Tasks 1–4 above.

## Failures
- Prior branch verdict is `FAIL`: one Critical and three Important release blockers remain at starting HEAD.

## Evidence
- `python -m unittest discover -s tests -p "test_*.py" -v` -> 106/106 PASS at starting HEAD.
- Incoming hashes: pair front `0754c7c51b225e57949bd77cb80eb32195ffc6d81151fe495d9ed1fde1ebbc21`; Xingbi five views `6c6fbc39b45ec8b7fd7dc6883dbb13464772fad5c5c57659ac7158de235850d9`; Tuotuo five views `cace50cd0e54c6180ceda2cb2797dc2fd61746fefc09a9bf64b19e008f017e46`; white ENHE logo `9e6b890cc043029fcf629684cf38c944376c879737c559772854cbe807dd972a`.

## Important Decisions
- Do not infer public rights from file placement.
- Keep code remediation and asset replacement as separate review surfaces.
- Prefer failing closed over legacy compatibility for release validation.

## Open Risks
- Explicit public authorization for the four new exact hashes is absent.
- The IP pair front is a 2D transparent illustration while both five-view sheets are 3D turnarounds; reference priority must prevent contradictory appearance guidance.
- The new white ENHE file has no ICC profile and appears to contain edge/noise artifacts on transparency; it must be assessed before replacing the current clean reference.

## Final Acceptance
- Status: PARTIAL
- Requirements verified: isolated worktree, runtime, clean baseline, incoming-file existence/hash/decode.
- Not verified: remediation implementation, new asset authorization/import, package, final review.
- Remaining risks: listed above.
