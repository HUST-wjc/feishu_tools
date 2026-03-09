"""feishu_tools — Doc 用法示例

⚠️ 使用前:
  1. 前往 https://open.feishu.cn/app 创建应用，获取 app_id 和 app_secret
  2. 为应用申请 docx:document 权限 (文档放在知识库中还需 wiki:wiki:readonly)
  3. 将应用添加为知识库文档的协作者
  4. 请在新建的、非生产环境的文档上运行本脚本，测试中包含清空和写入操作
"""

if __name__ == "__main__":
    from pprint import pprint
    from feishu_tools import FeishuDoc

    # ── 配置 ──────────────────────────────────────────────────────
    # 替换为你自己的应用凭据和文档 URL
    APP_ID = "cli_xxxx"
    APP_SECRET = "xxxx"
    DOC_URL = "https://xxx.feishu.cn/wiki/xxxxx"
    # 支持两种格式:
    #   知识库文档: https://xxx.feishu.cn/wiki/{node_token}
    #   个人空间文档: https://xxx.feishu.cn/docx/{document_id}

    # 用于素材测试的本地文件路径 (替换为你自己的文件)
    TEST_IMAGE = "./test.jpg"
    TEST_FILE = "./test.pdf"

    # ── 1. 初始化 ───────────────────────────────────────────────

    doc = FeishuDoc(app_id=APP_ID, app_secret=APP_SECRET, doc_url=DOC_URL)
    print(f"doc_id: {doc.doc_id}")

    # ── 2. 读取 — 元数据 & 纯文本 ──────────────────────────────

    meta = doc.get_doc_meta()
    pprint(meta)

    text = doc.get_raw_content()
    print(f"\n纯文本内容 (前 200 字):\n{text[:200]}")

    # ── 3. 读取 — 文档块结构 ───────────────────────────────────

    blocks = doc.get_doc_blocks()
    print(f"\n总块数: {len(blocks)}")
    for b in blocks[:10]:
        bt = b.get("block_type")
        bid = b.get("block_id", "")[:12]
        print(f"  [{bt:>2}] {bid}...  children={len(b.get('children', []))}")

    children = doc.get_children()
    print(f"\n根节点子块数: {len(children)}")

    # ── 4. 清空文档 ─────────────────────────────────────────────

    doc.clear_content()
    print("\n文档已清空")
    print(f"当前子块数: {len(doc.get_children())}")

    # ── 5. Markdown 写入 ────────────────────────────────────────

    md_content = """\
# feishu_doc 模块测试

这是通过 `FeishuDoc.write_markdown()` 写入的测试文档。

## 基本格式

支持 **加粗**、*斜体*、~~删除线~~、`行内代码`

支持 [飞书开放平台](https://open.feishu.cn) 超链接

## 列表

无序列表:
- 项目 A
- 项目 B
- 项目 C

有序列表:
1. 第一步
2. 第二步
3. 第三步

## 代码块

```python
from feishu_tools import FeishuDoc

doc = FeishuDoc(app_id='...', app_secret='...', doc_url='...')
doc.clear_content()
doc.write_markdown('# Hello World')
```

## 引用

> 飞书文档 API 支持将 Markdown 内容自动转换为文档块

---

*文档写入完毕*
"""

    result = doc.write_markdown(md_content)
    print(f"\n写入完成, 新建 {len(result.get('children', []))} 个块")

    # ── 6. 追加 Markdown ──────────────────────────────────────

    doc.append_markdown("## 追加章节\n\n这是通过 `append_markdown` 追加的内容。")
    print("追加写入完成")

    # ── 7. 素材 — 上传 & 插入图片/文件块 ─────────────────────

    # 上传素材，获取 file_token
    # 通过 get_children 获取根节点 block_id
    parent_node = 'xxxx'
    img_token = doc.upload_media(TEST_IMAGE, parent_node=doc.doc_id)
    print(f"\n上传素材: file_token={img_token}")

    # 在文档末尾插入图片块 (自动创建 Image Block → 上传 → 绑定)
    img_block_token = doc.insert_media_block(TEST_IMAGE)
    print(f"插入图片块: file_token={img_block_token}")

    # 在文档末尾插入文件块 (自动创建 File Block → 上传 → 绑定)
    file_block_token = doc.insert_media_block(TEST_FILE)
    print(f"插入文件块: file_token={file_block_token}")

    # ── 8. 验证 ─────────────────────────────────────────────────

    print(f"\n--- 写入后纯文本 ---\n{doc.get_raw_content()}")

    blocks = doc.get_doc_blocks()
    print(f"--- 写入后块结构 (共 {len(blocks)} 块) ---")
    for b in blocks[:20]:
        bt = b.get("block_type")
        bid = b.get("block_id", "")[:12]
        print(f"  [{bt:>2}] {bid}...  children={len(b.get('children', []))}")
