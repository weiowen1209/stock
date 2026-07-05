from datetime import date

from backend.data_provider.base import KLineItem, QuoteData, UnsupportedCapabilityError
from backend.data_provider.eastmoney_provider import EastmoneyProvider


class AKShareProvider:
    name = "akshare"

    def __init__(self) -> None:
        self._fallback = EastmoneyProvider()

    async def get_realtime_quote(self, code: str) -> QuoteData:
        data = await self._fallback.get_realtime_quote(code)
        data.source = self.name
        return data

    async def get_kline(
        self,
        code: str,
        period: str = "day",
        start: date | None = None,
        end: date | None = None,
    ) -> list[KLineItem]:
        data = await self._fallback.get_kline(code, period=period, start=start, end=end)
        for item in data:
            item.source = self.name
        return data

    async def get_fundamentals(self, code: str):
        raise UnsupportedCapabilityError(f"{self.name} fundamentals are not implemented in stage 2")
