from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ..data_type import FIELD_TYPE_MAP

if TYPE_CHECKING:
    from ...feishu_api import FeishuAPI


class FieldMixin:
    """字段 CRUD"""

    feishu_api: FeishuAPI
    app_token: str
    table_id: str

    # ── 查询 ──────────────────────────────────────────────────

    def list_fields(self) -> list[dict[str, Any]]:
        """获取多维表格列
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/list

        响应示例:
        
        ```
        [
        {'field_id': 'fld1RPTPLu',
        'field_name': '一级分类',
        'is_primary': True,
        'property': None,
        'type': 1,
        'ui_type': 'Text'},
        ...
        ]
        ```
        """
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/fields"
        return self.feishu_api.paginate("GET", url)
    
    def _resolve_field_type(self, field_type: int | str | None = None) -> int:
        raw_field_type = field_type
        if isinstance(field_type, str):
            field_type = FIELD_TYPE_MAP.get(field_type)
            if field_type is None:
                raise ValueError(f"不支持的字段类型: {raw_field_type}, 支持的字段类型: {FIELD_TYPE_MAP.keys()}")
        elif field_type is None:
            field_type = 1
        elif not isinstance(field_type, int):
            raise ValueError((
            f"field_type 必须是 int 类型 或者 str 类型, "
            f"int 类型可选: {FIELD_TYPE_MAP.values()}, str 类型可选: {FIELD_TYPE_MAP.keys()}, "
            f"当前传入值为: {raw_field_type}"
            ))
        return field_type

    # ── 创建 ──────────────────────────────────────────────────

    def create_field(self, field_name: str, field_type: int | str | None = None, override_payload: dict[str, Any] | None = None):
        """创建多维表格列
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/create
        """
        if not override_payload:
            field_type = self._resolve_field_type(field_type)

            payload = {
                "field_name": field_name,
                "type": field_type,
            }
        else:
            payload = override_payload

        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/fields"
        return self.feishu_api.request("POST", url, body=payload)["field"]

    def _resolve_field_info(self, field_name=None, fields_list=None, field_id=None) -> tuple[str, str, int]:
        if not field_name and not field_id:
            raise ValueError("field_name 和 field_id 不能同时为空")
        fields_list = fields_list or self.list_fields()
        for f in fields_list:
            if f["field_name"] == field_name or f["field_id"] == field_id:
                return f["field_id"], f["field_name"], f["type"]
        raise ValueError(f"字段不存在, field_name: {field_name}, field_id: {field_id}")

    # ── 更新 ──────────────────────────────────────────────────

    def update_field(self,
        field_name: str | None = None,
        field_type: int | str | None = None,
        override_payload: dict[str, Any] | None = None,
        fields_list: list[dict[str, Any]] | None = None,
        field_id: str | None = None) -> dict[str, Any]:
        """更新多维表格列
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/update
        """
        field_id, field_old_name, field_old_type = self._resolve_field_info(field_name, fields_list, field_id)

        if not override_payload:
            field_type = self._resolve_field_type(field_type) if field_type is not None else field_old_type
            field_name = field_name if field_name is not None else field_old_name

            payload = {
                "field_name": field_name,
                "type": field_type,
            }
        else:
            payload = override_payload

        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/fields/{field_id}"
        return self.feishu_api.request("PUT", url, body=payload)["field"]

    # ── 删除 ──────────────────────────────────────────────────

    def delete_field(self,
                    field_name: str | None = None,
                    fields_list: list[dict[str, Any]] | None = None,
                    field_id: str | None = None) -> dict[str, Any]:
        """删除多维表格列
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-field/delete
        """
        field_id, _, _ = self._resolve_field_info(field_name, fields_list, field_id)

        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/fields/{field_id}"
        return self.feishu_api.request("DELETE", url)
