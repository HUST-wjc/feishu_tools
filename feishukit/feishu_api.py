import re
from typing import Any, Generator

import requests


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9+/]+={0,2}")

class FeishuRuntimeError(RuntimeError):
    """飞书 API 请求错误"""
    pass


class _TokenInvalidError(Exception):
    pass


class FeishuAPI:
    def __init__(self, app_id: str, app_secret: str):
        if not all([app_id.strip(), app_secret.strip()]):
            raise ValueError("app_id 和 app_secret 不能为空")
        self.app_id = app_id.strip()
        self.app_secret = app_secret.strip()
        self.base_url = "https://open.feishu.cn/open-apis"
        self.access_token = self._get_access_token()

    def _get_access_token(self) -> str:
        """获取飞书 access_token
        https://open.feishu.cn/document/server-docs/api-call-guide/calling-process/get-access-token

        此处 requests 默认 timeout 30s, 防止飞书偶发的网络问题。不接受配置 timeout 参数，因为 30s 已经足够长
        """
        url = f"{self.base_url}/auth/v3/tenant_access_token/internal"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        data = {"app_id": self.app_id, "app_secret": self.app_secret}
        response = requests.post(url, headers=headers, json=data, timeout=30)
        result = response.json()
        if result.get("code") != 0:
            response_msg = _combine_response_msg("POST", url, response.status_code, response.text)
            raise FeishuRuntimeError(f"获取 access_token 失败: {response_msg}")
        return result["tenant_access_token"]

    def _request(self, 
        method: str, 
        url: str, 
        params: dict[str, Any] | None = None, 
        body: dict[str, Any] | None = None, 
        files: dict | None = None, 
        timeout: int = 120,
        raw: bool = False,
    ) -> dict | bytes:
        url = f"{self.base_url}/{url.lstrip('/')}"
        params = params or {}
        headers: dict[str, str] = {"Authorization": f"Bearer {self.access_token}"}
        if files:
            response = requests.request(method, url, headers=headers, params=params, data=body or {}, files=files, timeout=timeout)
        elif body is not None:
            headers["Content-Type"] = "application/json"
            response = requests.request(method, url, headers=headers, params=params, json=body, timeout=timeout)
        else:
            response = requests.request(method, url, headers=headers, params=params, timeout=timeout)

        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            response_msg = _combine_response_msg(method, url, response.status_code, response.text)
            if "invalid access token" in response.text.lower():
                raise _TokenInvalidError(response_msg) from e
            raise FeishuRuntimeError(response_msg) from e

        if raw:
            return response.content

        response_msg = _combine_response_msg(method, url, response.status_code, response.text)
        result = response.json()
        if result.get("code") != 0:
            if result.get("code") == 99991663:
                raise _TokenInvalidError(response_msg)
            raise FeishuRuntimeError(response_msg)
        return result.get("data") or {}

    def request(self, 
        method: str, 
        url: str, 
        params: dict[str, Any] | None = None, 
        body: dict[str, Any] | None = None, 
        files: dict | None = None, 
        timeout: int = 120,
    ) -> dict:
        try:
            return self._request(method, url, params, body, files, timeout)  # type: ignore[return-value]
        except _TokenInvalidError:
            self.access_token = self._get_access_token()
            return self._request(method, url, params, body, files, timeout)  # type: ignore[return-value]

    def request_raw(self, method: str, url: str, params: dict[str, Any] | None = None, timeout: int = 300) -> bytes:
        """发送请求并返回原始二进制内容，用于文件下载等非 JSON 响应"""
        try:
            return self._request(method, url, params, raw=True, timeout=timeout)  # type: ignore[return-value]
        except _TokenInvalidError:
            self.access_token = self._get_access_token()
            return self._request(method, url, params, raw=True, timeout=timeout)  # type: ignore[return-value]

    def _download_stream(self, url: str, save_path: str, params: dict[str, Any] | None = None, timeout: int = 300) -> None:
        full_url = f"{self.base_url}/{url.lstrip('/')}"
        headers: dict[str, str] = {"Authorization": f"Bearer {self.access_token}"}
        with requests.get(full_url, headers=headers, params=params or {}, timeout=timeout, stream=True) as resp:
            try:
                resp.raise_for_status()
            except requests.HTTPError as e:
                response_msg = _combine_response_msg("GET", full_url, resp.status_code, resp.text)
                if "invalid access token" in resp.text.lower():
                    raise _TokenInvalidError(response_msg) from e
                raise FeishuRuntimeError(response_msg) from e
            with open(save_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)

    def download_to_file(self, url: str, save_path: str, params: dict[str, Any] | None = None, timeout: int = 300) -> None:
        """流式下载到文件，避免大文件占满内存"""
        try:
            self._download_stream(url, save_path, params, timeout)
        except _TokenInvalidError:
            self.access_token = self._get_access_token()
            self._download_stream(url, save_path, params, timeout)

    def iter_paginate(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
        page_size: int = 500,
        size_limit: int = 0,
        item_key: str = 'items',
        timeout: int = 600,
    ) -> Generator[Any, Any, None]:
        # 迭代分页获取数据，以飞书表格为例，默认 2万行，可扩充至 5 万行，最高扩容到 200 万行
        params = dict(params or {})
        body = body or {}

        if 0 < size_limit < page_size:
            page_size = size_limit
        body["page_size"] = page_size

        page_token = None
        yielded = 0

        while True:
            _params = params if page_token is None else {**params, "page_token": page_token}
            result = self.request(method, url, params=_params, body=body, timeout=timeout)

            for item in result.get(item_key) or []:
                yield item
                yielded += 1
                if 0 < size_limit <= yielded:
                    return

            if not result.get("has_more") or not result.get("page_token"):
                return

            page_token = result["page_token"]

    def paginate(self, *args, **kwargs) -> list:
        return list(self.iter_paginate(*args, **kwargs))

    def get_wiki_app_token(self, node_token: str, obj_type: str = "wiki") -> str:
        """获取知识库节点信息
        https://open.feishu.cn/document/docs/drive-v1/file/file-overview

        获取文件 node_token 对应的实际 obj_token

        obj_type: 文件类型, 可选值为 doc, docx, sheet, mindnote, bitable, file, slides, wiki。默认为 wiki
        """
        result = self.request("GET", "/wiki/v2/spaces/get_node", {"token": node_token, "obj_type": obj_type})
        return result["node"]["obj_token"]

    def _masked_credentials(self) -> tuple[str, str]:
        """获取加密后的应用元数据, 用于其他 类的 __repr__ 方法"""
        app_id = self.app_id
        app_secret = self.app_secret
        app_secret_encrypted = app_secret[:2] + "*" * (len(app_secret) - 2)
        return app_id, app_secret_encrypted


def _combine_response_msg(method: str, url: str, status_code: int, text: str) -> str:
    return (
        f"\nmethod: {method}\n"
        f"url: {url}\n"
        f"status_code: {status_code}\n"
        f"text: {text}"
    )