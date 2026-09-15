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


class ScenarioName(StrEnum):
    BASE = "base"
    BULL = "bull"
    BEAR = "bear"


class AnalysisMode(StrEnum):
    INVESTOR = "investor"
    MANAGEMENT = "management"
    DUE_DILIGENCE_CREDIT = "due_diligence_credit"
