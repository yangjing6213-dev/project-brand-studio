# BrandLoom

BrandLoom 是用于 Codex 的品牌视觉工作流 Skill：它以一次一个问题的确认式 QA，整理项目上下文、文案、风格、字体、权利和输出规格，再生成可追溯的 LOGO 主视觉与封面。

## 安装与调用

将本仓库的 `brandloom/` 目录复制到 Codex skills 目录（通常为 `$CODEX_HOME/skills/brandloom/`），重新打开工作区后使用：

```text
Use $brandloom
```

例如：`Use $brandloom，为我的开源项目制作中英文 LOGO 主视觉和 GitHub 封面。`

## QA 与素材

BrandLoom 每次只询问一个未确认问题；信息变更会按失效矩阵重新确认。素材库保存使用权、保存 scope 与默认 scope。公司正式 LOGO 不交给图片模型重绘，也不拉伸、改字形或改几何结构；关键中英文文字由 Pillow 确定性排版。

内置 IP 为 `author-anime`、`tuotuo`、`xingbi`，三者同级可选，支持单独、两两与三者组合。LOGO 主视觉和封面可分别选择 IP 组合。支持中文与英文版本切换，本地化复用已确认的底图和素材哈希而不覆盖原语言版本。

## 生成与边界

只有达到 `GENERATION_READY` 且已获明确确认时，才可调用宿主内置图片工具。图片工具不可用、失败、返回空路径或文件不可读时会硬停止：不会索取 API Key、改用 Images API/SDK/第三方服务或递归 Codex。

所有上传素材必须确认使用权、保存 scope 与默认 scope。公开包只含具有 provenance 且 `authorization_status` 为 `user_authorized` 的资产；第三方商业海报仅可提炼抽象风格，不能进入发行包。请勿输入私密资料、密钥、Token、Cookie 或未经授权的人像/品牌素材。

## 本地运行与开发

需要 Python 3.12 与唯一运行时依赖 Pillow 12.3.0：

```powershell
py -3.12 -m pip install -r requirements-runtime.txt
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
py -3.12 scripts/build_skill_package.py
```

构建产物为 `dist/brandloom.zip`，只打包 `brandloom/` 的可发行内容；构建会拒绝缺失授权 provenance 的图片资产。开发期状态、staging 素材与本地输出均不加入 Git。
