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
- Initial Git state: isolated branch `codex/brandloom-platform-cover-qa` from `f6fc1ed`; working tree already contained uncommitted implementation and tests from the preceding BrandLoom iteration. The completed implementation was committed as `b359715` and fast-forwarded locally to `main`; no push or publication occurred.
- The pre-existing local visual edits and three PNG deliverables were preserved in the main worktree. A protective stash remains available as `stash@{0}`; it was not dropped. The isolated worktree remains available at `.worktrees/brandloom-platform-cover-qa`.
- Runtime: bundled Python 3.12.14. The current final verification is recorded below; the system Python alias is unavailable in this host, so checks use the bundled Python executable.

## Task Plan
| ID | Objective | Files likely affected | Acceptance criteria | Verification | Dependencies | Status |
|---|---|---|---|---|---|---|
| T1 | Finish QA contract for platform language and copy strategy | QA workflow, Skill, checklist, contract tests | Each target records language; platform copy strategy is explicit; no square-first step | focused Skill contract test | none | verified |
| T2 | Define validated platform/custom output configuration and template sizing | models, spec registry, templates, tests | Known target dimensions resolve exactly; custom positive dimensions and safe limits validate | targeted unit tests | T1 | verified |
| T3 | Render target-sized covers without distorting completed layouts | renderer/layout/templates/tests | Text/logo are laid out on target canvas; unsupported aspect/layout fails closed | renderer tests + pixel/dimension checks | T2 + confirmed same-ratio resize/no-crop policy | verified |
| T4 | Route per-target language/copy/output through generation, manifests, QA and delivery | prompt builder, CLI, validation, manifest tests | Each selected target has independent output path, manifest, exact size, and delivery review | end-to-end CLI tests | T2,T3 | verified |
| T5 | Align docs and verify/package the finished Skill | references, README, tests, package checks | Current limits are accurate; full tests/package exclusions pass | full suite, build, ZIP inspect, diff/status | T1–T4 | verified |
| T6 | Automatically recover missing font characters | font coverage/resolution, CLI, font guidance, tests | Check all used characters; prefer local/profile fallbacks; download a pinned, licensed fallback to ignored local cache when needed; continue only after coverage and layout pass | focused tests with mocked download, full unittest, compileall, package exclusion check | T1–T5 | verified |

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
- T6 implementation is complete locally. Preflight now reads Unicode cmap data (formats 4, 6, 12, and 13) and checks every visible character in title, subtitle, value, feature, and workflow copy, including ASCII punctuation and workflow step numbers. It tries the confirmed font, the preset fallback chain, then every locally discovered font; only if none works does it fetch a pinned Noto Sans CJK SC file into `.brandloom/font-cache/`.
- The download is restricted to pinned `raw.githubusercontent.com` URLs, exact expected byte count and SHA-256, and a matching SIL Open Font License file. It stores the license and a JSON provenance record, validates that Pillow can open the font, and never installs into system folders or the public Skill package. A replaced/corrupt cache entry is preserved; the verified copy is staged and installed beside it.
- The selected/resolved font still passes existing Pillow layout-fit checks before image-tool requests and composition. Network, integrity, or unsupported-script failures report the specific cause instead of rendering boxes or pretending the copy is complete.
- User follow-up changed the previous manual font-confirmation gate: an unsupported character must cause automatic recovery, not a user prompt. This override is reflected in the Skill, QA instructions, and font preset guidance.
- Focused tests now cover ASCII punctuation detection in cmap formats 4, 6, and 12, profile/local font recovery, download fallback, license/provenance retention, tampered download and unapproved redirect rejection, and exact copy/workflow text collection including step numbers.
- The branch was locally integrated into `main` by fast-forward at `b359715`. A post-integration independent review found no Critical, Important, or Minor findings; it confirmed preflight and drawing share the same workflow geometry and that the previously confirmed cover layout values remain intact.
- The optional Skill Creator validator was unblocked without changing project dependencies: PyYAML was exposed using a temporary process-scoped `PYTHONPATH`, and Python UTF-8 mode resolved Windows console encoding. It reported `Skill is valid!`.
- The verified candidate package for this font-recovery update is `dist/brandloom-font-recovery-20261011-r3.zip`; it is a local ignored build artifact, not committed or published.

## Remaining Work
- T6 implementation and verification are complete. No commit, push, or publication was performed.
- Host image generation and human visual review of a real project cover were not part of this implementation/integration request; perform them when an actual project generation is initiated.

## Failures
- An initial full-suite run exposed implementation defects and stale fixtures: a manifest variable typo, fixtures without an explicit company-logo choice, an obsolete legacy-cover expectation, and assertions that no longer matched the confirmed card opacity wording. These were corrected without weakening validation; the final suite passed.
- Independent review findings were addressed: each platform compose now needs a current preflight request ID tied to the confirmed target and brief hash; targetless legacy covers need accepted logo-card evidence before state transition; Style B requires confirmed clothing and a contrast-safe accent; Style D requires an explicitly confirmed project-style source.
- The final independent review found that font-file existence alone did not prove character coverage or layout fit and that workflow card labels could overflow. The preflight now checks every displayed copy slot and workflow heading/subtitle/label/detail against the selected fonts and layout; it fails closed before emitting a generation request. The regression tests were first observed failing, then passed after the fix.
- The independent font review's findings were resolved: redirect targets are checked before following them, workflow step numbers are included in font coverage, and Unicode cmap format 6 is supported to avoid unnecessary font substitution. The final independent review found no Critical, Important, or Minor findings.
- Skill Creator's auxiliary validator initially lacked PyYAML in the bundled Python environment and encountered Windows console encoding with Chinese text. PyYAML was exposed through a temporary process-scoped `PYTHONPATH` and the validator ran with Python UTF-8 mode. It reported `Skill is valid!`; no project dependency or validator script was changed.
- The first live fallback download was correctly rejected because the source SHA-256 had one transposed character in the constant. The bytes were independently re-fetched and hashed; the constant was corrected to the actual pinned file hash before any font was installed. The subsequent live download, Pillow load, glyph coverage, license, and provenance checks passed.

## Evidence
- Bundled Python 3.12.14 `-X utf8 -m unittest discover -s tests -q` after T6 changes -> 236 tests passed, 1 skipped.
- Focused platform/prompt tests -> 36 passed; pipeline, legacy-contract, and Skill-contract tests -> 62 passed.
- Bundled Python `-m compileall -q brandloom/scripts` -> passed.
- Skill Creator `quick_validate.py brandloom` -> `Skill is valid!`; PyYAML was exposed only through a temporary process-scoped `PYTHONPATH`, and `-X utf8` handled the Windows console encoding. No project/runtime dependency was added.
- `scripts/build_skill_package.py --output dist/brandloom-font-recovery-20261011-r3.zip` -> succeeded; archive contains 63 entries and excludes `.brandloom`, `staging`, tests, docs, font cache, `__pycache__`, and `.git`. SHA-256: `cb80f6d2d47e59048f8dfb35b56c4b6ed1b1a530ba90b40cf973645daa40f1ed`.
- `git diff --check` -> passed.
- Final independent font review -> no Critical, Important, or Minor findings; read-only.
- Local Git integration -> `main` points to `b359715` (`feat: add multi-platform BrandLoom cover workflow`); no remote write was performed. The original local visual files and their pending edits remain uncommitted and untouched by publication actions.
- Live fallback install into a temporary directory -> official Noto Sans CJK SC version 2.004 loaded in Pillow; the sample containing English letters, digits, ASCII punctuation, em dash, and Chinese produced no missing characters; license and provenance files were present. Temporary verification cache was discarded automatically.

## Important Decisions
- The default is separate per-platform composition, never stretching a completed image across aspect ratios.
- Base-image transformation policy is confirmed: exact aspect ratio permits proportional resize only; different ratios stop and require a separate image; cropping and distortion are prohibited.
- Douyin/Xiaohongshu 1080×1440 is a recommended starting point, not an official fixed requirement.
- Image tools cannot be used until the per-task `GENERATION_READY` confirmation.
- User superseded the previous “missing font stops for user choice” policy. A valid automatic fallback is preferred; the fallback must cover all used text and pass the existing fit check before generation may proceed.

## Open Risks
- Real host-generated visual results were not created or visually reviewed in this code-change task. Each actual platform canvas still requires per-image manual review after generation; image-tool success alone is not visual acceptance.
- Automatic download needs network access to GitHub only when no installed font covers all displayed text. If the host blocks that source or the downloaded bytes do not match the pin, the Skill cannot safely install an unverified font and reports the exact cause instead of continuing with missing glyphs.
- The pinned CJK fallback covers common English/CJK copy and punctuation, not every possible script or emoji; unsupported characters still cannot be rendered honestly by this single fallback.

## Final Acceptance
- Status: PASS for implementation, auxiliary validation, and local branch integration. No artwork generation, visual acceptance, or publishing acceptance is claimed.
- Requirements verified: project-specific visible QA choices, platform/custom target resolution, target-specific layout and copy, proportional resize-only policy, no-crop enforcement, independent output manifests/reviews, and package exclusions.
- Not run: host image generation and manual visual review; there is no new artwork from this implementation task to inspect.
- Remaining risk: visually inspect each generated canvas before any external use or publication. The working tree intentionally retains local visual edits and PNGs; `stash@{0}` remains as a recovery copy.
