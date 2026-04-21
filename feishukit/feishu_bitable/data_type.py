''' 官方字段编辑指南
https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/guide

查找引用 (19) 和 公式 (20) 字段, 在使用列出记录接口时, 返回的实际值而不是公式，比如 "{'type': 1, 'value': [{'text': 'xxx', 'type': 'text'}]}"
人员类型 (11, 1003, 1004) 为列表, 包含字段 avatar_url, email, en_name, id, name
'''

FIELD_TYPE_MAP_CN: dict[str, int] = {
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
    "查找引用": 19,
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

# ui_type (PascalCase) → type 的完整映射见飞书文档，此处仅覆盖 CN 表已有类型
_FIELD_TYPE_EN: dict[str, int] = {
    "Text": 1,
    "Number": 2,
    "SingleSelect": 3,
    "MultiSelect": 4,
    "DateTime": 5,
    "Checkbox": 7,
    "User": 11,
    "Phone": 13,
    "Url": 15,
    "Attachment": 17,
    "SingleLink": 18,
    "Lookup": 19,
    "Formula": 20,
    "DuplexLink": 21,
    "Location": 22,
    "GroupChat": 23,
    "CreatedTime": 1001,
    "ModifiedTime": 1002,
    "CreatedUser": 1003,
    "ModifiedUser": 1004,
    "AutoNumber": 1005,
}

FIELD_TYPE_MAP_EN: dict[str, int] = {
    **_FIELD_TYPE_EN,
    **{k.lower(): v for k, v in _FIELD_TYPE_EN.items()},
}

FIELD_TYPE_MAP: dict[str, int] = {**FIELD_TYPE_MAP_CN, **FIELD_TYPE_MAP_EN}

TEXT_TYPE = 1
NUMBER_TYPE = 2
FORMULA_TYPE = {19, 20}


def map_field_with_type(fields_meta: list[dict]) -> dict[str, int]:
    """根据字段元信息，返回字段名称到字段类型的映射"""
    field_type_map = {}
    for field in fields_meta:
        name = field.get("field_name")
        typ = field.get("type")
        if name and typ:
            field_type_map[name] = int(typ)
    return field_type_map


def parse_record(field_type_map: dict, record: dict, automatic_fields: bool = False) -> tuple[str, dict] | tuple[str, dict, dict]:
    """将单条记录解析为 (record_id, fields_dict) 或 (record_id, fields_dict, meta_dict)。

    处理规则:
    - 文本类型 (1): 将 rich-text 列表拼接为纯字符串
    - 数字类型 (2): 公式返回的数字列表自动展平为单值
    - 公式/引用类型 (19, 20): 提取实际值后按其内部类型递归处理
    - 其余类型: 保持飞书原始返回值不变

    automatic_fields=True 时额外返回第三个元素 meta_dict，
    包含 created_time / last_modified_time / created_by / last_modified_by。
    """
    record_id = record["record_id"]
    fields = record.get("fields") or {}

    output = {}
    for field, value in fields.items():
        if field is None:
            continue
        typ = field_type_map.get(field)
        if typ in FORMULA_TYPE and isinstance(value, dict):
            # 尝试解析公式类型，解析失败回退回原始类型
            raw_typ = typ
            typ = value.get("type")
            if typ:
                value = value.get("value")
            else:
                typ = raw_typ
        if typ == TEXT_TYPE:
            parsed_value = "".join(v["text"] for v in value) if value else ""
        elif typ == NUMBER_TYPE:
            # 一般 number 类型返回的是数字本身，不用解析
            # 公式类型 number 类型返回的 value 是数字列表，需要展平
            parsed_value = value[0] if isinstance(value, list) and len(value) == 1 else value
        else:
            parsed_value = value
        output[field] = parsed_value

    if automatic_fields:
        record_meta_fields = ['created_time', 'last_modified_time', 'created_by', 'last_modified_by']
        record_meta = {field: record.get(field) for field in record_meta_fields}
        return record_id, output, record_meta
    
    return record_id, output
