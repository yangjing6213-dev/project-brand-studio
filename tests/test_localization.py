from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from brandloom.scripts.brandloom_core.manifests import build_generation_manifest
from brandloom.scripts.brandloom_core.models import BrandBrief
from brandloom.scripts.brandloom_core.renderer import render_brand_asset
from brandloom.scripts.brandloom_core.validation import QAReport, localize_brief, validate_output
from tests.font_test_utils import find_test_font


class LocalizationAndQATests(unittest.TestCase):
    def _font(self) -> Path:
        return find_test_font()

    def _brief(self, title: str, subtitle: str) -> BrandBrief:
        return BrandBrief("1.0", {"name": "demo", "slug": "demo"},
                          {"title": title, "subtitle": subtitle}, {"foreground": "#111111"},
                          {"heading": str(self._font()), "body": str(self._font())},
                          {"logo_card_ip": ["tuotuo"]}, {"logo_card": {"width": 1254, "height": 1254}})

    def _fixtures(self, root: Path) -> tuple[Path, Path, dict[str, Path]]:
        base = root / "base.png"
        Image.new("RGBA", (1254, 1254), "white").save(base)
        logo = root / "logo.png"
        Image.new("RGBA", (400, 100), (10, 80, 180, 255)).save(logo)
        return base, logo, {"company_logo": logo, "project_mark": logo}

    def _complete_manifest(
        self,
        root: Path,
        output: Path,
        brief: BrandBrief,
        *,
        rights_status: str = "user_authorized",
        asset_id: str = "enhe-natural-id",
    ) -> tuple[dict[str, object], dict[str, Path]]:
        brief_path = root / "brand-brief.json"
        brief_path.write_text(json.dumps(asdict(brief), ensure_ascii=False), encoding="utf-8")
        template = root / "template.json"
        template.write_text('{"schema_version":"1.0"}', encoding="utf-8")
        base = root / "base-source.png"
        Image.new("RGBA", output.size if isinstance(output, Image.Image) else (1254, 1254), "white").save(base)
        logo = root / "company-logo.png"
        Image.new("RGBA", (400, 100), (10, 80, 180, 255)).save(logo)
        font = self._font()
        manifest = build_generation_manifest(
            brief_path=brief_path,
            assets=[{
                "asset_id": asset_id,
                "category": "company-logo",
                "scope": "project",
                "rights_status": rights_status,
                "path": str(logo),
                "sha256": _sha(logo),
            }],
            template_path=template,
            font_paths={"heading": font, "body": font},
            base_image_path=base,
            output_path=output,
            qa_state="INTERNAL_LOGO_QA",
            rendered_copy=brief.copy,
            output_type="logo-card",
            host_request={"schema_version": "1.0", "backend": "host_builtin_image_tool", "output_type": "logo_card", "aspect_ratio": "1:1", "dimensions": [1254, 1254], "prompt": "fixture", "reference_assets": []},
        )
        return manifest, {"brief": brief_path, "template": template, "base": base, "logo": logo, "font": font}

    def test_localization_reuses_hashes_and_preserves_english(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base, logo, assets = self._fixtures(root)
            english = self._brief("Brand title", "English subtitle")
            english_copy_before = dict(english.copy)
            chinese = localize_brief(english, language="zh-CN", copy={"title": "品牌标题", "subtitle": "中文副标题"})
            en = render_brand_asset(Path("brandloom/templates/logo-card-1x1.json"), english, base_image=base, asset_paths=assets,
                                    font_paths={"heading": self._font(), "body": self._font()}, output_dir=root / "en")
            # CJK acceptance requires an explicitly selected capable font.
            msyh = Path(r"C:\Windows\Fonts\msyh.ttc")
            if not msyh.is_file():
                self.skipTest("Microsoft YaHei is not installed on this platform")
            chinese = BrandBrief(chinese.schema_version, chinese.project, chinese.copy, chinese.style,
                                 {"heading": str(msyh), "body": str(msyh)}, chinese.assets, chinese.outputs)
            zh = render_brand_asset(Path("brandloom/templates/logo-card-1x1.json"), chinese, base_image=base, asset_paths=assets,
                                    font_paths={"heading": msyh, "body": msyh}, output_dir=root / "zh")
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
            self.assertEqual(chinese.copy["language"], "zh-CN")
            self.assertNotIn("language", chinese.project)

    def test_validate_output_reports_automated_failures_and_manual_warnings(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "out.png"
            Image.new("RGBA", (100, 100), "white").save(output)
            report = validate_output(output_path=output, expected_dimensions=(1254, 1254), manifest={"rendered_copy": {}},
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
            report = validate_output(output_path=output, expected_dimensions=(1254, 1254), manifest={"rendered_copy": {"title": "Title", "subtitle": "Subtitle"}},
                                     brief=self._brief("Title", "Subtitle"), asset_hashes={"company_logo": "hash"}, output_type="logo_card")
            self.assertIn("dimensions", report.failures)

    def test_validate_output_covers_required_failure_modes(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "out.png"
            Image.new("RGBA", (1254, 1254), "white").save(output)
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
                report = validate_output(output, expected_dimensions=(1254, 1254), manifest=manifest,
                                         brief=self._brief("Title", "Subtitle"), asset_hashes=hashes,
                                         existing_output_paths=existing, custom_ip_rights=rights,
                                         logo_card_ip=selected)
                self.assertIn(failure, report.failures)

    def test_manifest_copy_must_use_canonical_rendered_copy(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "out.png"
            Image.new("RGBA", (1254, 1254), "white").save(output)
            brief = self._brief("Title", "Subtitle")
            report = validate_output(output, manifest={"copy": brief.copy}, brief=brief, asset_hashes={"company_logo": "hash"})
            self.assertIn("manifest_copy", report.failures)

    def test_malformed_brief_is_a_qa_failure(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "out.png"
            Image.new("RGBA", (1254, 1254), "white").save(output)
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

    def test_complete_manifest_uses_category_rights_and_expected_observed_asset_hashes(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "logo-card-1x1-v01.png"
            Image.new("RGBA", (1254, 1254), "white").save(output)
            brief = self._brief("Title", "Subtitle")
            manifest, paths = self._complete_manifest(root, output, brief)
            asset = manifest["assets"][0]
            self.assertEqual(asset["asset_id"], "enhe-natural-id")
            self.assertEqual(asset["category"], "company-logo")
            self.assertEqual(asset["scope"], "project")
            self.assertEqual(asset["rights_status"], "user_authorized")
            self.assertEqual(asset["expected_sha256"], _sha(paths["logo"]))
            self.assertEqual(asset["observed_sha256"], _sha(paths["logo"]))
            report = validate_output(
                output,
                manifest=manifest,
                brief=brief,
                brief_path=paths["brief"],
                output_root=root,
                output_type="logo_card",
            )
            self.assertTrue(report.passed, report.failures)
            self.assertTrue(report.checks["company_logo_hash"])

    def test_complete_manifest_output_collision_is_only_new_failure(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "logo-card-1x1-v01.png"
            Image.new("RGBA", (1254, 1254), "white").save(output)
            brief = self._brief("Title", "Subtitle")
            manifest, paths = self._complete_manifest(root, output, brief)
            baseline = validate_output(output, manifest=manifest, brief=brief, brief_path=paths["brief"], output_root=root, output_type="logo_card")
            self.assertTrue(baseline.passed, baseline.failures)
            collided = validate_output(output, manifest=manifest, brief=brief, brief_path=paths["brief"], output_root=root, output_type="logo_card", existing_output_paths=[output])
            self.assertFalse(collided.passed)
            self.assertEqual(collided.failures, ("output_collision",))

    def test_manifest_integrity_rehashes_every_recorded_input_and_output(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "logo-card-1x1-v01.png"
            Image.new("RGBA", (1254, 1254), "white").save(output)
            brief = self._brief("Title", "Subtitle")
            manifest, paths = self._complete_manifest(root, output, brief)
            for key, check in (
                ("brief", "manifest_brief"),
                ("template", "manifest_template"),
                ("base", "manifest_base_image"),
                ("logo", "manifest_assets"),
            ):
                with self.subTest(key=key):
                    original = paths[key].read_bytes()
                    paths[key].write_bytes(original + b"tampered")
                    report = validate_output(
                        output,
                        manifest=manifest,
                        brief=brief,
                        brief_path=paths["brief"],
                        output_root=root,
                        output_type="logo_card",
                    )
                    self.assertFalse(report.checks[check])
                    paths[key].write_bytes(original)

            original_output = output.read_bytes()
            Image.new("RGBA", (1254, 1254), "black").save(output)
            report = validate_output(
                output,
                manifest=manifest,
                brief=brief,
                brief_path=paths["brief"],
                output_root=root,
                output_type="logo_card",
            )
            self.assertFalse(report.checks["manifest_output"])
            output.write_bytes(original_output)

            font_entry = manifest["fonts"]["heading"]
            font_entry["sha256"] = "0" * 64
            report = validate_output(
                output,
                manifest=manifest,
                brief=brief,
                brief_path=paths["brief"],
                output_root=root,
                output_type="logo_card",
            )
            self.assertFalse(report.checks["manifest_fonts"])

    def test_qa_fully_decodes_png_and_requires_rgb_or_rgba(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brief = self._brief("Title", "Subtitle")
            output = root / "logo-card-1x1-v01.png"
            Image.new("RGBA", (1254, 1254), "white").save(output)
            manifest, paths = self._complete_manifest(root, output, brief)
            output.write_bytes(output.read_bytes()[:-64])
            report = validate_output(
                output,
                manifest=manifest,
                brief=brief,
                brief_path=paths["brief"],
                output_root=root,
                output_type="logo_card",
            )
            self.assertFalse(report.checks["png_decode"])

            palette = root / "palette-v01.png"
            Image.new("P", (1254, 1254)).save(palette)
            palette_manifest, palette_paths = self._complete_manifest(root, palette, brief)
            report = validate_output(
                palette,
                manifest=palette_manifest,
                brief=brief,
                brief_path=palette_paths["brief"],
                output_root=root,
                output_type="logo_card",
            )
            self.assertFalse(report.checks["color_mode"])

    def test_manifest_output_path_must_match_and_output_must_be_versioned_and_contained(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "logo-card-1x1.png"
            other = root / "other-v01.png"
            Image.new("RGBA", (1254, 1254), "white").save(output)
            Image.new("RGBA", (1254, 1254), "white").save(other)
            brief = self._brief("Title", "Subtitle")
            manifest, paths = self._complete_manifest(root, output, brief)
            report = validate_output(
                other,
                manifest=manifest,
                brief=brief,
                brief_path=paths["brief"],
                output_root=root,
                output_type="logo_card",
            )
            self.assertFalse(report.checks["output_manifest_path"])
            report = validate_output(
                output,
                manifest=manifest,
                brief=brief,
                brief_path=paths["brief"],
                output_root=root,
                output_type="logo_card",
            )
            self.assertFalse(report.checks["versioned_output"])

            outside = root.parent / "outside-v01.png"
            try:
                Image.new("RGBA", (1254, 1254), "white").save(outside)
                outside_manifest, outside_paths = self._complete_manifest(root, outside, brief)
                report = validate_output(
                    outside,
                    manifest=outside_manifest,
                    brief=brief,
                    brief_path=outside_paths["brief"],
                    output_root=root,
                    output_type="logo_card",
                )
                self.assertFalse(report.checks["output_contained"])
            finally:
                outside.unlink(missing_ok=True)

    def test_non_authorized_manifest_asset_fails_closed(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "logo-card-1x1-v01.png"
            Image.new("RGBA", (1254, 1254), "white").save(output)
            brief = self._brief("Title", "Subtitle")
            manifest, paths = self._complete_manifest(root, output, brief, rights_status="unknown")
            report = validate_output(
                output,
                manifest=manifest,
                brief=brief,
                brief_path=paths["brief"],
                output_root=root,
                output_type="logo_card",
            )
            self.assertFalse(report.checks["manifest_assets"])
            self.assertFalse(report.checks["company_logo_hash"])


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    unittest.main()
