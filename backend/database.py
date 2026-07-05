from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.config import get_settings
from backend.models import Base


settings = get_settings()
engine = create_async_engine(settings.database_url, echo=False, future=True)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_import_batch_columns(conn)
        await _ensure_report_parse_result_columns(conn)


async def _ensure_import_batch_columns(conn) -> None:
    result = await conn.execute(text("PRAGMA table_info(import_batches)"))
    columns = {row[1] for row in result.fetchall()}
    if "document_id" not in columns:
        await conn.execute(text("ALTER TABLE import_batches ADD COLUMN document_id INTEGER"))
    if "parse_job_id" not in columns:
        await conn.execute(text("ALTER TABLE import_batches ADD COLUMN parse_job_id INTEGER"))


async def _ensure_report_parse_result_columns(conn) -> None:
    result = await conn.execute(text("PRAGMA table_info(report_parse_results)"))
    columns = {row[1] for row in result.fetchall()}
    if columns and "field_sources_json" not in columns:
        await conn.execute(text("ALTER TABLE report_parse_results ADD COLUMN field_sources_json TEXT"))


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
