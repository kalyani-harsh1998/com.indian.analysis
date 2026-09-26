"""IT-services metric vocabulary; scoring and sector overrides remain deferred."""

from indian_company_analysis.domain.metrics import MetricId

IT_SERVICES_METRICS = (
    MetricId.REVENUE,
    MetricId.COST_OF_REVENUE,
    MetricId.EBITDA,
    MetricId.EBIT,
    MetricId.PROFIT_AFTER_TAX,
    MetricId.CASH_FLOW_FROM_OPERATIONS,
    MetricId.TRADE_RECEIVABLES,
    MetricId.REVENUE_GROWTH,
    MetricId.EBIT_MARGIN,
    MetricId.CFO_TO_PAT_CONVERSION,
    MetricId.RECEIVABLE_DAYS,
    MetricId.RETURN_ON_CAPITAL_EMPLOYED,
)
