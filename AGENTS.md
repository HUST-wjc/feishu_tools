# AGENTS.md — feishukit 开发入口

本文件只保留 agent 开发 feishukit 时必须先知道的规则。详细流程放在
`docs/agents_doc/` 和 `docs/design_doc/` 下，按任务需要再读取。

## 基本原则

- 先读 README 和现有源码风格，再设计接口。
- 不要主动执行 `git pull`、`lark-cli update`、`clone` 或安装依赖；需要时先征得用户确认。
- 不要读取、输出或提交 `local_test/` 中的真实凭据、token cache、配置密钥；除非用户明确指定某个文件可读。需要测试规则时只读 `docs/agents_doc/local_test_policy.md`。
- SDK 不主动兼容旧接口、猜测式响应结构或错误调用方式。用当前官方文档或真实测试确认响应结构后，只实现单一路径。
- 复杂查询条件优先透传飞书原生 `dict`，不要把官方 filter, sorter 等复杂字段的所有内容展平成 Python 参数。
- 不要为一次性、一两行逻辑制造大量私有函数；只有复杂、可复用、可测试的逻辑才拆分。

## 代码风格偏好

- 先实现最短、最直的正确路径，符合 KISS 原则；不要为了假想场景增加 fallback。
- alpha 阶段可以删除误导性接口，而不是保留兼容层，但需要和开发者确认。
- 私有 helper 只有在逻辑复用、复杂度隔离或可测试性明显提升时才创建。
- 如果一个同名参数在本类中的语义不同于其他 client，优先改名或删除；不要只靠实现细节维持。
- 不要缓存可以通过 API 直接获取、且不属于认证状态的数据；确需缓存时应放在最接近使用者的一层。
- 真实接口返回值一旦确认，就按单一路径实现；不写 `x if exists else y` 这类猜测式兼容分支。

## 常用流程

- 文档目录索引：见 `docs/README.md`。
- 新增模块或接入新 OpenAPI：见 `docs/agents_doc/agent_openapi_workflow.md`。
- 验证函数返回值、docstring 和官方响应体是否一致：见 `docs/agents_doc/api_response_verification.md`。
- 编写或运行本地测试：见 `docs/agents_doc/local_test_policy.md`。
- 新增或调整示例脚本：见 `docs/agents_doc/example_policy.md`。
- 调整 user token 默认 scope：见 `docs/design_doc/user_token_scope_policy.md`。

## 本地文档索引

飞书官方文档索引位于 `docs/agents_doc/feishu_md_doc_url_YYYY_MM-DD.json`。
文件名日期代表更新时间。除非用户明确要求或索引明显过期，不要主动更新索引。

索引条目中的 `md_url` 是实现时优先阅读的官方 Markdown 文档地址；普通 OpenAPI
接口应以其中的 endpoint、请求体和响应体示例为准。
