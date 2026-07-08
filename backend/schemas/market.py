from datetime import date, datetime
from decimal import Decimal

from backend.schemas.common import OrmModel


class QuoteRead(OrmModel):
    code: str
    price: Decimal | None = None
    change_pct: Decimal | None = None
    turnover_rate: Decimal | None = None
    volume: int | None = None
    turnover: Decimal | None = None
    market_cap: Decimal | None = None
    source: str | None = None
    source_updated_at: datetime | None = None
    updated_at: datetime


class KLineRead(OrmModel):
    code: str
    period: str
    date: date
    open: Decimal | None = None
    close: Decimal | None = None
    high: Decimal | None = None
    low: Decimal | None = None
    volume: int | None = None
    turnover: Decimal | None = None
    change_pct: Decimal | None = None
    source: str | None = None
    updated_at: datetime


class SyncRequest(OrmModel):
    codes: list[str] | None = None
    include_quotes: bool = True
    include_kline: bool = True
    period: str = "day"
    periods: list[str] | None = None
    start_date: date | None = None
    end_date: date | None = None
    force_full: bool = False


class SyncResult(OrmModel):
    task_type: str
    status: str
    records_count: int
    detail: str | None = None


class SyncProgress(OrmModel):
    stage: str
    message: str
    provider: str | None = None
    code: str | None = None
    percent: int
    current: int = 0
    total: int = 0
    updated_at: str


class ProviderHealthRead(OrmModel):
    provider: str
    status: str
    consecutive_failures: int
    last_success_at: str | None = None
    last_failure_at: str | None = None
    next_probe_at: str | None = None
    error_message: str | None = None


class SyncStatus(OrmModel):
    latest_logs: list[dict]
    missing_quotes: list[str]
    missing_kline: list[str]
    providers: list[ProviderHealthRead]
    progress: SyncProgress
    coverage: dict[str, int | str | None]
