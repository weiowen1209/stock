import json
from datetime import date, datetime
from typing import Any

import httpx

from backend.data_provider.base import KLineItem, ProviderError, QuoteData, UnsupportedCapabilityError
from backend.data_provider.utils import is_a_share_code, normalize_code, parse_date, to_decimal, to_int


class SinaProvider:
    name = "sina"
    quote_url = "https://hq.sinajs.cn/list={symbol}"
    kline_url = "https://quotes.sina.cn/cn/api/json_v2.php/CN_MarketData.getKLineData"

    async def get_realtime_quote(self, code: str) -> QuoteData:
        async with httpx.AsyncClient(timeout=10, headers={"Referer": "https://finance.sina.com.cn"}) as client:
            response = await client.get(self.quote_url.format(symbol=_sina_symbol(code)))
            response.raise_for_status()
        return parse_sina_quote_payload(code, response.text)

    async def get_kline(
        self,
        code: str,
        period: str = "day",
        start: date | None = None,
        end: date | None = None,
    ) -> list[KLineItem]:
        scale = {"day": 240, "week": 1200, "month": 7200}.get(period)
        if scale is None:
            raise ProviderError(f"unsupported period: {period}")
        params = {"symbol": _sina_symbol(code), "scale": scale, "ma": "no", "datalen": 1023}
        async with httpx.AsyncClient(timeout=10, headers={"Referer": "https://finance.sina.com.cn"}) as client:
            response = await client.get(self.kline_url, params=params)
            response.raise_for_status()
        rows = parse_sina_kline_payload(code, period, response.text)
        if start:
            rows = [item for item in rows if item.date >= start]
        if end:
            rows = [item for item in rows if item.date <= end]
        return rows


def parse_sina_quote_payload(code: str, payload: str) -> QuoteData:
    raw = _extract_quoted_value(payload)
    parts = raw.split(",")
    if len(parts) < 32 or not parts[0]:
        raise ProviderError(f"sina returned empty quote for {code}")
    previous_close = to_decimal(parts[2])
    price = to_decimal(parts[3])
    change_pct = None
    if previous_close and price is not None and previous_close != 0:
        change_pct = ((price - previous_close) / previous_close * 100).quantize(to_decimal("0.01"))
    return QuoteData(
        code=normalize_code(code),
        price=price,
        change_pct=change_pct,
        volume=to_int(parts[8]),
        turnover=to_decimal(parts[9]),
        source="sina",
        updated_at=_parse_quote_datetime(parts[30], parts[31]),
    )


def parse_sina_kline_payload(code: str, period: str, payload: str) -> list[KLineItem]:
    raw = payload.split("=", 1)[1] if "=" in payload else payload
    rows: list[dict[str, Any]] = json.loads(raw.strip().rstrip(";"))
    if not rows:
        raise ProviderError(f"sina returned empty kline for {code}")
    normalized = normalize_code(code)
    return [
        KLineItem(
            code=normalized,
            period=period,
            date=parse_date(str(item.get("day") or item.get("date"))),
            open=to_decimal(item.get("open")),
            close=to_decimal(item.get("close")),
            high=to_decimal(item.get("high")),
            low=to_decimal(item.get("low")),
            volume=to_int(item.get("volume")),
            source="sina",
        )
        for item in rows
    ]


def _sina_symbol(code: str) -> str:
    normalized = normalize_code(code)
    if not is_a_share_code(normalized):
        raise UnsupportedCapabilityError(f"sina does not support {normalized}")
    prefix = "sh" if normalized.startswith(("6", "9")) else "sz"
    return f"{prefix}{normalized}"


def _extract_quoted_value(payload: str) -> str:
    if '"' not in payload:
        raise ProviderError("sina returned invalid quote payload")
    return payload.split('"', 2)[1]


def _parse_quote_datetime(day: str, clock: str) -> datetime | None:
    try:
        return datetime.strptime(f"{day} {clock}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
