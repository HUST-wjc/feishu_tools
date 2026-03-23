# Changelog

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
