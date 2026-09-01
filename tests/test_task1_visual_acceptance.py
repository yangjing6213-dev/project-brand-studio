from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from brandloom.scripts.brandloom_core.models import BrandBrief
from brandloom.scripts.brandloom_core.renderer import BrandIntegrityError, render_brand_asset


class Task1VisualAcceptanceTests(unittest.TestCase):
    def _brief(self, title: str = "Hello BrandLoom", *, treatment: str | None = None) -> BrandBrief:
        assets = {"company_logo_treatment": treatment} if treatment is not None else {}
        return BrandBrief("1.0", {"name": "demo", "slug": "demo"},
                          {"title": title}, {"foreground": "#111111"}, {}, assets, {})

    def _fixtures(self, root: Path) -> tuple[Path, Path]:
        base = root / "base.png"
        Image.new("RGBA", (2048, 2048), "white").save(base)
        logo = root / "logo.png"
        image = Image.new("RGBA", (400, 100), (0, 0, 0, 0))
        for x in range(20, 380):
            for y in range(20, 80):
                image.putpixel((x, y), (220, 40, 120, 200))
        image.save(logo)
        return base, logo

    def _fonts(self) -> dict[str, Path]:
        windows = Path(r"C:\Windows\Fonts")
        return {"heading": windows / "msyh.ttc", "body": windows / "msyh.ttc"}

    def test_monochrome_black_preserves_source_hash_and_visible_bounds(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base, logo = self._fixtures(root)
            result = render_brand_asset(Path("brandloom/templates/logo-card-1x1.json"), self._brief(treatment="monochrome-black"),
                                        base_image=base, asset_paths={"company_logo": logo}, font_paths=self._fonts(), output_dir=root / "out")
            self.assertEqual(result.logo_treatment, "monochrome-black")
            self.assertEqual(result.source_hashes["company_logo"], hashlib.sha256(logo.read_bytes()).hexdigest())
            rendered = Image.open(result.output_path).convert("RGBA")
            pixels = [rendered.getpixel((x, y)) for x in range(140, 660) for y in range(120, 270)]
            dark = [pixel for pixel in pixels if pixel[0] < 40 and pixel[1] < 40 and pixel[2] < 40]
            self.assertTrue(dark)

    def test_unsupported_logo_treatment_fails_closed(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base, logo = self._fixtures(root)
            with self.assertRaises(BrandIntegrityError):
                render_brand_asset(Path("brandloom/templates/logo-card-1x1.json"), self._brief(treatment="neon"),
                                   base_image=base, asset_paths={"company_logo": logo}, font_paths=self._fonts(), output_dir=root / "out")

    def test_confirmed_font_missing_cjk_glyph_fails(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base, logo = self._fixtures(root)
            arial = Path(r"C:\Windows\Fonts\arial.ttf")
            with self.assertRaises(BrandIntegrityError):
                render_brand_asset(Path("brandloom/templates/logo-card-1x1.json"), self._brief("品牌标题"),
                                   base_image=base, asset_paths={"company_logo": logo},
                                   font_paths={"heading": arial}, output_dir=root / "out")

    def test_confirmed_cjk_font_renders_chinese_copy(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            base, logo = self._fixtures(root)
            msyh = Path(r"C:\Windows\Fonts\msyh.ttc")
            render_brand_asset(Path("brandloom/templates/logo-card-1x1.json"), self._brief("品牌标题"),
                               base_image=base, asset_paths={"company_logo": logo},
                               font_paths={"heading": msyh}, output_dir=root / "out")


if __name__ == "__main__":
    unittest.main()
