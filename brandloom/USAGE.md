# BrandLoom local usage

BrandLoom requires Python 3.12 or newer and the single runtime dependency in
`requirements-runtime.txt`.

The ZIP is a portable Skill package, not a hosted image service. Install it in
any local skills directory; the package does not include an API key, a hidden
network client, or a replacement image provider. Complete generation requires
the current agent host to expose its built-in image tool under the host's own
tool interface. If that capability is unavailable or fails, BrandLoom stops
and preserves the confirmed plan; it does not fall back to an API, SDK, or
third-party provider.

The bundled ENHE logo and IP references are supplied for BrandLoom's confirmed
visual workflow. Their inclusion does not transfer ENHE trademark ownership or
grant a buyer permission to present those assets as their own brand. For a
different project, confirm rights for every uploaded asset and use the
project's own authorized assets where appropriate.

From the directory that contains the installed `brandloom/` folder:

```powershell
python -m pip install -r brandloom/requirements-runtime.txt
python brandloom/scripts/brandloom_cli.py --help
python brandloom/scripts/brandloom_cli.py init --workspace <workspace>
```

The CLI is an offline state, asset, composition, validation, and delivery
boundary. It does not call an image provider. The host Skill obtains one base
image per selected target only after the confirmed QA gate, then passes the
tool-returned path to `compose`. The new flow exports platform covers and does
not create or approve a square logo image.

Selected targets, exact dimensions, language, confirmed copy, scene concept,
and optional workflow cards are recorded in
`.brandloom/brand-brief.json` → `outputs.targets`. Each target is composed,
validated, and manually reviewed independently. After one target is accepted,
the session returns to `GENERATION_READY` for the next selected target; it only
reaches `DELIVERED` when all selected targets are accepted.

For example, after the Skill has confirmed the GitHub Social Preview target and
before invoking the host image tool, preflight the request for the confirmed
target. Preflight also validates the layout and workflow copy, resolves the
selected project mark and required fonts, and checks the approved company-logo
and reference selections. The output contains the approved scene prompt,
dimensions, and all reference image paths that must be passed to the host tool:

```powershell
python brandloom/scripts/brandloom_cli.py request --workspace <workspace> --target-id github-social-preview
```

Only after the preflight succeeds, ask the host image tool for the base image.
After it returns a 2:1 base image:

```powershell
python brandloom/scripts/brandloom_cli.py compose --workspace <workspace> --type cover --target-id github-social-preview --request-id <request_id-from-preflight> --base <returned-image-path>
python brandloom/scripts/brandloom_cli.py validate --workspace <workspace> --type cover --target-id github-social-preview
python brandloom/scripts/brandloom_cli.py deliver --workspace <workspace> --type cover --target-id github-social-preview --reviewed
```

The platform presets and their official/recommended status are listed in
`references/output-specs.md`. A base may be resized only when its aspect ratio
exactly matches the target; resizing is proportional and never crops, distorts,
or overwrites the source. A mismatched ratio stops the current target. Custom
dimensions are limited to 320–8192 pixels per side and 16 megapixels total.

The old `logo-card` CLI route remains only for historical workspaces that do
not have platform targets configured. It is rejected when a new platform-cover
target list exists.
