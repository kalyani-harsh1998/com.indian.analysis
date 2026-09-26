from decimal import Decimal

from indian_company_analysis.analytics.ratios import (
    cfo_to_pat_conversion,
    operating_margin,
    revenue_growth,
)


def test_revenue_growth_is_deterministic_decimal_math() -> None:
    assert revenue_growth(Decimal("112"), Decimal("100")) == Decimal("0.12")


def test_operating_margin() -> None:
    assert operating_margin(Decimal("24"), Decimal("120")) == Decimal("0.2")


def test_cfo_to_pat_conversion() -> None:
    assert cfo_to_pat_conversion(Decimal("180"), Decimal("150")) == Decimal("1.2")


def test_zero_denominators_return_none() -> None:
    assert revenue_growth(Decimal("10"), Decimal(0)) is None
    assert operating_margin(Decimal("10"), Decimal(0)) is None
    assert cfo_to_pat_conversion(Decimal("10"), Decimal(0)) is None


def test_missing_values_return_none() -> None:
    assert revenue_growth(None, Decimal("10")) is None
    assert operating_margin(Decimal("10"), None) is None
    assert cfo_to_pat_conversion(None, Decimal("10")) is None
