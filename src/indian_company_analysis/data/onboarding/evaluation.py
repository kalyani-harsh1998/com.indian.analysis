"""Golden-case evaluation for provider-neutral onboarding proposals."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from indian_company_analysis.data.normalization.numbers import parse_reported_decimal
from indian_company_analysis.data.onboarding.contracts import OnboardingProposalProvider
from indian_company_analysis.data.onboarding.models import (
    DocumentOnboardingProposal,
    DocumentOnboardingRequest,
    MetricAggregationComponent,
    ProposalValidationResult,
)
from indian_company_analysis.data.onboarding.validation import validate_onboarding_proposal
from indian_company_analysis.domain.metrics import MetricId
from indian_company_analysis.domain.models import DomainModel

EvaluationQualification = Literal[
    "unqualified",
    "provisional_internal_review",
    "ca_approved_real",
]

_RATE_QUANTUM = Decimal("0.000001")


class ExpectedMappingDecision(DomainModel):
    evidence_id: str = Field(min_length=1)
    metric_id: MetricId
    sign_multiplier: Decimal = Decimal("1")

    @model_validator(mode="after")
    def multiplier_is_sign_only(self) -> ExpectedMappingDecision:
        if self.sign_multiplier not in (Decimal("-1"), Decimal("1")):
            raise ValueError("sign_multiplier must be either -1 or 1")
        return self


class ExpectedAggregationDecision(DomainModel):
    metric_id: MetricId
    components: tuple[MetricAggregationComponent, ...] = Field(min_length=2)


class ExpectedExclusionDecision(DomainModel):
    evidence_id: str = Field(min_length=1)


class ExpectedAbstentionDecision(DomainModel):
    evidence_id: str = Field(min_length=1)


class ExpectedMetricValue(DomainModel):
    metric_id: MetricId
    value: Decimal


class ReconciliationTerm(DomainModel):
    metric_id: MetricId
    coefficient: Decimal


class ReconciliationExpectation(DomainModel):
    reconciliation_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    terms: tuple[ReconciliationTerm, ...] = Field(min_length=2)
    expected_difference: Decimal = Decimal("0")
    tolerance: Decimal = Field(default=Decimal("0.01"), ge=0)

    @model_validator(mode="after")
    def term_metrics_are_unique(self) -> ReconciliationExpectation:
        metric_ids = [term.metric_id for term in self.terms]
        if len(metric_ids) != len(set(metric_ids)):
            raise ValueError("reconciliation expectation contains duplicate metrics")
        return self


class EvaluationThresholds(DomainModel):
    minimum_mapping_precision: Decimal = Field(default=Decimal("1"), ge=0, le=1)
    minimum_mapping_recall: Decimal = Field(default=Decimal("1"), ge=0, le=1)
    minimum_aggregation_precision: Decimal = Field(default=Decimal("1"), ge=0, le=1)
    minimum_aggregation_recall: Decimal = Field(default=Decimal("1"), ge=0, le=1)
    minimum_exclusion_precision: Decimal = Field(default=Decimal("1"), ge=0, le=1)
    minimum_exclusion_recall: Decimal = Field(default=Decimal("1"), ge=0, le=1)
    minimum_abstention_precision: Decimal = Field(default=Decimal("1"), ge=0, le=1)
    minimum_abstention_recall: Decimal = Field(default=Decimal("1"), ge=0, le=1)
    minimum_evidence_coverage: Decimal = Field(default=Decimal("1"), ge=0, le=1)
    maximum_hallucinated_evidence: int = Field(default=0, ge=0)
    require_valid_proposal: bool = True
    require_expected_values: bool = True
    require_reconciliations: bool = True


class OnboardingEvaluationFixture(DomainModel):
    case_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    fixture_version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    request: DocumentOnboardingRequest
    expected_mappings: tuple[ExpectedMappingDecision, ...]
    expected_aggregations: tuple[ExpectedAggregationDecision, ...]
    expected_exclusions: tuple[ExpectedExclusionDecision, ...]
    expected_abstentions: tuple[ExpectedAbstentionDecision, ...] = ()
    expected_metric_values: tuple[ExpectedMetricValue, ...]
    reconciliation_expectations: tuple[ReconciliationExpectation, ...]
    thresholds: EvaluationThresholds = EvaluationThresholds()

    @model_validator(mode="after")
    def golden_decisions_are_complete_and_unique(self) -> OnboardingEvaluationFixture:
        evidence_ids = [mapping.evidence_id for mapping in self.expected_mappings]
        for aggregation in self.expected_aggregations:
            evidence_ids.extend(component.evidence_id for component in aggregation.components)
        evidence_ids.extend(exclusion.evidence_id for exclusion in self.expected_exclusions)
        evidence_ids.extend(abstention.evidence_id for abstention in self.expected_abstentions)
        request_ids = [row.evidence_id for row in self.request.evidence_rows]
        if len(evidence_ids) != len(set(evidence_ids)) or set(evidence_ids) != set(request_ids):
            raise ValueError("golden decisions must dispose of every evidence row exactly once")

        metric_ids = [mapping.metric_id for mapping in self.expected_mappings]
        metric_ids.extend(item.metric_id for item in self.expected_aggregations)
        if len(metric_ids) != len(set(metric_ids)):
            raise ValueError("golden decisions contain duplicate canonical metrics")
        value_metrics = [item.metric_id for item in self.expected_metric_values]
        if len(value_metrics) != len(set(value_metrics)):
            raise ValueError("expected metric values contain duplicate metrics")
        reconciliation_ids = [item.reconciliation_id for item in self.reconciliation_expectations]
        if len(reconciliation_ids) != len(set(reconciliation_ids)):
            raise ValueError("evaluation fixture contains duplicate reconciliation IDs")
        return self


class ProposalAccuracyMetrics(DomainModel):
    evidence_row_count: int = Field(ge=1)
    mapping_expected_count: int = Field(ge=0)
    mapping_proposed_count: int = Field(ge=0)
    mapping_correct_count: int = Field(ge=0)
    mapping_precision: Decimal = Field(ge=0, le=1)
    mapping_recall: Decimal = Field(ge=0, le=1)
    aggregation_expected_count: int = Field(ge=0)
    aggregation_proposed_count: int = Field(ge=0)
    aggregation_correct_count: int = Field(ge=0)
    aggregation_precision: Decimal = Field(ge=0, le=1)
    aggregation_recall: Decimal = Field(ge=0, le=1)
    exclusion_expected_count: int = Field(ge=0)
    exclusion_proposed_count: int = Field(ge=0)
    exclusion_correct_count: int = Field(ge=0)
    exclusion_precision: Decimal = Field(ge=0, le=1)
    exclusion_recall: Decimal = Field(ge=0, le=1)
    abstention_expected_count: int = Field(ge=0)
    abstention_proposed_count: int = Field(ge=0)
    abstention_correct_count: int = Field(ge=0)
    abstention_precision: Decimal = Field(ge=0, le=1)
    abstention_recall: Decimal = Field(ge=0, le=1)
    evidence_coverage: Decimal = Field(ge=0, le=1)
    hallucinated_evidence_count: int = Field(ge=0)
    duplicate_evidence_count: int = Field(ge=0)
    unaccounted_evidence_count: int = Field(ge=0)
    exact_decision_match: bool


class MetricValueComparison(DomainModel):
    metric_id: MetricId
    expected_value: Decimal
    proposed_value: Decimal | None
    matched: bool

    @model_validator(mode="after")
    def match_status_is_consistent(self) -> MetricValueComparison:
        if self.matched != (
            self.proposed_value is not None and self.proposed_value == self.expected_value
        ):
            raise ValueError("metric value match status is inconsistent")
        return self


class ReconciliationEvaluationResult(DomainModel):
    reconciliation_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    difference: Decimal | None
    expected_difference: Decimal
    tolerance: Decimal = Field(ge=0)
    missing_metrics: tuple[MetricId, ...]
    passed: bool

    @model_validator(mode="after")
    def pass_status_is_consistent(self) -> ReconciliationEvaluationResult:
        expected_pass = (
            not self.missing_metrics
            and self.difference is not None
            and abs(self.difference - self.expected_difference) <= self.tolerance
        )
        if self.passed != expected_pass:
            raise ValueError("reconciliation evaluation pass status is inconsistent")
        return self


class OnboardingEvaluationReport(DomainModel):
    case_id: str = Field(min_length=1)
    fixture_version: str = Field(min_length=1)
    evaluation_qualification: EvaluationQualification = "unqualified"
    evaluated_at: datetime
    proposal: DocumentOnboardingProposal
    validation: ProposalValidationResult
    metrics: ProposalAccuracyMetrics
    metric_values: tuple[MetricValueComparison, ...]
    reconciliations: tuple[ReconciliationEvaluationResult, ...]
    thresholds: EvaluationThresholds
    failure_reasons: tuple[str, ...]
    passed: bool

    @model_validator(mode="after")
    def report_status_is_consistent(self) -> OnboardingEvaluationReport:
        if self.evaluated_at.tzinfo is None or self.evaluated_at.utcoffset() is None:
            raise ValueError("evaluation timestamp must include a timezone")
        if self.passed != (not self.failure_reasons):
            raise ValueError("evaluation passes exactly when no failure reasons remain")
        return self


class OnboardingProposalEvaluator:
    """Score one provider proposal against a versioned human-reviewed fixture."""

    def evaluate(
        self,
        fixture: OnboardingEvaluationFixture,
        provider: OnboardingProposalProvider,
        *,
        evaluated_at: datetime,
        evaluation_qualification: EvaluationQualification = "unqualified",
    ) -> OnboardingEvaluationReport:
        proposal = provider.propose(fixture.request)
        validation = validate_onboarding_proposal(fixture.request, proposal)
        metrics = self._accuracy_metrics(fixture, proposal)
        proposed_values = self._proposed_metric_values(fixture.request, proposal)
        value_comparisons = tuple(
            MetricValueComparison(
                metric_id=expected.metric_id,
                expected_value=expected.value,
                proposed_value=proposed_values.get(expected.metric_id),
                matched=proposed_values.get(expected.metric_id) == expected.value,
            )
            for expected in fixture.expected_metric_values
        )
        reconciliations = tuple(
            self._reconcile(expectation, proposed_values)
            for expectation in fixture.reconciliation_expectations
        )
        failure_reasons = self._failure_reasons(
            fixture.thresholds,
            validation,
            metrics,
            value_comparisons,
            reconciliations,
        )
        return OnboardingEvaluationReport(
            case_id=fixture.case_id,
            fixture_version=fixture.fixture_version,
            evaluation_qualification=evaluation_qualification,
            evaluated_at=evaluated_at,
            proposal=proposal,
            validation=validation,
            metrics=metrics,
            metric_values=value_comparisons,
            reconciliations=reconciliations,
            thresholds=fixture.thresholds,
            failure_reasons=failure_reasons,
            passed=not failure_reasons,
        )

    @staticmethod
    def persist(report: OnboardingEvaluationReport, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        serialized = report.model_dump_json(indent=2) + "\n"
        if output.exists() and output.read_text(encoding="utf-8") != serialized:
            raise ValueError(f"refusing to overwrite different evaluation report: {output}")
        output.write_text(serialized, encoding="utf-8")

    def _accuracy_metrics(
        self,
        fixture: OnboardingEvaluationFixture,
        proposal: DocumentOnboardingProposal,
    ) -> ProposalAccuracyMetrics:
        expected_mappings = {
            (item.evidence_id, item.metric_id, item.sign_multiplier)
            for item in fixture.expected_mappings
        }
        proposed_mappings = {
            (item.evidence_id, item.metric_id, item.sign_multiplier) for item in proposal.mappings
        }
        expected_aggregations = {
            self._aggregation_key(item.metric_id, item.components)
            for item in fixture.expected_aggregations
        }
        proposed_aggregations = {
            self._aggregation_key(item.metric_id, item.components) for item in proposal.aggregations
        }
        expected_exclusions = {item.evidence_id for item in fixture.expected_exclusions}
        proposed_exclusions = {item.evidence_id for item in proposal.exclusions}
        expected_abstentions = {item.evidence_id for item in fixture.expected_abstentions}
        proposed_abstentions = {item.evidence_id for item in proposal.abstentions}

        proposed_uses = [item.evidence_id for item in proposal.mappings]
        for aggregation in proposal.aggregations:
            proposed_uses.extend(component.evidence_id for component in aggregation.components)
        proposed_uses.extend(item.evidence_id for item in proposal.exclusions)
        proposed_uses.extend(item.evidence_id for item in proposal.abstentions)
        request_ids = {row.evidence_id for row in fixture.request.evidence_rows}
        use_counts = Counter(proposed_uses)
        known_used = request_ids & set(proposed_uses)
        hallucinated = set(proposed_uses) - request_ids
        mapping_correct = len(expected_mappings & proposed_mappings)
        aggregation_correct = len(expected_aggregations & proposed_aggregations)
        exclusion_correct = len(expected_exclusions & proposed_exclusions)
        abstention_correct = len(expected_abstentions & proposed_abstentions)

        return ProposalAccuracyMetrics(
            evidence_row_count=len(request_ids),
            mapping_expected_count=len(expected_mappings),
            mapping_proposed_count=len(proposed_mappings),
            mapping_correct_count=mapping_correct,
            mapping_precision=self._rate(
                mapping_correct, len(proposed_mappings), len(expected_mappings)
            ),
            mapping_recall=self._rate(
                mapping_correct, len(expected_mappings), len(expected_mappings)
            ),
            aggregation_expected_count=len(expected_aggregations),
            aggregation_proposed_count=len(proposed_aggregations),
            aggregation_correct_count=aggregation_correct,
            aggregation_precision=self._rate(
                aggregation_correct, len(proposed_aggregations), len(expected_aggregations)
            ),
            aggregation_recall=self._rate(
                aggregation_correct, len(expected_aggregations), len(expected_aggregations)
            ),
            exclusion_expected_count=len(expected_exclusions),
            exclusion_proposed_count=len(proposed_exclusions),
            exclusion_correct_count=exclusion_correct,
            exclusion_precision=self._rate(
                exclusion_correct, len(proposed_exclusions), len(expected_exclusions)
            ),
            exclusion_recall=self._rate(
                exclusion_correct, len(expected_exclusions), len(expected_exclusions)
            ),
            abstention_expected_count=len(expected_abstentions),
            abstention_proposed_count=len(proposed_abstentions),
            abstention_correct_count=abstention_correct,
            abstention_precision=self._rate(
                abstention_correct, len(proposed_abstentions), len(expected_abstentions)
            ),
            abstention_recall=self._rate(
                abstention_correct, len(expected_abstentions), len(expected_abstentions)
            ),
            evidence_coverage=(Decimal(len(known_used)) / Decimal(len(request_ids))).quantize(
                _RATE_QUANTUM
            ),
            hallucinated_evidence_count=len(hallucinated),
            duplicate_evidence_count=sum(1 for count in use_counts.values() if count > 1),
            unaccounted_evidence_count=len(request_ids - known_used),
            exact_decision_match=(
                expected_mappings == proposed_mappings
                and expected_aggregations == proposed_aggregations
                and expected_exclusions == proposed_exclusions
                and expected_abstentions == proposed_abstentions
            ),
        )

    @staticmethod
    def _aggregation_key(
        metric_id: MetricId,
        components: tuple[MetricAggregationComponent, ...],
    ) -> tuple[MetricId, tuple[tuple[str, Decimal], ...]]:
        return (
            metric_id,
            tuple(sorted((item.evidence_id, item.coefficient) for item in components)),
        )

    @staticmethod
    def _rate(correct: int, denominator: int, expected_count: int) -> Decimal:
        if denominator == 0:
            return Decimal("1.000000") if expected_count == 0 else Decimal("0.000000")
        return (Decimal(correct) / Decimal(denominator)).quantize(_RATE_QUANTUM)

    @staticmethod
    def _proposed_metric_values(
        request: DocumentOnboardingRequest,
        proposal: DocumentOnboardingProposal,
    ) -> dict[MetricId, Decimal]:
        evidence_by_id = {row.evidence_id: row for row in request.evidence_rows}
        values: dict[MetricId, Decimal] = {}
        duplicate_metrics: set[MetricId] = set()
        for mapping in proposal.mappings:
            evidence = evidence_by_id.get(mapping.evidence_id)
            if evidence is None or evidence.reported_label != mapping.reported_label:
                continue
            try:
                value = parse_reported_decimal(evidence.raw_value) * mapping.sign_multiplier
            except ValueError:
                continue
            if mapping.metric_id in values:
                duplicate_metrics.add(mapping.metric_id)
            else:
                values[mapping.metric_id] = value
        for aggregation in proposal.aggregations:
            contributions: list[Decimal] = []
            for component in aggregation.components:
                evidence = evidence_by_id.get(component.evidence_id)
                if evidence is None:
                    contributions = []
                    break
                try:
                    contributions.append(
                        parse_reported_decimal(evidence.raw_value) * component.coefficient
                    )
                except ValueError:
                    contributions = []
                    break
            if len(contributions) != len(aggregation.components):
                continue
            if aggregation.metric_id in values:
                duplicate_metrics.add(aggregation.metric_id)
            else:
                values[aggregation.metric_id] = sum(contributions, Decimal("0"))
        for metric_id in duplicate_metrics:
            values.pop(metric_id, None)
        return values

    @staticmethod
    def _reconcile(
        expectation: ReconciliationExpectation,
        values: dict[MetricId, Decimal],
    ) -> ReconciliationEvaluationResult:
        missing = tuple(
            term.metric_id for term in expectation.terms if term.metric_id not in values
        )
        difference = None
        if not missing:
            difference = sum(
                (values[term.metric_id] * term.coefficient for term in expectation.terms),
                Decimal("0"),
            )
        passed = (
            difference is not None
            and abs(difference - expectation.expected_difference) <= expectation.tolerance
        )
        return ReconciliationEvaluationResult(
            reconciliation_id=expectation.reconciliation_id,
            description=expectation.description,
            difference=difference,
            expected_difference=expectation.expected_difference,
            tolerance=expectation.tolerance,
            missing_metrics=missing,
            passed=passed,
        )

    @staticmethod
    def _failure_reasons(
        thresholds: EvaluationThresholds,
        validation: ProposalValidationResult,
        metrics: ProposalAccuracyMetrics,
        values: tuple[MetricValueComparison, ...],
        reconciliations: tuple[ReconciliationEvaluationResult, ...],
    ) -> tuple[str, ...]:
        reasons: list[str] = []
        checks = (
            (metrics.mapping_precision, thresholds.minimum_mapping_precision, "mapping precision"),
            (metrics.mapping_recall, thresholds.minimum_mapping_recall, "mapping recall"),
            (
                metrics.aggregation_precision,
                thresholds.minimum_aggregation_precision,
                "aggregation precision",
            ),
            (
                metrics.aggregation_recall,
                thresholds.minimum_aggregation_recall,
                "aggregation recall",
            ),
            (
                metrics.exclusion_precision,
                thresholds.minimum_exclusion_precision,
                "exclusion precision",
            ),
            (
                metrics.exclusion_recall,
                thresholds.minimum_exclusion_recall,
                "exclusion recall",
            ),
            (
                metrics.abstention_precision,
                thresholds.minimum_abstention_precision,
                "abstention precision",
            ),
            (
                metrics.abstention_recall,
                thresholds.minimum_abstention_recall,
                "abstention recall",
            ),
            (
                metrics.evidence_coverage,
                thresholds.minimum_evidence_coverage,
                "evidence coverage",
            ),
        )
        for actual, required, label in checks:
            if actual < required:
                reasons.append(f"{label} {actual} is below required {required}")
        if metrics.hallucinated_evidence_count > thresholds.maximum_hallucinated_evidence:
            reasons.append("hallucinated evidence exceeds the permitted maximum")
        if thresholds.require_valid_proposal and not validation.ready_for_review:
            reasons.append("proposal failed deterministic validation")
        if thresholds.require_expected_values and any(not item.matched for item in values):
            reasons.append("one or more expected canonical values did not match")
        if thresholds.require_reconciliations and any(not item.passed for item in reconciliations):
            reasons.append("one or more accounting reconciliations did not pass")
        return tuple(reasons)
