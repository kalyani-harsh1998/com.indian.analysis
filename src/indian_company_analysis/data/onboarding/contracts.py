"""Provider-neutral protocol for model-assisted onboarding proposals."""

from typing import Protocol

from indian_company_analysis.data.onboarding.models import (
    DocumentOnboardingProposal,
    DocumentOnboardingRequest,
)


class OnboardingProposalProvider(Protocol):
    """Suggest a configuration; implementations do not approve financial facts."""

    def propose(self, request: DocumentOnboardingRequest) -> DocumentOnboardingProposal:
        """Return a strict candidate proposal for deterministic validation."""
        ...
