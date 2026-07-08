import hashlib
import io
import json
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy import desc, select
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.fact_service import create_candidate_facts_for_import, list_candidate_facts
from backend.models import (
    AnnualReportExtraction,
    BusinessSegment,
    ExpenseItem,
    FinancialReport,
    ImportBatch,
    ReportDocument,
    ReportParseJob,
    ReportParseResult,
)
from backend.pdf_financial_parser import parse_financial_tables
from backend.schemas.importing import (
    ConfirmImportRequest,
    ConfirmImportResult,
    ExpenseInput,
    ImportPreview,
    ManualFinancialInput,
    ReportDocumentUploadResult,
    ReportExtractions,
    SegmentInput,
)


async def create_upload_preview(
    session: AsyncSession,
    file_name: str,
    content: bytes,
    code: str | None = None,
    report_period: str | None = None,
    mime_type: str | None = None,
) -> ImportPreview:
    result = await create_report_document_upload(
        session,
        file_name,
        content,
        code=code,
        report_period=report_period,
        mime_type=mime_type,
    )
    return result.preview


async def create_report_document_upload(
    session: AsyncSession,
    file_name: str,
    content: bytes,
    code: str | None = None,
    report_period: str | None = None,
    mime_type: str | None = None,
    source_site: str | None = None,
) -> ReportDocumentUploadResult:
    file_hash = hashlib.sha256(content).hexdigest()
    document = await _get_document_by_hash(session, file_hash)
    is_duplicate = document is not None
    if document is None:
        saved_path = _save_upload(file_name, content, file_hash)
        document = ReportDocument(
            code=code,
            report_period=report_period,
            report_type=_infer_report_type(report_period),
            original_filename=file_name,
            stored_filename=saved_path.name,
            storage_path=str(saved_path),
            file_hash=file_hash,
            file_size=len(content),
            mime_type=mime_type,
            page_count=_estimate_page_count(content),
            source_site=source_site,
            status="stored",
        )
        session.add(document)
        await session.flush()
    elif code or report_period:
        document.code = document.code or code
        document.report_period = document.report_period or report_period
        document.report_type = document.report_type or _infer_report_type(document.report_period)

    preview = await parse_report_document(session, document.id, code=code, report_period=report_period, is_duplicate=is_duplicate)
    await session.commit()
    await session.refresh(document)
    return ReportDocumentUploadResult(document=document, preview=preview, is_duplicate=is_duplicate)


async def parse_report_document(
    session: AsyncSession,
    document_id: int,
    code: str | None = None,
    report_period: str | None = None,
    is_duplicate: bool = False,
) -> ImportPreview:
    document = await session.get(ReportDocument, document_id)
    if document is None:
        raise ValueError("report document not found")
    content = _read_document_content(document)
    text = _decode_content(content)
    parsed = parse_financial_tables(
        text,
        code=code,
        report_period=report_period,
    )
    financial = parsed.financial
    segments = parsed.segments or _parse_segments(text)
    expenses = parsed.expenses or _parse_expenses(text)
    confidence = parsed.confidence if text else Decimal("0.30")
    warnings = ["PDF解析结果需要人工确认后才会入库", *parsed.warnings]
    if is_duplicate:
        warnings.insert(0, "检测到相同PDF，已复用已保存文件")
    if not text:
        warnings.append("当前PDF未提取到可解析文本，可能需要OCR或人工补录")

    job = ReportParseJob(
        document_id=document.id,
        parser_version="financial-table-v1",
        status="parsed",
        confidence=confidence,
        warnings=json.dumps(warnings, ensure_ascii=False),
        finished_at=datetime.now(),
    )
    session.add(job)
    await session.flush()
    result = ReportParseResult(
        document_id=document.id,
        job_id=job.id,
        financial_json=financial.model_dump_json(),
        segments_json=json.dumps([item.model_dump(mode="json") for item in segments], ensure_ascii=False),
        expenses_json=expenses.model_dump_json() if expenses else None,
        field_sources_json=json.dumps(parsed.field_sources, ensure_ascii=False),
        extractions_json=parsed.extractions.model_dump_json() if parsed.extractions else None,
    )
    session.add(result)
    document.code = financial.code
    document.report_period = financial.report_period
    document.report_type = _infer_report_type(financial.report_period)
    document.status = "parsed"
    batch = ImportBatch(
        import_type="pdf",
        file_name=document.stored_filename,
        code=financial.code,
        report_period=financial.report_period,
        status="parsed",
        summary=json.dumps(_preview_summary(financial), ensure_ascii=False),
        document_id=document.id,
        parse_job_id=job.id,
    )
    session.add(batch)
    await session.flush()
    await session.refresh(document)
    await session.refresh(job)
    await session.refresh(batch)
    await create_candidate_facts_for_import(
        session=session,
        batch=batch,
        financial=financial,
        segments=segments,
        expenses=expenses,
        extractions=parsed.extractions,
        field_sources=parsed.field_sources,
        confidence=confidence,
        parser_version=job.parser_version,
    )
    candidate_facts = await list_candidate_facts(session, batch_id=batch.id)
    return ImportPreview(
        batch=batch,
        financial=financial,
        segments=segments,
        candidate_facts=candidate_facts,
        expenses=expenses,
        confidence=confidence,
        warnings=warnings,
        field_sources=parsed.field_sources,
        extractions=parsed.extractions,
        document=document,
        parse_job=job,
        is_duplicate=is_duplicate,
    )


async def create_manual_preview(
    session: AsyncSession, payload: ConfirmImportRequest
) -> ImportPreview:
    batch = ImportBatch(
        import_type="manual",
        code=payload.financial.code,
        report_period=payload.financial.report_period,
        status="parsed",
        summary=json.dumps(_preview_summary(payload.financial), ensure_ascii=False),
    )
    session.add(batch)
    await session.flush()
    await session.refresh(batch)
    await create_candidate_facts_for_import(
        session=session,
        batch=batch,
        financial=payload.financial,
        segments=payload.segments,
        expenses=payload.expenses,
        extractions=payload.extractions,
        field_sources={},
        confidence=Decimal("1.00"),
        parser_version="manual-v1",
    )
    candidate_facts = await list_candidate_facts(session, batch_id=batch.id)
    await session.commit()
    await session.refresh(batch)
    return ImportPreview(
        batch=batch,
        financial=payload.financial,
        segments=payload.segments,
        candidate_facts=candidate_facts,
        expenses=payload.expenses,
        confidence=Decimal("1.00"),
        warnings=[],
        field_sources={},
        extractions=payload.extractions,
    )


async def confirm_import(
    session: AsyncSession, batch_id: int, payload: ConfirmImportRequest
) -> ConfirmImportResult:
    batch = await session.get(ImportBatch, batch_id)
    if batch is None:
        raise ValueError("import batch not found")
    financial_records = await _upsert_financial(session, batch_id, payload.financial)
    segment_records = await _upsert_segments(session, batch_id, payload.financial, payload.segments)
    expense_records = await _upsert_expenses(session, batch_id, payload.financial, payload.expenses)
    extraction_records = await _upsert_extractions(session, batch_id, batch, payload.financial, payload.extractions)
    batch.status = "confirmed"
    batch.confirmed_at = datetime.now()
    batch.code = payload.financial.code
    batch.report_period = payload.financial.report_period
    batch.summary = json.dumps(_preview_summary(payload.financial), ensure_ascii=False)
    if batch.document_id:
        document = await session.get(ReportDocument, batch.document_id)
        if document:
            document.code = payload.financial.code
            document.report_period = payload.financial.report_period
            document.report_type = _infer_report_type(payload.financial.report_period)
            document.status = "confirmed"
    await session.commit()
    await session.refresh(batch)
    return ConfirmImportResult(
        batch=batch,
        financial_records=financial_records,
        segment_records=segment_records,
        expense_records=expense_records,
        extraction_records=extraction_records,
    )


async def list_import_batches(session: AsyncSession, limit: int = 20) -> list[ImportBatch]:
    result = await session.execute(select(ImportBatch).order_by(desc(ImportBatch.created_at)).limit(limit))
    return list(result.scalars().all())


async def get_import_batch(session: AsyncSession, batch_id: int) -> ImportBatch | None:
    return await session.get(ImportBatch, batch_id)


async def list_report_documents(
    session: AsyncSession, code: str | None = None, limit: int = 50
) -> list[ReportDocument]:
    stmt = select(ReportDocument).order_by(desc(ReportDocument.created_at)).limit(limit)
    if code:
        stmt = stmt.where(ReportDocument.code == code)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_report_document(session: AsyncSession, document_id: int) -> ReportDocument | None:
    return await session.get(ReportDocument, document_id)


def get_report_document_path(document: ReportDocument) -> Path:
    path = Path(document.storage_path)
    if not path.exists():
        raise FileNotFoundError("report document file not found")
    return path


async def get_latest_document_preview(session: AsyncSession, document_id: int) -> ImportPreview | None:
    document = await session.get(ReportDocument, document_id)
    if document is None:
        return None
    result = await session.execute(
        select(ReportParseResult)
        .where(ReportParseResult.document_id == document_id)
        .order_by(desc(ReportParseResult.created_at))
        .limit(1)
    )
    parse_result = result.scalar_one_or_none()
    if parse_result is None:
        return None
    job = await session.get(ReportParseJob, parse_result.job_id)
    batch_result = await session.execute(
        select(ImportBatch)
        .where(ImportBatch.document_id == document_id, ImportBatch.parse_job_id == parse_result.job_id)
        .order_by(desc(ImportBatch.created_at))
        .limit(1)
    )
    batch = batch_result.scalar_one_or_none()
    if batch is None:
        return None
    candidate_facts = await list_candidate_facts(session, batch_id=batch.id)
    return ImportPreview(
        batch=batch,
        financial=ManualFinancialInput.model_validate_json(parse_result.financial_json),
        segments=[SegmentInput.model_validate(item) for item in json.loads(parse_result.segments_json)],
        candidate_facts=candidate_facts,
        expenses=ExpenseInput.model_validate_json(parse_result.expenses_json) if parse_result.expenses_json else None,
        confidence=job.confidence if job and job.confidence is not None else Decimal("0"),
        warnings=json.loads(job.warnings) if job and job.warnings else [],
        field_sources=json.loads(parse_result.field_sources_json) if parse_result.field_sources_json else {},
        extractions=ReportExtractions.model_validate_json(parse_result.extractions_json) if parse_result.extractions_json else None,
        document=document,
        parse_job=job,
        is_duplicate=False,
    )


def _save_upload(file_name: str, content: bytes, file_hash: str | None = None) -> Path:
    settings = get_settings()
    safe_name = re.sub(r"[^0-9A-Za-z._-]", "_", file_name)
    prefix = file_hash[:12] if file_hash else datetime.now().strftime("%Y%m%d%H%M%S")
    target = settings.upload_dir / f"{prefix}_{safe_name}"
    target.write_bytes(content)
    return target


async def _get_document_by_hash(session: AsyncSession, file_hash: str) -> ReportDocument | None:
    result = await session.execute(select(ReportDocument).where(ReportDocument.file_hash == file_hash))
    return result.scalar_one_or_none()


def _read_document_content(document: ReportDocument) -> bytes:
    return get_report_document_path(document).read_bytes()


def _estimate_page_count(content: bytes) -> int | None:
    marker_count = content.count(b"/Type /Page")
    return marker_count or None


def _infer_report_type(report_period: str | None) -> str | None:
    if not report_period:
        return None
    if "一季" in report_period:
        return "一季报"
    if "半年" in report_period or "中报" in report_period:
        return "半年报"
    if "三季" in report_period:
        return "三季报"
    if "年报" in report_period:
        return "年报"
    return None


def _decode_content(content: bytes) -> str:
    extracted = _decode_pdf_text(content)
    if extracted:
        return extracted
    for encoding in ("utf-8", "gb18030", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return ""


def _decode_pdf_text(content: bytes) -> str:
    if not content.startswith(b"%PDF"):
        return ""
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        snippets = re.findall(rb"\(([^()]{1,200})\)\s*Tj", content)
        try:
            return "\n".join(item.decode("gb18030", errors="ignore") for item in snippets)
        except UnicodeDecodeError:
            return ""


def _parse_financial_text(
    text: str, code: str | None = None, report_period: str | None = None
) -> ManualFinancialInput:
    return ManualFinancialInput(
        code=code or _match_text(text, r"(?:代码|证券代码)[:：\s]*([0-9]{6})") or "688017",
        report_period=report_period or _match_text(text, r"(20[0-9]{2}(?:年报|半年报|一季报|三季报))") or "2024年报",
        report_date=_match_text(text, r"(?:报告日|报告日期)[:：\s]*(20[0-9]{2}-[0-9]{2}-[0-9]{2})"),
        revenue=_match_decimal(text, "营业收入"),
        gross_profit=_match_decimal(text, "毛利"),
        gross_margin=_match_decimal(text, "毛利率"),
        net_profit=_match_decimal(text, "净利润"),
        operating_cash_flow=_match_decimal(text, "经营现金流"),
        total_assets=_match_decimal(text, "总资产"),
        net_assets=_match_decimal(text, "净资产"),
        eps=_match_decimal(text, "每股收益"),
        roe=_match_decimal(text, "ROE"),
        rd_ratio=_match_decimal(text, "研发费用率"),
    )


def _parse_segments(text: str) -> list[SegmentInput]:
    output: list[SegmentInput] = []
    for name in ("机器人核心部件", "工业自动化", "智能装备服务"):
        revenue = _match_decimal(text, name)
        if revenue is not None:
            output.append(SegmentInput(segment_name=name, revenue=revenue))
    return output


def _parse_expenses(text: str) -> ExpenseInput | None:
    expenses = ExpenseInput(
        selling_expense=_match_decimal(text, "销售费用"),
        admin_expense=_match_decimal(text, "管理费用"),
        rd_expense=_match_decimal(text, "研发费用"),
        finance_expense=_match_decimal(text, "财务费用"),
    )
    if any(value is not None for value in expenses.model_dump().values()):
        return expenses
    return None


def _match_text(text: str, pattern: str) -> str | None:
    matched = re.search(pattern, text, re.I)
    return matched.group(1) if matched else None


def _match_decimal(text: str, label: str) -> Decimal | None:
    pattern = rf"{re.escape(label)}[:：\s]*(-?[0-9]+(?:\.[0-9]+)?)"
    matched = re.search(pattern, text, re.I)
    if not matched:
        return None
    try:
        return Decimal(matched.group(1))
    except (InvalidOperation, ValueError):
        return None


def _preview_summary(financial: ManualFinancialInput) -> dict[str, str | None]:
    return {
        "code": financial.code,
        "report_period": financial.report_period,
        "revenue": str(financial.revenue) if financial.revenue is not None else None,
        "net_profit": str(financial.net_profit) if financial.net_profit is not None else None,
    }


async def _upsert_financial(
    session: AsyncSession, batch_id: int, financial: ManualFinancialInput
) -> int:
    stmt = insert(FinancialReport).values(
        code=financial.code,
        report_period=financial.report_period,
        report_date=_parse_date(financial.report_date),
        revenue=financial.revenue,
        gross_profit=financial.gross_profit,
        gross_margin=financial.gross_margin,
        net_profit=financial.net_profit,
        operating_cash_flow=financial.operating_cash_flow,
        total_assets=financial.total_assets,
        net_assets=financial.net_assets,
        eps=financial.eps,
        roe=financial.roe,
        rd_ratio=financial.rd_ratio,
        source="import",
        import_id=batch_id,
        review_status="confirmed",
    )
    update_fields = {key: getattr(stmt.excluded, key) for key in [
        "report_date", "revenue", "gross_profit", "gross_margin", "net_profit",
        "operating_cash_flow", "total_assets", "net_assets", "eps", "roe", "rd_ratio",
        "source", "import_id", "review_status"
    ]}
    await session.execute(stmt.on_conflict_do_update(index_elements=["code", "report_period"], set_=update_fields))
    return 1


async def _upsert_segments(
    session: AsyncSession,
    batch_id: int,
    financial: ManualFinancialInput,
    segments: list[SegmentInput],
) -> int:
    count = 0
    for item in segments:
        stmt = insert(BusinessSegment).values(
            code=financial.code,
            report_period=financial.report_period,
            segment_type=item.segment_type,
            segment_name=item.segment_name,
            revenue=item.revenue,
            cost=item.cost,
            gross_profit=item.gross_profit,
            gross_margin=item.gross_margin,
            revenue_yoy=item.revenue_yoy,
            source="import",
            import_id=batch_id,
            review_status="confirmed",
        )
        update_fields = {key: getattr(stmt.excluded, key) for key in [
            "revenue", "cost", "gross_profit", "gross_margin", "revenue_yoy",
            "source", "import_id", "review_status"
        ]}
        await session.execute(
            stmt.on_conflict_do_update(
                index_elements=["code", "report_period", "segment_type", "segment_name"],
                set_=update_fields,
            )
        )
        count += 1
    return count


async def _upsert_expenses(
    session: AsyncSession,
    batch_id: int,
    financial: ManualFinancialInput,
    expenses: ExpenseInput | None,
) -> int:
    if expenses is None:
        return 0
    stmt = insert(ExpenseItem).values(
        code=financial.code,
        report_period=financial.report_period,
        selling_expense=expenses.selling_expense,
        admin_expense=expenses.admin_expense,
        rd_expense=expenses.rd_expense,
        finance_expense=expenses.finance_expense,
        source="import",
        import_id=batch_id,
    )
    update_fields = {key: getattr(stmt.excluded, key) for key in [
        "selling_expense", "admin_expense", "rd_expense", "finance_expense", "source", "import_id"
    ]}
    await session.execute(stmt.on_conflict_do_update(index_elements=["code", "report_period"], set_=update_fields))
    return 1


async def _upsert_extractions(
    session: AsyncSession,
    batch_id: int,
    batch: ImportBatch,
    financial: ManualFinancialInput,
    extractions: ReportExtractions | None,
) -> int:
    if extractions is None:
        return 0
    values = extractions.model_dump()
    notes = values.pop("notes", {}) or {}
    stmt = insert(AnnualReportExtraction).values(
        code=financial.code,
        report_period=financial.report_period,
        document_id=batch.document_id,
        import_id=batch_id,
        **values,
        notes_json=json.dumps(notes, ensure_ascii=False),
        source="import",
        review_status="confirmed",
    )
    update_fields = {
        key: getattr(stmt.excluded, key)
        for key in [
            "document_id",
            "import_id",
            "operating_profit",
            "total_profit",
            "non_recurring_net_profit",
            "income_tax_expense",
            "minority_interest",
            "other_income",
            "investment_income",
            "fair_value_change_income",
            "credit_impairment_loss",
            "asset_impairment_loss",
            "asset_disposal_income",
            "cash_received_from_sales",
            "cash_received_other_operating",
            "inventory_total",
            "inventory_impairment",
            "capital_reserve",
            "total_share_capital",
            "rd_investment",
            "rd_investment_ratio",
            "patent_count",
            "invention_patent_count",
            "construction_in_progress",
            "notes_json",
            "source",
            "review_status",
        ]
    }
    await session.execute(stmt.on_conflict_do_update(index_elements=["code", "report_period"], set_=update_fields))
    return 1


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()
