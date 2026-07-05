import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation

from backend.schemas.importing import ExpenseInput, ManualFinancialInput, SegmentInput


@dataclass
class ExtractedValue:
    value: Decimal
    label: str
    section: str
    confidence: Decimal
    unit: str | None = None
    line: str | None = None


@dataclass
class FinancialParseResult:
    financial: ManualFinancialInput
    expenses: ExpenseInput | None
    segments: list[SegmentInput] = field(default_factory=list)
    confidence: Decimal = Decimal("0")
    warnings: list[str] = field(default_factory=list)
    field_sources: dict[str, dict[str, str]] = field(default_factory=dict)


FIELD_RULES: dict[str, dict[str, object]] = {
    "revenue": {"section": "income", "labels": ["营业总收入", "营业收入", "主营业务收入"]},
    "operating_cost": {"section": "income", "labels": ["营业成本", "主营业务成本", "营业总成本"]},
    "gross_profit": {"section": "income", "labels": ["营业毛利"]},
    "net_profit": {
        "section": "income",
        "labels": ["归属于母公司股东的净利润", "归属于上市公司股东的净利润", "归母净利润", "净利润"],
    },
    "eps": {"section": "income", "labels": ["基本每股收益", "每股收益"], "apply_unit": False},
    "total_assets": {"section": "balance", "labels": ["资产总计", "总资产"]},
    "net_assets": {"section": "balance", "labels": ["归属于母公司所有者权益合计", "所有者权益合计", "股东权益合计", "净资产"]},
    "operating_cash_flow": {
        "section": "cashflow",
        "labels": ["经营活动产生的现金流量净额", "经营活动现金流量净额", "经营现金流量净额", "经营现金流"],
    },
    "selling_expense": {"section": "income", "labels": ["销售费用"]},
    "admin_expense": {"section": "income", "labels": ["管理费用"]},
    "rd_expense": {"section": "income", "labels": ["研发费用"]},
    "finance_expense": {"section": "income", "labels": ["财务费用"]},
}

SECTION_PATTERNS = {
    "income": [r"合并利润表", r"利润表", r"损益表"],
    "balance": [r"合并资产负债表", r"资产负债表"],
    "cashflow": [r"合并现金流量表", r"现金流量表"],
}

UNIT_MULTIPLIERS = {
    "元": Decimal("1"),
    "人民币元": Decimal("1"),
    "千元": Decimal("1000"),
    "万元": Decimal("10000"),
    "百万元": Decimal("1000000"),
    "亿元": Decimal("100000000"),
}


def parse_financial_tables(text: str, code: str | None = None, report_period: str | None = None) -> FinancialParseResult:
    normalized = _normalize_text(text)
    sections = _split_sections(normalized)
    extracted: dict[str, ExtractedValue] = {}
    for field_name, rule in FIELD_RULES.items():
        labels = [str(item) for item in rule["labels"]]
        preferred_section = str(rule["section"])
        extracted[field_name] = _find_field_value(labels, sections, preferred_section, bool(rule.get("apply_unit", True)))

    financial = ManualFinancialInput(
        code=code or _match_text(normalized, r"(?:证券代码|股票代码|代码)[:：\s]*([0-9]{6})") or "688017",
        report_period=report_period or _match_report_period(normalized) or "2024年报",
        report_date=_match_report_date(normalized),
        revenue=_value(extracted, "revenue"),
        gross_profit=_value(extracted, "gross_profit") or _calculate_gross_profit(extracted),
        gross_margin=_calculate_gross_margin(extracted),
        net_profit=_value(extracted, "net_profit"),
        operating_cash_flow=_value(extracted, "operating_cash_flow"),
        total_assets=_value(extracted, "total_assets"),
        net_assets=_value(extracted, "net_assets"),
        eps=_value(extracted, "eps"),
        roe=None,
        rd_ratio=_calculate_ratio(_value(extracted, "rd_expense"), _value(extracted, "revenue")),
    )
    expenses = ExpenseInput(
        selling_expense=_value(extracted, "selling_expense"),
        admin_expense=_value(extracted, "admin_expense"),
        rd_expense=_value(extracted, "rd_expense"),
        finance_expense=_value(extracted, "finance_expense"),
    )
    if not any(value is not None for value in expenses.model_dump().values()):
        expenses = None
    segments = parse_business_segments(normalized)
    found_count = sum(1 for item in extracted.values() if item.value is not None)
    confidence = min(Decimal("0.90"), Decimal("0.35") + Decimal(found_count) * Decimal("0.05"))
    warnings = _build_warnings(normalized, extracted)
    return FinancialParseResult(
        financial=financial,
        expenses=expenses,
        segments=segments,
        confidence=confidence,
        warnings=warnings,
        field_sources=_build_sources(extracted),
    )


SEGMENT_TYPES = {
    "分行业": "industry",
    "主营业务分行业情况": "industry",
    "分产品": "product",
    "主营业务分产品情况": "product",
    "分地区": "region",
    "主营业务分地区情况": "region",
    "销售模式": "sales_mode",
    "主营业务分销售模式情况": "sales_mode",
}


def parse_business_segments(text: str) -> list[SegmentInput]:
    segments: list[SegmentInput] = []
    lines = [line.strip() for line in _normalize_text(text).splitlines() if line.strip()]
    for index, line in enumerate(lines):
        segment_type = _match_segment_type(line)
        if not segment_type:
            continue
        segment_lines = lines[index + 1:index + 45]
        segments.extend(_parse_segment_block(segment_lines, segment_type))
    return _dedupe_segments(segments)


def _match_segment_type(line: str) -> str | None:
    stripped = line.strip()
    for marker, segment_type in SEGMENT_TYPES.items():
        if marker in {"分行业", "分产品", "分地区", "销售模式"}:
            if stripped == marker or stripped.startswith(f"{marker} 营业收入"):
                return segment_type
            continue
        if marker in stripped:
            return segment_type
    return None


def _parse_segment_block(lines: list[str], segment_type: str) -> list[SegmentInput]:
    segments: list[SegmentInput] = []
    name_parts: list[str] = []
    for row in lines:
        if _match_segment_type(row) and not row.startswith(("分行业 ", "分产品 ", "分地区 ", "销售模式 ")):
            break
        if row.startswith(("分行业情况", "分产品情况")) or "成本构成" in row:
            break
        if row.startswith(("主营业务分行业、分产品", "主营业务分行业情况的说明", "产销量情况", "成本分析表")):
            break
        if _is_segment_header_or_note(row):
            continue
        if re.search(r"-?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?", row):
            merged = ("".join(name_parts) + " " + row).strip() if name_parts else row
            segment = _parse_segment_row(merged, segment_type)
            if segment:
                segments.append(segment)
            name_parts = []
            continue
        if re.search(r"[\u4e00-\u9fffA-Za-z]", row) and len(row) <= 20:
            name_parts.append(row)
    return segments


def _is_segment_header_or_note(row: str) -> bool:
    return (
        row.startswith(("单位：", "币种：", "苏州绿的", "（%）", "比上年", "减（%）", "本比上", "年增减", "上年增减"))
        or row in {"营业收入", "营业成本", "毛利率", "毛利率比", "营业成", "个百分点", "年增减", "（%）", "本比上"}
        or row.startswith(("分行业 营业收入", "分产品 营业收入", "分地区 营业收入", "销售模式 营业收入"))
    )


def _parse_segment_row(row: str, segment_type: str) -> SegmentInput | None:
    if not re.search(r"[\u4e00-\u9fffA-Za-z]", row):
        return None
    numbers = re.findall(r"-?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?", row)
    if len(numbers) < 3:
        return None
    name = row.split(numbers[0], 1)[0].strip(" ：:").replace(" ", "")
    if not name or len(name) > 40:
        return None
    values = [_to_decimal(item.replace(",", ""), "元") for item in numbers]
    if len(values) < 3 or values[0] is None or values[1] is None:
        return None
    gross_margin = values[2] if values[2] is not None and abs(values[2]) <= Decimal("100") else _calculate_ratio(values[0] - values[1], values[0])
    return SegmentInput(
        segment_type=segment_type,
        segment_name=name,
        revenue=values[0],
        cost=values[1],
        gross_profit=values[0] - values[1],
        gross_margin=gross_margin,
        revenue_yoy=values[3] if len(values) > 3 and values[3] is not None and abs(values[3]) <= Decimal("1000") else None,
    )


def _dedupe_segments(segments: list[SegmentInput]) -> list[SegmentInput]:
    output: list[SegmentInput] = []
    seen: set[tuple[str, str]] = set()
    for segment in segments:
        key = (segment.segment_type, segment.segment_name)
        if key in seen:
            continue
        seen.add(key)
        output.append(segment)
    return output


def _normalize_text(text: str) -> str:
    text = text.replace("\r", "\n").replace("\u3000", " ")
    text = re.sub(r"[\t ]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text


def _split_sections(text: str) -> dict[str, str]:
    markers: list[tuple[int, str]] = []
    for section, patterns in SECTION_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                markers.append((match.start(), section))
                break
    if not markers:
        return {"all": text}
    markers.sort(key=lambda item: item[0])
    sections: dict[str, str] = {}
    for index, (start, section) in enumerate(markers):
        end = markers[index + 1][0] if index + 1 < len(markers) else len(text)
        sections[section] = text[start:end]
    sections["all"] = text
    return sections


def _find_field_value(labels: list[str], sections: dict[str, str], preferred_section: str, apply_unit: bool = True) -> ExtractedValue:
    search_order = [preferred_section, "all"] if preferred_section in sections else ["all"]
    for section in search_order:
        source = sections.get(section, "")
        value = _find_in_text(labels, source, section, apply_unit=apply_unit)
        if value.value is not None:
            return value
    return ExtractedValue(value=None, label=labels[0], section=preferred_section, confidence=Decimal("0"))


def _find_in_text(labels: list[str], text: str, section: str, apply_unit: bool = True) -> ExtractedValue:
    section_unit = _detect_unit(text) if apply_unit else None
    lines = text.splitlines()
    for label in labels:
        compact_label = _compact(label)
        for index, line in enumerate(lines):
            compact_line = _compact(line)
            if not compact_line or compact_label not in compact_line:
                continue
            window = _join_continuation_lines(lines, index, label)
            value, unit = _extract_number_from_line(window, label, section_unit=section_unit, apply_unit=apply_unit)
            if value is not None:
                confidence = Decimal("0.86") if section != "all" else Decimal("0.70")
                return ExtractedValue(value=value, label=label, section=section, confidence=confidence, unit=unit, line=window.strip())
    return ExtractedValue(value=None, label=labels[0], section=section, confidence=Decimal("0"))


def _join_continuation_lines(lines: list[str], index: int, label: str) -> str:
    current = lines[index].strip()
    if _extract_number_from_line(current, label, apply_unit=False)[0] is not None:
        return current
    chunks = [current]
    for next_line in lines[index + 1:index + 4]:
        stripped = next_line.strip()
        if not stripped:
            continue
        chunks.append(stripped)
        if re.search(r"(?<![0-9])-?[0-9]+(?:,[0-9]{3})*(?:\.[0-9]+)?(?![0-9%])", stripped):
            break
    return " ".join(chunks)


def _extract_number_from_line(
    line: str, label: str, section_unit: str | None = None, apply_unit: bool = True
) -> tuple[Decimal | None, str | None]:
    unit = (_detect_unit(line) or section_unit) if apply_unit else None
    cleaned = line.replace(",", "")
    compact_label = _compact(label)
    label_index = _compact(cleaned).find(compact_label)
    if label_index >= 0:
        cleaned = cleaned[max(0, label_index):]
    numbers = re.findall(r"(?<![0-9])\(?-?[0-9]+(?:\.[0-9]+)?\)?(?![0-9%])", cleaned)
    values = [_to_decimal(number, unit) for number in numbers]
    values = [value for value in values if value is not None]
    if not values:
        return None, unit
    return values[0], unit


def _detect_unit(line: str) -> str | None:
    for unit in ("人民币元", "百万元", "万元", "千元", "亿元", "元"):
        if unit in line:
            return unit
    return None


def _to_decimal(raw: str, unit: str | None) -> Decimal | None:
    negative = raw.startswith("(") and raw.endswith(")")
    raw = raw.strip("()")
    try:
        value = Decimal(raw)
    except (InvalidOperation, ValueError):
        return None
    if negative:
        value = -value
    multiplier = UNIT_MULTIPLIERS.get(unit or "元", Decimal("1"))
    return value * multiplier


def _compact(value: str) -> str:
    return re.sub(r"[\s:：　（）()]+", "", value)


def _match_text(text: str, pattern: str) -> str | None:
    matched = re.search(pattern, text, re.I)
    return matched.group(1) if matched else None


def _match_report_period(text: str) -> str | None:
    matched = re.search(r"(20[0-9]{2}\s*年\s*(?:年度报告|年度|半年度报告|半年度|第一季度报告|第三季度报告|年报|半年报|一季报|三季报))", text)
    if not matched:
        return None
    value = re.sub(r"\s+", "", matched.group(1))
    normalized = (
        value.replace("年度报告", "年报")
        .replace("半年度报告", "半年报")
        .replace("第一季度报告", "一季报")
        .replace("第三季度报告", "三季报")
        .replace("年度", "年报")
    )
    return normalized.replace("年年报", "年报")


def _match_report_date(text: str) -> str | None:
    matched = re.search(r"(?:报告期末|报告日|报告日期)[:：\s]*(20[0-9]{2})[年\-/\.](0?[1-9]|1[0-2])[月\-/\.](3[01]|[12][0-9]|0?[1-9])", text)
    if not matched:
        return None
    year, month, day = matched.groups()
    return f"{year}-{int(month):02d}-{int(day):02d}"


def _value(extracted: dict[str, ExtractedValue], field_name: str) -> Decimal | None:
    item = extracted.get(field_name)
    return item.value if item else None


def _calculate_gross_profit(extracted: dict[str, ExtractedValue]) -> Decimal | None:
    revenue = _value(extracted, "revenue")
    operating_cost = _value(extracted, "operating_cost")
    if revenue is None or operating_cost is None:
        return None
    return revenue - operating_cost


def _calculate_gross_margin(extracted: dict[str, ExtractedValue]) -> Decimal | None:
    gross_profit = _value(extracted, "gross_profit") or _calculate_gross_profit(extracted)
    revenue = _value(extracted, "revenue")
    return _calculate_ratio(gross_profit, revenue)


def _calculate_ratio(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator in (None, Decimal("0")):
        return None
    return (numerator / denominator * Decimal("100")).quantize(Decimal("0.01"))


def _build_warnings(text: str, extracted: dict[str, ExtractedValue]) -> list[str]:
    warnings: list[str] = []
    if text.startswith("%PDF") or not text.strip():
        warnings.append("当前PDF文本层较弱，建议后续接入OCR引擎补充扫描版解析")
    required = ["revenue", "net_profit", "total_assets", "operating_cash_flow"]
    missing = [name for name in required if _value(extracted, name) is None]
    if missing:
        warnings.append("关键三表字段缺失：" + "、".join(missing))
    return warnings


def _build_sources(extracted: dict[str, ExtractedValue]) -> dict[str, dict[str, str]]:
    sources: dict[str, dict[str, str]] = {}
    for field_name, item in extracted.items():
        if item.value is None:
            continue
        sources[field_name] = {
            "value": str(item.value),
            "label": item.label,
            "section": item.section,
            "confidence": str(item.confidence),
            "unit": item.unit or "原始单位",
            "line": item.line or "",
        }
    return sources
