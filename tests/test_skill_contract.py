from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "brandloom"


class SkillContractTests(unittest.TestCase):
    def test_front_matter_and_agent_metadata(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill_text.startswith("---\n"))
        self.assertIn("name: brandloom", skill_text)
        agent_text = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "BrandLoom"', agent_text)
        self.assertIn("Use $brandloom", agent_text)

    def test_all_referenced_markdown_files_exist(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        references = sorted(set(re.findall(r"references/[A-Za-z0-9_.-]+[.]md", skill_text)))
        self.assertTrue(references)
        for reference in references:
            self.assertTrue((SKILL_ROOT / reference).is_file(), reference)

    def test_runtime_dependency_is_pinned(self) -> None:
        requirements = (ROOT / "requirements-runtime.txt").read_text(encoding="utf-8")
        self.assertEqual(requirements.strip(), "Pillow==12.3.0")


if __name__ == "__main__":
    unittest.main()
