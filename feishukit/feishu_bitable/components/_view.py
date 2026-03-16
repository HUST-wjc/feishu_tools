from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...feishu_api import FeishuAPI


class ViewMixin:
    """视图 CRUD"""

    feishu_api: FeishuAPI
    app_token: str
    table_id: str

    # ── 查询 ──────────────────────────────────────────────────

    def list_views(self) -> list[dict[str, Any]]:
        """获取多维表格视图
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-view/list
        """
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/views"
        return self.feishu_api.paginate("GET", url)

    def _resolve_view_id(self, view_name: str | None = None, view_list: list[dict[str, Any]] | None = None, view_id: str | None = None) -> str:
        if view_id:
            return view_id
        if not view_name:
            raise ValueError("view_name 和 view_id 不能同时为空")
        view_list = view_list or self.list_views()
        for v in view_list:
            if v["view_name"] == view_name:
                return v["view_id"]
        raise ValueError(f"视图不存在, view_name: {view_name}, view_id: {view_id}\n 可选视图列表: {view_list}")

    def get_view_info(self, view_name: str | None = None, view_list: list[dict[str, Any]] | None = None, view_id: str | None = None) -> dict[str, Any]:
        """获取多维表格视图信息
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-view/get
        """
        view_id = self._resolve_view_id(view_name, view_list, view_id)
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/views/{view_id}"
        return self.feishu_api.request("GET", url)["view"]

    # ── 创建 ──────────────────────────────────────────────────

    def create_view(self, view_name: str, view_type: str | None = None) -> dict[str, Any]:
        """创建多维表格视图
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-view/create

        view_name: 必填, 视图名称。名称不能包含特殊字符，请确保其符合以下规则：
            长度不超过 100 个字符
            不为空且不包含这些特殊符号：[ ]
            示例值："表格视图 1"

        view_type: 选填，视图类型，不填默认为表格视图。
            示例值："grid"

            可选值有：
            grid: 表格视图
            kanban: 看板视图
            gallery: 画册视图
            gantt: 甘特视图
            form: 表单视图
        """
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/views"
        body = {"view_name": view_name}
        if view_type:
            body["view_type"] = view_type
        return self.feishu_api.request("POST", url, body=body)["view"]

    # ── 更新 ──────────────────────────────────────────────────

    def update_view(self,
        view_name: str | None = None,
        view_list: list[dict[str, Any]] | None = None,
        view_id: str | None = None,
        view_new_name: str | None = None,
        view_property: dict[str, Any] | None = None) -> dict[str, Any]:
        """更新多维表格视图
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-view/patch

        view_new_name 和 property 示例, field_id 需要通过 list_fields 获取:
        ```
        '{
            "property": {
                "filter_info": {
                    "conditions": [
                        {
                            "field_id": "fldpTw2262",
                            "operator": "isGreater",
                            "value": "[\"ExactDate\",\"1642672432000\"]"
                        }
                    ],
                    "conjunction": "and"
                },
                "hidden_fields": null
            },
            "view_name": "grid"
        }'
        ```
        """
        view_id = self._resolve_view_id(view_name, view_list, view_id)
        payload = {}
        if view_new_name:
            payload["view_name"] = view_new_name
        if view_property:
            payload["property"] = view_property
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/views/{view_id}"
        return self.feishu_api.request("PATCH", url, body=payload)["view"]

    # ── 删除 ──────────────────────────────────────────────────

    def delete_view(self, 
        view_name: str | None = None, 
        view_list: list[dict[str, Any]] | None = None, 
        view_id: str | None = None) -> None:
        """删除多维表格视图
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table-view/delete

        删除成功无返回值
        """
        view_id = self._resolve_view_id(view_name, view_list, view_id)
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/views/{view_id}"
        self.feishu_api.request("DELETE", url)
