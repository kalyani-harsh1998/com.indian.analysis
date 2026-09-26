"""Deterministic parsing of reported financial numeric cells."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

_REPORTED_NUMBER = re.compile(r"^-?[0-9][0-9,]*(?:\.[0-9]+)?$")
_MISSING_MARKERS = frozenset({"-", "–", "—"})


def parse_reported_decimal(raw_value: str) -> Decimal:
    """Parse comma-grouped and parenthesized values without inferring missing data."""

    cleaned = raw_value.strip()
    if cleaned in _MISSING_MARKERS:
        raise ValueError("dash represents a missing or not-applicable value")
    negative_parentheses = cleaned.startswith("(") and cleaned.endswith(")")
    if negative_parentheses:
        cleaned = cleaned[1:-1].strip()
    if not _REPORTED_NUMBER.fullmatch(cleaned):
        raise ValueError("value is not a supported reported number")
    normalized = cleaned.replace(",", "")
    try:
        value = Decimal(normalized)
    except InvalidOperation as error:
        raise ValueError("value cannot be represented as a decimal") from error
    return -value if negative_parentheses else value
