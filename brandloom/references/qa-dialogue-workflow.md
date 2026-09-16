# QA 对话工作流

## 状态机

`INTAKE → CONTEXT_ANALYSIS → CONTEXT_CONFIRM_PENDING → COPY_DIRECTION_PENDING → STYLE_PENDING → FONT_PENDING → COMPANY_LOGO_PENDING → PROJECT_MARK_PENDING → IP_CAST_PENDING → IP_COMBINATION_PENDING → (CUSTOM_IP_REFERENCE_PENDING → CUSTOM_IP_DRAFT_PENDING → RIGHTS_CONFIRM_PENDING)? → IP_USAGE_PENDING → SHOT_LIST_PENDING → OUTPUT_SPEC_PENDING → COHERENCE_REVIEW_PENDING → GENERATION_CONFIRM_PENDING → GENERATION_READY → GENERATE_LOGO_BASE → COMPOSE_LOGO_CARD → INTERNAL_LOGO_QA → LOGO_USER_REVIEW → GENERATE_COVER_BASE → COMPOSE_COVER → INTERNAL_COVER_QA → USER_REVIEW → DELIVERED`；任意待确认状态可 `CANCELLED`。

一次只问一个问题。每阶段给出互斥选项并标明推荐项；推荐、默认、沉默和模型推断都不算确认。选项必须在同一条面向用户的消息中完整列出，并根据当前项目内容说明推荐理由；不得只写确认结论而省略选项。每条消息最后请用户回复选项字母。用户只说继续但未选择选项时，必须重新显示选项并请求明确选择，不得替用户猜测。用户可输入自定义要求。所有阶段支持 `修改`、`返回`、`取消`；发现版权、可读性或协调性风险时先提示，只有用户接受风险或采用调整后才推进。

## 确认值与 CLI

每个 `*_PENDING` 状态只接受下表对应的确认 key，必须先确认再离开该状态（取消除外）。确认式 key 的值必须是 JSON 布尔值 `true`；`yes`、`no`、`false`、`拒绝`、`0` 等原始文本均会被拒绝。命令行示例：

`brandloom state-confirm --workspace <dir> --key context --value true --state COPY_DIRECTION_PENDING`

`ip_cast` 仅接受 `author-anime`、`tuotuo`、`xingbi`、`custom`；`rights` 仅接受 `missing`、`unknown`、`draft_unconfirmed`、`analysis_only`、`user_authorized`。只有 `rights=user_authorized` 的自定义 IP 会通过生成门禁。

| 待确认状态 | 唯一确认 key |
|---|---|
| `CONTEXT_CONFIRM_PENDING` | `context` |
| `COPY_DIRECTION_PENDING` | `copy` |
| `STYLE_PENDING` | `style` |
| `FONT_PENDING` | `font` |
| `COMPANY_LOGO_PENDING` | `company_logo` |
| `PROJECT_MARK_PENDING` | `project_mark` |
| `IP_CAST_PENDING` | `ip_cast` |
| `IP_COMBINATION_PENDING` | `ip_combination` |
| `CUSTOM_IP_REFERENCE_PENDING` | `custom_ip_reference` |
| `CUSTOM_IP_DRAFT_PENDING` | `custom_ip_draft` |
| `RIGHTS_CONFIRM_PENDING` | `rights` |
| `IP_USAGE_PENDING` | `ip_usage` |
| `SHOT_LIST_PENDING` | `shot_list` |
| `OUTPUT_SPEC_PENDING` | `output_spec` |
| `COHERENCE_REVIEW_PENDING` | `coherence` |
| `GENERATION_CONFIRM_PENDING` | `generation_confirmation` |

## 菜单

以下每个菜单都必须原样转化为一条面向用户的消息：先列出全部 A/B/C 选项，再标出推荐项和推荐理由，最后请用户回复选项字母。

- `CONTEXT_CONFIRM_PENDING`：A. 确认当前项目理解（推荐）；B. 修正项目名称、用途或受众；C. 暂停并补充资料。推荐理由：当前项目已有 README、SKILL.md 和 package.json 可交叉验证，先锁定“普通 AI 用户 → 可编辑 PPT”的理解能避免后续文案跑偏。
- `COPY_DIRECTION_PENDING`：A. 项目介绍型（推荐）；B. 痛点—解决方案—结果型；C. 核心功能型；D. 使用场景与工作流型；E. 商业转化型。推荐理由：AI PPT Producer 面向普通 AI 用户，先讲清“不会做 PPT 也能得到可编辑演示文稿”最容易建立理解。
- `STYLE_PENDING`：A. `editorial-minimal` → `editorial-minimal-grid`（推荐）；B. `reference-adaptive` → `bright-saas-real-scene`；C. `reference-adaptive` → `dark-neon-product`；D. `reference-adaptive` → `high-density-commercial`；E. `reference-adaptive` → `cinematic-monitor-hero`；F. `soft-3d-brand` → `soft-3d-brand-icon`。推荐理由：当前项目强调低漂移、可编辑和可审查，编辑式网格能把 Brief、样张和页面结构表达得更清楚；每个选项都已包含具体 profile，不需要再隐藏追问。
- `FONT_PENDING`：A. 微软雅黑 + Segoe UI（推荐）；B. 思源黑体 + Inter；C. HarmonyOS Sans + Inter；D. 阿里妈妈数黑体 + Montserrat；E. 得意黑 + Space Grotesk。推荐理由：项目同时包含中英文标题、流程和功能说明，A 在本机可读性与跨语言稳定性最适合；缺失字体必须确认回退。
- `COMPANY_LOGO_PENDING`：A. 使用已授权 ENHE 原始 LOGO，黑色单色合成（推荐）；B. 使用原始 LOGO 并保持原色；C. 本次不放公司 LOGO。推荐理由：明亮真实场景上黑色 LOGO 对比度清晰，能与 AI PPT Producer 的编辑式版面保持一致。选择 A/B 前必须先执行 `brandloom asset-add --workspace <dir> --source <path> --category company-logo --scope <project|personal> --rights user_authorized --save-confirmed`，再核对 `.brandloom/asset-manifest.json` 中的 `rights_status`、`save_scope_confirmed`、`default_scope` 与 `usage_term`（使用期限），并确认保存 scope 与 default scope；确认结果写入 `confirmed.company_logo_treatment`，资产记录作为权利与 scope 的实际来源。仅允许 `scale`、`position`；`recolor_monochrome`（映射为 `monochrome-black`）、`opacity`、`external_shadow` 需单独确认，禁止 `redraw`、`distort`、`change_letterforms`、`change_geometry`、`use_as_training_reference`。
- `PROJECT_MARK_PENDING`：A. 本次不放项目标志（推荐）；B. 生成新的抽象项目标志；C. 使用当前上传或项目库标志。推荐理由：仓库目前没有独立项目标志，使用项目名称、页面卡片和流程结构更能准确表达可编辑 PPT 工作流，避免添加未经确认的符号。
- `IP_CAST_PENDING`：A. 拓拓 + 星比（推荐）；B. 仅拓拓；C. 仅星比；D. 黑发动漫人物；E. 自定义 IP。推荐理由：普通 AI 用户更容易接受双角色叙事，拓拓可执行内容整理，星比可表达完成结果；自定义 IP 需要额外参考与权利确认。
- `IP_COMBINATION_PENDING`：A. 拓拓 + 星比（推荐）；B. 仅拓拓；C. 仅星比；D. 黑发人物 + 拓拓；E. 黑发人物 + 星比；F. 三者；G. 上传自定义 IP；H. 返回上一层。推荐理由：当前项目的流程天然分为“整理输入”和“展示输出”两步，拓拓与星比分工最清晰，也能让封面保持亲和而不拥挤。
- `CUSTOM_IP_REFERENCE_PENDING`：A. 确认真实可访问参考并仅作抽象分析（推荐）；B. 补充或更换参考；C. 取消自定义 IP。推荐理由：当前项目已有内置 IP 可用，只有在确实需要自定义角色时才进入此分支；先锁定参考来源可避免把他人形象直接复制进项目。
- `CUSTOM_IP_DRAFT_PENDING`：A. 确认抽象 profile 草稿（推荐）；B. 修改 profile；C. 重新分析参考；D. 返回。推荐理由：AI PPT Producer 的视觉重点是内容工作流，先确认角色的抽象动作与职责，能控制角色不抢占页面信息层级。
- `RIGHTS_CONFIRM_PENDING`：A. 确认 `user_authorized` 使用权、保存 scope 和 default scope（推荐）；B. 声明 `analysis_only`；C. 声明 `unknown`；D. 声明 `missing`；E. 声明 `draft_unconfirmed`；F. 返回或取消。推荐理由：当前项目计划公开使用视觉资产，只有权利、保存范围和默认范围都明确时才可进入生成；其他选项必须阻塞生成；若权利尚未明确，不得选择 A。
- `IP_USAGE_PENDING`：A. 方形图不放 IP、封面使用拓拓 + 星比（推荐）；B. 方形图与封面都使用组合；C. 方形图使用单个 IP、封面使用组合；D. 分别自定义位置与动作；E. 返回修改角色。推荐理由：方形图需要快速识别项目名称，封面才有足够空间表达“整理 → 完成”的角色分工，符合普通 AI 用户的阅读路径。
- `SHOT_LIST_PENDING`：A. 确认推荐场景与动作（推荐）；B. 调整 LOGO 主视觉；C. 调整封面；D. 调整功能点或角色动作；E. 只交付方案和提示词。推荐理由：真实的个人内容创作工作室、主题笔记、页面卡片和编辑器能直接对应仓库的 Brief、Prototype 与可编辑 PPTX 流程。
- `OUTPUT_SPEC_PENDING`：A. 完整双语（bilingual）标准包：PNG/sRGB，LOGO 1254×1254 + 封面 1774×887（推荐）；B. 仅 GitHub Social Preview 1280x640（只生成一张预览图）；C. 仅一张 LOGO（logo-only）：当前语言，1254×1254；D. 仅一张封面（cover-only）：当前语言，1774×887；E. 自定义单画布：只生成一张，由用户提供尺寸与语言；F. 自定义多输出包：由用户一次性提供每个 LOGO/封面的尺寸与语言；G. 返回。以上 A-F 是互斥的完整输出方案，不把双语、尺寸或输出对象拆成可叠加开关。推荐理由：当前目标是同时获得中文和英文的方形图与封面，A 的默认尺寸能覆盖 Skill 平台和项目说明使用。
- `COHERENCE_REVIEW_PENDING`：A. 采用推荐调整（推荐）；B. 保持当前要求并接受风险；C. 修改当前要求；D. 返回指定阶段；E. 取消。推荐理由：编辑式网格、同一真实场景、双语复用底图和“方形无 IP / 封面双 IP”分工能在四张输出之间保持一致。
- `GENERATION_CONFIRM_PENDING`：A. 确认先生成 LOGO，再继续封面（推荐）；B. 仅生成 LOGO；C. 仅生成封面（需已有 LOGO）；D. 返回修改；E. 取消。推荐理由：先锁定方形主视觉，再复用品牌档案生成封面，可以减少普通用户最在意的标题、Logo 和配色漂移。

LOGO 验收菜单：接受并继续封面；修改文字；修改构图；修改项目标志或 IP；返回画风或字体。封面验收菜单：接受全部并交付；修改指定图片；仅修改文字或布局；返回修改画风、字体或 IP；保留当前版本并结束。

## 失效矩阵

| 变更项 | 保留 | 必须重新确认 |
|---|---|---|
| context | 原始来源 | 文案、风格、字体、LOGO、项目标志、IP、使用、shot list、规格、协调性、生成确认 |
| copy | 项目理解 | 文案草案、shot list、协调性、生成确认 |
| style | 项目理解、文案方向 | 字体、shot list、输出适配、协调性、生成确认 |
| font | 上游内容 | 文案排版、shot list、协调性、生成确认 |
| company-logo | 上游内容 | LOGO 安全区、shot list、协调性、生成确认 |
| project-mark | 上游内容 | 项目标志处理方式、shot list、协调性、生成确认 |
| ip-cast | 上游内容 | IP 组合、位置、动作、shot list、协调性、生成确认 |
| ip-combination | 上游内容 | 组合、位置、动作、custom IP、权利、使用、shot list、协调性、生成确认 |
| custom-IP-reference | 上游 IP 选择 | profile 草稿、权利、保存范围、使用、shot list、协调性、生成确认 |
| custom-IP-draft | 上游 IP 选择、参考确认 | profile 草稿、权利、保存范围、使用、shot list、协调性、生成确认 |
| rights | 上游内容 | 自定义 IP 权利状态、IP 使用、shot list、协调性、生成确认 |
| ip-usage | 上游内容 | IP 位置与动作、shot list、协调性、生成确认 |
| shot-list | 上游内容 | shot list、协调性、生成确认 |
| output-spec | 上游内容 | 输出适配、协调性、生成确认 |
| 单图局部问题 | 所有已锁定上游项 | 该图变更摘要与再次生成确认 |

`GENERATION_READY` 是唯一图片工具 gate；编辑、返回或任何上游变化都会离开该 gate。

## 图片工具边界与失败处理

当前 host 仅允许 `host_builtin_image_tool`，必须处于 `GENERATION_READY`。调用时使用工具返回路径 exactly（原样），不得改写、猜测或扫描路径。工具不可用或调用失败、空返回路径、文件缺失/不可读、严重比例不匹配时立即 hard-stop，返回相应阶段并报告原因；不得自动重试。不得使用 API keys、Images API、第三方 provider、递归 Codex 或其他生成后端。
