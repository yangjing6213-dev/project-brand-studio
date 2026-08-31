# QA 对话工作流

## 状态机

`INTAKE → CONTEXT_ANALYSIS → CONTEXT_CONFIRM_PENDING → COPY_DIRECTION_PENDING → STYLE_PENDING → FONT_PENDING → COMPANY_LOGO_PENDING → PROJECT_MARK_PENDING → IP_CAST_PENDING → IP_COMBINATION_PENDING → (CUSTOM_IP_REFERENCE_PENDING → CUSTOM_IP_DRAFT_PENDING → RIGHTS_CONFIRM_PENDING)? → IP_USAGE_PENDING → SHOT_LIST_PENDING → OUTPUT_SPEC_PENDING → COHERENCE_REVIEW_PENDING → GENERATION_CONFIRM_PENDING → GENERATION_READY → GENERATE_LOGO_BASE → COMPOSE_LOGO_CARD → INTERNAL_LOGO_QA → LOGO_USER_REVIEW → GENERATE_COVER_BASE → COMPOSE_COVER → INTERNAL_COVER_QA → USER_REVIEW → DELIVERED`；任意待确认状态可 `CANCELLED`。

一次只问一个问题。每阶段给出互斥选项并标明推荐项；推荐、默认、沉默和模型推断都不算确认。用户可输入自定义要求。所有阶段支持 `修改`、`返回`、`取消`；发现版权、可读性或协调性风险时先提示，只有用户接受风险或采用调整后才推进。

## 菜单

- `COPY_DIRECTION_PENDING`：项目介绍型（推荐）；痛点—解决方案—结果型；核心功能型；使用场景与工作流型；商业转化型。
- `STYLE_PENDING` 顶层仅三类：`reference-adaptive`（推荐）；`editorial-minimal`；`soft-3d-brand`。选择 `reference-adaptive` 后再选四个主家族：`bright-saas-real-scene`、`dark-neon-product`、`high-density-commercial`、`cinematic-monitor-hero`；另列两个具体 profile：`editorial-minimal-grid`、`soft-3d-brand-icon`（不增加顶层菜单数量）。
- `FONT_PENDING`：微软雅黑 + Segoe UI（推荐）；思源黑体 + Inter；HarmonyOS Sans + Inter；阿里妈妈数黑体 + Montserrat；得意黑 + Space Grotesk。缺失字体必须确认回退。
- `COMPANY_LOGO_PENDING`：仅本次使用（推荐）；保存当前项目不设默认；保存当前项目并设项目默认；保存个人库不设默认；保存个人库并设个人默认；另确认权利和允许操作。默认允许 `scale`、`position`；`recolor_monochrome`、`opacity`、`external_shadow` 仅在用户确认后允许；禁止 `redraw`、`distort`、`change_letterforms`、`change_geometry`、`use_as_training_reference`。
- `PROJECT_MARK_PENDING`：使用当前上传；上传新的；使用项目库；本次不放；生成新概念分支。
- `IP_CAST_PENDING`：黑发动漫人物；拓拓；星比；拓拓 + 星比（推荐）；更多组合或自定义 IP。`IP_COMBINATION_PENDING`：黑发人物 + 拓拓；黑发人物 + 星比；三者；上传自定义 IP；返回上一层。
- `CUSTOM_IP_REFERENCE_PENDING`：确认真实可访问参考；确认仅抽象分析、不复制外形；补充/更换参考；返回；取消。`CUSTOM_IP_DRAFT_PENDING`：确认抽象 profile 草稿；修改 profile；重新分析；返回；取消。`RIGHTS_CONFIRM_PENDING`：确认 `user_authorized` 使用权；声明 `analysis_only`/`unknown`/`missing`/`draft_unconfirmed`；确认保存 scope 和 default scope；返回；取消。非 `user_authorized` 必须阻塞，不得生成。
- `IP_USAGE_PENDING`：两图同组；LOGO 单个、封面组合（推荐）；LOGO 不放 IP、封面使用；分别自定义；返回修改角色。
- `SHOT_LIST_PENDING`：确认推荐；调整 LOGO 主视觉；调整封面；调整功能点或角色动作；只交付方案和提示词。
- `OUTPUT_SPEC_PENDING`：确认默认 PNG/sRGB 规格；GitHub Social Preview 1280x640；logo-only；cover-only；bilingual；custom dimensions（重新检查比例/安全区）；分别设置 LOGO 与封面；返回。
- `COHERENCE_REVIEW_PENDING`：保持要求并接受风险；采用推荐调整（推荐）；修改当前要求；返回指定阶段；取消。
- `GENERATION_CONFIRM_PENDING`：确认生成 LOGO 后继续封面（推荐）；仅生成 LOGO；仅生成封面（需已有 LOGO）；返回修改；取消。

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
