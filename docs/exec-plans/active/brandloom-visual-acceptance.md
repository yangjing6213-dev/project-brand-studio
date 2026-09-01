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
  - Generate one 2048x2048 and one 2048x1024 base image with the host built-in
    image tool, preserve returned paths, and compose them through BrandLoom.
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

- Worktree: `F:/Projects/project-brand-studio/.worktrees/brandloom-implementation`
- Branch: `brandloom-implementation`
- Starting HEAD: `e090581c1bf2c5160fe6e8e779e9b980a3a5e9df`
- Main remains at the earlier baseline and must not be modified in this task.
- Existing BrandLoom automated verification is 137/137; visual generation was
  previously not run.
- User supplied black-logo reference:
  `C:/Users/amene/Desktop/项目视觉素材生成项目/LOGO/logo 2.0/ChatGPT Image 2026年8月22日 20_11_06 (3).png`.

## Task Plan

| ID | Objective | Files likely affected | Acceptance criteria | Verification | Dependencies | Status |
|---|---|---|---|---|---|---|
| T1 | Add explicit black logo treatment and CJK glyph coverage guard | `renderer.py`, `fonts.py`, tests, focused docs | RED→GREEN; source hash and geometry preserved; missing glyphs fail closed | focused tests, related/full unittest, diff/status, independent review | existing asset/renderer contracts | verified |
| T4 | Final concentrated review-fix wave | treatment mapping, state confirmation, asset policy, manifest QA, tests/docs | five final-review findings covered; RED→GREEN; T2 remains PARTIAL | focused/related/full tests, compileall, two package builds/audit, diff/status | T1; existing T2 gate | verified |
| T2 | Run host image generation and two fresh compositions | ignored `.brandloom/`, `F:/Projects/cognitive-anchor-sketcher/assets/brandloom-visual-acceptance/`, evidence report | exact dimensions, valid paths, black logo legible, Chinese copy readable, no overwrite | image inspection, BrandLoom CLI QA/delivery, manifest audit | T1; `GENERATION_READY` | blocked |
| T3 | Finalize evidence and package | active plan, ignored SDD ledger, package output | full executable verification and package audit; no scope drift | full unittest, compileall, deterministic ZIP audit, diff/status | T1–T2 | verified |

## Completed + Verified

- T1 implementation commits: `1973f4d2c65b842ca06ae2e2d686b4e5e8a7fe32` and review-fix commit `5db6c1eb6f17327830830462b24b18dd2253ef07`. The initial independent review was `NEEDS_FIX` (missing-glyph sentinel and CLI error-type findings); both fixes are in the second commit. Fresh Task 3 full unittest evidence is 143 tests passing.
- T3 executed with bundled Python 3.12.13 and Pillow 12.3.0: full unittest (143), `compileall -q brandloom tests`, and focused package/asset tests (21) all passed. Two direct package builds produced identical SHA-256 `2a0dc4d22252b896ad0c930797e5e64ca1fcdb2da654ff02344401814c906ce7`.
- ZIP audit found 59 unique entries and no entries from `.brandloom`, `staging`, `tests`, `.superpowers`, `.git`, or `__pycache__`; it also found no supplied composite sheet, cognitive-anchor/generated-image paths, or secret/private-path content.
- Final concentrated fix wave: added shared operation→treatment mapping, state-bound `company_logo_treatment` confirmation and invalidation, machine-readable ENHE operation policy, strict non-default manifest treatment/hash/operation/confirmation QA, and Emoji-safe glyph sentinels. Focused RED was observed before implementation; focused/related suite now passes 62 tests and full suite passes 148 tests. T2 exact-size generation remains PARTIAL/blocked.

## Current Work

- No safe compose task can proceed: T2 must remain at `GENERATION_READY` until a future user-authorized host generation returns exact-size bases.

## Remaining Work

- Obtain new host-built generation results that are exactly 2048×2048 and 2048×1024, then rerun compose, automated validation, manifest audit, manual composed-output inspection, and reviewed delivery.

## Failures

- T2 dimension gate: `exec-6a6cfbc5-25ab-4b0f-bbec-0e87d767dced.png` at `C:\Users\amene\.codex\generated_images\01a05d86-3df9-7782-9c01-f89678b502a2\exec-6a6cfbc5-25ab-4b0f-bbec-0e87d767dced.png` is 1254×1254, SHA-256 `2f2e4d6ceebf42c2cc984285c94562787458ccd2ce5d48241cb979f289d8c438`.
- T2 dimension gate: `exec-bbdff959-f8ce-443a-b7a8-04cedbc942ee.png` at `C:\Users\amene\.codex\generated_images\01a05d86-3df9-7782-9c01-f89678b502a2\exec-bbdff959-f8ce-443a-b7a8-04cedbc942ee.png` is 1774×887, SHA-256 `e9d9c22a4f559e2b17ef9902c1b60397a5760bfb0e9d2c7aa3be45f1e48703f0`.
- Both paths are readable and their generated bases were visually inspected, but neither satisfies the exact pixel contract. `validate_generated_path` hard-stopped composition before output/manifest writes; compose, composed-output visual QA, automated validate, and `deliver --reviewed` are unavailable.

## Evidence

- `C:\Users\amene\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe --version` plus Pillow import -> Python 3.12.13; Pillow 12.3.0.
- `-m unittest discover -s tests -q` -> 143 tests, OK (exit 0).
- `-m compileall -q brandloom tests` -> exit 0.
- `-m unittest tests.test_package tests.test_task3_assets -v` -> 21 tests, OK (exit 0).
- `scripts/build_skill_package.py` twice -> matching SHA-256 above (exit 0); ZIP audit -> 59 unique entries, zero excluded/composite/private-path/secret hits.
- Final fix package builds (`dist/final-fix-a.zip`, `dist/final-fix-b.zip`) -> matching SHA-256 `7aa9ee12666fd86be6266b7a8b7014449886fc9f51efca6845177b3b27f9ae59`; 60 unique entries, zero excluded entries.

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

- Status: PARTIAL
- Requirements verified: T1 code-level black-treatment and CJK tests; generated-base inspection; hard-stop on invalid generation dimensions; full test/compile/package and deterministic ZIP evidence.
- Not verified: final composed black-logo contrast, Chinese glyph readability in a delivered composition, alpha/manifest values for that composition, and reviewed delivery. No final visual acceptance is claimed.
- Remaining risks: host image generation can return correct aspect ratios with non-contract pixel dimensions; no resize, fallback, or automatic retry is authorized.
