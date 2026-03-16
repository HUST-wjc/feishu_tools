"""feishukit — Driver 用法示例

⚠️ 使用前:
  1. 前往 https://open.feishu.cn/app 创建应用，获取 app_id 和 app_secret
  2. 为应用申请 drive:drive 权限
  3. 请在非生产环境中运行本脚本，测试中包含上传和删除操作
"""

if __name__ == "__main__":
    import os
    from pprint import pprint
    from feishukit import FeishuDriver

    # ── 配置 ──────────────────────────────────────────────────────
    APP_ID = "cli_xxxx"
    APP_SECRET = "xxxx"
    TEST_FILE = "./test.txt"  # 替换为你自己的测试文件

    # ── 1. 初始化 ───────────────────────────────────────────────

    driver = FeishuDriver(app_id=APP_ID, app_secret=APP_SECRET)
    print(driver)

    # ── 2. 元数据 ───────────────────────────────────────────────

    root = driver.get_root_folder_meta()
    print(f"\n根文件夹 token: {root.get('token')}")
    print(f"根文件夹 id:    {root.get('id')}")

    files = driver.list_files()
    print(f"\n根目录文件数: {len(files)}")
    for f in files[:5]:
        print(f"  {f.get('token')}: {f.get('name')} ({f.get('type')})")

    # ── 3. 上传文件到云空间 ─────────────────────────────────────

    folder_token = root["token"]
    file_token = driver.upload(
        "files", TEST_FILE,
        parent_type="explorer",
        parent_node=folder_token,
    )
    print(f"\n上传成功, file_token: {file_token}")

    # ── 4. 查询文件元数据 ───────────────────────────────────────

    meta = driver.get_file_meta(file_token)
    pprint(meta)

    # ── 5. 下载文件 ─────────────────────────────────────────────

    save_dir = "./tmp/driver_test_download"
    save_path = driver.download("files", file_token, f"{save_dir}/{os.path.basename(TEST_FILE)}")

    original_size = os.path.getsize(TEST_FILE)
    downloaded_size = os.path.getsize(save_path)
    print(f"\n下载完成: {save_path}")
    print(f"大小一致: {original_size == downloaded_size}")

    # ── 6. 临时下载链接 ─────────────────────────────────────────

    # 注: 临时链接仅支持 medias 类型，files 类型不支持
    # urls = driver.get_tmp_download_urls([media_token])
    # pprint(urls)

    # ── 7. 删除文件 ─────────────────────────────────────────────

    result = driver.delete_file(file_token)
    print(f"\n删除成功 (文件进入回收站)")

    # 验证删除
    meta_after = driver.get_file_meta(file_token)
    deleted = meta_after.get("metas", [{}])[0].get("type", "") == ""
    print(f"文件已删除: {deleted}")
