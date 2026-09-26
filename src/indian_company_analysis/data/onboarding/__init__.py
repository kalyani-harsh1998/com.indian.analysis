"""Provider-neutral contracts for model-assisted document onboarding."""

from indian_company_analysis.data.onboarding.aggregation import (
    AggregatedNormalizedFact,
    AggregationComponentLineage,
    AggregationExecutionIssue,
    AggregationExecutionResult,
    execute_approved_aggregations,
)
from indian_company_analysis.data.onboarding.approval import approve_onboarding_proposal
from indian_company_analysis.data.onboarding.contracts import OnboardingProposalProvider
from indian_company_analysis.data.onboarding.models import (
    ApprovedAggregationComponent,
    ApprovedAggregationRule,
    ApprovedDirectMapping,
    ApprovedExclusion,
    ApprovedOnboardingConfiguration,
    DocumentOnboardingProposal,
    DocumentOnboardingRequest,
    ExclusionCandidate,
    MappingCandidate,
    MetricAggregationCandidate,
    MetricAggregationComponent,
    ModelRunProvenance,
    OnboardingEvidenceRow,
    ProposalValidationIssue,
    ProposalValidationResult,
)
from indian_company_analysis.data.onboarding.request_builder import build_onboarding_request
from indian_company_analysis.data.onboarding.static_provider import StaticProposalProvider
from indian_company_analysis.data.onboarding.validation import validate_onboarding_proposal

__all__ = [
    "AggregatedNormalizedFact",
    "AggregationComponentLineage",
    "AggregationExecutionIssue",
    "AggregationExecutionResult",
    "ApprovedAggregationComponent",
    "ApprovedAggregationRule",
    "ApprovedDirectMapping",
    "ApprovedExclusion",
    "ApprovedOnboardingConfiguration",
    "DocumentOnboardingProposal",
    "DocumentOnboardingRequest",
    "ExclusionCandidate",
    "MappingCandidate",
    "MetricAggregationCandidate",
    "MetricAggregationComponent",
    "ModelRunProvenance",
    "OnboardingEvidenceRow",
    "OnboardingProposalProvider",
    "ProposalValidationIssue",
    "ProposalValidationResult",
    "StaticProposalProvider",
    "approve_onboarding_proposal",
    "build_onboarding_request",
    "execute_approved_aggregations",
    "validate_onboarding_proposal",
]
