from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from indian_company_analysis.domain.enums import (
    CalculationStatus,
    ConfidenceLevel,
    PeriodType,
    ReportingBasis,
    RestatementStatus,
    SourceKind,
    ValueClassification,
)
from indian_company_analysis.domain.models import (
    CalculationResult,
    CompanyIdentifier,
    ForecastAssumption,
    ForecastScenario,
    MetricObservation,
    ReportingPeriod,
    SourceReference,
)


def _annual_period() -> ReportingPeriod:
    return ReportingPeriod(
        label="FY2026",
        period_type=PeriodType.ANNUAL,
        start_date=date(2025, 4, 1),
        end_date=date(2026, 3, 31),
    )


def test_company_requires_a_market_identifier() -> None:
    with pytest.raises(ValidationError, match="at least one exchange"):
        CompanyIdentifier(company_id="example", legal_name="Example Limited")


def test_observation_requires_provenance() -> None:
    with pytest.raises(ValidationError):
        MetricObservation(
            observation_id="example:revenue:fy2026",
            company_id="example",
            metric_id="revenue",
            value=Decimal("100"),
            unit="INR million",
            period=_annual_period(),
            reporting_basis=ReportingBasis.CONSOLIDATED,
            value_classification=ValueClassification.REPORTED,
            source_reference_ids=(),
        )


def test_synthetic_source_requires_explicit_flag() -> None:
    with pytest.raises(ValidationError, match="synthetic source kind"):
        SourceReference(
            source_id="demo",
            source_kind=SourceKind.SYNTHETIC,
            source_organization="Example",
            source_document="Fixture",
            locator="fixture.json",
            retrieval_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            is_synthetic=False,
        )


def test_scenario_enum_rejects_unknown_value() -> None:
    assumption = ForecastAssumption(
        assumption_id="growth",
        name="Growth",
        description="Synthetic assumption used only for enum validation",
        value=Decimal("0.10"),
        unit="ratio",
        evidence_reference_ids=("demo",),
        confidence=ConfidenceLevel.LOW,
    )
    with pytest.raises(ValidationError):
        ForecastScenario(
            scenario="optimistic",
            horizon_years=3,
            assumptions=(assumption,),
            model_version="test",
            confidence=ConfidenceLevel.LOW,
        )


def test_restated_observation_requires_revision_and_superseded_id() -> None:
    with pytest.raises(ValidationError, match="restated observations require"):
        MetricObservation(
            observation_id="example:revenue:restated",
            company_id="example",
            metric_id="revenue",
            value=Decimal("100"),
            unit="INR million",
            period=_annual_period(),
            reporting_basis=ReportingBasis.CONSOLIDATED,
            value_classification=ValueClassification.REPORTED,
            source_reference_ids=("source",),
            restatement_status=RestatementStatus.RESTATED,
        )


def test_unsuccessful_calculation_cannot_expose_a_value() -> None:
    with pytest.raises(ValidationError, match="must not expose a value"):
        CalculationResult(
            calculation_id="example:revenue_growth:fy2026",
            company_id="example",
            metric_id="revenue_growth",
            period=_annual_period(),
            reporting_basis=ReportingBasis.CONSOLIDATED,
            status=CalculationStatus.MISSING_INPUT,
            value=Decimal("0"),
            unit="ratio",
            formula="current / prior - 1",
            formula_version="test",
            input_observation_ids=(),
            source_reference_ids=(),
        )
