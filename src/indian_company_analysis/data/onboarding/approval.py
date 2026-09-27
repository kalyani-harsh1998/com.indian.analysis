"""Human-review gate for deterministic promotion of onboarding proposals."""

from __future__ import annotations

from datetime import datetime

from indian_company_analysis.data.normalization.models import (
    MetricLabelMapping,
    MetricMappingSet,
)
from indian_company_analysis.data.onboarding.models import (
    ApprovedAggregationComponent,
    ApprovedAggregationRule,
    ApprovedDirectMapping,
    ApprovedExclusion,
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

    evidence_by_id = {row.evidence_id: row for row in request.evidence_rows}
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

    direct_mappings = tuple(
        ApprovedDirectMapping(
            candidate_id=candidate.candidate_id,
            evidence_id=candidate.evidence_id,
            source_locator=evidence_by_id[candidate.evidence_id].source_locator,
            reported_label=evidence_by_id[candidate.evidence_id].reported_label,
            raw_value=evidence_by_id[candidate.evidence_id].raw_value,
            metric_id=candidate.metric_id,
            sign_multiplier=candidate.sign_multiplier,
            confidence=candidate.confidence,
            rationale=candidate.rationale,
            source_proposal_id=proposal.proposal_id,
        )
        for candidate in proposal.mappings
    )
    aggregation_rules = tuple(
        ApprovedAggregationRule(
            rule_id=candidate.candidate_id,
            rule_version=aggregation_rule_version,
            metric_id=candidate.metric_id,
            components=tuple(
                ApprovedAggregationComponent(
                    evidence_id=component.evidence_id,
                    source_locator=evidence_by_id[component.evidence_id].source_locator,
                    reported_label=evidence_by_id[component.evidence_id].reported_label,
                    raw_value=evidence_by_id[component.evidence_id].raw_value,
                    coefficient=component.coefficient,
                )
                for component in candidate.components
            ),
            confidence=candidate.confidence,
            rationale=candidate.rationale,
            source_proposal_id=proposal.proposal_id,
        )
        for candidate in proposal.aggregations
    )
    exclusions = tuple(
        ApprovedExclusion(
            evidence_id=candidate.evidence_id,
            source_locator=evidence_by_id[candidate.evidence_id].source_locator,
            reported_label=evidence_by_id[candidate.evidence_id].reported_label,
            raw_value=evidence_by_id[candidate.evidence_id].raw_value,
            confidence=candidate.confidence,
            rationale=candidate.rationale,
            source_proposal_id=proposal.proposal_id,
        )
        for candidate in proposal.exclusions
    )

    return ApprovedOnboardingConfiguration(
        configuration_version=configuration_version,
        request_id=request.request_id,
        proposal_id=proposal.proposal_id,
        document_id=request.document_id,
        extraction_id=request.extraction_id,
        extraction_profile_version=request.extraction_profile_version,
        company_id=request.company_id,
        source_reference_id=request.source_reference_id,
        source_checksum_sha256=request.source_checksum_sha256,
        source_organization=request.source_organization,
        document_type=request.document_type,
        unit=request.unit,
        period=request.period,
        reporting_basis=request.reporting_basis,
        model_run=proposal.model_run,
        mapping_set=mapping_set,
        direct_mappings=direct_mappings,
        aggregation_rules=aggregation_rules,
        exclusions=exclusions,
        reviewed_by=reviewed_by,
        reviewed_at=reviewed_at,
        approval_policy_version=approval_policy_version,
        normalization_blockers=(),
        ready_for_normalization=True,
    )
