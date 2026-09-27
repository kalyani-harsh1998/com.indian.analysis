"""Tests for deterministic parsing of reported financial numbers."""

from decimal import Decimal

import pytest

from indian_company_analysis.data.normalization.numbers import parse_reported_decimal


@pytest.mark.parametrize(
    ("raw_value", "expected"),
    (
        ("1,78,650", Decimal("178650")),
        ("(1,246)", Decimal("-1246")),
        ("416", Decimal("416")),
        ("-12.50", Decimal("-12.50")),
    ),
)
def test_parse_reported_decimal(raw_value: str, expected: Decimal) -> None:
    assert parse_reported_decimal(raw_value) == expected


@pytest.mark.parametrize("raw_value", ("-", "–", "INR 100", "1,2A3", "(100"))
def test_parse_reported_decimal_rejects_missing_or_ambiguous_values(raw_value: str) -> None:
    with pytest.raises(ValueError):
        parse_reported_decimal(raw_value)
