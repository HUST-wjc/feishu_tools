"""feishukit — Spreadsheet 用法示例

使用前:
  1. 前往 https://open.feishu.cn/app 创建应用，获取 app_id 和 app_secret
  2. 为应用申请 sheets:spreadsheet.meta:read / sheets:spreadsheet:read / sheets:spreadsheet:write_only 权限
     (电子表格放在知识库中还需 wiki:node:read)
  3. 将应用添加为电子表格的协作者
  4. 请在新建的、非生产环境的电子表格上运行写入示例
"""

if __name__ == "__main__":
    from pprint import pprint
    from feishukit import FeishuSpreadsheet

    APP_ID = "cli_xxxx"
    APP_SECRET = "xxxx"
    SPREADSHEET_URL = "https://xxx.feishu.cn/sheets/xxxxx?sheet=abc123"
    # 支持两种格式:
    #   知识库: https://xxx.feishu.cn/wiki/{node_token}?sheet={sheet_id}
    #   个人目录: https://xxx.feishu.cn/sheets/{spreadsheet_token}?sheet={sheet_id}
    # 不带 ?sheet= 时不会自动取第一个工作表

    url_type, token, default_sheet_id = FeishuSpreadsheet.parse_spreadsheet_url(SPREADSHEET_URL)
    print(f"url_type={url_type}, token={token}, default_sheet_id={default_sheet_id}")

    ss = FeishuSpreadsheet(app_id=APP_ID, app_secret=APP_SECRET, spreadsheet_url=SPREADSHEET_URL)
    print(ss)
    print(f"spreadsheet_token: {ss.spreadsheet_token}")
    print(f"default_sheet_id: {ss.default_sheet_id}")

    meta = ss.get_spreadsheet_meta()
    pprint(meta)

    sheets = ss.list_sheets()
    print(f"工作表数量: {len(sheets)}")
    for s in sheets:
        grid = s.get("grid_properties") or {}
        print(f"  {s['sheet_id']}: {s['title']} rows={grid.get('row_count')} cols={grid.get('column_count')}")

    # 读取方式 1: 完整官方 range
    values = ss.get_values("abc123!A1:C10", value_render_option="ToString")
    pprint(values)

    # 读取方式 2: 相对 range + sheet_id
    # values = ss.get_values("A1:C10", sheet_id="abc123", value_render_option="ToString")

    # 读取方式 3: sheet_id + cell_range
    # values = ss.get_values(sheet_id="abc123", cell_range="A1:C10", value_render_option="ToString")

    # 读取方式 4: sheet_name + cell_range
    # values = ss.get_values(sheet_name="Sheet1", cell_range="A1:C10", value_render_option="ToString")

    # 解析读取
    # rows = ss.get_rows(sheet_name="Sheet1", cell_range="A1:C10", value_render_option="ToString")
    # records = ss.get_records(sheet_name="Sheet1", cell_range="A1:C10", value_render_option="ToString")
    # cell = ss.get_cell("A1", sheet_name="Sheet1", value_render_option="ToString")

    # 写入示例: 覆盖 A1:B2。传入单格 A1 时会按 values 尺寸自动扩展范围。
    # ss.update_values(values=[["Hello", 1], ["World", 2]], sheet_name="Sheet1", cell_range="A1:B2")
    # ss.update_values("A1", [["Hello", 1], ["World", 2]], sheet_name="Sheet1")

    # 追加示例: 找到 A:B 范围的第一个空白位置后写入
    # ss.append_values("abc123!A:B", [["new", "row"]], insert_data_option="INSERT_ROWS")

    # 查找 / 替换
    # ss.find_values("Hello", sheet_name="Sheet1", cell_range="A1:C10")
    # ss.replace_values("Hello", "Hi", sheet_name="Sheet1", cell_range="A1:C10", match_entire_cell=True)
