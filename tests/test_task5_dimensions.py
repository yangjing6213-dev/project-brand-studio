from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from brandloom.scripts.brandloom_core.models import BrandBrief
from brandloom.scripts.brandloom_core.prompt_builder import build_host_request, validate_generated_path


class Task5DimensionContractTests(unittest.TestCase):
    def _brief(self) -> BrandBrief:
        return BrandBrief(
            schema_version="1.0",
            project={"name": "Demo", "slug": "demo"},
            copy={"title": "Title"},
            style={"profile": "reference-adaptive"},
            fonts={},
            assets={},
            outputs={},
        )

    def test_host_generation_uses_approved_dimensions_and_rejects_historical_defaults(self) -> None:
        request = build_host_request(self._brief(), "logo_card")
        self.assertEqual(request["dimensions"], [1254, 1254])
        self.assertEqual(build_host_request(self._brief(), "cover")["dimensions"], [1774, 887])
        with TemporaryDirectory() as directory:
            old = Path(directory) / "old.png"
            Image.new("RGB", (2048, 2048), "white").save(old)
            with self.assertRaises(ValueError):
                validate_generated_path(old, expected="logo_card")
            old_cover = Path(directory) / "old-cover.png"
            Image.new("RGB", (2048, 1024), "white").save(old_cover)
            with self.assertRaises(ValueError):
                validate_generated_path(old_cover, expected="cover")


if __name__ == "__main__":
    unittest.main()
