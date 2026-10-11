from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_IMAGES = (
    "docs/examples/brandloom-host-logo-card-1254x1254.png",
    "docs/examples/brandloom-host-cover-1774x887.png",
)


def _yaml_string(text: str, key: str) -> str:
    match = re.search(rf"^[ \t]*{re.escape(key)}:[ \t]*\"([^\"]*)\"[ \t]*$", text, re.MULTILINE)
    if match is None:
        raise AssertionError(f"missing quoted YAML scalar: {key}")
    return match.group(1)


class DocumentationContractTests(unittest.TestCase):
    def test_marketplace_copy_matches_cover_only_workflow(self) -> None:
        listing = (ROOT / "docs" / "marketplace-listing.md").read_text(encoding="utf-8")
        architecture = (ROOT / "brandloom" / "references" / "architecture.md").read_text(encoding="utf-8")

        self.assertNotIn("logo cards", listing)
        self.assertNotIn("logo-first", listing)
        self.assertNotIn("LOGO 主视觉", listing)
        self.assertIn("适配平台的项目封面", listing)
        self.assertNotIn("方形 LOGO 主视觉与封面必须", architecture)
        self.assertIn("所有平台封面", architecture)

    def test_skill_ui_metadata_matches_current_cover_only_workflow(self) -> None:
        metadata = (ROOT / "brandloom" / "agents" / "openai.yaml").read_text(encoding="utf-8")
        short_description = _yaml_string(metadata, "short_description")
        default_prompt = _yaml_string(metadata, "default_prompt")

        self.assertGreaterEqual(len(short_description), 25)
        self.assertLessEqual(len(short_description), 64)
        self.assertIn("多平台", short_description)
        self.assertIn("封面", short_description)
        self.assertNotIn("方形", short_description + default_prompt)
        self.assertNotIn("LOGO", short_description + default_prompt)
        self.assertTrue(default_prompt.startswith("Use $brandloom"))

    def test_bilingual_readmes_show_the_two_human_reviewed_examples_in_order(self) -> None:
        for readme_name in ("README.md", "README.en.md"):
            text = (ROOT / readme_name).read_text(encoding="utf-8")
            heading, next_heading = (
                ("## 五、示例效果", "## 六、安装方法")
                if readme_name == "README.md"
                else ("## 5. Example results", "## 6. Installation")
            )
            section = text.split(heading, 1)[1].split(next_heading, 1)[0]
            positions = [section.find(image) for image in EXAMPLE_IMAGES]
            self.assertTrue(all(position >= 0 for position in positions), readme_name)
            self.assertEqual(positions, sorted(positions), readme_name)
            self.assertIn("1254", section)
            self.assertIn("1774", section)

    def test_readme_cover_images_have_accurate_publication_provenance(self) -> None:
        for source_filename, image_relative in zip(
            ("cover-2x1-v07.png", "cover-2x1-v10.png"),
            ("docs/examples/cover-2x1-v07-zh.png", "docs/examples/cover-2x1-v10-en.png"),
        ):
            image_path = ROOT / image_relative
            provenance_path = image_path.with_name(f"{image_path.stem}.provenance.json")
            self.assertTrue(provenance_path.is_file(), str(provenance_path))
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            actual_hash = hashlib.sha256(image_path.read_bytes()).hexdigest()
            self.assertEqual(provenance["source_filename"], source_filename)
            self.assertEqual(provenance["sha256"], actual_hash)
            self.assertEqual(provenance["authorization_status"], "user_authorized")
            self.assertEqual(provenance["distribution_scope"], "public_repository_documentation")


if __name__ == "__main__":
    unittest.main()
