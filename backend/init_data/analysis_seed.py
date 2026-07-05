from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.sqlite import insert

from backend.models import BusinessSegment, ExpenseItem, FinancialReport, KLineData, ValuationMetric


TARGET_CODES = ["688017", "300124", "002747"]


async def seed_analysis_data(session: AsyncSession) -> None:
    existing = await session.scalar(select(FinancialReport.id).limit(1))
    if existing is not None:
        return
    for index, code in enumerate(TARGET_CODES):
        await _seed_financials(session, code, index)
        await _seed_segments(session, code, index)
        await _seed_expenses(session, code, index)
        await _seed_valuation(session, code, index)
        await _seed_kline_if_empty(session, code, index)
    await session.commit()


async def _seed_financials(session: AsyncSession, code: str, offset: int) -> None:
    rows = [
        ("2022年报", date(2022, 12, 31), 180000 + offset * 22000, 62000, 24500),
        ("2023年报", date(2023, 12, 31), 224000 + offset * 25000, 81200, 31800),
        ("2024年报", date(2024, 12, 31), 276000 + offset * 28000, 103000, 42600),
    ]
    for period, report_date, revenue, gross_profit, net_profit in rows:
        session.add(
            FinancialReport(
                code=code,
                report_period=period,
                report_date=report_date,
                revenue=Decimal(revenue),
                gross_profit=Decimal(gross_profit + offset * 6000),
                gross_margin=Decimal("37.32") + Decimal(offset),
                net_profit=Decimal(net_profit + offset * 4500),
                operating_cash_flow=Decimal(net_profit + 9000),
                total_assets=Decimal(revenue * 2),
                net_assets=Decimal(revenue),
                eps=Decimal("1.28") + Decimal(offset) / Decimal(10),
                roe=Decimal("13.6") + Decimal(offset),
                rd_ratio=Decimal("8.4") + Decimal(offset) / Decimal(2),
                source="sample",
                review_status="confirmed",
            )
        )


async def _seed_segments(session: AsyncSession, code: str, offset: int) -> None:
    names = ["机器人核心部件", "工业自动化", "智能装备服务"]
    for index, name in enumerate(names):
        revenue = Decimal(88000 + offset * 8000 + index * 26000)
        cost = revenue * Decimal("0.62")
        session.add(
            BusinessSegment(
                code=code,
                report_period="2024年报",
                segment_type="product",
                segment_name=name,
                revenue=revenue,
                cost=cost,
                gross_profit=revenue - cost,
                gross_margin=Decimal("38.00") - Decimal(index * 2),
                revenue_yoy=Decimal("18.5") - Decimal(index),
                source="sample",
                review_status="confirmed",
            )
        )


async def _seed_expenses(session: AsyncSession, code: str, offset: int) -> None:
    session.add(
        ExpenseItem(
            code=code,
            report_period="2024年报",
            selling_expense=Decimal(9800 + offset * 600),
            admin_expense=Decimal(13200 + offset * 700),
            rd_expense=Decimal(23800 + offset * 1200),
            finance_expense=Decimal(2600 + offset * 200),
            source="sample",
        )
    )


async def _seed_valuation(session: AsyncSession, code: str, offset: int) -> None:
    for day in range(6):
        session.add(
            ValuationMetric(
                code=code,
                date=date(2026, 6, 25) + timedelta(days=day),
                pe=Decimal("48.5") + Decimal(day) + Decimal(offset * 2),
                pb=Decimal("5.2") + Decimal(day) / Decimal(10),
                peg=Decimal("1.6") + Decimal(offset) / Decimal(10),
                market_cap=Decimal(12000000000 + offset * 2200000000 + day * 90000000),
                source="sample",
            )
        )


async def _seed_kline_if_empty(session: AsyncSession, code: str, offset: int) -> None:
    existing = await session.scalar(select(KLineData.id).where(KLineData.code == code).limit(1))
    if existing is not None:
        return
    base = Decimal("42.00") + Decimal(offset * 8)
    for day in range(40):
        current = base + Decimal(day) * Decimal("0.26")
        stmt = insert(KLineData).values(
            code=code,
            period="day",
            date=date(2026, 5, 1) + timedelta(days=day),
            open=current - Decimal("0.18"),
            close=current,
            high=current + Decimal("0.72"),
            low=current - Decimal("0.56"),
            volume=1000000 + day * 18000,
            turnover=Decimal(50000000 + day * 600000),
            change_pct=Decimal("0.85"),
            source="sample",
        )
        await session.execute(stmt.on_conflict_do_nothing(index_elements=["code", "period", "date"]))
