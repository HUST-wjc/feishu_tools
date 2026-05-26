# User Token Scope Policy

`FeishuUser(scopes=None)` 使用 `DEFAULT_USER_DEVICE_FLOW_SCOPES`。默认值应覆盖
feishukit 当前主要模块的常见 user 身份读写路径，同时避开常见需要企业管理审核的权限。

## 默认覆盖目标

- `Bitable`：表、字段、视图、记录的基础读写删。
- `FeishuDoc`：Markdown 读取、docx block 读写、素材上传/下载、wiki URL 解析。
- `FeishuSpreadsheet`：元数据、工作表列表、单元格读写。
- `FeishuDriver`：根目录/文件元数据、小文件上传、下载、删除。

## 当前默认 scope

```python
DEFAULT_USER_DEVICE_FLOW_SCOPES = (
    "bitable:app",
    "docs:document.content:read",
    "docs:document.media:upload",
    "docs:document.media:download",
    "docx:document.block:convert",
    "docx:document:readonly",
    "docx:document:write_only",
    "docx:document:create",
    "wiki:space:retrieve",
    "wiki:node:read",
    "wiki:node:retrieve",
    "sheets:spreadsheet.meta:read",
    "sheets:spreadsheet:read",
    "sheets:spreadsheet:write_only",
    "drive:drive.metadata:readonly",
    "drive:file:upload",
    "drive:file:download",
    "space:document:delete",
)
```

`offline_access` 不写在此列表中，由 `FeishuUserDeviceAuth` 在
`offline_access=True` 时自动追加。

## 不默认申请的 scope

以下权限在常见企业里可能需要管理审核，默认不要加入：

- `docs:doc`
- `docs:doc:readonly`
- `drive:drive`
- `drive:drive:readonly`
- `drive:drive.search:readonly`
- `drive:export:readonly`
- `drive:file`
- `drive:file:readonly`
- `space:document:retrieve`
- `im:message.send_as_user`
- `im:message:recall`
- 各类群管理、群置顶、业务标签等 IM 管理权限

如果新增功能必须使用这些权限，应该让调用方显式传入 `scopes`，并在方法文档或测试中说明。

## 维护规则

- device flow 单次最多申请 50 个 scope。
- refresh token 刷新时可以用 `scope` 缩减本次 user access token 的权限范围，但不能超出最初 device flow 授权范围。
- 当 cache 中已有 scope 不是本次请求 scope 的超集时，`FeishuUserDeviceAuth` 应提示重新 device flow。
- 官方 scope list 页面是动态组件，普通 `.md` 版本可能只包含占位标签；必要时结合官方页面、lark-cli skill 和真实错误信息判断。

官方 scope list:
https://open.feishu.cn/document/server-docs/application-scope/scope-list
