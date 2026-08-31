# BrandLoom Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个可安装的 `brandloom` Codex Skill，通过确认式 QA、可追溯素材库、内置图片工具和 Pillow 确定性合成，稳定生成项目 LOGO 主视觉与封面。

**Architecture:** Skill 的 Markdown 指令负责理解上下文、推进 QA 和调用宿主内置图片工具；Python 3.12 脚本负责状态、素材库、字体解析、模板渲染、版本管理和 QA。关键文字与公司 LOGO 不由图片模型重绘，而是在底图生成后确定性合成。

**Tech Stack:** Markdown、JSON、Python 3.12+、Pillow 12.3.0、Python `unittest`、GitHub Actions。

**Spec:** `docs/superpowers/specs/2026-08-31-brandloom-design.md`

## Global Constraints

- 仓库名称固定为 `project-brand-studio`，Skill 目录和 front matter 名称固定为 `brandloom`。
- Skill 调用方式固定为 `Use $brandloom`。
- Python 最低版本为 3.12。
- 唯一运行时第三方依赖为 `Pillow==12.3.0`。
- 运行时状态、模板、品牌档案和 manifest 使用 JSON，不增加 YAML 解析依赖。
- 公司 LOGO 默认禁止重绘、拉伸、改变字形和改变几何结构。
- 关键中英文文案必须通过 Pillow 确定性排版。
- 未完成 QA 门禁时不得调用图片工具。
- 不请求、读取、打印或使用 API Key；不得回退到 Images API、第三方图片提供商或递归启动 Codex。
- `.brandloom/`、`staging/brand-assets/` 和本地输出不得自动加入 Git。
- 不覆盖原始素材或已有输出。
- 附件1–6的第三方商业海报不得进入公开发行包。
- ENHE LOGO 与三个内置 IP 只有在用户明确确认公开分发权并记录 SHA-256 后才能进入 `brandloom/assets/defaults/`。
- 每个任务完成后运行目标测试、相关全量测试并检查 `git diff` 与 `git status`。
- 未执行成功的验证不得标记为 PASS。

---

## File Map

### Skill 指令

- `brandloom/SKILL.md`：任务路由、QA 门禁、图片工具调用条件和交付规则。
- `brandloom/agents/openai.yaml`：显示名称、简述、默认调用提示和隐式调用策略。
- `brandloom/references/*.md`：文案、风格、字体、素材、IP、构图、输出、生成和 QA 规则。

### 运行时代码

- `brandloom/scripts/brandloom_cli.py`：命令行入口。
- `brandloom/scripts/brandloom_core/models.py`：枚举与 dataclass。
- `brandloom/scripts/brandloom_core/state_machine.py`：状态转换与下游失效。
- `brandloom/scripts/brandloom_core/asset_library.py`：素材注册、去重、默认项和版本。
- `brandloom/scripts/brandloom_core/fonts.py`：系统字体解析。
- `brandloom/scripts/brandloom_core/layout.py`：模板与文字盒计算。
- `brandloom/scripts/brandloom_core/renderer.py`：Pillow 合成。
- `brandloom/scripts/brandloom_core/prompt_builder.py`：无关键文字底图提示词。
- `brandloom/scripts/brandloom_core/manifests.py`：生成记录。
- `brandloom/scripts/brandloom_core/validation.py`：内部 QA。

### 模板与资产

- `brandloom/templates/*.json`：1:1、2:1 和 Social Preview 模板。
- `brandloom/assets/defaults/`：只包含已授权的公司 LOGO、IP 和项目自有示例。

### 测试与构建

- `tests/test_*.py`：标准库 `unittest`。
- `scripts/build_skill_package.py`：构建最小发行 ZIP。
- `.github/workflows/validate-skill.yml`：测试和包内容检查。
- `.github/workflows/codeql.yml`：GitHub Actions CodeQL。

---

### Task 1: 建立最小可验证 Skill 仓库

**Files:**
- Create: `brandloom/SKILL.md`
- Create: `brandloom/agents/openai.yaml`
- Create: `brandloom/references/architecture.md`
- Create: `tests/test_skill_contract.py`
- Create: `requirements-runtime.txt`
- Create: `.gitignore`
- Create: `.github/workflows/validate-skill.yml`
- Create: `.github/workflows/codeql.yml`

**Interfaces:**
- Produces: 可被后续任务扩展的 Skill 目录、最小引用合同和 CI 入口。
- Consumes: 无。

- [ ] **Step 1: 写失败的仓库合同测试**

Create `tests/test_skill_contract.py`:

```python
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = ROOT / "brandloom"

class SkillContractTests(unittest.TestCase):
    def test_front_matter_and_agent_metadata(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill_text.startswith("---\n"))
        self.assertIn("name: brandloom", skill_text)
        agent_text = (SKILL_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "BrandLoom"', agent_text)
        self.assertIn("Use $brandloom", agent_text)

    def test_all_referenced_markdown_files_exist(self) -> None:
        skill_text = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        references = sorted(set(re.findall(r"references/[A-Za-z0-9_.-]+[.]md", skill_text)))
        self.assertTrue(references)
        for reference in references:
            self.assertTrue((SKILL_ROOT / reference).is_file(), reference)

    def test_runtime_dependency_is_pinned(self) -> None:
        requirements = (ROOT / "requirements-runtime.txt").read_text(encoding="utf-8")
        self.assertEqual(requirements.strip(), "Pillow==12.3.0")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试，确认失败**

Run:

```powershell
py -3.12 -m unittest tests.test_skill_contract -v
```

Expected: FAIL because `brandloom/SKILL.md` and other files do not exist.

- [ ] **Step 3: 创建最小 Skill 文件**

Create `brandloom/SKILL.md`:

```markdown
---
name: brandloom
description: 用于分析项目、对话、附件、链接和品牌素材，并通过确认式 QA 生成或修改项目 LOGO 主视觉、项目标志、GitHub 封面、中英文版本和品牌视觉变体。
---

# BrandLoom

先读取 `references/architecture.md`。任何生成或改图请求都必须先完成确认式 QA；当前状态不是 `GENERATION_READY` 时不得调用图片工具。
```

Create `brandloom/agents/openai.yaml`:

```yaml
interface:
  display_name: "BrandLoom"
  short_description: "通过确认式 QA 生成一致的项目 LOGO 主视觉与封面"
  default_prompt: "Use $brandloom to 先分析当前项目、对话、附件与链接，再逐项确认文案、风格、字体、LOGO、IP、shot list 和输出规格。"
policy:
  allow_implicit_invocation: true
```

Create `brandloom/references/architecture.md` with the architecture, non-goals and terminology copied from the design spec sections 1–5.

Create `requirements-runtime.txt`:

```text
Pillow==12.3.0
```

Create `.gitignore`:

```gitignore
.venv/
__pycache__/
*.py[cod]
.brandloom/
staging/brand-assets/
dist/
build/
```

- [ ] **Step 4: 创建 CI**

Create `.github/workflows/validate-skill.yml`:

```yaml
name: Validate Skill

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install --disable-pip-version-check -r requirements-runtime.txt
      - run: python -m unittest discover -s tests -p "test_*.py" -v
```

Create `.github/workflows/codeql.yml` using `github/codeql-action/init@v4`, `languages: actions`, `build-mode: none`, and `github/codeql-action/analyze@v4`, with `security-events: write`.

- [ ] **Step 5: 运行测试并检查仓库**

Run:

```powershell
py -3.12 -m pip install -r requirements-runtime.txt
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
git diff --check
git status --short
```

Expected: all tests PASS; only Task 1 files are uncommitted.

- [ ] **Step 6: Commit**

```powershell
git add brandloom tests requirements-runtime.txt .gitignore .github
git commit -m "chore: scaffold BrandLoom skill"
```

---

### Task 2: 定义运行时模型与 JSON 序列化

**Files:**
- Create: `brandloom/scripts/brandloom_core/__init__.py`
- Create: `brandloom/scripts/brandloom_core/models.py`
- Create: `brandloom/scripts/brandloom_core/json_io.py`
- Create: `tests/test_models.py`

**Interfaces:**
- Produces:
  - `QAState`
  - `TaskMode`
  - `AssetCategory`
  - `AssetScope`
  - `RightsStatus`
  - `QASession`
  - `AssetRecord`
  - `BrandBrief`
  - `read_json_dataclass(path, cls)`
  - `write_json_dataclass(path, value)`
- Consumes: Python 3.12 standard library.

- [ ] **Step 1: 写失败的模型测试**

Create `tests/test_models.py`:

```python
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from brandloom.scripts.brandloom_core.json_io import read_json_dataclass, write_json_dataclass
from brandloom.scripts.brandloom_core.models import QAState, QASession, TaskMode

class ModelTests(unittest.TestCase):
    def test_session_round_trip(self) -> None:
        session = QASession(
            schema_version="1.0",
            session_id="20260831-test",
            mode=TaskMode.NEW,
            state=QAState.INTAKE,
            project_slug="agentguardian",
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "qa-state.json"
            write_json_dataclass(path, session)
            loaded = read_json_dataclass(path, QASession)
        self.assertEqual(loaded, session)
        self.assertEqual(loaded.state, QAState.INTAKE)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试，确认导入失败**

```powershell
py -3.12 -m unittest tests.test_models -v
```

Expected: FAIL with missing module or class.

- [ ] **Step 3: 实现枚举与 dataclass**

Create `models.py` with `StrEnum` values matching the design spec. The required `QASession` signature is:

```python
@dataclass(frozen=True)
class QASession:
    schema_version: str
    session_id: str
    mode: TaskMode
    state: QAState
    project_slug: str
    source_refs: tuple[str, ...] = ()
    confirmed: dict[str, object] = field(default_factory=dict)
    invalidated: tuple[str, ...] = ()
    generation_backend: str = "host_builtin_image_tool"
    updated_at: str = ""
```

Define `AssetRecord` with exact fields:

```python
@dataclass(frozen=True)
class AssetRecord:
    asset_id: str
    category: AssetCategory
    scope: AssetScope
    relative_path: str
    sha256: str
    width: int
    height: int
    rights_status: RightsStatus
    save_scope_confirmed: bool
    default_scope: AssetScope | None
    allowed_operations: tuple[str, ...]
    forbidden_operations: tuple[str, ...]
    created_at: str
```

Define `BrandBrief` as nested plain dictionaries plus validated top-level fields:

```python
@dataclass(frozen=True)
class BrandBrief:
    schema_version: str
    project: dict[str, object]
    copy: dict[str, object]
    style: dict[str, object]
    fonts: dict[str, object]
    assets: dict[str, object]
    outputs: dict[str, object]
```

- [ ] **Step 4: 实现 JSON round-trip**

`write_json_dataclass()` must convert dataclasses, tuples and enums to JSON-safe values, write UTF-8 with `ensure_ascii=False`, and use atomic replacement through a sibling `.tmp` file.

`read_json_dataclass()` must restore `QASession`, including enum values and tuples. Unsupported classes must raise `TypeError`.

- [ ] **Step 5: 运行测试**

```powershell
py -3.12 -m unittest tests.test_models -v
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
git diff --check
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add brandloom/scripts tests/test_models.py
git commit -m "feat: add BrandLoom runtime models"
```

---

### Task 3: 实现 QA 状态机与下游失效

**Files:**
- Create: `brandloom/scripts/brandloom_core/state_machine.py`
- Create: `tests/test_state_machine.py`

**Interfaces:**
- Consumes: `QASession`, `QAState`.
- Produces:
  - `advance(session: QASession, target: QAState) -> QASession`
  - `confirm(session: QASession, key: str, value: object) -> QASession`
  - `invalidate_from(session: QASession, key: str) -> QASession`
  - `assert_generation_ready(session: QASession) -> None`

- [ ] **Step 1: 写生成门禁和失效测试**

Create `tests/test_state_machine.py`:

```python
import unittest

from brandloom.scripts.brandloom_core.models import QAState, QASession, TaskMode
from brandloom.scripts.brandloom_core.state_machine import (
    GenerationGateError,
    advance,
    assert_generation_ready,
    confirm,
    invalidate_from,
)

def session_at(state: QAState) -> QASession:
    return QASession(
        schema_version="1.0",
        session_id="test",
        mode=TaskMode.NEW,
        state=state,
        project_slug="demo",
    )

class StateMachineTests(unittest.TestCase):
    def test_cannot_skip_from_intake_to_generation_ready(self) -> None:
        with self.assertRaises(ValueError):
            advance(session_at(QAState.INTAKE), QAState.GENERATION_READY)

    def test_generation_gate_blocks_pending_state(self) -> None:
        with self.assertRaises(GenerationGateError):
            assert_generation_ready(session_at(QAState.OUTPUT_SPEC_PENDING))

    def test_style_change_invalidates_font_and_downstream(self) -> None:
        session = session_at(QAState.GENERATION_CONFIRM_PENDING)
        session = confirm(session, "style", "bright-saas-real-scene")
        changed = invalidate_from(session, "style")
        self.assertIn("font", changed.invalidated)
        self.assertIn("shot_list", changed.invalidated)
        self.assertIn("generation_confirmation", changed.invalidated)
        self.assertEqual(changed.state, QAState.FONT_PENDING)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试，确认失败**

```powershell
py -3.12 -m unittest tests.test_state_machine -v
```

Expected: FAIL because `state_machine.py` does not exist.

- [ ] **Step 3: 实现显式转换图**

Create a `TRANSITIONS: dict[QAState, frozenset[QAState]]` that follows the exact design state machine. `advance()` must reject targets not in the current state's set.

Implement `INVALIDATION_RULES`:

```python
INVALIDATION_RULES = {
    "context": (
        QAState.COPY_DIRECTION_PENDING,
        ("copy", "style", "font", "company_logo", "project_mark", "ip_cast",
         "ip_usage", "shot_list", "output_spec", "coherence", "generation_confirmation"),
    ),
    "copy": (
        QAState.COPY_DIRECTION_PENDING,
        ("copy", "shot_list", "coherence", "generation_confirmation"),
    ),
    "style": (
        QAState.FONT_PENDING,
        ("font", "shot_list", "output_spec", "coherence", "generation_confirmation"),
    ),
    "font": (
        QAState.FONT_PENDING,
        ("font", "shot_list", "coherence", "generation_confirmation"),
    ),
    "company_logo": (
        QAState.COMPANY_LOGO_PENDING,
        ("company_logo", "shot_list", "coherence", "generation_confirmation"),
    ),
    "project_mark": (
        QAState.PROJECT_MARK_PENDING,
        ("project_mark", "shot_list", "coherence", "generation_confirmation"),
    ),
    "ip_cast": (
        QAState.IP_CAST_PENDING,
        ("ip_cast", "ip_usage", "shot_list", "coherence", "generation_confirmation"),
    ),
    "output_spec": (
        QAState.OUTPUT_SPEC_PENDING,
        ("output_spec", "coherence", "generation_confirmation"),
    ),
}
```

`assert_generation_ready()` must require `state == QAState.GENERATION_READY` and all required keys present in `confirmed`.

- [ ] **Step 4: 运行测试**

```powershell
py -3.12 -m unittest tests.test_state_machine -v
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add brandloom/scripts/brandloom_core/state_machine.py tests/test_state_machine.py
git commit -m "feat: enforce BrandLoom QA state machine"
```

---

### Task 4: 编写完整 QA、预设与 Skill 路由

**Files:**
- Modify: `brandloom/SKILL.md`
- Create: `brandloom/references/qa-dialogue-workflow.md`
- Create: `brandloom/references/context-analysis.md`
- Create: `brandloom/references/copy-directions.md`
- Create: `brandloom/references/style-presets.md`
- Create: `brandloom/references/font-presets.md`
- Create: `brandloom/references/brand-assets.md`
- Create: `brandloom/references/composition-recipes.md`
- Create: `brandloom/references/output-specs.md`
- Create: `brandloom/references/localization-and-editing.md`
- Create: `brandloom/references/rights-and-provenance.md`
- Create: `brandloom/references/qa-checklist.md`
- Modify: `tests/test_skill_contract.py`

**Interfaces:**
- Produces: Skill 可执行的完整对话规则和静态参考。
- Consumes: 设计规格、`QAState` 名称。

- [ ] **Step 1: 扩展合同测试**

Add tests that assert:

```python
required = {
    "CONTEXT_CONFIRM_PENDING",
    "COPY_DIRECTION_PENDING",
    "STYLE_PENDING",
    "FONT_PENDING",
    "COMPANY_LOGO_PENDING",
    "PROJECT_MARK_PENDING",
    "IP_CAST_PENDING",
    "IP_USAGE_PENDING",
    "SHOT_LIST_PENDING",
    "OUTPUT_SPEC_PENDING",
    "COHERENCE_REVIEW_PENDING",
    "GENERATION_CONFIRM_PENDING",
    "GENERATION_READY",
}
workflow = (SKILL_ROOT / "references" / "qa-dialogue-workflow.md").read_text(encoding="utf-8")
for state in required:
    self.assertIn(state, workflow)
self.assertIn("一次只问一个问题", workflow)
self.assertIn("推荐、默认、沉默和模型推断都不算确认", workflow)
```

Add a test that `SKILL.md` contains `GENERATION_READY` and `host_builtin_image_tool`.

- [ ] **Step 2: 运行测试，确认失败**

```powershell
py -3.12 -m unittest tests.test_skill_contract -v
```

Expected: FAIL for missing reference files and strings.

- [ ] **Step 3: 写 QA 工作流**

`qa-dialogue-workflow.md` must include:

- Full state machine.
- One-question rule.
- Global commands.
- The exact five copy direction options.
- The three style options.
- The five font profiles.
- Company LOGO save/default menu.
- Project mark menu.
- Two-stage IP menu.
- IP usage menu.
- Shot list menu.
- Output specification menu.
- Coherence warning menu.
- Final generation menu.
- Logo review and cover review menus.
- Downstream invalidation matrix.

- [ ] **Step 4: 写参考文件**

Copy the approved requirements from the spec into focused files. Do not repeat unrelated theory. `style-presets.md` must explicitly say attachment1–6 third-party images are local analysis references only and are not distributable assets.

`font-presets.md` must state that no font files are bundled, and missing fonts block until the user confirms a fallback.

`brand-assets.md` must distinguish `company-logo`, `project-mark`, `logo-card`, `cover`, `ip`, `style-reference`, and `ui-screenshot`.

- [ ] **Step 5: 更新 SKILL.md**

`SKILL.md` must route:

- analysis-only / plan-only.
- new generation.
- edit.
- localization.
- variant.
- custom IP.
- missing image tool.
- generation result handling.

It must instruct the agent to read only the references needed for the current stage and not load the full library at once.

- [ ] **Step 6: 运行合同测试**

```powershell
py -3.12 -m unittest tests.test_skill_contract -v
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
git diff --check
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add brandloom/SKILL.md brandloom/references tests/test_skill_contract.py
git commit -m "feat: define BrandLoom confirmation workflow"
```

---

### Task 5: 实现素材库、来源和默认项

**Files:**
- Create: `brandloom/scripts/brandloom_core/paths.py`
- Create: `brandloom/scripts/brandloom_core/asset_library.py`
- Create: `tests/test_asset_library.py`

**Interfaces:**
- Consumes: `AssetRecord`, `AssetCategory`, `AssetScope`, `RightsStatus`.
- Produces:
  - `resolve_personal_root() -> Path`
  - `project_root(workspace: Path) -> Path`
  - `sha256_file(path: Path) -> str`
  - `register_asset(...) -> AssetRecord`
  - `list_assets(...) -> tuple[AssetRecord, ...]`
  - `set_default(...) -> None`
  - `resolve_default(...) -> AssetRecord | None`

- [ ] **Step 1: 写去重、默认和防覆盖测试**

Create tests using `TemporaryDirectory`:

```python
def test_duplicate_hash_reuses_existing_record(self) -> None:
    first = register_asset(..., make_default=False)
    second = register_asset(..., make_default=False)
    self.assertEqual(first.asset_id, second.asset_id)
    self.assertEqual(len(list_assets(...)), 1)

def test_new_default_replaces_flag_without_deleting_old_asset(self) -> None:
    first = register_asset(..., make_default=True)
    second = register_asset(..., make_default=True)
    self.assertEqual(resolve_default(...).asset_id, second.asset_id)
    self.assertTrue((library_root / first.relative_path).exists())

def test_unconfirmed_save_is_rejected(self) -> None:
    with self.assertRaises(ValueError):
        register_asset(..., save_scope_confirmed=False)
```

Also test that a `company-logo` record automatically receives forbidden operations `redraw`, `distort`, `change_letterforms`, `change_geometry`.

- [ ] **Step 2: 运行测试，确认失败**

```powershell
py -3.12 -m unittest tests.test_asset_library -v
```

- [ ] **Step 3: 实现路径解析**

`resolve_personal_root()`:

```python
def resolve_personal_root() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    base = Path(codex_home).expanduser() if codex_home else Path.home() / ".codex"
    return base / "brandloom"
```

`project_root(workspace)` returns `workspace.resolve() / ".brandloom"` and does not create directories until a write operation is confirmed.

- [ ] **Step 4: 实现注册**

`register_asset()` must:

1. Validate source is a regular readable image.
2. Validate `save_scope_confirmed`.
3. Validate rights status is not `missing` or `unknown` for generation-capable assets.
4. Compute SHA-256 and dimensions.
5. Reuse an existing same-scope, same-category, same-hash record.
6. Copy to a versioned name without overwrite.
7. Atomically update `asset-manifest.json`.
8. Set default only when requested.

- [ ] **Step 5: 运行测试**

```powershell
py -3.12 -m unittest tests.test_asset_library -v
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
```

- [ ] **Step 6: Commit**

```powershell
git add brandloom/scripts/brandloom_core tests/test_asset_library.py
git commit -m "feat: add local BrandLoom asset library"
```

---

### Task 6: 添加三个内置 IP 与组合档案

**Critical precondition:** Before this task, the user must place the authorized source files at:

```text
staging/brand-assets/enhe-company-logo.png
staging/brand-assets/author-anime.png
staging/brand-assets/tuotuo-xingbi.png
```

The user must explicitly confirm that these exact files may be included in the public Skill distribution. If public distribution is not authorized, stop this task and register the files only in the user's personal library; do not weaken or bypass this gate.

**Files:**
- Create: `brandloom/assets/defaults/company-logo/enhe/`
- Create: `brandloom/assets/defaults/ip/author-anime/`
- Create: `brandloom/assets/defaults/ip/tuotuo/`
- Create: `brandloom/assets/defaults/ip/xingbi/`
- Create: `brandloom/references/ip-profiles.md`
- Create: `brandloom/references/ip-combinations.md`
- Create: `tests/test_ip_profiles.py`

**Interfaces:**
- Produces: three independent built-in profile IDs and seven built-in combinations.
- Consumes: authorized staging files and asset library hash functions.

- [ ] **Step 1: 写 profile 合同测试**

Test exact IDs and required files:

```python
EXPECTED = {
    "author-anime": {"profile.md", "provenance.json", "reference.png"},
    "tuotuo": {"profile.md", "provenance.json", "reference.png"},
    "xingbi": {"profile.md", "provenance.json", "reference.png"},
}
```

Test that `ip-combinations.md` includes:

```text
author-only
tuotuo-only
xingbi-only
tuotuo-xingbi
author-tuotuo
author-xingbi
author-tuotuo-xingbi
```

- [ ] **Step 2: 运行测试，确认失败**

```powershell
py -3.12 -m unittest tests.test_ip_profiles -v
```

- [ ] **Step 3: 导入并拆分参考**

Copy `author-anime.png` unchanged to `author-anime/reference.png`.

From `tuotuo-xingbi.png`, create two lossless cropped reference images with transparent or white padding:

- `tuotuo/reference.png`
- `xingbi/reference.png`

Do not alter the source file. Record the original source SHA-256 in both provenance files and record crop coordinates.

- [ ] **Step 4: 编写 profile**

`author-anime/profile.md` must lock black tousled hair, light gray jacket, white inner shirt, friendly confident expression and presenter role.

`tuotuo/profile.md` must lock blue rounded form, square black glasses, lightning-shaped head feature and execution/system role.

`xingbi/profile.md` must lock yellow five-point star, white gloves/shoes, friendly smile and feedback/result role.

- [ ] **Step 5: 创建 provenance**

Each `provenance.json` must contain:

```json
{
  "source_reference": "user-provided project asset",
  "sha256": "actual digest",
  "confirmed_at": "actual ISO-8601 timestamp",
  "confirmation_source": "user_confirmed",
  "authorization_status": "user_authorized",
  "distribution_scope": "public_skill_package"
}
```

- [ ] **Step 6: 运行测试与人工图像检查**

```powershell
py -3.12 -m unittest tests.test_ip_profiles -v
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
```

Open all four packaged reference images and verify the correct subject, no accidental crop of another character, and no third-party poster included.

- [ ] **Step 7: Commit**

```powershell
git add brandloom/assets/defaults brandloom/references/ip-profiles.md brandloom/references/ip-combinations.md tests/test_ip_profiles.py
git commit -m "feat: add BrandLoom built-in IP profiles"
```

---

### Task 7: 实现字体发现与严格回退

**Files:**
- Create: `brandloom/references/font-presets.json`
- Create: `brandloom/scripts/brandloom_core/fonts.py`
- Create: `tests/test_fonts.py`

**Interfaces:**
- Produces:
  - `FontProfile`
  - `discover_font_files(extra_roots: tuple[Path, ...] = ()) -> dict[str, tuple[Path, ...]]`
  - `resolve_font(profile: FontProfile, role: str, extra_roots: tuple[Path, ...] = ()) -> Path`
  - `FontNotFoundError`
- Consumes: system font directories and optional project font paths.

- [ ] **Step 1: 写可控目录测试**

Use temporary fake `.ttf` files and inject `extra_roots`. Test exact family-name alias matching from the JSON preset, and test that a missing confirmed font raises `FontNotFoundError` rather than silently returning another file.

- [ ] **Step 2: 运行测试，确认失败**

```powershell
py -3.12 -m unittest tests.test_fonts -v
```

- [ ] **Step 3: 创建字体预设 JSON**

Include five profiles with ordered aliases for heading, body and Latin roles. Each profile must include `fallback_profile_id`; fallback is used only after user confirmation, not automatically.

- [ ] **Step 4: 实现发现与解析**

Scan only:

- Windows: `%WINDIR%\Fonts`
- macOS: `/System/Library/Fonts`, `/Library/Fonts`, `~/Library/Fonts`
- Linux: `/usr/share/fonts`, `/usr/local/share/fonts`, `~/.local/share/fonts`
- explicitly supplied project roots

Do not scan the full drive.

- [ ] **Step 5: 运行测试**

```powershell
py -3.12 -m unittest tests.test_fonts -v
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
```

- [ ] **Step 6: Commit**

```powershell
git add brandloom/references/font-presets.json brandloom/scripts/brandloom_core/fonts.py tests/test_fonts.py
git commit -m "feat: add strict BrandLoom font resolution"
```

---

### Task 8: 创建模板与确定性 Pillow 渲染器

**Files:**
- Create: `brandloom/templates/logo-card-1x1.json`
- Create: `brandloom/templates/cover-2x1.json`
- Create: `brandloom/templates/social-preview-2x1.json`
- Create: `brandloom/scripts/brandloom_core/layout.py`
- Create: `brandloom/scripts/brandloom_core/renderer.py`
- Create: `tests/test_renderer.py`

**Interfaces:**
- Consumes: `BrandBrief`, template JSON, base image, asset paths and resolved font paths.
- Produces:
  - `load_template(path: Path) -> dict[str, object]`
  - `fit_text_box(...) -> TextLayout`
  - `render_brand_asset(...) -> RenderResult`
  - `TextOverflowError`
  - `BrandIntegrityError`

- [ ] **Step 1: 写渲染合同测试**

Tests must create a plain white base image and synthetic transparent logos. Assert:

```python
result = render_brand_asset(...)
self.assertEqual(result.width, 2048)
self.assertEqual(result.height, 2048)
self.assertTrue(result.output_path.is_file())
```

Test cover dimensions 2048 × 1024.

Test that a very long title raises `TextOverflowError`.

Test that company logo target box preserves source aspect ratio within a one-pixel rounding tolerance.

Test that an existing output path creates `-v02` rather than overwriting.

- [ ] **Step 2: 运行测试，确认失败**

```powershell
py -3.12 -m unittest tests.test_renderer -v
```

- [ ] **Step 3: 创建模板**

Each template JSON must declare:

```json
{
  "schema_version": "1.0",
  "canvas": {"width": 2048, "height": 2048, "safe_margin": 123},
  "slots": {
    "company_logo": {"x": 140, "y": 120, "w": 520, "h": 150, "fit": "contain"},
    "title": {"x": 140, "y": 390, "w": 900, "h": 560, "min_font_size": 72},
    "project_mark": {"x": 140, "y": 1320, "w": 480, "h": 480, "fit": "contain"}
  }
}
```

The cover template must reserve a left text panel and a right scene area. Do not hard-code project-specific copy.

- [ ] **Step 4: 实现文字布局**

`fit_text_box()` must:

1. Respect explicit line breaks.
2. Try sizes from configured maximum down to minimum.
3. Calculate multiline bounds with Pillow.
4. Return exact lines, font size and bounding box.
5. Raise `TextOverflowError` if no size fits.

- [ ] **Step 5: 实现合成**

`render_brand_asset()` must:

- Open images in RGBA.
- Resize with LANCZOS.
- Preserve company LOGO aspect ratio.
- Draw text from exact brand brief strings.
- Apply only allowed project-mark transforms.
- Convert output to sRGB-compatible PNG.
- Write to a new versioned path.
- Return a `RenderResult` with dimensions and source hashes.

- [ ] **Step 6: 运行测试**

```powershell
py -3.12 -m unittest tests.test_renderer -v
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
```

- [ ] **Step 7: Commit**

```powershell
git add brandloom/templates brandloom/scripts/brandloom_core/layout.py brandloom/scripts/brandloom_core/renderer.py tests/test_renderer.py
git commit -m "feat: add deterministic BrandLoom renderer"
```

---

### Task 9: 构建底图提示词与图片工具边界

**Files:**
- Create: `brandloom/scripts/brandloom_core/prompt_builder.py`
- Create: `brandloom/references/generation-backend.md`
- Create: `tests/test_prompt_builder.py`
- Modify: `brandloom/SKILL.md`

**Interfaces:**
- Consumes: confirmed `BrandBrief`, shot list, output type and selected IP profiles.
- Produces:
  - `build_base_prompt(brief: BrandBrief, output_type: str) -> str`
  - `validate_generated_path(path: Path) -> tuple[int, int]`
  - agent-facing tool-call rules.

- [ ] **Step 1: 写提示词边界测试**

Assert prompt includes:

- target aspect ratio.
- selected style profile.
- reserved blank text zones.
- selected IP roles.
- instruction to avoid visible company logo and final marketing text.

Assert prompt does not contain:

```text
OPENAI_API_KEY
Images API
image_gen.py
redraw the company logo
```

Test invalid or missing returned file paths raise `FileNotFoundError` or `ValueError`.

- [ ] **Step 2: 运行测试，确认失败**

```powershell
py -3.12 -m unittest tests.test_prompt_builder -v
```

- [ ] **Step 3: 实现 prompt builder**

For `logo_card`, prompt must request a 1:1 real-scene base with defined reserved areas.

For `cover`, prompt must request a 2:1 scene that reuses the accepted LOGO visual DNA and selected IP roles.

The prompt may include small non-critical abstract UI marks but must ask for no readable final copy.

- [ ] **Step 4: 写 generation backend 规则**

`generation-backend.md` must state:

- `GENERATION_READY` is mandatory.
- Use the current host's built-in image generation/edit tool.
- The agent must use the tool's returned path exactly.
- No API keys or alternate providers.
- Failure hard-stops and preserves confirmed plan.
- No automatic retry without user choice.

- [ ] **Step 5: 更新 SKILL.md**

Add exact route:

```text
GENERATION_READY
  → build prompt
  → call host built-in image tool
  → validate returned file
  → compose with renderer
```

- [ ] **Step 6: 运行测试**

```powershell
py -3.12 -m unittest tests.test_prompt_builder -v
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
```

- [ ] **Step 7: Commit**

```powershell
git add brandloom/scripts/brandloom_core/prompt_builder.py brandloom/references/generation-backend.md brandloom/SKILL.md tests/test_prompt_builder.py
git commit -m "feat: define BrandLoom image generation boundary"
```

---

### Task 10: 实现 CLI、manifest 与端到端本地管线

**Files:**
- Create: `brandloom/scripts/brandloom_core/manifests.py`
- Create: `brandloom/scripts/brandloom_cli.py`
- Create: `tests/test_pipeline.py`

**Interfaces:**
- Produces CLI commands:
  - `init`
  - `asset-add`
  - `state-show`
  - `state-confirm`
  - `compose`
  - `validate`
  - `deliver`
- Consumes: previous runtime modules.

- [ ] **Step 1: 写临时工作区端到端测试**

The test must:

1. Run `init` against a temp workspace.
2. Register synthetic company logo and project mark.
3. Write a confirmed `brand-brief.json`.
4. Create a fake base image.
5. Run `compose --type logo-card`.
6. Run `validate`.
7. Assert output and `generation-manifest-v01.json` exist.
8. Run compose again and assert `-v02`.

Invoke `brandloom_cli.main([...])` directly instead of spawning a process.

- [ ] **Step 2: 运行测试，确认失败**

```powershell
py -3.12 -m unittest tests.test_pipeline -v
```

- [ ] **Step 3: 实现 manifest**

`build_generation_manifest()` must record:

- brief SHA-256.
- every asset ID and hash.
- template path and hash.
- font paths and hashes.
- base image original path and hash.
- output path and hash.
- QA state.
- timestamp.

Do not record secrets or full conversation content.

- [ ] **Step 4: 实现 CLI**

Use `argparse`. Every write command must accept `--workspace`. `asset-add` must require explicit flags:

```text
--scope project|personal
--rights user_authorized|analysis_only
--save-confirmed
--make-default
```

Absence of `--save-confirmed` must fail with exit code 2.

`compose` must call `assert_generation_ready()` unless `--test-fixture` is used inside tests.

- [ ] **Step 5: 运行测试**

```powershell
py -3.12 -m unittest tests.test_pipeline -v
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
```

- [ ] **Step 6: Commit**

```powershell
git add brandloom/scripts/brandloom_cli.py brandloom/scripts/brandloom_core/manifests.py tests/test_pipeline.py
git commit -m "feat: add BrandLoom local pipeline"
```

---

### Task 11: 添加本地化、编辑与内部 QA

**Files:**
- Create: `brandloom/scripts/brandloom_core/validation.py`
- Create: `tests/test_localization.py`
- Modify: `brandloom/references/localization-and-editing.md`
- Modify: `brandloom/references/qa-checklist.md`
- Modify: `brandloom/SKILL.md`

**Interfaces:**
- Produces:
  - `validate_output(...) -> QAReport`
  - `localize_brief(...) -> BrandBrief`
  - `QAReport`
- Consumes: render result, brand brief, manifest and existing base image.

- [ ] **Step 1: 写本地化复用测试**

Create English and Chinese briefs with the same assets and base image. Render both. Assert:

- base image hash is identical in both manifests.
- company logo hash is identical.
- output paths differ.
- Chinese output text values match the Chinese brief exactly.
- original English output remains unchanged.

- [ ] **Step 2: 写 QA 测试**

Test failures for:

- wrong dimensions.
- missing company logo source hash.
- manifest text not equal to brief text.
- output path collision without versioning.
- custom IP with `analysis_only`.
- `logo_card` containing more than the confirmed IP count.

- [ ] **Step 3: 运行测试，确认失败**

```powershell
py -3.12 -m unittest tests.test_localization -v
```

- [ ] **Step 4: 实现 QAReport**

Use:

```python
@dataclass(frozen=True)
class QAReport:
    passed: bool
    checks: dict[str, bool]
    warnings: tuple[str, ...]
    failures: tuple[str, ...]
```

`validate_output()` must separate automated checks from manual visual checks. Automated failure prevents `DELIVERED`; warnings require user review.

- [ ] **Step 5: 更新 Skill 对话**

Add:

- logo-first user review.
- cover generation only after logo acceptance.
- localization route that reuses base and assets.
- edit route that invalidates only affected choices.
- no automatic regeneration.

- [ ] **Step 6: 运行测试**

```powershell
py -3.12 -m unittest tests.test_localization -v
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
```

- [ ] **Step 7: Commit**

```powershell
git add brandloom/scripts/brandloom_core/validation.py brandloom/references brandloom/SKILL.md tests/test_localization.py
git commit -m "feat: add BrandLoom localization and QA"
```

---

### Task 12: 文档、示例、发行包与最终验证

**Files:**
- Create: `README.md`
- Create: `README.en.md`
- Create: `LICENSE`
- Create: `NOTICE.md`
- Create: `docs/examples/`
- Create: `scripts/build_skill_package.py`
- Create: `tests/test_package.py`
- Modify: `.github/workflows/validate-skill.yml`

**Interfaces:**
- Produces: `dist/brandloom.zip`.
- Consumes: completed `brandloom/` directory and approved example assets.

- [ ] **Step 1: 写发行包测试**

Test that the built ZIP contains:

```text
brandloom/SKILL.md
brandloom/agents/openai.yaml
brandloom/references/
brandloom/templates/
brandloom/scripts/
brandloom/assets/defaults/
```

Test that it excludes:

```text
.brandloom/
staging/
tests/
docs/superpowers/
.git/
__pycache__/
```

Test the ZIP contains no files whose SHA-256 matches a denylist generated from attachment1–6 third-party references.

- [ ] **Step 2: 运行测试，确认失败**

```powershell
py -3.12 -m unittest tests.test_package -v
```

- [ ] **Step 3: 编写构建脚本**

`build_skill_package.py` must use `zipfile`, sort paths for deterministic order, normalize timestamps, and refuse to package an asset without `provenance.json` and `authorization_status == "user_authorized"`.

- [ ] **Step 4: 编写 README**

README must include:

- BrandLoom 定位。
- 安装到 Codex skills 目录的方法。
- `Use $brandloom` 示例。
- 一次一个问题的 QA 示例。
- 素材库 scope。
- 公司 LOGO 不重绘原则。
- 三个内置 IP 和组合。
- 中文/英文切换。
- 图片工具不可用时的失败口径。
- 权利与隐私边界。
- 本地运行命令。
- 开发测试命令。

README.en must carry the same factual content.

- [ ] **Step 5: 添加自有示例**

Add at least:

- one 1:1 `logo-card`.
- one 2:1 `cover`.
- one localization pair.

Every example must have a matching provenance record and no private path, email, token, QR code or third-party brand.

- [ ] **Step 6: 更新 CI**

Add package build and ZIP contract test after unit tests:

```yaml
      - run: python scripts/build_skill_package.py
      - run: python -m unittest tests.test_package -v
```

- [ ] **Step 7: 运行完整验证**

```powershell
py -3.12 -m pip install -r requirements-runtime.txt
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
py -3.12 scripts/build_skill_package.py
git diff --check
git status --short
```

Then inspect:

```powershell
py -3.12 -c "import zipfile; z=zipfile.ZipFile('dist/brandloom.zip'); print('\n'.join(z.namelist()))"
```

Expected:

- All tests PASS.
- ZIP only contains distributable Skill files.
- No staging or project-local library.
- No unauthorized reference images.
- No untracked generated files except intentional `dist/brandloom.zip` if the repository policy retains it.

- [ ] **Step 8: Commit**

```powershell
git add README.md README.en.md LICENSE NOTICE.md docs/examples scripts tests/test_package.py .github/workflows/validate-skill.yml
git commit -m "docs: prepare BrandLoom skill release"
```

---

## Final Acceptance Run

After all tasks:

```powershell
py -3.12 -m unittest discover -s tests -p "test_*.py" -v
py -3.12 scripts/build_skill_package.py
git diff --check
git status --short
```

Perform two manual workspace acceptance runs:

### Acceptance A: 新项目中文品牌图

- Public project link.
- ENHE company logo from library.
- Project mark upload.
- `author-anime + tuotuo + xingbi` for cover.
- Bright SaaS style.
- Chinese output.
- Confirm logo first, then cover.
- Verify 2048 × 2048 and 2048 × 1024.
- Verify exact Chinese copy and company logo integrity.

### Acceptance B: 英文到中文本地化

- Use an accepted English logo-card and cover.
- Reuse the same base images and asset hashes.
- Replace only confirmed copy and required layout.
- Verify old outputs remain.
- Verify new files receive next version numbers.

Completion status may be reported as `PASS` only when automated tests, build, both manual acceptance runs, `git diff --check`, and `git status` review all succeed.
