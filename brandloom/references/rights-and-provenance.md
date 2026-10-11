# 权利与来源

附件1–6第三方海报只能本地抽象分析，不能公开发行。自定义 IP 必须经历：真实可访问参考 → 抽象特征草稿 → 用户确认 profile → 确认使用权 → 确认保存/默认范围 → 生成。状态 `missing`、`unknown`、`draft_unconfirmed`、`analysis_only` 均禁止生成；只有 `user_authorized` 可生成。

公开包仅可包含用户明确授权的公司 LOGO、内置 IP 或自有示例；保存前记录 SHA-256 和 provenance。无权利确认的素材仅 `analysis_only`，不上传、不训练、不进入发行包。

Style 1/2 使用的人物照片必须由用户单独提供，并确认自己拥有使用权或已取得人物/权利人的必要授权。人物照与风格参考分开记录；不能从风格参考图提取、仿造或替换其人物身份。人物照片的使用范围（仅本次/当前项目/个人素材库）和默认范围（不设默认/项目默认/个人默认）必须分别确认；未确认或权利状态为 `unknown` 时不得生成。默认推荐仅本次使用、不设默认。

四张主视觉风格参考图只保存在本机被 Git 忽略的 `.brandloom/style-reference-library/` 中，仅供抽象分析和图片工具的风格参考，不上传、训练、提交或打包公开发行。除非另行确认权利，不得公开传播原图；不得复制图中人物身份、原文字、商标、产品界面、水印或账号信息。

公司 LOGO 默认只允许 `scale`、`position`；规范 operation `recolor_monochrome` 映射为 concrete treatment `monochrome-black`，以及 `opacity`、`external_shadow` 均需逐项用户确认。白色 `enhe-white-v2` 变体的 machine-readable metadata 明确禁止 `recolor_monochrome`。始终禁止 `redraw`、`distort`、`change_letterforms`、`change_geometry`、`use_as_training_reference`。
