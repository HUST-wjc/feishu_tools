# Spreadsheet 用户指南

`FeishuSpreadsheet` 封装飞书电子表格的元数据、工作表查询、单元格读写、追加、前插、查找和替换。

## 初始化

```python
from feishukit import FeishuSpreadsheet

ss = FeishuSpreadsheet(
    app_id="cli_xxxx",
    app_secret="xxxx",
    spreadsheet_url="https://xxx.feishu.cn/wiki/xxxxx?sheet=abc123",
)
```

`spreadsheet_url` 支持两种格式：

- 知识库中的电子表格：`https://xxx.feishu.cn/wiki/{node_token}?sheet={sheet_id}`
- 个人目录中的电子表格：`https://xxx.feishu.cn/sheets/{spreadsheet_token}?sheet={sheet_id}`

如果 URL 中不包含 `sheet=`，不会自动取第一个工作表。读取或写入数据时，需要显式传入完整 range、`sheet_id` 或 `sheet_name`，避免误操作其它工作表。

## Spreadsheet / Sheet

```python
meta = ss.get_spreadsheet_meta()
sheets = ss.list_sheets()
sheet = ss.get_sheet(sheet_name="Sheet1")
sheet_id = ss.resolve_sheet_id(sheet_name="Sheet1")
```

## 读取

```python
value_range = ss.get_values("abc123!A1:C10")
value_range = ss.get_values("A1:C10", sheet_id="abc123")
value_range = ss.get_values(sheet_id="abc123", cell_range="A1:C10")
value_range = ss.get_values(sheet_name="Sheet1", cell_range="A1:C10")

rows = ss.get_rows(sheet_name="Sheet1", cell_range="A1:C10")
cell = ss.get_cell("A1", sheet_name="Sheet1")
records = ss.get_records(sheet_name="Sheet1", cell_range="A1:C10")

value_ranges = ss.batch_get_values(["abc123!A1:C10", "def456!A1:B2"])
```

`get_values()` 默认返回飞书原始 `valueRange` 结构。

`get_rows()` 返回二维列表。

`get_records()` 使用读取范围内的第一行作为表头，返回 `list[dict]`。

日期、公式和人员字段的渲染方式可通过 `value_render_option`、`date_time_render_option` 和 `user_id_type` 控制。

## 写入

```python
ss.update_values("abc123!A1:B2", [["Hello", 1], ["World", 2]])
ss.update_values("A1", [["Hello", 1], ["World", 2]], sheet_id="abc123")
ss.update_values(values=[["Hello", 1]], sheet_name="Sheet1", cell_range="A1:B1")

ss.batch_update_values([("abc123!A1:B1", [["x", "y"]])])
```

如果传入单个起始单元格，例如 `A1`，`update_values()` 会按 `values` 的行列数自动扩展为矩形范围。

## 追加和前插

```python
ss.append_values("abc123!A:B", [["new", "row"]], insert_data_option="INSERT_ROWS")
ss.prepend_values("abc123!A2:B2", [["inserted", "row"]])
```

## 查找和替换

```python
ss.find_values("Hello", sheet_name="Sheet1", cell_range="A1:C10")
ss.replace_values("Hello", "Hi", sheet_name="Sheet1", cell_range="A1:C10", match_entire_cell=True)
```

如果不传 `range` 或 `cell_range`，查找和替换会在整张工作表中执行。
