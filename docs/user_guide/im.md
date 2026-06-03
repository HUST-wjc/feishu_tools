# IM 用户指南

`FeishuIM` 封装飞书即时通讯中常用的 group 和 message 能力。

当前模块按能力分为两部分：

- Group：聊天发现、群信息、群创建更新删除、群成员管理。
- Message：消息列表、消息详情、发送、回复、撤回、表情回复。

飞书 OpenAPI 把普通群、话题群和单聊都放在 chat/group 体系里。SDK 仍按业务语义使用 `group` 命名，但 `list_groups(group_types="p2p")` 返回的是单聊。

## 初始化

应用身份：

```python
from feishukit import FeishuIM

im = FeishuIM(app_id="cli_xxxx", app_secret="xxxx")
```

用户身份：

```python
from feishukit import FeishuUser

api = FeishuUser(
    app_id="cli_xxxx",
    app_secret="xxxx",
    token_cache_path="./token_cache.json",
)
im = api.im()
```

IM 的 user/bot 身份差异很明显。bot 身份取决于机器人是否在群内、应用可用范围和应用身份权限；user 身份取决于当前授权用户是否能访问目标聊天，以及用户身份 scope 是否已授权。

## Group 读取

```python
# 列出当前 token 所在聊天。group_types 透传为飞书请求参数 types。
groups = im.list_groups(size_limit=20)
groups = im.list_groups(group_types="group", size_limit=20)
groups = im.list_groups(group_types=["group", "p2p"], size_limit=20)

# 搜索可见群聊。search_groups 使用 POST /im/v2/chats/search。
groups = im.search_groups("项目群", size_limit=10)

groups = im.search_groups(
    "项目群",
    chat_filter={
        "search_types": ["private", "external", "public_joined"],
        "member_ids": ["ou_xxx"],
        "is_manager": True,
        "disable_search_by_user": True,
    },
    sorter="create_time_desc",
    size_limit=10,
)

group = im.get_group("oc_xxx")
members = im.list_group_members("oc_xxx", size_limit=100)
is_member = im.is_in_group("oc_xxx")
```

`group_types` 当前已通过 lark-cli Go 实现和真实接口测试确认支持 `group` / `p2p`。`p2p` 仅适合 user access token；bot 身份无法列单聊。话题群不属于 `group_types` 的取值，它会包含在 `group` 中，通常可通过返回里的 `chat_mode` 或 `group_message_type` 区分。

`search_groups()` 返回的是 v2 search 响应中每个 item 的 `meta_data`。v2 search 的 `chat_mode` 枚举和 `list_groups()` 不完全相同：普通群常见为 `DEFAULT`，话题群常见为 `THREAD`。

## Group 写操作

```python
created = im.create_group(
    name="测试群",
    user_ids=["ou_xxx"],
    chat_type="private",
)
chat_id = created["chat_id"]

im.update_group(chat_id, description="新的群描述")
im.add_group_members(chat_id, ["ou_yyy"])
im.remove_group_members(chat_id, ["ou_yyy"])
im.delete_group(chat_id)
```

不常用的官方字段通过 `extra_body` 透传：

```python
im.update_group(
    "oc_xxx",
    extra_body={
        "membership_approval": "approval_required",
        "join_message_visibility": "only_owner",
    },
)
```

写操作测试限制：

- 用户身份修改群组时，只能在 `chat_test_1`、`chat_test_2`、`chat_topic_test_1` 中测试。
- 删除/解散群只能用于测试过程中自己新建的群。
- 真实拉人、踢人、解散群都应单独确认测试目标，不要在生产群上跑自动化写测试。

## Message 读取

```python
# 获取会话消息，container_id 默认为 chat_id。
messages = im.list_messages("oc_xxx", size_limit=20)

# 普通 chat 历史默认只返回 thread root messages，避免主消息流混入话题回复。
messages = im.list_messages(
    "oc_xxx",
    only_thread_root_messages=True,
    size_limit=20,
)

# 获取话题回复消息，默认按创建时间升序。
thread_messages = im.list_thread_messages("omt_xxx", size_limit=20)

# 单条消息。官方返回 items list，合并转发消息会包含子消息。
items = im.get_message("om_xxx")

# 批量获取消息，单次最多 50 条。
items = im.get_messages(["om_xxx", "om_yyy"])
```

读取接口默认传 `card_msg_content_type="raw_card_content"`，让卡片消息返回结构更稳定。如需使用飞书官方默认行为，可显式传 `card_msg_content_type=None`。

消息返回保留飞书原始 message dict。SDK 会额外尝试增加 `content_text` 字段，方便快速查看文本、post/rich-text 标题或正文片段；原始 `body.content` 不会被替换。

## Message 发送与回复

```python
sent = im.send_text("hello", chat_id="oc_xxx")
message_id = sent["message_id"]

im.reply_text(message_id, "收到")
im.reply_text(message_id, "进入话题回复流", reply_in_thread=True)
```

更原生的消息发送：

```python
im.send_message(
    "interactive",
    {"elements": [{"tag": "markdown", "content": "hello"}]},
    chat_id="oc_xxx",
)

im.send_message(
    "text",
    {"text": "hello"},
    receive_id="ou_xxx",
    receive_id_type="open_id",
)
```

`send_message()` 的收件人可以传 `chat_id`、`open_id`、`user_id`、`union_id`、`email` 之一，也可以传原生 `receive_id + receive_id_type`。`content` 传 dict 时会自动序列化为飞书要求的 JSON 字符串。

用户身份发送或回复消息通常需要 `im:message.send_as_user` 和 `im:message`；bot 身份发送或回复消息通常需要 `im:message:send_as_bot`。这些写入是否成功还取决于调用方是否在目标聊天中、应用可用范围和目标用户/群的可见性。

## Reaction

```python
reaction = im.add_reaction("om_xxx", "SMILE")
reactions = im.list_reactions("om_xxx")
im.delete_reaction("om_xxx", reaction["reaction_id"])
```

删除 reaction 只能删除当前 token 自己添加的表情回复。

## 权限提示

`FeishuUser(scopes=None)` 默认覆盖 IM 常用读写路径的一部分，包括 group 读取、群信息更新、消息读取、消息基础权限和 reaction 读写。以下高风险或常见需审核权限不默认申请，调用方需要按需显式传入：

- 以用户身份发消息：`im:message.send_as_user`
- 以用户身份创建群：`im:chat:create_by_user`
- 撤回消息：`im:message:recall`
- 添加或移除群成员：`im:chat.members:write_only`
- 解散群：不在默认 scope 策略内；只应对本次测试新建的群执行

IM 接口对身份、权限和成员关系非常敏感。建议先用读取接口确认目标群和消息，再执行写操作。
