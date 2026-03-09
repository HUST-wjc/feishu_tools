from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from ..data_type import map_field_with_type, parse_record

if TYPE_CHECKING:
    from ...feishu_api import FeishuAPI


class RecordMixin:
    """记录 CRUD"""

    feishu_api: FeishuAPI
    app_token: str
    table_id: str
    request_delay: float

    # ── 查询 ──────────────────────────────────────────────────

    def list_records(self,
        field_names: list[str] | None = None,
        field_sort: None | list[dict[str, Any]] = None,
        field_filter: None | dict[str, Any] = None,
        view_name: str | None = None,
        view_list: list[dict[str, Any]] | None = None,
        view_id: str | None = None,
        automatic_fields: bool = False,
        page_size: int = 500,
        size_limit: int = 0,
        timeout: int = 120) -> list[dict[str, Any]]:
        """获取多维表格记录, 值为 None 的字段会被忽略
        https://open.feishu.cn/document/docs/bitable-v1/app-table-record/search
        
        当 filter 参数 或 sort 参数不为空时，请求视为对数据表中的全部数据做条件过滤，指定的 view_id 会被忽略。

        参数说明:
        - size_limit: 限制返回的记录数量，默认不限制
        - field_names: 字段名称，用于指定本次查询返回记录中包含的字段
        - timeout: 请求超时时间，默认 120 秒
        - field_sort: 排序条件
        - field_filter: 包含条件筛选信息的对象
        - view_name: 使用指定 view_name 获取 view_id, 多维表格中视图的唯一标识, 限制获取的数据在指定视图里
        - view_list: 如果已经通过 list_views 获取了视图列表，则可以传入 view_list 参数，避免重复调用 list_views 接口
        - view_id: 如果已经通过 list_views 获取了视图列表，则可以传入 view_id 参数，避免重复调用 list_views 接口
        - automatic_fields: 是否自动计算并返回创建时间 (created_time)、修改时间 (last_modified_time)、创建人 (created_by)、修改人 (last_modified_by) 这四类字段。默认为 false, 表示不返回。

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

        存在历史接口，但是已被官方废弃，请使用 list_parsed_records 代替
        历史接口 url: f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records"

        page_size: 分页大小，默认 500, 官方支持的最大值为 500
        """
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/search"

        if view_name or view_id:
            view_id = self._resolve_view_id(view_name, view_list, view_id) # type: ignore

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

    def list_parsed_records(self, fields_meta: list[dict[str, Any]] | None = None, **kwargs) -> list[tuple[str, dict]]:
        """获取多维表格记录，并根据字段类型进行解析"""
        records = self.list_records(**kwargs)
        if not records:
            return []
        fields_meta = fields_meta or self.list_fields() # type: ignore
        field_type_map = map_field_with_type(fields_meta) # type: ignore
        return [parse_record(field_type_map, record) for record in records]

    def get_record(self, rid: str) -> dict[str, Any]:
        """根据 rid 获取多维表格记录"""
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/{rid}"
        return self.feishu_api.request("GET", url)["record"]

    def batch_get_records(self, rids: list[str], batch_size=100) -> list[dict[str, Any]]:
        """批量获取多维表格记录
        https://open.feishu.cn/document/docs/bitable-v1/app-table-record/batch_get

        通过多个记录 ID 查询记录信息。
        该接口最多支持查询 100 条记录。
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

    def create_record(self, record: dict[str, Any]) -> dict[str, Any]:
        """创建多维表格记录, 返回创建的记录 record, 包含 record_id 键
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/create
        """
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records"
        body = {"fields": record}
        return self.feishu_api.request("POST", url, body=body)["record"]

    def batch_create_records(self, records: list[dict[str, Any]], batch_size=1000) -> list:
        """批量创建多维表格记录
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/batch_create

        单次调用最多新增 1,000 条记录。
        """
        all_results = []
        for i in range(0, len(records), batch_size):
            batch_records = records[i:i + batch_size]
            url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/batch_create"
            body = {"records": [{"fields": record} for record in batch_records]}
            batch_result = self.feishu_api.request("POST", url, body=body)["records"] or []
            all_results.extend(batch_result)
            if i + batch_size < len(records):
                time.sleep(self.request_delay)
        return all_results

    # ── 更新 ──────────────────────────────────────────────────

    def update_record(self, rid: str, record: dict[str, Any]) -> dict[str, Any]:
        """更新多维表格记录
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/update
        """
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/{rid}"
        body = {"fields": record}
        return self.feishu_api.request("PUT", url, body=body)["record"]

    def batch_update_records(self, records: list[tuple[str, dict[str, Any]]], batch_size=1000) -> list:
        """
        批量更新多维表格记录
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/batch_update

        需要 records 格式为 [(record_id, record_dict), ...]

        单次调用最多更新 1,000 条记录
        """
        all_results = []
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/batch_update"

        for i in range(0, len(records), batch_size):
            batch_records = records[i:i + batch_size]
            _records = [{"record_id": rid, "fields": record} for rid, record in batch_records]
            body = {"records": _records}
            batch_result = self.feishu_api.request("POST", url, body=body)["records"]
            all_results.extend(batch_result)
            if i + batch_size < len(records):
                time.sleep(self.request_delay)
        return all_results

    # ── 删除 ──────────────────────────────────────────────────

    def delete_record(self, rid: str) -> dict[str, Any]:
        """删除多维表格记录
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/delete

        rid: 数据表中一条记录的唯一标识。通过查询记录接口获取。
        """
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/{rid}"
        return self.feishu_api.request("DELETE", url)

    def batch_delete_records(self, rids: list[str], batch_size=500) -> list[dict[str, Any]]:
        """批量删除多维表格记录
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-record/batch_delete

        单次调用中最多删除 500 条记录
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