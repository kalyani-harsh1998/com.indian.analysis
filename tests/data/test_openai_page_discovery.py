"""Tests for the optional OpenAI bounded page-discovery adapter."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from indian_company_analysis import __main__ as command_line
from indian_company_analysis.data.extraction import (
    OpenAIPageDiscoveryError,
    OpenAIPageDiscoveryProposalProvider,
    PageDiscoveryCandidate,
    PageDiscoveryInput,
    PageDiscoveryProposal,
    PageDiscoveryProvenance,
    PageDiscoverySelection,
    openai_page_discovery,
    validate_page_discovery_proposal,
)
from indian_company_analysis.data.extraction.page_discovery import _candidate_checksum
from indian_company_analysis.data.onboarding.models import ModelRunProvenance


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


def _input() -> PageDiscoveryInput:
    candidates = (
        PageDiscoveryCandidate(page_number=12, lexical_score=4, excerpt="Tax expense note."),
        PageDiscoveryCandidate(page_number=24, lexical_score=3, excerpt="Other taxes."),
    )
    return PageDiscoveryInput(
        input_id="fictionalco-fy25-page-input-v1",
        request_id="fictionalco-fy25-tax-request-v1",
        document_id="fictionalco-fy25-report",
        source_checksum_sha256="a" * 64,
        target_scope_id="fictionalco-fy25-tax-v1",
        candidate_pages=candidates,
        candidate_pages_checksum_sha256=_candidate_checksum(candidates),
        provenance=PageDiscoveryProvenance(
            source_document_id="fictionalco-fy25-report",
            policy_version="test-v1",
            policy_checksum_sha256="b" * 64,
            extraction_tool="test",
            extraction_tool_version="1",
        ),
    )


def _provider(
    response: _FakeResponse,
) -> tuple[OpenAIPageDiscoveryProposalProvider, _FakeResponses]:
    responses = _FakeResponses(response)
    provider = OpenAIPageDiscoveryProposalProvider(
        model_id="gpt-6-astra",
        client_factory=lambda: _FakeClient(responses),
    )
    return provider, responses


def test_openai_page_discovery_selects_only_from_bounded_packet() -> None:
    discovery_input = _input()
    provider, responses = _provider(
        _FakeResponse(
            id="resp_page_selection",
            model="gpt-6-astra-2026-10-01",
            output_text=json.dumps(
                {
                    "selections": [
                        {
                            "page_number": 12,
                            "confidence": "high",
                            "rationale": "The excerpt explicitly names the tax expense note.",
                        }
                    ]
                }
            ),
        )
    )

    proposal = provider.propose(discovery_input)

    assert proposal.selections[0].page_number == 12
    assert proposal.model_run.provider == "openai"
    assert proposal.model_run.model_version == "gpt-6-astra-2026-10-01"
    assert validate_page_discovery_proposal(discovery_input, proposal).ready_for_review is True
    call = responses.calls[0]
    assert call["store"] is False
    assert call["max_output_tokens"] == 1_000
    assert "raw PDF" not in str(call)
    input_messages = call["input"]
    assert isinstance(input_messages, list)
    assert input_messages[0]["role"] == "developer"
    assert input_messages[1]["role"] == "user"
    assert "candidate_pages" in str(input_messages[1]["content"])
    text = call["text"]
    assert isinstance(text, dict)
    schema = text["format"]["schema"]
    assert schema["$defs"]["_OpenAIPageSelection"]["properties"]["page_number"] == {
        "type": "integer",
        "enum": [12, 24],
    }


def test_openai_page_discovery_rejects_invalid_or_out_of_packet_responses() -> None:
    discovery_input = _input()
    provider, _ = _provider(_FakeResponse(id="resp_invalid", model="test", output_text="not JSON"))
    with pytest.raises(OpenAIPageDiscoveryError, match="did not match"):
        provider.propose(discovery_input)

    provider, _ = _provider(
        _FakeResponse(
            id="resp_outside",
            model="test",
            output_text=json.dumps(
                {
                    "selections": [
                        {
                            "page_number": 99,
                            "confidence": "high",
                            "rationale": "This is deliberately outside the packet.",
                        }
                    ]
                }
            ),
        )
    )
    with pytest.raises(OpenAIPageDiscoveryError, match="outside the candidate packet"):
        provider.propose(discovery_input)


def test_default_client_explicitly_disables_sdk_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    options: list[dict[str, object]] = []
    fake = _FakeClient(_FakeResponses(_FakeResponse(id="unused", model="test", output_text=None)))

    def create(**kwargs: object) -> _FakeClient:
        options.append(kwargs)
        return fake

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=create))
    assert openai_page_discovery._create_openai_client() is fake
    assert options == [{"max_retries": 0}]


def test_page_discovery_cli_persists_only_a_locally_valid_review_proposal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    discovery_input = _input()
    input_path = tmp_path / "page-discovery-input.json"
    output_path = tmp_path / "proposal.json"
    input_path.write_text(discovery_input.model_dump_json(indent=2), encoding="utf-8")

    def propose(
        _self: OpenAIPageDiscoveryProposalProvider,
        received_input: PageDiscoveryInput,
    ) -> PageDiscoveryProposal:
        assert received_input == discovery_input
        return PageDiscoveryProposal(
            proposal_id="fictionalco-fy25-page-proposal-v1",
            input_id=received_input.input_id,
            request_id=received_input.request_id,
            document_id=received_input.document_id,
            source_checksum_sha256=received_input.source_checksum_sha256,
            candidate_pages_checksum_sha256=received_input.candidate_pages_checksum_sha256,
            model_run=ModelRunProvenance(
                provider="openai",
                model_id="test-model",
                model_version="test-model",
                prompt_version="page-discovery-input-v1",
                schema_version="openai-page-discovery-proposal-v1",
                generated_at=datetime(2026, 10, 14, tzinfo=UTC),
                input_checksum_sha256="c" * 64,
                instructions_checksum_sha256="d" * 64,
            ),
            selections=(
                PageDiscoverySelection(
                    page_number=12,
                    confidence="high",
                    rationale="Synthetic bounded page selection.",
                ),
            ),
        )

    monkeypatch.setattr(OpenAIPageDiscoveryProposalProvider, "propose", propose)

    assert (
        command_line.main(
            [
                "propose-openai-page-discovery",
                "--input",
                str(input_path),
                "--model",
                "test-model",
                "--output",
                str(output_path),
            ]
        )
        == 0
    )
    persisted = PageDiscoveryProposal.model_validate_json(output_path.read_text(encoding="utf-8"))
    assert persisted.selections[0].page_number == 12
