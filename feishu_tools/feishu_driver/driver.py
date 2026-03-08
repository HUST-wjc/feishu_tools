import os
from typing import Any

from ..feishu_api import FeishuAPI

CHUNK_SIZE = 4 * 1024 * 1024  # 4MB，飞书固定分片大小
MAX_DIRECT_UPLOAD_SIZE = 20 * 1024 * 1024  # 20MB，直接上传的大小上限
IMAGE_EXTENSIONS = frozenset({".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg", ".ico", ".tiff", ".tif"})


class FeishuDriver:
    """飞书云空间相关能力
    https://open.feishu.cn/document/server-docs/docs/drive-v1/introduction
    """

    def __init__(self, app_id: str = '', app_secret: str = '', feishu_api: FeishuAPI | None = None) -> None:
        self.feishu_api = feishu_api or FeishuAPI(app_id, app_secret)

    def __repr__(self) -> str:
        app_id, app_secret_encrypted = self.feishu_api._masked_credentials()
        return f"FeishuDriver(app_id={app_id}, app_secret={app_secret_encrypted})"

    # ── 查询 ──────────────────────────────────────────────────

    def get_root_folder_meta(self) -> dict[str, Any]:
        """
        获取我的空间 (根文件夹) 元数据
        https://open.feishu.cn/document/server-docs/docs/drive-v1/folder/get-root-folder-meta

        获取用户"我的空间" (根文件夹) 的元数据，包括根文件夹的 token、ID 和文件夹所有者的 ID。
        """
        # https://open.feishu.cn/open-apis/drive/explorer/v2/root_folder/meta
        return self.feishu_api.request("GET", "/drive/explorer/v2/root_folder/meta")

    def list_files(self,
        page_size: int = 100,
        folder_token: str | None = None,
        order_by: str | None = None,
        direction: str | None = None,
        user_id_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """获取用户云空间指定文件夹中文件信息清单
        https://open.feishu.cn/document/server-docs/docs/drive-v1/folder/list

        page_size: 每页数据项数量，最大 200, 默认 100。获取根目录时返回全部数据
        folder_token: 文件夹 token, 不填则获取根目录清单 (根目录不支持分页)
        order_by: 排序方式 - EditedTime(默认) / CreatedTime
        direction: 排序规则，与 order_by 配合 - DESC(默认) / ASC
        user_id_type: 用户 ID 类型 - open_id(默认) / union_id / user_id
        """
        params: dict[str, Any] = {}

        if page_size:
            params["page_size"] = page_size
        if folder_token:
            params["folder_token"] = folder_token
        if order_by:
            params["order_by"] = order_by
        if direction:
            params["direction"] = direction
        if user_id_type:
            params["user_id_type"] = user_id_type
        return self.feishu_api.paginate("GET", "/drive/v1/files", params=params, item_key='files')

    def get_file_meta(self,
        request_files: str | list[str] | None = None,
        request_docs: list[dict[str, str]] | None = None,
        with_url: bool = False,
        user_id_type: str = 'open_id',
    ) -> dict[str, Any]:
        """获取文件元数据
        https://open.feishu.cn/document/server-docs/docs/drive-v1/file/batch_query

        该接口用于根据文件 token 获取其元数据, 包括标题、所有者、创建时间、密级、访问链接等数据。

        request_docs: 请求文档列表, 一次不可超过200个。格式为 [{"doc_token": doc_token, "doc_type": "file"}], doc_type 可选值为 doc, sheet, bitable, mindnote, file, wiki, docx, folder
        with_url: 是否返回文件的下载链接
        user_id_type: 用户 ID 类型, 可选值为 open_id, union_id, user_id
        """
        if not request_files and not request_docs:
            raise ValueError("request_files 和 request_docs 不能同时为空")
        if not request_docs:
            if isinstance(request_files, str):
                request_files = [request_files]
            request_docs = [{"doc_token": doc_token, "doc_type": "file"} for doc_token in request_files] # type: ignore

        params: dict[str, str] = {"user_id_type": user_id_type}
        body: dict[str, Any] = {"request_docs": request_docs, "with_url": with_url}
        return self.feishu_api.request("POST", "/drive/v1/metas/batch_query", params=params, body=body)
        
    # ── 上传 ──────────────────────────────────────────────────

    def upload(self,
        upload_type: str,
        file_path: str,
        parent_type: str,
        parent_node: str,
        file_name: str | None = None,
        extra: str | None = None,   
    ) -> str:
        """上传分为文件 (file) 和素材 (media) 两种类型。
        文件: 
            https://open.feishu.cn/document/docs/drive-v1/file/file-overview
            上传至云空间
        素材: 
            https://open.feishu.cn/document/server-docs/docs/drive-v1/media/introduction
            上传至指定云文档中, 此时文件将显示在对应云文档中, 在云空间中不会显示。

        <= 20MB 走直接上传，> 20MB 自动走分片上传。
        
        upload_type: 上传类型, 可选值为 files, medias
        parent_type: 上传点类型, 
            文件: 上传点的类型。取固定值 explorer, 表示将文件上传至云空间中。
            素材: 上传点的类型。你可根据上传的素材类型与云文档类型确定上传点类型。
                目前可选值为 doc_image / docx_image / sheet_image / doc_file / docx_file / sheet_file / bitable_image / bitable_file / ccm_import_open
    
        parent_node: 上传点 token (云文档的 token)
        file_name: 素材名称，默认取文件名
        extra: 部分场景需要传入素材所在云文档的 token, 格式见官方文档
        """
        file_path = os.path.expanduser(file_path)
        file_size = os.path.getsize(file_path)
        file_name = file_name or os.path.basename(file_path)

        if file_size <= MAX_DIRECT_UPLOAD_SIZE:
            return self._upload_all(upload_type, file_path, parent_type, parent_node, file_size, file_name, extra)
        else:
            return self._upload_multipart(upload_type, file_path, parent_type, parent_node, file_size, file_name, extra)

    # ── 直接上传 (≤ 20MB) ─────────────────────────────────────

    def _upload_all(self,
        upload_type: str,
        file_path: str,
        parent_type: str,
        parent_node: str,
        file_size: int,
        file_name: str,
        extra: str | None = None,
    ) -> str:
        """上传 (≤ 20MB)
        文件: https://open.feishu.cn/document/server-docs/docs/drive-v1/upload/upload_all
        素材: https://open.feishu.cn/document/server-docs/docs/drive-v1/media/upload_all
        """
        body: dict[str, Any] = {
            "file_name": file_name,
            "parent_type": parent_type,
            "parent_node": parent_node,
            "size": str(file_size),
        }
        if extra:
            body["extra"] = extra

        with open(file_path, "rb") as f:
            files = {"file": (file_name, f)}
            result = self.feishu_api.request("POST", f"/drive/v1/{upload_type}/upload_all", body=body, files=files)
        return result["file_token"]

    # ── 分片上传 (> 20MB) ─────────────────────────────────────

    def _upload_prepare(self,
        upload_type: str,
        parent_type: str,
        parent_node: str,
        file_size: int,
        file_name: str,
        extra: str | None = None,
    ) -> dict[str, Any]:
        """分片上传-预上传，获取 upload_id 和分片策略
        文件: https://open.feishu.cn/document/server-docs/docs/drive-v1/upload/multipart-upload-file-/upload_prepare
        素材: https://open.feishu.cn/document/server-docs/docs/drive-v1/media/multipart-upload-media/upload_prepare
        """
        body: dict[str, Any] = {
            "file_name": file_name,
            "parent_type": parent_type,
            "parent_node": parent_node,
            "size": file_size,
        }
        if extra:
            body["extra"] = extra
        return self.feishu_api.request("POST", f"/drive/v1/{upload_type}/upload_prepare", body=body)

    def _upload_part(self, upload_type: str, upload_id: str, seq: int, chunk: bytes) -> None:
        """分片上传-上传分片
        文件: https://open.feishu.cn/document/server-docs/docs/drive-v1/upload/multipart-upload-file-/upload_part
        素材: https://open.feishu.cn/document/server-docs/docs/drive-v1/media/multipart-upload-media/upload_part
        """
        body: dict[str, Any] = {
            "upload_id": upload_id,
            "seq": str(seq),
            "size": str(len(chunk)),
        }
        files = {"file": (f"part_{seq}", chunk)}
        self.feishu_api.request("POST", f"/drive/v1/{upload_type}/upload_part", body=body, files=files)

    def _upload_finish(self, upload_type: str, upload_id: str, block_num: int) -> str:
        """分片上传-完成上传，返回 file_token
        文件: https://open.feishu.cn/document/server-docs/docs/drive-v1/upload/multipart-upload-file-/upload_finish
        素材: https://open.feishu.cn/document/server-docs/docs/drive-v1/media/multipart-upload-media/upload_finish
        """
        body = {"upload_id": upload_id, "block_num": block_num}
        result = self.feishu_api.request("POST", f"/drive/v1/{upload_type}/upload_finish", body=body)
        return result["file_token"]

    def _upload_multipart(self,
        upload_type: str,
        file_path: str,
        parent_type: str,
        parent_node: str,
        file_size: int,
        file_name: str,
        extra: str | None = None,
    ) -> str:
        """分片上传素材 (> 20MB)，内部自动完成 预上传 → 上传分片 → 完成上传"""
        prepare = self._upload_prepare(upload_type, parent_type, parent_node, file_size, file_name, extra)
        upload_id = prepare["upload_id"]
        block_num = prepare["block_num"]

        with open(file_path, "rb") as f:
            for seq in range(block_num):
                chunk = f.read(CHUNK_SIZE)
                self._upload_part(upload_type, upload_id, seq, chunk)

        return self._upload_finish(upload_type, upload_id, block_num)

    # ── 下载 ──────────────────────────────────────────────────

    def download(self, download_type: str, file_token: str, save_path: str, extra: str | None = None) -> str:
        """流式下载文件或素材到本地文件，返回保存路径
        文件: https://open.feishu.cn/document/server-docs/docs/drive-v1/download/download
        素材: https://open.feishu.cn/document/server-docs/docs/drive-v1/media/download

        file_token: 文件或素材的 token (通过文档块、电子表格、多维表格记录获取)
        save_path: 本地保存路径
        extra: 高级权限多维表格需要额外鉴权参数
        """
        params: dict[str, Any] = {}
        if extra:
            params["extra"] = extra
        save_path = os.path.expanduser(save_path)
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        self.feishu_api.download_to_file(f"/drive/v1/{download_type}/{file_token}/download", save_path, params=params)
        return save_path

    def get_tmp_download_urls(self, file_tokens: list[str], extra: str | None = None) -> list[dict[str, str]]:
        """批量获取素材临时下载链接 (24 小时有效)，一次最多 5 个
        https://open.feishu.cn/document/server-docs/docs/drive-v1/media/batch_get_tmp_download_url

        返回: [{"file_token": "...", "tmp_download_url": "..."}, ...]
        """
        params: dict[str, Any] = {"file_tokens": file_tokens}
        if extra:
            params["extra"] = extra
        result = self.feishu_api.request("GET", "/drive/v1/medias/batch_get_tmp_download_url", params=params)
        return result.get("tmp_download_urls") or []

    # ── 删除 ──────────────────────────────────────────────────

    def delete_file(self, file_token: str, file_type: str = "file") -> dict[str, Any]:
        """删除云空间中的文件或文件夹，只能删除文件，不能删除素材。删除成功后会进入回收站
        https://open.feishu.cn/document/server-docs/docs/drive-v1/file/delete

        删除文件不会返回有效值
        删除文件夹时会返回异步任务 ID ("task_id"), 
        可继续使用查询异步任务状态接口 (https://open.feishu.cn/document/server-docs/docs/drive-v1/file/async-task/task_check) 查询任务执行状态
        
        如果 type 与实际不匹配, 则会返回 404 错误

        删除文件接口，调用身份需要具有以下两种权限之一:
            该应用是文件所有者并且具有该文件所在父文件夹的编辑权限
            该应用并非文件所有者, 但是该文件所在父文件夹的所有者或者拥有该父文件夹的所有权限 (full access)
        即应用无法删除用户创建的文件
        """
        return self.feishu_api.request("DELETE", f"/drive/v1/files/{file_token}", params={"type": file_type})
