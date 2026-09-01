"""Build a deterministic, rights-checked BrandLoom skill ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from PIL import Image, UnidentifiedImageError


REPO_ROOT = Path(__file__).resolve().parents[1]
IMAGE_SUFFIXES = {
    ".avif",
    ".bmp",
    ".gif",
    ".heic",
    ".heif",
    ".ico",
    ".jfif",
    ".jpeg",
    ".jpe",
    ".jpg",
    ".png",
    ".svg",
    ".tif",
    ".tiff",
    ".webp",
}
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


def is_sha256(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(character in "0123456789abcdef" for character in value.lower())


def provenance_path_for(path: Path) -> Path | None:
    # Prefer a same-stem record for versioned/supplemental files. Keep the
    # directory-level fallback for the original canonical layout.
    per_file = path.with_name(f"{path.stem}.provenance.json")
    if per_file.is_file():
        return per_file
    per_directory = path.with_name("provenance.json")
    if per_directory.is_file():
        return per_directory
    return None


def validate_asset(path: Path, denylist: set[str]) -> None:
    provenance_path = provenance_path_for(path)
    if provenance_path is None:
        raise PackageError(f"Image lacks adjacent provenance.json: {path}")
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise PackageError(f"Asset provenance is invalid JSON: {provenance_path}") from error
    required_text_fields = (
        "source_reference",
        "sha256",
        "confirmed_at",
        "confirmation_source",
        "authorization_status",
        "distribution_scope",
    )
    missing = [field for field in required_text_fields if not isinstance(provenance.get(field), str) or not provenance[field].strip()]
    if missing:
        raise PackageError(f"Image provenance lacks required fields {missing}: {provenance_path}")
    if provenance["authorization_status"] != "user_authorized":
        raise PackageError(f"Image is not authorized for distribution: {path}")
    if provenance["distribution_scope"] != "public_skill_package":
        raise PackageError(f"Image provenance has a non-public distribution scope: {provenance_path}")
    if not is_sha256(provenance["sha256"]):
        raise PackageError(f"Image provenance has an invalid SHA-256: {provenance_path}")
    try:
        if "T" not in provenance["confirmed_at"]:
            raise ValueError("timestamp lacks T separator")
        confirmed_at = datetime.fromisoformat(provenance["confirmed_at"].replace("Z", "+00:00"))
        if confirmed_at.tzinfo is None:
            raise ValueError("timestamp lacks timezone")
    except ValueError as error:
        raise PackageError(f"Image provenance has an invalid ISO-8601 confirmation time: {provenance_path}") from error
    expected_hash = provenance.get("reference_sha256", provenance["sha256"])
    if not is_sha256(expected_hash):
        raise PackageError(f"Image provenance has an invalid reference SHA-256: {provenance_path}")
    actual_hash = sha256(path).lower()
    if actual_hash != expected_hash.lower():
        raise PackageError(f"Image SHA-256 does not match provenance: {path}")
    relevant_hashes = {actual_hash, provenance["sha256"].lower()}
    if "reference_sha256" in provenance:
        relevant_hashes.add(provenance["reference_sha256"].lower())
    if relevant_hashes.intersection(denylist):
        raise PackageError(f"Image matches denylist: {path}")
    if path.suffix.lower() != ".svg":
        try:
            with Image.open(path) as image:
                image.load()
        except (UnidentifiedImageError, OSError, SyntaxError, ValueError) as error:
            raise PackageError(f"Raster image cannot be decoded: {path}") from error


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
        if path.suffix.lower() in IMAGE_SUFFIXES:
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
