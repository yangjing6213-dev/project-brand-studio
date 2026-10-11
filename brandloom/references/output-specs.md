# 平台封面输出规格

默认导出 PNG、sRGB；每个已确认的平台用途独立构图、独立检查并创建新版本，不覆盖历史文件。BrandLoom 的封面不再固定为 2:1；也不生成 1:1 LOGO 方形图。

## 平台尺寸与规格口径

| 输出位置 | 推荐输出尺寸 | 比例 | 规格口径与注意点 |
|---|---:|---:|---|
| YouTube 长视频缩略图 | 3840×2160 | 16:9 | YouTube 官方推荐此分辨率；最低宽度 640 px。上传自定义缩略图要求账号已验证；上传大小上限随设备而异。 |
| YouTube Shorts 封面 | 2160×3840 | 9:16 | YouTube 官方推荐此分辨率；最低高度 640 px。自定义 Shorts 缩略图需账号已验证，并只能在电脑端通过 YouTube Studio 添加。 |
| YouTube 频道横幅 | 2560×1440 | 16:9 | 官方推荐尺寸；最低 2048×1152。最低尺寸下文字/标志安全区为 1235×338；上传文件不超过 6 MB。 |
| 抖音作品封面 | 1080×1440 | 3:4 | 实用建议值，不是抖音官方公布的固定像素要求。公开图片上传接口没有规定作品封面的固定像素尺寸；视频发布接口支持传入自定义封面，但没有列出像素/比例规范。发布界面与展示位置可能裁切，重要内容应远离边缘并在账号实际预览。 |
| 小红书笔记封面 | 1080×1440 | 3:4 | 常用工作尺寸，不是官方唯一像素规格。官方开放分享 SDK 对部分分享图片路径说明，宽高比小于 3:4 或大于 2:1、宽度超过 1280 时会裁切；这是 SDK 分享图片行为，不是笔记封面的完整规格承诺。 |
| GitHub 仓库 Social Preview | 1280×640 | 2:1 | GitHub 官方建议 1280×640 获得较佳显示效果，至少 640×320；PNG/JPG/GIF 小于 1 MB。 |
| 自定义 | 用户提供的准确宽×高 | 自动计算 | 必须逐项确认宽、高像素和使用位置；每边 320–8192 px、总像素不超过 1600 万；未确认不得生成。输出尺寸符合用户输入不代表目标平台认可该规格。 |

## 使用规则

- 开始视觉方案前先确认平台、具体用途和画幅；YouTube 必须区分长视频缩略图、Shorts 封面、频道横幅，可多选。
- 用户可多选平台；每个选中位置单独生成适配画面，不把一张已经排版完成的图片硬拉伸成另一种比例。
- 按目标读者逐个平台选择一种输出语言；将平台用途、尺寸、语言及该平台确认后的文案一并写入 `brand-brief.json` 的 `outputs.targets`，不根据平台名称自行猜测目标语言。
- 抖音和小红书的 1080×1440 是建议的工作起点。若用户优先考虑账号内实际发布效果，可先用该尺寸草案，再由用户在发布界面预览/裁切。
- 自定义尺寸需要输入正整数宽、高；按尺寸推导比例并重新确认安全区、文案长度与构图。不得擅自把自定义尺寸当成某个平台的官方要求。
- 目标像素尺寸是最终导出要求；用户已确认：底图与目标画幅比例完全相同时，才允许在内存中按比例缩放到指定像素；比例不一致时停止并单独生成匹配画幅的底图。不得裁切，不得横向或纵向拉伸，也不改写原底图。放大只改变像素尺寸，不会补出真实细节。
- 平台公开规格包含文件大小上限时，交付前也会校验：GitHub Social Preview 必须小于 1 MB，YouTube 频道横幅不得超过 6 MB；超限会阻止交付，不会假报通过。
- 关键中文/英文文字与公司 LOGO 仍由确定性排版/合成处理；公司 LOGO 不重绘、不拉伸、不改字形或几何结构。
- 每个目标分别生成、排版、验收和交付；每个目标保存独立图片版本、JSON 布局模板和 manifest。逐张通过后，才标记整个所选平台批次为完成。
- 流程卡片的磨砂处理只发生在卡片内部：约 60% 透明度（约 40% 不透明）填充、局部柔化、细线边框；不模糊整张底图、不加流程图外框。宽版最多 4 步；竖版最多 3 步；已确认步骤不能为适配画幅而静默删减，超出上限时需要重新确认精简版步骤。

## 官方规格来源

- YouTube 视频与 Shorts 缩略图：[YouTube Help — Add custom thumbnails](https://support.google.com/youtube/answer/72431)
- YouTube 频道横幅：[YouTube Help — Channel banner & profile picture tips](https://support.google.com/youtube/answer/12950272)；[Manage your channel branding](https://support.google.com/youtube/answer/10456525)
- 抖音公开图片上传接口（未列作品封面像素比例）：[抖音开放平台 — 上传图片](https://open.douyin.com/platform/resource/docs/openapi/video-management/douyin/publish-img/upload/)；视频发布接口支持自定义封面但未列尺寸：[抖音开放平台 — 创建视频](https://open.douyin.com/platform/resource/docs/openapi/video-management/douyin/create/create-video)
- 小红书分享图片裁切说明：[小红书分享开放平台 — iOS SDK 接入指南](https://agora.xiaohongshu.com/doc/ios)
- GitHub Social Preview：[GitHub Docs — Customizing your repository's social media preview](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/customizing-your-repositorys-social-media-preview)

## 运行代码行为

本地 CLI 支持上述六种平台目标和受限自定义尺寸；输出配置存放在 `.brandloom/brand-brief.json` 的 `outputs.targets`。每项记录用途、尺寸、语言、已确认文案、真实场景描述及（可选）流程卡片内容。平台尺寸由 JSON 规格表解析；每次合成会创建新的 JSON 布局模板、版本化封面与独立 manifest。

CLI 不调用图片服务。宿主 Skill 只在 `GENERATION_READY` 后为每个目标分别请求底图，再把工具返回路径交给本地 CLI；底图比例一致时可无裁切缩放，不一致时立即停止。旧 `logo-card` 命令仅兼容没有平台目标配置的历史工作区；新平台封面配置存在时，该命令会被拒绝。
