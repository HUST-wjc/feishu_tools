from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...feishu_api import FeishuAPI


_ALLOWED_RECEIVE_ID_TYPES = {"open_id", "union_id", "user_id", "email", "chat_id"}
DEFAULT_CARD_MSG_CONTENT_TYPE = "raw_card_content"


def _resolve_receive_id(
    *,
    receive_id: str | None = None,
    receive_id_type: str | None = None,
    chat_id: str | None = None,
    open_id: str | None = None,
    user_id: str | None = None,
    union_id: str | None = None,
    email: str | None = None,
) -> tuple[str, str]:
    """把 SDK 便捷目标参数统一成飞书原生 receive_id_type/receive_id。"""
    native_pair = bool(receive_id) or bool(receive_id_type)
    shortcut_values = {
        "chat_id": chat_id,
        "open_id": open_id,
        "user_id": user_id,
        "union_id": union_id,
        "email": email,
    }
    provided_shortcuts = [(key, value) for key, value in shortcut_values.items() if value]

    if native_pair:
        if not receive_id or not receive_id_type:
            raise ValueError("receive_id 和 receive_id_type 必须同时传入")
        if provided_shortcuts:
            raise ValueError("receive_id/receive_id_type 不能和 chat_id/open_id/user_id/union_id/email 混用")
        if receive_id_type not in _ALLOWED_RECEIVE_ID_TYPES:
            raise ValueError(f"receive_id_type 仅支持 {sorted(_ALLOWED_RECEIVE_ID_TYPES)}")
        return receive_id_type, receive_id

    if len(provided_shortcuts) != 1:
        raise ValueError("chat_id/open_id/user_id/union_id/email 必须且只能传入一个")
    return provided_shortcuts[0]


def _normalize_content(content: dict[str, Any] | str) -> str:
    """飞书发送/回复消息接口要求 content 是 JSON 字符串。"""
    if isinstance(content, str):
        return content
    return json.dumps(content, ensure_ascii=False)


def _add_content_text(message: dict[str, Any]) -> dict[str, Any]:
    """从常见文本类 content 中提取 content_text, 原始 message 字段不变。"""
    body = message.get("body")
    if not isinstance(body, dict):
        return message
    raw_content = body.get("content")
    if not isinstance(raw_content, str) or not raw_content:
        return message

    try:
        content = json.loads(raw_content)
    except json.JSONDecodeError:
        content_text = raw_content
    else:
        content_text = ""
        if isinstance(content, dict):
            for key in ("text", "title", "template"):
                value = content.get(key)
                if isinstance(value, str) and value:
                    content_text = value
                    break
            if not content_text:
                content_text = _extract_post_text(content)

    if not content_text:
        return message
    message = dict(message)
    message["content_text"] = content_text
    return message


def _extract_post_text(content: dict[str, Any]) -> str:
    """从飞书 post/rich-text content 的段落结构中提取纯文本片段。"""
    segments: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            text = value.get("text")
            if isinstance(text, str) and text:
                segments.append(text)
                return
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(content.get("content"))
    if not segments:
        for key in ("zh_cn", "en_us", "ja_jp"):
            localized = content.get(key)
            if isinstance(localized, dict):
                walk(localized.get("content"))
                if segments:
                    break
    return "".join(segments)


class MessageMixin:
    """消息读写"""

    feishu_api: FeishuAPI

    # ── 读取 ──────────────────────────────────────────────────

    def list_messages(
        self,
        container_id: str,
        *,
        container_id_type: str = "chat",
        start_time: str | None = None,
        end_time: str | None = None,
        sort: str = "desc",
        card_msg_content_type: str | None = DEFAULT_CARD_MSG_CONTENT_TYPE,
        only_thread_root_messages: bool | None = True,
        page_size: int = 50,
        size_limit: int = 0,
        timeout: int = 120,
    ) -> list[dict[str, Any]]:
        """获取会话或话题历史消息。

        https://open.feishu.cn/document/server-docs/im-v1/message/list

        ``container_id_type`` 可选 ``chat`` 或 ``thread``。普通群/单聊传
        chat_id；话题回复列表传 thread_id 且 ``container_id_type="thread"``。
        ``start_time`` / ``end_time`` 使用飞书原生秒级时间戳字符串。
        ``only_thread_root_messages`` 仅用于 chat 容器, 默认为 True, 避免
        普通消息流混入话题回复。传 None 可不透传该参数。
        返回值保留原始字段，并额外增加 ``content_text`` 方便阅读文本类消息。
        """
        if sort not in {"asc", "desc"}:
            raise ValueError("sort 仅支持 asc / desc")
        if container_id_type not in {"chat", "thread"}:
            raise ValueError("container_id_type 仅支持 chat / thread")
        if container_id_type == "thread" and (start_time or end_time):
            raise ValueError("thread 容器暂不支持 start_time / end_time")

        sort_type = "ByCreateTimeAsc" if sort == "asc" else "ByCreateTimeDesc"
        params: dict[str, Any] = {
            "container_id_type": container_id_type,
            "container_id": container_id,
            "sort_type": sort_type,
        }
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if card_msg_content_type is not None:
            params["card_msg_content_type"] = card_msg_content_type
        if container_id_type == "chat" and only_thread_root_messages is not None:
            params["only_thread_root_messages"] = "true" if only_thread_root_messages else "false"

        messages = self.feishu_api.paginate(
            "GET",
            "/im/v1/messages",
            params=params,
            page_size=page_size,
            size_limit=size_limit,
            timeout=timeout,
        )
        return [_add_content_text(message) for message in messages]

    def list_thread_messages(
        self,
        thread_id: str,
        *,
        sort: str = "asc",
        card_msg_content_type: str | None = DEFAULT_CARD_MSG_CONTENT_TYPE,
        page_size: int = 50,
        size_limit: int = 0,
        timeout: int = 120,
    ) -> list[dict[str, Any]]:
        """获取话题下的回复消息, 默认按创建时间升序。"""
        return self.list_messages(
            thread_id,
            container_id_type="thread",
            sort=sort,
            card_msg_content_type=card_msg_content_type,
            only_thread_root_messages=None,
            page_size=page_size,
            size_limit=size_limit,
            timeout=timeout,
        )

    def get_message(
        self,
        message_id: str,
        *,
        user_id_type: str = "open_id",
        card_msg_content_type: str | None = DEFAULT_CARD_MSG_CONTENT_TYPE,
        timeout: int = 120,
    ) -> list[dict[str, Any]]:
        """获取单条消息内容。

        https://open.feishu.cn/document/server-docs/im-v1/message/get

        官方返回 ``items`` 列表；合并转发消息会包含根消息和子消息。
        """
        params: dict[str, Any] = {"user_id_type": user_id_type}
        if card_msg_content_type is not None:
            params["card_msg_content_type"] = card_msg_content_type
        data = self.feishu_api.request(
            "GET",
            f"/im/v1/messages/{message_id}",
            params=params,
            timeout=timeout,
        )
        return [_add_content_text(message) for message in data.get("items") or []]

    def get_messages(
        self,
        message_ids: str | list[str],
        *,
        card_msg_content_type: str | None = DEFAULT_CARD_MSG_CONTENT_TYPE,
        timeout: int = 120,
    ) -> list[dict[str, Any]]:
        """批量获取消息详情。

        当前官方 Markdown 文档只公开单条 ``GET /im/v1/messages/:message_id``；
        这里使用 lark-cli Go 实现中的批量 ``GET /im/v1/messages/mget``，
        并已通过真实接口测试。参数来源为 lark-cli Go 代码和真实测试，
        而不是当前官方 Markdown 文档。

        ``message_ids`` 可传单个 message_id 字符串或 message_id 列表。
        单次最多 50 条。
        """
        if isinstance(message_ids, str):
            message_ids = [message_ids]
        if not message_ids:
            raise ValueError("message_ids 不能为空")
        if len(message_ids) > 50:
            raise ValueError("get_messages 单次最多支持 50 个 message_id")

        params: dict[str, Any] = {"message_ids": message_ids}
        if card_msg_content_type is not None:
            params["card_msg_content_type"] = card_msg_content_type

        data = self.feishu_api.request(
            "GET",
            "/im/v1/messages/mget",
            params=params,
            timeout=timeout,
        )
        return [_add_content_text(message) for message in data.get("items") or []]

    # ── 写入 ──────────────────────────────────────────────────

    def send_message(
        self,
        msg_type: str,
        content: dict[str, Any] | str,
        *,
        receive_id: str | None = None,
        receive_id_type: str | None = None,
        chat_id: str | None = None,
        open_id: str | None = None,
        user_id: str | None = None,
        union_id: str | None = None,
        email: str | None = None,
        idempotency_key: str | None = None,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """发送消息。

        https://open.feishu.cn/document/server-docs/im-v1/message/create

        常用场景可直接传 ``chat_id`` / ``open_id`` / ``user_id`` /
        ``union_id`` / ``email`` 之一。更原生的调用可传
        ``receive_id`` + ``receive_id_type``。
        ``content`` 可以直接传飞书原生 JSON 字符串，也可以传 dict，
        SDK 会自动序列化。
        user 身份发送消息通常需要 ``im:message.send_as_user`` 和
        ``im:message``; bot 身份需要 ``im:message:send_as_bot``。
        返回飞书官方 data，包含 message_id、chat_id、create_time。
        """
        resolved_type, resolved_id = _resolve_receive_id(
            receive_id=receive_id,
            receive_id_type=receive_id_type,
            chat_id=chat_id,
            open_id=open_id,
            user_id=user_id,
            union_id=union_id,
            email=email,
        )
        body = {
            "receive_id": resolved_id,
            "msg_type": msg_type,
            "content": _normalize_content(content),
        }
        if idempotency_key:
            body["uuid"] = idempotency_key

        return self.feishu_api.request(
            "POST",
            "/im/v1/messages",
            params={"receive_id_type": resolved_type},
            body=body,
            timeout=timeout,
        )

    def send_text(
        self,
        text: str,
        *,
        receive_id: str | None = None,
        receive_id_type: str | None = None,
        chat_id: str | None = None,
        open_id: str | None = None,
        user_id: str | None = None,
        union_id: str | None = None,
        email: str | None = None,
        idempotency_key: str | None = None,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """发送文本消息。"""
        return self.send_message(
            "text",
            {"text": text},
            receive_id=receive_id,
            receive_id_type=receive_id_type,
            chat_id=chat_id,
            open_id=open_id,
            user_id=user_id,
            union_id=union_id,
            email=email,
            idempotency_key=idempotency_key,
            timeout=timeout,
        )

    def reply_message(
        self,
        message_id: str,
        msg_type: str,
        content: dict[str, Any] | str,
        *,
        reply_in_thread: bool = False,
        idempotency_key: str | None = None,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """回复消息。

        https://open.feishu.cn/document/server-docs/im-v1/message/reply

        ``content`` 可以直接传飞书原生 JSON 字符串，也可以传 dict。
        user 身份回复消息通常需要 ``im:message.send_as_user`` 和
        ``im:message``; bot 身份需要 ``im:message:send_as_bot``。
        """
        body: dict[str, Any] = {
            "msg_type": msg_type,
            "content": _normalize_content(content),
        }
        if reply_in_thread:
            body["reply_in_thread"] = True
        if idempotency_key:
            body["uuid"] = idempotency_key

        return self.feishu_api.request(
            "POST",
            f"/im/v1/messages/{message_id}/reply",
            body=body,
            timeout=timeout,
        )

    def reply_text(
        self,
        message_id: str,
        text: str,
        *,
        reply_in_thread: bool = False,
        idempotency_key: str | None = None,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """回复文本消息。"""
        return self.reply_message(
            message_id,
            "text",
            {"text": text},
            reply_in_thread=reply_in_thread,
            idempotency_key=idempotency_key,
            timeout=timeout,
        )

    def revoke_message(
        self,
        message_id: str,
        *,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """撤回消息。

        https://open.feishu.cn/document/server-docs/im-v1/message/delete

        user / bot 身份都需要 ``im:message:recall``。bot 身份通常只能撤回
        自己发送的消息; 撤回他人群消息还要求 bot 是群主、管理员或建群机器人。
        """
        return self.feishu_api.request(
            "DELETE",
            f"/im/v1/messages/{message_id}",
            timeout=timeout,
        )

    # ── 表情回复 ────────────────────────────────────────────────

    def add_reaction(
        self,
        message_id: str,
        emoji_type: str,
        *,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """添加消息表情回复。

        https://open.feishu.cn/document/server-docs/im-v1/message-reaction/create
        """
        return self.feishu_api.request(
            "POST",
            f"/im/v1/messages/{message_id}/reactions",
            body={"reaction_type": {"emoji_type": emoji_type}},
            timeout=timeout,
        )

    def delete_reaction(
        self,
        message_id: str,
        reaction_id: str,
        *,
        timeout: int = 120,
    ) -> dict[str, Any]:
        """删除消息表情回复。

        https://open.feishu.cn/document/server-docs/im-v1/message-reaction/delete
        """
        return self.feishu_api.request(
            "DELETE",
            f"/im/v1/messages/{message_id}/reactions/{reaction_id}",
            timeout=timeout,
        )

    def list_reactions(
        self,
        message_id: str,
        *,
        reaction_type: str | None = None,
        user_id_type: str = "open_id",
        page_size: int = 50,
        size_limit: int = 0,
        timeout: int = 120,
    ) -> list[dict[str, Any]]:
        """获取消息表情回复列表。

        https://open.feishu.cn/document/server-docs/im-v1/message-reaction/list
        """
        params: dict[str, Any] = {"user_id_type": user_id_type}
        if reaction_type:
            params["reaction_type"] = reaction_type
        return self.feishu_api.paginate(
            "GET",
            f"/im/v1/messages/{message_id}/reactions",
            params=params,
            page_size=page_size,
            size_limit=size_limit,
            timeout=timeout,
        )
