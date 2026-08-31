# QA 对话工作流

## 状态机

`INTAKE → CONTEXT_ANALYSIS → CONTEXT_CONFIRM_PENDING → COPY_DIRECTION_PENDING → STYLE_PENDING → FONT_PENDING → COMPANY_LOGO_PENDING → PROJECT_MARK_PENDING → IP_CAST_PENDING → IP_COMBINATION_PENDING → (CUSTOM_IP_REFERENCE_PENDING → CUSTOM_IP_DRAFT_PENDING → RIGHTS_CONFIRM_PENDING)? → IP_USAGE_PENDING → SHOT_LIST_PENDING → OUTPUT_SPEC_PENDING → COHERENCE_REVIEW_PENDING → GENERATION_CONFIRM_PENDING → GENERATION_READY → GENERATE_LOGO_BASE → COMPOSE_LOGO_CARD → INTERNAL_LOGO_QA → LOGO_USER_REVIEW → GENERATE_COVER_BASE → COMPOSE_COVER → INTERNAL_COVER_QA → USER_REVIEW → DELIVERED`；任意待确认状态可 `CANCELLED`。

一次只问一个问题。每阶段给出互斥选项并标明推荐项；推荐、默认、沉默和模型推断都不算确认。用户可输入自定义要求。所有阶段支持 `修改`、`返回`、`取消`；发现版权、可读性或协调性风险时先提示，只有用户接受风险或采用调整后才推进。

## 菜单

- `COPY_DIRECTION_PENDING`：项目介绍型（推荐）；痛点—解决方案—结果型；核心功能型；使用场景与工作流型；商业转化型。
- `STYLE_PENDING` 顶层仅三类：`reference-adaptive`（推荐）；`editorial-minimal`；`soft-3d-brand`。选择 `reference-adaptive` 后再选四个主家族：`bright-saas-real-scene`、`dark-neon-product`、`high-density-commercial`、`cinematic-monitor-hero`；另有具体 profile `bright-saas-real-scene` 与 `editorial-minimal-grid` 供精确指定。
- `FONT_PENDING`：微软雅黑 + Segoe UI（推荐）；思源黑体 + Inter；HarmonyOS Sans + Inter；阿里妈妈数黑体 + Montserrat；得意黑 + Space Grotesk。缺失字体必须确认回退。
- `COMPANY_LOGO_PENDING`：仅本次使用（推荐）；保存当前项目不设默认；保存当前项目并设项目默认；保存个人库不设默认；保存个人库并设个人默认；另确认权利和允许操作。
- `PROJECT_MARK_PENDING`：使用当前上传；上传新的；使用项目库；本次不放；生成新概念分支。
- `IP_CAST_PENDING`：黑发动漫人物；拓拓；星比；拓拓 + 星比（推荐）；更多组合或自定义 IP。`IP_COMBINATION_PENDING`：黑发人物 + 拓拓；黑发人物 + 星比；三者；上传自定义 IP；返回上一层。
- `IP_USAGE_PENDING`：两图同组；LOGO 单个、封面组合（推荐）；LOGO 不放 IP、封面使用；分别自定义；返回修改角色。
- `SHOT_LIST_PENDING`：确认推荐；调整 LOGO 主视觉；调整封面；调整功能点或角色动作；只交付方案和提示词。
- `OUTPUT_SPEC_PENDING`：确认默认 PNG/sRGB 规格；自定义尺寸；自定义格式/色彩空间；分别设置 LOGO 与封面；返回。
- `COHERENCE_REVIEW_PENDING`：保持要求并接受风险；采用推荐调整（推荐）；修改当前要求；返回指定阶段；取消。
- `GENERATION_CONFIRM_PENDING`：确认生成 LOGO 后继续封面（推荐）；仅生成 LOGO；仅生成封面（需已有 LOGO）；返回修改；取消。

LOGO 验收菜单：接受并继续封面；修改文字；修改构图；修改项目标志或 IP；返回画风或字体。封面验收菜单：接受全部并交付；修改指定图片；仅修改文字或布局；返回修改画风、字体或 IP；保留当前版本并结束。

## 失效矩阵

| 变更 | 必须重新确认 |
|---|---|
| context | 文案、风格、字体、LOGO、项目标志、IP、使用、shot list、规格、协调性、生成确认 |
| copy | 文案草案、shot list、协调性、生成确认 |
| style/font | 后续字体或排版、shot list、规格适配、协调性、生成确认 |
| company-logo/project-mark | 相应安全区或处理方式、shot list、协调性、生成确认 |
| ip-cast/ip-combination/custom-IP/rights/usage | 后续 IP、shot list、协调性、生成确认 |
| shot-list/output-spec | 协调性、生成确认 |
| 单图局部问题 | 该图摘要与再次生成确认 |

`GENERATION_READY` 是唯一图片工具 gate；编辑、返回或任何上游变化都会离开该 gate。
