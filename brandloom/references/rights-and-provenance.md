# 权利与来源

附件1–6第三方海报只能本地抽象分析，不能公开发行。自定义 IP 必须经历：真实可访问参考 → 抽象特征草稿 → 用户确认 profile → 确认使用权 → 确认保存/默认范围 → 生成。状态 `missing`、`unknown`、`draft_unconfirmed`、`analysis_only` 均禁止生成；只有 `user_authorized` 可生成。

公开包仅可包含用户明确授权的公司 LOGO、内置 IP 或自有示例；保存前记录 SHA-256 和 provenance。无权利确认的素材仅 `analysis_only`，不上传、不训练、不进入发行包。

公司 LOGO 默认只允许 `scale`、`position`；规范 operation `recolor_monochrome` 映射为 concrete treatment `monochrome-black`，以及 `opacity`、`external_shadow` 均需逐项用户确认。白色 `enhe-white-v2` 变体的 machine-readable metadata 明确禁止 `recolor_monochrome`。始终禁止 `redraw`、`distort`、`change_letterforms`、`change_geometry`、`use_as_training_reference`。
