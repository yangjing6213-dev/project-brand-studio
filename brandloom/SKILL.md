---
name: brandloom
description: 用于分析项目、对话、附件、链接和品牌素材，并通过确认式 QA 生成或修改适配 YouTube、抖音、小红书、GitHub 与自定义尺寸的项目封面、中英文版本和品牌视觉变体；不生成 LOGO 方形主视觉。
---

# BrandLoom

先读取 `references/architecture.md`，再根据当前阶段按需读取参考文件；不要一次加载完整参考库。任何生成或改图请求都必须先完成确认式 QA，只有 `qa_state = GENERATION_READY` 且用户明确确认后，才可调用 `host_builtin_image_tool`。QA 每次只问一个问题；每次提问都必须在发给用户的消息中展示 A/B/C 等明确选项和实际差别。推荐必须根据已分析的项目内容与目标用途选择，并说明理由；不得固定推荐同一项或只问用户选哪个。多选时明确说明可多选；一个阶段有多个决定时分轮提问并记录，收齐后才通过该阶段。主视觉风格按 `references/style-presets.md` 展示四种明确方案，并完成所选方案对应的条件确认后才可离开 `STYLE_PENDING`。

## 任务路由

- `analysis-only`：只分析可访问上下文，读取 `context-analysis.md`，交付证据、推断和未确认项，不进入生成门禁。
- `plan-only`：读取 `copy-directions.md`、`style-presets.md`、`composition-recipes.md`、`output-specs.md`，交付文案、shot list 和提示词，不调用图片工具。
- `new`：按 `qa-dialogue-workflow.md` 逐项确认；按阶段读取上下文、文案、风格、字体、素材、构图、规格和权利参考，进入 `GENERATION_READY` 后才生成。
- `edit`：读取 `localization-and-editing.md` 与受影响阶段参考，保留未变更的确认；任何上游修改按失效矩阵重新确认。
- `localize`：读取 `localization-and-editing.md` 与 `output-specs.md`，以用户已通过的语言版本作为构图母版，复用同一底图、版式、LOGO、项目标志、IP 和来源哈希，只替换获确认文案与必要排版；原语言输出不改写，并创建新的版本路径。
- `variant`：读取 `localization-and-editing.md`、`composition-recipes.md`、`output-specs.md`，保持品牌档案，重新确认尺寸、平台或风格差异。
- `custom-IP`：读取 `rights-and-provenance.md`、`brand-assets.md`，依次完成参考、抽象 profile、草稿、使用权和保存范围确认；未到 `user_authorized` 不得生成。
- 缺少图片工具：当前仅允许 host 内置 `host_builtin_image_tool`；仍可完成 analysis-only/plan-only，或交付已确认的本地合成计划。工具不可用、调用失败、空返回路径、图片缺失/不可读或严重比例不匹配时 hard-stop，明确说明无法生成，不伪造调用结果、不自动重试，不使用 API keys、Images API、第三方 provider 或递归 Codex。

## 阶段参考路由

按当前状态仅读取对应文件：上下文→`context-analysis.md`；文案→`copy-directions.md`；风格→`style-presets.md` 与 `composition-recipes.md`；字体→`font-presets.md`；公司 LOGO/项目标志/IP/人物素材→`brand-assets.md` 与 `rights-and-provenance.md`；输出→`output-specs.md`；编辑/本地化→`localization-and-editing.md`；问答门禁→`qa-dialogue-workflow.md`；内部验收→`qa-checklist.md`。

## 生成结果处理

进入 `GENERATION_READY` 后，每个目标先运行本地请求预检：`python brandloom/scripts/brandloom_cli.py request --workspace <工作区> --target-id <已确认目标ID>`。读取 JSON 输出的 `prompt`、`dimensions`、`reference_assets` 和 `request_id`，将提示词与每个参考项的 `path` 原样传给宿主图片工具。预检会先校验平台版式和流程文案、公司 LOGO 与项目标志选择，并检查封面文字涉及的全部字符（包括英文和标点）；发现字体缺字时会自动尝试本机后备字体，必要时下载并校验获许可的字体到 `.brandloom/font-cache/`，再检查文字是否排得下。字体修复和其他必要条件都通过后，才可调用图片工具。合成时必须将同一个 `request_id` 传给 `compose --request-id <预检返回的request_id>`；该编号与当前目标、已确认 brief、提示词和参考素材内容绑定，不能跳过、跨目标复用或在参考素材变化后继续用。预检只检查已确认目标与素材并输出请求，不调用图片工具；若字体下载或校验失败、文字仍无法显示或版式放不下，预检才会说明具体原因并停止，不得先生成再补确认。安装包用户若没有本地风格参考图，应让用户提供对应参考图（仅本次、仅抽象分析、不设默认），或明确选择按风格文字说明继续；后者写入 `style.reference_mode: "text-only"`。不得因缺图静默跳过参考，也不得把参考图打包进公开发行包。

图片工具只生成无关键文字、无公司 LOGO 的底图；底图必须是贴合项目用途的真实场景，不使用纯抽象背景替代。背景可满铺，文案可直接叠在场景上，不固定为左侧文案区、右侧场景。按平台分别生成匹配画幅的场景底图；只有宽高比例完全一致时才可无裁切、无变形等比例缩放到目标像素。使用 Pillow 确定性合成并写入 manifest。仅生成用户确认的平台封面，不生成 1:1 LOGO 方形图。默认保持品牌色、核心卖点和视觉气质统一，并按平台调整文案长度、信息量、构图、主体大小和安全区。风格 1、2 必须使用用户单独提供且确认有权使用的人物素材；风格参考图中的人物不能代替人物素材或作为人物身份依据。风格 2 还必须呈现主讲人物和展示大屏，除标题外的文案排入大屏，并先确认穿着与标题强调色；屏幕构图必须适合后续确定性排字，细则见 `references/composition-recipes.md`。若工作区存在 `.brandloom/style-reference-library/`，每次生成都把已选风格对应的附件作为风格/构图参考传给图片工具（风格 B 同时使用舞台与排版参考）；禁止复制其中人物身份、原文案、商标或水印。确认使用流程卡片时，宽版最多 4 步、竖版最多 3 步；卡片内部约 60% 不透明度（约 40% 透明）并局部柔化，细边框、平滑圆角、文字留白，不模糊整张底图、不加总外框。生成前核对项目事实、逐字文案、尺寸、风格、参考素材、人物/穿着、强调色和文字区域；全部确认后再发起一次生成并按 `references/qa-checklist.md` 验收，目标是减少返工，不承诺图片模型必然一次命中。任何差异都应说明并经用户确认修正，不自动重试或覆盖旧版本。使用工具返回路径 exactly（原样）；对每张封面分别执行内部 QA 和人工验收；失败、尺寸比例不符、文字溢出或权利状态不合格时硬停止，不覆盖旧版本。

公司 LOGO（如用户确认使用）只作为封面元素等比例合成，不单独生成方形图。编辑只使失效矩阵命中的选择失效；本地化复用已确认底图和素材哈希。自动化 QA 失败阻止 `DELIVERED`，人工视觉 warning 需要用户复核；不自动重试或自动再生。

## 生成边界

GENERATION_READY
  → build prompt
  → call host built-in image tool
  → validate returned file
  → compose with renderer
