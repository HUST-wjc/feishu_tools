# Changelog

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
