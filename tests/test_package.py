"""Release-package contract tests for BrandLoom."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_skill_package.py"
PACKAGE_PATH = REPO_ROOT / "dist" / "brandloom.zip"


class PackageContractTests(unittest.TestCase):
    def build_package(self) -> None:
        subprocess.run(
            [sys.executable, str(BUILD_SCRIPT)],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_release_zip_contains_required_skill_content_and_excludes_local_paths(self) -> None:
        self.build_package()
        with zipfile.ZipFile(PACKAGE_PATH) as archive:
            names = archive.namelist()

        required = {
            "brandloom/SKILL.md",
            "brandloom/agents/openai.yaml",
        }
        self.assertTrue(required.issubset(names))
        for directory in (
            "brandloom/references/",
            "brandloom/templates/",
            "brandloom/scripts/",
            "brandloom/assets/defaults/",
        ):
            self.assertTrue(any(name.startswith(directory) for name in names), directory)

        excluded_parts = (".brandloom/", "staging/", "tests/", "docs/superpowers/", ".git/", "__pycache__/")
        self.assertFalse(
            [name for name in names if any(part in name for part in excluded_parts)],
            names,
        )

    def test_release_zip_is_deterministic(self) -> None:
        self.build_package()
        first = PACKAGE_PATH.read_bytes()
        self.build_package()
        self.assertEqual(first, PACKAGE_PATH.read_bytes())

    def test_builder_rejects_assets_without_authorized_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "brandloom"
            asset = source / "assets" / "defaults" / "sample"
            asset.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: brandloom\n---\n", encoding="utf-8")
            (asset / "reference.png").write_bytes(b"not-an-image-but-an-asset")
            result = subprocess.run(
                [sys.executable, str(BUILD_SCRIPT), "--source", str(source), "--output", str(Path(temporary_directory) / "package.zip")],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("provenance", result.stderr.lower())

    def test_builder_rejects_supported_image_outside_assets_without_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "brandloom"
            references = source / "references"
            references.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: brandloom\n---\n", encoding="utf-8")
            (references / "untracked-preview.webp").write_bytes(b"image outside assets")
            result = subprocess.run(
                [sys.executable, str(BUILD_SCRIPT), "--source", str(source), "--output", str(Path(temporary_directory) / "package.zip")],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("provenance", result.stderr.lower())

    def test_builder_rejects_incomplete_or_forged_provenance_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "brandloom"
            asset = source / "assets" / "defaults" / "sample"
            asset.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: brandloom\n---\n", encoding="utf-8")
            (asset / "reference.bmp").write_bytes(b"actual image bytes")
            (asset / "provenance.json").write_text(
                json.dumps(
                    {
                        "source_reference": "synthetic test asset",
                        "sha256": "0" * 64,
                        "confirmed_at": "2026-09-01T00:00:00+00:00",
                        "confirmation_source": "test",
                        "authorization_status": "user_authorized",
                        "distribution_scope": "public_skill_package",
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(BUILD_SCRIPT), "--source", str(source), "--output", str(Path(temporary_directory) / "package.zip")],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sha-256", result.stderr.lower())

    def test_builder_accepts_cropped_asset_reference_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "brandloom"
            asset = source / "assets" / "defaults" / "sample"
            asset.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: brandloom\n---\n", encoding="utf-8")
            payload = b"cropped image bytes"
            image = asset / "reference.tiff"
            image.write_bytes(payload)
            (asset / "provenance.json").write_text(
                json.dumps(
                    {
                        "source_reference": "synthetic source image",
                        "sha256": "1" * 64,
                        "reference_sha256": hashlib.sha256(payload).hexdigest(),
                        "confirmed_at": "2026-09-01T00:00:00+00:00",
                        "confirmation_source": "test",
                        "authorization_status": "user_authorized",
                        "distribution_scope": "public_skill_package",
                    }
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [sys.executable, str(BUILD_SCRIPT), "--source", str(source), "--output", str(Path(temporary_directory) / "package.zip")],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_builder_rejects_denylisted_asset_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source = Path(temporary_directory) / "brandloom"
            asset = source / "assets" / "defaults" / "sample"
            asset.mkdir(parents=True)
            (source / "SKILL.md").write_text("---\nname: brandloom\n---\n", encoding="utf-8")
            payload = b"synthetic forbidden reference"
            (asset / "reference.png").write_bytes(payload)
            (asset / "provenance.json").write_text(
                json.dumps(
                    {
                        "source_reference": "synthetic test asset",
                        "sha256": hashlib.sha256(payload).hexdigest(),
                        "confirmed_at": "2026-09-01T00:00:00+00:00",
                        "confirmation_source": "test",
                        "authorization_status": "user_authorized",
                        "distribution_scope": "public_skill_package",
                    }
                ),
                encoding="utf-8",
            )
            denylist = Path(temporary_directory) / "denylist.json"
            denylist.write_text(json.dumps([hashlib.sha256(payload).hexdigest()]), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(BUILD_SCRIPT),
                    "--source",
                    str(source),
                    "--output",
                    str(Path(temporary_directory) / "package.zip"),
                    "--denylist",
                    str(denylist),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("denylist", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
