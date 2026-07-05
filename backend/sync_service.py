from datetime import date

from sqlalchemy import desc, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.data_provider.failover_manager import AllProvidersFailed, FailoverManager
from backend.data_provider.registry import registry
from backend.models import KLineData, ProviderHealth, RealtimeQuote, Stock, SyncLog
from backend.schemas.market import SyncResult
from backend.sync.progress import progress_hub


async def sync_quotes(session: AsyncSession, codes: list[str]) -> SyncResult:
    manager = FailoverManager(registry.chain_for("quote"))
    records_count = 0
    errors: list[str] = []
    total = max(len(codes), 1)
    await progress_hub.publish("quotes", f"第1步：准备同步实时行情，共 {len(codes)} 只股票", percent=5, current=0, total=len(codes))
    for index, code in enumerate(codes, start=1):
        await progress_hub.publish(
            "quotes",
            f"第2步：同步 {code} 实时行情（{index}/{len(codes)}）",
            code=code,
            percent=5 + int(index / total * 35),
            current=index,
            total=len(codes),
        )
        base_percent = 5 + int((index - 1) / total * 35)
        try:
            quote, provider_name = await manager.execute(
                session,
                lambda provider, stock_code=code: provider.get_realtime_quote(stock_code),
                lambda provider, stock_code=code, progress=base_percent: progress_hub.publish(
                    "quotes",
                    f"第1步：连接 {provider.name} 数据源，拉取 {stock_code} 实时行情",
                    provider=provider.name,
                    code=stock_code,
                    percent=progress,
                    current=index,
                    total=len(codes),
                ),
            )
        except AllProvidersFailed as exc:
            errors.append(f"{code}: {exc}")
            continue
        stmt = insert(RealtimeQuote).values(
            code=quote.code,
            price=quote.price,
            change_pct=quote.change_pct,
            turnover_rate=quote.turnover_rate,
            volume=quote.volume,
            turnover=quote.turnover,
            market_cap=quote.market_cap,
            source=provider_name,
        )
        update_fields = {
            "price": stmt.excluded.price,
            "change_pct": stmt.excluded.change_pct,
            "turnover_rate": stmt.excluded.turnover_rate,
            "volume": stmt.excluded.volume,
            "turnover": stmt.excluded.turnover,
            "market_cap": stmt.excluded.market_cap,
            "source": stmt.excluded.source,
        }
        await session.execute(stmt.on_conflict_do_update(index_elements=["code"], set_=update_fields))
        records_count += 1
    status = "success" if not errors else "failed" if records_count == 0 else "fallback"
    detail = "; ".join(errors) if errors else "quotes synced"
    await _write_sync_log(session, "realtime", status, records_count, detail)
    await progress_hub.publish(
        "failed" if status == "failed" else "quotes",
        _sync_finish_message("实时行情", status, records_count, len(codes), errors),
        percent=42,
        current=records_count,
        total=len(codes),
    )
    return SyncResult(task_type="realtime", status=status, records_count=records_count, detail=detail)


async def sync_kline(
    session: AsyncSession,
    codes: list[str],
    period: str = "day",
    start: date | None = None,
    end: date | None = None,
) -> SyncResult:
    manager = FailoverManager(registry.chain_for("kline"))
    records_count = 0
    errors: list[str] = []
    period_label = _period_label(period)
    total = max(len(codes), 1)
    await progress_hub.publish(
        "kline",
        f"第4步：准备同步{period_label}K线，共 {len(codes)} 只股票",
        percent=45,
        current=0,
        total=len(codes),
    )
    for index, code in enumerate(codes, start=1):
        await progress_hub.publish(
            "kline",
            f"第5步：同步 {code} {period_label}K线（{index}/{len(codes)}）",
            code=code,
            percent=45 + int(index / total * 45),
            current=index,
            total=len(codes),
        )
        base_percent = 45 + int((index - 1) / total * 45)
        try:
            rows, provider_name = await manager.execute(
                session,
                lambda provider, stock_code=code: provider.get_kline(
                    stock_code, period=period, start=start, end=end
                ),
                lambda provider, stock_code=code, progress=base_percent: progress_hub.publish(
                    "kline",
                    f"第4步：连接 {provider.name} 数据源，拉取 {stock_code} {period_label}K线",
                    provider=provider.name,
                    code=stock_code,
                    percent=progress,
                    current=index,
                    total=len(codes),
                ),
            )
        except AllProvidersFailed as exc:
            errors.append(f"{code}: {exc}")
            continue
        for item in rows:
            stmt = insert(KLineData).values(
                code=item.code,
                period=item.period,
                date=item.date,
                open=item.open,
                close=item.close,
                high=item.high,
                low=item.low,
                volume=item.volume,
                turnover=item.turnover,
                change_pct=item.change_pct,
                source=provider_name,
            )
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
            records_count += 1
    status = "success" if not errors else "failed" if records_count == 0 else "fallback"
    detail = "; ".join(errors) if errors else f"{period} kline synced"
    await _write_sync_log(session, f"kline_{period}", status, records_count, detail)
    failed_count = len(errors)
    await progress_hub.publish(
        "failed" if status == "failed" else "done",
        _sync_finish_message(f"{period_label}K线", status, records_count, len(codes), errors),
        percent=100,
        current=len(codes) - failed_count,
        total=len(codes),
    )
    return SyncResult(task_type=f"kline_{period}", status=status, records_count=records_count, detail=detail)


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
