import asyncio
from datetime import date, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.data_provider.base import KLineItem, QuoteData
from backend.data_provider.failover_manager import AllProvidersFailed, FailoverManager, ProviderAttempt, persist_provider_attempts
from backend.data_provider.registry import registry
from backend.models import KLineData, ProviderHealth, RealtimeQuote, Stock, SyncLog
from backend.schemas.market import SyncResult
from backend.sync.progress import progress_hub


async def sync_quotes(session: AsyncSession, codes: list[str]) -> SyncResult:
    records_count = 0
    errors: list[str] = []
    total_codes = len(codes)
    total = max(total_codes, 1)
    settings = get_settings()
    await progress_hub.publish("quotes", f"第1步：准备同步实时行情，共 {total_codes} 只股票", percent=5, current=0, total=total_codes)

    manager = FailoverManager(registry.chain_for("quote"))
    health_map = await _load_provider_health_map(session, [provider.name for provider in manager.providers])
    semaphore = asyncio.Semaphore(max(1, settings.sync_concurrency))

    async def fetch_one(index: int, code: str) -> tuple[str, QuoteData | None, str | None, str | None, list[ProviderAttempt]]:
        base_percent = 5 + int(index / total * 35)
        await progress_hub.publish(
            "quotes",
            f"第2步：同步 {code} 实时行情（{index + 1}/{total_codes}）",
            code=code,
            percent=base_percent,
            current=index + 1,
            total=total_codes,
        )
        attempts: list[ProviderAttempt] = []
        async with semaphore:
            try:
                quote, provider_name = await manager.execute_with_health_map(
                    health_map,
                    lambda provider, stock_code=code: provider.get_realtime_quote(stock_code),
                    lambda provider, stock_code=code, progress=base_percent: progress_hub.publish(
                        "quotes",
                        f"第1步：连接 {provider.name} 数据源，拉取 {stock_code} 实时行情",
                        provider=provider.name,
                        code=stock_code,
                        percent=progress,
                        current=index + 1,
                        total=total_codes,
                    ),
                    attempts=attempts,
                )
                return code, quote, provider_name, None, attempts
            except AllProvidersFailed as exc:
                return code, None, None, f"{code}: {exc}", attempts

    results = await asyncio.gather(*(fetch_one(index, code) for index, code in enumerate(codes)))

    for completed, (code, quote, provider_name, error, attempts) in enumerate(results, start=1):
        await progress_hub.publish(
            "quotes",
            f"第2步：实时行情进度 {completed}/{total_codes}",
            provider=provider_name,
            code=code,
            percent=5 + int(completed / total * 35),
            current=completed,
            total=total_codes,
        )
        await persist_provider_attempts(session, attempts, auto_commit=False)
        if error:
            errors.append(error)
            continue
        if quote is None or provider_name is None:
            continue
        source_updated_at = quote.updated_at
        stmt = insert(RealtimeQuote).values(
            code=quote.code,
            price=quote.price,
            change_pct=quote.change_pct,
            turnover_rate=quote.turnover_rate,
            volume=quote.volume,
            turnover=quote.turnover,
            market_cap=quote.market_cap,
            source=provider_name,
            source_updated_at=source_updated_at,
        )
        update_fields = {
            "price": stmt.excluded.price,
            "change_pct": stmt.excluded.change_pct,
            "turnover_rate": stmt.excluded.turnover_rate,
            "volume": stmt.excluded.volume,
            "turnover": stmt.excluded.turnover,
            "market_cap": stmt.excluded.market_cap,
            "source": stmt.excluded.source,
            "source_updated_at": source_updated_at,
        }
        await session.execute(stmt.on_conflict_do_update(index_elements=["code"], set_=update_fields))
        records_count += 1

    await session.commit()
    status = "success" if not errors else "failed" if records_count == 0 else "fallback"
    detail = "; ".join(errors) if errors else "quotes synced"
    await _write_sync_log(session, "realtime", status, records_count, detail)
    await progress_hub.publish(
        "failed" if status == "failed" else "quotes",
        _sync_finish_message("实时行情", status, records_count, total_codes, errors),
        percent=42,
        current=records_count,
        total=total_codes,
    )
    return SyncResult(task_type="realtime", status=status, records_count=records_count, detail=detail)


async def sync_kline(
    session: AsyncSession,
    codes: list[str],
    period: str = "day",
    start: date | None = None,
    end: date | None = None,
    force_full: bool = False,
) -> SyncResult:
    records_count = 0
    errors: list[str] = []
    period_label = _period_label(period)
    total_codes = len(codes)
    total = max(total_codes, 1)
    default_start = start or date(2022, 1, 1)
    settings = get_settings()
    await progress_hub.publish(
        "kline",
        f"第4步：准备同步{period_label}K线，共 {total_codes} 只股票",
        percent=45,
        current=0,
        total=total_codes,
    )

    incremental_starts = await _build_incremental_starts(session, codes, period, default_start, force_full)
    manager = FailoverManager(registry.chain_for("kline"))
    health_map = await _load_provider_health_map(session, [provider.name for provider in manager.providers])
    semaphore = asyncio.Semaphore(max(1, settings.sync_concurrency))

    async def fetch_one(index: int, code: str) -> tuple[str, list[KLineItem] | None, str | None, str | None, list[ProviderAttempt]]:
        base_percent = 45 + int(index / total * 45)
        incremental_start = incremental_starts.get(code, default_start)
        await progress_hub.publish(
            "kline",
            f"第5步：同步 {code} {period_label}K线（{index + 1}/{total_codes}）",
            code=code,
            percent=base_percent,
            current=index + 1,
            total=total_codes,
        )
        attempts: list[ProviderAttempt] = []
        async with semaphore:
            try:
                rows, provider_name = await manager.execute_with_health_map(
                    health_map,
                    lambda provider, stock_code=code, inc_start=incremental_start: provider.get_kline(
                        stock_code, period=period, start=inc_start, end=end
                    ),
                    lambda provider, stock_code=code, progress=base_percent: progress_hub.publish(
                        "kline",
                        f"第4步：连接 {provider.name} 数据源，拉取 {stock_code} {period_label}K线",
                        provider=provider.name,
                        code=stock_code,
                        percent=progress,
                        current=index + 1,
                        total=total_codes,
                    ),
                    attempts=attempts,
                )
                return code, rows, provider_name, None, attempts
            except AllProvidersFailed as exc:
                return code, None, None, f"{code}: {exc}", attempts

    results = await asyncio.gather(*(fetch_one(index, code) for index, code in enumerate(codes)))

    for completed, (code, rows, provider_name, error, attempts) in enumerate(results, start=1):
        await progress_hub.publish(
            "kline",
            f"第5步：{period_label}K线进度 {completed}/{total_codes}",
            provider=provider_name,
            code=code,
            percent=45 + int(completed / total * 45),
            current=completed,
            total=total_codes,
        )
        await persist_provider_attempts(session, attempts, auto_commit=False)
        if error:
            errors.append(error)
            continue
        if not rows or provider_name is None:
            continue
        await _upsert_kline_rows(session, rows, provider_name, batch_size=settings.sync_batch_size)
        records_count += len(rows)

    await session.commit()
    status = "success" if not errors else "failed" if records_count == 0 else "fallback"
    detail = "; ".join(errors) if errors else f"{period} kline synced"
    await _write_sync_log(session, f"kline_{period}", status, records_count, detail)
    failed_count = len(errors)
    await progress_hub.publish(
        "failed" if status == "failed" else "done",
        _sync_finish_message(f"{period_label}K线", status, records_count, total_codes, errors),
        percent=100,
        current=total_codes - failed_count,
        total=total_codes,
    )
    return SyncResult(task_type=f"kline_{period}", status=status, records_count=records_count, detail=detail)


async def _load_provider_health_map(session: AsyncSession, providers: list[str]) -> dict[str, ProviderHealth]:
    if not providers:
        return {}
    existing = {
        item.provider: item
        for item in (await session.execute(select(ProviderHealth).where(ProviderHealth.provider.in_(providers)))).scalars()
    }
    return {
        provider: existing.get(provider, ProviderHealth(provider=provider, status="available", consecutive_failures=0))
        for provider in providers
    }


async def _build_incremental_starts(
    session: AsyncSession,
    codes: list[str],
    period: str,
    default_start: date,
    force_full: bool,
) -> dict[str, date]:
    if not codes:
        return {}
    if force_full:
        return {code: default_start for code in codes}

    result = await session.execute(
        select(
            KLineData.code,
            func.min(KLineData.date),
            func.max(KLineData.date),
            func.count(),
        )
        .where(KLineData.period == period, KLineData.code.in_(codes))
        .group_by(KLineData.code)
    )
    summary = {row[0]: (row[1], row[2], row[3]) for row in result.all()}
    gap_codes = {
        code
        for code, (min_date, _max_date, count) in summary.items()
        if count == 0 or min_date is None or min_date > default_start
    }

    starts: dict[str, date] = {}
    overlap_days = 7 if period == "day" else 30 if period == "week" else 60
    for code in codes:
        min_date, max_date, count = summary.get(code, (None, None, 0))
        if count == 0 or max_date is None or code in gap_codes:
            starts[code] = default_start
            continue
        starts[code] = max_date - timedelta(days=overlap_days)
    return starts


async def _upsert_kline_rows(
    session: AsyncSession,
    rows: list[KLineItem],
    provider_name: str,
    *,
    batch_size: int,
) -> None:
    if not rows:
        return
    safe_batch_size = max(1, batch_size)
    for offset in range(0, len(rows), safe_batch_size):
        chunk = rows[offset:offset + safe_batch_size]
        values = [
            {
                "code": item.code,
                "period": item.period,
                "date": item.date,
                "open": item.open,
                "close": item.close,
                "high": item.high,
                "low": item.low,
                "volume": item.volume,
                "turnover": item.turnover,
                "change_pct": item.change_pct,
                "source": provider_name,
            }
            for item in chunk
        ]
        stmt = insert(KLineData).values(values)
        update_fields = {
            "open": stmt.excluded.open,
            "close": stmt.excluded.close,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "volume": stmt.excluded.volume,
            "turnover": stmt.excluded.turnover,
            "change_pct": stmt.excluded.change_pct,
            "source": stmt.excluded.source,
        }
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=["code", "period", "date"],
                set_=update_fields,
            )
        )
        await session.flush()


def _period_label(period: str) -> str:
    return {"day": "日线", "week": "周线", "month": "月线"}.get(period, period)


def _sync_finish_message(label: str, status: str, records_count: int, total_codes: int, errors: list[str]) -> str:
    if status == "failed" and _all_errors_are_unavailable(errors):
        return f"数据源不可用：{label}同步失败，当前没有可用数据源，请稍后重试或切换数据源"
    failed_count = len(errors)
    return f"{label}同步完成，成功 {total_codes - failed_count}/{total_codes} 只股票，写入 {records_count} 条记录"


def _all_errors_are_unavailable(errors: list[str]) -> bool:
    return bool(errors) and all("temporarily unavailable" in error for error in errors)


async def default_stock_codes(session: AsyncSession) -> list[str]:
    result = await session.execute(select(Stock.code).where(Stock.is_active.is_(True)).order_by(Stock.code))
    return list(result.scalars().all())


async def latest_sync_logs(session: AsyncSession, limit: int = 10) -> list[SyncLog]:
    result = await session.execute(select(SyncLog).order_by(desc(SyncLog.created_at)).limit(limit))
    return list(result.scalars().all())


async def list_provider_health(session: AsyncSession) -> list[ProviderHealth]:
    result = await session.execute(select(ProviderHealth).order_by(ProviderHealth.provider))
    return list(result.scalars().all())


async def list_registered_provider_health(session: AsyncSession) -> list[ProviderHealth]:
    names = registry.registered_names() if hasattr(registry, "registered_names") else []
    existing = {
        item.provider: item
        for item in (await session.execute(select(ProviderHealth).where(ProviderHealth.provider.in_(names)))).scalars()
    }
    rows: list[ProviderHealth] = []
    for name in names:
        health = existing.get(name)
        if health is None:
            health = ProviderHealth(provider=name, status="available", consecutive_failures=0)
            session.add(health)
            await session.flush()
        rows.append(health)
    return rows


async def _write_sync_log(
    session: AsyncSession,
    task_type: str,
    status: str,
    records_count: int,
    detail: str,
) -> None:
    session.add(
        SyncLog(
            task_type=task_type,
            status=status,
            records_count=records_count,
            detail=detail,
        )
    )
    await session.commit()
