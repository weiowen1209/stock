from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.concept_registry import concept_registry
from backend.data_provider.utils import normalize_code
from backend.models import KLineData, RealtimeQuote, Stock


@dataclass(slots=True)
class ConceptDiscoveryResult:
    discovered_count: int
    inserted_count: int
    updated_count: int
    stock_pool_count: int
    codes: list[str]


async def discover_and_upsert_concept_stocks(session: AsyncSession) -> ConceptDiscoveryResult:
    discovered = _deduplicate(concept_registry.discover_concept_stocks())
    inserted = 0
    updated = 0
    codes: list[str] = []
    for item in discovered:
        code = normalize_code(item["code"])
        codes.append(code)
        existing = await session.get(Stock, code)
        if existing is None:
            session.add(Stock(**{**item, "code": code, "is_active": True}))
            inserted += 1
            continue
        changed = _update_existing_stock(existing, item)
        if not existing.is_active:
            existing.is_active = True
            changed = True
        if changed:
            updated += 1
    await session.commit()
    stock_pool_count = await count_active_stocks(session)
    return ConceptDiscoveryResult(
        discovered_count=len(discovered),
        inserted_count=inserted,
        updated_count=updated,
        stock_pool_count=stock_pool_count,
        codes=sorted(codes),
    )


async def count_active_stocks(session: AsyncSession) -> int:
    result = await session.execute(select(func.count()).select_from(Stock).where(Stock.is_active.is_(True)))
    return int(result.scalar_one())


async def sync_coverage(session: AsyncSession) -> dict[str, int | str | None]:
    stock_codes = set((await session.execute(select(Stock.code).where(Stock.is_active.is_(True)))).scalars())
    quote_codes = set((await session.execute(select(RealtimeQuote.code))).scalars())
    kline_codes = set((await session.execute(select(KLineData.code).distinct())).scalars())
    quote_updated_at = (
        await session.execute(select(func.max(RealtimeQuote.updated_at)).where(RealtimeQuote.code.in_(stock_codes)))
    ).scalar_one_or_none()
    valid_kline_filter = KLineData.code.in_(stock_codes) & (KLineData.date <= date.today())
    kline_range = (
        await session.execute(select(func.min(KLineData.date), func.max(KLineData.date)).where(valid_kline_filter))
    ).one()
    kline_periods = (
        await session.execute(select(func.count(func.distinct(KLineData.period))).where(valid_kline_filter))
    ).scalar_one()
    missing_quotes = stock_codes - quote_codes
    missing_kline = stock_codes - kline_codes
    return {
        "stock_pool_count": len(stock_codes),
        "quote_count": len(stock_codes & quote_codes),
        "kline_count": len(stock_codes & kline_codes),
        "missing_quotes_count": len(missing_quotes),
        "missing_kline_count": len(missing_kline),
        "missing_total": len(missing_quotes) + len(missing_kline),
        "quote_updated_at": quote_updated_at.isoformat() if quote_updated_at else None,
        "kline_start_date": kline_range[0].isoformat() if kline_range[0] else None,
        "kline_end_date": kline_range[1].isoformat() if kline_range[1] else None,
        "kline_period_count": int(kline_periods or 0),
    }


def _deduplicate(items: list[dict[str, str]]) -> list[dict[str, str]]:
    deduped: dict[str, dict[str, str]] = {}
    for item in items:
        code = normalize_code(item["code"])
        deduped[code] = {**item, "code": code}
    return list(deduped.values())


def _update_existing_stock(stock: Stock, item: dict[str, str]) -> bool:
    changed = False
    for field in ["name", "exchange", "industry_chain", "industry_chain_detail", "core_products", "supply_chain_tags"]:
        value = item.get(field)
        if value is not None and getattr(stock, field) != value:
            setattr(stock, field, value)
            changed = True
    return changed
