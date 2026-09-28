"""Auditable human-review outcomes for onboarding proposals."""

from __future__ import annotations

from datetime import datetime

from indian_company_analysis.data.onboarding.approval import approve_onboarding_proposal
from indian_company_analysis.data.onboarding.models import (
    DocumentOnboardingProposal,
    DocumentOnboardingRequest,
    OnboardingReviewDecision,
)
from indian_company_analysis.data.onboarding.validation import validate_onboarding_proposal


def approve_proposal(
    request: DocumentOnboardingRequest,
    proposal: DocumentOnboardingProposal,
    *,
    decision_id: str,
    configuration_version: str,
    aggregation_rule_version: str,
    reviewed_by: str,
    reviewed_at: datetime,
    approval_policy_version: str,
    review_rationale: str,
) -> OnboardingReviewDecision:
    """Record approval only when deterministic validation permits configuration creation."""

    validation = validate_onboarding_proposal(request, proposal)
    configuration = approve_onboarding_proposal(
        request,
        proposal,
        configuration_version=configuration_version,
        aggregation_rule_version=aggregation_rule_version,
        reviewed_by=reviewed_by,
        reviewed_at=reviewed_at,
        approval_policy_version=approval_policy_version,
    )
    return OnboardingReviewDecision(
        decision_id=decision_id,
        outcome="approved",
        request_id=request.request_id,
        proposal_id=proposal.proposal_id,
        reviewed_by=reviewed_by,
        reviewed_at=reviewed_at,
        approval_policy_version=approval_policy_version,
        review_rationale=review_rationale,
        validation=validation,
        configuration=configuration,
    )


def reject_proposal(
    request: DocumentOnboardingRequest,
    proposal: DocumentOnboardingProposal,
    *,
    decision_id: str,
    reviewed_by: str,
    reviewed_at: datetime,
    approval_policy_version: str,
    review_rationale: str,
    rejection_reasons: tuple[str, ...],
) -> OnboardingReviewDecision:
    """Record a reviewer rejection without altering the original proposal."""

    return OnboardingReviewDecision(
        decision_id=decision_id,
        outcome="rejected",
        request_id=request.request_id,
        proposal_id=proposal.proposal_id,
        reviewed_by=reviewed_by,
        reviewed_at=reviewed_at,
        approval_policy_version=approval_policy_version,
        review_rationale=review_rationale,
        validation=validate_onboarding_proposal(request, proposal),
        rejection_reasons=rejection_reasons,
    )
