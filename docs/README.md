# feishukit 文档索引

本目录按读者和任务拆分。新 agent 接手时先读仓库根目录的 `README.md` 和
`AGENTS.md`，再按任务进入下面的文档。

## 用户指南

- `docs/user_guide/bitable.md`：多维表格 Table / Record / Field / View / Media。
- `docs/user_guide/doc.md`：飞书文档读取、Markdown 写入和素材块。
- `docs/user_guide/driver.md`：云空间文件、素材上传下载和删除。
- `docs/user_guide/spreadsheet.md`：电子表格读取、写入、range 规则。
- `docs/user_guide/user.md`：user access token、device flow、token cache。

## Agent 工作流

- `docs/agents_doc/agent_openapi_workflow.md`：新增模块或接入新 OpenAPI。
- `docs/agents_doc/api_response_verification.md`：修复返回值、docstring 和官方响应不一致的问题。
- `docs/agents_doc/local_test_policy.md`：编写或运行真实飞书接口测试。
- `docs/agents_doc/example_policy.md`：新增或调整 `example/` 脚本。
- `docs/agents_doc/feishu_md_doc_url_YYYY_MM-DD.json`：飞书官方文档 Markdown URL 索引。

## 设计文档

- `docs/design_doc/user_token_scope_policy.md`：`FeishuUser` 默认 scope 和授权策略。
