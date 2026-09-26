from decimal import Decimal

from indian_company_analysis.analytics.ratios import (
    activity_days,
    average,
    capital_employed,
    cfo_to_pat_conversion,
    compound_annual_growth,
    free_cash_flow,
    net_debt,
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


def test_average_balance_and_activity_days() -> None:
    average_receivables = average(Decimal("210"), Decimal("230"))
    assert average_receivables == Decimal("220")
    assert activity_days(average_receivables, Decimal("1260"), 365) == Decimal(
        "63.73015873015873015873015873"
    )


def test_cash_and_capital_measures() -> None:
    assert free_cash_flow(Decimal("250"), Decimal("110")) == Decimal("140")
    assert net_debt(Decimal("18"), Decimal("42"), Decimal("245")) == Decimal("-185")
    assert capital_employed(
        Decimal("890"), Decimal("18"), Decimal("42"), Decimal("245")
    ) == Decimal("705")


def test_compound_annual_growth() -> None:
    result = compound_annual_growth(Decimal("1260"), Decimal("800"), 4)
    assert result is not None
    assert result.quantize(Decimal("0.000001")) == Decimal("0.120263")
    assert compound_annual_growth(Decimal("100"), Decimal(0), 4) is None
