from datetime import date
from decimal import Decimal

import pytest

from indian_company_analysis.data.provenance import validate_observation_provenance
from indian_company_analysis.domain.enums import PeriodType, ReportingBasis, ValueClassification
from indian_company_analysis.domain.exceptions import ProvenanceError
from indian_company_analysis.domain.models import MetricObservation, ReportingPeriod


def test_unknown_source_reference_is_rejected() -> None:
    observation = MetricObservation(
        observation_id="example:revenue:fy2026",
        company_id="example",
        metric_id="revenue",
        value=Decimal("100"),
        unit="INR million",
        period=ReportingPeriod(
            label="FY2026",
            period_type=PeriodType.ANNUAL,
            start_date=date(2025, 4, 1),
            end_date=date(2026, 3, 31),
        ),
        reporting_basis=ReportingBasis.CONSOLIDATED,
        value_classification=ValueClassification.REPORTED,
        source_reference_ids=("missing",),
    )

    with pytest.raises(ProvenanceError, match="unknown sources"):
        validate_observation_provenance((observation,), frozenset({"known"}))
