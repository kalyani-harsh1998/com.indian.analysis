"""Pure, deterministic non-financial calculations using decimal arithmetic."""

from decimal import Decimal, localcontext


def safe_divide(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    """Return a ratio, or ``None`` when an input is absent or the denominator is zero."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def revenue_growth(
    current_revenue: Decimal | None, prior_revenue: Decimal | None
) -> Decimal | None:
    """Calculate period-over-period revenue growth as a decimal ratio."""
    ratio = safe_divide(current_revenue, prior_revenue)
    return None if ratio is None else ratio - Decimal(1)


def operating_margin(operating_profit: Decimal | None, revenue: Decimal | None) -> Decimal | None:
    """Calculate operating profit divided by revenue."""
    return safe_divide(operating_profit, revenue)


def cfo_to_pat_conversion(cfo: Decimal | None, pat: Decimal | None) -> Decimal | None:
    """Calculate cash flow from operations divided by profit after tax."""
    return safe_divide(cfo, pat)


def average(opening_value: Decimal, closing_value: Decimal) -> Decimal:
    """Return the simple average of opening and closing balances."""
    return (opening_value + closing_value) / Decimal(2)


def compound_annual_growth(
    ending_value: Decimal, beginning_value: Decimal, years: int
) -> Decimal | None:
    """Return CAGR for positive endpoints and a positive number of intervals."""
    if beginning_value <= 0 or ending_value < 0 or years <= 0:
        return None
    with localcontext() as context:
        context.prec = 28
        return context.power(ending_value / beginning_value, Decimal(1) / Decimal(years)) - Decimal(
            1
        )


def free_cash_flow(cfo: Decimal, capital_expenditure: Decimal) -> Decimal:
    """Subtract positive cash capital expenditure from operating cash flow."""
    return cfo - capital_expenditure


def gross_debt(short_term_debt: Decimal, long_term_debt: Decimal) -> Decimal:
    return short_term_debt + long_term_debt


def net_debt(
    short_term_debt: Decimal, long_term_debt: Decimal, cash_and_equivalents: Decimal
) -> Decimal:
    """Return gross debt less cash; a negative result represents net cash."""
    return gross_debt(short_term_debt, long_term_debt) - cash_and_equivalents


def capital_employed(
    equity: Decimal,
    short_term_debt: Decimal,
    long_term_debt: Decimal,
    cash_and_equivalents: Decimal,
) -> Decimal:
    """Return equity plus interest-bearing debt less cash and equivalents."""
    return equity + short_term_debt + long_term_debt - cash_and_equivalents


def activity_days(
    average_balance: Decimal, flow_denominator: Decimal, days_in_period: int
) -> Decimal | None:
    """Calculate balance days using an average balance and actual period length."""
    ratio = safe_divide(average_balance, flow_denominator)
    return None if ratio is None else ratio * Decimal(days_in_period)
