# Doc 用户指南

`FeishuDoc` 封装飞书新版文档 Docx 的读取、Markdown 写入、块操作和素材插入。

## 初始化

```python
from feishukit import FeishuDoc

doc = FeishuDoc(
    app_id="cli_xxxx",
    app_secret="xxxx",
    doc_url="https://xxx.feishu.cn/wiki/xxxxx",
)
```

`doc_url` 支持两种格式：

- 知识库文档：`https://xxx.feishu.cn/wiki/{node_token}`
- 个人空间文档：`https://xxx.feishu.cn/docx/{document_id}`

Markdown / docs_ai 高层读取接口可直接使用 URL 中的 wiki token；docx block、写入和素材接口会在内部解析成实际 docx document_id。

## 读取

```python
meta = doc.get_doc_meta()
markdown = doc.get_markdown()
data = doc.fetch_content("xml")
text = doc.get_raw_content()
blocks = doc.get_doc_blocks()
children = doc.get_children()
children = doc.get_children(block_id)
```

`get_markdown()` 适合直接读取整篇 Markdown。

`fetch_content()` 是 docs_ai 高层读取接口的薄封装，支持 `markdown` / `xml` / `text`，也支持直接传飞书原生 `read_option` 和 `export_option`：

```python
doc.fetch_content("xml", export_option={"export_block_id": True})
doc.fetch_content("markdown", read_option={"read_mode": "outline", "max_depth": "3"})
```

## 写入

```python
doc.clear_content()
doc.write_markdown("# 标题\n\n正文内容\n\n- 列表项")

doc.append_markdown("## 新增章节\n\n追加内容")
```

`write_markdown` 内部分两步：

1. 调用官方 convert API 将 Markdown 转为块 JSON。
2. 调用 create block 接口写入文档。

如果只需要转换不写入，可以单独使用 `convert_markdown`：

```python
blocks = doc.convert_markdown("# 标题")
```

## 手动创建块

```python
doc.create_block(children=[
    {"block_type": 3, "heading1": {"elements": [{"text_run": {"content": "标题"}}]}},
    {"block_type": 2, "text": {"elements": [{"text_run": {"content": "正文"}}]}},
])
```

块类型定义见 `feishukit/feishu_doc/data_type.py`。

## 素材

推荐直接使用 `insert_media_block()`：

```python
file_token = doc.insert_media_block("./photo.jpg")
file_token = doc.insert_media_block("./report.pdf")
```

`upload_media()` 是底层能力，需要调用方自己提供目标 block_id：

```python
file_token = doc.upload_media("./photo.jpg", parent_node=block_id)
```

素材上传后无法通过当前 SDK 直接删除，测试时请只在测试文档中使用。

## 删除

```python
doc.clear_content()
doc.delete_block(block_id, start_index=0, end_index=1)
```

`clear_content()` 会删除根节点下所有 children，但保留文档本身。

## 支持的 Markdown

- 标题 (`#` ~ `######`)
- 有序/无序列表
- 代码块
- 引用
- 分割线
- 加粗、斜体、删除线、行内代码、超链接

飞书特有块类型，如高亮块 Callout，需要使用 `create_block` 手动构建。

## 块类型速查

| 类型 | 值 | 类型 | 值 |
|------|----|------|----|
| text | 2 | bullet | 12 |
| heading1 | 3 | ordered | 13 |
| heading2 | 4 | code | 14 |
| heading3 | 5 | quote | 15 |
| heading4 | 6 | todo | 17 |
| heading5~9 | 7~11 | divider | 22 |
| file | 23 | image | 27 |
