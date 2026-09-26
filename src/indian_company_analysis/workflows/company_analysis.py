"""Source-aware deterministic company-analysis workflow."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from indian_company_analysis.analytics.engine import FinancialAnalysisEngine
from indian_company_analysis.analytics.reconciliation import FinancialStatementReconciler
from indian_company_analysis.data.catalog import SourceCatalog
from indian_company_analysis.data.contracts import DataSource
from indian_company_analysis.data.provenance import validate_observation_provenance
from indian_company_analysis.domain.enums import CalculationStatus, SourceKind
from indian_company_analysis.domain.models import (
    AnalysisRequest,
    AnalysisResult,
    AnalysisRunManifest,
    DemoDataset,
)

Clock = Callable[[], datetime]
RunIdFactory = Callable[[], str]


class CompanyAnalysisWorkflow:
    """Reconcile statements and calculate Phase 1 metrics with full lineage."""

    WORKFLOW_NAME = "synthetic_company_analysis"
    WORKFLOW_VERSION = "1.0.0"
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
        engine: FinancialAnalysisEngine | None = None,
        reconciler: FinancialStatementReconciler | None = None,
    ) -> None:
        self._source = source
        self._clock = clock or (lambda: datetime.now(UTC))
        self._run_id_factory = run_id_factory or (lambda: str(uuid4()))
        self._engine = engine or FinancialAnalysisEngine()
        self._reconciler = reconciler or FinancialStatementReconciler()

    def run(self) -> AnalysisResult:
        started_at = self._clock()
        dataset = self._source.load()
        catalog = SourceCatalog.from_references(dataset.source_references)
        validate_observation_provenance(dataset.observations, catalog.source_ids)
        calculations = self._engine.analyze(dataset)
        reconciliations = self._reconciler.reconcile(dataset)
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
            calculation_count=len(calculations),
            successful_calculation_count=sum(
                item.status is CalculationStatus.SUCCESS for item in calculations
            ),
            reconciliation_count=len(reconciliations),
            data_is_synthetic=SourceKind.SYNTHETIC in source_kinds,
            disclaimer=self.DISCLAIMER,
        )
        return AnalysisResult(
            manifest=manifest,
            source_references=dataset.source_references,
            reported_observations=dataset.observations,
            calculations=calculations,
            reconciliations=reconciliations,
            adjustments=dataset.adjustments,
        )

    def _build_request(self, dataset: DemoDataset) -> AnalysisRequest:
        companies = {company.company_id: company for company in dataset.companies}
        return AnalysisRequest(
            company=companies[dataset.primary_company_id],
            peers=tuple(companies[company_id] for company_id in dataset.peer_company_ids),
            as_of_date=dataset.analysis_as_of_date,
        )
