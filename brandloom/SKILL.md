---
name: brandloom
description: 用于分析项目、对话、附件、链接和品牌素材，并通过确认式 QA 生成或修改项目 LOGO 主视觉、项目标志、GitHub 封面、中英文版本和品牌视觉变体。
---

# BrandLoom

先读取 `references/architecture.md`，再根据当前阶段按需读取参考文件；不要一次加载完整参考库。任何生成或改图请求都必须先完成确认式 QA，只有 `qa_state = GENERATION_READY` 且用户明确确认后，才可调用 `host_builtin_image_tool`。

## 任务路由

- `analysis-only`：只分析可访问上下文，读取 `context-analysis.md`，交付证据、推断和未确认项，不进入生成门禁。
- `plan-only`：读取 `copy-directions.md`、`style-presets.md`、`composition-recipes.md`、`output-specs.md`，交付文案、shot list 和提示词，不调用图片工具。
- `new`：按 `qa-dialogue-workflow.md` 逐项确认；按阶段读取上下文、文案、风格、字体、素材、构图、规格和权利参考，进入 `GENERATION_READY` 后才生成。
- `edit`：读取 `localization-and-editing.md` 与受影响阶段参考，保留未变更的确认；任何上游修改按失效矩阵重新确认。
- `localize`：读取 `localization-and-editing.md` 与 `output-specs.md`，复用已确认底图、LOGO、项目标志、IP、布局和来源哈希，只替换获确认文案与必要排版；原语言输出不改写，并创建新的版本路径。
- `variant`：读取 `localization-and-editing.md`、`composition-recipes.md`、`output-specs.md`，保持品牌档案，重新确认尺寸、平台或风格差异。
- `custom-IP`：读取 `rights-and-provenance.md`、`brand-assets.md`，依次完成参考、抽象 profile、草稿、使用权和保存范围确认；未到 `user_authorized` 不得生成。
- 缺少图片工具：当前仅允许 host 内置 `host_builtin_image_tool`；仍可完成 analysis-only/plan-only，或交付已确认的本地合成计划。工具不可用、调用失败、空返回路径、图片缺失/不可读或严重比例不匹配时 hard-stop，明确说明无法生成，不伪造调用结果、不自动重试，不使用 API keys、Images API、第三方 provider 或递归 Codex。

## 阶段参考路由

按当前状态仅读取对应文件：上下文→`context-analysis.md`；文案→`copy-directions.md`；风格→`style-presets.md`；字体→`font-presets.md`；公司 LOGO/项目标志/IP→`brand-assets.md` 与 `rights-and-provenance.md`；构图→`composition-recipes.md`；输出→`output-specs.md`；编辑/本地化→`localization-and-editing.md`；问答门禁→`qa-dialogue-workflow.md`；内部验收→`qa-checklist.md`。

## 生成结果处理

图片工具只生成无关键文字、无公司 LOGO 的底图；使用 Pillow 确定性合成并写入 manifest。使用工具返回路径 exactly（原样），先执行内部 LOGO QA，再展示 LOGO 供用户验收，之后才生成封面；失败、尺寸不符、文字溢出或权利状态不合格时硬停止并返回相应阶段，不覆盖旧版本。

LOGO-first：完成自动化 QA 后先展示 LOGO 主视觉并等待用户验收；未接受前不得生成或展示封面。编辑只使失效矩阵命中的选择失效；本地化复用已确认底图和素材哈希。自动化 QA 失败阻止 `DELIVERED`，人工视觉 warning 需要用户复核；不自动重试或自动再生。

## 生成边界

GENERATION_READY
  → build prompt
  → call host built-in image tool
  → validate returned file
  → compose with renderer
