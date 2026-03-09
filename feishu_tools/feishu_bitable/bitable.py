import os
from typing import Any
from urllib.parse import urlparse, parse_qs

from ..feishu_api import FeishuAPI, TOKEN_PATTERN
from ..feishu_driver.driver import FeishuDriver, IMAGE_EXTENSIONS
from .components import TableMixin, RecordMixin, FieldMixin, ViewMixin


class Bitable(TableMixin, RecordMixin, FieldMixin, ViewMixin):
    """飞书多维表格
    https://open.feishu.cn/document/server-docs/docs/bitable-v1/bitable-overview
    
    一个 table_id 对应多维表格里的一张数据表，如果 bitable_url 里没有数据表的 id, 则默认取第一个数据表
    如果想操作多维表格里的其他数据表，可以用指定的 bitable_url 创建新的 Bitable 对象。
    """

    def __init__(self, 
        app_id: str = '', 
        app_secret: str = '', 
        bitable_url: str = '', 
        request_delay: float = 0.5, 
        feishu_api: FeishuAPI | None = None) -> None:

        self.feishu_api = feishu_api or FeishuAPI(app_id, app_secret)
        self.node_token, table_id = self.parse_bitable_url(bitable_url)
        self.driver = FeishuDriver(app_id='', app_secret='', feishu_api=self.feishu_api)

        if '/wiki/' in bitable_url:
            self.app_token = self.feishu_api.get_wiki_app_token(self.node_token)
        elif '/base/' in bitable_url:
            self.app_token = self.node_token
        else:
            raise ValueError(f"无法解析飞书多维表格URL: {bitable_url}, 需要满足模式: /wiki/ 或者 /base/")

        if not table_id:
            tables = self.list_tables()
            self.table_id = tables[0]["table_id"]
        else:
            self.table_id = table_id

        self.bitable_url = bitable_url
        self.request_delay = request_delay

    def __repr__(self) -> str:
        app_id, app_secret_encrypted = self.feishu_api._masked_credentials()
        return f"Bitable(app_id={app_id}, app_secret={app_secret_encrypted}, bitable_url={self.bitable_url}, request_delay={self.request_delay})"
    
    @staticmethod
    def parse_bitable_url(url: str) -> tuple[str, str | None]:
        """
        解析飞书多维表格URL
        同时支持放在知识库 (wiki) 里的多维表格 和 放在个人目录 (base) 里的多维表格
        """
        if not url:
            raise ValueError("bitable_url 不能为空")
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')

        node_token = None
        for i, part in enumerate(path_parts):
            if part in ('wiki', 'base') and i + 1 < len(path_parts):
                candidate = path_parts[i + 1]
                if TOKEN_PATTERN.fullmatch(candidate):
                    node_token = candidate
                break

        if not node_token:
            raise ValueError(f"无法解析飞书多维表格URL: {url}, 需要满足模式: /wiki/{{token}} 或 /base/{{token}}")

        table_id = parse_qs(parsed.query).get('table', [None])[0]
        return node_token, table_id

    def get_bitable_meta(self) -> dict[str, Any]:
        """获取多维表格元数据
        https://open.feishu.cn/document/server-docs/docs/bitable-v1/app/get
        """
        url = f"/bitable/v1/apps/{self.app_token}"
        return self.feishu_api.request("GET", url).get('app') or {}

    # ── 素材 ──────────────────────────────────────────────────

    def upload_media(self, file_path: str, parent_type: str | None = None) -> str:
        """上传素材到多维表格，返回 file_token

        素材不支持删除

        上传后可用于附件字段: {"附件字段名": [{"file_token": token}]}
        parent_type 自动推导: 图片扩展名 → bitable_image, 其余 → bitable_file
        """
        if not parent_type:
            ext = os.path.splitext(file_path)[1].lower()
            parent_type = "bitable_image" if ext in IMAGE_EXTENSIONS else "bitable_file"
        return self.driver.upload("medias", file_path, parent_type=parent_type, parent_node=self.app_token)