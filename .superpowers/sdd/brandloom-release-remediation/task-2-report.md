# Task 2 report

状态：PASS

## RED evidence

- 命令：`python -m unittest tests.test_task2_red -v`（使用工作区 Python 运行时）。结果：FAIL（2 failures, 1 error）。`v99/v100` 选择器返回 `v99`（词法倒序）；缺少 `accepted_logo` 字段导致 `TypeError`；缺少 `host_request` 未失败。原因均对应待实现契约，而非测试拼写/夹具错误。
- 目标测试包含完整 manifest 删除 `brief/assets/template/fonts/base_image/output/host_request/rendered_copy/output_type` 的逐项 fail-closed、accepted-logo 变更阻断、malformed project mark 阻断、数字版本排序和失效清除。

## GREEN and verification

- `python -m unittest tests.test_task2_red -v`：21 tests OK。
- `python -m unittest tests.test_localization tests.test_pipeline tests.test_models tests.test_state_machine -q`：53 tests OK。
- `python -m unittest discover -s tests -q`：135 tests OK。
- `python -m compileall -q brandloom tests`：退出码 0。
- `git diff --check`：退出码 0。

## 修改文件

- `brandloom/scripts/brandloom_core/models.py`：QASession accepted-logo evidence 字段。
- `brandloom/scripts/brandloom_core/json_io.py`：旧 session 缺失默认字段安全读取。
- `brandloom/scripts/brandloom_core/state_machine.py`：invalidate 清除 accepted evidence。
- `brandloom/scripts/brandloom_core/manifests.py`：生产 manifest 始终记录 output_type、host_request。
- `brandloom/scripts/brandloom_core/validation.py`：完整 manifest fail-closed、host request/cover accepted-logo 检查。
- `brandloom/scripts/brandloom_core/prompt_builder.py`：传递精确 accepted-logo evidence。
- `brandloom/scripts/brandloom_cli.py`：accepted-logo 持久化/校验、项目标记解析硬停、数字版本排序。
- `tests/test_pipeline.py`、`tests/test_task2_red.py`：升级生产完整 fixture 并新增回归测试。

## 自审

- 未修改 staging 或默认二进制资产；无外部调用、runtime bypass、伪造 hash 或兼容开关。
- RGB/RGBA 无 ICC 的 sRGB 规则保持不变。
- accepted evidence 包含 resolved output path、SHA-256、manifest path；cover 组合校验文件存在、摘要及 manifest identity，且新 logo 组合/上游 invalidate 会清除旧证据。
- `_load_session` 对旧/畸形 accepted evidence 默认无信任证据。

## concerns

无已知阻塞或未验证项。
