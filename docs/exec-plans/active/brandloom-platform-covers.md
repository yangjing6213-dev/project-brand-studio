# BrandLoom platform cover outputs

## Original Goal
Replace the Skill's logo-square-first workflow with user-selected YouTube, Douyin, Xiaohongshu, GitHub, and custom-size project covers; remove logo-card generation from the normal Skill workflow.

## Task Contract
- Requirements: support YouTube long-form (3840×2160), Shorts (2160×3840), channel banner (2560×1440); Douyin and Xiaohongshu practical starting point 1080×1440; GitHub Social Preview 1280×640; confirmed custom dimensions. User selected all three YouTube targets.
- Design decisions: one consistent brand system with per-platform layout adaptation; same core selling point with per-platform copy length/information density; one language per target audience; real-world project-relevant scene backgrounds; no 1:1 LOGO card output. For scene continuity, use one shared scene concept and independently generate a layout-matched base for every aspect ratio; keep setting, lighting, and mood consistent without cropping. User confirmed all three YouTube targets.
- Constraints: preserve JSON runtime data and Pillow-only runtime; maintain `GENERATION_READY` before host image tool; do not call paid/external APIs, push, publish, or overwrite historical outputs; keep official requirements distinct from recommendations.
- Acceptance Criteria: selected targets/languages/dimensions are confirmed and recorded per output; each selected output is composed at the exact requested pixels with target-specific layout and copy; each output gets an independent versioned manifest and QA; no unselected square logo is generated; unsupported transformation or image-tool output fails closed.
- Deliverables: updated QA/skill instructions, output spec/template configuration, runtime generation/composition/validation support, tests, and updated user-facing docs.
- Non-goals: new providers/APIs, background image generation in this implementation turn, GitHub publication, or deleting historical user output.
- Risks: host image tool may not produce requested pixel dimensions; custom extreme aspect ratios may not fit current composition recipes. User resolved base-image handling: only exact same-aspect-ratio proportional resize may be used; differing ratios hard-stop and require a separately generated base; no cropping or distortion. Upscaling does not create image detail.
- Testing Strategy: test-first per schema/renderer/CLI behavior, focused and full unittest, compileall if runtime code changes, `git diff --check`, status/diff scope audit, Skill validation if dependencies are available.

## Current Repository State
- Governing instructions: user-provided AGENTS.md instructions; no repository AGENTS.md found in the active worktree.
- Relevant architecture: `BrandBrief.outputs` is a JSON mapping; platform/custom output sizes resolve from a JSON registry; versioned templates and manifests are created per selected target. The confirmed policy is exact-ratio proportional resize only, with no crop or distortion.
- Initial Git state: isolated branch `codex/brandloom-platform-cover-qa` from `f6fc1ed`; working tree already contains uncommitted implementation and tests from the preceding BrandLoom iteration. Main worktree was left untouched.
- Runtime: bundled Python 3.12.14. The current final verification is recorded below; the system Python alias is unavailable in this host, so checks use the bundled Python executable.

## Task Plan
| ID | Objective | Files likely affected | Acceptance criteria | Verification | Dependencies | Status |
|---|---|---|---|---|---|---|
| T1 | Finish QA contract for platform language and copy strategy | QA workflow, Skill, checklist, contract tests | Each target records language; platform copy strategy is explicit; no square-first step | focused Skill contract test | none | verified |
| T2 | Define validated platform/custom output configuration and template sizing | models, spec registry, templates, tests | Known target dimensions resolve exactly; custom positive dimensions and safe limits validate | targeted unit tests | T1 | verified |
| T3 | Render target-sized covers without distorting completed layouts | renderer/layout/templates/tests | Text/logo are laid out on target canvas; unsupported aspect/layout fails closed | renderer tests + pixel/dimension checks | T2 + confirmed same-ratio resize/no-crop policy | verified |
| T4 | Route per-target language/copy/output through generation, manifests, QA and delivery | prompt builder, CLI, validation, manifest tests | Each selected target has independent output path, manifest, exact size, and delivery review | end-to-end CLI tests | T2,T3 | verified |
| T5 | Align docs and verify/package the finished Skill | references, README, tests, package checks | Current limits are accurate; full tests/package exclusions pass | full suite, build, ZIP inspect, diff/status | T1–T4 | verified |

## Completed + Verified
- Platform output requirements and public platform-spec sources were recorded in `brandloom/references/output-specs.md`; exact official requirements are distinguished from practical recommendations.
- QA menu includes three YouTube targets, common-brand/per-platform-layout strategy, per-platform copy density, real-scene requirement, and one language per target audience.
- User-facing QA now requires visibly labeled choices in every question, a project-specific recommendation with its reason, and separate questions when one stage contains multiple decisions; a contract test guards this requirement.
- User confirmed one real-scene concept across platforms, with separate bases per aspect ratio and consistent setting, lighting, and mood.
- User confirmed workflow diagram density adapts to each canvas: clear 3–4 steps on wide covers; 2–3 short steps or benefits on vertical/small covers, without tiny text.
- User confirmed diagram styling: thin borders, approximately 60% opacity (40% transparency) frosted treatment inside each step card, no whole-image blur or outer diagram frame, smooth corners, and sufficient text spacing.
- User-confirmed base-image rule is recorded: exact aspect-ratio match permits proportional resizing only; different ratios stop and require a separately generated base; cropping and distortion are prohibited.
- Full platform targets, constrained custom sizes, proportional resize/no-crop handling, per-target templates, frosted workflow-card rendering, independent manifests, target file-size validation, and batch delivery were implemented and covered by tests.
- Cover image prompts no longer inherit the old fixed left-third/bottom-band blank zones; they explicitly request a full-bleed real scene with overlay copy and no fixed left-copy/right-scene arrangement.
- The exact user-confirmed workflow-card style is implemented and recorded: thin outlines, localized translucent/frosted fill, no whole-image blur or outer frame, smooth corners, and adequate text spacing.

## Current Work
- Runtime, QA contract, and documentation are implemented. The independent review's final finding is now fixed: request preflight checks actual font glyph coverage and copy/workflow text fit before a generation request can be emitted; overflow now stops instead of silently falling back to the smallest font.
- Four focused regression tests cover unsupported glyphs in main copy and workflow labels, plus text that cannot fit in the main copy box or workflow card. All pass.
- Independent rereview of the final fix found no Critical or Important issues. It recorded one Minor edge case: glyph validation focuses on non-ASCII characters, so an unusual font missing an ASCII glyph could evade this check; this is accepted as a low-risk residual for this integration.
- The current candidate package is `dist/brandloom-platform-covers-verified-20261011-r5.zip`; it is a local ignored build artifact, not committed or published.

## Remaining Work
- Commit the isolated branch and locally integrate it while preserving the unrelated dirty main-worktree visual edits; then verify the integrated result. Do not push or publish.
- Host image generation and human visual review of a real project cover are not part of this implementation run; perform them when an actual project generation is initiated.

## Failures
- An initial full-suite run exposed implementation defects and stale fixtures: a manifest variable typo, fixtures without an explicit company-logo choice, an obsolete legacy-cover expectation, and assertions that no longer matched the confirmed card opacity wording. These were corrected without weakening validation; the final suite passed.
- Independent review findings were addressed: each platform compose now needs a current preflight request ID tied to the confirmed target and brief hash; targetless legacy covers need accepted logo-card evidence before state transition; Style B requires confirmed clothing and a contrast-safe accent; Style D requires an explicitly confirmed project-style source.
- The final independent review found that font-file existence alone did not prove character coverage or layout fit and that workflow card labels could overflow. The preflight now checks every displayed copy slot and workflow heading/subtitle/label/detail against the selected fonts and layout; it fails closed before emitting a generation request. The regression tests were first observed failing, then passed after the fix.
- Independent rereview after the fix found no Critical or Important issues. Ruling: accept its single Minor note about rare fonts missing ASCII glyphs as a low-risk residual; the reported issue was missing Chinese glyphs and the new preflight now checks Chinese copy and workflow text.
- Skill Creator's auxiliary validator initially lacked PyYAML in the bundled Python environment and encountered Windows console encoding with Chinese text. PyYAML was exposed through a temporary process-scoped `PYTHONPATH` and the validator ran with Python UTF-8 mode. It reported `Skill is valid!`; no project dependency or validator script was changed.

## Evidence
- Bundled Python `-m unittest discover -s tests -q` -> 225 tests passed, 1 skipped.
- Focused platform/prompt tests -> 36 passed; pipeline, legacy-contract, and Skill-contract tests -> 62 passed.
- Bundled Python `-m compileall -q brandloom/scripts` -> passed.
- Skill Creator `quick_validate.py brandloom` -> `Skill is valid!`; PyYAML was exposed only through a temporary process-scoped `PYTHONPATH`, and `-X utf8` handled the Windows console encoding. No project/runtime dependency was added.
- `scripts/build_skill_package.py --output dist/brandloom-platform-covers-verified-20261011-r5.zip` -> succeeded; archive contains 63 entries including the platform registry and templates, with no forbidden entries (`.brandloom`, staging, tests, docs, cache, or `.git`). SHA-256: `31c37148bd76c04fb3a31beba0143da1bd5f88038c98061a282366291908b512`.
- `git diff --check` -> passed (Git printed only expected LF-to-CRLF notices for three Markdown files).

## Important Decisions
- The default is separate per-platform composition, never stretching a completed image across aspect ratios.
- Base-image transformation policy is confirmed: exact aspect ratio permits proportional resize only; different ratios stop and require a separate image; cropping and distortion are prohibited.
- Douyin/Xiaohongshu 1080×1440 is a recommended starting point, not an official fixed requirement.
- Image tools cannot be used until the per-task `GENERATION_READY` confirmation.

## Open Risks
- Real host-generated visual results were not created or visually reviewed in this code-change task. Each actual platform canvas still requires per-image manual review after generation; image-tool success alone is not visual acceptance.
- Glyph coverage validation checks non-ASCII characters; a rare font missing an ASCII glyph may not be caught by preflight.

## Final Acceptance
- Status: pending local integration verification; no artwork or publishing acceptance is claimed.
- Requirements verified: project-specific visible QA choices, platform/custom target resolution, target-specific layout and copy, proportional resize-only policy, no-crop enforcement, independent output manifests/reviews, and package exclusions.
- Not run: host image generation and manual visual review; there is no new artwork from this implementation task to inspect.
- Remaining risk: visually inspect each generated canvas before any external use or publication.
