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
| T1 | Scaffold minimal installable skill and CI | brandloom/SKILL.md, agents, architecture, tests, requirements, ignore, workflows | Contract tests and pinned dependency pass | focused + full unittest, diff/status | none | pending |
| T2 | Define runtime enums/dataclasses and JSON IO | core models/json_io, tests | Session round-trip and atomic JSON behavior | focused + full unittest, diff | T1 | pending |
| T3 | Enforce QA transitions/invalidation/gate | state_machine, tests | Explicit transitions and generation gate | focused + full unittest, diff | T2 | pending |
| T4 | Add complete QA references and routing | SKILL.md, references, contract tests | All states/options/rules and routes present | focused + full unittest, diff | T1,T3 | pending |
| T5 | Implement rights-aware local asset library | paths, asset_library, tests | Hash dedupe, defaults, versioning, rights checks | focused + full unittest, diff | T2 | pending |
| T6 | Add authorized built-in logo/IP profiles | defaults, IP refs, tests | Three profiles, seven combinations, provenance and image checks | focused + full unittest + manual image check | T5 + explicit user A | blocked at gate |
| T7 | Resolve fonts with strict fallback | font presets, fonts.py, tests | Alias resolution and no silent fallback | focused + full unittest, diff | T2,T4 | pending |
| T8 | Render deterministic templates with Pillow | templates, layout, renderer, tests | Dimensions, text fit, aspect integrity, versioning | focused + full unittest, diff | T2,T5,T7 | pending |
| T9 | Build generation prompts and backend boundary | prompt_builder, backend ref, SKILL.md, tests | Safe prompt and returned-path validation | focused + full unittest, diff | T3,T4,T6,T8 | pending |
| T10 | Implement CLI, manifests, local pipeline | manifests, CLI, tests | init/assets/state/compose/validate/deliver E2E | focused + full unittest, diff | T2,T3,T5,T8,T9 | pending |
| T11 | Add localization/editing/internal QA | validation, refs, SKILL.md, tests | Reuse hashes/base, QA failure gates, no overwrite | focused + full unittest, diff | T8,T10 | pending |
| T12 | Document, package, examples, final CI | READMEs, legal docs, examples, builder, tests, CI | Deterministic ZIP and exclusions; final acceptance | full unittest, build, ZIP inspect, manual acceptance, final review | T1–T11 | pending |

## Completed + Verified
- None yet.

## Current Work
- Preflight scan and SDD ledger are complete, including the independent consistency/interface reconciliation and R1–R12 rulings. Task 1 is in progress; next check is its TDD report, commit, and independent review.

## Remaining Work
- Tasks 1–12, Task 6 authorization gate, final review and finishing-branch menu.

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
- Task 6 cannot proceed until the user explicitly chooses A, B, or C for the exact staging files; no provenance or binary copying will occur before A.
- Host image-generation availability is not yet established; if absent, visual acceptance must be reported PARTIAL.

## Final Acceptance
- Status: PARTIAL
- Requirements verified: repository/worktree isolation and runtime baseline only.
- Not verified: all implementation tasks, package, and manual workspace runs.
- Remaining risks: listed above.
