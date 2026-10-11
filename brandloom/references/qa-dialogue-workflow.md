# QA 对话工作流

## 状态机

`INTAKE → CONTEXT_ANALYSIS → CONTEXT_CONFIRM_PENDING → OUTPUT_TARGET_PENDING → OUTPUT_SPEC_PENDING → COPY_DIRECTION_PENDING → STYLE_PENDING → FONT_PENDING → COMPANY_LOGO_PENDING → PROJECT_MARK_PENDING → IP_CAST_PENDING → IP_COMBINATION_PENDING → (CUSTOM_IP_REFERENCE_PENDING → CUSTOM_IP_DRAFT_PENDING → RIGHTS_CONFIRM_PENDING)? → IP_USAGE_PENDING → SHOT_LIST_PENDING → COHERENCE_REVIEW_PENDING → GENERATION_CONFIRM_PENDING → GENERATION_READY → GENERATE_COVER_BASE → COMPOSE_COVER → INTERNAL_COVER_QA → USER_REVIEW → DELIVERED`；任意待确认状态可 `CANCELLED`。

一次只问一个问题。每阶段必须在用户消息中显示选项（使用 A/B/C 等标签），明确写出各选项的实际差异，并标注“推荐”；不得只问“选哪个”、只暗示选项或省略推荐。平台目标可多选，其余单项问题互斥。推荐、默认、沉默和模型推断都不算确认。用户可输入自定义要求。所有阶段支持 `修改`、`返回`、`取消`；发现版权、可读性或协调性风险时先提示，只有用户接受风险或采用调整后才推进。平台与尺寸必须在文案、画风等视觉要求之前确认；不生成 1:1 LOGO 方形图。

### 提问模板

发给用户的每条确认消息都必须直接包含选项，不能只在内部知道选项或让用户猜：

```text
本次只确认一个问题：[用一句话说明要决定什么]
A. [选项及实际结果]
B. [选项及实际结果]（推荐）— [结合已分析的项目内容和目标用途，明确说明推荐理由]
C. [选项及实际结果]
也可以直接描述你的自定义要求。
```

推荐项必须结合已分析的项目内容和目标用途，明确说明推荐理由；不得每次固定推荐同一项或把所有目标都标成推荐。多选时明确说明可以多选。若一个阶段包含多个独立决定（例如平台尺寸、语言、文案策略、文案方向、场景和流程卡片），留在该待确认阶段逐轮提问，每轮只问其中一个；收齐并记录后才确认该阶段。不得把多个问题塞进一条消息，或用一次“确认”代替尚未展示的选项。

## 确认值与 CLI

每个 `*_PENDING` 状态只接受下表对应的确认 key，必须先确认再离开该状态（取消除外）。确认式 key 的值必须是 JSON 布尔值 `true`；`yes`、`no`、`false`、`拒绝`、`0` 等原始文本均会被拒绝。命令行示例：

`brandloom state-confirm --workspace <dir> --key context --value true --state OUTPUT_TARGET_PENDING`

平台目标确认示例：`brandloom state-confirm --workspace <dir> --key output_targets --value true --state OUTPUT_SPEC_PENDING`。具体选择的平台、封面用途与像素尺寸另记入当前项目的 `brand-brief.json`，不能只靠布尔确认推断。

`ip_cast` 仅接受 `author-anime`、`tuotuo`、`xingbi`、`custom`；`rights` 仅接受 `missing`、`unknown`、`draft_unconfirmed`、`analysis_only`、`user_authorized`。只有 `rights=user_authorized` 的自定义 IP 会通过生成门禁。

| 待确认状态 | 唯一确认 key |
|---|---|
| `CONTEXT_CONFIRM_PENDING` | `context` |
| `OUTPUT_TARGET_PENDING` | `output_targets` |
| `OUTPUT_SPEC_PENDING` | `output_spec` |
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
| `COHERENCE_REVIEW_PENDING` | `coherence` |
| `GENERATION_CONFIRM_PENDING` | `generation_confirmation` |

## 菜单

- `OUTPUT_TARGET_PENDING`：逐项显示带字母的目标选项及用途：A. YouTube 长视频缩略图；B. YouTube Shorts 封面；C. YouTube 频道横幅；D. 抖音作品封面；E. 小红书笔记封面；F. GitHub Social Preview；G. 自定义尺寸。注明此题可多选；推荐哪些选项必须结合已分析出的项目用途和用户目标，不能固定推荐全部平台。尺寸和规格性质在下一阶段逐项确认。不得把方形 LOGO 主视觉作为输出选项。
- `OUTPUT_SPEC_PENDING`：对已选目标逐个确认精确宽、高、比例、安全区及规格性质，按 `output-specs.md` 标清“官方推荐 / 实用建议 / 用户自定义”；自定义宽、高每边 320–8192 px、总像素不超过 1600 万。尺寸确认后，再逐个平台单独询问语言：A. 每个平台按目标读者选择一种语言（推荐，需说明依据）；B. 每个平台都生成中文和英文；C. 所有平台统一一种语言。没有确认用途、尺寸和语言时不得推进；把每项用途、像素、比例、规格口径和语言记录到 `brand-brief.json` 的 `outputs.targets`，不能把推荐值当作用户确认。
- `COPY_DIRECTION_PENDING`：保持本状态并分轮提问。先问文案策略：A. 同一核心卖点、按平台调整文案长度和信息量（推荐，若目标平台不同）；B. 所有平台使用同一文案；C. 逐平台采用不同重点。确认后再单独问内容方向：A. 项目介绍型；B. 痛点—解决方案—结果型；C. 核心功能型；D. 使用场景与工作流型；E. 转化介绍型；根据项目分析推荐一项并解释理由。之后按已确认语言和信息密度起草每个平台的标题、副标题、卖点和列表，另发一条消息让用户接受或修改文案；全部确认后才记录 `copy=true` 并进入下一阶段。将策略和最终文案写入 `brand-brief.json` 的 `outputs.targets[].copy`，不能只记录策略名或留存未确认文案。
- `STYLE_PENDING`：先分轮确认跨平台视觉策略，再确认主视觉风格；不能在同一条消息中询问多个决定。跨平台策略选项为：A. 品牌统一、版式适配（保留品牌色与核心卖点，但按各平台重做构图、文字量、主体大小和安全区；在多平台输出且项目需要统一识别时推荐）；B. 各平台独立设计；C. 逐个平台指定。需根据用户已选平台数量和宣传目的显示一个推荐项及理由。随后展示四个带字母的风格选项，并结合项目内容与平台用途只推荐最合适的一项：A. 创作者桌面手写标题（`creator-desk-handwritten`，附件1：暖色真实创作空间、桌前人物、手写感标题）；B. 演讲舞台大屏海报（`stage-screen-poster`，附件2的舞台场景 + 附件3的大字分层排版）；C. 明亮 SaaS 产品展示（`light-saas-product-showcase`，附件4的浅色产品展示、界面主视觉与功能卡片）；D. 沿用当前项目已有风格（`project-existing-style`，只可基于该项目已确认的品牌档案或已通过视觉成品）。没有可复用的 D 类依据时，说明缺少素材，让用户改选 A–C 或补充项目参考；不得猜测。不得继续显示旧的三类主风格菜单。

  选择 A/B 后必须出现独立的人物素材问题，明确显示：A. 现在上传一张有权使用的人物照片（推荐；能按用户指定的长相设计）；B. 使用已授权素材库中的人物照片（仅在确有该素材时显示）；C. 改选 C/D；D. 取消。风格附件中的人物只作氛围/构图参考，不得充当身份来源。没有可用人物素材时不得确认风格或生成。收到照片后再分别确认使用权（确认拥有权利/已获当事人必要授权才继续）、保存范围（仅本次/当前项目/个人素材库）和默认范围（不设默认/项目默认/个人默认）；推荐人物照仅本次使用、不设默认。把素材授权不清楚或拒绝授权作为停止条件。

 选择 B 时，在人物素材可用后分轮追加两个独立问题。先问穿着风格并展示选项：A. 休闲商务（简洁衬衫/外套；推荐项须根据项目与读者解释）；B. 简洁日常（纯色 T 恤或针织衫）；C. 正式演讲（西装/正式外套）；D. 科技休闲（干净的连帽衫或休闲外套）；E. 自定义。将用户选定的具体穿着写入 `style.presenter_outfit`，缺失时预检失败。再问标题颜色：固定基础色为白色，关键词只使用一种强调色，标题总共两种颜色。选项为 A. 白色 + 从附件3实际取样的亮黄色（适合深色舞台时推荐，展示取样色块/HEX）；B. 白色 + 当前项目已确认的品牌强调色（显示其准确色值）；C. 白色 + 用户自定义颜色（需给色名或 HEX）。每轮只问一件事；结合当前项目和背景显示推荐理由，不得暗中换色。强调色需对预期深海军蓝舞台 `#0A1730` 达到至少 3:1 对比度；未达到时不得预检，需让用户重新选择颜色。风格 B 必须同时保留主讲人物和展示大屏，镜头角度可变化；主标题放在屏幕外，除主标题外的副标题、说明和卖点排入展示大屏。人物、穿着与标题颜色未全部确认前，不得离开 `STYLE_PENDING`。

  选择 C 时不要求人物素材；如要显示准确、可读的产品界面，另请用户提供真实截图，否则只用不带虚构文字的界面形块。选择 D 时核对当前项目已确认来源；若没有来源，不得把通用模板称为项目既有风格。C/D 不询问风格 B 专属的穿着和标题颜色。

  四种风格与适用条件的回答均写入 `brand-brief.json` 的 `style` 对象，记录 profile、跨平台策略、人物素材引用及其权利/保存范围、风格 B 的 `presenter_outfit`、标题颜色、风格 D 的复用来源。人物引用格式为已登记素材 `person_reference: {"asset_id":"...","scope":"project|personal"}`，或仅本次使用的绝对路径 `person_reference: {"path":"...","rights_status":"user_authorized","save_scope":"this_run","default_scope":"none"}`。风格 B 需记录 `title_base_color:"#FFFFFF"`、`title_emphasis_color` 与确切出现在主标题内的 `title_emphasis_text`；强调色需对 `#0A1730` 达到至少 3:1 对比度；缺少任一项均不能预检生成请求。A/B/C 风格参考缺失时，必须询问用户上传/提供参考图（仅本次、仅抽象分析、不设默认），或明确选择文字描述继续；将用户提供的图片路径写入 `style.reference_mode:"provided"` 和 `style.reference_paths`，每项包含 `path`、`rights_status:"analysis_only"`、`save_scope:"this_run"`、`default_scope:"none"`。用户选择文字描述时写入 `style.reference_mode:"text-only"`；不得静默跳过参考。D 必须同时记录 `style.source_description` 和 `style.source_confirmed:true`，或以 `reference_mode:"provided"`、`reference_paths` 指向已通过的项目视觉图，并记录来源描述与确认；未明确确认来源时预检失败。所有适用子问题完成后，才可确认 `style=true` 并进入 `FONT_PENDING`。
- `FONT_PENDING`：微软雅黑 + Segoe UI（推荐）；思源黑体 + Inter；HarmonyOS Sans + Inter；阿里妈妈数黑体 + Montserrat；得意黑 + Space Grotesk。缺失字体必须确认回退。
- `COMPANY_LOGO_PENDING`：一次只确认一个问题：是否在封面使用 LOGO、素材权利、保存范围和默认范围分别提问并逐项记录；不得把权利或保存授权与“使用 LOGO”混为一次确认。必须把明确选择写入 `assets.company_logo`：所选素材的准确 asset ID、`"default"`（用户明确选择已登记默认 LOGO），或 `"none"`（用户明确选择不使用）。字段缺失视为未确认，不能静默选用默认素材。保存范围选项包括仅本次、当前项目、个人库；默认范围单独选择“不设默认 / 设为项目默认 / 设为个人默认”。默认允许 `scale`、`position`；`recolor_monochrome`（规范 operation，映射为 concrete treatment `monochrome-black`）、`opacity`、`external_shadow` 仅在用户确认后允许；禁止 `redraw`、`distort`、`change_letterforms`、`change_geometry`、`use_as_training_reference`。非默认 treatment 必须在此状态记录 `confirmed.company_logo_treatment`。
- `PROJECT_MARK_PENDING`：使用当前上传；上传新的；使用项目库；本次不放；生成新概念分支。
- `IP_CAST_PENDING`：黑发动漫人物；拓拓；星比；拓拓 + 星比（推荐）；更多组合或自定义 IP。`IP_COMBINATION_PENDING`：黑发人物 + 拓拓；黑发人物 + 星比；三者；上传自定义 IP；返回上一层。
- `CUSTOM_IP_REFERENCE_PENDING`：确认真实可访问参考；确认仅抽象分析、不复制外形；补充/更换参考；返回；取消。`CUSTOM_IP_DRAFT_PENDING`：确认抽象 profile 草稿；修改 profile；重新分析；返回；取消。`RIGHTS_CONFIRM_PENDING`：确认 `user_authorized` 使用权；声明 `analysis_only`/`unknown`/`missing`/`draft_unconfirmed`；确认保存 scope 和 default scope；返回；取消。非 `user_authorized` 必须阻塞，不得生成。
- `IP_USAGE_PENDING`：所有封面使用同一组角色；所有封面不放 IP；按平台分别选择（推荐，可逐张控制）；返回修改角色。
- `SHOT_LIST_PENDING`：分轮提问。先问场景策略：A. 同一场景主题、每种画幅单独重构镜头（推荐，若需跨平台品牌一致）；B. 各平台采用不同但协调的场景；C. 用户提供匹配画幅底图。确认后，再问是否放流程卡片、改用核心收益或不放流程内容，并结合项目情况推荐。若选择流程卡片，从项目材料提炼步骤，逐张展示文字让用户确认；无证据支持的项目步骤不得编造。宽版最多 4 步，竖版或小画幅最多 3 步；超出上限时重新展示精简建议并确认，不能静默删减。用户已确认的视觉处理为：卡片用细线边框和约 60% 不透明度（约 40% 透明）的局部磨砂底；只柔化各卡片内部背景，不模糊整张图、不加流程图外框；圆角平滑，文字与边框留足距离。将真实场景描述写入各目标的 `scene_concept`，将通过确认的步骤写入 `outputs.targets[].workflow_steps`。保持品牌色、核心卖点和视觉气质一致，分别调整文案密度、主体大小、安全区和角色位置。
- `COHERENCE_REVIEW_PENDING`：保持要求并接受风险；采用推荐调整（推荐）；修改当前要求；返回指定阶段；取消。
- `GENERATION_CONFIRM_PENDING`：确认一次性生成已选平台封面（推荐）；返回修改平台、尺寸或视觉要求；取消。

封面验收菜单：全部接受并交付；按平台逐张接受；修改指定平台封面；只改文字或布局；返回修改画风、字体、素材或输出尺寸；保留当前版本并结束。每张封面通过后单独记录交付状态；如仍有已选目标未完成，回到 `GENERATION_READY` 继续下一项；全部完成后才进入 `DELIVERED`。不要先做或要求验收方形 LOGO 图。

进入 `GENERATION_READY` 后，每个目标必须先通过 CLI 生成请求预检，再调用图片工具：`python brandloom/scripts/brandloom_cli.py request --workspace <工作区> --target-id <已确认目标ID>`。将 JSON 输出中的 `prompt` 和 `reference_assets` 里的每个 `path` 原样传给宿主图片工具，并保存返回的 `request_id`。预检会检查目标、版式与流程文案、公司 LOGO 和项目标志选择、人物授权、本地风格参考以及封面文案所需字体；失败时不得调用图片工具。它只生成请求，不会调用图片工具。合成时必须将同一 `request_id` 传给 `compose --request-id <预检返回的request_id>`；它绑定当前目标、已确认 brief、提示词和参考素材内容，不能跳过、跨目标复用，或在 brief/参考素材变化后继续使用。

## 失效矩阵

| 变更项 | 保留 | 必须重新确认 |
|---|---|---|
| context | 原始来源 | 输出目标、输出尺寸、文案、风格、字体、LOGO、项目标志、IP、使用、shot list、协调性、生成确认 |
| output-targets | 项目理解 | 所选平台用途、输出尺寸、shot list、协调性、生成确认 |
| output-spec | 项目理解、所选平台 | 输出尺寸、安全区、shot list、协调性、生成确认 |
| copy | 项目理解 | 文案草案、shot list、协调性、生成确认 |
| style | 项目理解、文案方向 | 所选风格及其条件项（人物素材/权利/保存范围、风格 2 穿着与标题强调色、风格 4 来源）、字体、shot list、输出适配、协调性、生成确认 |
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
| 单图局部问题 | 所有已锁定上游项 | 该图变更摘要与再次生成确认 |

`GENERATION_READY` 是唯一图片工具 gate；编辑、返回或任何上游变化都会离开该 gate。确认通过后只生成所选封面版本，不存在 LOGO 方形图生成/验收阶段；每张封面单独运行自动检查并记录版本，人工验收按平台逐张处理。状态机允许一张封面完成后返回 `GENERATION_READY`，直至所选目标全部通过。

## 图片工具边界与失败处理

当前 host 仅允许 `host_builtin_image_tool`，必须处于 `GENERATION_READY`。调用时使用工具返回路径 exactly（原样），不得改写、猜测或扫描路径。底图与目标画幅比例完全相同时，才可在内存中等比例缩放到目标像素；比例不一致时必须停止并为该平台单独生成匹配画幅的底图。不得裁切、拉伸或覆盖原图。放大不会补出图像细节。工具不可用或调用失败、空返回路径、文件缺失/不可读时立即 hard-stop，返回相应阶段并报告原因；不得自动重试。不得使用 API keys、Images API、第三方 provider、递归 Codex 或其他生成后端。
