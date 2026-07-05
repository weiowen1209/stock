from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.init_data.stock_list import INITIAL_STOCKS
from backend.models import Stock


async def seed_initial_stocks(session: AsyncSession) -> int:
    inserted = 0
    for item in INITIAL_STOCKS:
        existing = await session.get(Stock, item["code"])
        if existing is not None:
            continue
        session.add(Stock(**item))
        inserted += 1
    if inserted:
        await session.commit()
    return inserted


async def list_stocks(
    session: AsyncSession,
    industry_chain: str | None = None,
    keyword: str | None = None,
) -> list[Stock]:
    stmt = select(Stock).where(Stock.is_active.is_(True)).order_by(Stock.industry_chain, Stock.code)
    if industry_chain:
        stmt = stmt.where(Stock.industry_chain == industry_chain)
    if keyword:
        like_keyword = f"%{keyword}%"
        stmt = stmt.where(Stock.name.like(like_keyword) | Stock.code.like(like_keyword))
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_stock(session: AsyncSession, code: str) -> Stock | None:
    return await session.get(Stock, code)


async def group_stocks_by_industry(session: AsyncSession) -> dict[str, list[Stock]]:
    stocks = await list_stocks(session)
    groups: dict[str, list[Stock]] = defaultdict(list)
    for stock in stocks:
        groups[stock.industry_chain].append(stock)
    return dict(groups)
