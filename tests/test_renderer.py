from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from brandloom.scripts.brandloom_core.models import BrandBrief
from brandloom.scripts.brandloom_core.renderer import (
    BrandIntegrityError,
    TextOverflowError,
    render_brand_asset,
)
from tests.font_test_utils import find_test_font


class RendererTests(unittest.TestCase):
    def _brief(self, title: str = "Hello BrandLoom") -> BrandBrief:
        return BrandBrief(
            schema_version="1.0",
            project={"name": "demo", "slug": "demo"},
            copy={"title": title, "subtitle": "A deterministic brand system", "body": ""},
            style={"background": "#ffffff", "foreground": "#111111"},
            fonts={},
            assets={},
            outputs={},
        )

    def _font(self) -> Path:
        return find_test_font()

    def _fixtures(self, root: Path) -> tuple[Path, Path]:
        base = root / "base.png"
        Image.new("RGBA", (1254, 1254), (255, 255, 255, 255)).save(base)
        logo = root / "logo.png"
        image = Image.new("RGBA", (400, 100), (0, 0, 0, 0))
        for x in range(20, 380):
            for y in range(20, 80):
                image.putpixel((x, y), (10, 80, 180, 255))
        image.save(logo)
        return base, logo

    def test_logo_card_dimensions_and_source_hashes(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base, logo = self._fixtures(root)
            result = render_brand_asset(
                Path("brandloom/templates/logo-card-1x1.json"),
                self._brief(),
                base_image=base,
                asset_paths={"company_logo": logo, "project_mark": logo},
                font_paths={"heading": self._font(), "body": self._font()},
                output_dir=root / "out",
            )
            self.assertEqual((result.width, result.height), (1254, 1254))
            self.assertTrue(result.output_path.is_file())
            self.assertIn("company_logo", result.source_hashes)

    def test_cover_dimensions(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _square_base, logo = self._fixtures(root)
            base = root / "cover-base.png"
            Image.new("RGBA", (1774, 887), (255, 255, 255, 255)).save(base)
            cover = render_brand_asset(
                Path("brandloom/templates/cover-2x1.json"),
                self._brief(),
                base_image=base,
                asset_paths={"company_logo": logo, "project_mark": logo},
                font_paths={"heading": self._font(), "body": self._font()},
                output_dir=root / "out",
            )
        self.assertEqual((cover.width, cover.height), (1774, 887))

    def test_base_dimension_mismatch_is_rejected_before_render(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base, logo = self._fixtures(root)
            with self.assertRaises(BrandIntegrityError):
                render_brand_asset(
                    Path("brandloom/templates/cover-2x1.json"),
                    self._brief(),
                    base_image=base,
                    asset_paths={"company_logo": logo},
                    font_paths={"heading": self._font(), "body": self._font()},
                    output_dir=root / "out",
                )

    def test_custom_template_canvas_is_supported_only_by_explicit_local_renderer(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "custom-template.json"
            template.write_text(
                json.dumps({"schema_version": "1.0", "canvas": {"width": 1000, "height": 500}, "slots": {}}),
                encoding="utf-8",
            )
            base = root / "custom-base.png"
            Image.new("RGBA", (1000, 500), (240, 240, 240, 255)).save(base)
            result = render_brand_asset(
                template,
                {"copy": {}, "style": {}, "assets": {}},
                base_image=base,
                asset_paths={},
                font_paths={},
                output_dir=root / "out",
            )
            self.assertEqual((result.width, result.height), (1000, 500))
            with Image.open(result.output_path) as image:
                self.assertEqual(image.size, (1000, 500))

    def test_long_title_raises_text_overflow(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base, logo = self._fixtures(root)
            with self.assertRaises(TextOverflowError):
                render_brand_asset(
                    Path("brandloom/templates/logo-card-1x1.json"),
                    self._brief("x " * 1000),
                    base_image=base,
                    asset_paths={"company_logo": logo, "project_mark": logo},
                    font_paths={"heading": self._font(), "body": self._font()},
                    output_dir=root / "out",
                )

    def test_logo_aspect_ratio_is_preserved(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base, logo = self._fixtures(root)
            result = render_brand_asset(
                Path("brandloom/templates/logo-card-1x1.json"),
                self._brief(),
                base_image=base,
                asset_paths={"company_logo": logo, "project_mark": logo},
                font_paths={"heading": self._font(), "body": self._font()},
                output_dir=root / "out",
            )
        self.assertAlmostEqual(result.logo_size[0] / result.logo_size[1], 4.0, delta=0.03)

    def test_existing_output_is_versioned_without_overwrite(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base, logo = self._fixtures(root)
            first = render_brand_asset(
                Path("brandloom/templates/logo-card-1x1.json"),
                self._brief(),
                base_image=base,
                asset_paths={"company_logo": logo, "project_mark": logo},
                font_paths={"heading": self._font(), "body": self._font()},
                output_dir=root / "out",
            )
            original = first.output_path.read_bytes()
            second = render_brand_asset(
                Path("brandloom/templates/logo-card-1x1.json"),
                self._brief(),
                base_image=base,
                asset_paths={"company_logo": logo, "project_mark": logo},
                font_paths={"heading": self._font(), "body": self._font()},
                output_dir=root / "out",
            )
            self.assertTrue(first.output_path.name.endswith("-v01.png"))
            self.assertTrue(second.output_path.name.endswith("-v02.png"))
            self.assertEqual(first.output_path.read_bytes(), original)

    def test_body_font_does_not_silently_fall_back_to_heading(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base, logo = self._fixtures(root)
            with self.assertRaises(BrandIntegrityError):
                render_brand_asset(
                    Path("brandloom/templates/logo-card-1x1.json"),
                    self._brief(),
                    base_image=base,
                    asset_paths={"company_logo": logo},
                    font_paths={"heading": self._font()},
                    output_dir=root / "out",
                )

    def test_value_line_and_features_are_rendered_and_audited(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _square_base, logo = self._fixtures(root)
            base = root / "cover-base.png"
            Image.new("RGBA", (1774, 887), (255, 255, 255, 255)).save(base)
            brief = self._brief()
            brief = BrandBrief(
                brief.schema_version,
                brief.project,
                {
                    "language": "en",
                    "title": "Hello BrandLoom",
                    "subtitle": "A deterministic brand system",
                    "value_line": "Confirm before generation",
                    "features": ["Traceable assets", "No overwrite"],
                },
                brief.style,
                brief.fonts,
                brief.assets,
                brief.outputs,
            )
            result = render_brand_asset(
                Path("brandloom/templates/cover-2x1.json"),
                brief,
                base_image=base,
                asset_paths={"company_logo": logo},
                font_paths={"heading": self._font(), "body": self._font()},
                output_dir=root / "out",
            )
            self.assertEqual(
                result.rendered_copy,
                {
                    "title": "Hello BrandLoom",
                    "subtitle": "A deterministic brand system",
                    "value_line": "Confirm before generation",
                    "features": ["Traceable assets", "No overwrite"],
                },
            )

    def test_unknown_nonempty_copy_field_hard_stops(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base, logo = self._fixtures(root)
            brief = self._brief()
            brief = BrandBrief(
                brief.schema_version,
                brief.project,
                {**brief.copy, "cta": "Buy now"},
                brief.style,
                brief.fonts,
                brief.assets,
                brief.outputs,
            )
            with self.assertRaises(BrandIntegrityError):
                render_brand_asset(
                    Path("brandloom/templates/logo-card-1x1.json"),
                    brief,
                    base_image=base,
                    asset_paths={"company_logo": logo},
                    font_paths={"heading": self._font(), "body": self._font()},
                    output_dir=root / "out",
                )

    def test_templates_are_json_and_social_preview_is_2x1(self) -> None:
        for name in ("logo-card-1x1.json", "cover-2x1.json", "social-preview-2x1.json"):
            payload = json.loads((Path("brandloom/templates") / name).read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "1.0")
            self.assertEqual(payload["canvas"]["width"] / payload["canvas"]["height"], 2 if "2x1" in name else 1)


if __name__ == "__main__":
    unittest.main()
