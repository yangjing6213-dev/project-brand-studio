# BrandLoom 产品设计规格

**文档状态：** 已确认设计  
**日期：** 2026-08-31  
**仓库名称：** `project-brand-studio`  
**Skill 目录与调用名：** `brandloom` / `Use $brandloom`  
**显示名称：** BrandLoom（品牌织造）  
**目标宿主：** Codex Skill；同时保持指令、素材与脚本可迁移到支持 Agent Skills 的其他宿主  
**参考基线：** `yangjing6213-dev/cognitive-anchor-sketcher` 的 `SKILL.md + references + QA 状态机 + 合约测试` 结构

---

## 1. 产品结论

BrandLoom 不是“一段生图提示词”，而是一套本地优先、确认式、可追溯的项目品牌视觉工作流。它先分析用户当前可访问的对话、上传附件、链接、项目文件和既有素材，再通过逐项 QA 锁定文案、画风、字体、公司 LOGO、项目标志、IP 角色、构图与输出规格。全部门禁通过后，才生成 LOGO 主视觉和封面。

BrandLoom 的核心差异是：

1. **先理解项目，再设计视觉。**
2. **公司 LOGO 使用原文件确定性合成，不交给生图模型重绘。**
3. **关键中文和英文文案使用确定性排版，不依赖模型直接写字。**
4. **LOGO 主视觉与封面共享同一个品牌档案、素材库和版本记录。**
5. **每次上传素材都确认保存范围、默认范围与使用权。**
6. **三个内置 IP 同等级可选，并支持单独或组合使用。**

---

## 2. 术语边界

### 2.1 `project-mark`

项目图标、App Icon 或纯图形标志。可以由用户上传，也可以在用户明确选择后生成新概念。允许按用户确认的方式进行单色化、渐变化、材质化或简化，但必须保持辨识度。

### 2.2 `company-logo`

公司正式 LOGO，例如 ENHE。默认只能使用用户上传的原文件进行等比例缩放、定位和颜色版本切换。不得由生图模型重绘，不得改变字形、几何比例或字母结构。

### 2.3 `logo-card`

附件1类型的 1:1 方形品牌主视觉。它不是纯 LOGO，通常包含公司 LOGO、项目名称、项目标志、定位文案、真实场景和产品界面。

### 2.4 `cover`

附件2类型的 2:1 横版封面，用于 GitHub README、Social Preview、产品页、Skill 平台和发布内容。

### 2.5 `ip-character`

参与画面动作的人物或品牌角色，不是角落装饰。内置三种：

- `author-anime`：黑发动漫人物。
- `tuotuo`：蓝色角色。
- `xingbi`：黄色星星。

---

## 3. 目标与非目标

### 3.1 V1 目标

- 分析用户当前可访问的对话、附件、公开链接和 workspace 文件。
- 形成可确认的项目理解：功能、目标用户、痛点、使用结果和证据状态。
- 按一次一个问题的 QA 流程确认全部设计决策。
- 生成或修改 `logo-card` 和 `cover`。
- 支持中文、英文和中英双语版本。
- 使用素材库保证公司 LOGO、项目标志和 IP 的跨任务一致性。
- 使用 Pillow 进行确定性文字、LOGO、项目标志和已授权素材合成。
- 保留版本、来源、授权、提示词、输入资产哈希和输出路径。
- 默认本地运行，不上传素材库，不启用遥测。
- 支持 `new`、`edit`、`localize`、`variant`、`plan-only` 五种任务模式。

### 3.2 V1 非目标

- 不自动创建真正的商标注册方案。
- 不保证生成 SVG、AI 或可编辑矢量源文件。
- 不提供 Figma 云同步或团队协作后台。
- 不自动发布到 GitHub Release、Skill 平台或社交媒体。
- 不批量生成几十个平台尺寸。
- 不附带或分发字体文件。
- 不把第三方参考海报原图打包进公开 Skill。
- 不在未经人工复核的情况下对外发布生成内容。
- 不自动覆盖任何已有素材或输出。

---

## 4. 用户与核心场景

### 4.1 主要用户

- 一人公司、独立开发者和 AI Builder。
- 使用 Codex、Agent、MCP 或其他 AI 工作流的项目作者。
- 需要为 GitHub 项目、Skill、软件或数字产品建立统一视觉的人。
- 已经有公司 LOGO、IP 或参考图，但缺乏稳定品牌流程的人。

### 4.2 关键场景

1. 用户提供 GitHub 链接、项目说明和参考图，生成一套中文 LOGO 主视觉与封面。
2. 用户已有英文版，要求保留视觉并生成中文版。
3. 用户更换项目标志或公司 LOGO，重新合成而不改变背景场景。
4. 用户选择黑发人物、拓拓、星比或其组合参与封面。
5. 用户把新素材保存为项目默认或个人默认，供下一次任务复用。
6. 用户只需要项目分析、文案或 shot list，不进入生图。

---

## 5. 总体架构

BrandLoom 分成五个独立单元：

```text
对话与材料分析
      ↓
确认式 QA 状态机
      ↓
品牌档案与素材解析
      ↓
内置图片工具生成无关键文字底图
      ↓
Pillow 确定性排版与品牌合成
      ↓
内部 QA、用户验收、版本化交付
```

### 5.1 Skill 指令层

`brandloom/SKILL.md` 负责：

- 任务识别与模式路由。
- 判断当前会话中真实可访问的材料。
- 一次只推进一个 QA 阶段。
- 生成文案、风格分析、shot list 和提示词。
- 在 `GENERATION_READY` 前禁止调用图片工具。
- 调用宿主当前可用的内置图片生成或编辑工具。
- 将工具返回的真实文件路径交给本地合成脚本。

### 5.2 参考规则层

`brandloom/references/` 负责：

- QA 菜单与回退规则。
- 文案、画风、字体、IP 和构图预设。
- 素材保存、来源、授权和默认规则。
- 生成提示词模板。
- 输出规格和内部 QA。
- 编辑、本地化和失败处理。

### 5.3 本地脚本层

`brandloom/scripts/brandloom_core/` 负责：

- JSON 数据结构。
- 状态机与下游失效。
- 素材库、SHA-256 去重和默认资产解析。
- 字体解析。
- 模板布局与 Pillow 合成。
- 输出尺寸、留白、文字溢出和品牌完整性验证。
- 生成 manifest 和 QA 报告。
- 版本化保存，不覆盖历史文件。

### 5.4 内置只读资产层

`brandloom/assets/defaults/` 负责：

- 经用户明确授权可公开分发的 ENHE 公司 LOGO。
- `author-anime`、`tuotuo`、`xingbi` 三个同等级内置 IP。
- 项目自有的示例图。
- 不包含附件1–6中的第三方商业海报原图；只保留其抽象风格 DNA。

### 5.5 项目运行时数据层

工作区中的 `.brandloom/` 保存当前项目数据，个人素材库保存到：

```text
$CODEX_HOME/brandloom/
```

若未设置 `CODEX_HOME`，使用：

```text
~/.codex/brandloom/
```

---

## 6. 仓库文件结构

```text
project-brand-studio/
├─ brandloom/
│  ├─ SKILL.md
│  ├─ agents/
│  │  └─ openai.yaml
│  ├─ references/
│  │  ├─ architecture.md
│  │  ├─ qa-dialogue-workflow.md
│  │  ├─ context-analysis.md
│  │  ├─ copy-directions.md
│  │  ├─ style-presets.md
│  │  ├─ font-presets.md
│  │  ├─ brand-assets.md
│  │  ├─ ip-profiles.md
│  │  ├─ ip-combinations.md
│  │  ├─ composition-recipes.md
│  │  ├─ output-specs.md
│  │  ├─ generation-backend.md
│  │  ├─ localization-and-editing.md
│  │  ├─ rights-and-provenance.md
│  │  └─ qa-checklist.md
│  ├─ templates/
│  │  ├─ logo-card-1x1.json
│  │  ├─ cover-2x1.json
│  │  └─ social-preview-2x1.json
│  ├─ assets/
│  │  └─ defaults/
│  │     ├─ company-logo/
│  │     ├─ ip/
│  │     │  ├─ author-anime/
│  │     │  ├─ tuotuo/
│  │     │  └─ xingbi/
│  │     └─ examples/
│  └─ scripts/
│     ├─ brandloom_cli.py
│     └─ brandloom_core/
│        ├─ __init__.py
│        ├─ models.py
│        ├─ json_io.py
│        ├─ paths.py
│        ├─ state_machine.py
│        ├─ asset_library.py
│        ├─ fonts.py
│        ├─ layout.py
│        ├─ renderer.py
│        ├─ prompt_builder.py
│        ├─ manifests.py
│        └─ validation.py
├─ tests/
│  ├─ test_skill_contract.py
│  ├─ test_models.py
│  ├─ test_state_machine.py
│  ├─ test_asset_library.py
│  ├─ test_ip_profiles.py
│  ├─ test_fonts.py
│  ├─ test_renderer.py
│  ├─ test_prompt_builder.py
│  ├─ test_pipeline.py
│  ├─ test_localization.py
│  └─ test_package.py
├─ docs/
│  ├─ examples/
│  └─ superpowers/
│     ├─ specs/
│     └─ plans/
├─ scripts/
│  └─ build_skill_package.py
├─ staging/
│  └─ brand-assets/
├─ .github/
│  └─ workflows/
│     ├─ validate-skill.yml
│     └─ codeql.yml
├─ requirements-runtime.txt
├─ README.md
├─ README.en.md
├─ LICENSE
└─ NOTICE.md
```

---

## 7. 项目运行时目录

只有用户选择保存素材或生成输出时才创建：

```text
.brandloom/
├─ brand-brief.json
├─ qa-state.json
├─ defaults.json
├─ library/
│  ├─ project-mark/
│  ├─ company-logo/
│  ├─ ip/
│  ├─ style-reference/
│  │  ├─ logo-card/
│  │  └─ cover/
│  └─ ui-screenshot/
├─ manifests/
│  ├─ asset-manifest.json
│  └─ provenance.json
├─ sessions/
│  └─ 20260831-142500-agentguardian/
│     ├─ intake-summary.md
│     ├─ shot-list.md
│     ├─ generation-request.json
│     └─ qa-report.json
└─ outputs/
   └─ agentguardian/
      ├─ 01-logo-card-v01.png
      ├─ 02-cover-v01.png
      └─ generation-manifest-v01.json
```

原则：

- 不保存完整对话原文，默认只保存派生后的项目摘要与来源说明。
- 不覆盖同名输出；使用 `-v02`、`-v03`。
- 原始上传文件不被修改。
- 个人素材库和项目素材库均不自动进入 Git。
- `staging/` 只用于开发时导入已获公开分发授权的内置素材。

---

## 8. 任务模式

| 模式 | 行为 |
|---|---|
| `new` | 分析项目并生成新的 LOGO 主视觉与封面 |
| `edit` | 修改已有视觉，保留未变更的品牌选择 |
| `localize` | 保留背景、素材和构图，确定性替换语言 |
| `variant` | 保持品牌档案，生成尺寸、风格或平台变体 |
| `plan-only` | 交付分析、文案、shot list 和提示词，不调用图片工具 |

---

## 9. QA 状态机

```text
INTAKE
  → CONTEXT_ANALYSIS
  → CONTEXT_CONFIRM_PENDING
  → COPY_DIRECTION_PENDING
  → STYLE_PENDING
  → FONT_PENDING
  → COMPANY_LOGO_PENDING
  → PROJECT_MARK_PENDING
  → IP_CAST_PENDING
      → IP_COMBINATION_PENDING
      → CUSTOM_IP_REFERENCE_PENDING
      → CUSTOM_IP_DRAFT_PENDING
      → RIGHTS_CONFIRM_PENDING
  → IP_USAGE_PENDING
  → SHOT_LIST_PENDING
  → OUTPUT_SPEC_PENDING
  → COHERENCE_REVIEW_PENDING
  → GENERATION_CONFIRM_PENDING
  → GENERATION_READY
  → GENERATE_LOGO_BASE
  → COMPOSE_LOGO_CARD
  → INTERNAL_LOGO_QA
  → LOGO_USER_REVIEW
  → GENERATE_COVER_BASE
  → COMPOSE_COVER
  → INTERNAL_COVER_QA
  → USER_REVIEW
  → DELIVERED | CANCELLED
```

### 9.1 对话规则

- 一次只问一个问题。
- 每个阶段提供 3–5 个互斥选项，标明推荐项。
- 用户可以输入自然语言自定义要求。
- 推荐、默认、沉默和模型推断都不算确认。
- 所有阶段支持 `修改`、`返回`、`取消`。
- 用户要求优先，但 Skill 必须指出明显的不协调、可读性、版权或品牌完整性风险。
- 只有用户确认接受风险或采用调整后，才推进到下一阶段。
- 只有 `qa_state = GENERATION_READY` 才能调用图片工具。

### 9.2 下游失效规则

| 变更项 | 保留 | 必须重新确认 |
|---|---|---|
| 项目理解 | 原始来源 | 所有下游项 |
| 文案方向 | 项目理解 | 文案草案、shot list、协调性、生成确认 |
| 画面风格 | 项目理解、文案方向 | 字体、shot list、输出适配、协调性、生成确认 |
| 字体 | 上游内容 | 文案排版、shot list、协调性、生成确认 |
| 公司 LOGO | 上游内容 | LOGO 安全区、shot list、协调性、生成确认 |
| 项目标志 | 上游内容 | 标志处理方式、shot list、协调性、生成确认 |
| IP 角色 | 上游内容 | IP 使用位置、动作、shot list、协调性、生成确认 |
| 输出规格 | 上游内容 | 协调性、生成确认 |
| 某张图局部问题 | 所有锁定上游项 | 该图变更摘要与再次生成确认 |

---

## 10. 上下文分析

BrandLoom 只分析当前真实可访问的材料：

- 当前用户消息。
- 当前会话中可访问的历史消息。
- 当前会话上传且可读取的文件。
- 用户提供的公开链接。
- workspace 中的 README、说明文档、截图和品牌资产。
- 已存在的 `.brandloom/brand-brief.json`。

新会话无法访问旧对话时，不得声称已读取。应提供：

1. 上传对话导出文件。
2. 粘贴项目说明。
3. 提供公开项目链接。
4. 上传 README 或截图。
5. 只按当前简述分析。

### 10.1 分析结果

```text
项目名称
项目类型
核心功能
目标用户
主要痛点
使用后得到什么
可验证依据
推断项
未确认信息
已识别附件
已识别链接
已有品牌资产
```

### 10.2 文案证据状态

- `verified`：README、代码、文档或可核验页面明确支持。
- `user_supplied`：用户明确提供。
- `inferred`：根据材料推断，必须在最终确认中标注。
- `unsupported`：无依据，不得进入正式宣传文案。
- `conceptual_mockup`：仅用于界面示意，不能当作真实指标或产品状态。

不得擅自写入虚构用户数量、性能比例、安全分数、发布状态或尚未实现的功能。

---

## 11. 文案方向

`COPY_DIRECTION_PENDING` 提供：

1. **项目介绍型（推荐）**：项目名称、一句话定位、项目类型、核心价值。
2. **痛点—解决方案—结果型**：问题、解决方式和用户得到的结果。
3. **核心功能型**：项目名称、3–4 个能力点和输出结果。
4. **使用场景与工作流型**：目标用户、输入、处理过程和输出。
5. **商业转化型**：价值标题、收益、证明和行动引导。

确认方向后先交付可编辑的纯文本文案草案，不直接生成图片。

---

## 12. 画面风格

### 12.1 默认：`reference-adaptive`

对附件1–6进行风格聚类，选择最适合当前项目的一个主家族，而不是机械混合：

- `bright-saas-real-scene`：浅色 SaaS、真实办公场景、左文右图、蓝紫渐变。
- `dark-neon-product`：深色霓虹科技、紫蓝光效、产品 UI 与真实桌面融合。
- `high-density-commercial`：黑金、高信息密度、强标题和功能清单。
- `cinematic-monitor-hero`：真实办公室、中心显示器、电影感软件展示和大字覆盖。

分析输出必须说明：

```text
选择的主家族
主色与辅助色
背景类型
场景类型
构图方式
信息密度
光线
按钮与标签样式
图标表现
明确排除的冲突特征
```

### 12.2 额外风格一：`editorial-minimal`

- 大量留白。
- 网格化编辑式排版。
- 大标题和少量产品截图。
- 无复杂光效和大量功能说明。
- 适合 GitHub 与长期品牌使用。

### 12.3 额外风格二：`soft-3d-brand`

- 柔和 3D 项目标志。
- 浅色渐变与轻玻璃质感。
- 更强调 App Icon 与平台商品图表现。
- 适合 Skill 商店和产品目录。

---

## 13. 字体系统

字体选择是一套组合，不是单一字体。Skill 不附带字体文件。

1. **微软雅黑 + Segoe UI**：基础、稳健、Windows 兼容。
2. **思源黑体 + Inter**：现代、开源项目感、中英文混排。
3. **HarmonyOS Sans + Inter**：清爽科技、适合 AI 与 SaaS。
4. **阿里妈妈数黑体 + Montserrat**：强商业标题；只有本机存在且使用许可满足时使用。
5. **得意黑 + Space Grotesk**：年轻、艺术、辨识度强；只有本机存在且使用许可满足时使用。

字体解析顺序：

```text
用户确认字体
  → 项目指定字体路径
  → 系统字体目录
  → 已确认的替代字体
  → 阻塞并请求用户选择
```

不得静默替换字体。文字无法在安全区内排下时，返回文案或字体阶段，不得自动删除文案。

---

## 14. 公司 LOGO 与项目标志

### 14.1 公司 LOGO

上传后必须确认：

1. 仅本次使用。
2. 保存到当前项目，不设默认。
3. 保存到当前项目并设为项目默认。
4. 保存到个人素材库，不设默认。
5. 保存到个人素材库并设为个人默认。

并确认：

- 拥有或已获得必要使用权。
- 允许的操作范围。

默认允许：

```text
scale
position
recolor_monochrome（仅用户确认后）
opacity（仅用户确认后）
external_shadow（仅用户确认后）
```

默认禁止：

```text
redraw
distort
change_letterforms
change_geometry
use_as_training_reference
```

### 14.2 项目标志

选项：

1. 使用当前已上传项目标志。
2. 上传新的项目标志。
3. 使用项目素材库中的标志。
4. 本次不放项目标志。
5. 明确进入“生成新项目标志概念”分支。

用户上传项目标志后可选择：

- 原样使用。
- 单色化。
- 品牌渐变化。
- 轻 3D 或材质化。
- 简化为小尺寸 App Icon。

每一种处理方式都要先给出可能的辨识度风险并获得确认。

---

## 15. 内置 IP 与组合

三个 IP 同等级默认可选：

| ID | 形象 | 默认职责 |
|---|---|---|
| `author-anime` | 黑发动漫人物 | 作者/品牌代表、产品讲解者、界面展示者 |
| `tuotuo` | 蓝色角色 | AI 助手、系统操作者、工作流执行者 |
| `xingbi` | 黄色星星 | 成果、亮点、方向、反馈和成功状态 |

第一层菜单：

1. 黑发动漫人物。
2. 拓拓。
3. 星比。
4. 拓拓 + 星比。
5. 更多组合或自定义 IP。

第二层菜单：

1. 黑发人物 + 拓拓。
2. 黑发人物 + 星比。
3. 黑发人物 + 拓拓 + 星比。
4. 上传自定义 IP。
5. 返回上一层。

组合职责：

```text
黑发人物：讲解和展示
拓拓：执行项目核心动作
星比：表示结果、方向或反馈
```

不得让多个角色重复表达同一层信息。

### 15.1 LOGO 与封面分别使用

1. 两张图使用同一组角色。
2. LOGO 使用单个角色，封面使用组合（推荐）。
3. LOGO 不放 IP，封面使用角色。
4. 分别自定义。
5. 返回修改角色。

若 1:1 画面中角色过多，必须触发协调性提示。

### 15.2 自定义 IP

流程：

```text
上传真实可访问参考
  → 仅提炼抽象特征草稿
  → 用户确认 profile
  → 确认使用权
  → 确认保存范围和默认范围
  → 才可生成
```

授权状态：

- `missing`
- `unknown`
- `draft_unconfirmed`
- `analysis_only`
- `user_authorized`

只有 `user_authorized` 可以进入生成。

---

## 16. 默认 shot list

### 16.1 LOGO 主视觉

```text
类型：logo-card
比例：1:1
尺寸：2048 × 2048
顶部：公司 LOGO
左侧：项目名称、定位和 Skill 标签
左下：项目 App Icon 或项目标志
右侧：真实场景和产品界面
文字密度：低
背景：真实场景浅景深
重点：项目名称、项目标志、公司品牌
```

### 16.2 封面

```text
类型：cover
比例：2:1
尺寸：2048 × 1024
左上：公司 LOGO、项目标志、项目名称
左侧：核心文案和 3–4 个功能点
中部：视觉隐喻、保护元素或主动作
右侧：产品 UI、设备和 IP 角色
背景：真实办公场景
一致性：复用已确认的标志、配色、字体和 IP profile
```

`SHOT_LIST_PENDING`：

1. 确认推荐方案。
2. 调整 LOGO 主视觉布局。
3. 调整封面布局。
4. 调整功能点数量或角色动作。
5. 只交付方案和提示词。

---

## 17. 输出规格

### 17.1 默认

```json
{
  "logo_card": {
    "aspect_ratio": "1:1",
    "width": 2048,
    "height": 2048,
    "format": "PNG",
    "color_space": "sRGB",
    "safe_margin_percent": 6
  },
  "cover": {
    "aspect_ratio": "2:1",
    "width": 2048,
    "height": 1024,
    "format": "PNG",
    "color_space": "sRGB",
    "safe_margin_percent": 5
  }
}
```

### 17.2 可选

- GitHub Social Preview：1280 × 640。
- 仅 LOGO 主视觉。
- 仅封面。
- 中英文双版本。
- 自定义尺寸；必须重新检查模板安全区。

---

## 18. 数据格式

运行时使用 JSON，避免为 YAML 增加第二个解析依赖。

### 18.1 `qa-state.json`

```json
{
  "schema_version": "1.0",
  "session_id": "20260831-142500-agentguardian",
  "mode": "new",
  "state": "STYLE_PENDING",
  "project_slug": "agentguardian",
  "source_refs": [],
  "confirmed": {
    "context": true,
    "copy_direction": "project-introduction"
  },
  "invalidated": [],
  "generation_backend": "host_builtin_image_tool",
  "updated_at": "2026-08-31T14:25:00+08:00"
}
```

### 18.2 `brand-brief.json`

```json
{
  "schema_version": "1.0",
  "project": {
    "name": "AgentGuardian",
    "slug": "agentguardian",
    "type": "local-first-security-auditor",
    "summary": "本地优先的 AI 智能体安全审计工具",
    "audience": ["独立开发者", "AI Agent 使用者"],
    "pain_points": ["不清楚本地数据是否会被意外访问"],
    "outcomes": ["在使用智能体前完成只读检查"]
  },
  "copy": {
    "direction": "project-introduction",
    "language": "zh-CN",
    "title": "智能体守护者",
    "subtitle": "本地优先的 AI 智能体安全审计工具",
    "value_line": "在智能体接触你的数据前，先完成审计。"
  },
  "style": {
    "profile": "bright-saas-real-scene",
    "palette": {
      "primary": "#15356F",
      "secondary": "#536DFE",
      "accent": "#38C6D9",
      "background": "#F7F9FC"
    },
    "lighting": "soft-daylight",
    "density": "low"
  },
  "fonts": {
    "profile": "harmonyos-inter",
    "heading": "HarmonyOS Sans SC Bold",
    "body": "HarmonyOS Sans SC Regular",
    "latin": "Inter"
  },
  "assets": {
    "company_logo": "enhe-company-logo-black-v1",
    "project_mark": "agentguardian-mark-v1",
    "logo_card_ip": ["tuotuo"],
    "cover_ip": ["author-anime", "tuotuo", "xingbi"]
  },
  "outputs": {
    "logo_card": {"width": 2048, "height": 2048},
    "cover": {"width": 2048, "height": 1024}
  }
}
```

### 18.3 `asset-manifest.json`

每个资产至少包含：

```json
{
  "asset_id": "enhe-company-logo-black-v1",
  "category": "company-logo",
  "scope": "project",
  "relative_path": "library/company-logo/enhe-company-logo-black-v1.png",
  "sha256": "hex-digest",
  "dimensions": {"width": 1920, "height": 500},
  "rights_status": "user_authorized",
  "save_scope_confirmed": true,
  "default_scope": "project",
  "allowed_operations": ["scale", "position"],
  "forbidden_operations": ["redraw", "distort", "change_letterforms"],
  "created_at": "2026-08-31T14:25:00+08:00"
}
```

### 18.4 `generation-manifest-v01.json`

记录：

- 品牌档案哈希。
- 使用的所有资产 ID 与 SHA-256。
- 底图提示词。
- 图片工具返回的原始路径。
- 合成模板与字体路径。
- 输出路径。
- QA 结果。
- 版本与时间。
- 不记录密钥、Cookie、账号或完整私人对话。

---

## 19. 素材库

### 19.1 三种 scope

1. `skill-defaults`：Skill 内置只读。
2. `project`：当前 workspace 的 `.brandloom/library/`。
3. `personal`：`$CODEX_HOME/brandloom/library/` 或 `~/.codex/brandloom/library/`。

### 19.2 注册规则

- 计算 SHA-256。
- 同 scope、同类别、同哈希时复用已有资产。
- 文件名使用安全 slug 和版本号。
- 不覆盖原文件。
- 每个 scope、每个类别最多一个默认项。
- 新默认项会取消旧默认标记，但不会删除旧资产。
- 没有保存确认时只在本次会话中使用。
- 没有权利确认时只能 `analysis_only`。

### 19.3 默认解析顺序

```text
本次明确选择
  → 当前项目默认
  → 个人默认
  → Skill 内置默认可选菜单
  → 阻塞并询问
```

---

## 20. 权利与公开发行

附件1–6中的第三方商业设计只能用于本地分析其抽象风格，不能进入公开仓库或发行包。

公开 Skill 中只允许包含：

- 用户明确拥有并授权公开分发的 ENHE LOGO。
- 用户明确拥有并授权公开分发的三个内置 IP。
- 用户自有或明确授权的示例输出。
- 抽象化的风格文字描述。

在将候选内置素材复制到 `brandloom/assets/defaults/` 前，必须完成一次关键门禁：

1. 用户确认拥有或已获得公开分发权。
2. 为每个源文件记录 SHA-256。
3. 创建 `provenance.json`。
4. 未通过时，Skill 仍可运行，但该资产只能保存在用户本地素材库，不能进入发行包。

---

## 21. 生成与确定性合成

### 21.1 底图生成原则

图片工具只生成：

- 真实场景。
- 设备、工作台和环境。
- 不含关键文字的界面占位。
- 不含公司 LOGO 的预留区域。
- 与品牌档案一致的颜色、光线和构图。
- 必要时包含经授权 IP 角色。

图片工具不得负责：

- 公司 LOGO 重绘。
- 项目名称的最终排版。
- 中文功能点。
- 精确按钮文字。
- 版权或发布状态声明。

### 21.2 合成顺序

```text
读取底图
  → 校验尺寸与文件存在
  → 放置项目标志
  → 放置公司 LOGO 原文件
  → 排版项目名称、副标题和标签
  → 排版功能点
  → 放置可选 UI 截图
  → 执行安全区与溢出检查
  → 输出新版本 PNG
  → 写入 generation manifest
```

### 21.3 字体与文字

- 使用 Pillow `ImageFont.truetype`。
- 支持用户指定换行。
- 自动缩小只允许在模板定义的最小字号以上。
- 达到最小字号仍溢出时硬停止。
- 不删除文案，不改写已确认文本。
- 本地化时复用同一底图、公司 LOGO、项目标志和 IP 素材，只替换文案与必要布局。

### 21.4 图片工具失败

以下任一发生时硬停止：

- 当前宿主没有可用内置图片工具。
- 工具调用失败。
- 返回路径为空。
- 返回文件不存在。
- 输出不是可读取图片。
- 输出比例与任务严重不符。

不得自动改用 API Key、Images API、第三方提供商或递归启动 Codex。

---

## 22. 协调性审查

`COHERENCE_REVIEW_PENDING` 检查：

- 画风与字体是否冲突。
- 颜色与公司 LOGO 对比度是否不足。
- 1:1 画面是否角色过多。
- 标题和功能点是否过长。
- 项目标志材质化是否破坏辨识度。
- IP 是否只是装饰。
- 真实场景是否抢夺标题。
- LOGO 与封面是否像两个不同项目。
- 用户要求是否触发第三方品牌复制风险。

出现问题时提供：

1. 保持用户要求并接受风险。
2. 采用推荐调整。
3. 修改当前要求。
4. 返回指定阶段。
5. 取消。

---

## 23. 内部 QA

### 23.1 文字

- 与 `brand-brief.json` 完全一致。
- 无乱码、错字和意外大小写。
- 不超安全区。
- 使用已确认字体或已确认替代字体。
- 不出现模型生成的伪中文作为关键内容。

### 23.2 品牌

- 公司 LOGO 源文件哈希可追溯。
- 等比例缩放。
- 未改变字形或几何结构。
- 项目标志处理模式已确认。
- 不出现第三方品牌、水印或误导性官方背书。

### 23.3 IP

- 外形与 profile 一致。
- 角色承担明确动作。
- 组合职责不重复。
- 未确认或 `analysis_only` 的自定义 IP 未进入生成。

### 23.4 规格

- `logo-card` 为 2048 × 2048。
- `cover` 为 2048 × 1024。
- PNG 可正常解码。
- sRGB。
- 目标路径未覆盖旧文件。
- manifest 完整。

### 23.5 用户验收

LOGO 主视觉先验收：

1. 接受并继续生成封面。
2. 修改文字。
3. 修改构图。
4. 修改项目标志或 IP。
5. 返回画风或字体。

封面验收：

1. 接受全部并交付。
2. 修改指定图片。
3. 仅修改文字或布局。
4. 返回修改画风、字体或 IP。
5. 保留当前版本并结束。

---

## 24. 安全与隐私

- 不读取或保存 API Key、Token、Cookie、密码或支付信息。
- 不把素材库发送到云端存储。
- 不默认保存完整对话。
- 不使用用户素材训练模型。
- 不自动 Git add 用户本地 `.brandloom/`。
- `.gitignore` 必须忽略 `.brandloom/`、`staging/brand-assets/` 和临时输出。
- 公开示例必须人工复核并清除本地路径、账号、邮箱和私密信息。
- 外部发布时由用户人工复核，并说明 AI 参与。

---

## 25. 技术栈与依赖

- Python 3.12 或更高。
- Pillow 12.3.0，唯一运行时第三方依赖。
- Python 标准库：`argparse`、`dataclasses`、`enum`、`hashlib`、`json`、`pathlib`、`shutil`、`unittest`。
- Markdown 作为 Skill 指令与参考文档。
- JSON 作为运行时状态、模板、manifest 和品牌档案格式。
- GitHub Actions 执行标准库测试、静态合同检查和 Actions CodeQL。

---

## 26. 验收标准

### 26.1 QA

- 未完成全部门禁时无法进入 `GENERATION_READY`。
- 每个阶段一次只问一个问题。
- 用户变更后正确失效下游选择。
- 自定义要求会触发协调性分析。
- `plan-only` 不调用图片工具。

### 26.2 素材库

- 每个上传素材都要求保存范围与默认范围确认。
- 未确认保存时不复制到素材库。
- 哈希重复时复用，不产生重复文件。
- 不覆盖原始文件和历史版本。
- 权利不明时阻塞公开打包和生成使用。

### 26.3 合成

- 公司 LOGO 使用原文件。
- 关键文字与品牌档案逐字一致。
- 字体缺失时阻塞，不静默替换。
- 文字溢出时阻塞，不删除内容。
- LOGO 与封面复用同一品牌档案。

### 26.4 交付

- 默认生成 1 张 1:1 LOGO 主视觉和 1 张 2:1 封面。
- 先验收 LOGO，再生成封面。
- 输出有版本号和 manifest。
- 旧文件保留。
- README 提供安装、使用、素材授权和失败处理说明。

---

## 27. 发布范围

### V0.1：可分析、可完成 QA

- Skill 骨架。
- 状态机。
- 文案、画风、字体、IP 和规格参考。
- 不调用图片工具也能完整走完方案流程。

### V0.2：本地素材库与确定性合成

- 项目与个人素材库。
- 哈希、默认项、授权和版本。
- Pillow 排版、LOGO 合成和模板渲染。

### V0.3：完整生成闭环

- 内置图片工具底图生成。
- LOGO 验收后生成封面。
- 本地化、编辑、内部 QA 和 manifest。

### V1.0：公开发行候选

- 三个内置 IP 与 ENHE LOGO 的公开授权记录。
- 完整 README、示例、CI 和发行包。
- 在至少两个独立工作区完成安装与生成验收。
