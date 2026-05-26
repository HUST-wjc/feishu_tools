# Bitable 用户指南

`Bitable` 封装飞书多维表格的 Table、Record、Field、View 和素材上传能力。

## 初始化

```python
from feishukit import Bitable

bt = Bitable(
    app_id="cli_xxxx",
    app_secret="xxxx",
    bitable_url="https://xxx.feishu.cn/wiki/xxxxx?table=tblxxxx&view=vewxxxx",
)
```

`bitable_url` 支持两种格式：

- 知识库中的多维表格：`https://xxx.feishu.cn/wiki/{node_token}?table={table_id}&view={view_id}`
- 个人目录中的多维表格：`https://xxx.feishu.cn/base/{app_token}?table={table_id}&view={view_id}`

如果 URL 中不包含 `table=`，会自动取多维表格中的第一个数据表。
如果 URL 中包含 `view=`，会自动解析为 `bt.default_view_id`。

## Record

```python
# 查询
records = bt.list_records()
records = bt.list_records(size_limit=10)
records = bt.list_records(field_names=["名称", "状态"])
records = bt.list_records(view_name="视图名")
records = bt.list_records(use_default_view_id=True)
records = bt.list_records(automatic_fields=True)

# 带过滤条件
records = bt.list_records(field_filter={
    "conditions": [{"field_name": "状态", "operator": "is", "value": ["完成"]}],
    "conjunction": "and",
})

# 带排序
records = bt.list_records(field_sort=[{"field_name": "日期", "desc": True}])

# 解析记录
parsed = bt.list_parsed_records()
parsed = bt.list_parsed_records(automatic_fields=True)

# 单条操作
record = bt.get_record("recxxxx")
first = bt.take_one_record()
rid = bt.create_record({"名称": "test", "状态": "进行中"})["record_id"]
bt.update_record(rid, {"状态": "完成"})
bt.delete_record(rid)

# 批量操作
bt.batch_create_records([{"名称": f"item_{i}"} for i in range(10)])
bt.batch_get_records(["recxxxx1", "recxxxx2"])
bt.batch_update_records([(rid1, {"状态": "完成"}), (rid2, {"状态": "进行中"})])
bt.batch_delete_records(["recxxxx1", "recxxxx2"])
```

写入人员字段时可按需指定 `user_id_type`：

```python
bt.create_record({"负责人": ["ou_xxx"]}, user_id_type="open_id")
bt.batch_update_records([(rid, {"负责人": ["on_xxx"]})], user_id_type="union_id")
```

记录接口的返回值会因飞书接口和字段类型不同而变化。`list_records` / `batch_get_records` 的文本字段通常是 rich-text list，`create_record` / `update_record` 的文本字段通常是字符串。复杂返回结构以函数 docstring 和官方响应为准。

## Field

```python
fields = bt.list_fields()

# field_type 支持 int 或中文名："文本", "数字", "单选", "多选", "日期" 等
bt.create_field("新字段", field_type="数字")

bt.update_field(field_name="旧名", override_payload={"field_name": "新名", "type": 1})
bt.delete_field(field_name="要删除的字段")
```

字段类型速查：

| 中文名 | 类型值 | 中文名 | 类型值 |
|--------|--------|--------|--------|
| 文本 | 1 | 单项关联 | 18 |
| 数字 | 2 | 查找引用 | 19 |
| 单选 | 3 | 公式 | 20 |
| 多选 | 4 | 双向关联 | 21 |
| 日期 | 5 | 地理位置 | 22 |
| 复选框 | 7 | 群组 | 23 |
| 人员 | 11 | 创建时间 | 1001 |
| 电话号码 | 13 | 最后更新时间 | 1002 |
| 超链接 | 15 | 创建人 | 1003 |
| 附件 | 17 | 修改人 | 1004 |
|  |  | 自动编号 | 1005 |

`create_field` 和 `update_field` 的 `field_type` 参数支持传中文名或 int 值。

## View

```python
views = bt.list_views()
info = bt.get_view_info(view_name="表格")

# view_type: "grid" | "kanban" | "gallery" | "gantt" | "form"
bt.create_view("新视图", view_type="grid")
bt.update_view(view_name="旧名称", view_new_name="新名称")
bt.delete_view(view_name="要删除的视图")
```

## Table

```python
tables = bt.list_tables()
size = bt.get_table_size()
meta = bt.get_bitable_meta()

bt.create_table("新数据表")
bt.batch_create_tables(["表1", "表2"])
bt.update_table(table_new_name="新名称")
bt.delete_table(table_name)
bt.batch_delete_tables(table_names=["表1", "表2"])
```

## 素材上传

```python
file_token = bt.upload_media("./photo.jpg")
bt.create_record({"附件": [{"file_token": file_token}]})
```

素材上传到多维表格后无法通过当前 SDK 直接删除，测试时建议只在可清理的测试表里使用。

## API 覆盖

| 资源 | list | get | batch_get | create | batch_create | update | batch_update | delete | batch_delete |
|------|------|-----|-----------|--------|--------------|--------|--------------|--------|--------------|
| Table | yes | - | - | yes | yes | yes | - | yes | yes |
| Record | yes | yes | yes | yes | yes | yes | yes | yes | yes |
| Field | yes | - | - | yes | - | yes | - | yes | - |
| View | yes | yes | - | yes | - | yes | - | yes | - |
| Media | - | - | - | `upload_media` | - | - | - | - | - |

## filter 与 sort

filter 示例：

```python
bt.list_records(field_filter={
    "conditions": [
        {"field_name": "职位", "operator": "is", "value": ["初级销售员"]},
        {"field_name": "销售额", "operator": "isGreater", "value": ["10000.0"]},
    ],
    "conjunction": "and",
})
```

常用 operator：`is`, `isNot`, `contains`, `doesNotContain`, `isEmpty`, `isNotEmpty`, `isGreater`, `isLess` 等。

完整列表见 [官方记录筛选指南](https://open.feishu.cn/document/docs/bitable-v1/app-table-record/record-filter-guide)。

sort 示例：

```python
bt.list_records(field_sort=[{"field_name": "日期", "desc": True}])
```

当 `field_filter` 或 `field_sort` 不为空时，`view_id` / `view_name` 会被忽略。

## 速率限制

批量写入操作默认每批次间等待 0.5 秒，可通过 `request_delay` 参数调整：

```python
bt = Bitable(app_id="...", app_secret="...", bitable_url="...", request_delay=1.0)
```
