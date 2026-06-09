# Local Test Policy

`local_test/` 用于手动和半自动验证 feishukit 的真实飞书接口行为。

`local_test/` 为本地测试路径，如路径或者文件不存在可以自行创建

## 资源安全

- 只在 `local_test/config_test.py` 中标明“测试用，可以随意读写删”的文档、表格、文件夹上执行写入、删除、上传测试。
- 测试脚本开头检查一次资源用途即可，不要在每个读写操作前重复判断。
- 测试写入的字段、记录、视图、表、文档块、文件都应在 `finally` 中清理。
- 大文件上传和无法自动清理的素材上传可以保留脚本，但默认注释或跳过。

## 脚本组织

- 每个模块独立目录，例如 `feishu_bitable/`、`feishu_doc/`、`feishu_driver/`、`feishu_spreadsheet/`、`feishu_user/`。
- 默认生成 `.py` 脚本给 agent 自动测试。
- 如需 notebook，先让 `.py` 测试通过，询问用户是否需要`.ipynb`，如果需要则生成对应 `.ipynb` 供开发者手动调试。

## User Token 测试

- 默认使用 `local_test/token_cache.json`。
- no-confirm 脚本禁止触发 device flow；cache 缺权限时应明确报错或 SKIP。
- 需要用户确认的 device flow 单独放在 with-confirm 脚本中运行。
- 测试 device flow 时使用长 timeout，避免短 timeout 反复生成新 device code。

## IM 测试

- message 发送、回复、reaction 等写入测试只能在 用户明确标明用于测试的群组 中执行。
- group 更新测试只能在上述安全群中执行；group 删除/解散只能用于本次测试新建的群。
- 不自动测试踢出群成员；`im:chat.members:write_only` 同时覆盖拉人和踢人，使用前必须单独确认测试对象。
- 测试消息应在 `finally` 中撤回或清理；撤回失败时输出失败原因，但不要重试破坏性操作。

## 权限不足

真实飞书 app 可能没有开通某些权限。测试脚本可以把非核心路径标为 SKIP，
但输出要说明缺少哪个 scope。核心读写路径缺权限时应失败，提醒开发者更新 app 权限或 user token cache。
