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

    def test_dialogue_workflow_covers_confirmation_states_and_rules(self) -> None:
        required = {
            "CONTEXT_CONFIRM_PENDING",
            "COPY_DIRECTION_PENDING",
            "STYLE_PENDING",
            "FONT_PENDING",
            "COMPANY_LOGO_PENDING",
            "PROJECT_MARK_PENDING",
            "IP_CAST_PENDING",
            "IP_USAGE_PENDING",
            "SHOT_LIST_PENDING",
            "OUTPUT_SPEC_PENDING",
            "COHERENCE_REVIEW_PENDING",
            "GENERATION_CONFIRM_PENDING",
            "GENERATION_READY",
        }
        workflow = (SKILL_ROOT / "references" / "qa-dialogue-workflow.md").read_text(encoding="utf-8")
        for state in required:
            self.assertIn(state, workflow)
        self.assertIn("一次只问一个问题", workflow)
        self.assertIn("推荐、默认、沉默和模型推断都不算确认", workflow)

    def test_skill_routes_generation_gate_to_host_image_tool(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("GENERATION_READY", skill_text)
        self.assertIn("host_builtin_image_tool", skill_text)

    def test_workflow_static_boundaries_and_menus(self) -> None:
        workflow = (SKILL_ROOT / "references" / "qa-dialogue-workflow.md").read_text(encoding="utf-8")
        style = (SKILL_ROOT / "references" / "style-presets.md").read_text(encoding="utf-8")
        for profile in (
            "bright-saas-real-scene",
            "dark-neon-product",
            "high-density-commercial",
            "cinematic-monitor-hero",
            "editorial-minimal-grid",
            "soft-3d-brand-icon",
        ):
            self.assertIn(profile, style)
        for operation in (
            "scale",
            "position",
            "recolor_monochrome",
            "opacity",
            "external_shadow",
            "redraw",
            "distort",
            "change_letterforms",
            "change_geometry",
            "use_as_training_reference",
        ):
            self.assertIn(operation, workflow)
        for phrase in ("当前 host 仅允许", "空返回路径", "不可用或调用失败", "不得自动重试"):
            self.assertIn(phrase, workflow)
        for option in ("GitHub Social Preview 1280x640", "logo-only", "cover-only", "bilingual", "custom dimensions"):
            self.assertIn(option, workflow)
        self.assertIn("| 变更项 | 保留 | 必须重新确认 |", workflow)
        self.assertIn("保留", workflow)
        self.assertIn("必须重新确认", workflow)


if __name__ == "__main__":
    unittest.main()
