"""Canonical non-financial metric dictionary for the Phase 1 engine."""

from dataclasses import dataclass
from enum import StrEnum

from indian_company_analysis.domain.enums import MetricNature, StatementType, UnitType


class MetricId(StrEnum):
    # Income statement facts
    REVENUE = "revenue"
    COST_OF_REVENUE = "cost_of_revenue"
    EBITDA = "ebitda"
    DEPRECIATION_AMORTIZATION = "depreciation_amortization"
    EBIT = "ebit"
    FINANCE_COST = "finance_cost"
    PROFIT_BEFORE_TAX = "profit_before_tax"
    TAX_EXPENSE = "tax_expense"
    PROFIT_AFTER_TAX = "profit_after_tax"

    # Balance-sheet facts
    CASH_AND_EQUIVALENTS = "cash_and_equivalents"
    TRADE_RECEIVABLES = "trade_receivables"
    INVENTORY = "inventory"
    PROPERTY_PLANT_EQUIPMENT = "property_plant_equipment"
    TOTAL_ASSETS = "total_assets"
    TRADE_PAYABLES = "trade_payables"
    SHORT_TERM_DEBT = "short_term_debt"
    LONG_TERM_DEBT = "long_term_debt"
    TOTAL_EQUITY = "total_equity"
    TOTAL_LIABILITIES_AND_EQUITY = "total_liabilities_and_equity"

    # Cash-flow facts
    CASH_FLOW_FROM_OPERATIONS = "cash_flow_from_operations"
    CAPITAL_EXPENDITURE = "capital_expenditure"
    CASH_FLOW_FROM_INVESTING = "cash_flow_from_investing"
    CASH_FLOW_FROM_FINANCING = "cash_flow_from_financing"
    OPENING_CASH = "opening_cash"
    CLOSING_CASH = "closing_cash"

    # Derived metrics
    REVENUE_GROWTH = "revenue_growth"
    REVENUE_CAGR = "revenue_cagr"
    EBITDA_MARGIN = "ebitda_margin"
    EBIT_MARGIN = "ebit_margin"
    PAT_MARGIN = "pat_margin"
    CFO_TO_PAT_CONVERSION = "cfo_to_pat_conversion"
    FREE_CASH_FLOW = "free_cash_flow"
    FREE_CASH_FLOW_MARGIN = "free_cash_flow_margin"
    RETURN_ON_EQUITY = "return_on_equity"
    RETURN_ON_CAPITAL_EMPLOYED = "return_on_capital_employed"
    RECEIVABLE_DAYS = "receivable_days"
    INVENTORY_DAYS = "inventory_days"
    PAYABLE_DAYS = "payable_days"
    CASH_CONVERSION_CYCLE = "cash_conversion_cycle"
    GROSS_DEBT = "gross_debt"
    NET_DEBT = "net_debt"
    DEBT_TO_EQUITY = "debt_to_equity"
    INTEREST_COVERAGE = "interest_coverage"


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    metric_id: MetricId
    display_name: str
    statement_type: StatementType
    nature: MetricNature
    unit_type: UnitType
    description: str


def _fact(
    metric_id: MetricId,
    display_name: str,
    statement_type: StatementType,
    nature: MetricNature,
    description: str,
) -> MetricDefinition:
    return MetricDefinition(
        metric_id=metric_id,
        display_name=display_name,
        statement_type=statement_type,
        nature=nature,
        unit_type=UnitType.MONETARY,
        description=description,
    )


def _derived(
    metric_id: MetricId, display_name: str, unit_type: UnitType, description: str
) -> MetricDefinition:
    return MetricDefinition(
        metric_id=metric_id,
        display_name=display_name,
        statement_type=StatementType.ANALYTICAL,
        nature=MetricNature.DERIVED,
        unit_type=unit_type,
        description=description,
    )


METRIC_DEFINITIONS: dict[MetricId, MetricDefinition] = {
    definition.metric_id: definition
    for definition in (
        _fact(
            MetricId.REVENUE,
            "Revenue",
            StatementType.INCOME_STATEMENT,
            MetricNature.FLOW,
            "Revenue from operations.",
        ),
        _fact(
            MetricId.COST_OF_REVENUE,
            "Cost of revenue",
            StatementType.INCOME_STATEMENT,
            MetricNature.FLOW,
            "Direct cost associated with revenue; stored as a positive expense.",
        ),
        _fact(
            MetricId.EBITDA,
            "EBITDA",
            StatementType.INCOME_STATEMENT,
            MetricNature.FLOW,
            "Earnings before interest, tax, depreciation and amortization.",
        ),
        _fact(
            MetricId.DEPRECIATION_AMORTIZATION,
            "Depreciation and amortization",
            StatementType.INCOME_STATEMENT,
            MetricNature.FLOW,
            "Depreciation and amortization expense stored as a positive amount.",
        ),
        _fact(
            MetricId.EBIT,
            "EBIT",
            StatementType.INCOME_STATEMENT,
            MetricNature.FLOW,
            "Operating profit after depreciation and amortization.",
        ),
        _fact(
            MetricId.FINANCE_COST,
            "Finance cost",
            StatementType.INCOME_STATEMENT,
            MetricNature.FLOW,
            "Finance cost stored as a positive expense.",
        ),
        _fact(
            MetricId.PROFIT_BEFORE_TAX,
            "Profit before tax",
            StatementType.INCOME_STATEMENT,
            MetricNature.FLOW,
            "Profit before current and deferred tax.",
        ),
        _fact(
            MetricId.TAX_EXPENSE,
            "Tax expense",
            StatementType.INCOME_STATEMENT,
            MetricNature.FLOW,
            "Tax expense stored as a positive amount; tax credits may be negative.",
        ),
        _fact(
            MetricId.PROFIT_AFTER_TAX,
            "Profit after tax",
            StatementType.INCOME_STATEMENT,
            MetricNature.FLOW,
            "Profit attributable before any analytical normalization.",
        ),
        _fact(
            MetricId.CASH_AND_EQUIVALENTS,
            "Cash and equivalents",
            StatementType.BALANCE_SHEET,
            MetricNature.STOCK,
            "Cash and cash equivalents at period end.",
        ),
        _fact(
            MetricId.TRADE_RECEIVABLES,
            "Trade receivables",
            StatementType.BALANCE_SHEET,
            MetricNature.STOCK,
            "Gross or net trade receivables according to the captured definition.",
        ),
        _fact(
            MetricId.INVENTORY,
            "Inventory",
            StatementType.BALANCE_SHEET,
            MetricNature.STOCK,
            "Inventory at period end; often not material for IT services.",
        ),
        _fact(
            MetricId.PROPERTY_PLANT_EQUIPMENT,
            "Property, plant and equipment",
            StatementType.BALANCE_SHEET,
            MetricNature.STOCK,
            "Net carrying value of property, plant and equipment.",
        ),
        _fact(
            MetricId.TOTAL_ASSETS,
            "Total assets",
            StatementType.BALANCE_SHEET,
            MetricNature.STOCK,
            "Total assets at period end.",
        ),
        _fact(
            MetricId.TRADE_PAYABLES,
            "Trade payables",
            StatementType.BALANCE_SHEET,
            MetricNature.STOCK,
            "Trade payables at period end.",
        ),
        _fact(
            MetricId.SHORT_TERM_DEBT,
            "Short-term debt",
            StatementType.BALANCE_SHEET,
            MetricNature.STOCK,
            "Interest-bearing debt due within twelve months.",
        ),
        _fact(
            MetricId.LONG_TERM_DEBT,
            "Long-term debt",
            StatementType.BALANCE_SHEET,
            MetricNature.STOCK,
            "Interest-bearing debt due after twelve months.",
        ),
        _fact(
            MetricId.TOTAL_EQUITY,
            "Total equity",
            StatementType.BALANCE_SHEET,
            MetricNature.STOCK,
            "Total equity attributable to owners and non-controlling interests where applicable.",
        ),
        _fact(
            MetricId.TOTAL_LIABILITIES_AND_EQUITY,
            "Total liabilities and equity",
            StatementType.BALANCE_SHEET,
            MetricNature.STOCK,
            "Total liabilities plus equity at period end.",
        ),
        _fact(
            MetricId.CASH_FLOW_FROM_OPERATIONS,
            "Cash flow from operations",
            StatementType.CASH_FLOW,
            MetricNature.FLOW,
            "Net cash generated from operating activities.",
        ),
        _fact(
            MetricId.CAPITAL_EXPENDITURE,
            "Capital expenditure",
            StatementType.CASH_FLOW,
            MetricNature.FLOW,
            "Cash capital expenditure stored as a positive outflow.",
        ),
        _fact(
            MetricId.CASH_FLOW_FROM_INVESTING,
            "Cash flow from investing",
            StatementType.CASH_FLOW,
            MetricNature.FLOW,
            "Net investing cash flow using statement sign conventions.",
        ),
        _fact(
            MetricId.CASH_FLOW_FROM_FINANCING,
            "Cash flow from financing",
            StatementType.CASH_FLOW,
            MetricNature.FLOW,
            "Net financing cash flow using statement sign conventions.",
        ),
        _fact(
            MetricId.OPENING_CASH,
            "Opening cash",
            StatementType.CASH_FLOW,
            MetricNature.STOCK,
            "Cash and cash equivalents at the start of the period.",
        ),
        _fact(
            MetricId.CLOSING_CASH,
            "Closing cash",
            StatementType.CASH_FLOW,
            MetricNature.STOCK,
            "Cash and cash equivalents at the end of the period.",
        ),
        _derived(
            MetricId.REVENUE_GROWTH,
            "Revenue growth",
            UnitType.RATIO,
            "Current revenue divided by prior-period revenue, less one.",
        ),
        _derived(
            MetricId.REVENUE_CAGR,
            "Revenue CAGR",
            UnitType.RATIO,
            "Compound annual revenue growth over the available annual interval.",
        ),
        _derived(
            MetricId.EBITDA_MARGIN, "EBITDA margin", UnitType.RATIO, "EBITDA divided by revenue."
        ),
        _derived(MetricId.EBIT_MARGIN, "EBIT margin", UnitType.RATIO, "EBIT divided by revenue."),
        _derived(
            MetricId.PAT_MARGIN,
            "PAT margin",
            UnitType.RATIO,
            "Profit after tax divided by revenue.",
        ),
        _derived(
            MetricId.CFO_TO_PAT_CONVERSION,
            "CFO-to-PAT conversion",
            UnitType.RATIO,
            "Operating cash flow divided by profit after tax.",
        ),
        _derived(
            MetricId.FREE_CASH_FLOW,
            "Free cash flow",
            UnitType.MONETARY,
            "Operating cash flow less positive capital expenditure.",
        ),
        _derived(
            MetricId.FREE_CASH_FLOW_MARGIN,
            "Free-cash-flow margin",
            UnitType.RATIO,
            "Free cash flow divided by revenue.",
        ),
        _derived(
            MetricId.RETURN_ON_EQUITY,
            "Return on equity",
            UnitType.RATIO,
            "Profit after tax divided by average total equity.",
        ),
        _derived(
            MetricId.RETURN_ON_CAPITAL_EMPLOYED,
            "Return on capital employed",
            UnitType.RATIO,
            (
                "EBIT divided by average capital employed, where capital employed is "
                "equity plus debt less cash."
            ),
        ),
        _derived(
            MetricId.RECEIVABLE_DAYS,
            "Receivable days",
            UnitType.DAYS,
            "Average trade receivables divided by revenue, multiplied by period days.",
        ),
        _derived(
            MetricId.INVENTORY_DAYS,
            "Inventory days",
            UnitType.DAYS,
            "Average inventory divided by cost of revenue, multiplied by period days.",
        ),
        _derived(
            MetricId.PAYABLE_DAYS,
            "Payable days",
            UnitType.DAYS,
            "Average trade payables divided by cost of revenue, multiplied by period days.",
        ),
        _derived(
            MetricId.CASH_CONVERSION_CYCLE,
            "Cash-conversion cycle",
            UnitType.DAYS,
            "Receivable days plus inventory days less payable days.",
        ),
        _derived(
            MetricId.GROSS_DEBT,
            "Gross debt",
            UnitType.MONETARY,
            "Short-term debt plus long-term debt.",
        ),
        _derived(
            MetricId.NET_DEBT,
            "Net debt",
            UnitType.MONETARY,
            "Gross debt less cash and equivalents; negative values indicate net cash.",
        ),
        _derived(
            MetricId.DEBT_TO_EQUITY,
            "Debt to equity",
            UnitType.RATIO,
            "Gross debt divided by total equity.",
        ),
        _derived(
            MetricId.INTEREST_COVERAGE,
            "Interest coverage",
            UnitType.RATIO,
            "EBIT divided by finance cost.",
        ),
    )
}
