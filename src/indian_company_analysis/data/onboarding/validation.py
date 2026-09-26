"""Deterministic validation for model-produced onboarding proposals."""

from collections import defaultdict

from indian_company_analysis.data.onboarding.models import (
    DocumentOnboardingProposal,
    DocumentOnboardingRequest,
    ProposalValidationIssue,
    ProposalValidationResult,
)
from indian_company_analysis.domain.enums import MetricNature
from indian_company_analysis.domain.metrics import METRIC_DEFINITIONS, MetricId


def validate_onboarding_proposal(
    request: DocumentOnboardingRequest,
    proposal: DocumentOnboardingProposal,
) -> ProposalValidationResult:
    """Verify proposal identity, evidence use, labels, and canonical metric semantics."""

    issues: list[ProposalValidationIssue] = []
    _validate_identity(request, proposal, issues)

    evidence_by_id = {row.evidence_id: row for row in request.evidence_rows}
    evidence_users: dict[str, list[str]] = defaultdict(list)
    target_users: dict[MetricId, list[str]] = defaultdict(list)

    for mapping_candidate in proposal.mappings:
        evidence = evidence_by_id.get(mapping_candidate.evidence_id)
        if evidence is None:
            issues.append(
                ProposalValidationIssue(
                    code="unknown_evidence",
                    message="mapping references evidence that is not in the onboarding request",
                    candidate_id=mapping_candidate.candidate_id,
                    evidence_id=mapping_candidate.evidence_id,
                )
            )
        else:
            evidence_users[mapping_candidate.evidence_id].append(mapping_candidate.candidate_id)
            if mapping_candidate.reported_label != evidence.reported_label:
                issues.append(
                    ProposalValidationIssue(
                        code="reported_label_mismatch",
                        message="mapping label does not exactly match its source evidence row",
                        candidate_id=mapping_candidate.candidate_id,
                        evidence_id=mapping_candidate.evidence_id,
                    )
                )
        _validate_reported_metric(
            mapping_candidate.metric_id, mapping_candidate.candidate_id, issues
        )
        target_users[mapping_candidate.metric_id].append(mapping_candidate.candidate_id)

    for aggregation_candidate in proposal.aggregations:
        _validate_reported_metric(
            aggregation_candidate.metric_id,
            aggregation_candidate.candidate_id,
            issues,
        )
        target_users[aggregation_candidate.metric_id].append(aggregation_candidate.candidate_id)
        for component in aggregation_candidate.components:
            if component.evidence_id not in evidence_by_id:
                issues.append(
                    ProposalValidationIssue(
                        code="unknown_evidence",
                        message=(
                            "aggregation references evidence that is not in the onboarding request"
                        ),
                        candidate_id=aggregation_candidate.candidate_id,
                        evidence_id=component.evidence_id,
                    )
                )
            else:
                evidence_users[component.evidence_id].append(aggregation_candidate.candidate_id)

    for exclusion in proposal.exclusions:
        if exclusion.evidence_id not in evidence_by_id:
            issues.append(
                ProposalValidationIssue(
                    code="unknown_evidence",
                    message="exclusion references evidence that is not in the onboarding request",
                    evidence_id=exclusion.evidence_id,
                )
            )
        else:
            evidence_users[exclusion.evidence_id].append("exclusion")

    for evidence_id, users in evidence_users.items():
        if len(users) > 1:
            issues.append(
                ProposalValidationIssue(
                    code="duplicate_evidence_use",
                    message="source evidence is consumed by more than one proposal decision",
                    evidence_id=evidence_id,
                )
            )

    for evidence_row in request.evidence_rows:
        if evidence_row.evidence_id not in evidence_users:
            issues.append(
                ProposalValidationIssue(
                    code="unaccounted_evidence",
                    message=(
                        "source evidence is neither mapped, aggregated, nor explicitly excluded"
                    ),
                    evidence_id=evidence_row.evidence_id,
                )
            )

    for metric_id, candidate_ids in target_users.items():
        if len(candidate_ids) > 1:
            for candidate_id in candidate_ids:
                issues.append(
                    ProposalValidationIssue(
                        code="duplicate_metric_target",
                        message=(
                            f"more than one candidate targets canonical metric {metric_id.value}"
                        ),
                        candidate_id=candidate_id,
                    )
                )

    if not proposal.mappings and not proposal.aggregations:
        issues.append(
            ProposalValidationIssue(
                code="no_metric_candidates",
                message="proposal must contain at least one mapping or aggregation candidate",
            )
        )

    invalid_candidate_ids = {
        issue.candidate_id for issue in issues if issue.candidate_id is not None
    }
    invalid_evidence_ids = {issue.evidence_id for issue in issues if issue.evidence_id is not None}
    validated_mapping_ids = tuple(
        candidate.candidate_id
        for candidate in proposal.mappings
        if candidate.candidate_id not in invalid_candidate_ids
        and candidate.evidence_id not in invalid_evidence_ids
    )
    validated_aggregation_ids = tuple(
        candidate.candidate_id
        for candidate in proposal.aggregations
        if candidate.candidate_id not in invalid_candidate_ids
        and not any(
            component.evidence_id in invalid_evidence_ids for component in candidate.components
        )
    )
    validated_exclusion_evidence_ids = tuple(
        exclusion.evidence_id
        for exclusion in proposal.exclusions
        if exclusion.evidence_id not in invalid_evidence_ids
    )
    return ProposalValidationResult(
        request_id=request.request_id,
        proposal_id=proposal.proposal_id,
        validated_mapping_ids=validated_mapping_ids,
        validated_aggregation_ids=validated_aggregation_ids,
        validated_exclusion_evidence_ids=validated_exclusion_evidence_ids,
        issues=tuple(issues),
        ready_for_review=not issues,
    )


def _validate_identity(
    request: DocumentOnboardingRequest,
    proposal: DocumentOnboardingProposal,
    issues: list[ProposalValidationIssue],
) -> None:
    identity_fields = (
        ("request_id", request.request_id, proposal.request_id),
        ("document_id", request.document_id, proposal.document_id),
        ("company_id", request.company_id, proposal.company_id),
        (
            "source_reference_id",
            request.source_reference_id,
            proposal.source_reference_id,
        ),
        (
            "source_checksum_sha256",
            request.source_checksum_sha256,
            proposal.source_checksum_sha256,
        ),
        ("source_organization", request.source_organization, proposal.source_organization),
        ("document_type", request.document_type, proposal.document_type),
    )
    for field_name, expected, actual in identity_fields:
        if actual != expected:
            issues.append(
                ProposalValidationIssue(
                    code="proposal_identity_mismatch",
                    message=f"proposal {field_name} does not match the onboarding request",
                )
            )


def _validate_reported_metric(
    metric_id: MetricId,
    candidate_id: str,
    issues: list[ProposalValidationIssue],
) -> None:
    if METRIC_DEFINITIONS[metric_id].nature is MetricNature.DERIVED:
        issues.append(
            ProposalValidationIssue(
                code="derived_metric_target",
                message="onboarding proposals may target reported facts, not derived metrics",
                candidate_id=candidate_id,
            )
        )
