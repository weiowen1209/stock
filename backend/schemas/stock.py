from datetime import date, datetime

from backend.schemas.common import OrmModel


class StockRead(OrmModel):
    code: str
    name: str
    exchange: str
    industry_chain: str
    industry_chain_detail: str | None = None
    core_products: str | None = None
    supply_chain_tags: str | None = None
    list_date: date | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class IndustryGroup(OrmModel):
    industry_chain: str
    stocks: list[StockRead]
