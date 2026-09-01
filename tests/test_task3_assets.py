from __future__ import annotations

import hashlib
from io import BytesIO
import json
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

from brandloom.scripts.brandloom_core.models import BrandBrief
from brandloom.scripts.brandloom_core.prompt_builder import build_host_request
from brandloom.scripts.brandloom_core import asset_library
from brandloom.scripts.brandloom_core.models import AssetCategory


ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = ROOT / "brandloom" / "assets" / "defaults"
INCOMING = ROOT / "staging" / "brand-assets" / "incoming"
BUILD = ROOT / "scripts" / "build_skill_package.py"

EXPECTED = {
    "tuotuo-geometry-v1": ("ip/tuotuo/tuotuo-five-view-v1.png", "拓拓五视图.png", "supplemental_geometry", "cace50cd0e54c6180ceda2cb2797dc2fd61746fefc09a9bf64b19e008f017e46"),
    "xingbi-geometry-v1": ("ip/xingbi/xingbi-five-view-v1.png", "星比五视图.png", "supplemental_geometry", "6c6fbc39b45ec8b7fd7dc6883dbb13464772fad5c5c57659ac7158de235850d9"),
    "tuotuo-xingbi-front-v1": ("ip/shared/tuotuo-xingbi-front-v1.png", "拓拓与星比正视图.png", "shared_primary_appearance", "0754c7c51b225e57949bd77cb80eb32195ffc6d81151fe495d9ed1fde1ebbc21"),
    "enhe-white-v2": ("company-logo/enhe-white-v2/reference.png", "白色 ENHE LOGO.png", "explicit_logo_variant", "9e6b890cc043029fcf629684cf38c944376c879737c559772854cbe807dd972a"),
}

EXPECTED_LAYOUT = {
    "tuotuo-geometry-v1": ((1672, 941), "RGB"),
    "xingbi-geometry-v1": ((1448, 1086), "RGB"),
    "tuotuo-xingbi-front-v1": ((1254, 1254), "RGBA"),
    "enhe-white-v2": ((2172, 724), "RGBA"),
}


class Task3AssetTests(unittest.TestCase):
    def test_exact_authorized_assets_have_public_paths_hashes_and_roles(self) -> None:
        for asset_id, (relative, source_name, role, expected_hash) in EXPECTED.items():
            image = ASSET_ROOT / relative
            self.assertTrue(image.is_file(), asset_id)
            source = INCOMING / source_name
            self.assertTrue(source.is_file(), source)
            self.assertEqual(source.read_bytes(), image.read_bytes(), asset_id)
            self.assertEqual(hashlib.sha256(image.read_bytes()).hexdigest(), expected_hash, asset_id)
            with Image.open(image) as decoded:
                decoded.load()
                self.assertEqual((decoded.size, decoded.mode), EXPECTED_LAYOUT[asset_id])
            provenance = image.with_name(f"{image.stem}.provenance.json")
            self.assertTrue(provenance.is_file(), asset_id)
            data = json.loads(provenance.read_text(encoding="utf-8"))
            self.assertEqual(data["source_filename"], source_name)
            self.assertEqual(data["sha256"], expected_hash)
            self.assertEqual(data["authorization_status"], "user_authorized")
            self.assertEqual(data["distribution_scope"], "public_skill_package")
            self.assertEqual(data["reference_role"], role)
            self.assertEqual(data["transformation"], "exact-byte-copy")
            self.assertEqual(data["confirmation_source"], "user_confirmed")
            self.assertRegex(data["confirmed_at"], r"^2026-09-01T.*[+-][0-9]{2}:[0-9]{2}$")
            self.assertEqual(data["save_scope"], "skill-defaults")
            self.assertIs(data["save_scope_confirmed"], True)
            self.assertEqual(data["default_scope"], "skill-defaults")
            self.assertIs(data["default_selection"], False)

    def test_host_request_includes_pair_once_and_geometry_for_selected_characters(self) -> None:
        brief = BrandBrief(
            "1.0", {"name": "Demo", "slug": "demo"}, {"title": "Demo"},
            {"profile": "reference-adaptive"}, {},
            {"logo_card_ip": ["tuotuo", "xingbi"]},
            {"logo_card": {"width": 1254, "height": 1254}},
        )
        request = build_host_request(brief, "logo_card")
        refs = request["reference_assets"]
        ids = [entry["asset_id"] for entry in refs]
        self.assertEqual(ids.count("tuotuo-xingbi-front-v1"), 1)
        self.assertIn("tuotuo-geometry-v1", ids)
        self.assertIn("xingbi-geometry-v1", ids)
        for entry in refs:
            self.assertEqual(entry["category"], "ip-character")
            self.assertIn(entry["reference_role"], {"canonical_appearance", "shared_primary_appearance", "supplemental_geometry"})

    def test_single_character_gets_only_its_geometry_supplement(self) -> None:
        brief = BrandBrief(
            "1.0", {"name": "Demo", "slug": "demo"}, {"title": "Demo"},
            {"profile": "reference-adaptive"}, {},
            {"logo_card_ip": ["tuotuo"]},
            {"logo_card": {"width": 1254, "height": 1254}},
        )
        ids = [entry["asset_id"] for entry in build_host_request(brief, "logo_card")["reference_assets"]]
        self.assertIn("tuotuo", ids)
        self.assertIn("tuotuo-geometry-v1", ids)
        self.assertNotIn("tuotuo-xingbi-front-v1", ids)

    def test_white_logo_variant_is_explicitly_resolvable_and_old_fallback_remains(self) -> None:
        with TemporaryDirectory() as directory:
            workspace = Path(directory)
            skill_root = ROOT / "brandloom"
            selected = asset_library.resolve_asset(
                AssetCategory.COMPANY_LOGO,
                workspace=workspace,
                explicit_asset_id="enhe-white-v2",
                skill_root=skill_root,
            )
            self.assertEqual(selected.record.asset_id, "enhe-white-v2")
            self.assertEqual(selected.path, (ASSET_ROOT / "company-logo/enhe-white-v2/reference.png").resolve())

    def test_package_contains_exact_assets_and_excludes_incoming(self) -> None:
        output = ROOT / "dist" / "task3-test.zip"
        output.unlink(missing_ok=True)
        result = subprocess.run([sys.executable, str(BUILD), "--source", str(ROOT / "brandloom"), "--output", str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        with zipfile.ZipFile(output) as archive:
            names = set(archive.namelist())
            for asset_id, (relative, source_name, _role, expected_hash) in EXPECTED.items():
                packaged = f"brandloom/assets/defaults/{relative}"
                self.assertIn(packaged, names)
                payload = archive.read(packaged)
                self.assertEqual(hashlib.sha256(payload).hexdigest(), expected_hash, asset_id)
                stem = packaged.rsplit("/", 1)[1].rsplit(".", 1)[0]
                sidecar = packaged.rsplit("/", 1)[0] + f"/{stem}.provenance.json"
                self.assertIn(sidecar, names, asset_id)
                provenance = json.loads(archive.read(sidecar).decode("utf-8"))
                self.assertEqual(provenance["source_filename"], source_name)
                self.assertEqual(provenance["sha256"], expected_hash)
                self.assertEqual(provenance["reference_sha256"], expected_hash)
                self.assertEqual(provenance["authorization_status"], "user_authorized")
                self.assertEqual(provenance["distribution_scope"], "public_skill_package")
                self.assertEqual(provenance["save_scope"], "skill-defaults")
                self.assertIs(provenance["save_scope_confirmed"], True)
                self.assertEqual(provenance["default_scope"], "skill-defaults")
                self.assertIs(provenance["default_selection"], False)
                with Image.open(BytesIO(payload)) as decoded:
                    decoded.load()
                    self.assertEqual((decoded.size, decoded.mode), EXPECTED_LAYOUT[asset_id])
            self.assertFalse(any("incoming" in name or "staging" in name for name in names))

    def test_same_stem_provenance_tamper_does_not_fall_back_to_directory_record(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            skill_root = root / "brandloom"
            asset_dir = skill_root / "assets" / "defaults" / "company-logo" / "sample"
            asset_dir.mkdir(parents=True)
            image = asset_dir / "reference.png"
            Image.new("RGBA", (8, 8), "white").save(image)
            digest = hashlib.sha256(image.read_bytes()).hexdigest()
            valid = {
                "source_reference": "fixture",
                "sha256": digest,
                "confirmed_at": "2026-09-01T00:00:00+00:00",
                "confirmation_source": "fixture",
                "authorization_status": "user_authorized",
                "distribution_scope": "public_skill_package",
            }
            (asset_dir / "provenance.json").write_text(json.dumps(valid), encoding="utf-8")
            (skill_root / "SKILL.md").write_text("---\nname: brandloom\n---\n", encoding="utf-8")
            cases = {
                "hash-mismatch": json.dumps({**valid, "sha256": "0" * 64}),
                "unauthorized": json.dumps({**valid, "authorization_status": "analysis_only"}),
                "malformed": "{not-json",
            }
            for label, sidecar in cases.items():
                with self.subTest(label=label):
                    sidecar_path = asset_dir / "reference.provenance.json"
                    sidecar_path.write_text(sidecar, encoding="utf-8")
                    if label == "unauthorized":
                        self.assertEqual(
                            asset_library._skill_default_records(AssetCategory.COMPANY_LOGO, skill_root),
                            (),
                        )
                    else:
                        with self.assertRaises(asset_library.AssetManifestError):
                            asset_library._skill_default_records(AssetCategory.COMPANY_LOGO, skill_root)
                    result = subprocess.run(
                        [sys.executable, str(BUILD), "--source", str(skill_root), "--output", str(root / f"package-{label}.zip")],
                        capture_output=True,
                        text=True,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertTrue(
                        "provenance" in result.stderr.lower()
                        or "authorized" in result.stderr.lower()
                    )


if __name__ == "__main__":
    unittest.main()
