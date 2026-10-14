"""Tests for the optional OpenAI bounded page-discovery adapter."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from indian_company_analysis import __main__ as command_line
from indian_company_analysis.data.extraction import (
    OpenAIPageDiscoveryError,
    OpenAIPageDiscoveryProposalProvider,
    PageDiscoveryCandidate,
    PageDiscoveryEvidenceAnchor,
    PageDiscoveryInput,
    PageDiscoveryProposal,
    PageDiscoveryProvenance,
    PageDiscoveryRequestContext,
    PageDiscoverySelection,
    openai_page_discovery,
    validate_page_discovery_proposal,
)
from indian_company_analysis.data.extraction.page_discovery import (
    _candidate_checksum,
    _request_context_checksum,
)
from indian_company_analysis.data.onboarding.models import ModelRunProvenance
from indian_company_analysis.domain.enums import PeriodType, ReportingBasis
from indian_company_analysis.domain.metrics import MetricId
from indian_company_analysis.domain.models import ReportingPeriod


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
    request_context = PageDiscoveryRequestContext(
        company_id="fictionalco",
        reporting_basis=ReportingBasis.CONSOLIDATED,
        period=ReportingPeriod(
            label="FY2025",
            period_type=PeriodType.ANNUAL,
            start_date=date(2024, 4, 1),
            end_date=date(2025, 3, 31),
        ),
        target_scope_id="fictionalco-fy25-tax-v1",
        target_metric_ids=(MetricId.TAX_EXPENSE,),
        purpose="Find the consolidated annual tax expense note.",
        evidence_anchors=(
            PageDiscoveryEvidenceAnchor(
                evidence_id="row-12-4",
                page_number=12,
                table_id="consolidated_profit_and_loss",
                row_number=4,
                column_name="FY2025",
                reported_label="Tax expense",
            ),
        ),
    )
    return PageDiscoveryInput(
        input_id="fictionalco-fy25-page-input-v1",
        request_id="fictionalco-fy25-tax-request-v1",
        document_id="fictionalco-fy25-report",
        source_checksum_sha256="a" * 64,
        request_context=request_context,
        request_context_checksum_sha256=_request_context_checksum(request_context),
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
                    "selection_status": "selected",
                    "selected_reporting_basis": "consolidated",
                    "selected_period_label": "FY2025",
                    "primary_selection": {
                        "page_number": 12,
                        "confidence": "high",
                        "rationale": "The excerpt explicitly names the consolidated tax note.",
                    },
                    "supporting_selections": [],
                    "abstention_reason": None,
                }
            ),
        )
    )

    proposal = provider.propose(discovery_input)

    assert proposal.primary_selection is not None
    assert proposal.primary_selection.page_number == 12
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
    assert "request_context" in str(input_messages[1]["content"])
    text = call["text"]
    assert isinstance(text, dict)
    schema = text["format"]["schema"]
    assert schema["$defs"]["_OpenAIPageSelection"]["properties"]["page_number"] == {
        "type": "integer",
        "enum": [12, 24],
    }
    assert schema["properties"]["selected_reporting_basis"] == {
        "type": "string",
        "enum": ["consolidated"],
    }
    assert schema["properties"]["selected_period_label"] == {
        "type": "string",
        "enum": ["FY2025"],
    }
    assert set(schema["required"]) == set(schema["properties"])


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
                    "selection_status": "selected",
                    "selected_reporting_basis": "consolidated",
                    "selected_period_label": "FY2025",
                    "primary_selection": {
                        "page_number": 99,
                        "confidence": "high",
                        "rationale": "This is deliberately outside the packet.",
                    },
                    "supporting_selections": [],
                    "abstention_reason": None,
                }
            ),
        )
    )
    with pytest.raises(OpenAIPageDiscoveryError, match="outside the candidate packet"):
        provider.propose(discovery_input)


def test_page_discovery_requires_request_basis_and_preserves_abstention() -> None:
    discovery_input = _input()
    tampered_input = discovery_input.model_dump(mode="json")
    tampered_input["request_context"]["reporting_basis"] = "standalone"
    with pytest.raises(ValueError, match="request-context checksum"):
        PageDiscoveryInput.model_validate(tampered_input)

    wrong_basis = PageDiscoveryProposal(
        proposal_id="fictionalco-fy25-wrong-basis-v1",
        input_id=discovery_input.input_id,
        request_id=discovery_input.request_id,
        document_id=discovery_input.document_id,
        source_checksum_sha256=discovery_input.source_checksum_sha256,
        request_context_checksum_sha256=discovery_input.request_context_checksum_sha256,
        candidate_pages_checksum_sha256=discovery_input.candidate_pages_checksum_sha256,
        model_run=ModelRunProvenance(
            provider="static",
            model_id="test",
            model_version="test",
            prompt_version="page-discovery-input-v2",
            schema_version="page-discovery-proposal-v2",
            generated_at=datetime(2026, 10, 15, tzinfo=UTC),
        ),
        selection_status="selected",
        selected_reporting_basis=ReportingBasis.STANDALONE,
        selected_period_label="FY2025",
        primary_selection=PageDiscoverySelection(
            page_number=12,
            confidence="high",
            rationale="Deliberately mismatched basis for validation testing.",
        ),
        supporting_selections=(),
        abstention_reason=None,
    )
    mismatch = validate_page_discovery_proposal(discovery_input, wrong_basis)
    assert mismatch.ready_for_review is False
    assert mismatch.issues[0].code == "reporting_basis_mismatch"

    wrong_period = wrong_basis.model_copy(
        update={
            "proposal_id": "fictionalco-fy25-wrong-period-v1",
            "selected_reporting_basis": ReportingBasis.CONSOLIDATED,
            "selected_period_label": "FY2024",
        }
    )
    period_mismatch = validate_page_discovery_proposal(discovery_input, wrong_period)
    assert period_mismatch.ready_for_review is False
    assert period_mismatch.issues[0].code == "period_mismatch"

    provider, _ = _provider(
        _FakeResponse(
            id="resp_abstain",
            model="test",
            output_text=json.dumps(
                {
                    "selection_status": "abstain",
                    "selected_reporting_basis": "consolidated",
                    "selected_period_label": "FY2025",
                    "primary_selection": None,
                    "supporting_selections": [],
                    "abstention_reason": "None of the candidate excerpts identifies the note.",
                }
            ),
        )
    )
    abstention = provider.propose(discovery_input)
    abstention_validation = validate_page_discovery_proposal(discovery_input, abstention)
    assert abstention_validation.issues == ()
    assert abstention_validation.abstention_requested is True
    assert abstention_validation.ready_for_review is False


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
            request_context_checksum_sha256=received_input.request_context_checksum_sha256,
            candidate_pages_checksum_sha256=received_input.candidate_pages_checksum_sha256,
            model_run=ModelRunProvenance(
                provider="openai",
                model_id="test-model",
                model_version="test-model",
                prompt_version="page-discovery-input-v2",
                schema_version="openai-page-discovery-proposal-v2",
                generated_at=datetime(2026, 10, 14, tzinfo=UTC),
                input_checksum_sha256="c" * 64,
                instructions_checksum_sha256="d" * 64,
            ),
            selection_status="selected",
            selected_reporting_basis=ReportingBasis.CONSOLIDATED,
            selected_period_label="FY2025",
            primary_selection=PageDiscoverySelection(
                page_number=12,
                confidence="high",
                rationale="Synthetic bounded page selection.",
            ),
            supporting_selections=(),
            abstention_reason=None,
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
    assert persisted.primary_selection is not None
    assert persisted.primary_selection.page_number == 12
