"""Provider-neutral contracts for model-assisted document onboarding."""

from indian_company_analysis.data.onboarding.aggregation import (
    AggregatedNormalizedFact,
    AggregationComponentLineage,
    AggregationExecutionIssue,
    AggregationExecutionResult,
    execute_approved_aggregations,
)
from indian_company_analysis.data.onboarding.approval import approve_onboarding_proposal
from indian_company_analysis.data.onboarding.catalog import (
    LocalOnboardingConfigurationCatalog,
    LocalOnboardingReviewCatalog,
)
from indian_company_analysis.data.onboarding.contracts import OnboardingProposalProvider
from indian_company_analysis.data.onboarding.corpus import (
    EvaluationCorpusEntry,
    LocalEvaluationCorpusCatalog,
    provisionally_review_entry,
)
from indian_company_analysis.data.onboarding.evaluation import (
    EvaluationQualification,
    EvaluationThresholds,
    ExpectedAbstentionDecision,
    ExpectedAggregationDecision,
    ExpectedExclusionDecision,
    ExpectedMappingDecision,
    ExpectedMetricValue,
    MetricValueComparison,
    OnboardingEvaluationFixture,
    OnboardingEvaluationReport,
    OnboardingProposalEvaluator,
    ProposalAccuracyMetrics,
    ReconciliationEvaluationResult,
    ReconciliationExpectation,
    ReconciliationTerm,
)
from indian_company_analysis.data.onboarding.models import (
    AbstentionCandidate,
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
    OnboardingReviewDecision,
    ProposalValidationIssue,
    ProposalValidationResult,
)
from indian_company_analysis.data.onboarding.normalization_workflow import (
    OnboardingNormalizationBatch,
    OnboardingNormalizationIssue,
    OnboardingNormalizationWorkflow,
)
from indian_company_analysis.data.onboarding.request_builder import build_onboarding_request
from indian_company_analysis.data.onboarding.reuse import (
    DecisionReuseAssessment,
    OnboardingReuseAssessment,
    OnboardingReuseAssessor,
    ReuseContextDifference,
)
from indian_company_analysis.data.onboarding.review import approve_proposal, reject_proposal
from indian_company_analysis.data.onboarding.static_provider import StaticProposalProvider
from indian_company_analysis.data.onboarding.validation import (
    validate_configuration_identity,
    validate_onboarding_proposal,
)

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
    "AbstentionCandidate",
    "DocumentOnboardingProposal",
    "DocumentOnboardingRequest",
    "DecisionReuseAssessment",
    "EvaluationThresholds",
    "EvaluationQualification",
    "EvaluationCorpusEntry",
    "ExclusionCandidate",
    "ExpectedAggregationDecision",
    "ExpectedAbstentionDecision",
    "ExpectedExclusionDecision",
    "ExpectedMappingDecision",
    "ExpectedMetricValue",
    "MappingCandidate",
    "MetricAggregationCandidate",
    "MetricAggregationComponent",
    "MetricValueComparison",
    "LocalOnboardingConfigurationCatalog",
    "LocalEvaluationCorpusCatalog",
    "LocalOnboardingReviewCatalog",
    "ModelRunProvenance",
    "OnboardingEvidenceRow",
    "OnboardingEvaluationFixture",
    "OnboardingEvaluationReport",
    "OnboardingNormalizationBatch",
    "OnboardingNormalizationIssue",
    "OnboardingNormalizationWorkflow",
    "OnboardingProposalProvider",
    "OnboardingProposalEvaluator",
    "OnboardingReviewDecision",
    "OnboardingReuseAssessment",
    "OnboardingReuseAssessor",
    "ProposalAccuracyMetrics",
    "ProposalValidationIssue",
    "ProposalValidationResult",
    "ReconciliationEvaluationResult",
    "ReconciliationExpectation",
    "ReconciliationTerm",
    "ReuseContextDifference",
    "StaticProposalProvider",
    "approve_onboarding_proposal",
    "approve_proposal",
    "build_onboarding_request",
    "execute_approved_aggregations",
    "reject_proposal",
    "provisionally_review_entry",
    "validate_configuration_identity",
    "validate_onboarding_proposal",
]
