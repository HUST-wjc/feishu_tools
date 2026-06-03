# feishukit

飞书非官方 Python SDK，替代官方 Java 风格的 SDK。

目前支持：

- 多维表格 `Bitable`
- 文档 `FeishuDoc`
- 云空间 `FeishuDriver`
- 即时通讯 `FeishuIM`
- 电子表格 `FeishuSpreadsheet`
- 用户身份 API `FeishuUser`

默认推荐使用 tenant access token，也就是应用身份操作飞书资源；只有确实需要“代理当前用户本人”访问资源时，再使用 `FeishuUser`。

feishukit 不内置日志模块，用户可以在调用方法时自行添加日志。

## 为什么不用官方 SDK？

以“更新一条多维表格记录”为例。

官方 SDK (`lark-oapi`)：

```python
import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *

client = lark.Client.builder() \
    .app_id("YOUR_APP_ID") \
    .app_secret("YOUR_APP_SECRET") \
    .build()

request = UpdateAppTableRecordRequest.builder() \
    .app_token("YOUR_APP_TOKEN") \
    .table_id("YOUR_TABLE_ID") \
    .record_id("YOUR_RECORD_ID") \
    .request_body(AppTableRecord.builder()
        .fields({"状态": "完成"})
        .build()) \
    .build()

response = client.bitable.v1.app_table_record.update(request)

if not response.success():
    raise Exception(f"code: {response.code}, msg: {response.msg}")
```

feishukit：

```python
from feishukit import Bitable

bt = Bitable(
    app_id="YOUR_APP_ID",
    app_secret="YOUR_APP_SECRET",
    bitable_url="https://xxx.feishu.cn/base/appxxxxx?table=tblxxxxx",
)

bt.update_record("recxxxxx", {"状态": "完成"})
```

## 安装

```bash
pip install feishukit
```

唯一运行时依赖为 `requests`。

## 前置条件

1. 前往 [飞书开发者后台](https://open.feishu.cn/app) 创建应用，获取 `app_id` 和 `app_secret`。
2. 在应用的权限管理中，按实际要调用的模块申请权限。
3. 对 Bitable / Spreadsheet / Doc 等云文档资源，将应用添加为目标文档的协作者或文档应用。
4. 不要把 `app_id`、`app_secret`、access token 写入 README、示例输出或提交内容。

tenant access token 和 user access token 是两套身份：

- tenant access token：应用身份。适合项目服务、同步任务和大多数自动化脚本。
- user access token：用户身份。适合 notebook、个人脚本，以及必须以当前用户本人权限访问资源的场景。

应用后台里的“应用身份权限”和“用户身份权限”不会自动一致。使用 `FeishuUser` 前，需要在应用后台开通对应的用户身份权限。

## 示例脚本

完整示例在 `example/`：

- `bitable_usage.py`
- `doc_usage.py`
- `driver_usage.py`
- `spreadsheet_usage.py`
- `user_usage.py`

示例中包含写入或删除操作，请只在测试文档、测试表格和测试文件夹上运行。

## 快速上手

### Bitable

多维表格是 feishukit 当前最成熟、最常用的模块。

```python
from feishukit import Bitable

bt = Bitable(
    app_id="cli_xxxx",
    app_secret="xxxx",
    bitable_url="https://xxx.feishu.cn/wiki/xxxxx?table=tblxxxx",
)

records = bt.list_parsed_records(size_limit=10)
rid = bt.create_record({"名称": "test", "状态": "进行中"})["record_id"]
bt.update_record(rid, {"状态": "完成"})
bt.delete_record(rid)
```

详细用法见 [Bitable 用户指南](docs/user_guide/bitable.md)。

### User Token

`FeishuUser` 使用 device flow 获取 user access token，并能用当前用户身份派生 Bitable、Doc、Spreadsheet、Driver、IM client。

```python
from feishukit import FeishuUser

api = FeishuUser(
    app_id="cli_xxxx",
    app_secret="xxxx",
    token_cache_path="./token_cache.json",
    scopes=None,          # 使用 feishukit 默认常用 user scope
    offline_access=True,  # 缓存 refresh token，避免频繁重新授权
)

user = api.get_current_user()
bt = api.bitable("https://xxx.feishu.cn/base/xxxxx?table=tblxxxx")
doc = api.doc("https://xxx.feishu.cn/wiki/xxxxx")
ss = api.spreadsheet("https://xxx.feishu.cn/sheets/xxxxx?sheet=abc123")
driver = api.driver()
im = api.im()
```

默认仍建议优先使用 tenant token。只有当目标资源必须以“当前用户本人”身份访问，或资源协作权限只授予用户而非应用时，再使用 `FeishuUser`。

详细用法见 [User Token 用户指南](docs/user_guide/user.md)。

### Doc

```python
from feishukit import FeishuDoc

doc = FeishuDoc(
    app_id="cli_xxxx",
    app_secret="xxxx",
    doc_url="https://xxx.feishu.cn/wiki/xxxxx",
)

markdown = doc.get_markdown()
doc.append_markdown("## 新增章节\n\n正文")
```

详细用法见 [Doc 用户指南](docs/user_guide/doc.md)。

### Driver

```python
from feishukit import FeishuDriver

driver = FeishuDriver(app_id="cli_xxxx", app_secret="xxxx")
root = driver.get_root_folder_meta()
file_token = driver.upload("files", "./report.pdf", parent_type="explorer", parent_node=root["token"])
driver.delete_file(file_token, file_type="file")
```

详细用法见 [Driver 用户指南](docs/user_guide/driver.md)。

### IM

```python
from feishukit import FeishuIM

im = FeishuIM(app_id="cli_xxxx", app_secret="xxxx")

groups = im.search_groups("测试群", size_limit=5)
groups = im.list_groups(group_types="p2p", size_limit=5)  # user 身份可列单聊
messages = im.list_messages("oc_xxx", size_limit=10)
sent = im.send_text("hello", chat_id="oc_xxx")
im.reply_text(sent["message_id"], "received")
```

IM 读取接口保留飞书原始 message dict，并额外补充轻量 `content_text`。写操作会真实发送消息或修改群组。测试群成员、更新群和解散群前，先确认目标是专用测试群；解散群只能用于本次测试新建的群。

详细用法见 [IM 用户指南](docs/user_guide/im.md)。

### Spreadsheet

```python
from feishukit import FeishuSpreadsheet

ss = FeishuSpreadsheet(
    app_id="cli_xxxx",
    app_secret="xxxx",
    spreadsheet_url="https://xxx.feishu.cn/wiki/xxxxx?sheet=abc123",
)

rows = ss.get_rows(sheet_id="abc123", cell_range="A1:C10")
ss.update_values(sheet_id="abc123", cell_range="A1:B2", values=[["Hello", "World"]])
```

详细用法见 [Spreadsheet 用户指南](docs/user_guide/spreadsheet.md)。

## 共享认证

多个业务 client 可以共享同一个 `FeishuAPI`，避免重复获取 token：

```python
from feishukit import FeishuAPI, Bitable, FeishuDoc

api = FeishuAPI(app_id="cli_xxxx", app_secret="xxxx")
bt = Bitable(bitable_url="...", feishu_api=api)
doc = FeishuDoc(doc_url="...", feishu_api=api)
```

## 开发与维护

面向 agent 或维护者的开发规则见 [AGENTS.md](AGENTS.md)。

更新记录见 [CHANGELOG.md](CHANGELOG.md)。

## 依赖

- Python >= 3.10
- requests
