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
            "creator-desk-handwritten",
            "stage-screen-poster",
            "light-saas-product-showcase",
            "project-existing-style",
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
        for option in (
            "YouTube 长视频缩略图",
            "YouTube Shorts 封面",
            "YouTube 频道横幅",
            "抖音作品封面",
            "小红书笔记封面",
            "GitHub Social Preview",
            "自定义尺寸",
        ):
            self.assertIn(option, workflow)
        self.assertIn("| 变更项 | 保留 | 必须重新确认 |", workflow)
        self.assertIn("| custom-IP-reference |", workflow)
        self.assertIn("| custom-IP-draft |", workflow)
        self.assertIn("保留", workflow)
        self.assertIn("必须重新确认", workflow)

    def test_visual_style_qa_has_four_reference_branches_and_conditional_gates(self) -> None:
        workflow = (SKILL_ROOT / "references" / "qa-dialogue-workflow.md").read_text(encoding="utf-8")
        style = (SKILL_ROOT / "references" / "style-presets.md").read_text(encoding="utf-8")
        assets = (SKILL_ROOT / "references" / "brand-assets.md").read_text(encoding="utf-8")
        rights = (SKILL_ROOT / "references" / "rights-and-provenance.md").read_text(encoding="utf-8")
        for required in (
            "创作者桌面手写标题",
            "演讲舞台大屏海报",
            "明亮 SaaS 产品展示",
            "沿用当前项目已有风格",
            "选择 A/B 后必须出现独立的人物素材问题",
            "选择 B 时，在人物素材可用后分轮追加两个独立问题",
            "标题颜色：固定基础色为白色",
            "除主标题外的副标题、说明和卖点排入展示大屏",
            "没有可复用的 D 类依据时",
        ):
            self.assertIn(required, workflow)
        self.assertIn("主讲人物和展示大屏必须同时清晰出现", style)
        self.assertIn("`.brandloom/style-reference-library/`", style)
        self.assertIn("本地参考图库可用时，默认附带所选风格对应的图", style)
        self.assertIn("不进入提交、ZIP 或公开发行包", style)
        self.assertIn("person-reference", assets)
        self.assertIn("默认推荐仅本次使用、不设默认", assets)
        self.assertIn("确认自己拥有使用权或已取得人物/权利人的必要授权", rights)
        self.assertIn("不得复制图中人物身份、原文字、商标、产品界面、水印或账号信息", rights)

    def test_platform_cover_qa_replaces_logo_first_flow(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        workflow = (SKILL_ROOT / "references" / "qa-dialogue-workflow.md").read_text(encoding="utf-8")
        recipes = (SKILL_ROOT / "references" / "composition-recipes.md").read_text(encoding="utf-8")
        combined = skill_text + "\n" + workflow
        self.assertIn("OUTPUT_TARGET_PENDING", workflow)
        self.assertIn("OUTPUT_SPEC_PENDING", workflow)
        self.assertLess(workflow.index("OUTPUT_TARGET_PENDING"), workflow.index("COPY_DIRECTION_PENDING"))
        self.assertLess(workflow.index("OUTPUT_SPEC_PENDING"), workflow.index("COPY_DIRECTION_PENDING"))
        self.assertIn("使用 A/B/C 等标签", workflow)
        self.assertIn("并标注“推荐”", workflow)
        self.assertIn("YouTube", workflow)
        self.assertIn("抖音", workflow)
        self.assertIn("小红书", workflow)
        self.assertIn("GitHub", workflow)
        self.assertIn("自定义尺寸", workflow)
        self.assertIn("品牌统一、版式适配", workflow)
        self.assertIn("按各平台重做构图", workflow)
        self.assertIn("同一核心卖点、按平台调整文案长度和信息量", workflow)
        self.assertIn("每个平台按目标读者选择一种语言", workflow)
        self.assertIn("记录到 `brand-brief.json` 的 `outputs.targets`", workflow)
        self.assertIn("同一场景主题、每种画幅单独重构镜头", workflow)
        self.assertIn("真实场景描述写入各目标的 `scene_concept`", workflow)
        self.assertIn("宽版最多 4 步", workflow)
        self.assertIn("竖版或小画幅最多 3 步", workflow)
        self.assertIn("卡片用细线边框和约 60% 不透明度（约 40% 透明）的局部磨砂底", workflow)
        self.assertIn("不模糊整张图、不加流程图外框", workflow)
        self.assertIn("圆角平滑，文字与边框留足距离", workflow)
        self.assertIn("真实场景背景铺满画面", recipes)
        self.assertIn("文案允许覆盖在背景上", recipes)
        self.assertIn("不对整张背景加模糊层", recipes)
        self.assertIn("不生成 1:1 LOGO 方形图", skill_text)
        for obsolete_step in ("GENERATE_LOGO_BASE", "COMPOSE_LOGO_CARD", "LOGO_USER_REVIEW"):
            self.assertNotIn(obsolete_step, combined)
        self.assertNotIn("LOGO-first", skill_text)

    def test_user_facing_qa_uses_visible_options_and_project_specific_recommendation(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        workflow = (SKILL_ROOT / "references" / "qa-dialogue-workflow.md").read_text(encoding="utf-8")
        self.assertIn("提问模板", workflow)
        self.assertIn("本次只确认一个问题", workflow)
        self.assertIn("A.", workflow)
        self.assertIn("（推荐）", workflow)
        self.assertIn("结合已分析的项目内容和目标用途", workflow)
        self.assertIn("明确说明推荐理由", workflow)
        self.assertIn("多选时明确说明可以多选", workflow)
        self.assertIn("展示 A/B/C 等明确选项和实际差别", skill_text)
        self.assertIn("根据已分析的项目内容与目标用途选择", skill_text)

    def test_platform_specs_label_official_requirements_and_recommendations(self) -> None:
        specs = (SKILL_ROOT / "references" / "output-specs.md").read_text(encoding="utf-8")
        for required_item in (
            "3840×2160",
            "2160×3840",
            "2560×1440",
            "1235×338",
            "1080×1440",
            "1280×640",
            "抖音",
            "不是抖音官方公布的固定像素要求",
            "自定义尺寸",
            "自定义 Shorts 缩略图需账号已验证，并只能在电脑端通过 YouTube Studio 添加",
            "公开图片上传接口没有规定作品封面的固定像素尺寸",
            "1280×640",
            "小于 1 MB",
            "超限会阻止交付",
        ):
            self.assertIn(required_item, specs)

    def test_platform_base_image_policy_forbids_crop_and_cross_ratio_resize(self) -> None:
        specs = (SKILL_ROOT / "references" / "output-specs.md").read_text(encoding="utf-8")
        workflow = (SKILL_ROOT / "references" / "qa-dialogue-workflow.md").read_text(encoding="utf-8")
        self.assertIn("底图与目标画幅比例完全相同时，才允许在内存中按比例缩放", specs)
        self.assertIn("比例不一致时停止", specs)
        self.assertIn("不得裁切", specs)
        self.assertIn("底图与目标画幅比例完全相同时", workflow)
        self.assertIn("比例不一致时必须停止", workflow)


if __name__ == "__main__":
    unittest.main()
