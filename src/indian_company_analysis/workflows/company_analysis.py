"""Thin source-aware company-analysis workflow for the synthetic POC."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from indian_company_analysis.analytics.ratios import (
    cfo_to_pat_conversion,
    operating_margin,
    revenue_growth,
)
from indian_company_analysis.data.catalog import SourceCatalog
from indian_company_analysis.data.contracts import DataSource
from indian_company_analysis.data.provenance import validate_observation_provenance
from indian_company_analysis.domain.enums import ReportingBasis, SourceKind, ValueClassification
from indian_company_analysis.domain.exceptions import MissingMetricError
from indian_company_analysis.domain.models import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisRunManifest,
    CompanyIdentifier,
    DemoDataset,
    MetricObservation,
    ReportingPeriod,
)

Clock = Callable[[], datetime]
RunIdFactory = Callable[[], str]


class CompanyAnalysisWorkflow:
    """Calculate three demo ratios while retaining source-reference lineage."""

    WORKFLOW_NAME = "synthetic_company_analysis"
    WORKFLOW_VERSION = "0.1.0"
    DISCLAIMER = (
        "Synthetic demonstration data only. Not investment, audit, tax, legal, "
        "or regulated financial advice."
    )

    def __init__(
        self,
        source: DataSource,
        *,
        clock: Clock | None = None,
        run_id_factory: RunIdFactory | None = None,
    ) -> None:
        self._source = source
        self._clock = clock or (lambda: datetime.now(UTC))
        self._run_id_factory = run_id_factory or (lambda: str(uuid4()))

    def run(self) -> AnalysisResult:
        started_at = self._clock()
        dataset = self._source.load()
        catalog = SourceCatalog.from_references(dataset.source_references)
        validate_observation_provenance(dataset.observations, catalog.source_ids)
        calculated = tuple(
            self._calculate_company_metrics(dataset, company) for company in dataset.companies
        )
        observations = tuple(item for company_items in calculated for item in company_items)
        request = self._build_request(dataset)
        source_kinds = frozenset(source.source_kind for source in dataset.source_references)
        completed_at = self._clock()
        manifest = AnalysisRunManifest(
            run_id=self._run_id_factory(),
            workflow_name=self.WORKFLOW_NAME,
            workflow_version=self.WORKFLOW_VERSION,
            started_at=started_at,
            completed_at=completed_at,
            request=request,
            input_dataset_name=dataset.dataset_name,
            input_data_version=dataset.dataset_version,
            input_source_ids=tuple(sorted(catalog.source_ids)),
            source_kinds=source_kinds,
            output_observation_count=len(observations),
            data_is_synthetic=SourceKind.SYNTHETIC in source_kinds,
            disclaimer=self.DISCLAIMER,
        )
        return AnalysisResult(
            manifest=manifest,
            source_references=dataset.source_references,
            observations=observations,
        )

    def _build_request(self, dataset: DemoDataset) -> AnalysisRequest:
        companies = {company.company_id: company for company in dataset.companies}
        return AnalysisRequest(
            company=companies[dataset.primary_company_id],
            peers=tuple(companies[company_id] for company_id in dataset.peer_company_ids),
            as_of_date=dataset.analysis_as_of_date,
        )

    def _calculate_company_metrics(
        self, dataset: DemoDataset, company: CompanyIdentifier
    ) -> tuple[MetricObservation, ...]:
        company_observations = [
            observation
            for observation in dataset.observations
            if observation.company_id == company.company_id
        ]
        revenue_observations = sorted(
            (item for item in company_observations if item.metric_id == "revenue"),
            key=lambda item: item.period.end_date,
        )
        if len(revenue_observations) < 2:
            raise MissingMetricError(f"two revenue periods are required for {company.company_id}")
        prior_revenue, current_revenue = revenue_observations[-2:]
        period = current_revenue.period
        basis = current_revenue.reporting_basis

        operating_profit = self._find(company_observations, "operating_profit", period)
        cfo = self._find(company_observations, "cash_flow_from_operations", period)
        pat = self._find(company_observations, "profit_after_tax", period)

        definitions = (
            (
                "revenue_growth",
                revenue_growth(current_revenue.value, prior_revenue.value),
                (current_revenue, prior_revenue),
            ),
            (
                "operating_margin",
                operating_margin(operating_profit.value, current_revenue.value),
                (operating_profit, current_revenue),
            ),
            (
                "cfo_to_pat_conversion",
                cfo_to_pat_conversion(cfo.value, pat.value),
                (cfo, pat),
            ),
        )
        results: list[MetricObservation] = []
        for metric_id, value, inputs in definitions:
            if value is None:
                continue
            results.append(
                self._calculated_observation(
                    company.company_id, metric_id, value, period, basis, inputs
                )
            )
        return tuple(results)

    @staticmethod
    def _find(
        observations: list[MetricObservation], metric_id: str, period: ReportingPeriod
    ) -> MetricObservation:
        for observation in observations:
            if observation.metric_id == metric_id and observation.period == period:
                return observation
        raise MissingMetricError(f"required metric {metric_id} is missing for {period.label}")

    @staticmethod
    def _calculated_observation(
        company_id: str,
        metric_id: str,
        value: Decimal,
        period: ReportingPeriod,
        reporting_basis: ReportingBasis,
        inputs: tuple[MetricObservation, ...],
    ) -> MetricObservation:
        source_ids = tuple(
            sorted({source_id for item in inputs for source_id in item.source_reference_ids})
        )
        return MetricObservation(
            observation_id=f"{company_id}:{metric_id}:{period.end_date.isoformat()}",
            company_id=company_id,
            metric_id=metric_id,
            value=value,
            unit="ratio",
            period=period,
            reporting_basis=reporting_basis,
            value_classification=ValueClassification.CALCULATED,
            source_reference_ids=source_ids,
        )
