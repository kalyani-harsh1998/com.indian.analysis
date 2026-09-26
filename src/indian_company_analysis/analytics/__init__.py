"""Deterministic non-financial analysis and reconciliation."""

from indian_company_analysis.analytics.engine import FinancialAnalysisEngine
from indian_company_analysis.analytics.ratios import (
    cfo_to_pat_conversion,
    operating_margin,
    revenue_growth,
)
from indian_company_analysis.analytics.reconciliation import FinancialStatementReconciler

__all__ = [
    "FinancialAnalysisEngine",
    "FinancialStatementReconciler",
    "cfo_to_pat_conversion",
    "operating_margin",
    "revenue_growth",
]
