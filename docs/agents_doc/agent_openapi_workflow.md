# Agent OpenAPI Workflow

本流程适用于新增模块、接入新的飞书 OpenAPI 资源，或新增较大的 API 能力。
小范围 bugfix、docstring、测试脚本调整、局部重构不需要完整执行。

## 1. 找官方文档

1. 查看 `docs/agents_doc/` 下最新的 `feishu_md_doc_url_YYYY_MM-DD.json`。
2. 用目标关键词搜索条目的 `name`、`url`、`md_url`。
3. 读取最相关的官方 `.md` 文档，确认 endpoint、HTTP 方法、请求体和响应结构。

如果索引距今超过 7 天，或用户明确要求更新，先询问用户再运行：

```bash
python3 update_feishu_md_doc_url.py
```

## 官方 Markdown 文档

飞书开放平台页面通常提供 Markdown 版本，适合 agent / CLI 抓取。相比解析
前端渲染后的 HTML，Markdown 版本更稳定，也更容易搜索接口路径、权限、
请求参数和响应字段。

例如，多维表格概述页面：

```bash
curl -L "https://open.feishu.cn/document/server-docs/docs/bitable-v1/bitable-overview.md"
```

对应浏览器页面为：

```text
https://open.feishu.cn/document/server-docs/docs/bitable-v1/bitable-overview
```

如果不确定页面是否提供 Markdown 版本，可以先检查 HTML 头部是否包含类似链接：

```html
<link rel="alternate" type="text/markdown" href="...md" tip="pure markdown version, better for ai" />
```

约定：

- 优先使用 `open.feishu.cn` 官方文档。
- 优先读取 `.md` 版本；常见做法是在官方文档 URL 后追加 `.md`。
- 如果 `.md` 不可用，再查看 HTML 头部的 `rel="alternate"` Markdown 链接。
- 对比 SDK 行为时，先看概述页，再看具体子功能接口页。
- 只有 feishukit 未覆盖对应能力时，才参考原始 HTTP API。
- 不要把 `app_id`、`app_secret`、access token 写入 README、示例输出或提交内容。

## 2. 优先寻找官方高层能力

如果需求看起来需要自己做复杂转换、解析或渲染，先确认飞书是否已有更高层 API：

- Markdown 读取：优先找导出、fetch、AI 读取接口，而不是手写 block 到 Markdown 的渲染器。
- 文件转换：优先找 import/export 接口，而不是本地解析格式。
- 搜索：优先找 search 接口，而不是分页拉全量后本地过滤。

官方高层 API 可用且语义稳定时优先使用。只有高层 API 不存在、权限不可用，
或返回信息不足时，才退回到底层 block、record、message 结构自行处理。

## 3. 参考 lark-cli 和 skills

本地 lark-cli skills 和 lark-cli 仓库只作为参考，不阻塞主流程。

- 不主动更新 `lark-cli` 或 `skills`。
- 不主动 `git pull` 本地 lark-cli 仓库。
- 参考重点是接口命名、scope、参数结构和边界情况，不复制实现。

推荐调研顺序：

1. README 和现有源码风格
2. 官方 md 文档中最相关的 1-3 个接口
3. 本地 skill / lark-cli 中对应 shortcut 的说明
4. 必要时再看 lark-cli 源码

## 4. 设计 P0 接口

动手前先列出公开方法清单和每个方法的使用场景，避免范围蔓延。

设计原则：

- 高频、重要接口优先；罕见管理接口暂不实现。
- 公开接口分成 P0 和 Later。P0 只包含最小可用闭环。
- P0 应复用现有 `FeishuAPI` / `FeishuUser` / `paginate` 模式。
- 只读需求不要混入发送、删除、管理类写操作。
- 不引入新的 token 管理、缓存、日志、数据库或后台任务，除非用户明确要求。

## 5. 新增 API 最小 checklist

代码 commit 前确认下面项目已经处理：

- 官方接口的文档 URL，如果存在，已写入公开方法 docstring (形似 https://open.feishu.cn/document/server-docs/docs/xxx)。
- 已确认 endpoint、HTTP method、query/body 参数和响应 `data` 结构和官方文档匹配。
- 接口和 user token 相关时，已确认所需 scope，并判断是否影响 `FeishuUser` 默认 scope。
- 公开方法签名只暴露常用参数；复杂结构保持飞书原生 `dict`。
- 返回值路径与官方响应一致，不写猜测式兼容分支。
- 列表接口优先复用 `paginate` / `iter_paginate`。
- README、`docs/user_guide/` 或 `example/` 已按需要同步。
- 如涉及真实接口行为，已按 `local_test_policy.md` 补充或运行测试。
