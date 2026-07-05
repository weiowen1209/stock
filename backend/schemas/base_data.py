from backend.schemas.common import OrmModel
from backend.schemas.stock import StockRead


class BaseDataImportResult(OrmModel):
    row_count: int
    parsed_count: int
    inserted_count: int
    updated_count: int
    disabled_count: int
    skipped_count: int
    active_count: int
    skipped_examples: list[dict[str, str]]


class BaseDataStockUpsert(OrmModel):
    industry_chain: str
    industry_chain_detail_level2: str
    industry_chain_detail_level3: str
    name: str
    code: str | int


class BaseDataStockList(OrmModel):
    stocks: list[StockRead]


class StockCategoryRead(OrmModel):
    id: int
    industry_chain: str
    level2: str
    level3: str


class StockCategoryWrite(OrmModel):
    industry_chain: str
    level2: str
    level3: str
