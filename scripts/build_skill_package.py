"""Build a deterministic, rights-checked BrandLoom skill ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
EXCLUDED_PARTS = {".brandloom", "staging", "tests", "docs", ".git", "__pycache__"}
NORMALIZED_DATE_TIME = (2020, 1, 1, 0, 0, 0)


class PackageError(ValueError):
    """Raised when the candidate package violates its release boundary."""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_denylist(path: Path | None) -> set[str]:
    if path is None:
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PackageError(f"Cannot read denylist {path}: {error}") from error
    if not isinstance(payload, list) or not all(isinstance(value, str) for value in payload):
        raise PackageError("Denylist must be a JSON array of SHA-256 strings")
    invalid = [value for value in payload if len(value) != 64 or any(char not in "0123456789abcdef" for char in value.lower())]
    if invalid:
        raise PackageError("Denylist contains an invalid SHA-256 value")
    return {value.lower() for value in payload}


def is_excluded(relative_path: Path) -> bool:
    return any(part in EXCLUDED_PARTS or part.endswith(".pyc") for part in relative_path.parts)


def validate_asset(path: Path, denylist: set[str]) -> None:
    provenance_path = path.with_name("provenance.json")
    if not provenance_path.is_file():
        raise PackageError(f"Asset lacks adjacent provenance.json: {path}")
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise PackageError(f"Asset provenance is invalid JSON: {provenance_path}") from error
    if provenance.get("authorization_status") != "user_authorized":
        raise PackageError(f"Asset is not authorized for distribution: {path}")
    if sha256(path).lower() in denylist:
        raise PackageError(f"Asset matches denylist: {path}")


def package_files(source: Path, denylist: set[str]) -> list[Path]:
    if not source.is_dir():
        raise PackageError(f"Skill source directory does not exist: {source}")
    files = sorted(
        (path for path in source.rglob("*") if path.is_file() and not is_excluded(path.relative_to(source))),
        key=lambda path: path.relative_to(source).as_posix(),
    )
    if not files or not (source / "SKILL.md").is_file():
        raise PackageError(f"Skill source must contain SKILL.md: {source}")
    for path in files:
        relative_path = path.relative_to(source)
        if relative_path.parts[0] == "assets" and path.suffix.lower() in IMAGE_SUFFIXES:
            validate_asset(path, denylist)
    return files


def build(source: Path, output: Path, denylist: set[str]) -> None:
    files = package_files(source, denylist)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=output.parent, suffix=".zip", delete=False) as temporary_file:
        temporary_path = Path(temporary_file.name)
    try:
        with zipfile.ZipFile(temporary_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in files:
                info = zipfile.ZipInfo(f"{source.name}/{path.relative_to(source).as_posix()}", NORMALIZED_DATE_TIME)
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        temporary_path.replace(output)
    finally:
        temporary_path.unlink(missing_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=REPO_ROOT / "brandloom")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "dist" / "brandloom.zip")
    parser.add_argument("--denylist", type=Path, help="Optional JSON array of forbidden SHA-256 hashes")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    try:
        build(arguments.source.resolve(), arguments.output.resolve(), load_denylist(arguments.denylist))
    except PackageError as error:
        print(f"Package build refused: {error}", file=sys.stderr)
        return 1
    print(f"Built {arguments.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
