from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from typing import TypeVar

from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.data_provider.base import DataProvider, ProviderError, UnsupportedCapabilityError
from backend.models import ProviderHealth


T = TypeVar("T")


class AllProvidersFailed(ProviderError):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class FailoverManager:
    def __init__(self, providers: list[DataProvider]) -> None:
        self.providers = providers
        self.settings = get_settings()

    async def execute(
        self,
        session: AsyncSession,
        operation: Callable[[DataProvider], Awaitable[T]],
        on_provider_attempt: Callable[[DataProvider], Awaitable[None]] | None = None,
    ) -> tuple[T, str]:
        errors: list[str] = []
        for provider in self.providers:
            if on_provider_attempt is not None:
                await on_provider_attempt(provider)
            health = await _get_health(session, provider.name)
            if _is_temporarily_unavailable(health):
                errors.append(f"{provider.name}: temporarily unavailable")
                continue
            try:
                result = await operation(provider)
            except UnsupportedCapabilityError as exc:
                errors.append(f"{provider.name}: {exc}")
                continue
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")
                await _mark_failure(session, health, str(exc), self.settings.provider_failure_threshold)
                continue
            await _mark_success(session, health)
            return result, provider.name
        raise AllProvidersFailed(errors)


def _is_temporarily_unavailable(health: ProviderHealth) -> bool:
    if health.status != "unavailable":
        return False
    return health.next_probe_at is not None and health.next_probe_at > datetime.now()


async def _get_health(session: AsyncSession, provider: str) -> ProviderHealth:
    health = await session.get(ProviderHealth, provider)
    if health is not None:
        return health
    health = ProviderHealth(provider=provider, status="available", consecutive_failures=0)
    session.add(health)
    await session.flush()
    return health


async def _mark_success(session: AsyncSession, health: ProviderHealth) -> None:
    health.status = "available"
    health.consecutive_failures = 0
    health.last_success_at = datetime.now()
    health.error_message = None
    health.next_probe_at = None
    await session.commit()


async def _mark_failure(session: AsyncSession, health: ProviderHealth, error: str, threshold: int) -> None:
    health.consecutive_failures += 1
    health.last_failure_at = datetime.now()
    health.error_message = error
    if health.consecutive_failures >= threshold:
        health.status = "unavailable"
        health.next_probe_at = datetime.now() + timedelta(minutes=get_settings().provider_probe_interval_minutes)
    await session.commit()
