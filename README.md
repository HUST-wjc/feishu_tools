# feishu-tools

飞书非官方 Python SDK，替代官方 Java 风格的 SDK。
目前支持**多维表格 (Bitable)**、**文档 (Doc)** 和 **云空间 (Driver)** API。

没有任何日志模块，用户可以在调用方法时自行添加日志记录

## 为什么不用官方 SDK？

以"更新一条多维表格记录"为例——

**官方 SDK (`lark-oapi`)**

```python
import lark_oapi as lark
from lark_oapi.api.bitable.v1 import *

client = lark.Client.builder() \
    .app_id("YOUR_APP_ID") \
    .app_secret("YOUR_APP_SECRET") \
    .build()

request = UpdateAppTableRecordRequest.builder() \
    .app_token("appbcbWCzen6D8dezhoCH2RpMAh") \
    .table_id("tblsRc9GRRXKqhvW") \
    .record_id("recqwIwhc6") \
    .request_body(AppTableRecord.builder()
        .fields({"状态": "完成"})
        .build()) \
    .build()

response = client.bitable.v1.app_table_record.update(request)

if not response.success():
    raise Exception(f"code: {response.code}, msg: {response.msg}")
```

**feishu-tools**

```python
from feishu_tools import Bitable

bt = Bitable(app_id="YOUR_APP_ID", app_secret="YOUR_APP_SECRET",
             bitable_url="https://xxx.feishu.cn/base/appbcbWCzen6D8dezhoCH2RpMAh?table=tblsRc9GRRXKqhvW")

bt.update_record("recqwIwhc6", {"状态": "完成"})
```

## 前置条件

1. 前往 [飞书开发者后台](https://open.feishu.cn/app) 创建应用，获取 `app_id` 和 `app_secret`
2. 在应用的权限管理中，按需申请权限：

| 权限 | 说明 | 模块 |
|------|------|------|
| `bitable:app` | 查看、评论、编辑和管理多维表格 | Bitable |
| `wiki:wiki:readonly` | 查看知识库（多维表格或文档放在知识库中时需要） | Bitable / Doc |
| `docx:document` | 查看、编辑和管理云空间中所有文档 | Doc |
| `drive:drive` | 查看、管理、上传、下载云空间中所有文件 | Driver |

3. Bitable: 将应用添加为多维表格的协作者（多维表格右上角 `...` → 添加协作者 → 搜索应用名称）
4. Doc: 将应用添加为知识库文档的协作者

> 参考: [飞书开放平台 - 开发文档](https://open.feishu.cn/document/home/index)

## 安装

```bash
pip install -e ./feishu_tools
```

## 示例

完整用法参考 `example/` 目录下的脚本：

- `bitable_usage.py` — Bitable 全功能演示 (Table / Record / Field / View CRUD)
- `doc_usage.py` — Doc 全功能演示 (读取 / Markdown 写入 / 清空 / 素材插入)
- `driver_usage.py` — Driver 全功能演示 (云空间文件上传 / 下载 / 删除 / 元数据)

> **注意**: 请在新建的、非生产环境的多维表格和文档上运行示例，测试中包含删除操作。

## 快速上手

### feishu_bitable

```python
from feishu_tools import Bitable

bt = Bitable(
    app_id="cli_xxxx",
    app_secret="xxxx",
    bitable_url="https://xxx.feishu.cn/wiki/xxxxx?table=tblxxxx",
)
```

`bitable_url` 支持两种格式：
- **知识库中的多维表格**: `https://xxx.feishu.cn/wiki/{node_token}?table={table_id}`
- **个人目录中的多维表格**: `https://xxx.feishu.cn/base/{app_token}?table={table_id}`

如果 URL 中不包含 `table=` 参数，会自动取多维表格中的第一个数据表。

#### API 一览

##### Record（记录）

```python
# 查询
records = bt.list_records()                              # 全量
records = bt.list_records(size_limit=10)                 # 限制数量
records = bt.list_records(field_names=["名称", "状态"])   # 指定字段
records = bt.list_records(view_name="视图名")             # 按视图查询
records = bt.list_records(automatic_fields=True)         # 含创建时间/修改时间等

# 带过滤条件
records = bt.list_records(field_filter={
    "conditions": [{"field_name": "状态", "operator": "is", "value": ["完成"]}],
    "conjunction": "and",
})

# 带排序
records = bt.list_records(field_sort=[{"field_name": "日期", "desc": True}])

# 解析记录 (自动展平文本、人员等复合类型)
parsed = bt.list_parsed_records()  # -> [(record_id, {field: value}), ...]

# 单条操作
record = bt.get_record("recXXXX")
first  = bt.take_one_record()
rid    = bt.create_record({"名称": "test", "状态": "进行中"})["record_id"]
bt.update_record(rid, {"状态": "完成"})
bt.delete_record(rid)

# 批量操作
bt.batch_create_records([{"名称": f"item_{i}"} for i in range(10)])
bt.batch_get_records(["recXXX1", "recXXX2"])
bt.batch_update_records([(rid1, {"状态": "完成"}), (rid2, {"状态": "进行中"})])
bt.batch_delete_records(["recXXX1", "recXXX2"])
```

##### Field（字段/列）

```python
fields = bt.list_fields()

# field_type 支持 int 或中文名: "文本", "数字", "单选", "多选", "日期" 等
bt.create_field("新字段", field_type="数字")

# 通过字段名或 field_id 定位
bt.update_field(field_name="旧名", override_payload={"field_name": "新名", "type": 1})
bt.delete_field(field_name="要删除的字段")
```

##### View（视图）

```python
views = bt.list_views()
info  = bt.get_view_info(view_name="表格")

# view_type: "grid" | "kanban" | "gallery" | "gantt" | "form"
bt.create_view("新视图", view_type="grid")
bt.update_view(view_name="旧名称", view_new_name="新名称")
bt.delete_view(view_name="要删除的视图")
```

##### Table（数据表）

```python
tables = bt.list_tables()
size   = bt.get_table_size()       # 当前表记录数
meta   = bt.get_bitable_meta()     # 多维表格元数据

bt.create_table("新数据表")
bt.batch_create_tables(["表1", "表2"])
bt.update_table(table_new_name="新名称")
bt.delete_table(table_name)
bt.batch_delete_tables(table_names=["表1", "表2"])
```

##### 素材上传

```python
# 上传图片/文件到多维表格，parent_type 自动推导
file_token = bt.upload_media("./photo.jpg")

# 写入附件字段
bt.create_record({"附件": [{"file_token": file_token}]})
```

#### API 覆盖

| 资源   | list | get | batch_get | create | batch_create | update | batch_update | delete | batch_delete |
|--------|------|-----|-----------|--------|--------------|--------|--------------|--------|--------------|
| Table  | ✅   | -   | -         | ✅     | ✅           | ✅     | -            | ✅     | ✅           |
| Record | ✅   | ✅  | ✅        | ✅     | ✅           | ✅     | ✅           | ✅     | ✅           |
| Field  | ✅   | -   | -         | ✅     | -            | ✅     | -            | ✅     | -            |
| View   | ✅   | ✅  | -         | ✅     | -            | ✅     | -            | ✅     | -            |
| Media  | -    | -   | -         | ✅ (`upload_media`) | - | -  | -            | -      | -            |

#### 字段类型速查

| 中文名 | 类型值 | 中文名 | 类型值 |
|--------|--------|--------|--------|
| 文本   | 1      | 单项关联 | 18   |
| 数字   | 2      | 查找引用 | 19   |
| 单选   | 3      | 公式     | 20   |
| 多选   | 4      | 双向关联 | 21   |
| 日期   | 5      | 地理位置 | 22   |
| 复选框 | 7      | 群组     | 23   |
| 人员   | 11     | 创建时间 | 1001 |
| 电话号码 | 13   | 最后更新时间 | 1002 |
| 超链接 | 15     | 创建人   | 1003 |
| 附件   | 17     | 修改人   | 1004 |
|        |        | 自动编号 | 1005 |

`create_field` 和 `update_field` 的 `field_type` 参数支持传中文名（如 `"数字"`）或 int 值（如 `2`）。

#### 速率限制

批量写入操作（`batch_create_records`, `batch_update_records`, `batch_delete_records`）默认每批次间等待 0.5 秒，可通过 `request_delay` 参数调整：

```python
bt = Bitable(app_id="...", app_secret="...", bitable_url="...", request_delay=1.0)
```

#### filter 与 sort 参考

filter 示例：

```python
bt.list_records(field_filter={
    "conditions": [
        {"field_name": "职位", "operator": "is", "value": ["初级销售员"]},
        {"field_name": "销售额", "operator": "isGreater", "value": ["10000.0"]},
    ],
    "conjunction": "and",  # 或 "or"
})
```

常用 operator: `is`, `isNot`, `contains`, `doesNotContain`, `isEmpty`, `isNotEmpty`, `isGreater`, `isLess` 等。
完整列表见 [官方文档 - 记录筛选指南](https://open.feishu.cn/document/docs/bitable-v1/app-table-record/record-filter-guide)。

sort 示例：

```python
bt.list_records(field_sort=[{"field_name": "日期", "desc": True}])
```

> 当 `field_filter` 或 `field_sort` 不为空时，`view_id` / `view_name` 会被忽略。

### feishu_doc

```python
from feishu_tools import FeishuDoc

doc = FeishuDoc(
    app_id="cli_xxxx",
    app_secret="xxxx",
    doc_url="https://xxx.feishu.cn/wiki/xxxxx",
)
```

`doc_url` 支持两种格式：
- **知识库文档**: `https://xxx.feishu.cn/wiki/{node_token}`
- **个人空间文档**: `https://xxx.feishu.cn/docx/{document_id}`

#### API 一览

##### 读取

```python
meta     = doc.get_doc_meta()          # 文档元数据 (标题、版本号等)
text     = doc.get_raw_content()       # 纯文本内容 (\n 分割)
blocks   = doc.get_doc_blocks()        # 所有文档块
children = doc.get_children()          # 根节点的子块列表
children = doc.get_children(block_id)  # 指定块的子块列表
```

##### 写入

```python
# Markdown 写入 (推荐)
doc.clear_content()
doc.write_markdown("# 标题\n\n正文内容\n\n- 列表项")

# 追加到文档末尾
doc.append_markdown("## 新增章节\n\n追加内容")

# 手动构建块写入 (块类型定义见 data_type.py)
doc.create_block(children=[
    {"block_type": 3, "heading1": {"elements": [{"text_run": {"content": "标题"}}]}},
    {"block_type": 2, "text": {"elements": [{"text_run": {"content": "正文"}}]}},
])
```

##### 素材

```python
# 上传素材到文档
file_token = doc.upload_media("./photo.jpg", parent_node)

# 在文档末尾插入图片 (自动创建 Image Block → 上传 → 绑定)
file_token = doc.update_media_block("./photo.jpg")

# 在文档末尾插入文件 (自动创建 File Block → 上传 → 绑定)
file_token = doc.update_media_block("./report.pdf")
```

##### 删除

```python
doc.clear_content()  # 清空文档所有内容
```

#### API 覆盖

| 操作 | 方法 |
|------|------|
| 文档元数据 | `get_doc_meta` |
| 纯文本内容 | `get_raw_content` |
| 获取所有块 | `get_doc_blocks` |
| 获取子块 | `get_children` |
| Markdown → 块 JSON | `convert_markdown` |
| Markdown 写入 | `write_markdown` |
| Markdown 追加 | `append_markdown` |
| 手动创建块 | `create_block` |
| 上传素材 | `upload_media` |
| 插入图片/文件块 | `update_media_block` |
| 清空文档 | `clear_content` |

#### Markdown 写入说明

`write_markdown` 内部分两步: 先调用 [convert API](https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/document-docx/docx-v1/document/convert) 将 Markdown 转为块 JSON，再调用 `create_block` 写入文档。如果只需要转换不写入，可以单独使用 `convert_markdown`。

支持的 Markdown 语法：

- 标题 (`#` ~ `######`)
- 有序/无序列表
- 代码块 (含语言标注)
- 引用 (`>`)
- 分割线 (`---`)
- 加粗、斜体、删除线、行内代码、超链接

不支持飞书特有块类型（如高亮块 Callout），需要时请用 `create_block` 配合 `data_type.BLOCK_TYPE_MAP` 手动构建。

#### 块类型速查

| 类型 | 值 | 类型 | 值 |
|------|----|------|----|
| text | 2 | bullet (无序列表) | 12 |
| heading1 | 3 | ordered (有序列表) | 13 |
| heading2 | 4 | code (代码块) | 14 |
| heading3 | 5 | quote (引用) | 15 |
| heading4 | 6 | todo (待办) | 17 |
| heading5~9 | 7~11 | divider (分割线) | 22 |
| file | 23 | image | 27 |

完整列表见 `feishu_doc/data_type.py`。

### feishu_driver

```python
from feishu_tools import FeishuDriver

driver = FeishuDriver(app_id="cli_xxxx", app_secret="xxxx")
```

`FeishuDriver` 封装云空间的文件和素材操作。Bitable 和 FeishuDoc 内部自动创建 `FeishuDriver` 实例，也可独立使用。

#### API 一览

```python
# 元数据
root  = driver.get_root_folder_meta()          # 根文件夹信息
files = driver.list_files()                    # 根目录文件列表
files = driver.list_files(folder_token="xxx")  # 指定文件夹
meta  = driver.get_file_meta("file_token")     # 文件元数据

# 上传 (≤ 20MB 直接上传, > 20MB 自动分片)
token = driver.upload("files", "./report.pdf", parent_type="explorer", parent_node=folder_token)
token = driver.upload("medias", "./photo.jpg", parent_type="docx_image", parent_node=block_id)

# 下载
driver.download("files", file_token, "./local/report.pdf")
driver.download("medias", media_token, "./local/photo.jpg")

# 临时下载链接 (24h 有效, 一次最多 5 个)
urls = driver.get_tmp_download_urls([token1, token2])

# 删除 (仅云空间文件, 素材不支持删除)
driver.delete_file(file_token, file_type="file")
```

#### API 覆盖

| 操作 | 方法 | 说明 |
|------|------|------|
| 根文件夹元数据 | `get_root_folder_meta` | 获取我的空间根目录信息 |
| 文件列表 | `list_files` | 指定文件夹或根目录 |
| 文件元数据 | `get_file_meta` | 批量查询，一次最多 200 个 |
| 上传 | `upload` | 文件 (`files`) 或素材 (`medias`)，自动切换直传/分片 |
| 下载 | `download` | 下载到本地路径 |
| 临时链接 | `get_tmp_download_urls` | 24h 有效，一次最多 5 个 |
| 删除 | `delete_file` | 仅云空间文件，删除后进入回收站 |

#### upload_type 与 parent_type 参考

| upload_type | parent_type | 用途 |
|-------------|-------------|------|
| `files` | `explorer` | 上传文件到云空间 |
| `medias` | `docx_image` | 上传图片素材到文档 |
| `medias` | `docx_file` | 上传文件素材到文档 |
| `medias` | `bitable_image` | 上传图片素材到多维表格 |
| `medias` | `bitable_file` | 上传文件素材到多维表格 |

> Bitable 和 FeishuDoc 的 `upload_media` / `update_media_block` 会自动推导 `parent_type`，通常无需直接调用 `FeishuDriver.upload`。

### 共享认证

多个实例可共享同一个 `FeishuAPI`，避免重复获取 token：

```python
from feishu_tools import FeishuAPI, Bitable, FeishuDoc

api = FeishuAPI(app_id="cli_xxxx", app_secret="xxxx")
bt  = Bitable(app_id="", app_secret="", bitable_url="...", feishu_api=api)
doc = FeishuDoc(app_id="", app_secret="", doc_url="...", feishu_api=api)

# bt.driver 和 doc.driver 共享同一个 api 实例
```

## 依赖

- Python >= 3.10
- requests
