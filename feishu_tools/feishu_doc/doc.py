import os
from typing import Any
from urllib.parse import urlparse

from ..feishu_api import FeishuAPI, TOKEN_PATTERN
from ..feishu_driver.driver import FeishuDriver, IMAGE_EXTENSIONS
from .data_type import get_block_type


class FeishuDoc:
    """飞书文档
    https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/docx-overview

    文档 OpenAPI 中, 两个基础概念为文档和块。

    文档
        文档是用户在云文档中创建的一篇在线文档。每篇文档都有唯一的 document_id 作为标识。
        document_id 可以通过 url 或者 开放平台接口解析"我的空间 (根文件夹)"获取
    
    块
        在一篇文档中, 有多个不同类型的段落, 这些段落被定义为块(Block)。块是文档中的最小构建单元, 是内容的结构化组成元素, 有着明确的含义。
        块有多种形态, 可以是一段文字、一张电子表格、一张图片或一个多维表格等。每个块都有唯一的 block_id 作为标识。

        每一篇文档都有一个根块, 即页面块(Page block)。页面块的 block_id 与其所在文档的 document_id 相同。
        在数据结构中, 文档的页面块与其它块形成父子关系, 页面块为父块, 称为 Parent, 其它块为子块, 称为 Children。其它块之间也可形成父子关系。
    """

    def __init__(self, 
        app_id: str = '', 
        app_secret: str = '', 
        doc_url: str = '', 
        feishu_api: FeishuAPI | None = None) -> None:
        
        self.feishu_api = feishu_api or FeishuAPI(app_id, app_secret)

        url_type, token = self._parse_doc_url(doc_url)
        self.driver = FeishuDriver(feishu_api=self.feishu_api)

        if url_type == 'wiki':
            self.node_token = token
            self.doc_id = self.feishu_api.get_wiki_app_token(self.node_token)
        else:
            self.node_token = ''
            self.doc_id = token

        self.doc_url = doc_url

    def __repr__(self) -> str:
        app_id, app_secret_encrypted = self.feishu_api._masked_credentials()
        return f"FeishuDoc(app_id={app_id}, app_secret={app_secret_encrypted}, doc_url={self.doc_url})"
    
    @staticmethod
    def _parse_doc_url(url: str) -> tuple[str, str]:
        """解析飞书文档 URL, 返回 (url_type, token)

        支持两种格式:
        - 知识库文档: https://xxx.feishu.cn/wiki/{node_token}  → ("wiki", node_token)
        - 个人空间文档: https://xxx.feishu.cn/docx/{document_id} → ("docx", document_id)
        """
        if not url:
            raise ValueError("doc_url 不能为空")
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        for i, part in enumerate(path_parts):
            if part in ('wiki', 'docx') and i + 1 < len(path_parts):
                candidate = path_parts[i + 1]
                if TOKEN_PATTERN.fullmatch(candidate):
                    return part, candidate
                break
        raise ValueError(f"无法解析飞书文档URL: {url}, 需要满足模式: /wiki/{{token}} 或 /docx/{{token}}")

    # ── 读取 ──────────────────────────────────────────────────

    def get_doc_meta(self) -> dict[str, Any]:
        """获取文档元数据
        https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document/get
        """
        return self.feishu_api.request("GET", f"/docx/v1/documents/{self.doc_id}")

    def get_raw_content(self, lang: int = 0) -> str:
        """获取文档纯文本内容
        https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document/raw_content

        lang: @用户 的语言, 0=默认名称, 1=英文名称
        返回以 '\\n' 分割的纯文本, 非 Markdown 格式
        """
        url = f"/docx/v1/documents/{self.doc_id}/raw_content"
        return self.feishu_api.request("GET", url, params={"lang": lang})["content"]

    def get_doc_blocks(self,
        doc_version: int = -1,
        page_size: int = 500,
        size_limit: int = 0,
        timeout: int = 120) -> list[dict[str, Any]]:
        """获取文档所有块
        https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document/list

        doc_version: 文档版本号, -1 表示最新版本
        """
        url = f"/docx/v1/documents/{self.doc_id}/blocks"
        params = {"document_revision_id": doc_version}
        return self.feishu_api.paginate(
            "GET", url, params=params,
            page_size=page_size, size_limit=size_limit, timeout=timeout,
        )

    def get_children(self,
        block_id: str | None = None,
        page_size: int = 500,
        size_limit: int = 0,
        timeout: int = 120) -> list[dict[str, Any]]:
        """获取块的子块列表
        https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document-block-children/get

        block_id: 父块 ID, 默认为文档根节点
        """
        block_id = block_id or self.doc_id
        url = f"/docx/v1/documents/{self.doc_id}/blocks/{block_id}/children"
        return self.feishu_api.paginate(
            "GET", url,
            page_size=page_size, size_limit=size_limit, timeout=timeout,
        )

    # ── 写入 ──────────────────────────────────────────────────

    def convert_markdown(self, content: str) -> dict[str, Any]:
        """将 Markdown 转换为文档块结构 (不写入文档)
        https://open.feishu.cn/open-apis/docx/v1/documents/blocks/convert

        返回:
            first_level_block_ids: 第一级块的临时 ID 列表 (代表顺序)
            blocks: 带父子关系的完整块列表
            block_id_to_image_urls: 图片临时 ID 与 URL 的映射 (如有)
        """
        body = {"content": content, "content_type": "markdown"}
        return self.feishu_api.request("POST", "/docx/v1/documents/blocks/convert", body=body)

    def _markdown_to_children(self, content: str) -> list[dict[str, Any]]:
        """将 Markdown 转换为可直接传入 create_block 的 children 列表"""
        data = self.convert_markdown(content)
        first_level_ids = data.get("first_level_block_ids", [])
        blocks_by_id = {b["block_id"]: b for b in data.get("blocks", [])}
        children = []
        for bid in first_level_ids:
            block = blocks_by_id.get(bid)
            if block:
                children.append({
                    k: v for k, v in block.items()
                    if k not in ("block_id", "parent_id", "children")
                })
        return children

    def write_markdown(self, content: str) -> dict[str, Any]:
        """将 Markdown 转换为文档块并写入文档开头 (convert + create_block)

        支持标准 Markdown: 标题、列表、代码块、引用、加粗、斜体、链接等。
        不支持飞书特有块 (如高亮块 Callout), 需要时请用 create_block 手动构建。
        建议先调用 clear_content() 清空文档再写入。
        """
        return self.create_block(children=self._markdown_to_children(content))

    def append_markdown(self, content: str) -> dict[str, Any]:
        """将 Markdown 转换为文档块并追加到文档末尾"""
        end_index = len(self.get_children())
        return self.create_block(children=self._markdown_to_children(content), index=end_index)

    def create_block(self,
        children: list[dict[str, Any]],
        block_id: str | None = None,
        index: int = 0,
        client_token: str | None = None) -> dict[str, Any]:
        """在指定位置创建子块
        https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document-block/create

        children: 子块列表, 块类型定义见 data_type.py
        block_id: 父块 ID, 默认为文档根节点
        index: 插入位置, 0=开头, 传入子块数量=末尾
        client_token: 幂等键, 相同 client_token 不会重复创建
        """
        block_id = block_id or self.doc_id
        url = f"/docx/v1/documents/{self.doc_id}/blocks/{block_id}/children"
        params: dict[str, Any] = {"document_revision_id": -1}
        if client_token:
            params["client_token"] = client_token
        body = {"children": children, "index": index}
        return self.feishu_api.request("POST", url, params=params, body=body)

    def update_block(self, block_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """更新文档块
        https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document-block/patch
        """
        url = f"/docx/v1/documents/{self.doc_id}/blocks/{block_id}"
        params: dict[str, Any] = {"document_revision_id": -1}
        return self.feishu_api.request("PATCH", url, params=params, body=payload)

    # ── 素材 ──────────────────────────────────────────────────

    def upload_media(self, file_path: str, parent_node: str, parent_type: str | None = None) -> str:
        """上传素材到云文档，返回 file_token

        素材不支持删除
        
        上传后可用于附件字段: {"附件字段名": [{"file_token": token}]}
        parent_type 自动推导: 图片扩展名 → docx_image, 其余 → docx_file

        注意: 旧版文档支持的 parent_type 为 doc_image 和 doc_file
        """
        if not parent_type:
            ext = os.path.splitext(file_path)[1].lower()
            parent_type = "docx_image" if ext in IMAGE_EXTENSIONS else "docx_file"
        return self.driver.upload("medias", file_path, parent_type=parent_type, parent_node=parent_node)

    def update_media_block(self,
        file_path: str,
        index: int | None = None,
        block_id: str | None = None,
        parent_type: str | None = None,
    ) -> str:
        """在文档中插入图片或文件，返回 file_token

        根据文件扩展名自动判断类型:
            图片扩展名 → 创建 Image Block (block_type=27), parent_type=docx_image
            其余       → 创建 File Block  (block_type=23), parent_type=docx_file
        可通过 parent_type 手动指定覆盖。

        正确流程: 创建空 Block → 上传素材到该 Block → PATCH 绑定 token
        素材的 parent_node 必须是目标 Block 的 block_id, 否则绑定会 400。

        index: 插入位置, 默认追加到末尾
        block_id: 父块 ID, 默认为文档根节点
        """
        ext = os.path.splitext(file_path)[1].lower()
        is_image = ext in IMAGE_EXTENSIONS

        if index is None:
            index = len(self.get_children(block_id))

        if is_image:
            block_type = get_block_type("image")
            result = self.create_block(
                children=[{"block_type": block_type, "image": {}}],
                block_id=block_id, index=index,
            )
            media_block_id = result["children"][0]["block_id"]
            file_token = self.upload_media(file_path, parent_node=media_block_id, parent_type=parent_type)
            self.update_block(media_block_id, {"replace_image": {"token": file_token}})
        else:
            block_type = get_block_type("file")
            result = self.create_block(
                children=[{"block_type": block_type, "file": {"token": ""}}],
                block_id=block_id, index=index,
            )
            # File Block 被 View Block 包裹, File Block ID 在 View Block 的 children 中
            view_block = result["children"][0]
            media_block_id = view_block["children"][0]
            file_token = self.upload_media(file_path, parent_node=media_block_id, parent_type=parent_type)
            self.update_block(media_block_id, {"replace_file": {"token": file_token}})

        return file_token

    # ── 删除 ──────────────────────────────────────────────────

    def delete_block(self, 
        block_id: str, 
        start_index: int = 0, 
        end_index: int = 1, 
        document_revision_id: int = -1,
        client_token: str | None = None) -> dict[str, Any]:
        """删除文档块
        https://open.feishu.cn/document/server-docs/docs/docs/docx-v1/document-block/batch_delete
        """
        url = f"/docx/v1/documents/{self.doc_id}/blocks/{block_id}/children/batch_delete"
        body = {"start_index": start_index, "end_index": end_index}
        
        params: dict[str, Any] = {"document_revision_id": document_revision_id}
        if client_token:
            params["client_token"] = client_token
        return self.feishu_api.request("DELETE", url, params=params, body=body)

    def clear_content(self) -> dict[str, Any]:
        """清空文档内容 (保留文档本身)
        """
        children = self.get_children()
        if not children:
            return {}
        return self.delete_block(self.doc_id, 0, len(children))