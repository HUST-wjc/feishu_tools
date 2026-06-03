from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...feishu_api import FeishuAPI


class GroupMixin:
    """群聊和成员管理"""

    feishu_api: FeishuAPI

    def list_groups(
        self,
        *,
        user_id_type: str = "open_id",
        sort_type: str = "ByActiveTimeDesc",
        group_types: str | list[str] | None = None,
        page_size: int = 100,
        size_limit: int = 0,
        timeout: int = 120,
    ) -> list[dict[str, Any]]:
        """列出当前 token 所在聊天。

        https://open.feishu.cn/document/server-docs/group/chat/list

        - sort_type: "ByCreateTimeAsc" 或 "ByActiveTimeDesc"。
          留空则默认为 "ByCreateTimeAsc", 选择 "ByActiveTimeDesc" 时, 可能会因为群聊更新过快, 导致部分群组因为分页机制无法被获取到。
        - group_types: 透传到请求参数 ``types``。该参数不在当前官方Markdown 文档中，来源为 lark-cli 的 chat list 实现和真实测试。
          当前已知取值为 "group" / "p2p"。p2p 仅适用于 user_access_token,
          bot 身份不能列单聊。thread/topic 不属于 group_types; 话题群仍属于 group, 可通过返回中的
          chat_mode 或 group_message_type 区分。
        - page_size: 分页大小, 官方最大值为 100。
        - size_limit: 限制返回总数, 0 表示不限制。
        """
        params: dict[str, Any] = {
            "user_id_type": user_id_type,
            "sort_type": sort_type,
        }
        if group_types:
            params["types"] = ",".join(group_types) if isinstance(group_types, list) else group_types
        return self.feishu_api.paginate(
            "GET",
            "/im/v1/chats",
            params=params,
            page_size=page_size,
            size_limit=size_limit,
            timeout=timeout,
        )

    def search_groups(
        self,
        query: str = "",
        *,
        chat_filter: dict[str, Any] | None = None,
        sorter: str | None = None,
        user_id_type: str | None = "open_id",
        page_size: int = 100,
        size_limit: int = 0,
        timeout: int = 120,
    ) -> list[dict[str, Any]]:
        """搜索当前 token 可见的群聊。

        https://open.feishu.cn/document/server-docs/group/chat/search

        官方 Markdown 文档目前为 v1 接口; lark-cli 已使用``POST /im/v2/chats/search``。
        这里采用 v2 接口, 参数来源为 lark-cli Go 实现和真实接口测试。

        - query: 搜索关键词, v2 接口支持按群名/成员名搜索。
        - chat_filter: 搜索过滤条件, 常用字段例如:

          ```
          {
              "search_types": [
                  "private",
                  "external",
                  "public_joined",
                  "public_not_joined",
              ],
              "member_ids": ["ou_xxx"],
              "is_manager": True,
              "disable_search_by_user": True,
          }
          ```

          search_types 用于筛选私有群、外部群、已加入公开群和未加入公开群;
          member_ids 用于按成员 open_id 筛选; is_manager 只返回当前身份创建或
          管理的群; disable_search_by_user 关闭按成员名优先搜索。
        - sorter: 排序字段, 例如 create_time_desc、update_time_desc、
          member_count_desc。
        - user_id_type: 控制返回 owner_id 等用户 ID 字段的类型; 已通过
          v2 search 真实接口探测。
        """

        body: dict[str, Any] = {}
        if query:
            body["query"] = query
        if chat_filter:
            body["filter"] = chat_filter
        if sorter:
            body["sorter"] = sorter

        items = self.feishu_api.paginate(
            "POST",
            "/im/v2/chats/search",
            params={"user_id_type": user_id_type} if user_id_type else None,
            body=body,
            page_size=page_size,
            size_limit=size_limit,
            timeout=timeout,
        )
        return [item["meta_data"] for item in items if item.get("meta_data")]

    def get_group(
        self,
        chat_id: str,
        *,
        user_id_type: str = "open_id",
        timeout: int = 120,
    ) -> dict[str, Any]:
        """获取群信息。

        https://open.feishu.cn/document/server-docs/group/chat/get-2
        """
        return self.feishu_api.request(
            "GET",
            f"/im/v1/chats/{chat_id}",
            params={"user_id_type": user_id_type},
            timeout=timeout,
        )

    # ── 创建 / 更新 / 删除 ─────────────────────────────────────

    def create_group(
        self,
        name: str = "",
        description: str | None = None,
        chat_type: str = "private",
        chat_mode: str = "group",
        group_message_type: str | None = None,
        *,
        user_ids: list[str] | None = None,
        bot_ids: list[str] | None = None,
        owner_id: str | None = None,
        user_id_type: str = "open_id",
        set_bot_manager: bool = False,
        idempotency_key: str | None = None,
        extra_body: dict[str, Any] | None = None,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """创建群聊或话题群, 返回官方群信息 data。

        https://open.feishu.cn/document/server-docs/group/chat/create

        常用字段用命名参数; 不常用的原生请求体字段放入
        ``extra_body``, 会覆盖同名命名参数生成的字段。
        """
        body = {
            key: value
            for key, value in {
                "name": name,
                "description": description,
                "user_id_list": user_ids,
                "bot_id_list": bot_ids,
                "owner_id": owner_id,
                "chat_type": chat_type,
                "chat_mode": chat_mode,
                "group_message_type": group_message_type,
            }.items()
            if value is not None and value != ""
        }
        if extra_body:
            body.update(extra_body)

        params: dict[str, Any] = {"user_id_type": user_id_type}
        if set_bot_manager:
            params["set_bot_manager"] = True
        if idempotency_key:
            params["uuid"] = idempotency_key

        return self.feishu_api.request(
            "POST",
            "/im/v1/chats",
            params=params,
            body=body,
            timeout=timeout,
        )

    def update_group(
        self,
        chat_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
        owner_id: str | None = None,
        chat_type: str | None = None,
        group_message_type: str | None = None,
        user_id_type: str = "open_id",
        extra_body: dict[str, Any] | None = None,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """更新群信息。

        https://open.feishu.cn/document/server-docs/group/chat/update

        未传的字段不会更新。更少用的官方字段, 例如权限配置或国际化
        名称, 可通过 ``extra_body`` 透传。
        """
        body = {
            key: value
            for key, value in {
                "name": name,
                "description": description,
                "owner_id": owner_id,
                "chat_type": chat_type,
                "group_message_type": group_message_type,
            }.items()
            if value is not None and value != ""
        }
        if extra_body:
            body.update(extra_body)
        if not body:
            raise ValueError("至少需要传入一个待更新字段")

        return self.feishu_api.request(
            "PUT",
            f"/im/v1/chats/{chat_id}",
            params={"user_id_type": user_id_type},
            body=body,
            timeout=timeout,
        )

    def delete_group(self, chat_id: str, *, timeout: int = 120) -> dict[str, Any]:
        """解散群。

        https://open.feishu.cn/document/server-docs/group/chat/delete

        会解散指定群, 返回官方 data。
        """
        return self.feishu_api.request(
            "DELETE",
            f"/im/v1/chats/{chat_id}",
            timeout=timeout,
        )

    # ── 成员 ──────────────────────────────────────────────────

    def list_group_members(
        self,
        chat_id: str,
        *,
        member_id_type: str = "open_id",
        page_size: int = 100,
        size_limit: int = 0,
        timeout: int = 120,
    ) -> list[dict[str, Any]]:
        """获取群成员列表。

        https://open.feishu.cn/document/server-docs/group/chat-member/get
        """
        return self.feishu_api.paginate(
            "GET",
            f"/im/v1/chats/{chat_id}/members",
            params={"member_id_type": member_id_type},
            page_size=page_size,
            size_limit=size_limit,
            timeout=timeout,
        )

    def add_group_members(
        self,
        chat_id: str,
        member_ids: list[str],
        *,
        member_id_type: str = "open_id",
        succeed_type: int | None = None,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """将用户或机器人拉入群聊。

        https://open.feishu.cn/document/server-docs/group/chat-member/create

        ``member_id_type="app_id"`` 时用于拉机器人, member_ids 应传 app_id。
        """
        params: dict[str, Any] = {"member_id_type": member_id_type}
        if succeed_type is not None:
            params["succeed_type"] = succeed_type
        return self.feishu_api.request(
            "POST",
            f"/im/v1/chats/{chat_id}/members",
            params=params,
            body={"id_list": member_ids},
            timeout=timeout,
        )

    def remove_group_members(
        self,
        chat_id: str,
        member_ids: list[str],
        *,
        member_id_type: str = "open_id",
        timeout: int = 120,
    ) -> dict[str, Any]:
        """将用户或机器人移出群聊。

        https://open.feishu.cn/document/server-docs/group/chat-member/delete
        """
        return self.feishu_api.request(
            "DELETE",
            f"/im/v1/chats/{chat_id}/members",
            params={"member_id_type": member_id_type},
            body={"id_list": member_ids},
            timeout=timeout,
        )

    def is_in_group(self, chat_id: str, *, timeout: int = 120) -> bool:
        """判断当前 token 对应的用户或机器人是否在群里。

        https://open.feishu.cn/document/server-docs/group/chat-member/is_in_chat
        """
        data = self.feishu_api.request(
            "GET",
            f"/im/v1/chats/{chat_id}/members/is_in_chat",
            timeout=timeout,
        )
        return bool(data.get("is_in_chat"))
