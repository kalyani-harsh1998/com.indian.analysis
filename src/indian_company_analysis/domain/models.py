"""Validated business objects for evidence-backed company analysis."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from indian_company_analysis.domain.enums import (
    AnalysisMode,
    CalculationStatus,
    ConfidenceLevel,
    PeriodType,
    ReconciliationStatus,
    ReconciliationType,
    ReportingBasis,
    RestatementStatus,
    ScenarioName,
    SourceKind,
    ValueClassification,
)
from indian_company_analysis.domain.metrics import MetricId


class DomainModel(BaseModel):
    """Immutable, strict base for domain records."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class CompanyIdentifier(DomainModel):
    company_id: str = Field(min_length=1)
    legal_name: str = Field(min_length=1)
    nse_symbol: str | None = Field(default=None, pattern=r"^[A-Z0-9&-]+$")
    bse_scrip_code: str | None = Field(default=None, pattern=r"^\d{6}$")
    isin: str | None = Field(default=None, pattern=r"^IN[A-Z0-9]{10}$")

    @model_validator(mode="after")
    def require_market_identifier(self) -> CompanyIdentifier:
        if not any((self.nse_symbol, self.bse_scrip_code, self.isin)):
            raise ValueError("at least one exchange or security identifier is required")
        return self


class AnalysisRequest(DomainModel):
    company: CompanyIdentifier
    peers: tuple[CompanyIdentifier, ...] = ()
    mode: AnalysisMode = AnalysisMode.INVESTOR
    as_of_date: date


class ReportingPeriod(DomainModel):
    label: str = Field(min_length=1)
    period_type: PeriodType
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def dates_are_ordered(self) -> ReportingPeriod:
        if self.end_date < self.start_date:
            raise ValueError("reporting period end date must not precede start date")
        return self


class SourceReference(DomainModel):
    source_id: str = Field(min_length=1)
    source_kind: SourceKind
    source_organization: str = Field(min_length=1)
    source_document: str = Field(min_length=1)
    locator: str = Field(min_length=1)
    retrieval_timestamp: datetime
    publication_date: date | None = None
    checksum_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    parser_version: str | None = None
    is_synthetic: bool = False

    @model_validator(mode="after")
    def synthetic_flag_matches_kind(self) -> SourceReference:
        if (self.source_kind is SourceKind.SYNTHETIC) != self.is_synthetic:
            raise ValueError("synthetic source kind and is_synthetic flag must agree")
        return self


class MetricObservation(DomainModel):
    observation_id: str = Field(min_length=1)
    company_id: str = Field(min_length=1)
    metric_id: MetricId
    value: Decimal
    unit: str = Field(min_length=1)
    period: ReportingPeriod
    reporting_basis: ReportingBasis
    value_classification: ValueClassification
    source_reference_ids: tuple[str, ...] = Field(min_length=1)
    revision_number: int = Field(default=0, ge=0)
    restatement_status: RestatementStatus = RestatementStatus.ORIGINAL
    supersedes_observation_id: str | None = None

    @model_validator(mode="after")
    def restatement_fields_are_consistent(self) -> MetricObservation:
        if self.restatement_status is RestatementStatus.RESTATED:
            if self.revision_number < 1 or self.supersedes_observation_id is None:
                raise ValueError(
                    "restated observations require a positive revision and superseded ID"
                )
        elif self.supersedes_observation_id is not None:
            raise ValueError("only restated observations may identify a superseded observation")
        return self


class AdjustmentRecord(DomainModel):
    adjustment_id: str = Field(min_length=1)
    company_id: str = Field(min_length=1)
    metric_id: MetricId
    period: ReportingPeriod
    reporting_basis: ReportingBasis
    original_observation_id: str = Field(min_length=1)
    adjustment_amount: Decimal
    adjusted_value: Decimal
    rationale: str = Field(min_length=1)
    source_reference_ids: tuple[str, ...] = Field(min_length=1)


class CalculationResult(DomainModel):
    calculation_id: str = Field(min_length=1)
    company_id: str = Field(min_length=1)
    metric_id: MetricId
    period: ReportingPeriod
    reporting_basis: ReportingBasis
    status: CalculationStatus
    value: Decimal | None = None
    unit: str = Field(min_length=1)
    formula: str = Field(min_length=1)
    formula_version: str = Field(min_length=1)
    input_observation_ids: tuple[str, ...]
    source_reference_ids: tuple[str, ...]
    message: str | None = None
    value_classification: ValueClassification = ValueClassification.CALCULATED

    @model_validator(mode="after")
    def status_matches_value(self) -> CalculationResult:
        if self.status is CalculationStatus.SUCCESS and self.value is None:
            raise ValueError("successful calculations require a value")
        if self.status is not CalculationStatus.SUCCESS and self.value is not None:
            raise ValueError("unsuccessful calculations must not expose a value")
        return self


class ReconciliationResult(DomainModel):
    reconciliation_id: str = Field(min_length=1)
    company_id: str = Field(min_length=1)
    reconciliation_type: ReconciliationType
    period: ReportingPeriod
    reporting_basis: ReportingBasis
    status: ReconciliationStatus
    difference: Decimal | None = None
    tolerance: Decimal = Field(ge=0)
    input_observation_ids: tuple[str, ...]
    source_reference_ids: tuple[str, ...]
    message: str = Field(min_length=1)


class PeerCandidate(DomainModel):
    company: CompanyIdentifier
    rationale: str = Field(min_length=1)
    similarity_score: Decimal = Field(ge=0, le=1)
    evidence_reference_ids: tuple[str, ...] = Field(min_length=1)


class AnalyticalFinding(DomainModel):
    finding_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    observation: str = Field(min_length=1)
    materiality: str = Field(min_length=1)
    evidence_reference_ids: tuple[str, ...] = Field(min_length=1)
    confidence: ConfidenceLevel


class ForecastAssumption(DomainModel):
    assumption_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    value: Decimal | str
    unit: str | None = None
    evidence_reference_ids: tuple[str, ...] = Field(min_length=1)
    confidence: ConfidenceLevel


class ForecastScenario(DomainModel):
    scenario: ScenarioName
    horizon_years: int = Field(ge=1, le=10)
    assumptions: tuple[ForecastAssumption, ...] = Field(min_length=1)
    model_version: str = Field(min_length=1)
    confidence: ConfidenceLevel


class Recommendation(DomainModel):
    recommendation_id: str = Field(min_length=1)
    observation: str = Field(min_length=1)
    evidence_reference_ids: tuple[str, ...] = Field(min_length=1)
    materiality: str = Field(min_length=1)
    root_cause_hypotheses: tuple[str, ...] = Field(min_length=1)
    proposed_action: str = Field(min_length=1)
    value_creation_mechanism: str = Field(min_length=1)
    estimated_impact_range: str = Field(min_length=1)
    time_horizon: str = Field(min_length=1)
    implementation_difficulty: str = Field(min_length=1)
    dependencies: tuple[str, ...]
    internal_information_required: tuple[str, ...]
    kpis: tuple[str, ...] = Field(min_length=1)
    confidence: ConfidenceLevel
    is_outside_in_hypothesis: bool = True


class AnalysisRunManifest(DomainModel):
    run_id: str = Field(min_length=1)
    workflow_name: str = Field(min_length=1)
    workflow_version: str = Field(min_length=1)
    started_at: datetime
    completed_at: datetime
    request: AnalysisRequest
    input_dataset_name: str = Field(min_length=1)
    input_data_version: str = Field(min_length=1)
    input_source_ids: tuple[str, ...] = Field(min_length=1)
    source_kinds: frozenset[SourceKind] = Field(min_length=1)
    calculation_count: int = Field(ge=0)
    successful_calculation_count: int = Field(ge=0)
    reconciliation_count: int = Field(ge=0)
    data_is_synthetic: bool
    disclaimer: str = Field(min_length=1)

    @model_validator(mode="after")
    def timestamps_are_ordered(self) -> AnalysisRunManifest:
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must not precede started_at")
        if (SourceKind.SYNTHETIC in self.source_kinds) != self.data_is_synthetic:
            raise ValueError("data_is_synthetic must reflect the declared source kinds")
        return self


class DemoDataset(DomainModel):
    dataset_name: str = Field(min_length=1)
    dataset_version: str = Field(min_length=1)
    analysis_as_of_date: date
    primary_company_id: str = Field(min_length=1)
    peer_company_ids: tuple[str, ...]
    companies: tuple[CompanyIdentifier, ...] = Field(min_length=1)
    source_references: tuple[SourceReference, ...] = Field(min_length=1)
    observations: tuple[MetricObservation, ...] = Field(min_length=1)
    adjustments: tuple[AdjustmentRecord, ...] = ()

    @model_validator(mode="after")
    def references_are_consistent(self) -> DemoDataset:
        company_ids = {company.company_id for company in self.companies}
        requested_ids = {self.primary_company_id, *self.peer_company_ids}
        if not requested_ids <= company_ids:
            raise ValueError("primary company and every peer must exist in companies")

        source_ids = {source.source_id for source in self.source_references}
        observations_by_id = {
            observation.observation_id: observation for observation in self.observations
        }
        observation_ids = set(observations_by_id)
        active_keys: set[tuple[str, MetricId, date, ReportingBasis]] = set()
        for observation in self.observations:
            if observation.company_id not in company_ids:
                raise ValueError(f"unknown company_id on observation: {observation.company_id}")
            if not set(observation.source_reference_ids) <= source_ids:
                raise ValueError(
                    f"unknown source reference on observation: {observation.observation_id}"
                )
            if (
                observation.supersedes_observation_id is not None
                and observation.supersedes_observation_id not in observation_ids
            ):
                raise ValueError(
                    f"unknown superseded observation: {observation.supersedes_observation_id}"
                )
            if observation.restatement_status is not RestatementStatus.SUPERSEDED:
                key = (
                    observation.company_id,
                    observation.metric_id,
                    observation.period.end_date,
                    observation.reporting_basis,
                )
                if key in active_keys:
                    raise ValueError(f"duplicate active observation for {key}")
                active_keys.add(key)

        for adjustment in self.adjustments:
            if adjustment.original_observation_id not in observation_ids:
                raise ValueError(
                    f"unknown adjusted observation: {adjustment.original_observation_id}"
                )
            if not set(adjustment.source_reference_ids) <= source_ids:
                raise ValueError(
                    f"unknown source reference on adjustment: {adjustment.adjustment_id}"
                )
            original = observations_by_id[adjustment.original_observation_id]
            if (
                adjustment.company_id != original.company_id
                or adjustment.metric_id is not original.metric_id
                or adjustment.period != original.period
                or adjustment.reporting_basis is not original.reporting_basis
            ):
                raise ValueError(
                    f"adjustment context differs from observation: {adjustment.adjustment_id}"
                )
            if original.value + adjustment.adjustment_amount != adjustment.adjusted_value:
                raise ValueError(f"adjusted value does not reconcile: {adjustment.adjustment_id}")
        return self


class AnalysisResult(DomainModel):
    manifest: AnalysisRunManifest
    source_references: tuple[SourceReference, ...] = Field(min_length=1)
    reported_observations: tuple[MetricObservation, ...]
    calculations: tuple[CalculationResult, ...]
    reconciliations: tuple[ReconciliationResult, ...]
    adjustments: tuple[AdjustmentRecord, ...]
