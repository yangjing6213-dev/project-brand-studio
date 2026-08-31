# BrandLoom local usage

BrandLoom requires Python 3.12 or newer and the single runtime dependency in
`requirements-runtime.txt`.

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
