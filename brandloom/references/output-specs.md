# 输出规格

默认输出为 PNG、sRGB，且不覆盖旧版本：`logo-card` 1254×1254、1:1、安全边距约 6%；`cover` 1774×887、2:1、安全边距约 5%。GitHub Social Preview 保持 1280×640。可选输出包括 logo-only、cover-only、bilingual 和 custom dimensions；自定义尺寸必须重新检查比例、安全区和可读性，宿主返回无效尺寸时不得通过缩放伪造验收。所有版本写入 generation manifest。
