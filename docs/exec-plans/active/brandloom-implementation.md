# BrandLoom implementation

## Original Goal
Build the installable `brandloom` Codex Skill in repository `project-brand-studio`, callable as `Use $brandloom`, with a confirmation-first QA workflow, rights-aware asset library, deterministic Pillow composition, local pipeline, and distributable ZIP.

## Task Contract
- Requirements: Implement Tasks 1–12 in `docs/superpowers/plans/2026-08-31-brandloom-implementation.md` against the authority of `docs/superpowers/specs/2026-08-31-brandloom-design.md`.
- Constraints: Python >=3.12; runtime dependency only `Pillow==12.3.0`; JSON runtime data; deterministic company-logo and text composition; no secrets, external publishing, push, deployment, or unauthorized assets; `GENERATION_READY` gates image-tool calls.
- Acceptance Criteria: Each task has TDD red/green evidence, target and related suites, diff/status checks, a commit, and an independent spec/quality review; final suite/build/package checks and manual workspace acceptance are evidenced.
- Deliverables: `brandloom/` skill, runtime modules, references/templates/assets only when authorized, tests, docs, CI, and `dist/brandloom.zip`.
- Non-goals: External image/API calls, publishing, GitHub release, Figma/cloud sync, bundled fonts, third-party reference poster distribution, or automatic data deletion.
- Risks: Missing Python launcher (bundled runtime is available); Task 6 requires explicit public-distribution authorization for three exact source files; host may lack an image-generation tool, making visual acceptance partial.
- Testing Strategy: Strict per-task TDD with focused unittest, related full discovery, `git diff --check`, status review, package contract tests, and final independent review.

## Current Repository State
- Governing instructions: No `AGENTS.md` found in the repository or checked ancestors; user-provided execution instructions are binding.
- Relevant architecture/patterns: Planning/spec documents copied from the migration package into `docs/superpowers/`; no prior implementation.
- Initial Git state: Repository initialized on `main`; planning baseline commit `dacbeee`; implementation runs in linked worktree branch `brandloom-implementation`.
- Runtime: Bundled `C:/Users/amene/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe` reports Python 3.12.13 and Pillow 12.3.0.
- Baseline check: `python -m unittest -v` ran 0 tests; discovery against absent `tests/` was not applicable and reported an importable-start-directory error.

## Task Plan
| ID | Objective | Files likely affected | Acceptance criteria | Verification | Dependencies | Status |
|---|---|---|---|---|---|---|
| T1 | Scaffold minimal installable skill and CI | brandloom/SKILL.md, agents, architecture, tests, requirements, ignore, workflows | Contract tests and pinned dependency pass | focused + full unittest, diff/status | none | verified |
| T2 | Define runtime enums/dataclasses and JSON IO | core models/json_io, tests | Session round-trip and atomic JSON behavior | focused + full unittest, diff | T1 | verified |
| T3 | Enforce QA transitions/invalidation/gate | state_machine, tests | Explicit transitions and generation gate | focused + full unittest, diff | T2 | verified |
| T4 | Add complete QA references and routing | SKILL.md, references, contract tests | All states/options/rules and routes present | focused + full unittest, diff | T1,T3 | verified |
| T5 | Implement rights-aware local asset library | paths, asset_library, tests | Hash dedupe, defaults, versioning, rights checks | focused + full unittest, diff | T2 | verified |
| T6 | Add authorized built-in logo/IP profiles | defaults, IP refs, tests | Three profiles, seven combinations, provenance and image checks | focused + full unittest + manual image check | T5 + explicit user A | verified |
| T7 | Resolve fonts with strict fallback | font presets, fonts.py, tests | Alias resolution and no silent fallback | focused + full unittest, diff | T2,T4 | verified |
| T8 | Render deterministic templates with Pillow | templates, layout, renderer, tests | Dimensions, text fit, aspect integrity, versioning | focused + full unittest, diff | T2,T5,T7 | verified |
| T9 | Build generation prompts and backend boundary | prompt_builder, backend ref, SKILL.md, tests | Safe prompt and returned-path validation | focused + full unittest, diff | T3,T4,T6,T8 | verified |
| T10 | Implement CLI, manifests, local pipeline | manifests, CLI, tests | init/assets/state/compose/validate/deliver E2E | focused + full unittest, diff | T2,T3,T5,T8,T9 | verified |
| T11 | Add localization/editing/internal QA | validation, refs, SKILL.md, tests | Reuse hashes/base, QA failure gates, no overwrite | focused + full unittest, diff | T8,T10 | verified |
| T12 | Document, package, examples, final CI | READMEs, legal docs, examples, builder, tests, CI | Deterministic ZIP and exclusions; final acceptance | full unittest, build, ZIP inspect, manual acceptance, final review | T1–T11 | verified |

## Completed + Verified
- T1 scaffold: commit `a46d477`; focused and full unittest 3/3, diff check clean, independent review approved.
- T2 runtime models/JSON IO: commits `7831cdf` and `5a3c865`; fresh focused 7/7 and full 10/10, independent review plus scoped fix re-review approved.
- T3 QA state machine: commits `45027d9` and `e76c88b`; fresh focused 7/7 and full 17/17, independent review plus scoped fix re-review approved (one deferred coverage minor).
- T4 QA references/routing: commits `87f97fe`, `169d308`, `16e423e`, `569ed2f`; fresh focused 6/6 and full 20/20, two scoped fix re-reviews approved (one deferred static-test minor).
- T5 asset library: final implementation commit `2091875`; fresh focused 7/7 and full 27/27, independent review plus scoped fix re-review approved. Earlier amended commit IDs are retained only in the ignored SDD ledger.
- T6 built-in profiles: commit `372f18f`; fresh focused 4/4 and full 31/31, actual source hashes/byte copies/crop pixels verified, four-reference visual check passed, independent review approved (one deferred Minor test-coverage observation).
- T7 strict font resolution: commits `ba41efc` and `fccb2b9`; fresh focused 5/5 and full 36/36, independent review plus scoped fix re-review approved (embedded family metadata gap addressed; one deferred Minor test-coverage observation).
- T8 deterministic renderer: commit `ca7f21c`; fresh focused 6/6 and full 42/42, independent review approved (one deferred Minor test-coverage observation).
- T9 generation boundary: commits `7a623fd` and `94085af`; fresh focused 8/8 and full 50/50, independent review plus scoped fix re-review approved (canonical IP selection and strict expected dimensions addressed).
- T10 local pipeline: commits `8016b7d`, `6dbf7f3`, and `3594142`; fresh focused 6/6 and full 56/56, independent review plus two scoped fix re-reviews approved (prompt/path boundary, workspace validation, and raw returned-path preservation addressed).
- T11 localization and QA: final amended commit `b2f5cf6`; fresh focused localization+pipeline 16/16 and full 66/66, independent review plus two scoped fix re-reviews approved (canonical copy, brief boundary, Social Preview, and shared delivery QA addressed).
- T12 release package: commits `0f9077f`, `9247d99`, `b3c025c`, `05afb8d`; fresh focused 13/13 and full 79/79, deterministic ZIP SHA-256 `b775b826...f56f`, independent review plus three scoped fix re-reviews approved.
- Final concentrated review fix: commit `a7ac128fa73f99da48ab487eb01766647c237e8e`; 106/106 tests and deterministic 50-entry ZIP SHA-256 `2ba74d5ba3a5f0e3dd6d85f9b8465cb8de136361da1e5535219a0df562996903` passed. The one permitted scoped re-review still found one Critical and three Important residuals, so the branch is not merge-ready.
- Remediation Task 1: commits `3bd2873f79871e0933733425af8d6f9290650f16`, `120a552f3389359242240b2dcd44284028d27637`; strict state-bound confirmations and complete custom flow, full 114/114.
- Remediation Task 2: commits `b238de5`, `b4b9831`, `773d020`, `d69fbd9`, `a7968b9`, `a353d37`, `c4484b6` (bookkeeping `91bee68`); fail-closed manifests, accepted-logo binding, project-mark and numeric-version fixes, full 131/131 at completion and 137/137 after asset tests.
- Remediation Task 3: commit `c9cf676955330d864ca6241dd15010a110ec2000`; four explicitly authorized exact assets integrated byte-for-byte with versioned provenance and appearance/geometry roles; full 137/137 and package audit passed.
- Remediation Task 4: evidence/plan commit `993928cdff72538bdec92ad98c3e5b7b0d2e9228`; all-`"no"` exploit rejected, full 137/137, deterministic 59-entry ZIP, and two offline workspaces reached `DELIVERED`. Independent whole-branch review report `.superpowers/sdd/2026-08-31-brandloom-implementation/final-branch-review.md` found no Critical/Important implementation findings. Host image generation was intentionally not invoked, so visual acceptance remains PARTIAL.

## Current Work
- Original Tasks 1–12 and remediation Tasks 1–4 are implemented, committed, individually reviewed, and verified. The final whole-branch review and final offline acceptance evidence are recorded.
- Overall status is `PARTIAL`: all code, package, provenance, and offline acceptance checks pass; host-generated visual acceptance and composition-level visual review were not run under the no-external-call constraint.

## Remaining Work
- No code remediation remains in scope. A host-side visual run with the allowed built-in image tool and a human contrast/font review are still needed before claiming a complete visual PASS.
- Integration remains a user choice; do not merge, push, release, deploy, or publish automatically.

## Failures
- Baseline discovery cannot start because `tests/` does not exist in the planning baseline; this is expected for the empty scaffold and is retained as evidence, not treated as a product test failure.

## Evidence
- `git init -b main` -> repository initialized.
- `git commit -m "docs: establish BrandLoom planning baseline"` -> `dacbeee`.
- `git worktree add .worktrees/brandloom-implementation -b brandloom-implementation` -> linked worktree created.
- bundled Python `--version` -> `Python 3.12.13`; Pillow import -> `12.3.0`.
- `python -m unittest -v` -> 0 tests, exit 0.

## Important Decisions
- Work from the outer `F:/Projects/project-brand-studio` repository, not the nested migration package, per `CODEX_START_HERE.md`.
- Keep `.worktrees/`, `.superpowers/`, `staging/brand-assets/`, `.brandloom/`, and `dist/` ignored; no user runtime data is tracked.
- Use the bundled Python executable explicitly because the `py` launcher is absent.

## Open Risks
- Historical Critical: the original confirmation gate accepted arbitrary strings including `"no"`; closed by remediation Task 1 and the fresh all-`"no"` negative acceptance.
- Historical Important: incomplete-manifest compatibility, accepted-logo replacement, and unresolved project-mark omission; closed by remediation Task 2 with regression coverage and independent review.
- Minor: Task 6's historical Tuotuo crop retains the previously ruled cosmetic motion-line fragment; no new asset was cropped or altered during remediation.
- The four newly supplied exact assets are authorized for public distribution at `2026-09-01T16:49:10.1239046+08:00`; source/public bytes and hashes match. Attachment1–6 actual denylist inputs were never supplied, so exact production denylist coverage remains unclaimed.
- Host image generation was not invoked; deterministic Pillow composition and the structured request boundary were exercised. Available test fonts rendered CJK glyphs as tofu, so composition-level visual acceptance remains PARTIAL.

## Final Acceptance
- Status: `PARTIAL`; independent whole-branch review verdict: no Critical/Important implementation findings. The remaining PARTIAL is limited to host visual generation and composition-level visual review.
- Runtime and automated verification: Python 3.12.13, Pillow 12.3.0, 137/137 unittest cases passed with no skips; compileall and `git diff --check` passed.
- Package: two builds produced the same 59-entry ZIP SHA-256 `6ff681d53bcc43b62e35b22a908bd5b24317cd74426e7f2de695f2745d72c405`; all entries are under `brandloom/`, eight raster assets decode with authorized adjacent provenance, and staging/tests/docs/local state/Git/cache paths are excluded.
- Acceptance A: offline code-level Chinese logo-first workflow reached `DELIVERED`; exact copy, dimensions, IP selections, manifest hashes, and authorized ENHE source hash passed. Host generation was not invoked; available test font rendered CJK tofu and visual status is PARTIAL.
- Acceptance B: offline localization reached `DELIVERED`; English `v01` outputs remained unchanged, Chinese `v02` outputs reused the same base/asset hashes, all four outputs were preserved, and host generation was not invoked (visual status PARTIAL).
- Negative gate: a fresh workspace with all 13 confirmation values set to the string `"no"` was rejected by `GenerationGateError`.
- Asset authorization: the four exact user-supplied files are included only as byte-identical, versioned, provenance-backed public defaults; no redraw, crop, recolor, or overwrite was performed.
