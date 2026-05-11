from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from ...feishu_api import FeishuRuntimeError
from ..data_type import map_field_with_type, parse_record

if TYPE_CHECKING:
    from ...feishu_api import FeishuAPI


class RecordMixin:
    """记录 CRUD"""

    feishu_api: FeishuAPI
    app_token: str
    table_id: str
    default_view_id: str | None
    request_delay: float

    # ── 查询 ──────────────────────────────────────────────────

    def list_records(self,
        *,
        field_names: list[str] | None = None,
        field_sort: None | list[dict[str, Any]] = None,
        field_filter: None | dict[str, Any] = None,
        view_name: str | None = None,
        view_list: list[dict[str, Any]] | None = None,
        view_id: str | None = None,
        use_default_view_id: bool = False,
        automatic_fields: bool = False,
        page_size: int = 500,
        size_limit: int = 0,
        timeout: int = 120) -> list[dict[str, Any]]:
        """获取多维表格记录, 值为 None 的字段会被忽略
        https://open.feishu.cn/document/docs/bitable-v1/app-table-record/search
        
        参数很多, 所以禁止了位置参数, 必须使用关键字参数调用。
        当 filter 参数 或 sort 参数不为空时, 请求视为对数据表中的全部数据做条件过滤, 指定的 view_id 会被忽略。

        参数说明:
        - field_names: 字段名称, 用于指定本次查询返回记录中包含的字段
        - field_sort: 排序条件
        - field_filter: 包含条件筛选信息的对象
        - view_name: 使用指定 view_name 获取 view_id, 多维表格中视图的唯一标识, 限制获取的数据在指定视图里
        - view_list: 如果已经通过 list_views 获取了视图列表, 则可以传入 view_list 参数, 避免重复调用 list_views 接口
        - view_id: 如果已经通过 list_views 获取了视图列表, 则可以传入 view_id 参数, 避免重复调用 list_views 接口
        - use_default_view_id: 当 view_name 和 view_id 都为空时, 是否使用 bitable_url 中解析出的 default_view_id。默认为 false。
        - automatic_fields: 是否自动计算并返回创建时间 (created_time)、修改时间 (last_modified_time)、创建人 (created_by)、修改人 (last_modified_by) 这四类字段。默认为 false, 表示不返回。
        - page_size: 分页大小, 默认 500, 官方支持的最大值为 500
        - size_limit: 限制返回的记录数量, 默认不限制
        - timeout: 请求超时时间, 默认 120 秒

        返回示例:
        [
            {
                "record_id": "recABCDEFG",
                "fields": {
                    "标题": [{"text": "Hello", "type": "text"}],
                    "单选": "选项A",
                    "多选": ["选项A", "选项B"],
                    "日期": 1772380800000,
                    "公式": {"type": 5, "value": [1772380800000]},
                    "附件": [{"file_token": "file_xxx", "name": "cat.jpg", ...}],
                },
            }
            ...
        ]

        注意:
        - 文本字段在 list_records 中通常是 rich-text list。
        - 日期字段为时间戳, 毫秒
        - 公式字段返回的实际计算值, 不是公式字符串
        - automatic_fields=True 时 created_time / last_modified_time / created_by / last_modified_by 位于 record 顶层。
        - 如需简化的返回值, 可使用 list_parsed_records。

        sort 示例
        "sort": [
            {
                "desc": true,
                "field_name": "多行文本"
            }
        ],

        filter 示例
        官方文档 https://open.feishu.cn/document/docs/bitable-v1/app-table-record/record-filter-guide
        ```
        "filter": {
        "conditions": [
            {
                "field_name": "职位",
                "operator": "is",
                "value": [
                    "初级销售员"
                ]
            },
            {
                "field_name": "销售额",
                "operator": "isGreater",
                "value": [
                    "10000.0"
                ]
            }
        ],
        "conjunction": "and"
        },
        ```

        飞书存在历史列表接口, 但是已被官方废弃。本函数使用 search 接口。
        历史接口 url: f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records"

        page_size: 分页大小, 默认 500, 官方支持的最大值为 500
        """
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/search"

        if view_name or view_id:
            view_id = self._resolve_view_id(view_name, view_list, view_id) # type: ignore
        else:
            view_id = self.default_view_id if use_default_view_id else None

        body = {}

        if field_names:
            body['field_names'] = field_names
        if field_filter:
            body['filter'] = field_filter
        if field_sort:
            body['sort'] = field_sort
        if view_id:
            body['view_id'] = view_id
        if automatic_fields:
            body['automatic_fields'] = automatic_fields
        return self.feishu_api.paginate("POST", url, body=body, page_size=page_size, size_limit=size_limit, timeout=timeout)

    def take_one_record(self) -> dict[str, Any]:
        """获取多维表格第一条记录"""
        records = self.list_records(size_limit=1)
        return records[0] if records else {}

    def list_parsed_records(self, fields_meta: list[dict[str, Any]] | None = None, **kwargs) -> list[tuple[str, dict] | tuple[str, dict, dict]]:
        """获取多维表格记录, 并根据字段类型进行轻量解析。是更推荐的获取记录方式

        解析规则:
        - 文本类型 (1): rich-text list 拼接为纯字符串
        - 数字类型 (2): 一元素 list 会展平为单值
        - 公式/查找引用类型 (19/20): 取内部 value 后按内部 type 再解析
        - 其余类型: 保持飞书原始返回值

        返回示例 (automatic_fields=False):
        [
            ("recABCDEFG", {"标题": "Hello", "多选": ["选项A", "选项B"], "日期公式": [1772380800000]}),
        ]

        返回示例 (automatic_fields=True):
        [
            (
                "recABCDEFG",
                {"标题": "Hello"},
                {
                    "created_time": 1772440098000,
                    "last_modified_time": 1772527309000,
                    "created_by": {"id": "ou_xxx", "name": "张三", ...},
                    "last_modified_by": {"id": "ou_xxx", "name": "张三", ...},
                },
            )
        ]
        """
        records = self.list_records(**kwargs)
        if not records:
            return []
        automatic_fields = kwargs.get('automatic_fields', False)
        fields_meta = fields_meta or self.list_fields() # type: ignore
        field_type_map = map_field_with_type(fields_meta) # type: ignore
        return [parse_record(field_type_map, record, automatic_fields=automatic_fields) for record in records]

    def get_record(self, rid: str) -> dict[str, Any]:
        """根据 rid 获取多维表格记录

        飞书存在历史获取单个记录接口, 但官方已不推荐使用。
        https://open.feishu.cn/open-apis/bitable/v1/apps/:app_token/tables/:table_id/records/:record_id

        函数内实现已经改为调用 `batch_get_records`。

        返回单个 record dict:
        {
            "record_id": "recABCDEFG",
            "fields": {
                "标题": [{"text": "Hello", "type": "text"}],
                "日期": 1778256000000,
                "公式": {"type": 5, "value": [1778256000000]},
            },
        }

        注意: 文本字段为 rich-text list, 不是 create_record/update_record 返回中的字符串。
        不存在的 rid 会抛 FeishuRuntimeError。
        """
        res = self.batch_get_records([rid])
        if not res:
            raise FeishuRuntimeError(f"记录 {rid} 不存在")
        return res[0]

    def batch_get_records(self, rids: list[str], batch_size: int = 100) -> list[dict[str, Any]]:
        """批量获取多维表格记录
        https://open.feishu.cn/document/docs/bitable-v1/app-table-record/batch_get

        通过多个记录 ID 查询记录信息。
        该接口最多支持查询 100 条记录。

        只会返回 rid 存在的记录
        不存在的 rid 不会返回空字典 或 None

        返回示例:
        [
            {
                "record_id": "recABCDEFG",
                "fields": {
                    "标题": [{"text": "Hello", "type": "text"}],
                    "日期": 1778256000000,
                    "公式": {"type": 5, "value": [1778256000000]},
                },
            },
            ...
        ]
        """
        all_results = []
        for i in range(0, len(rids), batch_size):
            batch_rids = rids[i:i + batch_size]
            url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/batch_get"
            body = {"record_ids": batch_rids}
            batch_result = self.feishu_api.request("POST", url, body=body)["records"]
            all_results.extend(batch_result)
            if i + batch_size < len(rids):
                time.sleep(self.request_delay)
        return all_results

    # ── 创建 ──────────────────────────────────────────────────

    def create_record(self, record: dict[str, Any], user_id_type: str | None = None) -> dict[str, Any]:
        """创建多维表格记录, 返回创建的记录 record, 包含 record_id 键
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/create

        参数说明:
        - user_id_type: 可选值为 'open_id', 'union_id', 'user_id', 非必填，默认 open_id。
        - record 中的 fields:
            需先指定数据表中的字段（即指定列）, 再传入正确格式的数据作为一条记录。
            该接口支持的字段类型及其描述如下所示：

            文本：原值展示, 不支持 markdown 语法
            数字：填写数字格式的值
            单选：填写选项值, 对于新的选项值, 将会创建一个新的选项
            多选：填写多个选项值, 对于新的选项值, 将会创建一个新的选项。如果填写多个相同的新选项值, 将会创建多个相同的选项
            日期：填写毫秒级时间戳
            复选框：填写 true 或 false
            人员：填写用户的open_id、union_id 或 user_id, 类型需要与 user_id_type 指定的类型一致
            电话号码：填写文本内容
            超链接：字典值, text 为文本值, link 为 URL 链接
            附件：填写附件 token, 需要先调用上传素材或分片上传素材接口将附件上传至该多维表格中
            单向关联：填写被关联表的记录 ID
            双向关联：填写被关联表的记录 ID
            地理位置：填写经纬度坐标
            不同类型字段的数据结构请参考数据结构概述(https://open.feishu.cn/document/docs/bitable-v1/app-table-record/bitable-record-data-structure-overview)。

            示例值：{"文本":"HelloWorld"}

        返回示例:
        {
            "id": "recABCDEFG",
            "record_id": "recABCDEFG",
            "fields": {"标题": "Hello"},
        }

        注意: 文本字段在 create_record 返回中为字符串, 不是 list_records/batch_get_records 的 rich-text list。
        
        """
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records"
        body = {"fields": record}
        params = {"user_id_type": user_id_type} if user_id_type else None
        return self.feishu_api.request("POST", url, body=body, params=params)["record"]

    def batch_create_records(self, records: list[dict[str, Any]], batch_size: int = 1000, user_id_type: str | None = None) -> list[dict[str, Any]]:
        """批量创建多维表格记录
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/batch_create

        单次调用最多新增 1,000 条记录。

        参数说明:
        - user_id_type: 可选值为 'open_id', 'union_id', 'user_id', 非必填，默认 open_id。
        records 中的每个 record 的 fields 的格式参考 create_record 参数说明

        返回示例:
        [
            {
                "id": "recABCDEFG",
                "record_id": "recABCDEFG",
                "fields": {"标题": "批量测试_0"},
            },
            ...
        ]
        """
        all_results = []
        params = {"user_id_type": user_id_type} if user_id_type else None
        for i in range(0, len(records), batch_size):
            batch_records = records[i:i + batch_size]
            url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/batch_create"
            body = {"records": [{"fields": record} for record in batch_records]}
            batch_result = self.feishu_api.request("POST", url, body=body, params=params)["records"] or []
            all_results.extend(batch_result)
            if i + batch_size < len(records):
                time.sleep(self.request_delay)
        return all_results

    # ── 更新 ──────────────────────────────────────────────────

    def update_record(self, rid: str, record: dict[str, Any], user_id_type: str | None = None) -> dict[str, Any]:
        """更新多维表格记录
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/update
        
        参数说明:
        - user_id_type: 可选值为 'open_id', 'union_id', 'user_id', 非必填，默认 open_id。
        record 中的 fields 的格式参考 create_record 参数说明

        返回更新后的单个 record dict:
        {
            "id": "recABCDEFG",
            "record_id": "recABCDEFG",
            "fields": {"标题": "Hello"},
        }

        注意: 文本字段在 update_record 返回中为字符串, 不是 list_records/batch_get_records 的 rich-text list。
        """
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/{rid}"
        body = {"fields": record}
        params = {"user_id_type": user_id_type} if user_id_type else None
        return self.feishu_api.request("PUT", url, body=body, params=params)["record"]

    def batch_update_records(self, records: list[tuple[str, dict[str, Any]]], batch_size: int = 1000, user_id_type: str | None = None) -> list[dict[str, Any]]:
        """
        批量更新多维表格记录
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/batch_update

        需要 records 格式为 [(record_id, record_dict), ...]
        单次调用最多更新 1,000 条记录

        参数说明:
        - user_id_type: 可选值为 'open_id', 'union_id', 'user_id', 非必填，默认 open_id。
        records 中的每个 record 的 fields 的格式参考 create_record 参数说明

        返回示例:
        [
            {
                "id": "recABCDEFG",
                "record_id": "recABCDEFG",
                "fields": {"标题": "批量已更新_0"},
            },
            ...
        ]
        """
        all_results = []
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/batch_update"
        params = {"user_id_type": user_id_type} if user_id_type else None
        for i in range(0, len(records), batch_size):
            batch_records = records[i:i + batch_size]
            _records = [{"record_id": rid, "fields": record} for rid, record in batch_records]
            body = {"records": _records}
            batch_result = self.feishu_api.request("POST", url, body=body, params=params)["records"]
            all_results.extend(batch_result)
            if i + batch_size < len(records):
                time.sleep(self.request_delay)
        return all_results

    # ── 删除 ──────────────────────────────────────────────────

    def delete_record(self, rid: str) -> dict[str, Any]:
        """删除多维表格记录
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/delete

        rid: 数据表中一条记录的唯一标识。通过查询记录接口获取。

        返回示例:
        {"deleted": True, "record_id": "recABCDEFG"}
        """
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/{rid}"
        return self.feishu_api.request("DELETE", url)

    def batch_delete_records(self, rids: list[str], batch_size: int = 500) -> list[dict[str, Any]]:
        """批量删除多维表格记录
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/batch_delete

        单次调用中最多删除 500 条记录

        返回示例:
        [
            {"deleted": True, "record_id": "recABCDEFG"},
            {"deleted": True, "record_id": "recHIJKLMN"},
        ]
        """
        res = []
        for i in range(0, len(rids), batch_size):
            batch_rids = rids[i:i + batch_size]
            url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/batch_delete"
            body = {"records": batch_rids}
            batch_result = self.feishu_api.request("POST", url, body=body)["records"] or []
            res.extend(batch_result)
            if i + batch_size < len(rids):
                time.sleep(self.request_delay)
        return res
