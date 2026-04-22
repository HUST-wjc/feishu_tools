"""feishukit — Bitable 用法示例

⚠️ 使用前:
  1. 前往 https://open.feishu.cn/app 创建应用，获取 app_id 和 app_secret
  2. 为应用申请 bitable:app 权限 (多维表格放在知识库中还需 wiki:wiki:readonly)
  3. 将应用添加为多维表格的协作者
  4. 请在新建的、非生产环境的多维表格上运行本脚本，测试中包含删除操作
"""

if __name__ == "__main__":
    from pprint import pprint
    from feishukit import Bitable

    # ── 配置 ──────────────────────────────────────────────────────
    # 替换为你自己的应用凭据和多维表格 URL
    APP_ID = "cli_xxxx"
    APP_SECRET = "xxxx"
    BITABLE_URL = "https://xxx.feishu.cn/base/xxxxx?table=tblxxxx&view=vewxxxx"
    # 支持两种格式:
    #   知识库: https://xxx.feishu.cn/wiki/{node_token}?table={table_id}&view={view_id}
    #   个人目录: https://xxx.feishu.cn/base/{app_token}?table={table_id}&view={view_id}
    # 不带 ?table= 时自动取第一个数据表

    # ── 1. URL 解析 (纯本地, 无网络请求) ─────────────────────────

    wiki_url = "https://xxx.feishu.cn/wiki/ABC123def?table=tblXYZ789&view=vewXYZ789"
    url_type, node_token, table_id, view_id = Bitable.parse_bitable_url(wiki_url)
    print(f"wiki URL:  url_type={url_type}, node_token={node_token}, table_id={table_id}, view_id={view_id}")

    base_url = "https://xxx.feishu.cn/base/ZLIxbFb5BaAEfBsXSricKtYCnGf"
    url_type, node_token, table_id, view_id = Bitable.parse_bitable_url(base_url)
    print(f"base URL:  url_type={url_type}, node_token={node_token}, table_id={table_id}, view_id={view_id}")

    # ── 2. 初始化 & 元数据 ──────────────────────────────────────

    bt = Bitable(app_id=APP_ID, app_secret=APP_SECRET, bitable_url=BITABLE_URL)
    print(f"\napp_token:  {bt.app_token}")
    print(f"table_id:   {bt.table_id}")
    print(f"default_view_id: {bt.default_view_id}")

    meta = bt.get_bitable_meta()
    pprint(meta)

    # ── 3. Table 操作 ───────────────────────────────────────────

    tables = bt.list_tables()
    print(f"\n数据表数量: {len(tables)}")
    for t in tables:
        print(f"  {t['table_id']}: {t['name']}")

    size = bt.get_table_size()
    print(f"当前数据表记录数: {size}")

    # 批量创建 → 批量删除
    bt.batch_create_tables(["示例表1", "示例表2"])
    bt.batch_delete_tables(table_names=["示例表1", "示例表2"])
    print("Table 批量创建 → 删除: 成功")

    # ── 4. Field 操作 ───────────────────────────────────────────

    fields = bt.list_fields()
    print(f"\n字段数量: {len(fields)}")
    for f in fields:
        print(f"  {f['field_id']}: {f['field_name']} (type={f['type']})")

    # 创建 → 更新 → 删除
    new_field = bt.create_field("测试字段", field_type="数字")
    print(f"\n创建字段: {new_field['field_name']} (type={new_field['type']})")

    bt.update_field(field_id=new_field["field_id"], override_payload={
        "field_name": "测试字段_改名",
        "type": 2,
    })
    print("更新字段: 成功")

    bt.delete_field(field_id=new_field["field_id"])
    print("删除字段: 成功")

    # ── 5. Record 操作 — 查询 ───────────────────────────────────

    first_field = fields[0]["field_name"]

    records = bt.list_records()
    print(f"\n全部记录数: {len(records)}")

    records = bt.list_records(size_limit=2)
    print(f"size_limit=2: {len(records)} 条")

    one = bt.take_one_record()
    print(f"take_one_record: {one.get('record_id', 'N/A')}")

    # 带过滤
    records = bt.list_records(field_filter={
        "conditions": [{"field_name": first_field, "operator": "isNotEmpty", "value": []}],
        "conjunction": "and",
    })
    print(f"filter (isNotEmpty): {len(records)} 条")

    # 带排序
    records = bt.list_records(field_sort=[{"field_name": first_field, "desc": True}], size_limit=3)
    print(f"sort (desc, limit 3): {len(records)} 条")

    # 使用 bitable_url 中的默认视图
    records = bt.list_records(use_default_view_id=True, size_limit=3)
    print(f"default view (limit 3): {len(records)} 条")

    # 解析记录 — 自动展平文本类型
    parsed = bt.list_parsed_records(size_limit=2)
    print(f"\nlist_parsed_records (limit 2):")
    for rid, data in parsed:
        print(f"  {rid}: {data}")

    parsed_auto = bt.list_parsed_records(size_limit=1, automatic_fields=True)
    print(f"\nlist_parsed_records (automatic_fields=True, limit 1):")
    for rid, data, meta in parsed_auto:
        print(f"  {rid}: {data}")
        print(f"  meta: {meta}")

    # ── 6. Record 操作 — 单条 & 批量 CRUD ───────────────────────

    print("\n--- 单条记录 CRUD ---")
    record = bt.create_record({first_field: "测试记录"})
    rid = record["record_id"]
    print(f"创建: {rid}")

    record = bt.get_record(rid)
    print(f"获取: {record['fields'].get(first_field)}")

    bt.update_record(rid, {first_field: "测试记录_已更新"})
    print("更新: 成功")

    bt.delete_record(rid)
    print("删除: 成功")

    print("\n--- 批量记录 CRUD ---")
    new_records = [{first_field: f"批量_{i}"} for i in range(5)]
    created = bt.batch_create_records(new_records)
    created_ids = [r["record_id"] for r in created]
    print(f"batch_create: {len(created_ids)} 条")

    batch_got = bt.batch_get_records(created_ids)
    print(f"batch_get:    {len(batch_got)} 条")

    updates = [(rid, {first_field: f"已更新_{i}"}) for i, rid in enumerate(created_ids)]
    bt.batch_update_records(updates)
    print(f"batch_update: {len(updates)} 条")

    bt.batch_delete_records(created_ids)
    print(f"batch_delete: {len(created_ids)} 条")

    # ── 7. 素材上传 ──────────────────────────────────────────────

    # 上传图片/文件到多维表格, parent_type 根据扩展名自动推导
    TEST_FILE = "./test.jpg"  # 替换为你自己的测试文件
    file_token = bt.upload_media(TEST_FILE)
    print(f"\n上传素材: file_token={file_token}")

    # 确保有附件字段 (type=17)
    attachment_field = next((f for f in fields if f["type"] == 17), None)
    if not attachment_field:
        attachment_field = bt.create_field("附件", field_type="附件")
        print(f"创建附件字段: {attachment_field['field_name']}")

    # 将素材写入记录的附件字段
    record = bt.create_record({attachment_field["field_name"]: [{"file_token": file_token}]})
    rid = record["record_id"]
    print(f"写入附件记录: {rid}")
    bt.delete_record(rid)
    print("清理附件记录: 成功")

    # ── 8. View 操作 ────────────────────────────────────────────

    views = bt.list_views()
    print(f"\n视图数量: {len(views)}")
    for v in views:
        print(f"  {v['view_id']}: {v['view_name']} ({v['view_type']})")

    if views:
        info = bt.get_view_info(view_name=views[0]["view_name"])
        pprint(info)

    # 创建 → 更新 → 删除
    new_view = bt.create_view("test_view", view_type="grid")
    print(f"\n创建视图: {new_view['view_name']} ({new_view['view_type']})")

    bt.update_view(view_id=new_view["view_id"], view_new_name="test_view_renamed")
    print("更新视图: 成功")

    bt.delete_view(view_id=new_view["view_id"])
    print("删除视图: 成功")
