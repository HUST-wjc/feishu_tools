# Driver 用户指南

`FeishuDriver` 封装飞书云空间的文件和素材操作。Bitable 和 FeishuDoc 内部也会用它完成素材上传和下载。

## 初始化

```python
from feishukit import FeishuDriver

driver = FeishuDriver(app_id="cli_xxxx", app_secret="xxxx")
```

## 元数据

```python
root = driver.get_root_folder_meta()
files = driver.list_files()
files = driver.list_files(folder_token="fldxxxx")
meta = driver.get_file_meta("file_token")
```

`get_file_meta()` 支持批量查询，一次最多 200 个：

```python
meta = driver.get_file_meta(
    request_docs=[
        {"doc_token": "file_token", "doc_type": "file"},
        {"doc_token": "docx_token", "doc_type": "docx"},
    ],
    with_url=True,
)
```

## 上传

```python
token = driver.upload(
    "files",
    "./report.pdf",
    parent_type="explorer",
    parent_node=folder_token,
)

token = driver.upload(
    "medias",
    "./photo.jpg",
    parent_type="docx_image",
    parent_node=block_id,
)
```

`upload()` 会按文件大小自动选择：

- `<= 20MB`：直接上传
- `> 20MB`：分片上传

## 下载

```python
driver.download("files", file_token, "./local/report.pdf")
driver.download("medias", media_token, "./local/photo.jpg")
```

## 临时下载链接

```python
urls = driver.get_tmp_download_urls([token1, token2])
```

临时下载链接 24 小时有效，一次最多 5 个素材 token。

## 删除

```python
driver.delete_file(file_token, file_type="file")
```

删除只适用于云空间文件或文件夹。素材 `medias` 不支持删除。

## upload_type 与 parent_type

| upload_type | parent_type | 用途 |
|-------------|-------------|------|
| `files` | `explorer` | 上传文件到云空间 |
| `medias` | `docx_image` | 上传图片素材到文档 |
| `medias` | `docx_file` | 上传文件素材到文档 |
| `medias` | `bitable_image` | 上传图片素材到多维表格 |
| `medias` | `bitable_file` | 上传文件素材到多维表格 |

Bitable 和 FeishuDoc 的 `upload_media()` / `insert_media_block()` 会自动推导 `parent_type`，普通使用场景通常不需要直接调用 `FeishuDriver.upload("medias", ...)`。
