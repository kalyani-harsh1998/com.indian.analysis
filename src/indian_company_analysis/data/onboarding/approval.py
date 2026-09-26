"""Human-review gate for deterministic promotion of onboarding proposals."""

from __future__ import annotations

from datetime import datetime

from indian_company_analysis.data.normalization.models import (
    MetricLabelMapping,
    MetricMappingSet,
)
from indian_company_analysis.data.onboarding.models import (
    ApprovedAggregationRule,
    ApprovedOnboardingConfiguration,
    DocumentOnboardingProposal,
    DocumentOnboardingRequest,
)
from indian_company_analysis.data.onboarding.validation import validate_onboarding_proposal


def approve_onboarding_proposal(
    request: DocumentOnboardingRequest,
    proposal: DocumentOnboardingProposal,
    *,
    configuration_version: str,
    aggregation_rule_version: str,
    reviewed_by: str,
    reviewed_at: datetime,
    approval_policy_version: str,
) -> ApprovedOnboardingConfiguration:
    """Promote a valid proposal while retaining model and human-review provenance."""

    validation = validate_onboarding_proposal(request, proposal)
    if not validation.ready_for_review:
        codes = ", ".join(issue.code for issue in validation.issues)
        raise ValueError(f"onboarding proposal is not ready for review: {codes}")

    mapping_set = None
    if proposal.mappings:
        mapping_set = MetricMappingSet(
            mapping_version=configuration_version,
            source_organization=request.source_organization,
            document_type=request.document_type,
            mappings=tuple(
                MetricLabelMapping(
                    reported_label=candidate.reported_label,
                    metric_id=candidate.metric_id,
                    sign_multiplier=candidate.sign_multiplier,
                    confidence=candidate.confidence,
                    rationale=candidate.rationale,
                )
                for candidate in proposal.mappings
            ),
        )

    aggregation_rules = tuple(
        ApprovedAggregationRule(
            rule_id=candidate.candidate_id,
            rule_version=aggregation_rule_version,
            metric_id=candidate.metric_id,
            components=candidate.components,
            rationale=candidate.rationale,
            source_proposal_id=proposal.proposal_id,
        )
        for candidate in proposal.aggregations
    )
    blockers: list[str] = []
    if mapping_set is None:
        blockers.append("current normalization requires at least one direct mapping")
    if aggregation_rules:
        blockers.append("deterministic aggregation execution is not implemented")

    return ApprovedOnboardingConfiguration(
        configuration_version=configuration_version,
        request_id=request.request_id,
        proposal_id=proposal.proposal_id,
        document_id=request.document_id,
        source_checksum_sha256=request.source_checksum_sha256,
        model_run=proposal.model_run,
        mapping_set=mapping_set,
        aggregation_rules=aggregation_rules,
        excluded_evidence_ids=tuple(exclusion.evidence_id for exclusion in proposal.exclusions),
        reviewed_by=reviewed_by,
        reviewed_at=reviewed_at,
        approval_policy_version=approval_policy_version,
        normalization_blockers=tuple(blockers),
        ready_for_normalization=not blockers,
    )
