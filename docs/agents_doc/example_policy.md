# Example Policy

本流程适用于新增或调整 `example/` 下的示例脚本。

## 基本规则

- 示例只使用占位 `app_id`、`app_secret`、URL、token，不写真实凭据。
- 文件开头说明需要在飞书开发者后台开通哪些权限。
- 如果示例包含写入、删除、上传，必须提醒只在测试资源上运行。
- 示例优先展示推荐用法；高级或原始返回结构只作为补充。
- 示例应尽量可复制运行，但不要依赖 `local_test/` 的真实配置。
- 修改示例后，按需同步 README 或 `docs/user_guide/`。

## 命名约定

- Bitable：`example/bitable_usage.py`
- Doc：`example/doc_usage.py`
- Driver：`example/driver_usage.py`
- Spreadsheet：`example/spreadsheet_usage.py`
- User token：`example/user_usage.py`

新增模块时使用 `{module}_usage.py`，保持同样的文件头和占位配置风格。

## 检查清单

- 示例没有真实 `app_id`、`app_secret`、access token、refresh token、测试 URL。
- 写删操作有明显风险提示。
- 普通路径优先展示高层便捷方法。
- 复杂参数直接使用飞书原生 `dict` 示例。
- `python3 -m py_compile example/xxx_usage.py` 可通过。
