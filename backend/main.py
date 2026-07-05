from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.base_data import router as base_data_router
from backend.api.fundamentals import router as fundamentals_router
from backend.api.imports import router as imports_router
from backend.api.kline import router as kline_router
from backend.api.quotes import router as quotes_router
from backend.api.stocks import router as stocks_router
from backend.api.sync_status import router as sync_router
from backend.api.technical import router as technical_router
from backend.api.valuation import router as valuation_router
from backend.config import get_settings
from backend.database import AsyncSessionLocal, init_db
from backend.init_data.analysis_seed import seed_analysis_data
from backend.schemas.common import ErrorDetail, ResponseMeta
from backend.services import seed_initial_stocks
from backend.sync.scheduler import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    async with AsyncSessionLocal() as session:
        await seed_initial_stocks(session)
        await seed_analysis_data(session)
    start_scheduler()
    try:
        yield
    finally:
        shutdown_scheduler()


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(base_data_router)
app.include_router(stocks_router)
app.include_router(quotes_router)
app.include_router(kline_router)
app.include_router(sync_router)
app.include_router(fundamentals_router)
app.include_router(valuation_router)
app.include_router(technical_router)
app.include_router(imports_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "data": None,
            "meta": ResponseMeta().model_dump(mode="json"),
            "error": ErrorDetail(code="http_error", message=str(exc.detail)).model_dump(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "data": None,
            "meta": ResponseMeta().model_dump(mode="json"),
            "error": ErrorDetail(code="internal_error", message="Internal server error").model_dump(),
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/system/status")
async def system_status() -> dict[str, Any]:
    return {"status": "ok", "environment": settings.environment}
