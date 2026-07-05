from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol


@dataclass(slots=True)
class QuoteData:
    code: str
    price: Decimal | None = None
    change_pct: Decimal | None = None
    turnover_rate: Decimal | None = None
    volume: int | None = None
    turnover: Decimal | None = None
    market_cap: Decimal | None = None
    source: str = "unknown"
    updated_at: datetime | None = None


@dataclass(slots=True)
class KLineItem:
    code: str
    period: str
    date: date
    open: Decimal | None = None
    close: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    volume: int | None = None
    turnover: Decimal | None = None
    change_pct: Decimal | None = None
    source: str = "unknown"


class DataProvider(Protocol):
    name: str

    async def get_realtime_quote(self, code: str) -> QuoteData:
        ...

    async def get_kline(
        self,
        code: str,
        period: str = "day",
        start: date | None = None,
        end: date | None = None,
    ) -> list[KLineItem]:
        ...


class ProviderError(RuntimeError):
    pass


class UnsupportedCapabilityError(ProviderError):
    pass
