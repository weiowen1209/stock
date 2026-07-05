from datetime import date, datetime

import httpx

from backend.data_provider.base import KLineItem, ProviderError, QuoteData, UnsupportedCapabilityError
from backend.data_provider.utils import normalize_code, parse_date, to_decimal, to_int


class StooqProvider:
    name = "stooq"
    quote_url = "https://stooq.com/q/l/"
    kline_url = "https://stooq.com/q/d/l/"

    async def get_realtime_quote(self, code: str) -> QuoteData:
        symbol = _stooq_symbol(code)
        params = {"s": symbol, "f": "sd2t2ohlcv", "h": "", "e": "csv"}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(self.quote_url, params=params)
            response.raise_for_status()
        lines = [line for line in response.text.splitlines() if line.strip()]
        if len(lines) < 2:
            raise ProviderError(f"{self.name} returned empty quote for {code}")
        values = lines[1].split(",")
        if len(values) < 8 or values[6] in {"N/D", ""}:
            raise ProviderError(f"{self.name} returned invalid quote for {code}")
        previous_close = to_decimal(values[3])
        price = to_decimal(values[6])
        change_pct = None
        if previous_close and price is not None and previous_close != 0:
            change_pct = ((price - previous_close) / previous_close * 100).quantize(to_decimal("0.01"))
        return QuoteData(
            code=normalize_code(code),
            price=price,
            change_pct=change_pct,
            volume=to_int(values[7]),
            source=self.name,
            updated_at=_parse_stooq_datetime(values[1], values[2]),
        )

    async def get_kline(
        self,
        code: str,
        period: str = "day",
        start: date | None = None,
        end: date | None = None,
    ) -> list[KLineItem]:
        if period != "day":
            raise UnsupportedCapabilityError(f"{self.name} only supports day kline")
        params = {"s": _stooq_symbol(code), "i": "d", "d1": _date_param(start), "d2": _date_param(end)}
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(self.kline_url, params=params)
            response.raise_for_status()
        lines = [line for line in response.text.splitlines() if line.strip()]
        if len(lines) < 2 or lines[0].startswith("No data"):
            raise ProviderError(f"{self.name} returned empty kline for {code}")
        rows: list[KLineItem] = []
        normalized = normalize_code(code)
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) < 6:
                continue
            rows.append(
                KLineItem(
                    code=normalized,
                    period=period,
                    date=parse_date(parts[0]),
                    open=to_decimal(parts[1]),
                    high=to_decimal(parts[2]),
                    low=to_decimal(parts[3]),
                    close=to_decimal(parts[4]),
                    volume=to_int(parts[5]),
                    source=self.name,
                )
            )
        if not rows:
            raise ProviderError(f"{self.name} returned empty kline for {code}")
        return rows


def _stooq_symbol(code: str) -> str:
    normalized = normalize_code(code)
    if normalized.startswith("US."):
        return normalized[3:].lower() + ".us"
    raise UnsupportedCapabilityError(f"stooq does not support {normalized}")


def _date_param(value: date | None) -> str:
    return value.strftime("%Y%m%d") if value else "19900101"


def _parse_stooq_datetime(day: str, clock: str) -> datetime | None:
    try:
        return datetime.strptime(f"{day} {clock}", "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None
