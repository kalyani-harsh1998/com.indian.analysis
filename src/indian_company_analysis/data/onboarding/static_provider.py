"""Deterministic proposal provider used to test the onboarding boundary."""

from dataclasses import dataclass

from indian_company_analysis.data.onboarding.models import (
    DocumentOnboardingProposal,
    DocumentOnboardingRequest,
)


@dataclass(frozen=True, slots=True)
class StaticProposalProvider:
    """Return one prebuilt proposal without network or model dependencies."""

    proposal: DocumentOnboardingProposal

    def propose(self, request: DocumentOnboardingRequest) -> DocumentOnboardingProposal:
        if request.request_id != self.proposal.request_id:
            raise ValueError("static proposal request ID does not match the onboarding request")
        return self.proposal
