from __future__ import annotations

import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from brandloom.scripts.brandloom_core.manifests import build_generation_manifest
from brandloom.scripts.brandloom_core.models import BrandBrief
from brandloom.scripts.brandloom_core.renderer import render_brand_asset
from brandloom.scripts.brandloom_core.validation import QAReport, localize_brief, validate_output


class LocalizationAndQATests(unittest.TestCase):
    def _font(self) -> Path:
        for path in (Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\segoeui.ttf")):
            if path.is_file():
                return path
        self.skipTest("Windows font fixture unavailable")

    def _brief(self, title: str, subtitle: str) -> BrandBrief:
        return BrandBrief("1.0", {"name": "demo", "slug": "demo"},
                          {"title": title, "subtitle": subtitle}, {"foreground": "#111111"},
                          {"heading": str(self._font()), "body": str(self._font())},
                          {"logo_card_ip": ["tuotuo"]}, {"logo_card": {"width": 2048, "height": 2048}})

    def _fixtures(self, root: Path) -> tuple[Path, Path, dict[str, Path]]:
        base = root / "base.png"
        Image.new("RGBA", (2048, 2048), "white").save(base)
        logo = root / "logo.png"
        Image.new("RGBA", (400, 100), (10, 80, 180, 255)).save(logo)
        return base, logo, {"company_logo": logo, "project_mark": logo}

    def test_localization_reuses_hashes_and_preserves_english(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base, logo, assets = self._fixtures(root)
            english = self._brief("Brand title", "English subtitle")
            english_copy_before = dict(english.copy)
            chinese = localize_brief(english, language="zh-CN", copy={"title": "品牌标题", "subtitle": "中文副标题"})
            en = render_brand_asset(Path("brandloom/templates/logo-card-1x1.json"), english, base_image=base, asset_paths=assets,
                                    font_paths={"heading": self._font(), "body": self._font()}, output_dir=root / "en")
            zh = render_brand_asset(Path("brandloom/templates/logo-card-1x1.json"), chinese, base_image=base, asset_paths=assets,
                                    font_paths={"heading": self._font(), "body": self._font()}, output_dir=root / "zh")
            en_manifest = build_generation_manifest(brief_path=root / "en.json", assets=[{"asset_id": "logo", "sha256": _sha(logo)}],
                                                    template_path=Path("brandloom/templates/logo-card-1x1.json"), font_paths={}, base_image_path=base,
                                                    output_path=en.output_path, qa_state="GENERATION_READY", rendered_copy=english.copy)
            zh_manifest = build_generation_manifest(brief_path=root / "zh.json", assets=[{"asset_id": "logo", "sha256": _sha(logo)}],
                                                    template_path=Path("brandloom/templates/logo-card-1x1.json"), font_paths={}, base_image_path=base,
                                                    output_path=zh.output_path, qa_state="GENERATION_READY", rendered_copy=chinese.copy)
            self.assertEqual(en_manifest["base_image"]["sha256"], zh_manifest["base_image"]["sha256"])
            self.assertEqual(en_manifest["assets"][0]["sha256"], zh_manifest["assets"][0]["sha256"])
            self.assertNotEqual(en.output_path, zh.output_path)
            self.assertEqual(zh_manifest["rendered_copy"], chinese.copy)
            self.assertEqual(english.copy, english_copy_before)

    def test_validate_output_reports_automated_failures_and_manual_warnings(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "out.png"
            Image.new("RGBA", (100, 100), "white").save(output)
            report = validate_output(output_path=output, expected_dimensions=(2048, 2048), manifest={"rendered_copy": {}},
                                     brief=self._brief("Title", "Subtitle"), asset_hashes={"company_logo": ""}, output_type="logo_card",
                                     custom_ip_rights=["analysis_only"], logo_card_ip=["a", "b", "c", "d"])
            self.assertIsInstance(report, QAReport)
            self.assertFalse(report.passed)
            self.assertTrue(report.failures)
            self.assertIsInstance(report.warnings, tuple)

    def test_validate_output_rejects_wrong_dimensions(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "out.png"
            Image.new("RGBA", (100, 100), "white").save(output)
            report = validate_output(output_path=output, expected_dimensions=(2048, 2048), manifest={"rendered_copy": {"title": "Title", "subtitle": "Subtitle"}},
                                     brief=self._brief("Title", "Subtitle"), asset_hashes={"company_logo": "hash"}, output_type="logo_card")
            self.assertIn("dimensions", report.failures)

    def test_validate_output_covers_required_failure_modes(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "out.png"
            Image.new("RGBA", (2048, 2048), "white").save(output)
            base = {"rendered_copy": {"title": "wrong", "subtitle": "Subtitle"}}
            cases = (
                ({"company_logo": ""}, (), (), "company_logo_hash"),
                ({"company_logo": "hash"}, (), (), "manifest_copy"),
                ({"company_logo": "hash"}, (output,), (), "output_collision"),
                ({"company_logo": "hash"}, (), ("analysis_only",), "custom_ip_analysis_only"),
                ({"company_logo": "hash"}, (), (), "logo_card_ip_count"),
            )
            for hashes, existing, rights, failure in cases:
                manifest = base if failure == "manifest_copy" else {"rendered_copy": self._brief("Title", "Subtitle").copy}
                selected = ["a", "b", "c", "d"] if failure == "logo_card_ip_count" else ["a"]
                report = validate_output(output, expected_dimensions=(2048, 2048), manifest=manifest,
                                         brief=self._brief("Title", "Subtitle"), asset_hashes=hashes,
                                         existing_output_paths=existing, custom_ip_rights=rights,
                                         logo_card_ip=selected)
                self.assertIn(failure, report.failures)

    def test_manifest_copy_must_use_canonical_rendered_copy(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "out.png"
            Image.new("RGBA", (2048, 2048), "white").save(output)
            brief = self._brief("Title", "Subtitle")
            report = validate_output(output, manifest={"copy": brief.copy}, brief=brief, asset_hashes={"company_logo": "hash"})
            self.assertIn("manifest_copy", report.failures)

    def test_malformed_brief_is_a_qa_failure(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "out.png"
            Image.new("RGBA", (2048, 2048), "white").save(output)
            report = validate_output(output, manifest={"rendered_copy": {}}, brief={"copy": {}}, asset_hashes={"company_logo": "hash"})
            self.assertIn("brief_schema", report.failures)

    def test_social_preview_defaults_to_1280_by_640(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "social.png"
            Image.new("RGBA", (1280, 640), "white").save(output)
            report = validate_output(output, manifest={"rendered_copy": {}}, brief=self._brief("Title", "Subtitle"),
                                     asset_hashes={"company_logo": "hash"}, output_type="social-preview")
            self.assertTrue(report.checks["dimensions"])
            report2 = validate_output(output, manifest={"rendered_copy": {}}, brief=self._brief("Title", "Subtitle"),
                                      asset_hashes={"company_logo": "hash"}, output_type="social_preview")
            self.assertTrue(report2.checks["dimensions"])


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
