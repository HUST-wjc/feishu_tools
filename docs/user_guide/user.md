# User Token 用户指南

`FeishuUser` 用 device flow 获取 user access token，使 SDK 以当前授权用户本人身份调用飞书 API。

默认仍建议优先使用 tenant access token，也就是 `FeishuAPI` / `Bitable` / `FeishuDoc` 等普通入口。只有在资源权限属于用户本人、或 API 明确需要用户身份时，再使用 `FeishuUser`。

## 权限说明

tenant access token 和 user access token 是两套身份：

- tenant access token：应用身份。权限来自应用身份权限和文档协作者/文档应用授权。
- user access token：用户身份。权限来自用户身份权限和用户本人对资源的访问权限。

应用后台里的应用身份权限不会自动等于用户身份权限。使用 `FeishuUser` 前，需要在应用后台开通对应的用户身份权限。

## 基本用法

```python
from feishukit import FeishuUser

api = FeishuUser(
    app_id="cli_xxxx",
    app_secret="xxxx",
    token_cache_path="./token_cache.json",
    scopes=None,
    offline_access=True,
)

user = api.get_current_user()
print(user.get("name"))
```

第一次运行时会打印飞书授权链接，并阻塞等待用户在浏览器中确认授权。

## token cache

指定 `token_cache_path` 后，`FeishuUser` 会读写本地 token cache，避免每次都走 device flow：

```python
api = FeishuUser(
    app_id="cli_xxxx",
    app_secret="xxxx",
    token_cache_path="~/.config/feishukit/user_token.json",
)
```

cache 中保存 user access token、refresh token、过期时间和已授权 scope。refresh token 比 access token 更敏感，不要提交到 git。

`FeishuUser` 会按 cache 中的过期时间主动检查 user access token。access token 临近过期时，如果 refresh token 仍有效，会先刷新 token 再发起业务请求，避免先请求失败再重试。

如果 cache 中已有 scope 不是本次请求 scope 的超集，SDK 会提示重新 device flow 更新授权。

## 派生业务 client

`FeishuUser` 继承自 `FeishuAPI`，可以直接传给已有业务 client，也可以用工厂方法创建：

```python
bt = api.bitable("https://xxx.feishu.cn/base/xxxxx?table=tblxxxx")
doc = api.doc("https://xxx.feishu.cn/wiki/xxxxx")
ss = api.spreadsheet("https://xxx.feishu.cn/sheets/xxxxx?sheet=abc123")
driver = api.driver()
```

这些 client 的读写逻辑和普通 tenant 身份入口一致，只是底层 token 换成当前用户身份。

## scopes

`scopes=None` 使用 feishukit 默认常用 user scope，覆盖当前 SDK 的 Bitable、Doc、Spreadsheet、Driver 常用读写路径，并避开常见需要企业管理员审核的粗粒度权限。

如果需要更小或更大的权限范围，可以显式传入 scope：

```python
api = FeishuUser(
    app_id="cli_xxxx",
    app_secret="xxxx",
    scopes=["bitable:app", "wiki:node:read"],
    token_cache_path="./token_cache.json",
)
```

device flow 单次最多申请 50 个 scope。refresh token 刷新时可以缩减权限范围，但不能超过最初 device flow 授权范围。

默认 scope 的维护规则见 [User Token Scope Policy](../design_doc/user_token_scope_policy.md)。

## offline_access

`offline_access=True` 时会请求 refresh token 能力，适合 notebook 和脚本长期复用。

`offline_access=False` 时只拿短期 user access token；access token 过期后没有 refresh token 可用，需要重新授权。

## no-confirm 测试

本地测试脚本应把需要用户确认的 device flow 和不需要确认的 cache 复用测试拆开。详见 [Local Test Policy](../agents_doc/local_test_policy.md)。
