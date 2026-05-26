from typing import Any, Iterable
from urllib.parse import quote

from ..feishu_api import FeishuAPI, FeishuRuntimeError
from .auth import FeishuUserDeviceAuth

DEFAULT_USER_DEVICE_FLOW_SCOPES = (
    # user device flow 单次最多申请 50 个 scope。默认覆盖 feishukit 当前
    # bitable/doc/spreadsheet/driver 的常用读写路径，避开常见需企业管理审核的权限。
    # 官方 scope list: https://open.feishu.cn/document/server-docs/application-scope/scope-list
    "bitable:app",
    "docs:document.content:read",
    "docs:document.media:upload",
    "docs:document.media:download",
    "docx:document.block:convert",
    "docx:document:readonly",
    "docx:document:write_only",
    "docx:document:create",
    "wiki:space:retrieve",
    "wiki:node:read",
    "wiki:node:retrieve",
    "sheets:spreadsheet.meta:read",
    "sheets:spreadsheet:read",
    "sheets:spreadsheet:write_only",
    "drive:drive.metadata:readonly",
    "drive:file:upload",
    "drive:file:download",
    "space:document:delete",
)


class FeishuUser(FeishuAPI):
    def __init__(
        self,
        app_id: str = "",
        app_secret: str = "",
        *,
        token_cache_path: str | None = None,
        scopes: str | Iterable[str] | None = None,
        offline_access: bool = True,
        device_flow_timeout: int = 600,
        base_url: str = "https://open.feishu.cn/open-apis",
        accounts_url: str = "https://accounts.feishu.cn",
        feishu_api: FeishuAPI | None = None,
    ) -> None:
        """创建代表授权用户本人调用 API 的 Feishu API client。

        初始化时会确保 user access token 可用；没有可用 cache 或 refresh token
        时，会发起 device flow 并阻塞等待授权。
        `scopes=None` 时默认请求常用 bitable、doc、spreadsheet、driver
        读写和 wiki URL 解析权限。
        `offline_access=False` 会关闭 refresh token 能力；user access token
        过期后，下次请求必须重新走 device flow。
        """
        if scopes is None:
            scopes = DEFAULT_USER_DEVICE_FLOW_SCOPES

        if feishu_api is not None:
            app_id = feishu_api.app_id
            app_secret = feishu_api.app_secret
            base_url = feishu_api.base_url

        super().__init__(
            app_id,
            app_secret,
            base_url=base_url,
            init_access_token=False,
        )

        self.user_auth = FeishuUserDeviceAuth(
            app_id=self.app_id,
            app_secret=self.app_secret,
            open_base_url=self.base_url,
            accounts_base_url=accounts_url,
            scopes=scopes,
            offline_access=offline_access,
            token_cache_path=token_cache_path,
            device_flow_timeout=device_flow_timeout,
        )
        self.access_token = self._get_access_token()

    def _get_access_token(self, refresh: bool = False) -> str:
        if refresh:
            self.user_auth.refresh_after_invalid_token()
        else:
            self.user_auth.ensure_token_valid()
        return self.user_auth.access_token

    # ── 当前用户 ────────────────────────────────────────────────

    def get_current_user(self) -> dict[str, Any]:
        """获取当前授权用户信息。

        https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/reference/authen-v1/user_info/get
        返回当前 user_access_token 对应的用户信息 dict。
        """
        if self.user_auth.user:
            return self.user_auth.user
        data = self.request("GET", "/authen/v1/user_info")
        self.user_auth.user = data
        return data

    # ── 云文档 / 知识库发现 ─────────────────────────────────────

    def search_docs(
        self,
        query: str = "",
        *,
        doc_filter: dict[str, Any] | None = None,
        wiki_filter: dict[str, Any] | None = None,
        page_size: int = 15,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """搜索当前用户可见的云文档、知识库、表格、多维表格等资源。

        https://open.feishu.cn/document/uAjLw4CM/ukTMukTMukTM/search-v2/doc_wiki

        ``doc_filter`` 和 ``wiki_filter`` 直接使用飞书原生 filter 结构，例如:

        ```
        doc_filter={
            "doc_types": ["DOCX", "SHEET", "BITABLE"],
            "only_title": True,
            "folder_tokens": ["fld_xxx"],
        }
        wiki_filter={
            "doc_types": ["WIKI", "DOCX", "BITABLE"],
            "space_ids": ["space_xxx"],
        }
        ```

        如果两个 filter 都不传，会同时搜索普通云文档和知识库资源。
        对象内部读写仍交给对应 client。
        注意：搜索云文档可能需要额外审核权限，默认 scope 不主动申请。
        """

        page_size = min(max(int(page_size), 1), 20)
        body: dict[str, Any] = {"query": query, "page_size": page_size}
        if page_token:
            body["page_token"] = page_token

        if doc_filter is None and wiki_filter is None:
            body["doc_filter"] = {}
            body["wiki_filter"] = {}
        else:
            if doc_filter is not None:
                body["doc_filter"] = doc_filter
            if wiki_filter is not None:
                body["wiki_filter"] = wiki_filter

        data = self.request("POST", "/search/v2/doc_wiki/search", body=body)
        return {
            "total": data.get("total"),
            "has_more": data.get("has_more"),
            "page_token": data.get("page_token"),
            "results": data.get("res_units") or [],
        }

    def get_my_library_space(self) -> dict[str, Any]:
        """获取当前用户个人知识库对应的真实 space 信息。

        依赖知识库子节点列表接口:
        https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/wiki-v2/space-node/list

        优先调用个人知识库接口；当接口不返回 space 时，退回到个人知识库
        nodes 列表推导 space_id。返回 space dict。
        """
        try:
            data = self.request("GET", "/wiki/v2/spaces/my_library")
        except FeishuRuntimeError as exc:
            first_error = exc
        else:
            space = data.get("space") or {}
            if space:
                return space
            first_error = None

        data = self.request(
            "GET",
            "/wiki/v2/spaces/my_library/nodes",
            params={"page_size": 1},
        )
        items = data.get("items") or []
        if items and items[0].get("space_id"):
            return {"space_id": items[0]["space_id"], "space_type": "my_library"}
        if first_error:
            raise first_error
        return {}

    def list_my_library_nodes(
        self,
        *,
        parent_node_token: str | None = None,
        page_size: int = 50,
        size_limit: int = 0,
    ) -> list[dict[str, Any]]:
        """列出当前用户个人知识库中的节点。

        https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/wiki-v2/space-node/list
        对应 ``GET /wiki/v2/spaces/my_library/nodes``。

        返回节点 dict 列表；如需列出特定父节点下内容，传入 parent_node_token。
        """
        return self.list_wiki_nodes(
            "my_library",
            parent_node_token=parent_node_token,
            page_size=page_size,
            size_limit=size_limit,
        )

    def list_wiki_nodes(
        self,
        space_id: str,
        *,
        parent_node_token: str | None = None,
        page_size: int = 50,
        size_limit: int = 0,
    ) -> list[dict[str, Any]]:
        """列出指定知识库空间或父节点下的节点。

        https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/wiki-v2/space-node/list
        返回节点 dict 列表。
        """
        params: dict[str, Any] = {}
        if parent_node_token:
            params["parent_node_token"] = parent_node_token
        page_size = min(max(int(page_size), 1), 50)
        path = f"/wiki/v2/spaces/{quote(space_id, safe='')}/nodes"
        return self.paginate(
            "GET",
            path,
            params=params,
            page_size=page_size,
            size_limit=size_limit,
            item_key="items",
        )

    def get_wiki_node(self, token: str, obj_type: str | None = None) -> dict[str, Any]:
        """通过 node_token 或 obj_token 获取知识库节点信息。

        https://open.feishu.cn/document/server-docs/docs/wiki-v2/space-node/get_node
        返回 ``node`` dict。
        """
        params = {"token": token}
        if obj_type:
            params["obj_type"] = obj_type
        data = self.request("GET", "/wiki/v2/spaces/get_node", params=params)
        return data.get("node") or {}

    # ── 业务 client 工厂 ───────────────────────────────────────

    def bitable(self, bitable_url: str, **kwargs: Any):
        """用当前用户身份创建 Bitable client。"""
        from ..feishu_bitable.bitable import Bitable
        return Bitable(bitable_url=bitable_url, feishu_api=self, **kwargs)

    def doc(self, doc_url: str, **kwargs: Any):
        """用当前用户身份创建 FeishuDoc client。"""
        from ..feishu_doc.doc import FeishuDoc
        return FeishuDoc(doc_url=doc_url, feishu_api=self, **kwargs)

    def spreadsheet(self, spreadsheet_url: str, **kwargs: Any):
        """用当前用户身份创建 FeishuSpreadsheet client。"""
        from ..feishu_spreadsheet.spreadsheet import FeishuSpreadsheet
        return FeishuSpreadsheet(spreadsheet_url=spreadsheet_url, feishu_api=self, **kwargs)

    def driver(self, **kwargs: Any):
        """用当前用户身份创建 FeishuDriver client。"""
        from ..feishu_driver.driver import FeishuDriver
        return FeishuDriver(feishu_api=self, **kwargs)
