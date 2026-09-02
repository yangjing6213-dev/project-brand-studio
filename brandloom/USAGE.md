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
boundary. It does not call an image provider. The host Skill obtains a base
image only after the confirmed QA gate and passes its returned path to
`compose`. Run `logo-card` composition, validation, and reviewed delivery
before composing a `cover`.
