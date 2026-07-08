from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_session
from backend.fact_service import list_candidate_facts, list_confirmed_facts, list_evidence_items
from backend.import_service import (
    confirm_import,
    create_manual_preview,
    create_report_document_upload,
    create_upload_preview,
    get_import_batch,
    get_latest_document_preview,
    get_report_document,
    get_report_document_path,
    list_import_batches,
    list_report_documents,
    parse_report_document,
)
from backend.schemas.common import ApiResponse, ResponseMeta
from backend.schemas.importing import (
    CandidateFactRead,
    ConfirmImportRequest,
    ConfirmImportResult,
    ConfirmedFactRead,
    EvidenceItemRead,
    ImportBatchRead,
    ImportPreview,
    ReportDocumentRead,
    ReportDocumentUploadResult,
)


router = APIRouter(prefix="/api/imports", tags=["imports"])


@router.post("/upload", response_model=ApiResponse[ImportPreview])
async def upload_import_file(
    file: UploadFile = File(...),
    code: str | None = Form(default=None),
    report_period: str | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ImportPreview]:
    content = await file.read()
    preview = await create_upload_preview(
        session,
        file.filename or "upload.pdf",
        content,
        code=code,
        report_period=report_period,
        mime_type=file.content_type,
    )
    return ApiResponse(data=preview, meta=ResponseMeta(source="import"))


@router.post("/documents/upload", response_model=ApiResponse[ReportDocumentUploadResult])
async def upload_report_document(
    file: UploadFile = File(...),
    code: str | None = Form(default=None),
    report_period: str | None = Form(default=None),
    source_site: str | None = Form(default=None),
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ReportDocumentUploadResult]:
    content = await file.read()
    result = await create_report_document_upload(
        session,
        file.filename or "upload.pdf",
        content,
        code=code,
        report_period=report_period,
        mime_type=file.content_type,
        source_site=source_site,
    )
    return ApiResponse(data=result, meta=ResponseMeta(source="report_document"))


@router.get("/documents", response_model=ApiResponse[list[ReportDocumentRead]])
async def read_report_documents(
    code: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[ReportDocumentRead]]:
    rows = await list_report_documents(session, code=code)
    updated_at = max((row.updated_at for row in rows), default=None)
    return ApiResponse(data=rows, meta=ResponseMeta(source="report_document", updated_at=updated_at, stale=not rows))


@router.get("/documents/{document_id}", response_model=ApiResponse[ReportDocumentRead])
async def read_report_document(
    document_id: int,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ReportDocumentRead]:
    document = await get_report_document(session, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="report document not found")
    return ApiResponse(data=document, meta=ResponseMeta(source="report_document", updated_at=document.updated_at))


@router.get("/documents/{document_id}/file")
async def read_report_document_file(
    document_id: int,
    session: AsyncSession = Depends(get_session),
) -> FileResponse:
    document = await get_report_document(session, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="report document not found")
    try:
        path = get_report_document_path(document)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="report document file not found") from exc
    return FileResponse(path, media_type=document.mime_type or "application/pdf", filename=document.original_filename)


@router.post("/documents/{document_id}/parse", response_model=ApiResponse[ImportPreview])
async def reparse_report_document(
    document_id: int,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ImportPreview]:
    try:
        preview = await parse_report_document(session, document_id)
        await session.commit()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiResponse(data=preview, meta=ResponseMeta(source="report_document"))


@router.get("/documents/{document_id}/preview", response_model=ApiResponse[ImportPreview])
async def read_report_document_preview(
    document_id: int,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ImportPreview]:
    preview = await get_latest_document_preview(session, document_id)
    if preview is None:
        raise HTTPException(status_code=404, detail="report document preview not found")
    return ApiResponse(data=preview, meta=ResponseMeta(source="report_document"))


@router.post("/manual", response_model=ApiResponse[ImportPreview])
async def manual_import_preview(
    payload: ConfirmImportRequest,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ImportPreview]:
    preview = await create_manual_preview(session, payload)
    return ApiResponse(data=preview, meta=ResponseMeta(source="manual"))


@router.post("/{batch_id}/confirm", response_model=ApiResponse[ConfirmImportResult])
async def confirm_import_batch(
    batch_id: int,
    payload: ConfirmImportRequest,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[ConfirmImportResult]:
    try:
        result = await confirm_import(session, batch_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiResponse(data=result, meta=ResponseMeta(source="import"))


@router.get("", response_model=ApiResponse[list[ImportBatchRead]])
async def read_import_batches(session: AsyncSession = Depends(get_session)) -> ApiResponse[list[ImportBatchRead]]:
    rows = await list_import_batches(session)
    updated_at = max((row.created_at for row in rows), default=None)
    return ApiResponse(data=rows, meta=ResponseMeta(source="import", updated_at=updated_at, stale=not rows))


@router.get("/candidate-facts", response_model=ApiResponse[list[CandidateFactRead]])
async def read_candidate_facts(
    batch_id: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[CandidateFactRead]]:
    rows = await list_candidate_facts(session, batch_id=batch_id)
    updated_at = max((row.updated_at for row in rows), default=None)
    return ApiResponse(data=rows, meta=ResponseMeta(source="candidate_facts", updated_at=updated_at, stale=not rows))


@router.get("/evidence", response_model=ApiResponse[list[EvidenceItemRead]])
async def read_evidence_items(
    batch_id: int | None = None,
    code: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[EvidenceItemRead]]:
    rows = await list_evidence_items(session, batch_id=batch_id, code=code)
    updated_at = max((row.updated_at for row in rows), default=None)
    return ApiResponse(data=rows, meta=ResponseMeta(source="evidence", updated_at=updated_at, stale=not rows))


@router.get("/confirmed-facts", response_model=ApiResponse[list[ConfirmedFactRead]])
async def read_confirmed_facts(
    code: str | None = None,
    period: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> ApiResponse[list[ConfirmedFactRead]]:
    rows = await list_confirmed_facts(session, code=code, period=period)
    updated_at = max((row.updated_at for row in rows), default=None)
    return ApiResponse(data=rows, meta=ResponseMeta(source="confirmed_facts", updated_at=updated_at, stale=not rows))


@router.get("/{batch_id}", response_model=ApiResponse[ImportBatchRead])
async def read_import_batch(
    batch_id: int, session: AsyncSession = Depends(get_session)
) -> ApiResponse[ImportBatchRead]:
    batch = await get_import_batch(session, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail="import batch not found")
    return ApiResponse(data=batch, meta=ResponseMeta(source="import", updated_at=batch.created_at))
