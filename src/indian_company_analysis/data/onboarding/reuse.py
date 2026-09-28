"""Deterministic, review-only comparison of an approved configuration to a new filing."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from indian_company_analysis.data.onboarding.models import (
    ApprovedOnboardingConfiguration,
    DocumentOnboardingRequest,
    OnboardingEvidenceRow,
)
from indian_company_analysis.domain.metrics import MetricId
from indian_company_analysis.domain.models import DomainModel


class ReuseContextDifference(DomainModel):
    """One source-context difference between a prior configuration and new request."""

    field_name: str = Field(min_length=1)
    source_value: str = Field(min_length=1)
    target_value: str = Field(min_length=1)
    blocks_candidate_reuse: bool


class DecisionReuseAssessment(DomainModel):
    """Comparison of one prior decision to the target filing's extracted evidence."""

    source_decision_type: Literal["direct_mapping", "aggregation_rule", "exclusion"]
    source_decision_id: str = Field(min_length=1)
    source_metric_id: MetricId | None = None
    source_evidence_ids: tuple[str, ...] = Field(min_length=1)
    source_reported_labels: tuple[str, ...] = Field(min_length=1)
    target_evidence_ids: tuple[str, ...] = ()
    outcome: Literal[
        "reusable_candidate",
        "missing_evidence",
        "ambiguous_evidence",
        "incompatible_context",
    ]
    reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def decision_evidence_is_consistent(self) -> DecisionReuseAssessment:
        if len(self.source_evidence_ids) != len(self.source_reported_labels):
            raise ValueError("source evidence IDs and labels must have the same length")
        if self.outcome == "reusable_candidate":
            if len(self.target_evidence_ids) != len(self.source_evidence_ids):
                raise ValueError("reusable candidate must match every source evidence row once")
            if self.reasons:
                raise ValueError("reusable candidate must not contain blocking reasons")
        elif not self.reasons:
            raise ValueError("non-reusable decision assessment requires one or more reasons")
        return self


class OnboardingReuseAssessment(DomainModel):
    """Auditable comparison only; it can never authorize automatic configuration reuse."""

    assessment_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    assessed_at: datetime
    source_configuration: ApprovedOnboardingConfiguration
    target_request: DocumentOnboardingRequest
    context_differences: tuple[ReuseContextDifference, ...]
    decision_assessments: tuple[DecisionReuseAssessment, ...]
    new_evidence_rows: tuple[OnboardingEvidenceRow, ...]
    requires_human_approval: Literal[True] = True

    @model_validator(mode="after")
    def assessment_is_complete(self) -> OnboardingReuseAssessment:
        if self.assessed_at.tzinfo is None or self.assessed_at.utcoffset() is None:
            raise ValueError("reuse assessment timestamp must include a timezone")
        decision_ids = [item.source_decision_id for item in self.decision_assessments]
        if len(decision_ids) != len(set(decision_ids)):
            raise ValueError("reuse assessment contains duplicate source decisions")
        source_ids = {
            *(mapping.evidence_id for mapping in self.source_configuration.direct_mappings),
            *(
                component.evidence_id
                for rule in self.source_configuration.aggregation_rules
                for component in rule.components
            ),
            *(exclusion.evidence_id for exclusion in self.source_configuration.exclusions),
        }
        assessed_ids = {
            evidence_id
            for assessment in self.decision_assessments
            for evidence_id in assessment.source_evidence_ids
        }
        if assessed_ids != source_ids:
            raise ValueError(
                "reuse assessment must compare every source configuration evidence row"
            )
        return self

    @property
    def reusable_candidate_count(self) -> int:
        return sum(
            assessment.outcome == "reusable_candidate" for assessment in self.decision_assessments
        )

    @property
    def review_required_count(self) -> int:
        return len(self.decision_assessments) - self.reusable_candidate_count


class OnboardingReuseAssessor:
    """Compare exact evidence labels without applying a prior configuration automatically."""

    def assess(
        self,
        source_configuration: ApprovedOnboardingConfiguration,
        target_request: DocumentOnboardingRequest,
        *,
        assessment_id: str,
        assessed_at: datetime,
    ) -> OnboardingReuseAssessment:
        context_differences = self._context_differences(source_configuration, target_request)
        has_blocking_context_difference = any(
            difference.blocks_candidate_reuse for difference in context_differences
        )
        evidence_by_label: dict[str, list[OnboardingEvidenceRow]] = defaultdict(list)
        for row in target_request.evidence_rows:
            evidence_by_label[row.reported_label].append(row)

        assessments = self._decision_assessments(
            source_configuration,
            evidence_by_label,
            has_blocking_context_difference=has_blocking_context_difference,
        )
        assessments = self._mark_cross_decision_conflicts(assessments)
        source_labels = {mapping.reported_label for mapping in source_configuration.direct_mappings}
        source_labels.update(
            component.reported_label
            for rule in source_configuration.aggregation_rules
            for component in rule.components
        )
        source_labels.update(
            exclusion.reported_label for exclusion in source_configuration.exclusions
        )
        new_rows = tuple(
            row for row in target_request.evidence_rows if row.reported_label not in source_labels
        )
        return OnboardingReuseAssessment(
            assessment_id=assessment_id,
            assessed_at=assessed_at,
            source_configuration=source_configuration,
            target_request=target_request,
            context_differences=context_differences,
            decision_assessments=assessments,
            new_evidence_rows=new_rows,
        )

    @staticmethod
    def persist(assessment: OnboardingReuseAssessment, output: Path) -> None:
        output.parent.mkdir(parents=True, exist_ok=True)
        serialized = assessment.model_dump_json(indent=2) + "\n"
        if output.exists() and output.read_text(encoding="utf-8") != serialized:
            raise ValueError(f"refusing to overwrite different reuse assessment: {output}")
        output.write_text(serialized, encoding="utf-8")

    @staticmethod
    def _context_differences(
        source: ApprovedOnboardingConfiguration,
        target: DocumentOnboardingRequest,
    ) -> tuple[ReuseContextDifference, ...]:
        fields = (
            ("company_id", source.company_id, target.company_id, True),
            ("source_organization", source.source_organization, target.source_organization, True),
            ("document_type", source.document_type.value, target.document_type.value, True),
            ("unit", source.unit, target.unit, True),
            ("reporting_basis", source.reporting_basis.value, target.reporting_basis.value, True),
            (
                "extraction_profile_version",
                source.extraction_profile_version,
                target.extraction_profile_version,
                True,
            ),
            ("request_id", source.request_id, target.request_id, False),
            ("document_id", source.document_id, target.document_id, False),
            ("extraction_id", source.extraction_id, target.extraction_id, False),
            ("source_reference_id", source.source_reference_id, target.source_reference_id, False),
            (
                "source_checksum_sha256",
                source.source_checksum_sha256,
                target.source_checksum_sha256,
                False,
            ),
            ("period", source.period.label, target.period.label, False),
        )
        return tuple(
            ReuseContextDifference(
                field_name=field_name,
                source_value=str(source_value),
                target_value=str(target_value),
                blocks_candidate_reuse=blocks_candidate_reuse,
            )
            for field_name, source_value, target_value, blocks_candidate_reuse in fields
            if source_value != target_value
        )

    def _decision_assessments(
        self,
        configuration: ApprovedOnboardingConfiguration,
        evidence_by_label: dict[str, list[OnboardingEvidenceRow]],
        *,
        has_blocking_context_difference: bool,
    ) -> tuple[DecisionReuseAssessment, ...]:
        assessments: list[DecisionReuseAssessment] = []
        for mapping in configuration.direct_mappings:
            assessments.append(
                self._assess_decision(
                    source_decision_type="direct_mapping",
                    source_decision_id=mapping.candidate_id,
                    source_metric_id=mapping.metric_id,
                    source_evidence_ids=(mapping.evidence_id,),
                    source_labels=(mapping.reported_label,),
                    evidence_by_label=evidence_by_label,
                    has_blocking_context_difference=has_blocking_context_difference,
                )
            )
        for rule in configuration.aggregation_rules:
            assessments.append(
                self._assess_decision(
                    source_decision_type="aggregation_rule",
                    source_decision_id=rule.rule_id,
                    source_metric_id=rule.metric_id,
                    source_evidence_ids=tuple(
                        component.evidence_id for component in rule.components
                    ),
                    source_labels=tuple(component.reported_label for component in rule.components),
                    evidence_by_label=evidence_by_label,
                    has_blocking_context_difference=has_blocking_context_difference,
                )
            )
        for exclusion in configuration.exclusions:
            assessments.append(
                self._assess_decision(
                    source_decision_type="exclusion",
                    source_decision_id=f"exclusion-{exclusion.evidence_id}",
                    source_metric_id=None,
                    source_evidence_ids=(exclusion.evidence_id,),
                    source_labels=(exclusion.reported_label,),
                    evidence_by_label=evidence_by_label,
                    has_blocking_context_difference=has_blocking_context_difference,
                )
            )
        return tuple(assessments)

    @staticmethod
    def _assess_decision(
        *,
        source_decision_type: Literal["direct_mapping", "aggregation_rule", "exclusion"],
        source_decision_id: str,
        source_metric_id: MetricId | None,
        source_evidence_ids: tuple[str, ...],
        source_labels: tuple[str, ...],
        evidence_by_label: dict[str, list[OnboardingEvidenceRow]],
        has_blocking_context_difference: bool,
    ) -> DecisionReuseAssessment:
        if has_blocking_context_difference:
            return DecisionReuseAssessment(
                source_decision_type=source_decision_type,
                source_decision_id=source_decision_id,
                source_metric_id=source_metric_id,
                source_evidence_ids=source_evidence_ids,
                source_reported_labels=source_labels,
                outcome="incompatible_context",
                reasons=("company, statement context, or extraction profile is incompatible",),
            )
        target_rows = [evidence_by_label[label] for label in source_labels]
        missing_labels = [
            label for label, rows in zip(source_labels, target_rows, strict=True) if not rows
        ]
        if missing_labels:
            return DecisionReuseAssessment(
                source_decision_type=source_decision_type,
                source_decision_id=source_decision_id,
                source_metric_id=source_metric_id,
                source_evidence_ids=source_evidence_ids,
                source_reported_labels=source_labels,
                outcome="missing_evidence",
                reasons=(f"missing target labels: {', '.join(missing_labels)}",),
            )
        ambiguous_labels = [
            label for label, rows in zip(source_labels, target_rows, strict=True) if len(rows) != 1
        ]
        if ambiguous_labels:
            ambiguous_ids = tuple(row.evidence_id for rows in target_rows for row in rows)
            return DecisionReuseAssessment(
                source_decision_type=source_decision_type,
                source_decision_id=source_decision_id,
                source_metric_id=source_metric_id,
                source_evidence_ids=source_evidence_ids,
                source_reported_labels=source_labels,
                target_evidence_ids=ambiguous_ids,
                outcome="ambiguous_evidence",
                reasons=(f"ambiguous target labels: {', '.join(ambiguous_labels)}",),
            )
        return DecisionReuseAssessment(
            source_decision_type=source_decision_type,
            source_decision_id=source_decision_id,
            source_metric_id=source_metric_id,
            source_evidence_ids=source_evidence_ids,
            source_reported_labels=source_labels,
            target_evidence_ids=tuple(rows[0].evidence_id for rows in target_rows),
            outcome="reusable_candidate",
        )

    @staticmethod
    def _mark_cross_decision_conflicts(
        assessments: tuple[DecisionReuseAssessment, ...],
    ) -> tuple[DecisionReuseAssessment, ...]:
        target_use_counts = Counter(
            evidence_id
            for assessment in assessments
            if assessment.outcome == "reusable_candidate"
            for evidence_id in assessment.target_evidence_ids
        )
        return tuple(
            assessment.model_copy(
                update={
                    "outcome": "ambiguous_evidence",
                    "reasons": ("target evidence would be reused by multiple source decisions",),
                }
            )
            if assessment.outcome == "reusable_candidate"
            and any(
                target_use_counts[evidence_id] > 1 for evidence_id in assessment.target_evidence_ids
            )
            else assessment
            for assessment in assessments
        )
