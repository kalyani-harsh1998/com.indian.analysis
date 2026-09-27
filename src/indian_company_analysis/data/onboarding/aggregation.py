"""Deterministic execution of reviewed component aggregation rules."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field, model_validator

from indian_company_analysis.data.normalization.models import SourceFactLocator
from indian_company_analysis.data.normalization.numbers import parse_reported_decimal
from indian_company_analysis.data.onboarding.models import (
    ApprovedAggregationRule,
    ApprovedOnboardingConfiguration,
    DocumentOnboardingRequest,
    OnboardingEvidenceRow,
)
from indian_company_analysis.data.onboarding.validation import validate_configuration_identity
from indian_company_analysis.domain.enums import ValueClassification
from indian_company_analysis.domain.metrics import MetricId
from indian_company_analysis.domain.models import DomainModel, MetricObservation


class AggregationComponentLineage(DomainModel):
    """Parsed contribution of one immutable source row to an aggregate."""

    evidence_id: str = Field(min_length=1)
    source_locator: SourceFactLocator
    reported_label: str = Field(min_length=1)
    raw_value: str = Field(min_length=1)
    parsed_value: Decimal
    coefficient: Decimal
    contribution: Decimal

    @model_validator(mode="after")
    def contribution_matches_inputs(self) -> AggregationComponentLineage:
        if self.coefficient not in (Decimal("-1"), Decimal("1")):
            raise ValueError("aggregation coefficient must be either -1 or 1")
        if self.contribution != self.parsed_value * self.coefficient:
            raise ValueError("aggregation contribution must equal value times coefficient")
        return self


class AggregatedNormalizedFact(DomainModel):
    """Calculated canonical fact with source-component and approval lineage."""

    fact_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_reference_id: str = Field(min_length=1)
    observation: MetricObservation
    configuration_version: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    rule_id: str = Field(min_length=1)
    rule_version: str = Field(min_length=1)
    formula: str = Field(min_length=1)
    components: tuple[AggregationComponentLineage, ...] = Field(min_length=2)
    reviewed_by: str = Field(min_length=1)
    reviewed_at: datetime
    approval_policy_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def observation_and_components_are_consistent(self) -> AggregatedNormalizedFact:
        if self.observation.value_classification is not ValueClassification.CALCULATED:
            raise ValueError("aggregated observations must be classified as calculated")
        if self.source_reference_id not in self.observation.source_reference_ids:
            raise ValueError("aggregated observation must retain its source reference")
        expected_value = sum(
            (component.contribution for component in self.components), Decimal("0")
        )
        if self.observation.value != expected_value:
            raise ValueError("aggregated observation value must equal component contributions")
        return self


class AggregationExecutionIssue(DomainModel):
    """Reason one approved aggregation rule could not be executed."""

    rule_id: str = Field(min_length=1)
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    evidence_id: str | None = None


class AggregationExecutionResult(DomainModel):
    """Execution outcome for all approved aggregation rules in one configuration."""

    document_id: str = Field(min_length=1)
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    configuration_version: str = Field(min_length=1)
    total_rules: int = Field(ge=1)
    facts: tuple[AggregatedNormalizedFact, ...]
    issues: tuple[AggregationExecutionIssue, ...]
    ready_for_analysis: bool

    @model_validator(mode="after")
    def result_counts_and_readiness_are_consistent(self) -> AggregationExecutionResult:
        if self.total_rules != len(self.facts) + len(self.issues):
            raise ValueError("every aggregation rule must produce one fact or one issue")
        if self.ready_for_analysis != (not self.issues):
            raise ValueError("ready_for_analysis requires no aggregation execution issues")
        return self


class _RuleExecutionError(ValueError):
    def __init__(self, code: str, message: str, evidence_id: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.evidence_id = evidence_id


def execute_approved_aggregations(
    request: DocumentOnboardingRequest,
    configuration: ApprovedOnboardingConfiguration,
) -> AggregationExecutionResult:
    """Execute reviewed signed-sum rules without model arithmetic or inference."""

    validate_configuration_identity(request, configuration)
    if not configuration.aggregation_rules:
        raise ValueError("approved configuration contains no aggregation rules")
    if configuration.normalization_blockers:
        raise ValueError("approved configuration still contains normalization blockers")

    evidence_by_id = {row.evidence_id: row for row in request.evidence_rows}
    used_evidence: set[str] = set()
    used_metrics: set[MetricId] = set()
    facts: list[AggregatedNormalizedFact] = []
    issues: list[AggregationExecutionIssue] = []

    for rule in configuration.aggregation_rules:
        try:
            if rule.metric_id in used_metrics:
                raise _RuleExecutionError(
                    "duplicate_metric_target",
                    "more than one aggregation rule targets the same canonical metric",
                )
            duplicated_evidence = next(
                (
                    component.evidence_id
                    for component in rule.components
                    if component.evidence_id in used_evidence
                ),
                None,
            )
            if duplicated_evidence is not None:
                raise _RuleExecutionError(
                    "duplicate_evidence_use",
                    "source evidence is consumed by more than one aggregation rule",
                    duplicated_evidence,
                )
            used_metrics.add(rule.metric_id)
            used_evidence.update(component.evidence_id for component in rule.components)
            fact = _execute_rule(request, configuration, rule, evidence_by_id)
        except _RuleExecutionError as error:
            issues.append(
                AggregationExecutionIssue(
                    rule_id=rule.rule_id,
                    code=error.code,
                    message=str(error),
                    evidence_id=error.evidence_id,
                )
            )
            continue

        facts.append(fact)

    return AggregationExecutionResult(
        document_id=request.document_id,
        source_checksum_sha256=request.source_checksum_sha256,
        configuration_version=configuration.configuration_version,
        total_rules=len(configuration.aggregation_rules),
        facts=tuple(facts),
        issues=tuple(issues),
        ready_for_analysis=not issues,
    )


def _execute_rule(
    request: DocumentOnboardingRequest,
    configuration: ApprovedOnboardingConfiguration,
    rule: ApprovedAggregationRule,
    evidence_by_id: dict[str, OnboardingEvidenceRow],
) -> AggregatedNormalizedFact:
    components: list[AggregationComponentLineage] = []
    for approved_component in rule.components:
        evidence = evidence_by_id.get(approved_component.evidence_id)
        if evidence is None:
            raise _RuleExecutionError(
                "unknown_evidence",
                "approved aggregation references evidence absent from the request",
                approved_component.evidence_id,
            )
        if (
            evidence.source_locator != approved_component.source_locator
            or evidence.reported_label != approved_component.reported_label
            or evidence.raw_value != approved_component.raw_value
        ):
            raise _RuleExecutionError(
                "evidence_snapshot_mismatch",
                "request evidence differs from the human-approved source snapshot",
                approved_component.evidence_id,
            )
        try:
            parsed_value = parse_reported_decimal(evidence.raw_value)
        except ValueError as error:
            raise _RuleExecutionError(
                "invalid_numeric_value",
                str(error),
                approved_component.evidence_id,
            ) from error
        components.append(
            AggregationComponentLineage(
                evidence_id=approved_component.evidence_id,
                source_locator=evidence.source_locator,
                reported_label=evidence.reported_label,
                raw_value=evidence.raw_value,
                parsed_value=parsed_value,
                coefficient=approved_component.coefficient,
                contribution=parsed_value * approved_component.coefficient,
            )
        )

    value = sum((component.contribution for component in components), Decimal("0"))
    fact_id = f"{request.document_id}:aggregation:{rule.rule_id}"
    formula = " + ".join(
        f"{component.coefficient}*{component.evidence_id}" for component in components
    )
    observation = MetricObservation(
        observation_id=fact_id,
        company_id=request.company_id,
        metric_id=rule.metric_id,
        value=value,
        unit=request.unit,
        period=request.period,
        reporting_basis=request.reporting_basis,
        value_classification=ValueClassification.CALCULATED,
        source_reference_ids=(request.source_reference_id,),
    )
    return AggregatedNormalizedFact(
        fact_id=fact_id,
        document_id=request.document_id,
        source_checksum_sha256=request.source_checksum_sha256,
        source_reference_id=request.source_reference_id,
        observation=observation,
        configuration_version=configuration.configuration_version,
        proposal_id=configuration.proposal_id,
        rule_id=rule.rule_id,
        rule_version=rule.rule_version,
        formula=formula,
        components=tuple(components),
        reviewed_by=configuration.reviewed_by,
        reviewed_at=configuration.reviewed_at,
        approval_policy_version=configuration.approval_policy_version,
    )
