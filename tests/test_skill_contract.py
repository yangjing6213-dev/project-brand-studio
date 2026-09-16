from pathlib import Path
import re
import unittest

from brandloom.scripts.brandloom_core.models import QAState

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

    def test_pending_prompts_require_visible_options_and_project_recommendation(self) -> None:
        workflow = (SKILL_ROOT / "references" / "qa-dialogue-workflow.md").read_text(encoding="utf-8")
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for text, phrase in (
            (workflow, "选项必须在同一条面向用户的消息中完整列出"),
            (workflow, "根据当前项目内容说明推荐理由"),
            (workflow, "用户只说继续但未选择选项时，必须重新显示选项"),
            (skill_text, "不得只写确认结论而省略选项"),
        ):
            self.assertIn(phrase, text)

    def test_every_pending_state_has_labeled_options_and_recommendation(self) -> None:
        workflow = (SKILL_ROOT / "references" / "qa-dialogue-workflow.md").read_text(encoding="utf-8")
        menu = workflow.split("## 菜单", 1)[1].split("## 失效矩阵", 1)[0]
        expected_labels = {
            "CONTEXT_CONFIRM_PENDING": "ABC",
            "COPY_DIRECTION_PENDING": "ABCDE",
            "STYLE_PENDING": "ABCDEF",
            "FONT_PENDING": "ABCDE",
            "COMPANY_LOGO_PENDING": "ABC",
            "PROJECT_MARK_PENDING": "ABC",
            "IP_CAST_PENDING": "ABCDE",
            "IP_COMBINATION_PENDING": "ABCDEFGH",
            "CUSTOM_IP_REFERENCE_PENDING": "ABC",
            "CUSTOM_IP_DRAFT_PENDING": "ABCD",
            "RIGHTS_CONFIRM_PENDING": "ABCDEF",
            "IP_USAGE_PENDING": "ABCDE",
            "SHOT_LIST_PENDING": "ABCDE",
            "OUTPUT_SPEC_PENDING": "ABCDEFG",
            "COHERENCE_REVIEW_PENDING": "ABCDE",
            "GENERATION_CONFIRM_PENDING": "ABCDE",
        }
        pending_states = tuple(item.value for item in QAState if item.value.endswith("_PENDING"))
        self.assertEqual(set(expected_labels), set(pending_states))
        for state in pending_states:
            match = re.search(
                rf"^- `{re.escape(state)}`：(?P<body>.*?)(?=^- `|\Z)",
                menu,
                flags=re.MULTILINE | re.DOTALL,
            )
            self.assertIsNotNone(match, state)
            body = match.group("body")
            labels = "".join(re.findall(r"(?<![A-Z])([A-Z])\.\s", body))
            self.assertEqual(labels, expected_labels[state], state)
            self.assertEqual(len(re.findall(r"（推荐）", body)), 1, state)
            self.assertRegex(body, r"[A-Z]\.\s[^；。\n]*（推荐）", state)
            self.assertIn("推荐理由", body, state)
            self.assertRegex(body, r"推荐理由：(?=[^。\n]*(?:项目|AI PPT|PPT|普通 AI 用户|LOGO|封面))[^。\n]+", state)

    def test_qa_message_contract_ends_with_explicit_choice_request(self) -> None:
        workflow = (SKILL_ROOT / "references" / "qa-dialogue-workflow.md").read_text(encoding="utf-8")
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("最后请用户回复选项字母", workflow)
        self.assertIn("最后请用户回复选项字母", skill_text)

    def test_company_logo_menu_preserves_rights_scope_and_treatment_contract(self) -> None:
        workflow = (SKILL_ROOT / "references" / "qa-dialogue-workflow.md").read_text(encoding="utf-8")
        body = re.search(r"^- `COMPANY_LOGO_PENDING`：(?P<body>.*?)(?=^- `|\Z)", workflow, flags=re.MULTILINE | re.DOTALL).group("body")
        for phrase in ("使用期限", "保存 scope", "default scope", "权利", "asset-add", ".brandloom/asset-manifest.json", "usage_term", "save_scope_confirmed", "confirmed.company_logo_treatment"):
            self.assertIn(phrase, body)

    def test_style_menu_lists_concrete_profiles_without_hidden_second_choice(self) -> None:
        workflow = (SKILL_ROOT / "references" / "qa-dialogue-workflow.md").read_text(encoding="utf-8")
        body = re.search(r"^- `STYLE_PENDING`：(?P<body>.*?)(?=^- `|\Z)", workflow, flags=re.MULTILINE | re.DOTALL).group("body")
        for profile in (
            "bright-saas-real-scene",
            "dark-neon-product",
            "high-density-commercial",
            "cinematic-monitor-hero",
            "editorial-minimal-grid",
            "soft-3d-brand-icon",
        ):
            self.assertIn(profile, body)
        self.assertNotIn("选择 A 后才可再选", body)

    def test_output_menu_uses_complete_mutually_exclusive_plans(self) -> None:
        workflow = (SKILL_ROOT / "references" / "qa-dialogue-workflow.md").read_text(encoding="utf-8")
        body = re.search(r"^- `OUTPUT_SPEC_PENDING`：(?P<body>.*?)(?=^- `|\Z)", workflow, flags=re.MULTILINE | re.DOTALL).group("body")
        for phrase in ("完整双语", "仅一张 LOGO", "仅一张封面", "自定义单画布", "自定义多输出包"):
            self.assertIn(phrase, body)
        self.assertNotIn("分别设置 LOGO 与封面", body)

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
        for option in ("GitHub Social Preview 1280x640", "logo-only", "cover-only", "bilingual", "自定义单画布", "自定义多输出包"):
            self.assertIn(option, workflow)
        self.assertIn("| 变更项 | 保留 | 必须重新确认 |", workflow)
        self.assertIn("| custom-IP-reference |", workflow)
        self.assertIn("| custom-IP-draft |", workflow)
        self.assertIn("保留", workflow)
        self.assertIn("必须重新确认", workflow)


if __name__ == "__main__":
    unittest.main()
