from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from brandloom.scripts import brandloom_cli


class PipelineTests(unittest.TestCase):
    def _font(self) -> Path:
        for path in (Path(r"C:\Windows\Fonts\arial.ttf"), Path(r"C:\Windows\Fonts\segoeui.ttf")):
            if path.is_file():
                return path
        self.skipTest("Windows font fixture unavailable")

    def _asset(self, root: Path, name: str, size: tuple[int, int], color: tuple[int, int, int, int]) -> Path:
        path = root / name
        Image.new("RGBA", size, color).save(path)
        return path

    def test_local_cli_pipeline_versions_outputs_and_manifest(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(brandloom_cli.main(["init", "--workspace", str(root)]), 0)
            logo = self._asset(root, "logo.png", (400, 100), (10, 80, 180, 255))
            mark = self._asset(root, "mark.png", (200, 200), (220, 160, 10, 255))
            self.assertEqual(brandloom_cli.main([
                "asset-add", "--workspace", str(root), "--source", str(logo),
                "--category", "company-logo", "--scope", "project",
                "--rights", "user_authorized", "--save-confirmed", "--make-default",
            ]), 0)
            self.assertEqual(brandloom_cli.main([
                "asset-add", "--workspace", str(root), "--source", str(mark),
                "--category", "project-mark", "--scope", "project",
                "--rights", "user_authorized", "--save-confirmed", "--make-default",
            ]), 0)
            brief = {
                "schema_version": "1.0",
                "project": {"name": "Demo", "slug": "demo"},
                "copy": {"title": "Demo Brand", "subtitle": "Local pipeline"},
                "style": {"foreground": "#111111"},
                "fonts": {"heading": str(self._font()), "body": str(self._font())},
                "assets": {},
                "outputs": {},
            }
            (root / ".brandloom" / "brand-brief.json").write_text(json.dumps(brief), encoding="utf-8")
            qa = {"state": "GENERATION_READY", "confirmed": {
                key: True for key in ("context", "copy", "style", "font", "company_logo", "project_mark",
                                      "ip_cast", "ip_combination", "ip_usage", "shot_list", "output_spec",
                                      "coherence", "generation_confirmation")}}
            (root / ".brandloom" / "qa-state.json").write_text(json.dumps(qa), encoding="utf-8")
            base = self._asset(root, "base.png", (2048, 2048), (245, 245, 245, 255))
            self.assertEqual(brandloom_cli.main([
                "compose", "--workspace", str(root), "--type", "logo-card",
                "--base", str(base), "--test-fixture",
            ]), 0)
            output_dir = root / ".brandloom" / "outputs" / "demo"
            first = sorted(output_dir.glob("*.png"))
            self.assertTrue(first)
            self.assertTrue((output_dir / "generation-manifest-v01.json").is_file())
            self.assertEqual(brandloom_cli.main([
                "validate", "--workspace", str(root), "--type", "logo-card",
            ]), 0)
            self.assertEqual(brandloom_cli.main([
                "compose", "--workspace", str(root), "--type", "logo-card",
                "--base", str(base), "--test-fixture",
            ]), 0)
            self.assertTrue((output_dir / "generation-manifest-v02.json").is_file())

    def test_asset_add_requires_save_confirmation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brandloom_cli.main(["init", "--workspace", str(root)])
            source = self._asset(root, "logo.png", (32, 16), (1, 2, 3, 255))
            self.assertEqual(brandloom_cli.main([
                "asset-add", "--workspace", str(root), "--source", str(source),
                "--category", "company-logo", "--scope", "project", "--rights", "user_authorized",
            ]), 2)

    def test_compose_rejects_base_with_wrong_output_dimensions(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brandloom_cli.main(["init", "--workspace", str(root)])
            logo = self._asset(root, "logo.png", (40, 20), (1, 2, 3, 255))
            mark = self._asset(root, "mark.png", (20, 20), (4, 5, 6, 255))
            for source, category in ((logo, "company-logo"), (mark, "project-mark")):
                brandloom_cli.main(["asset-add", "--workspace", str(root), "--source", str(source), "--category", category,
                                    "--scope", "project", "--rights", "user_authorized", "--save-confirmed", "--make-default"])
            brief = {"schema_version": "1.0", "project": {"name": "Demo", "slug": "other"},
                     "copy": {"title": "Title"}, "style": {}, "fonts": {"heading": str(self._font())}, "assets": {}, "outputs": {}}
            (root / ".brandloom" / "brand-brief.json").write_text(json.dumps(brief), encoding="utf-8")
            Image.new("RGBA", (2048, 2048), "white").save(root / "base.png")
            with self.assertRaises(ValueError):
                brandloom_cli.main(["compose", "--workspace", str(root), "--type", "cover", "--base", str(root / "base.png"), "--test-fixture"])

    def test_validate_uses_brief_slug_and_manifest_relative_paths(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brandloom_cli.main(["init", "--workspace", str(root)])
            brief = {"schema_version": "1.0", "project": {"name": "Demo", "slug": "other"},
                     "copy": {}, "style": {}, "fonts": {}, "assets": {}, "outputs": {}}
            (root / ".brandloom" / "brand-brief.json").write_text(json.dumps(brief), encoding="utf-8")
            output_dir = root / ".brandloom" / "outputs" / "other"
            output_dir.mkdir(parents=True)
            image = output_dir / "logo-card-1x1.png"
            Image.new("RGBA", (2048, 2048), "white").save(image)
            (output_dir / "generation-manifest-v01.json").write_text(json.dumps({"output": {"path": "logo-card-1x1.png"}}), encoding="utf-8")
            self.assertEqual(brandloom_cli.main(["validate", "--workspace", str(root), "--type", "logo-card"]), 0)

    def test_state_confirm_rejects_unknown_state(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            brandloom_cli.main(["init", "--workspace", str(root)])
            self.assertEqual(brandloom_cli.main(["state-confirm", "--workspace", str(root), "--state", "NOT_A_STATE"]), 2)


if __name__ == "__main__":
    unittest.main()
