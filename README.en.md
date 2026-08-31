# BrandLoom

BrandLoom is a Codex Skill for brand-visual workflows. It uses confirmatory QA, one question at a time, to collect project context, copy, style, typography, rights, and output specifications before producing traceable logo key visuals and covers.

## Install and invoke

Copy this repository's `brandloom/` directory into the Codex skills directory (normally `$CODEX_HOME/skills/brandloom/`). Reopen the workspace and invoke it with:

```text
Use $brandloom
```

For example: `Use $brandloom to make Chinese and English logo key visuals and a GitHub cover for my open-source project.`

## QA and assets

BrandLoom asks only one unconfirmed question at a time. Changes are reconfirmed through an invalidation matrix. The asset library records rights, storage scope, and default scope. A formal company logo is never redrawn by an image model, stretched, altered in typeform, or altered in geometry; critical Chinese and English text is laid out deterministically with Pillow.

The built-in IP options are `author-anime`, `tuotuo`, and `xingbi`; they are peers and support single, pair, and all-three combinations. Logo key visuals and covers can choose IP combinations independently. Chinese and English versions are supported; localization reuses confirmed backgrounds and asset hashes without overwriting the source-language version.

## Generation and boundaries

Only `GENERATION_READY` work that has explicit confirmation can call the host built-in image tool. If the tool is unavailable, fails, returns an empty path, or returns an unreadable file, BrandLoom hard-stops: it does not request an API key or switch to an Images API, SDK, third-party provider, or recursive Codex call.

Every uploaded asset must have confirmed rights, storage scope, and default scope. The public package contains only assets with provenance and `authorization_status` of `user_authorized`; third-party commercial posters may inform abstract style only and never enter the release package. Do not provide private data, keys, tokens, cookies, or unauthorized portraits or brand assets.

## Local use and development

Python 3.12 and the sole runtime dependency Pillow 12.3.0 are required:

```powershell
py -3.12 -m pip install -r requirements-runtime.txt
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
py -3.12 scripts/build_skill_package.py
```

The build artifact is `dist/brandloom.zip`; it packages only releasable `brandloom/` content and rejects image assets that lack authorized provenance. Development state, staging assets, and local outputs are not added to Git.
