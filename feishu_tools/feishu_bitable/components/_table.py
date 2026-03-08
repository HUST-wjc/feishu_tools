from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...feishu_api import FeishuAPI


class TableMixin:
    """数据表 CRUD"""

    feishu_api: FeishuAPI
    app_token: str
    table_id: str

    # ── 查询 ──────────────────────────────────────────────────

    def list_tables(self) -> list[dict[str, Any]]:
        """获取多维表格列表
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table/list
        """
        url = f"/bitable/v1/apps/{self.app_token}/tables"
        return self.feishu_api.paginate("GET", url)

    def get_table_size(self) -> int:
        """获取多维表格记录数，只获取一条数据，快速返回，但是受限于飞书本身的接口限制，有时候还是会很慢很慢，可能是 1秒 也可能是 1分钟"""
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}/records/search"
        response = self.feishu_api.request("POST", url, body={'page_size': 1})
        return response['total']

    # ── 创建 ──────────────────────────────────────────────────

    def create_table(self, table_name: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """创建一个数据表 (非多维表格)
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table/create

        请求体示例

        ```
         '{
            "table": {
                "default_view_name": "默认的表格视图",
                "fields": [
                    {
                        "field_name": "索引字段",
                        "type": 1
                    },
                    {
                        "field_name": "单选",
                        "property": {
                            "options": [
                                {
                                    "color": 0,
                                    "name": "Enabled"
                                },
                                {
                                    "color": 1,
                                    "name": "Disabled"
                                },
                                {
                                    "color": 2,
                                    "name": "Draft"
                                }
                            ]
                        },
                        "type": 3,
                        "ui_type": "SingleSelect"
                    }
                ],
                "name": "数据表名称"
            }
        }'
        ```

        表格名为必填
        """
        url = f"/bitable/v1/apps/{self.app_token}/tables"

        if not payload:
            payload = {"table": {"name": table_name}}
        else:
            # 如果用户传入了 payload, 但是没有指定表格名称，则使用 table_name 填充
            if table_name and not payload.setdefault("table", {}).get("name"):
                payload["table"]["name"] = table_name

        return self.feishu_api.request("POST", url, body=payload)["table"]

    def batch_create_tables(self, table_names: list[str]) -> dict[str, Any]:
        """批量创建多维表格
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table/batch_create

        仅可指定数据表名称, 每个多维表格中，数据表与仪表盘的总数量上限为 100。
        
        请求体示例
        ```
        '{
            "tables": [
                {
                    "name": "一个新的数据表"
                }
            ]
        }'
        """
        url = f"/bitable/v1/apps/{self.app_token}/tables/batch_create"
        body = {"tables": [{"name": name} for name in table_names]}
        return self.feishu_api.request("POST", url, body=body)

    # ── 更新 ──────────────────────────────────────────────────

    def update_table(self, table_new_name: str | None = None) -> dict[str, Any]:
        """更新数据表的名称。
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table/patch

        如果名称为空或和旧名称相同，接口仍然会返回成功，但是名称不会被更改。
        """
        url = f"/bitable/v1/apps/{self.app_token}/tables/{self.table_id}"
        body = {"name": table_new_name}
        return self.feishu_api.request("PATCH", url, body=body)["table"]

    # ── 删除 ──────────────────────────────────────────────────

    def delete_table(self, table_name: str) -> None:
        """删除多维表格中的一张数据表
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table/delete

        删除成功无返回值
        此处我们使用 batch_delete_tables 来替代官方的 api 入口
        """
        self.batch_delete_tables(table_names=[table_name])

    def batch_delete_tables(self, 
        table_names: list[str] | None = None, 
        table_ids: list[str] | None = None, 
        table_list: list[dict[str, Any]] | None = None) -> None:
        """批量删除多维表格中的数据表
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app-table/batch_delete

        如果多维表格中只剩最后一张数据表，则不允许被删除
        删除成功无返回值
        """
        table_list = table_list or self.list_tables()
        if not table_names and not table_ids:
            raise ValueError("table_names 和 table_ids 不能同时为空")

        if not table_ids and table_names:
            table_ids = []
            remaining = set(table_names)

            for table in table_list:
                if table["name"] in remaining:
                    table_ids.append(table["table_id"])
                    remaining.discard(table["name"])
            if remaining:
                raise ValueError(f"删除表格时 {remaining} 未找到, 当前 table_list 为: {table_list}")

        url = f"/bitable/v1/apps/{self.app_token}/tables/batch_delete"
        body = {"table_ids": table_ids}
        self.feishu_api.request("POST", url, body=body)

