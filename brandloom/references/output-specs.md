# 输出规格

默认输出为 PNG、sRGB，且不覆盖旧版本：`logo-card` 1254×1254、1:1、安全边距约 6%；`cover` 1774×887、2:1、安全边距约 5%。GitHub Social Preview 保持 1280×640。

可选输出包括 logo-only、cover-only、bilingual 和 custom dimensions。自定义尺寸的边界是“本地模板/渲染 API”：调用方必须提供 JSON 模板的准确 `canvas`，使用 `render_brand_asset` 渲染，并再次以 `validate_generated_path(path, expected=(width, height))` 与 `validate_output(expected_dimensions=(width, height))` 校验。`brandloom_cli compose` 和 `build_host_request` 只接受上述固定宿主尺寸，不提供自定义尺寸 CLI 或宿主生成通道；宿主返回无效尺寸时不得通过缩放伪造验收。所有版本写入 generation manifest。
