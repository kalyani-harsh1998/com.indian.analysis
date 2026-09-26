"""Pure, deterministic demonstration ratios using decimal arithmetic."""

from decimal import Decimal


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
