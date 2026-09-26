"""Selection of current, non-superseded financial observations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from indian_company_analysis.domain.enums import PeriodType, ReportingBasis, RestatementStatus
from indian_company_analysis.domain.metrics import MetricId
from indian_company_analysis.domain.models import DemoDataset, MetricObservation, ReportingPeriod


@dataclass(frozen=True, slots=True)
class ObservationIndex:
    observations: tuple[MetricObservation, ...]
    _by_key: dict[tuple[str, MetricId, date, ReportingBasis], MetricObservation]

    @classmethod
    def from_dataset(cls, dataset: DemoDataset) -> ObservationIndex:
        active = tuple(
            observation
            for observation in dataset.observations
            if observation.restatement_status is not RestatementStatus.SUPERSEDED
        )
        return cls(
            observations=active,
            _by_key={
                (
                    observation.company_id,
                    observation.metric_id,
                    observation.period.end_date,
                    observation.reporting_basis,
                ): observation
                for observation in active
            },
        )

    def get(
        self,
        company_id: str,
        metric_id: MetricId,
        period: ReportingPeriod,
        basis: ReportingBasis,
    ) -> MetricObservation | None:
        return self._by_key.get((company_id, metric_id, period.end_date, basis))

    def bases_for(self, company_id: str) -> tuple[ReportingBasis, ...]:
        return tuple(
            sorted(
                {
                    item.reporting_basis
                    for item in self.observations
                    if item.company_id == company_id
                },
                key=str,
            )
        )

    def annual_periods_for(
        self, company_id: str, basis: ReportingBasis
    ) -> tuple[ReportingPeriod, ...]:
        periods = {
            item.period.end_date: item.period
            for item in self.observations
            if item.company_id == company_id
            and item.reporting_basis is basis
            and item.period.period_type is PeriodType.ANNUAL
        }
        return tuple(periods[end_date] for end_date in sorted(periods))


def source_ids(observations: tuple[MetricObservation, ...]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                source_id
                for observation in observations
                for source_id in observation.source_reference_ids
            }
        )
    )


def comparability_error(observations: tuple[MetricObservation, ...]) -> str | None:
    if not observations:
        return None
    companies = {item.company_id for item in observations}
    bases = {item.reporting_basis for item in observations}
    units = {item.unit for item in observations}
    period_types = {item.period.period_type for item in observations}
    if len(companies) != 1:
        return "inputs belong to different companies"
    if len(bases) != 1:
        return "inputs mix consolidated and standalone reporting bases"
    if len(units) != 1:
        return "inputs use different units"
    if period_types != {PeriodType.ANNUAL}:
        return "Phase 1 calculations require annual periods"
    return None
