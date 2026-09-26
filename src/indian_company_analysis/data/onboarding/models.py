"""Strict records for model-assisted document onboarding and review."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field, model_validator

from indian_company_analysis.data.normalization.models import (
    MetricMappingSet,
    SourceFactLocator,
)
from indian_company_analysis.domain.enums import (
    ConfidenceLevel,
    DocumentType,
    ReportingBasis,
)
from indian_company_analysis.domain.metrics import MetricId
from indian_company_analysis.domain.models import DomainModel, ReportingPeriod


class OnboardingEvidenceRow(DomainModel):
    """One extracted source row made available for semantic interpretation."""

    evidence_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]*$")
    source_locator: SourceFactLocator
    reported_label: str = Field(min_length=1)
    raw_value: str = Field(min_length=1)


class DocumentOnboardingRequest(DomainModel):
    """Checksummed evidence and accounting context sent to a proposal provider."""

    request_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    document_id: str = Field(min_length=1)
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_organization: str = Field(min_length=1)
    document_type: DocumentType
    unit: str = Field(min_length=1)
    period: ReportingPeriod
    reporting_basis: ReportingBasis
    evidence_rows: tuple[OnboardingEvidenceRow, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def evidence_is_unique(self) -> DocumentOnboardingRequest:
        evidence_ids = [row.evidence_id for row in self.evidence_rows]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("onboarding request contains duplicate evidence IDs")
        locators = [
            (
                row.source_locator.page_number,
                row.source_locator.table_id,
                row.source_locator.row_number,
                row.source_locator.column_name,
            )
            for row in self.evidence_rows
        ]
        if len(locators) != len(set(locators)):
            raise ValueError("onboarding request contains duplicate source locators")
        return self


class ModelRunProvenance(DomainModel):
    """Identity of the model invocation that produced a proposal."""

    provider: str = Field(min_length=1)
    model_id: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    generated_at: datetime

    @model_validator(mode="after")
    def timestamp_is_timezone_aware(self) -> ModelRunProvenance:
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise ValueError("model generation timestamp must include a timezone")
        return self


class MappingCandidate(DomainModel):
    """Proposed one-to-one mapping from an evidence row to a canonical metric."""

    candidate_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]*$")
    evidence_id: str = Field(min_length=1)
    reported_label: str = Field(min_length=1)
    metric_id: MetricId
    sign_multiplier: Decimal = Decimal("1")
    confidence: ConfidenceLevel
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def multiplier_is_sign_only(self) -> MappingCandidate:
        if self.sign_multiplier not in (Decimal("-1"), Decimal("1")):
            raise ValueError("sign_multiplier must be either -1 or 1")
        return self


class MetricAggregationComponent(DomainModel):
    """One source row and coefficient in a proposed aggregation."""

    evidence_id: str = Field(min_length=1)
    coefficient: Decimal = Decimal("1")

    @model_validator(mode="after")
    def coefficient_is_sign_only(self) -> MetricAggregationComponent:
        if self.coefficient not in (Decimal("-1"), Decimal("1")):
            raise ValueError("aggregation coefficient must be either -1 or 1")
        return self


class MetricAggregationCandidate(DomainModel):
    """Proposed many-to-one mapping; execution remains deterministic future work."""

    candidate_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]*$")
    metric_id: MetricId
    components: tuple[MetricAggregationComponent, ...] = Field(min_length=2)
    confidence: ConfidenceLevel
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def component_evidence_is_unique(self) -> MetricAggregationCandidate:
        evidence_ids = [component.evidence_id for component in self.components]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("aggregation candidate contains duplicate evidence IDs")
        return self


class ExclusionCandidate(DomainModel):
    """Explicit proposal not to map an extracted row into the canonical model."""

    evidence_id: str = Field(min_length=1)
    confidence: ConfidenceLevel
    rationale: str = Field(min_length=1)


class DocumentOnboardingProposal(DomainModel):
    """A model-produced candidate configuration; never an approved fact source."""

    proposal_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    request_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_organization: str = Field(min_length=1)
    document_type: DocumentType
    model_run: ModelRunProvenance
    mappings: tuple[MappingCandidate, ...] = ()
    aggregations: tuple[MetricAggregationCandidate, ...] = ()
    exclusions: tuple[ExclusionCandidate, ...] = ()

    @model_validator(mode="after")
    def candidate_identity_is_unique(self) -> DocumentOnboardingProposal:
        candidate_ids = [candidate.candidate_id for candidate in self.mappings]
        candidate_ids.extend(candidate.candidate_id for candidate in self.aggregations)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("onboarding proposal contains duplicate candidate IDs")
        exclusion_ids = [candidate.evidence_id for candidate in self.exclusions]
        if len(exclusion_ids) != len(set(exclusion_ids)):
            raise ValueError("onboarding proposal contains duplicate exclusion evidence IDs")
        return self


class ProposalValidationIssue(DomainModel):
    """Deterministic reason a model proposal cannot advance to review."""

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    candidate_id: str | None = None
    evidence_id: str | None = None


class ProposalValidationResult(DomainModel):
    """Deterministic validation result for one proposal/request pair."""

    request_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    validated_mapping_ids: tuple[str, ...]
    validated_aggregation_ids: tuple[str, ...]
    validated_exclusion_evidence_ids: tuple[str, ...]
    issues: tuple[ProposalValidationIssue, ...]
    ready_for_review: bool

    @model_validator(mode="after")
    def readiness_matches_issues(self) -> ProposalValidationResult:
        if self.ready_for_review != (not self.issues):
            raise ValueError("ready_for_review requires no proposal validation issues")
        return self


class ApprovedAggregationRule(DomainModel):
    """Human-approved aggregation semantics awaiting deterministic execution."""

    rule_id: str = Field(min_length=1)
    rule_version: str = Field(min_length=1)
    metric_id: MetricId
    components: tuple[MetricAggregationComponent, ...] = Field(min_length=2)
    rationale: str = Field(min_length=1)
    source_proposal_id: str = Field(min_length=1)


class ApprovedOnboardingConfiguration(DomainModel):
    """Reviewed model proposal with explicit support limits for normalization."""

    configuration_version: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    model_run: ModelRunProvenance
    mapping_set: MetricMappingSet | None
    aggregation_rules: tuple[ApprovedAggregationRule, ...]
    excluded_evidence_ids: tuple[str, ...]
    reviewed_by: str = Field(min_length=1)
    reviewed_at: datetime
    approval_policy_version: str = Field(min_length=1)
    normalization_blockers: tuple[str, ...]
    ready_for_normalization: bool

    @model_validator(mode="after")
    def readiness_and_review_are_consistent(self) -> ApprovedOnboardingConfiguration:
        if self.reviewed_at.tzinfo is None or self.reviewed_at.utcoffset() is None:
            raise ValueError("review timestamp must include a timezone")
        if self.ready_for_normalization != (not self.normalization_blockers):
            raise ValueError("ready_for_normalization requires no normalization blockers")
        return self
