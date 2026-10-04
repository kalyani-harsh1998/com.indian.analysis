"""Optional OpenAI adapter for bounded, review-only onboarding proposals.

This module deliberately imports the OpenAI SDK only when a live call is requested. It never
receives a raw PDF or local path: the sole provider input is a prompt-isolated evidence packet.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal, Protocol, cast

from pydantic import Field, ValidationError

from indian_company_analysis.data.onboarding.metric_catalog import build_onboarding_metric_catalog
from indian_company_analysis.data.onboarding.model_input import (
    ONBOARDING_MODEL_DEVELOPER_INSTRUCTIONS,
    OnboardingModelInputPolicy,
    PromptIsolatedOnboardingInputBuilder,
)
from indian_company_analysis.data.onboarding.models import (
    AbstentionCandidate,
    DocumentOnboardingProposal,
    DocumentOnboardingRequest,
    ExclusionCandidate,
    MappingCandidate,
    MetricAggregationCandidate,
    MetricAggregationComponent,
    ModelRunProvenance,
)
from indian_company_analysis.domain.enums import ConfidenceLevel
from indian_company_analysis.domain.metrics import MetricId
from indian_company_analysis.domain.models import DomainModel

_PROVIDER_NAME = "openai"
_SCHEMA_VERSION = "openai-onboarding-proposal-v2"


class OpenAIProviderError(RuntimeError):
    """A live provider response could not be converted into a proposal artifact."""


class _ResponsesResource(Protocol):
    def create(self, **kwargs: object) -> object:
        """Create one response."""


class _OpenAIClient(Protocol):
    @property
    def responses(self) -> _ResponsesResource:
        """Responses endpoint exposed by the client."""
        ...


class _OpenAIMappingCandidate(DomainModel):
    """Wire schema with all fields required for strict structured output."""

    candidate_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]*$")
    evidence_id: str = Field(min_length=1)
    reported_label: str = Field(min_length=1)
    metric_id: MetricId
    sign_multiplier: Literal[-1, 1]
    confidence: ConfidenceLevel
    rationale: str = Field(min_length=1)


class _OpenAIAggregationComponent(DomainModel):
    evidence_id: str = Field(min_length=1)
    coefficient: Literal[-1, 1]


class _OpenAIAggregationCandidate(DomainModel):
    candidate_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]*$")
    metric_id: MetricId
    components: tuple[_OpenAIAggregationComponent, ...] = Field(min_length=2)
    confidence: ConfidenceLevel
    rationale: str = Field(min_length=1)


class _OpenAIExclusionCandidate(DomainModel):
    evidence_id: str = Field(min_length=1)
    confidence: ConfidenceLevel
    rationale: str = Field(min_length=1)


class _OpenAIAbstentionCandidate(DomainModel):
    candidate_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]*$")
    evidence_id: str = Field(min_length=1)
    confidence: ConfidenceLevel
    rationale: str = Field(min_length=1)


class _OpenAIProposalContent(DomainModel):
    """Only the semantic decisions the provider may make.

    Request identity and model-run provenance are created locally after the response returns.
    """

    mappings: tuple[_OpenAIMappingCandidate, ...]
    aggregations: tuple[_OpenAIAggregationCandidate, ...]
    exclusions: tuple[_OpenAIExclusionCandidate, ...]
    abstentions: tuple[_OpenAIAbstentionCandidate, ...]


class OpenAIOnboardingProposalProvider:
    """Propose, but never approve, mappings from a bounded evidence packet.

    The caller must explicitly install the optional dependency and set `OPENAI_API_KEY` in its
    local environment. This adapter issues exactly one non-retrying request per `propose` call.
    """

    def __init__(
        self,
        *,
        model_id: str,
        input_policy: OnboardingModelInputPolicy,
        client_factory: Callable[[], _OpenAIClient] | None = None,
        maximum_output_tokens: int = 4_000,
    ) -> None:
        if maximum_output_tokens < 1:
            raise ValueError("maximum_output_tokens must be positive")
        self._model_id = model_id
        self._input_policy = input_policy
        self._client_factory = client_factory or _create_openai_client
        self._maximum_output_tokens = maximum_output_tokens

    def propose(self, request: DocumentOnboardingRequest) -> DocumentOnboardingProposal:
        """Create one stateless structured proposal from the request's minimal evidence."""

        input_packet = PromptIsolatedOnboardingInputBuilder().build(
            request,
            input_id=f"{request.request_id}-openai-input-v3",
            policy=self._input_policy,
        )
        user_payload = input_packet.provider_user_payload()
        started = time.monotonic()
        response = self._client_factory().responses.create(
            model=self._model_id,
            store=False,
            max_output_tokens=self._maximum_output_tokens,
            input=[
                {"role": "developer", "content": ONBOARDING_MODEL_DEVELOPER_INSTRUCTIONS},
                {"role": "user", "content": user_payload},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "onboarding_proposal_content",
                    "strict": True,
                    "schema": _proposal_response_schema(),
                }
            },
        )
        latency_milliseconds = int((time.monotonic() - started) * 1_000)
        proposal_content = _parse_proposal_content(response)
        model_version = _string_field(response, "model") or self._model_id
        response_id = _string_field(response, "id") or "response-without-id"
        proposal_id = _proposal_id(request.request_id, response_id)
        usage = getattr(response, "usage", None)

        return DocumentOnboardingProposal(
            proposal_id=proposal_id,
            request_id=request.request_id,
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
            model_run=ModelRunProvenance(
                provider=_PROVIDER_NAME,
                model_id=self._model_id,
                model_version=model_version,
                prompt_version=input_packet.prompt_contract_version,
                schema_version=_SCHEMA_VERSION,
                generated_at=datetime.now(UTC),
                input_tokens=_nonnegative_integer_field(usage, "input_tokens", "prompt_tokens"),
                output_tokens=_nonnegative_integer_field(
                    usage, "output_tokens", "completion_tokens"
                ),
                latency_milliseconds=latency_milliseconds,
                input_checksum_sha256=hashlib.sha256(user_payload.encode("utf-8")).hexdigest(),
                instructions_checksum_sha256=hashlib.sha256(
                    ONBOARDING_MODEL_DEVELOPER_INSTRUCTIONS.encode("utf-8")
                ).hexdigest(),
            ),
            mappings=tuple(
                MappingCandidate.model_validate(candidate.model_dump(mode="json"))
                for candidate in proposal_content.mappings
            ),
            aggregations=tuple(
                MetricAggregationCandidate(
                    candidate_id=candidate.candidate_id,
                    metric_id=candidate.metric_id,
                    components=tuple(
                        MetricAggregationComponent(
                            evidence_id=component.evidence_id,
                            coefficient=component.coefficient,
                        )
                        for component in candidate.components
                    ),
                    confidence=candidate.confidence,
                    rationale=candidate.rationale,
                )
                for candidate in proposal_content.aggregations
            ),
            exclusions=tuple(
                ExclusionCandidate.model_validate(candidate.model_dump(mode="json"))
                for candidate in proposal_content.exclusions
            ),
            abstentions=tuple(
                AbstentionCandidate.model_validate(candidate.model_dump(mode="json"))
                for candidate in proposal_content.abstentions
            ),
        )


def _create_openai_client() -> _OpenAIClient:
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError(
            "OpenAI support is optional. Install it with `uv sync --extra openai` before "
            "requesting a live onboarding proposal."
        ) from error
    return cast(_OpenAIClient, OpenAI(max_retries=0))


def _proposal_response_schema() -> dict[str, object]:
    """Advertise only eligible fact targets, using the same catalog as the input packet."""

    schema = _OpenAIProposalContent.model_json_schema()
    schema["$defs"]["MetricId"]["enum"] = [
        item.metric_id.value for item in build_onboarding_metric_catalog().definitions
    ]
    return schema


def _parse_proposal_content(response: object) -> _OpenAIProposalContent:
    status = _string_field(response, "status")
    if status in {"failed", "incomplete", "cancelled"}:
        raise OpenAIProviderError(f"OpenAI response did not complete successfully: {status}")
    output_text = _string_field(response, "output_text")
    if output_text is None:
        raise OpenAIProviderError("OpenAI response contained no structured text output")
    try:
        content = _OpenAIProposalContent.model_validate_json(output_text)
    except ValidationError as error:
        raise OpenAIProviderError(
            "OpenAI response did not match the onboarding proposal schema"
        ) from error
    eligible_ids = {item.metric_id for item in build_onboarding_metric_catalog().definitions}
    proposed_ids = [item.metric_id for item in content.mappings]
    proposed_ids.extend(item.metric_id for item in content.aggregations)
    if any(metric_id not in eligible_ids for metric_id in proposed_ids):
        raise OpenAIProviderError("OpenAI response targets a metric outside the onboarding catalog")
    return content


def _string_field(value: object, field_name: str) -> str | None:
    candidate = getattr(value, field_name, None)
    return candidate if isinstance(candidate, str) and candidate else None


def _nonnegative_integer_field(value: object, *field_names: str) -> int | None:
    for field_name in field_names:
        candidate = getattr(value, field_name, None)
        if isinstance(candidate, int) and not isinstance(candidate, bool) and candidate >= 0:
            return candidate
    return None


def _proposal_id(request_id: str, response_id: str) -> str:
    response_digest = hashlib.sha256(response_id.encode("utf-8")).hexdigest()[:12]
    return f"{request_id}-openai-{response_digest}"
