FIELD_TYPE_MAP: dict[str, int] = {
    "文本": 1,
    "数字": 2,
    "单选": 3,
    "多选": 4,
    "日期": 5,
    "复选框": 7,
    "人员": 11,
    "电话号码": 13,
    "超链接": 15,
    "附件": 17,
    "单项关联": 18,
    "查找引用": 19, # 本质上为公式
    "公式": 20,
    "双向关联": 21,
    "地理位置": 22,
    "群组": 23,
    "创建时间": 1001,
    "最后更新时间": 1002,
    "创建人": 1003,
    "修改人": 1004,
    "自动编号": 1005,
}

TEXT = 1

# 人员类型 (11, 1003, 1004) 为列表，包含字段 avatar_url, email, en_name, id, name


def map_field_with_type(fields_meta: list[dict]) -> dict[str, int]:
    """根据字段元信息，返回字段名称到字段类型的映射"""
    field_type_map = {}
    for field in fields_meta:
        name = field.get("field_name")
        typ = field.get("type")
        if name and typ:
            field_type_map[name] = int(typ)
    return field_type_map


def parse_record(field_type_map: dict, record: dict) -> tuple[str, dict]:
    """仅对需要结构化展平的类型做处理，其余保持原始值
    未来可能会持续优化
    """
    record_id = record["record_id"]
    fields = record.get("fields") or {}
    
    output = {}
    for field, value in fields.items():
        if field is None:
            continue
        typ = field_type_map.get(field)
        if typ == TEXT:
            if value:
                output[field] = "".join(v["text"] for v in value)
            else:
                output[field] = ""
        else:
            output[field] = value
    return record_id, output