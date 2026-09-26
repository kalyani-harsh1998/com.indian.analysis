"""Controlled vocabularies for financial meaning and provenance."""

from enum import StrEnum


class ValueClassification(StrEnum):
    REPORTED = "reported"
    CALCULATED = "calculated"
    ESTIMATED = "estimated"
    FORECAST = "forecast"
    MANAGEMENT_GUIDANCE = "management_guidance"
    ANALYST_HYPOTHESIS = "analyst_hypothesis"


class SourceKind(StrEnum):
    SYNTHETIC = "synthetic"
    EXCHANGE_FILING = "exchange_filing"
    ANNUAL_REPORT = "annual_report"
    REGULATOR = "regulator"
    COMPANY_IR = "company_ir"
    LICENSED_PROVIDER = "licensed_provider"
    SECONDARY = "secondary"


class DocumentType(StrEnum):
    ANNUAL_REPORT = "annual_report"
    FINANCIAL_RESULTS = "financial_results"
    INVESTOR_PRESENTATION = "investor_presentation"
    EXCHANGE_ANNOUNCEMENT = "exchange_announcement"
    XBRL_FILING = "xbrl_filing"
    GOVERNANCE_FILING = "governance_filing"
    OTHER = "other"


class LicenceCategory(StrEnum):
    UNASSESSED = "unassessed"
    INTERNAL_POC = "internal_poc"
    OPEN_LICENCE = "open_licence"
    LICENSED = "licensed"
    RESTRICTED = "restricted"


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReportingBasis(StrEnum):
    CONSOLIDATED = "consolidated"
    STANDALONE = "standalone"


class PeriodType(StrEnum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"


class StatementType(StrEnum):
    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW = "cash_flow"
    ANALYTICAL = "analytical"


class MetricNature(StrEnum):
    FLOW = "flow"
    STOCK = "stock"
    DERIVED = "derived"


class UnitType(StrEnum):
    MONETARY = "monetary"
    RATIO = "ratio"
    DAYS = "days"


class RestatementStatus(StrEnum):
    ORIGINAL = "original"
    RESTATED = "restated"
    SUPERSEDED = "superseded"


class CalculationStatus(StrEnum):
    SUCCESS = "success"
    MISSING_INPUT = "missing_input"
    ZERO_DENOMINATOR = "zero_denominator"
    INCOMPARABLE_INPUTS = "incomparable_inputs"
    NOT_APPLICABLE = "not_applicable"


class ReconciliationStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    MISSING_INPUT = "missing_input"
    INCOMPARABLE_INPUTS = "incomparable_inputs"


class ReconciliationType(StrEnum):
    EBITDA_TO_EBIT = "ebitda_to_ebit"
    PROFIT_AFTER_TAX = "profit_after_tax"
    BALANCE_SHEET = "balance_sheet"
    CASH_ROLL_FORWARD = "cash_roll_forward"


class ScenarioName(StrEnum):
    BASE = "base"
    BULL = "bull"
    BEAR = "bear"


class AnalysisMode(StrEnum):
    INVESTOR = "investor"
    MANAGEMENT = "management"
    DUE_DILIGENCE_CREDIT = "due_diligence_credit"
