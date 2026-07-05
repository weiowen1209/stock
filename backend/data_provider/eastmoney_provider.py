from datetime import date, datetime
from typing import Any

import httpx

from backend.data_provider.base import KLineItem, ProviderError, QuoteData, UnsupportedCapabilityError
from backend.data_provider.utils import eastmoney_sec_id, is_a_share_code, normalize_code, parse_date, to_decimal, to_int


class EastmoneyProvider:
    name = "eastmoney"
    base_url = "https://push2his.eastmoney.com"
    quote_url = "https://push2.eastmoney.com/api/qt/stock/get"

    async def get_realtime_quote(self, code: str) -> QuoteData:
        if normalize_code(code).startswith("US."):
            raise UnsupportedCapabilityError(f"{self.name} does not support US quotes yet")
        params = {
            "secid": eastmoney_sec_id(code),
            "fields": "f43,f44,f45,f46,f47,f48,f49,f57,f58,f60,f116,f170,f168",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(self.quote_url, params=params)
            response.raise_for_status()
        payload = response.json()
        data: dict[str, Any] | None = payload.get("data")
        if not data:
            raise ProviderError(f"{self.name} returned empty quote for {code}")
        return QuoteData(
            code=normalize_code(code),
            price=_scaled_decimal(data.get("f43")),
            change_pct=_scaled_decimal(data.get("f170")),
            turnover_rate=_scaled_decimal(data.get("f168")),
            volume=to_int(data.get("f47")),
            turnover=to_decimal(data.get("f48")),
            market_cap=to_decimal(data.get("f116")),
            source=self.name,
            updated_at=datetime.now(),
        )

    async def get_kline(
        self,
        code: str,
        period: str = "day",
        start: date | None = None,
        end: date | None = None,
    ) -> list[KLineItem]:
        if normalize_code(code).startswith("US."):
            raise UnsupportedCapabilityError(f"{self.name} does not support US kline yet")
        klt = {"day": "101", "week": "102", "month": "103"}.get(period)
        if klt is None:
            raise ProviderError(f"unsupported period: {period}")
        params = {
            "secid": eastmoney_sec_id(code),
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": klt,
            "fqt": "1",
            "beg": start.strftime("%Y%m%d") if start else "19900101",
            "end": end.strftime("%Y%m%d") if end else "20500101",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{self.base_url}/api/qt/stock/kline/get", params=params)
            response.raise_for_status()
        payload = response.json()
        data = payload.get("data") or {}
        rows = data.get("klines") or []
        if not rows:
            raise ProviderError(f"{self.name} returned empty kline for {code}")
        return [_parse_kline_row(normalize_code(code), period, row, self.name) for row in rows]


def _scaled_decimal(value: Any):
    raw = to_decimal(value)
    if raw is None:
        return None
    return raw / 100


def _parse_kline_row(code: str, period: str, row: str, source: str) -> KLineItem:
    parts = row.split(",")
    return KLineItem(
        code=code,
        period=period,
        date=parse_date(parts[0]),
        open=to_decimal(parts[1]),
        close=to_decimal(parts[2]),
        high=to_decimal(parts[3]),
        low=to_decimal(parts[4]),
        volume=to_int(parts[5]),
        turnover=to_decimal(parts[6]),
        change_pct=to_decimal(parts[8]),
        source=source,
    )
