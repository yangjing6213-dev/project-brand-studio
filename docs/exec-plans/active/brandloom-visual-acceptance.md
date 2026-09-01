# BrandLoom visual acceptance and contrast remediation

## Original Goal

Close the remaining visual-acceptance gap for BrandLoom by using an available
Codex image-generation capability for local acceptance, selecting a legible
company-logo treatment, and preventing missing CJK glyphs from reaching a
delivered artifact.

## Task Contract

- Requirements:
  - Keep the Skill runtime backend as `host_builtin_image_tool` and preserve
    the `GENERATION_READY` gate.
  - Use the supplied black-logo sheet as a local visual reference only; do not
    place the composite sheet or a guessed crop in the public package.
  - Support an explicit deterministic monochrome-black company-logo treatment
    without changing logo geometry, letterforms, proportions, or source bytes.
  - Reject confirmed fonts that cannot render the confirmed copy; use a
    locally available CJK-capable font for acceptance.
  - Generate one 1254x1254 and one 1774x887 base image with the host built-in
    image tool, preserve returned paths, and compose them through BrandLoom.
    The former 2048x2048 and 2048x1024 values are historical-only evidence.
- Constraints:
  - Python >=3.12; Pillow==12.3.0; JSON only for runtime state.
  - No API keys, fallback image API, third-party provider, recursive Codex,
    push, merge, release, deployment, or external account changes.
  - Never overwrite source assets, prior outputs, or historical versions.
  - Keep generated acceptance files outside Git tracking.
- Acceptance criteria:
  - T1 has observed RED then GREEN tests and an independent task review.
  - Black treatment is explicit, deterministic, hash-audited, and preserves
    the source alpha geometry.
  - Missing CJK glyphs fail closed with an actionable error; Microsoft YaHei
    (or another confirmed CJK font) renders the Chinese acceptance copy.
  - T2 produces and visually inspects both generated compositions, with no
    unreadable Chinese tofu and sufficient logo contrast.
  - Full unittest, compileall, package build/audit, diff/status checks, and a
    final independent review pass; any unavailable visual check remains
    explicitly `PARTIAL`.
- Deliverables:
  - Minimal renderer/font/test changes, updated relevant reference docs,
    ignored visual-acceptance evidence, deterministic `dist/brandloom.zip`,
    and this verified-state file plus SDD ledger.
- Non-goals:
  - Adding a new runtime provider or Codex CLI fallback, redesigning the ENHE
    mark, bundling fonts, or changing unrelated templates/API contracts.
- Risks:
  - A black treatment derived at render time may be mistaken for a new source
    asset; manifests must record the original source hash and treatment.
  - Host generation may fail or return an invalid path; hard-stop and report
    the exact missing evidence.
  - The attached sheet contains multiple logo variants and labels; treating it
    as a formal logo asset would introduce geometry/provenance ambiguity.

## Current Repository State

- Worktree: isolated repository worktree (`.worktrees/brandloom-implementation`)
- Branch: `brandloom-implementation`
- Starting HEAD: `e090581c1bf2c5160fe6e8e779e9b980a3a5e9df`
- Main remains at the earlier baseline and must not be modified in this task.
- Historical pre-remediation automated verification was 137/137; current
  verification counts are recorded in the concentrated-fix report.
- User supplied black-logo reference:
  `staging/brand-assets/incoming/` (exact authorized source recorded in ignored evidence).

## Task Plan

| ID | Objective | Files likely affected | Acceptance criteria | Verification | Dependencies | Status |
|---|---|---|---|---|---|---|
| T1 | Add explicit black logo treatment and CJK glyph coverage guard | `renderer.py`, `fonts.py`, tests, focused docs | RED→GREEN; source hash and geometry preserved; missing glyphs fail closed | focused tests, related/full unittest, diff/status, independent review | existing asset/renderer contracts | verified |
| T4 | Final concentrated review-fix wave | treatment mapping, state confirmation, asset policy, manifest QA, tests/docs | final-review findings covered; RED→GREEN; amended T2 evidence retained | focused/related/full tests, compileall, two package builds/audit, diff/status | T1; amended T2 evidence | verified |
| T2 | Run host image generation and two fresh compositions | ignored `.brandloom/`, ignored evidence report | exact 1254×1254 and 1774×887 dimensions, valid paths, legible logo/copy, no overwrite | image inspection, BrandLoom CLI QA/delivery, manifest audit | T1; `GENERATION_READY` | verified (visual residual recorded) |
| T3 | Finalize evidence and package | active plan, ignored SDD ledger, package output | full executable verification and package audit; no scope drift | full unittest, compileall, deterministic ZIP audit, diff/status | T1–T2 | verified |

## Completed + Verified

- T1 implementation commits: `1973f4d2c65b842ca06ae2e2d686b4e5e8a7fe32` and review-fix commit `5db6c1eb6f17327830830462b24b18dd2253ef07`. The initial independent review was `NEEDS_FIX` (missing-glyph sentinel and CLI error-type findings); both fixes are in the second commit. Fresh Task 3 full unittest evidence is 143 tests passing.
- T3 executed with bundled Python 3.12.13 and Pillow 12.3.0: current verification counts and the deterministic 60-entry package hash are recorded in the final-fix report below.
- Historical pre-final-fix ZIP audit found 59 unique entries and no entries from `.brandloom`, `staging`, `tests`, `.superpowers`, `.git`, or `__pycache__`; it also found no supplied composite sheet, cognitive-anchor/generated-image paths, or secret/private-path content. The current 60-entry audit is recorded below.
- Final concentrated fix wave: strict manifest treatment provenance, exact base/template dimensions, accepted-logo evidence binding, exact host-backend gate, explicit local custom-template validation, and refreshed QA/package evidence. Focused RED was observed before each behavioral fix; final counts are recorded in the final-fix report.
- Current concentrated-fix verification: focused 83/83 and full 158/158 tests
  passed; `compileall -q brandloom tests` and `git diff --check` passed. Two
  package builds were byte-identical (60 unique entries), SHA-256
  `a44087514447e20da7a559944d4832c9248236c826909295925af9e54063415d`; the
  exclusion audit passed. Exact commands and output paths are in the ignored
  `final-fix-report-dimension.md`.

## Current Work

- The amended host-fixed contract is active: `logo-card` 1254×1254 and `cover`
  1774×887. The concentrated fix implementation and fresh end-to-end QA are
  recorded; the single scoped final re-review remains the parent task's next
  checkpoint.

## Remaining Work

- Complete the final verification checklist and obtain the one scoped final
  re-review. Historical 2048-pixel evidence is retained read-only and is not a
  remaining generation requirement.

## Failures

- Historical pre-amendment gate evidence: the host returned 1254×1254 and
  1774×887 at ignored generated-image paths (hashes are retained in the
  ignored ledger). These dimensions now satisfy the active contract and were
  re-run through fresh compose/validate/reviewed-delivery evidence. The first
  white-treatment exploratory composition had insufficient contrast on its
  pale base; the reviewed black-treatment run is the current visual evidence.

## Evidence

- Bundled Python 3.12.13 plus Pillow 12.3.0 was used for verification.
- Historical pre-final-fix `-m unittest discover -s tests -q` -> 143 tests, OK (exit 0).
- Historical pre-final-fix `-m compileall -q brandloom tests` -> exit 0.
- Historical pre-final-fix `-m unittest tests.test_package tests.test_task3_assets -v` -> 21 tests, OK (exit 0).
- Historical pre-final-fix `scripts/build_skill_package.py` double build -> matching SHA-256 above (exit 0); current source evidence is the 60-entry double build below.
- Historical pre-amendment package hash: `3494a2b03ff4641f81b316a26cac0ccbb9ec6e505bbb50a958f9be98f29f3080` (superseded; current hash is recorded by the final-fix report).
- Current concentrated-fix report: `.superpowers/sdd/brandloom-visual-acceptance/final-fix-report-dimension.md` (ignored evidence; current package hash and exact QA paths are recorded there).
- The scoped re-review is recorded in ignored `.superpowers/sdd/brandloom-visual-acceptance/scope-rereview.md`: four final-review findings are PASS; the manifest-field fallback/operation-alias boundary is an adjudicated P2 residual, and no second fix wave is authorized.

## Important Decisions

- The Codex CLI capability probe showed that its explicit fallback script
  requires `OPENAI_API_KEY`; that path is excluded. The current host's built-in
  image tool is used directly for acceptance, with the cognitive-anchor
  directory serving only as a local output workspace.
- The supplied black sheet is not a clean single-logo asset. It is retained as
  a reference for choosing the horizontal black variant; the public Skill keeps
  the already authorized source and applies an explicit deterministic black
  treatment at composition time.
- A confirmed Arial path that maps Chinese characters to the same missing-glyph
  mask must fail closed. Acceptance will explicitly select the installed
  Microsoft YaHei collection rather than silently substituting it.

## Final Acceptance

- Status: implementation and fresh QA verified; scoped final re-review pending.
- Current acceptance requires strict manifest provenance, exact fixed dimensions,
  fresh logo-first/cover reviewed delivery, deterministic package evidence, and
  a clean scoped re-review. The current black-treatment images were inspected
  and are legible; visual identity/layout differences from the supplied host
  drafts remain an explicitly recorded cosmetic residual.
- Remaining known cosmetic risk: the deferred asset/contrast and host-scene
  identity minor is retained as an explicit follow-up; it does not authorize
  weakening the integrity gates.

## User-approved dimension amendment (2026-09-02)

The user explicitly authorized changing the default output contract to match the
host's stable returned dimensions: `logo-card` is `1254 × 1254` and `cover` is
`1774 × 887`. This amendment supersedes the prior 2048-pixel default for new
generation and composition runs; historical 2048-pixel evidence remains
read-only history and is not rewritten.

### Task 5 — migrate the default dimension contract

#### Objective

Make the host request, generated-base gate, templates, deterministic renderer,
offline QA defaults, tests, packaged references, and dated specification
amendment agree on the two user-approved dimensions.

#### Requirements

- Preserve `1:1` and `2:1` ratios and the existing JSON/Pillow-only runtime.
- Use `1254 × 1254` for `logo-card` and `1774 × 887` for `cover` everywhere a
  default is produced or validated.
- Scale template canvas, safe margins, slot coordinates, and font bounds so no
  slot is outside the new canvas and text remains deterministic.
- Keep `social-preview` at `1280 × 640` and retain a documented custom-dimension
  escape hatch; do not resize an invalid host return to manufacture acceptance.
- Update or add regression tests that accept the new defaults and reject the
  old defaults at the host-generation boundary.
- Keep old generated files and historical evidence untouched and untracked.

#### Non-goals

- No new image provider, API-key path, CLI fallback, or external call.
- No redesign of the ENHE mark, asset provenance, or unrelated visual style
  behavior in this bounded amendment.

#### Acceptance and verification

- Observe RED before implementation and GREEN after the minimum changes.
- Run focused and full unittest suites, compileall, `git diff --check`, and
  `git status --short`.
- Compose and validate the two already-generated v2 bases at their exact new
  dimensions in a fresh ignored QA workspace; preserve the logo-first gate and
  manual visual evidence.
- Rebuild `dist/brandloom.zip` twice and verify identical bytes and exclusion
  rules.
- Obtain an independent task review and a final whole-branch review before
  claiming completion.

## Post-amendment checkpoint (2026-09-02)

- Task 5 implementation is verified in commits `a3ec8f9` and `bfaf744`; its
  independent review and fix re-review are clean.
- The new host-fixed dimensions were exercised end-to-end in a fresh ignored
  workspace using the immutable v2 drafts. Both outputs passed automated QA and
  reviewed delivery; the final QA state is `DELIVERED`.
- The first white-treatment exploratory output was not selected because its
  contrast was insufficient on the pale base. A fresh run uses the authorized
  `enhe` source with the explicitly confirmed `monochrome-black` treatment and
  black deterministic copy, with no logo-card IP; both outputs are legible at
  the active dimensions.
- Remaining work is the single scoped final branch re-review. The complete
  unittest/compile/package audit is recorded in the concentrated-fix report;
  keep the plan active until that review and its evidence are recorded.

### Final concentrated-fix checkpoint (2026-09-02)

- Tracked implementation/docs/tests commit: `ac6035a82f12415c2b75295a66ed2b66cda31440`
  (`fix: close BrandLoom dimension and evidence findings`).
- Fresh QA was initialized with `brandloom_cli init` in the ignored workspace
  `.brandloom/task2-accept-20260902-run-fresh-black/`; the current brief was
  written before the state-confirm sequence. The state reached
  `GENERATION_READY`, then completed logo-first reviewed delivery and ended at
  `DELIVERED`. The persisted slug was synchronized to the current brief before
  generation; no prior `qa-state.json` was copied.
- The original host-return paths were consumed verbatim (no copy); their
  exact path strings and hashes are retained only in the ignored evidence
  report to avoid putting machine-local paths in tracked docs.
- The reviewed run explicitly selected the authorized `enhe` source and
  confirmed `monochrome-black`; logo-card IP selection is empty and cover IP
  selection is `author-anime`/`tuotuo`/`xingbi`. Output hashes and manifest
  hashes are recorded in `final-fix-report-dimension.md`.
- `view_image` inspection confirms both exact dimensions and legible black
  logo/copy. The host scene still has a cosmetic identity/layout difference
  from the supplied IP references; this is retained as a residual rather than
  represented as a full visual-fidelity pass.
