from datetime import date, datetime
from typing import Any

import httpx

from backend.data_provider.base import KLineItem, ProviderError, QuoteData, UnsupportedCapabilityError
from backend.data_provider.utils import normalize_code, parse_date, to_decimal, to_int


class TencentProvider:
    name = "tencent"
    base_url = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"

    async def get_realtime_quote(self, code: str) -> QuoteData:
        raise UnsupportedCapabilityError(f"{self.name} only provides kline data")

    async def get_kline(
        self,
        code: str,
        period: str = "day",
        start: date | None = None,
        end: date | None = None,
    ) -> list[KLineItem]:
        normalized = normalize_code(code)
        symbol = _tencent_symbol(normalized)
        if symbol is None:
            raise UnsupportedCapabilityError(f"{self.name} does not support {normalized}")
        tencent_period = {"day": "day", "week": "week", "month": "month"}.get(period)
        if tencent_period is None:
            raise ProviderError(f"unsupported period: {period}")
        count = {"day": "640", "week": "320", "month": "120"}.get(period, "640")
        start_str = start.strftime("%Y-%m-%d") if start else "1990-01-01"
        param = f"{symbol},{tencent_period},{start_str},,{count},qfq"
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                self.base_url,
                params={"param": param},
                headers={"Referer": "https://gu.qq.com/"},
            )
            response.raise_for_status()
        payload = response.json()
        data = payload.get("data") or {}
        stock_key = list(data.keys())[0] if data else ""
        stock_data = data.get(stock_key) or {}
        kline_key = f"qfq{tencent_period}" if tencent_period != "day" else "qfqday"
        raw_rows = stock_data.get(kline_key) or stock_data.get(tencent_period) or []
        if not raw_rows:
            raise ProviderError(f"{self.name} returned empty kline for {code}")
        rows: list[KLineItem] = []
        for item in raw_rows:
            parsed = _parse_tencent_row(normalized, period, item)
            if parsed is not None:
                if end and parsed.date > end:
                    continue
                rows.append(parsed)
        if not rows:
            raise ProviderError(f"{self.name} returned empty kline for {code}")
        return rows


def _tencent_symbol(normalized: str) -> str | None:
    """将内部代码转换为腾讯财经格式。

    港股 HK00700 -> hk00700
    美股 US.AAPL -> usAAPL.OQ (纳斯达克) / usAAPL.NY (纽约)
    """
    if normalized.startswith("HK") and normalized[2:].isdigit():
        return f"hk{normalized[2:]}"
    if normalized.startswith("US."):
        ticker = normalized[3:]
        return f"us{ticker}.OQ"
    return None


def _parse_tencent_row(code: str, period: str, item: Any) -> KLineItem | None:
    if not isinstance(item, (list, tuple)) or len(item) < 6:
        return None
    return KLineItem(
        code=code,
        period=period,
        date=parse_date(str(item[0])),
        open=to_decimal(item[1]),
        close=to_decimal(item[2]),
        high=to_decimal(item[3]),
        low=to_decimal(item[4]),
        volume=to_int(item[5]),
        turnover=to_decimal(item[6]) if len(item) > 6 and not isinstance(item[6], dict) else None,
        source="tencent",
    )
