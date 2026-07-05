from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.base_data_service import (
    build_base_data_template,
    create_stock_category,
    deactivate_base_data_stock,
    delete_stock_category,
    import_base_data_excel,
    list_base_data_stocks,
    list_stock_categories,
    update_stock_category,
    upsert_base_data_stock,
)
from backend.database import get_session
from backend.schemas.base_data import BaseDataImportResult, BaseDataStockUpsert, StockCategoryRead, StockCategoryWrite
from backend.schemas.common import ApiResponse, ResponseMeta
from backend.schemas.stock import StockRead


router = APIRouter(prefix="/api/base-data", tags=["base-data"])


@router.get("/stocks", response_model=ApiResponse[list[StockRead]])
async def read_base_data_stocks(
    include_inactive: bool = Query(default=False),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[StockRead]]:
    rows = await list_base_data_stocks(session, include_inactive=include_inactive)
    updated_at = max((row.updated_at for row in rows), default=None)
    return ApiResponse(data=rows, meta=ResponseMeta(source="base-data", updated_at=updated_at, stale=not rows))


@router.get("/stocks/template")
async def download_base_data_template(session: AsyncSession = Depends(get_session)) -> Response:
    content = await build_base_data_template(session)
    filename = quote("股票池导入模板.xlsx")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.get("/categories", response_model=ApiResponse[list[StockCategoryRead]])
async def read_stock_categories(session: AsyncSession = Depends(get_session)) -> ApiResponse[list[StockCategoryRead]]:
    rows = await list_stock_categories(session)
    updated_at = max((row.updated_at for row in rows), default=None)
    return ApiResponse(data=rows, meta=ResponseMeta(source="base-data", updated_at=updated_at, stale=not rows))


@router.post("/categories", response_model=ApiResponse[StockCategoryRead])
async def add_stock_category(
    payload: StockCategoryWrite,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[StockCategoryRead]:
    try:
        row = await create_stock_category(session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiResponse(data=row, meta=ResponseMeta(source="base-data"))


@router.put("/categories/{category_id}", response_model=ApiResponse[StockCategoryRead])
async def edit_stock_category(
    category_id: int,
    payload: StockCategoryWrite,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[StockCategoryRead]:
    try:
        row = await update_stock_category(session, category_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiResponse(data=row, meta=ResponseMeta(source="base-data"))


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_stock_category(category_id: int, session: AsyncSession = Depends(get_session)) -> None:
    try:
        await delete_stock_category(session, category_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/stocks", response_model=ApiResponse[StockRead])
async def save_base_data_stock(
    payload: BaseDataStockUpsert,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[StockRead]:
    try:
        row = await upsert_base_data_stock(session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiResponse(data=row, meta=ResponseMeta(source="base-data"))


@router.delete("/stocks/{code}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_base_data_stock(code: str, session: AsyncSession = Depends(get_session)) -> None:
    try:
        await deactivate_base_data_stock(session, code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/stocks/import-excel", response_model=ApiResponse[BaseDataImportResult])
async def import_base_data_stocks_excel(
    mode: str = Query(default="replace"),
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[BaseDataImportResult]:
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="请上传.xlsx格式的基础资料Excel")
    content = await file.read()
    try:
        result = await import_base_data_excel(session, content, mode=mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ApiResponse(data=result, meta=ResponseMeta(source="base-data"))
