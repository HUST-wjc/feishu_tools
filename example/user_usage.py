"""feishukit — FeishuUser 用法示例

使用前:
  1. 前往 https://open.feishu.cn/app 创建应用，获取 app_id 和 app_secret
  2. 为应用申请 FeishuUser 默认 scope 所需权限
  3. 第一次运行会打印飞书 device flow 授权链接，需要用户在浏览器中确认
  4. token_cache_path 指定后会保存 refresh token；请不要提交该文件
"""

if __name__ == "__main__":
    from feishukit import FeishuUser

    APP_ID = "cli_xxxx"
    APP_SECRET = "xxxx"
    TOKEN_CACHE_PATH = "./token_cache.json"

    api = FeishuUser(
        app_id=APP_ID,
        app_secret=APP_SECRET,
        token_cache_path=TOKEN_CACHE_PATH,
        scopes=None,          # None 使用默认常用 scope
        offline_access=True,  # 允许 refresh token，避免每次运行都重新授权
    )

    user = api.get_current_user()
    print(f"当前用户: {user.get('name')} ({user.get('open_id')})")

    # 后续业务 client 都会以当前用户身份请求飞书接口。
    # bt = api.bitable("https://xxx.feishu.cn/base/xxxxx?table=tblxxxx")
    # doc = api.doc("https://xxx.feishu.cn/wiki/xxxxx")
    # ss = api.spreadsheet("https://xxx.feishu.cn/sheets/xxxxx?sheet=abc123")
    # driver = api.driver()
