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
    extraction_id: str = Field(min_length=1)
    extraction_profile_version: str = Field(min_length=1)
    company_id: str = Field(min_length=1)
    source_reference_id: str = Field(min_length=1)
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
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    latency_milliseconds: int | None = Field(default=None, ge=0)
    estimated_cost: Decimal | None = Field(default=None, ge=0)
    cost_currency: str | None = Field(default=None, min_length=3, max_length=3)

    @model_validator(mode="after")
    def provenance_is_consistent(self) -> ModelRunProvenance:
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise ValueError("model generation timestamp must include a timezone")
        if (self.estimated_cost is None) != (self.cost_currency is None):
            raise ValueError("estimated model cost and currency must be supplied together")
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


class AbstentionCandidate(DomainModel):
    """Explicit model deferral of one evidence row to a human reviewer."""

    candidate_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]*$")
    evidence_id: str = Field(min_length=1)
    confidence: ConfidenceLevel
    rationale: str = Field(min_length=1)


class DocumentOnboardingProposal(DomainModel):
    """A model-produced candidate configuration; never an approved fact source."""

    proposal_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    request_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    extraction_id: str = Field(min_length=1)
    extraction_profile_version: str = Field(min_length=1)
    company_id: str = Field(min_length=1)
    source_reference_id: str = Field(min_length=1)
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_organization: str = Field(min_length=1)
    document_type: DocumentType
    model_run: ModelRunProvenance
    mappings: tuple[MappingCandidate, ...] = ()
    aggregations: tuple[MetricAggregationCandidate, ...] = ()
    exclusions: tuple[ExclusionCandidate, ...] = ()
    abstentions: tuple[AbstentionCandidate, ...] = ()

    @model_validator(mode="after")
    def candidate_identity_is_unique(self) -> DocumentOnboardingProposal:
        candidate_ids = [candidate.candidate_id for candidate in self.mappings]
        candidate_ids.extend(candidate.candidate_id for candidate in self.aggregations)
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("onboarding proposal contains duplicate candidate IDs")
        exclusion_ids = [candidate.evidence_id for candidate in self.exclusions]
        if len(exclusion_ids) != len(set(exclusion_ids)):
            raise ValueError("onboarding proposal contains duplicate exclusion evidence IDs")
        abstention_ids = [candidate.evidence_id for candidate in self.abstentions]
        if len(abstention_ids) != len(set(abstention_ids)):
            raise ValueError("onboarding proposal contains duplicate abstention evidence IDs")
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
    validated_abstention_ids: tuple[str, ...]
    issues: tuple[ProposalValidationIssue, ...]
    ready_for_review: bool

    @model_validator(mode="after")
    def readiness_matches_issues(self) -> ProposalValidationResult:
        if self.ready_for_review != (not self.issues):
            raise ValueError("ready_for_review requires no proposal validation issues")
        return self


class ApprovedDirectMapping(DomainModel):
    """Human-approved direct mapping with its exact evidence snapshot."""

    candidate_id: str = Field(min_length=1)
    evidence_id: str = Field(min_length=1)
    source_locator: SourceFactLocator
    reported_label: str = Field(min_length=1)
    raw_value: str = Field(min_length=1)
    metric_id: MetricId
    sign_multiplier: Decimal
    confidence: ConfidenceLevel
    rationale: str = Field(min_length=1)
    source_proposal_id: str = Field(min_length=1)

    @model_validator(mode="after")
    def multiplier_is_sign_only(self) -> ApprovedDirectMapping:
        if self.sign_multiplier not in (Decimal("-1"), Decimal("1")):
            raise ValueError("sign_multiplier must be either -1 or 1")
        return self


class ApprovedAggregationComponent(DomainModel):
    """Approved aggregation input with a frozen copy of its source evidence."""

    evidence_id: str = Field(min_length=1)
    source_locator: SourceFactLocator
    reported_label: str = Field(min_length=1)
    raw_value: str = Field(min_length=1)
    coefficient: Decimal

    @model_validator(mode="after")
    def coefficient_is_sign_only(self) -> ApprovedAggregationComponent:
        if self.coefficient not in (Decimal("-1"), Decimal("1")):
            raise ValueError("aggregation coefficient must be either -1 or 1")
        return self


class ApprovedAggregationRule(DomainModel):
    """Human-approved aggregation semantics and source-row evidence."""

    rule_id: str = Field(min_length=1)
    rule_version: str = Field(min_length=1)
    metric_id: MetricId
    components: tuple[ApprovedAggregationComponent, ...] = Field(min_length=2)
    confidence: ConfidenceLevel
    rationale: str = Field(min_length=1)
    source_proposal_id: str = Field(min_length=1)


class ApprovedExclusion(DomainModel):
    """Human-approved decision not to map one source row."""

    evidence_id: str = Field(min_length=1)
    source_locator: SourceFactLocator
    reported_label: str = Field(min_length=1)
    raw_value: str = Field(min_length=1)
    confidence: ConfidenceLevel
    rationale: str = Field(min_length=1)
    source_proposal_id: str = Field(min_length=1)


class ApprovedOnboardingConfiguration(DomainModel):
    """Reviewed model proposal with explicit support limits for normalization."""

    configuration_version: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    extraction_id: str = Field(min_length=1)
    extraction_profile_version: str = Field(min_length=1)
    company_id: str = Field(min_length=1)
    source_reference_id: str = Field(min_length=1)
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_organization: str = Field(min_length=1)
    document_type: DocumentType
    unit: str = Field(min_length=1)
    period: ReportingPeriod
    reporting_basis: ReportingBasis
    model_run: ModelRunProvenance
    mapping_set: MetricMappingSet | None
    direct_mappings: tuple[ApprovedDirectMapping, ...]
    aggregation_rules: tuple[ApprovedAggregationRule, ...]
    exclusions: tuple[ApprovedExclusion, ...]
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
        if (self.mapping_set is None) != (not self.direct_mappings):
            raise ValueError("mapping_set must exist exactly when direct mappings exist")
        if self.mapping_set is not None:
            if self.mapping_set.source_organization != self.source_organization:
                raise ValueError("mapping set source organization must match the configuration")
            if self.mapping_set.document_type is not self.document_type:
                raise ValueError("mapping set document type must match the configuration")
            if len(self.mapping_set.mappings) != len(self.direct_mappings):
                raise ValueError("mapping set must retain every approved direct mapping")
            for mapping, approved in zip(
                self.mapping_set.mappings, self.direct_mappings, strict=True
            ):
                if (
                    mapping.reported_label != approved.reported_label
                    or mapping.metric_id is not approved.metric_id
                    or mapping.sign_multiplier != approved.sign_multiplier
                    or mapping.confidence is not approved.confidence
                    or mapping.rationale != approved.rationale
                ):
                    raise ValueError("mapping set differs from approved direct mapping evidence")

        evidence_ids = [mapping.evidence_id for mapping in self.direct_mappings]
        for rule in self.aggregation_rules:
            evidence_ids.extend(component.evidence_id for component in rule.components)
        evidence_ids.extend(exclusion.evidence_id for exclusion in self.exclusions)
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("approved configuration reuses source evidence")

        metric_ids = [mapping.metric_id for mapping in self.direct_mappings]
        metric_ids.extend(rule.metric_id for rule in self.aggregation_rules)
        if len(metric_ids) != len(set(metric_ids)):
            raise ValueError("approved configuration contains duplicate canonical metrics")
        if not metric_ids:
            raise ValueError("approved configuration requires a mapping or aggregation rule")

        decision_ids = [mapping.candidate_id for mapping in self.direct_mappings]
        decision_ids.extend(rule.rule_id for rule in self.aggregation_rules)
        if len(decision_ids) != len(set(decision_ids)):
            raise ValueError("approved configuration contains duplicate decision IDs")

        proposal_ids = {
            *(mapping.source_proposal_id for mapping in self.direct_mappings),
            *(rule.source_proposal_id for rule in self.aggregation_rules),
            *(exclusion.source_proposal_id for exclusion in self.exclusions),
        }
        if proposal_ids != {self.proposal_id}:
            raise ValueError("all approved decisions must reference the configuration proposal")
        return self
