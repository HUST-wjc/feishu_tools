from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlparse

from ..feishu_api import FeishuAPI, TOKEN_PATTERN
from ._range import (
    looks_like_relative_range,
    normalize_point_range,
    normalize_range_separators,
    normalize_value_range,
    normalize_write_range,
    split_sheet_range,
)


class FeishuSpreadsheet:
    """飞书电子表格 (Spreadsheet)

    https://open.feishu.cn/document/server-docs/docs/sheets-v3/overview

    电子表格 OpenAPI 的核心层级是 spreadsheet、sheet 和 range。
    本类代表一个 spreadsheet；读取或写入单元格数据时必须明确 sheet，
    可以通过完整 range、sheet_id 或 sheet_name 定位。
    """

    def __init__(
        self,
        app_id: str = '',
        app_secret: str = '',
        spreadsheet_url: str = '',
        feishu_api: FeishuAPI | None = None,
    ) -> None:
        self.feishu_api = feishu_api or FeishuAPI(app_id, app_secret)

        url_type, token, sheet_id = self.parse_spreadsheet_url(spreadsheet_url)
        self.node_token = token if url_type == 'wiki' else ''
        self.spreadsheet_token = self.feishu_api.get_wiki_app_token(token) if url_type == 'wiki' else token
        self.default_sheet_id = sheet_id
        self.spreadsheet_url = spreadsheet_url

    def __repr__(self) -> str:
        app_id, app_secret_encrypted = self.feishu_api._masked_credentials()
        return (
            f"FeishuSpreadsheet(app_id={app_id}, app_secret={app_secret_encrypted}, "
            f"spreadsheet_url={self.spreadsheet_url})"
        )

    @staticmethod
    def parse_spreadsheet_url(url: str) -> tuple[str, str, str | None]:
        """解析飞书电子表格 URL，返回 (url_type, token, sheet_id)。

        支持两种格式：
        - 知识库: https://xxx.feishu.cn/wiki/{node_token}?sheet={sheet_id}
        - 个人目录: https://xxx.feishu.cn/sheets/{spreadsheet_token}?sheet={sheet_id}

        注意：URL 中不包含 ``sheet=`` 时不会自动推断工作表。
        """
        if not url:
            raise ValueError("spreadsheet_url 不能为空")
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        path_parts = parsed.path.strip('/').split('/')

        for i, part in enumerate(path_parts):
            if part in ('wiki', 'sheets') and i + 1 < len(path_parts):
                candidate = path_parts[i + 1]
                if TOKEN_PATTERN.fullmatch(candidate):
                    sheet_id = query.get('sheet', [None])[0]
                    return part, candidate, sheet_id
                break

        raise ValueError(f"无法解析飞书电子表格URL: {url}, 需要满足模式: /wiki/{{token}} 或 /sheets/{{token}}")

    # ── Spreadsheet / Sheet ─────────────────────────────────────

    def get_spreadsheet_meta(self, user_id_type: str | None = None) -> dict[str, Any]:
        """获取电子表格基础信息。

        https://open.feishu.cn/document/server-docs/docs/sheets-v3/spreadsheet/get
        """
        url = f"/sheets/v3/spreadsheets/{self.spreadsheet_token}"
        params = {"user_id_type": user_id_type} if user_id_type else None
        return self.feishu_api.request("GET", url, params=params).get('spreadsheet') or {}

    def list_sheets(self) -> list[dict[str, Any]]:
        """获取 spreadsheet 中所有工作表及其属性。

        https://open.feishu.cn/document/server-docs/docs/sheets-v3/spreadsheet-sheet/query
        """
        url = f"/sheets/v3/spreadsheets/{self.spreadsheet_token}/sheets/query"
        return self.feishu_api.request("GET", url).get('sheets') or []

    def get_sheet(
        self,
        sheet_id: str | None = None,
        sheet_name: str | None = None,
        sheets: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """根据 sheet_id 或 sheet_name 获取单个工作表元信息。

        依赖工作表查询接口:
        https://open.feishu.cn/document/server-docs/docs/sheets-v3/spreadsheet-sheet/query

        如果两者都不传，会尝试使用 URL 中的 ``sheet=`` 作为默认工作表。
        返回 ``list_sheets()`` 中对应的单个 sheet dict。
        """
        resolved_id = self.resolve_sheet_id(sheet_id=sheet_id, sheet_name=sheet_name, sheets=sheets)
        sheets = sheets or self.list_sheets()
        for sheet in sheets:
            if sheet.get('sheet_id') == resolved_id:
                return sheet
        raise ValueError(f"工作表不存在, sheet_id: {resolved_id}")

    def resolve_sheet_id(
        self,
        sheet_id: str | None = None,
        sheet_name: str | None = None,
        sheets: list[dict[str, Any]] | None = None,
    ) -> str:
        """解析工作表 ID。

        依赖工作表查询接口:
        https://open.feishu.cn/document/server-docs/docs/sheets-v3/spreadsheet-sheet/query

        优先级：显式 sheet_id > sheet_name 查找 > URL 中的 default_sheet_id。
        没有可用工作表定位信息时抛出 ValueError，避免静默读写错误工作表。
        """
        if sheet_id:
            return sheet_id
        if sheet_name:
            sheets = sheets or self.list_sheets()
            matched = [s for s in sheets if s.get('title') == sheet_name]
            if not matched:
                raise ValueError(f"工作表不存在, sheet_name: {sheet_name}")
            if len(matched) > 1:
                raise ValueError(f"工作表名称不唯一, sheet_name: {sheet_name}, matched: {matched}")
            return matched[0]['sheet_id']
        if self.default_sheet_id:
            return self.default_sheet_id
        raise ValueError("需要明确 sheet_id、sheet_name，或在 spreadsheet_url 中包含 ?sheet=abc123")

    # ── Values / Range ──────────────────────────────────────────

    def get_values(
        self,
        range: str | None = None,
        *,
        sheet_id: str | None = None,
        sheet_name: str | None = None,
        cell_range: str | None = None,
        value_render_option: str | None = None,
        date_time_render_option: str | None = None,
        user_id_type: str | None = None,
    ) -> dict[str, Any]:
        """读取单个范围的数据，返回官方 valueRange。

        https://open.feishu.cn/document/server-docs/docs/sheets-v3/data-operation/reading-a-single-range

        支持三种定位方式：
        - ``get_values("3d9834!A1:C10")``
        - ``get_values(sheet_id="3d9834", cell_range="A1:C10")``
        - ``get_values(sheet_name="Sheet1", cell_range="A1:C10")``

        如果 URL 中带有 ``?sheet=``，也可以省略 sheet_id/sheet_name：
        ``get_values(cell_range="A1:C10")``。
        """
        resolved_range = self._resolve_range(
            range=range,
            sheet_id=sheet_id,
            sheet_name=sheet_name,
            cell_range=cell_range,
            normalize_single_cell=True,
        )
        params = _clean_params({
            "valueRenderOption": value_render_option,
            "dateTimeRenderOption": date_time_render_option,
            "user_id_type": user_id_type,
        })
        url = f"/sheets/v2/spreadsheets/{self.spreadsheet_token}/values/{resolved_range}"
        return self.feishu_api.request("GET", url, params=params).get('valueRange') or {}

    def get_rows(
        self,
        range: str | None = None,
        *,
        sheet_id: str | None = None,
        sheet_name: str | None = None,
        cell_range: str | None = None,
        value_render_option: str | None = None,
        date_time_render_option: str | None = None,
        user_id_type: str | None = None,
    ) -> list[list[Any]]:
        """读取单个范围的数据，只返回二维 ``values`` 列表。

        依赖读取单个范围接口:
        https://open.feishu.cn/document/server-docs/docs/sheets-v3/data-operation/reading-a-single-range

        这是 `get_values()` 的轻量包装；空范围返回空列表。
        """
        value_range = self.get_values(
            range=range,
            sheet_id=sheet_id,
            sheet_name=sheet_name,
            cell_range=cell_range,
            value_render_option=value_render_option,
            date_time_render_option=date_time_render_option,
            user_id_type=user_id_type,
        )
        return value_range.get('values') or []

    def get_cell(
        self,
        cell: str,
        *,
        sheet_id: str | None = None,
        sheet_name: str | None = None,
        value_render_option: str | None = None,
        date_time_render_option: str | None = None,
        user_id_type: str | None = None,
    ) -> Any:
        """读取单个单元格的值。

        依赖读取单个范围接口:
        https://open.feishu.cn/document/server-docs/docs/sheets-v3/data-operation/reading-a-single-range

        ``cell`` 可以是 ``A1``，也可以是完整的 ``sheet_id!A1``。
        读取空单元格时返回 ``None``。
        """
        rows = self.get_rows(
            range=cell,
            sheet_id=sheet_id,
            sheet_name=sheet_name,
            value_render_option=value_render_option,
            date_time_render_option=date_time_render_option,
            user_id_type=user_id_type,
        )
        if not rows or not rows[0]:
            return None
        return rows[0][0]

    def get_records(
        self,
        range: str | None = None,
        *,
        sheet_id: str | None = None,
        sheet_name: str | None = None,
        cell_range: str | None = None,
        header_row_index: int = 0,
        skip_empty_rows: bool = True,
        value_render_option: str | None = None,
        date_time_render_option: str | None = None,
        user_id_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """按表头行把二维数据解析为 ``list[dict]``。

        依赖读取单个范围接口:
        https://open.feishu.cn/document/server-docs/docs/sheets-v3/data-operation/reading-a-single-range

        默认使用读取范围内的第一行作为表头。空表头会命名为
        ``column_1``、``column_2``；重复表头会追加 ``_2``、``_3``。
        本函数只做轻量解析，不改变飞书返回的单元格值类型。
        """
        rows = self.get_rows(
            range=range,
            sheet_id=sheet_id,
            sheet_name=sheet_name,
            cell_range=cell_range,
            value_render_option=value_render_option,
            date_time_render_option=date_time_render_option,
            user_id_type=user_id_type,
        )
        if not rows:
            return []
        if header_row_index < 0 or header_row_index >= len(rows):
            raise ValueError(f"header_row_index 超出范围: {header_row_index}, rows_count: {len(rows)}")

        headers = _normalize_headers(rows[header_row_index])
        records: list[dict[str, Any]] = []
        for row in rows[header_row_index + 1:]:
            if skip_empty_rows and _is_empty_row(row):
                continue
            if len(row) > len(headers):
                headers = _extend_headers(headers, len(row))
            records.append({header: row[index] if index < len(row) else None for index, header in enumerate(headers)})
        return records

    def batch_get_values(
        self,
        ranges: list[str],
        *,
        value_render_option: str | None = None,
        date_time_render_option: str | None = None,
        user_id_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """读取多个官方 range，返回官方 valueRanges。

        https://open.feishu.cn/document/ukTMukTMukTM/ukTMzUjL5EzM14SOxMTN
        ranges 必须是完整官方 range，例如 ``["sheet1!A1:B2"]``。
        """
        if not ranges:
            return []
        params = _clean_params({
            "ranges": ",".join(ranges),
            "valueRenderOption": value_render_option,
            "dateTimeRenderOption": date_time_render_option,
            "user_id_type": user_id_type,
        })
        url = f"/sheets/v2/spreadsheets/{self.spreadsheet_token}/values_batch_get"
        return self.feishu_api.request("GET", url, params=params).get('valueRanges') or []

    def update_values(
        self,
        range: str | None = None,
        values: list[list[Any]] | None = None,
        *,
        sheet_id: str | None = None,
        sheet_name: str | None = None,
        cell_range: str | None = None,
    ) -> dict[str, Any]:
        """向单个范围写入数据。若指定范围内已有数据，将被覆盖。

        https://open.feishu.cn/document/server-docs/docs/sheets-v3/data-operation/write-data-to-a-single-range
        如果传入单个起始单元格，例如 ``A1``，会按 values 的行列数自动扩展为矩形范围。
        返回飞书官方更新结果，通常包含 updatedRange / updatedRows / updatedCells。
        """
        if values is None:
            raise ValueError("values 不能为空")
        resolved_range = self._resolve_range(
            range=range,
            sheet_id=sheet_id,
            sheet_name=sheet_name,
            cell_range=cell_range,
            values=values,
            expand_write_range=True,
        )
        url = f"/sheets/v2/spreadsheets/{self.spreadsheet_token}/values"
        body = {"valueRange": {"range": resolved_range, "values": values}}
        return self.feishu_api.request("PUT", url, body=body)

    def batch_update_values(self, value_ranges: list[dict[str, Any]] | list[tuple[str, list[list[Any]]]]) -> dict[str, Any]:
        """向多个官方 range 写入数据。

        官方文档入口:
        https://open.feishu.cn/document/ukTMukTMukTM/uATMzUjLwEzM14CMxMTN/overview

        value_ranges 支持官方结构 ``[{"range": ..., "values": ...}]``，也支持
        ``[(range, values), ...]`` 的简写形式。
        """
        url = f"/sheets/v2/spreadsheets/{self.spreadsheet_token}/values_batch_update"
        body = {"valueRanges": [normalize_value_range(v) for v in value_ranges]}
        return self.feishu_api.request("POST", url, body=body)

    def append_values(
        self,
        range: str | None = None,
        values: list[list[Any]] | None = None,
        *,
        sheet_id: str | None = None,
        sheet_name: str | None = None,
        cell_range: str | None = None,
        insert_data_option: str | None = None,
    ) -> dict[str, Any]:
        """在指定范围的第一个空白位置追加数据。

        https://open.feishu.cn/document/server-docs/docs/sheets-v3/data-operation/append-data

        insert_data_option 可选 ``OVERWRITE`` 或 ``INSERT_ROWS``。
        """
        if values is None:
            raise ValueError("values 不能为空")
        resolved_range = self._resolve_range(
            range=range,
            sheet_id=sheet_id,
            sheet_name=sheet_name,
            cell_range=cell_range,
            normalize_single_cell=True,
        )
        params = {"insertDataOption": insert_data_option} if insert_data_option else None
        url = f"/sheets/v2/spreadsheets/{self.spreadsheet_token}/values_append"
        body = {"valueRange": {"range": resolved_range, "values": values}}
        return self.feishu_api.request("POST", url, params=params, body=body)

    def prepend_values(
        self,
        range: str | None = None,
        values: list[list[Any]] | None = None,
        *,
        sheet_id: str | None = None,
        sheet_name: str | None = None,
        cell_range: str | None = None,
    ) -> dict[str, Any]:
        """在指定范围的起始位置上方插入行，并写入数据。

        https://open.feishu.cn/document/server-docs/docs/sheets-v3/data-operation/prepend-data
        """
        if values is None:
            raise ValueError("values 不能为空")
        resolved_range = self._resolve_range(
            range=range,
            sheet_id=sheet_id,
            sheet_name=sheet_name,
            cell_range=cell_range,
            normalize_single_cell=True,
        )
        url = f"/sheets/v2/spreadsheets/{self.spreadsheet_token}/values_prepend"
        body = {"valueRange": {"range": resolved_range, "values": values}}
        return self.feishu_api.request("POST", url, body=body)

    def find_values(
        self,
        find: str,
        *,
        sheet_id: str | None = None,
        sheet_name: str | None = None,
        range: str | None = None,
        cell_range: str | None = None,
        match_case: bool = True,
        match_entire_cell: bool = False,
        search_by_regex: bool = False,
        include_formulas: bool = False,
    ) -> dict[str, Any]:
        """在指定工作表中查找单元格内容。

        https://open.feishu.cn/document/ukTMukTMukTM/uUDN04SN0QjL1QDN/sheets-v3/spreadsheet-sheet/find

        如果不传 ``range`` 或 ``cell_range``，则在整张工作表中查找。
        返回飞书官方查找结果 dict。
        """
        resolved_sheet_id = self._resolve_sheet_id_for_range_operation(
            sheet_id=sheet_id,
            sheet_name=sheet_name,
            range=range,
        )
        resolved_range = self._resolve_sheet_operation_range(
            resolved_sheet_id=resolved_sheet_id,
            range=range,
            cell_range=cell_range,
        )
        url = f"/sheets/v3/spreadsheets/{self.spreadsheet_token}/sheets/{resolved_sheet_id}/find"
        body = {
            "find": find,
            "find_condition": {
                "range": resolved_range,
                "match_case": match_case,
                "match_entire_cell": match_entire_cell,
                "search_by_regex": search_by_regex,
                "include_formulas": include_formulas,
            },
        }
        return self.feishu_api.request("POST", url, body=body)

    def replace_values(
        self,
        find: str,
        replacement: str,
        *,
        sheet_id: str | None = None,
        sheet_name: str | None = None,
        range: str | None = None,
        cell_range: str | None = None,
        match_case: bool = False,
        match_entire_cell: bool = False,
        search_by_regex: bool = False,
        include_formulas: bool = False,
    ) -> dict[str, Any]:
        """在指定工作表中查找并替换单元格内容。

        https://open.feishu.cn/document/server-docs/docs/sheets-v3/data-operation/replace

        如果不传 ``range`` 或 ``cell_range``，则在整张工作表中替换。
        返回飞书官方替换结果 dict。
        """
        resolved_sheet_id = self._resolve_sheet_id_for_range_operation(
            sheet_id=sheet_id,
            sheet_name=sheet_name,
            range=range,
        )
        resolved_range = self._resolve_sheet_operation_range(
            resolved_sheet_id=resolved_sheet_id,
            range=range,
            cell_range=cell_range,
        )
        url = f"/sheets/v3/spreadsheets/{self.spreadsheet_token}/sheets/{resolved_sheet_id}/replace"
        body = {
            "find": find,
            "replacement": replacement,
            "find_condition": {
                "range": resolved_range,
                "match_case": match_case,
                "match_entire_cell": match_entire_cell,
                "search_by_regex": search_by_regex,
                "include_formulas": include_formulas,
            },
        }
        return self.feishu_api.request("POST", url, body=body)

    def _resolve_sheet_id_for_range_operation(
        self,
        *,
        sheet_id: str | None = None,
        sheet_name: str | None = None,
        range: str | None = None,
    ) -> str:
        split = split_sheet_range(range) if range else None
        if sheet_id or sheet_name:
            resolved_sheet_id = self.resolve_sheet_id(sheet_id=sheet_id, sheet_name=sheet_name)
            if split and split[0] != resolved_sheet_id:
                raise ValueError(f"range 中的 sheet_id {split[0]} 与目标 sheet_id {resolved_sheet_id} 不一致")
            return resolved_sheet_id
        if split:
            return split[0]
        return self.resolve_sheet_id()

    def _resolve_sheet_operation_range(
        self,
        *,
        resolved_sheet_id: str,
        range: str | None = None,
        cell_range: str | None = None,
    ) -> str:
        if not range and not cell_range:
            return resolved_sheet_id
        if range:
            split = split_sheet_range(range)
            if split and split[0] != resolved_sheet_id:
                raise ValueError(f"range 中的 sheet_id {split[0]} 与目标 sheet_id {resolved_sheet_id} 不一致")
            if split:
                return normalize_point_range(normalize_range_separators(range))
        return self._resolve_range(
            range=range,
            sheet_id=resolved_sheet_id,
            cell_range=cell_range,
            normalize_single_cell=True,
        )

    def _resolve_range(
        self,
        *,
        range: str | None = None,
        sheet_id: str | None = None,
        sheet_name: str | None = None,
        cell_range: str | None = None,
        normalize_single_cell: bool = False,
        values: list[list[Any]] | None = None,
        expand_write_range: bool = False,
    ) -> str:
        if range is not None and cell_range is not None:
            raise ValueError("range 和 cell_range 不能同时传入")

        if range is not None:
            raw_range = normalize_range_separators(range)
            if not raw_range:
                raise ValueError("range 不能为空")
            if split_sheet_range(raw_range):
                if sheet_id or sheet_name:
                    raise ValueError("传入完整 range 时，不能同时传 sheet_id 或 sheet_name")
                resolved_range = raw_range
            else:
                if looks_like_relative_range(raw_range):
                    resolved_sheet_id = self.resolve_sheet_id(sheet_id=sheet_id, sheet_name=sheet_name)
                    resolved_range = f"{resolved_sheet_id}!{raw_range}"
                elif sheet_id or sheet_name:
                    raise ValueError("range 看起来不是单元格范围，不能同时传 sheet_id 或 sheet_name")
                else:
                    resolved_range = raw_range
        else:
            resolved_sheet_id = self.resolve_sheet_id(sheet_id=sheet_id, sheet_name=sheet_name)
            if cell_range:
                resolved_range = f"{resolved_sheet_id}!{normalize_range_separators(cell_range)}"
            else:
                resolved_range = resolved_sheet_id

        if expand_write_range:
            if values is None:
                raise ValueError("values 不能为空")
            return normalize_write_range(resolved_range, values)
        if normalize_single_cell:
            return normalize_point_range(resolved_range)
        return resolved_range


def _clean_params(params: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in params.items() if v is not None}


def _normalize_headers(row: list[Any]) -> list[str]:
    headers: list[str] = []
    seen: dict[str, int] = {}
    for index, value in enumerate(row):
        header = str(value).strip() if value is not None else ""
        if not header:
            header = f"column_{index + 1}"
        count = seen.get(header, 0) + 1
        seen[header] = count
        headers.append(header if count == 1 else f"{header}_{count}")
    return headers


def _extend_headers(headers: list[str], length: int) -> list[str]:
    if len(headers) >= length:
        return headers
    headers = headers[:]
    seen = set(headers)
    for index in range(len(headers), length):
        header = f"column_{index + 1}"
        suffix = 2
        while header in seen:
            header = f"column_{index + 1}_{suffix}"
            suffix += 1
        headers.append(header)
        seen.add(header)
    return headers


def _is_empty_row(row: list[Any]) -> bool:
    return all(cell is None or cell == "" for cell in row)
