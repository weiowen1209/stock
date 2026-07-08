from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.data_provider.base import DataProvider, ProviderError, UnsupportedCapabilityError
from backend.models import ProviderHealth


T = TypeVar("T")


@dataclass(slots=True)
class ProviderAttempt:
    provider: str
    success: bool
    error: str | None = None


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
        *,
        auto_commit: bool = True,
    ) -> tuple[T, str]:
        attempts: list[ProviderAttempt] = []
        health_map = await _load_health_map(session, [provider.name for provider in self.providers])
        return await self.execute_with_health_map(
            health_map,
            operation,
            on_provider_attempt=on_provider_attempt,
            attempts=attempts,
        )

    async def execute_with_health_map(
        self,
        health_map: dict[str, ProviderHealth],
        operation: Callable[[DataProvider], Awaitable[T]],
        on_provider_attempt: Callable[[DataProvider], Awaitable[None]] | None = None,
        *,
        attempts: list[ProviderAttempt] | None = None,
    ) -> tuple[T, str]:
        errors: list[str] = []
        attempt_log = attempts if attempts is not None else []
        for provider in self.providers:
            if on_provider_attempt is not None:
                await on_provider_attempt(provider)
            health = health_map.get(provider.name)
            if health is None:
                health = ProviderHealth(provider=provider.name, status="available", consecutive_failures=0)
                health_map[provider.name] = health
            if _is_temporarily_unavailable(health):
                errors.append(f"{provider.name}: temporarily unavailable")
                attempt_log.append(ProviderAttempt(provider=provider.name, success=False, error="temporarily unavailable"))
                continue
            try:
                result = await operation(provider)
            except UnsupportedCapabilityError as exc:
                errors.append(f"{provider.name}: {exc}")
                attempt_log.append(ProviderAttempt(provider=provider.name, success=False, error=str(exc)))
                continue
            except Exception as exc:
                errors.append(f"{provider.name}: {exc}")
                attempt_log.append(ProviderAttempt(provider=provider.name, success=False, error=str(exc)))
                continue
            attempt_log.append(ProviderAttempt(provider=provider.name, success=True, error=None))
            return result, provider.name
        raise AllProvidersFailed(errors)


def _is_temporarily_unavailable(health: ProviderHealth) -> bool:
    if health.status != "unavailable":
        return False
    return health.next_probe_at is not None and health.next_probe_at > datetime.now()


async def _load_health_map(session: AsyncSession, providers: list[str]) -> dict[str, ProviderHealth]:
    if not providers:
        return {}
    existing = {
        item.provider: item
        for item in (await session.execute(select(ProviderHealth).where(ProviderHealth.provider.in_(providers)))).scalars()
    }
    health_map: dict[str, ProviderHealth] = {}
    for provider in providers:
        health_map[provider] = existing.get(
            provider,
            ProviderHealth(provider=provider, status="available", consecutive_failures=0),
        )
    return health_map


async def persist_provider_attempts(
    session: AsyncSession,
    attempts: list[ProviderAttempt],
    *,
    auto_commit: bool = True,
) -> None:
    if not attempts:
        return
    latest_attempts = {attempt.provider: attempt for attempt in attempts}
    health_map = await _load_health_map(session, list(latest_attempts))
    existing_names = set((await session.execute(select(ProviderHealth.provider).where(ProviderHealth.provider.in_(latest_attempts)))).scalars())
    for provider, attempt in latest_attempts.items():
        health = health_map[provider]
        if provider not in existing_names:
            session.add(health)
            await session.flush()
            existing_names.add(provider)
        if attempt.success:
            await _mark_success(session, health, auto_commit=False)
        else:
            await _mark_failure(
                session,
                health,
                attempt.error or "unknown error",
                get_settings().provider_failure_threshold,
                auto_commit=False,
            )
    if auto_commit:
        await session.commit()


async def _mark_success(session: AsyncSession, health: ProviderHealth, *, auto_commit: bool = True) -> None:
    health.status = "available"
    health.consecutive_failures = 0
    health.last_success_at = datetime.now()
    health.error_message = None
    health.next_probe_at = None
    if auto_commit:
        await session.commit()
    else:
        await session.flush()


async def _mark_failure(
    session: AsyncSession,
    health: ProviderHealth,
    error: str,
    threshold: int,
    *,
    auto_commit: bool = True,
) -> None:
    health.consecutive_failures += 1
    health.last_failure_at = datetime.now()
    health.error_message = error
    if health.consecutive_failures >= threshold:
        health.status = "unavailable"
        health.next_probe_at = datetime.now() + timedelta(minutes=get_settings().provider_probe_interval_minutes)
    if auto_commit:
        await session.commit()
    else:
        await session.flush()
