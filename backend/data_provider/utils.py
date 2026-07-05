from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any


def normalize_code(code: str) -> str:
    return code.strip().upper()


def is_a_share_code(code: str) -> bool:
    normalized = normalize_code(code)
    return len(normalized) == 6 and normalized.isdigit() and normalized[0] in {"0", "3", "6"}


def code_with_market(code: str) -> str:
    normalized = normalize_code(code)
    if normalized.startswith("HK") and normalized[2:].isdigit():
        return f"116.{normalized[2:]}"
    if normalized.startswith(("6", "9")):
        return f"1.{normalized}"
    return f"0.{normalized}"


def eastmoney_sec_id(code: str) -> str:
    return code_with_market(code)


def to_decimal(value: Any) -> Decimal | None:
    if value in (None, "", "-", "--"):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def to_int(value: Any) -> int | None:
    if value in (None, "", "-", "--"):
        return None
    try:
        return int(Decimal(str(value).replace(",", "")))
    except (InvalidOperation, ValueError):
        return None


def parse_date(value: str) -> date:
    return datetime.strptime(value[:10], "%Y-%m-%d").date()
