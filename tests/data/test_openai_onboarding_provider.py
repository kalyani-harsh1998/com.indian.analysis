"""Tests for the optional, bounded OpenAI onboarding adapter."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import pytest

from indian_company_analysis.data.onboarding import (
    DocumentOnboardingRequest,
    OnboardingModelInputPolicy,
    OpenAIOnboardingProposalProvider,
    OpenAIProviderError,
    validate_onboarding_proposal,
)


@dataclass(frozen=True, slots=True)
class _FakeUsage:
    input_tokens: int = 123
    output_tokens: int = 45


@dataclass(frozen=True, slots=True)
class _FakeResponse:
    id: str
    model: str
    output_text: str | None
    usage: _FakeUsage = _FakeUsage()
    status: str = "completed"


@dataclass(slots=True)
class _FakeResponses:
    response: _FakeResponse
    calls: list[dict[str, object]] = field(default_factory=list)

    def create(self, **kwargs: object) -> object:
        self.calls.append(dict(kwargs))
        return self.response


@dataclass(slots=True)
class _FakeClient:
    responses: _FakeResponses


def _request() -> DocumentOnboardingRequest:
    fixture = json.loads(
        Path("tests/fixtures/evaluations/fictional_tax_onboarding.json").read_text(encoding="utf-8")
    )
    return DocumentOnboardingRequest.model_validate(fixture["request"])


def _provider_content() -> str:
    return json.dumps(
        {
            "mappings": [
                {
                    "candidate_id": "map-revenue",
                    "evidence_id": "row-1",
                    "reported_label": "Revenue from operations",
                    "metric_id": "revenue",
                    "sign_multiplier": 1,
                    "confidence": "high",
                    "rationale": "The row explicitly reports operating revenue.",
                },
                {
                    "candidate_id": "map-pbt",
                    "evidence_id": "row-2",
                    "reported_label": "Profit before tax",
                    "metric_id": "profit_before_tax",
                    "sign_multiplier": 1,
                    "confidence": "high",
                    "rationale": "The row explicitly reports profit before tax.",
                },
                {
                    "candidate_id": "map-pat",
                    "evidence_id": "row-5",
                    "reported_label": "Profit for the year",
                    "metric_id": "profit_after_tax",
                    "sign_multiplier": 1,
                    "confidence": "high",
                    "rationale": "The row explicitly reports profit for the year.",
                },
            ],
            "aggregations": [
                {
                    "candidate_id": "aggregate-tax",
                    "metric_id": "tax_expense",
                    "components": [
                        {"evidence_id": "row-3", "coefficient": 1},
                        {"evidence_id": "row-4", "coefficient": 1},
                    ],
                    "confidence": "high",
                    "rationale": "Current and deferred tax form total tax expense.",
                }
            ],
            "exclusions": [
                {
                    "evidence_id": "row-6",
                    "confidence": "high",
                    "rationale": "Other income has no canonical target in this onboarding scope.",
                }
            ],
            "abstentions": [],
        }
    )


def _provider(response: _FakeResponse) -> tuple[OpenAIOnboardingProposalProvider, _FakeResponses]:
    responses = _FakeResponses(response)
    provider = OpenAIOnboardingProposalProvider(
        model_id="gpt-6-astra",
        input_policy=OnboardingModelInputPolicy(policy_version="prompt-isolation-v1"),
        client_factory=lambda: _FakeClient(responses),
    )
    return provider, responses


def test_openai_provider_sends_only_bounded_data_and_binds_local_provenance() -> None:
    request = _request()
    provider, responses = _provider(
        _FakeResponse(
            id="resp_example",
            model="gpt-6-astra-2026-10-01",
            output_text=_provider_content(),
        )
    )

    proposal = provider.propose(request)

    assert proposal.request_id == request.request_id
    assert proposal.proposal_id.startswith(f"{request.request_id}-openai-")
    assert proposal.model_run.provider == "openai"
    assert proposal.model_run.model_id == "gpt-6-astra"
    assert proposal.model_run.model_version == "gpt-6-astra-2026-10-01"
    assert proposal.model_run.prompt_version == "onboarding-model-input-v2"
    assert proposal.model_run.input_tokens == 123
    assert proposal.model_run.output_tokens == 45
    assert proposal.model_run.estimated_cost is None
    assert proposal.model_run.cost_currency is None
    assert len(proposal.mappings) == 3
    assert proposal.aggregations[0].components[1].evidence_id == "row-4"
    assert validate_onboarding_proposal(request, proposal).ready_for_review is True

    assert len(responses.calls) == 1
    call = responses.calls[0]
    assert call["model"] == "gpt-6-astra"
    assert call["store"] is False
    assert call["max_output_tokens"] == 4_000
    assert "raw PDF" not in str(call)
    input_messages = cast(list[dict[str, object]], call["input"])
    assert isinstance(input_messages, list)
    assert input_messages[0]["role"] == "developer"
    assert input_messages[1]["role"] == "user"
    assert "untrusted_evidence_rows" in str(input_messages[1]["content"])
    assert "stored_relative_path" not in str(input_messages[1]["content"])
    text = cast(dict[str, dict[str, object]], call["text"])
    assert isinstance(text, dict)
    assert text["format"]["type"] == "json_schema"
    assert text["format"]["strict"] is True
    assert "(?" not in json.dumps(text["format"]["schema"])


def test_openai_provider_rejects_incomplete_or_unparseable_provider_output() -> None:
    request = _request()
    provider, _ = _provider(
        _FakeResponse(
            id="resp_incomplete",
            model="gpt-6-astra",
            output_text=None,
            status="incomplete",
        )
    )

    with pytest.raises(OpenAIProviderError, match="did not complete successfully"):
        provider.propose(request)

    provider, _ = _provider(
        _FakeResponse(
            id="resp_invalid",
            model="gpt-6-astra",
            output_text="not JSON",
        )
    )
    with pytest.raises(OpenAIProviderError, match="did not match"):
        provider.propose(request)
