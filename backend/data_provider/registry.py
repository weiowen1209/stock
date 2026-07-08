from backend.data_provider.base import DataProvider
from backend.data_provider.eastmoney_provider import EastmoneyProvider
from backend.data_provider.sina_provider import SinaProvider
from backend.data_provider.stooq_provider import StooqProvider
from backend.data_provider.tencent_provider import TencentProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, DataProvider] = {
            "sina": SinaProvider(),
            "eastmoney": EastmoneyProvider(),
            "tencent": TencentProvider(),
            "stooq": StooqProvider(),
        }
        self._chains: dict[str, list[str]] = {
            "quote": ["sina", "eastmoney", "stooq"],
            "kline": ["sina", "eastmoney", "tencent", "stooq"],
        }

    def get(self, name: str) -> DataProvider:
        return self._providers[name]

    def chain_for(self, data_type: str) -> list[DataProvider]:
        return [self._providers[name] for name in self._chains.get(data_type, [])]

    def registered_names(self) -> list[str]:
        return list(self._providers.keys())


registry = ProviderRegistry()
