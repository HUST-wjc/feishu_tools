import json
import time
from pathlib import Path
from typing import Any, Iterable

import requests

from ..feishu_api import (
    FeishuRuntimeError,
    _combine_response_msg,
)


class FeishuAuthError(FeishuRuntimeError):
    """飞书认证错误"""
    pass


class FeishuDeviceAuthTimeoutError(FeishuAuthError):
    """设备授权超时"""
    pass


class FeishuAuthorizationRejectedError(FeishuAuthError):
    """用户拒绝授权"""
    pass


class FeishuUserDeviceAuth:
    DEVICE_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:device_code"
    MAX_SCOPE_COUNT = 50

    def __init__(
        self,
        app_id: str,
        app_secret: str,
        *,
        open_base_url: str = "https://open.feishu.cn/open-apis",
        accounts_base_url: str = "https://accounts.feishu.cn",
        scopes: str | Iterable[str] | None = None,
        offline_access: bool = True,
        token_cache_path: str | None = None,
        device_flow_timeout: int = 600,
    ) -> None:
        """创建 device-flow 用户授权辅助对象。

        user access token 官方文档:
        https://open.feishu.cn/document/authentication-management/access-token/get-user-access-token

        `offline_access=True` 会请求 refresh token 能力。设为 False 时，
        飞书只返回短期 user access token；token 过期后需要重新走 device flow。
        """
        self.app_id = app_id
        self.app_secret = app_secret
        self.open_base_url = open_base_url.rstrip("/")
        self.accounts_base_url = accounts_base_url.rstrip("/")
        self.scope = _normalize_scopes(scopes, offline_access=offline_access)
        self.offline_access = offline_access
        self.token_cache_path = Path(token_cache_path).expanduser() if token_cache_path else None
        self.device_flow_timeout = device_flow_timeout

        self.access_token = ""
        self.refresh_token = ""
        self.expires_at = 0.0
        self.refresh_expires_at = 0.0
        self.token_type = "Bearer"
        self.granted_scope = ""
        self.user: dict[str, Any] = {}

        self._load_cache()

    @property
    def _access_token_valid(self) -> bool:
        if not self.access_token:
            return False
        if time.time() >= self.expires_at - 60:
            return False
        return True

    @property
    def _refresh_token_valid(self) -> bool:
        if not self.refresh_token:
            return False
        if time.time() >= self.refresh_expires_at - 60:
            return False
        return True

    def ensure_token_valid(self) -> str:
        if self._access_token_valid:
            return self.access_token
        if self._refresh_token_valid:
            self._refresh_with_refresh_token()
            return self.access_token
        self._authorize_with_device_flow()
        return self.access_token

    def _load_cache(self) -> None:
        if not self.token_cache_path or not self.token_cache_path.exists():
            return
        try:
            data = json.loads(self.token_cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            raise FeishuAuthError(f"读取 token cache 失败: {self.token_cache_path}") from e

        if data.get("auth_type") != "user" or data.get("app_id") != self.app_id:
            return

        cached_scope = data.get("scope") or ""
        missing_scopes = self._missing_requested_scopes(cached_scope)
        needs_refresh_token = self._needs_refresh_token(data)
        if missing_scopes or needs_refresh_token:
            reasons = []
            if missing_scopes:
                reasons.append(f"缺少 scopes: {', '.join(missing_scopes)}")
            if needs_refresh_token:
                reasons.append("缺少 refresh_token")
            print(
                f"当前 token cache 权限不足，需要重新授权更新权限 ({'; '.join(reasons)})。",
                flush=True,
            )
            return

        self.access_token = data.get("access_token") or ""
        self.refresh_token = data.get("refresh_token") or ""
        self.expires_at = float(data.get("expires_at") or 0)
        self.refresh_expires_at = float(data.get("refresh_expires_at") or 0)
        self.token_type = data.get("token_type") or "Bearer"
        self.granted_scope = cached_scope
        self.user = data.get("user") or {}

    def _missing_requested_scopes(self, cached_scope: str) -> list[str]:
        if not self.scope:
            return []
        requested = set(self.scope.split()) - {"offline_access"}
        cached = set(cached_scope.split())
        return sorted(requested - cached)

    def _needs_refresh_token(self, cache_data: dict[str, Any]) -> bool:
        if not self.scope or "offline_access" not in self.scope.split():
            return False
        return not bool(cache_data.get("refresh_token"))

    def _save_cache(self) -> None:
        if not self.token_cache_path:
            return
        data = {
            "auth_type": "user",
            "app_id": self.app_id,
            "access_token": self.access_token,
            "expires_at": self.expires_at,
            "refresh_token": self.refresh_token,
            "refresh_expires_at": self.refresh_expires_at,
            "scope": self.granted_scope,
            "token_type": self.token_type,
            "user": self.user,
        }
        self.token_cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _authorize_with_device_flow(self) -> None:
        device = self._request_device_code()
        verification_url = (
            device.get("verification_uri_complete")
            or device.get("verification_url")
            or device.get("verification_uri")
        )
        device_code = device.get("device_code")
        if not device_code or not verification_url:
            raise FeishuAuthError(f"设备授权响应缺少 device_code 或 verification URL: {device}")

        print("请在浏览器打开以下链接完成飞书授权：", flush=True)
        print(verification_url, flush=True)
        print("等待用户授权...", flush=True)

        interval = int(device.get("interval") or 5)
        expires_in = int(device.get("expires_in") or self.device_flow_timeout)
        deadline = time.time() + min(expires_in, self.device_flow_timeout)

        while time.time() < deadline:
            status, token = self._poll_device_token(device_code)
            if status == "pending":
                time.sleep(interval)
                continue
            if status == "slow_down":
                interval += 5
                time.sleep(interval)
                continue
            self._apply_token_response(token)
            self._save_cache()
            return

        raise FeishuDeviceAuthTimeoutError(
            "设备授权超时。不要用短 timeout 反复重试；如需重试，请让用户使用新打印的授权链接。"
        )

    def _request_device_code(self) -> dict[str, Any]:
        url = f"{self.accounts_base_url}/oauth/v1/device_authorization"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        body = {"client_id": self.app_id, "client_secret": self.app_secret}
        if self.scope is not None:
            body["scope"] = self.scope
        response = requests.post(url, headers=headers, json=body, timeout=30)
        result = _json_response(response, "POST", url)
        if _is_error_response(result):
            raise FeishuAuthError(f"请求 device code 失败: {_format_oauth_error(result)}")
        return _unwrap_data(result)

    def _poll_device_token(self, device_code: str) -> tuple[str, dict[str, Any]]:
        url = f"{self.open_base_url}/authen/v2/oauth/token"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        body = {
            "grant_type": self.DEVICE_GRANT_TYPE,
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "device_code": device_code,
        }
        response = requests.post(url, headers=headers, json=body, timeout=30)
        result = _json_response(response, "POST", url)

        error = result.get("error") or result.get("error_description")
        code = result.get("code")
        msg = str(error or result.get("msg") or result.get("message") or "").lower()
        if error == "authorization_pending" or "authorization_pending" in msg:
            return "pending", {}
        if error == "slow_down" or "slow_down" in msg:
            return "slow_down", {}
        if error == "access_denied" or code in {20054, 20055}:
            raise FeishuAuthorizationRejectedError("用户拒绝了飞书授权")
        if _is_error_response(result):
            raise FeishuAuthError(f"轮询 device token 失败: {_format_oauth_error(result)}")
        return "ok", _unwrap_data(result)

    def _refresh_with_refresh_token(self) -> None:
        if not self.refresh_token:
            raise FeishuAuthError("缺少 refresh_token，无法刷新 user_access_token")
        url = f"{self.open_base_url}/authen/v2/oauth/token"
        headers = {"Content-Type": "application/json; charset=utf-8"}
        body = {
            "grant_type": "refresh_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "refresh_token": self.refresh_token,
        }
        response = requests.post(url, headers=headers, json=body, timeout=30)
        result = _json_response(response, "POST", url)
        if _is_error_response(result):
            raise FeishuAuthError(f"刷新 user_access_token 失败，需要重新授权: {_format_oauth_error(result)}")
        self._apply_token_response(_unwrap_data(result))
        self._save_cache()

    def _apply_token_response(self, token: dict[str, Any]) -> None:
        self.access_token = token.get("access_token") or token.get("user_access_token") or ""
        self.refresh_token = token.get("refresh_token") or self.refresh_token
        if not self.access_token:
            raise FeishuAuthError(f"token 响应缺少 access_token: {token}")

        # user access token 预期约 2 小时过期，expires_in 通常为 7199 秒。
        # 授权 offline_access 时，refresh token 预期约 7 天过期。
        expires_in = int(token.get("expires_in") or 0)
        refresh_expires_in = int(token.get("refresh_token_expires_in") or 0)
        self.expires_at = time.time() + expires_in if expires_in else 0
        if refresh_expires_in:
            self.refresh_expires_at = time.time() + refresh_expires_in
        self.token_type = token.get("token_type") or "Bearer"
        self.granted_scope = token.get("scope") or self.granted_scope

        user = token.get("user") or token.get("user_info") or {}
        if isinstance(user, dict):
            self.user = user


def _normalize_scopes(scopes: str | Iterable[str] | None, offline_access: bool = True) -> str | None:
    if scopes is None:
        return None
    elif isinstance(scopes, str):
        if not scopes.strip():
            raise ValueError("scopes 为空字符串没有明确语义；不限制业务 scope 请传 None")
        candidates = scopes.split()
    else:
        candidates = list(scopes)

    normalized = []
    seen = set()
    for scope in candidates:
        scope = str(scope).strip()
        if not scope or scope in seen:
            continue
        normalized.append(scope)
        seen.add(scope)

    if offline_access and "offline_access" not in normalized:
        normalized.append("offline_access")

    if len(normalized) > FeishuUserDeviceAuth.MAX_SCOPE_COUNT:
        raise ValueError(f"device flow 单次最多申请 {FeishuUserDeviceAuth.MAX_SCOPE_COUNT} 个 scopes")

    return " ".join(normalized) if normalized else ("offline_access" if offline_access else None)


def _json_response(response: requests.Response, method: str, url: str) -> dict[str, Any]:
    try:
        return response.json()
    except ValueError as e:
        response_msg = _combine_response_msg(method, url, response.status_code, response.text)
        raise FeishuRuntimeError(response_msg) from e


def _unwrap_data(result: dict[str, Any]) -> dict[str, Any]:
    data = result.get("data")
    return data if isinstance(data, dict) else result


def _is_error_response(result: dict[str, Any]) -> bool:
    code = result.get("code")
    if code not in (None, 0):
        return True
    return bool(result.get("error"))


def _format_oauth_error(result: dict[str, Any]) -> str:
    return str({
        "code": result.get("code"),
        "msg": result.get("msg") or result.get("message"),
        "error": result.get("error"),
        "error_description": result.get("error_description"),
    })
