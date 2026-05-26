# API Response Verification

当测试中发现函数返回值不对、报错、实现与注释不一致，或开发者要求验证
某个接口时，按本流程处理。

## 检查顺序

1. 先看目标函数 docstring 是否有官方文档 URL。
2. 用最新的 `docs/agents_doc/feishu_md_doc_url_YYYY_MM-DD.json` 查找对应 `md_url`。
3. 读取官方 `.md`，重点确认 endpoint、HTTP 方法、请求体、响应体 `data` 结构。
4. 如果目标函数不是 OpenAPI 原子接口，就追溯到底层函数再查。例如
  `list_parsed_records()` 应追溯到 `list_records()` 和记录查询接口。
5. 必要时用 local_test 在测试资源上跑一次真实请求，确认当前实际响应。(local_test 为本地测试路径，如不存在可以自行创建)
6. 修改 SDK 返回值处理、docstring 和测试脚本，让三者保持一致。

## 实现规则

- 不写猜测式兼容分支，例如 `result["table"] if "table" in result else result`。
- 官方文档和真实响应都指向同一结构时，按单一路径实现。
- 如果官方文档和真实响应不一致，在代码注释或测试输出中记录差异，再选择当前可验证的结构。
- 如果函数只是 SDK 的语义包装，docstring 应说明它依赖的底层官方接口。

## feishu_md_doc_url 索引

索引文件位于 `docs/agents_doc/feishu_md_doc_url_YYYY_MM-DD.json`，日期即最后更新时间。

常见条目结构：

```json
{
  "name": "查询记录",
  "url": "https://open.feishu.cn/document/.../app-table-record/search",
  "md_url": "https://open.feishu.cn/document/.../app-table-record/search.md",
  "type": "DocumentType",
  "children": []
}
```

- `DocumentType`：实际文档页，`md_url` 通常可直接读取。
- `DirectoryType`：目录节点，通过 `children` 或子页面链接发现下级页面。
- `md_url` 为空：目录或尚未验证的页面。
