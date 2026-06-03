from __future__ import annotations

from ..feishu_api import FeishuAPI
from .components import GroupMixin, MessageMixin


class FeishuIM(GroupMixin, MessageMixin):
    """飞书即时通讯 IM

    https://open.feishu.cn/document/server-docs/group/overview
    https://open.feishu.cn/document/server-docs/im-v1/introduction

    当前按能力拆为两部分:
    - GroupMixin: 群聊查询、创建更新删除和成员管理
    - MessageMixin: 消息读取、发送、回复、撤回和 reaction
    """

    def __init__(
        self,
        app_id: str = "",
        app_secret: str = "",
        feishu_api: FeishuAPI | None = None,
    ) -> None:
        self.feishu_api = feishu_api or FeishuAPI(app_id, app_secret)

    def __repr__(self) -> str:
        app_id, app_secret_encrypted = self.feishu_api._masked_credentials()
        return f"FeishuIM(app_id={app_id}, app_secret={app_secret_encrypted})"
