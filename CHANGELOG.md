# Changelog

## 0.0.5 (未发布)

### 文档

- Bitable 的 README、用户指南和示例脚本改为优先展示 `list_parsed_records`，只在需要飞书原始响应结构时使用 `list_records`
- 增强 agent 维护文档：新增文档索引、示例脚本规范、新增 API checklist、返回值修复 checklist，并强化 `local_test/` 敏感文件规则
- 更新 PyPI 元数据描述和 keywords，补充 `FeishuUser` / user token 能力

## 0.0.4 (2026)

### feishu_user

- 新增 `FeishuUser`，支持通过 device flow 获取 user access token，并可复用本地 token cache
- 默认 user scope 覆盖 Bitable / Doc / Spreadsheet / Driver 的常用读写路径，并避开常见需企业管理审核的粗粒度权限
- 支持 `api.bitable()`、`api.doc()`、`api.spreadsheet()`、`api.driver()` 以当前用户身份创建业务 client
- token cache 缺少本次请求 scope 时，会提示重新 device flow 更新授权

### feishu_spreadsheet

- 新增 `FeishuSpreadsheet`，支持 wiki / sheets 两种 URL 格式
- 支持工作表元数据、单元格读取、批量读取、写入、批量写入、追加、前插、查找和替换
- 支持 `sheet_id`、`sheet_name`、完整 range、相对 range + sheet 定位方式
- 新增 `get_rows`、`get_cell`、`get_records` 等轻量读取包装

### feishu_doc

- 新增 `get_markdown()`，直接读取文档 Markdown 内容
- 新增 `fetch_content()`，封装 docs_ai 高层读取接口，支持 markdown / xml / text
- Markdown 写入链路改为官方 convert + block create，补充相关权限和文档说明

### feishu_bitable

- 记录写入接口新增 `user_id_type` 参数，支持按 `open_id` / `union_id` / `user_id` 写入人员字段
- `get_record` 改为复用 `batch_get_records`，避免继续依赖飞书已不推荐的单条记录历史接口
- 补充 Bitable 相关函数的返回值示例和类型注解，覆盖 Record / Field / Table / View / Meta 常用接口
- `parse_record` 文档补充公式 / 查找引用字段的解析行为说明
- Table create/update/delete 返回值修正为当前官方响应结构，不再尝试读取不存在的 `table` 字段

### 文档与测试

- 重构 `local_test/`，按模块拆分真实接口测试；旧测试文件归档到 `old_test_file/`, `local_test/` 在 gitignore 中，所以对用户无感知
- 新增 `AGENTS.md`，并将文档拆分为 `docs/user_guide/`、`docs/agents_doc/`、`docs/design_doc/`
- README 缩减为项目入口和快速上手，详细模块用法迁移到 `docs/user_guide/`

## 0.0.3 (2026)

### FeishuAPI

- 修复 `iter_paginate` / `paginate` 的 `page_size` 传参位置，统一通过 query params 发送，避免分页请求错误地将 `page_size` 放入请求体

### feishu_bitable

- `parse_bitable_url` 返回值更新为 `(url_type, token, table_id, view_id)`，支持从 bitable URL 中直接解析 `view` 参数
- `Bitable` 新增 `default_view_id` 属性，自动保存 `bitable_url` 中解析出的默认视图 ID
- `list_records` 新增 `use_default_view_id` 参数（默认 `False`），在未显式传入 `view_name` / `view_id` 时可使用 `default_view_id` 作为查询视图
- `list_records` 改为仅支持关键字参数调用，避免多可选参数场景下的位置参数歧义
- `parse_record` 新增 `automatic_fields` 参数（默认 `False`）
  - **返回值结构变更**：`automatic_fields=False` 时返回 `(record_id, fields_dict)`，`automatic_fields=True` 时返回 `(record_id, fields_dict, meta_dict)`，不再将元数据注入 `fields_dict`
  - `meta_dict` 包含 `created_time` / `last_modified_time` / `created_by` / `last_modified_by`
  - 移除原有的字段名冲突检测逻辑（hacky loop）
- `list_parsed_records` 自动从 `kwargs` 提取 `automatic_fields` 并传递给 `parse_record`，返回类型注解同步更新
- README、示例脚本和本地测试 notebook 已同步更新上述用法

### 文档

- 为 `_request`、`_download_stream`、`iter_paginate`、`paginate` 补充 docstring

## 0.0.2 (2026)

### feishu_bitable

- `FIELD_TYPE_MAP` 拆分为中文 (`FIELD_TYPE_MAP_CN`) 和英文 (`FIELD_TYPE_MAP_EN`)，合并后仍可通过 `FIELD_TYPE_MAP` 使用
- 新增字段类型常量 `TEXT_TYPE`、`NUMBER_TYPE`、`FORMULA_TYPE`
- `parse_record` 支持自动解析公式 / 查找引用字段的嵌套返回值
- `parse_record` 支持提取记录元数据 (created_time / last_modified_time / created_by / last_modified_by)
- 添加官方字段编辑指南链接与类型说明注释

### 其他

- `pyproject.toml`: project.urls 改为 GitHub Repository 链接

## 0.0.1 (2026)

### feishu_bitable

- 多维表格 Bitable 入口类，支持 wiki / base 两种 URL 格式
- Table: list / create / batch_create / update / delete / batch_delete
- Record: list / get / batch_get / create / batch_create / update / batch_update / delete / batch_delete
- Field: list / create / update / delete
- View: list / get / create / update / delete
- 记录解析 (`list_parsed_records`): 自动展平文本类型
- 素材上传 (`upload_media`): 上传图片/文件到多维表格，自动推导 parent_type
- 分页迭代器 (`iter_paginate` / `paginate`)
- Token 过期自动刷新

### feishu_doc

- 文档 FeishuDoc 入口类，支持知识库 wiki 文档和个人空间 docx 文档
- 读取: get_doc_meta / get_raw_content / get_doc_blocks / get_children
- 写入: write_markdown (Markdown → 文档块自动转换) / append_markdown (追加写入) / convert_markdown (仅转换不写入) / create_block (手动构建块)
- 素材: upload_media (上传素材到文档) / insert_media_block (在文档中插入图片或文件块)
- 删除: clear_content (清空文档内容)
- 块类型映射 (`data_type.py`): 52 种块类型的中英文名称 → 类型值映射

### feishu_driver

- 云空间 FeishuDriver，统一处理文件和素材的上传 / 下载 / 删除
- 上传: ≤ 20MB 直接上传，> 20MB 自动分片上传 (预上传 → 分片 → 完成)
- 下载: download (保存到本地) / get_tmp_download_urls (批量获取 24h 临时链接)
- 元数据: get_root_folder_meta / list_files / get_file_meta
- 删除: delete_file (删除云空间文件/文件夹)
- Bitable 和 FeishuDoc 内部通过 FeishuDriver 完成素材操作

### feishu_api

- `request` 方法支持 `files` 参数，传入时自动切换为 multipart/form-data 请求
- `request_raw`: 返回原始二进制内容，用于文件下载
- `get_wiki_app_token`: 根据知识库 node_token 获取 obj_token (Bitable 和 Doc 内部使用)
