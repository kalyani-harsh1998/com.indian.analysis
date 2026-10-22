"""Tests for the local, identity-bound PDF profile-review service."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from indian_company_analysis.__main__ import main
from indian_company_analysis.data.extraction.page_discovery import (
    PageDiscoveryCandidate,
    PageDiscoveryEvidenceAnchor,
    PageDiscoveryInput,
    PageDiscoveryProposal,
    PageDiscoveryProvenance,
    PageDiscoveryRequestContext,
    PageDiscoverySelection,
    _candidate_checksum,
    _request_context_checksum,
)
from indian_company_analysis.data.ingestion.local_intake import ImmutableRawDocumentStore
from indian_company_analysis.data.ingestion.models import LocalDocumentIntakeRequest
from indian_company_analysis.data.locators import SourceFactLocator
from indian_company_analysis.data.onboarding.model_input import (
    LocatorBoundContextBundle,
    OnboardingModelInputPolicy,
    PromptIsolatedOnboardingInputBuilder,
    onboarding_request_checksum,
)
from indian_company_analysis.data.onboarding.models import (
    DocumentOnboardingRequest,
    ModelRunProvenance,
    OnboardingEvidenceRow,
    OnboardingTargetScope,
)
from indian_company_analysis.domain.enums import (
    DocumentType,
    LicenceCategory,
    PeriodType,
    ReportingBasis,
    SourceKind,
)
from indian_company_analysis.domain.metrics import MetricId
from indian_company_analysis.domain.models import ReportingPeriod
from indian_company_analysis.review_ui.models import (
    ProfileCandidateSubmission,
    RegionDraftSubmission,
    ReviewerProfileReviewDecision,
)
from indian_company_analysis.review_ui.profile_workflow import (
    LocalReviewerProfileDecisionCatalog,
    ReviewerProfileWorkflow,
    candidate_checksum,
    read_draft,
)
from indian_company_analysis.review_ui.service import ProfileReviewSession

_NOW = datetime(2026, 10, 15, tzinfo=UTC)


def _session(tmp_path: Path) -> ProfileReviewSession:
    fixture = Path("tests/fixtures/documents/fictional_annual_report.pdf")
    raw_root = tmp_path / "raw"
    intake = ImmutableRawDocumentStore(raw_root).ingest(
        LocalDocumentIntakeRequest(
            document_id="fictionalco-fy25-annual-report",
            company_id="fictionalco",
            document_type=DocumentType.ANNUAL_REPORT,
            source_kind=SourceKind.SYNTHETIC,
            source_organization="Synthetic test fixture",
            source_document="Fictional Co FY25 annual report",
            source_locator="tests/fixtures/documents/fictional_annual_report.pdf",
            retrieved_at=datetime(2026, 10, 15, tzinfo=UTC),
            licence_category=LicenceCategory.INTERNAL_POC,
            input_path=fixture,
            is_synthetic=True,
        )
    )
    period = ReportingPeriod(
        label="FY2025",
        period_type=PeriodType.ANNUAL,
        start_date=date(2024, 4, 1),
        end_date=date(2025, 3, 31),
    )
    target_scope = OnboardingTargetScope(
        scope_id="fictionalco-fy25-revenue-v1",
        metric_ids=(MetricId.REVENUE,),
        purpose="Review a synthetic reported revenue table.",
    )
    request = DocumentOnboardingRequest(
        request_id="fictionalco-fy25-revenue-request-v1",
        document_id=intake.manifest.document_id,
        extraction_id="fictionalco-fy25-income-statement-v1",
        extraction_profile_version="synthetic-v1",
        company_id="fictionalco",
        source_reference_id=intake.manifest.source_reference.source_id,
        source_checksum_sha256=intake.manifest.checksum_sha256,
        source_organization="Synthetic test fixture",
        document_type=DocumentType.ANNUAL_REPORT,
        unit="INR crore",
        period=period,
        reporting_basis=ReportingBasis.CONSOLIDATED,
        target_scope=target_scope,
        evidence_rows=(
            OnboardingEvidenceRow(
                evidence_id="row-1-1",
                source_locator=SourceFactLocator(
                    page_number=1,
                    table_id="synthetic_income_statement",
                    row_number=1,
                    column_name="FY2025",
                ),
                reported_label="Revenue from operations",
                raw_value="100",
            ),
        ),
    )
    context = PageDiscoveryRequestContext(
        company_id=request.company_id,
        reporting_basis=request.reporting_basis,
        period=request.period,
        target_scope_id=target_scope.scope_id,
        target_metric_ids=target_scope.metric_ids,
        purpose=target_scope.purpose,
        evidence_anchors=(
            PageDiscoveryEvidenceAnchor(
                evidence_id="row-1-1",
                page_number=1,
                table_id="synthetic_income_statement",
                row_number=1,
                column_name="FY2025",
                reported_label="Revenue from operations",
            ),
        ),
    )
    candidates = (
        PageDiscoveryCandidate(
            page_number=1,
            lexical_score=1,
            excerpt="Synthetic revenue statement.",
        ),
    )
    discovery_input = PageDiscoveryInput(
        input_id="fictionalco-fy25-revenue-page-input-v1",
        request_id=request.request_id,
        document_id=request.document_id,
        source_checksum_sha256=request.source_checksum_sha256,
        request_context=context,
        request_context_checksum_sha256=_request_context_checksum(context),
        candidate_pages=candidates,
        candidate_pages_checksum_sha256=_candidate_checksum(candidates),
        provenance=PageDiscoveryProvenance(
            source_document_id=request.document_id,
            policy_version="test-v1",
            policy_checksum_sha256="a" * 64,
            extraction_tool="test",
            extraction_tool_version="1",
        ),
    )
    proposal = PageDiscoveryProposal(
        proposal_id="fictionalco-fy25-revenue-page-proposal-v1",
        input_id=discovery_input.input_id,
        request_id=request.request_id,
        document_id=request.document_id,
        source_checksum_sha256=request.source_checksum_sha256,
        request_context_checksum_sha256=discovery_input.request_context_checksum_sha256,
        candidate_pages_checksum_sha256=discovery_input.candidate_pages_checksum_sha256,
        model_run=ModelRunProvenance(
            provider="static",
            model_id="test",
            model_version="test",
            prompt_version="test-v1",
            schema_version="test-v1",
            generated_at=datetime(2026, 10, 15, tzinfo=UTC),
        ),
        selection_status="selected",
        selected_reporting_basis=ReportingBasis.CONSOLIDATED,
        selected_period_label="FY2025",
        primary_selection=PageDiscoverySelection(
            page_number=1,
            confidence="high",
            rationale="Synthetic page selected for local reviewer tests.",
        ),
        supporting_selections=(),
        abstention_reason=None,
    )
    return ProfileReviewSession(
        source_manifest=intake.manifest,
        onboarding_request=request,
        page_discovery_input=discovery_input,
        page_discovery_proposal=proposal,
        raw_root=raw_root,
        draft_root=tmp_path / "drafts",
    )


def test_profile_reviewer_renders_validated_page_and_persists_only_new_drafts(
    tmp_path: Path,
) -> None:
    session = _session(tmp_path)

    metadata = session.metadata()
    assert metadata.pages[0].page_number == 1
    assert metadata.pages[0].selection_role == "primary"
    assert session.render_page_png(1).startswith(b"\x89PNG\r\n\x1a\n")

    draft, preview_text = session.create_draft(
        RegionDraftSubmission(
            draft_id="fictionalco-page-one-region-v1",
            profile_version="reviewer-region-v1",
            reviewer_name="Test Reviewer",
            review_notes="Whole-page synthetic reviewer selection.",
            page_number=1,
            x0=Decimal("0"),
            top=Decimal("0"),
            x1=metadata.pages[0].width,
            bottom=metadata.pages[0].height,
        )
    )

    assert draft.status == "draft"
    assert "Fictional" in preview_text
    persisted = tmp_path / "drafts" / "fictionalco-page-one-region-v1.json"
    assert persisted.exists()
    with pytest.raises(ValueError, match="refusing to overwrite"):
        session.create_draft(
            RegionDraftSubmission(
                draft_id="fictionalco-page-one-region-v1",
                profile_version="reviewer-region-v1",
                reviewer_name="Test Reviewer",
                review_notes="Repeat selection must not overwrite the first draft.",
                page_number=1,
                x0=Decimal("0"),
                top=Decimal("0"),
                x1=metadata.pages[0].width,
                bottom=metadata.pages[0].height,
            )
        )


def test_profile_reviewer_rejects_unselected_page_and_out_of_bounds_region(tmp_path: Path) -> None:
    session = _session(tmp_path)
    metadata = session.metadata()
    with pytest.raises(ValueError, match="validated proposal page"):
        session.render_page_png(2)
    with pytest.raises(ValueError, match="exceeds the verified PDF page bounds"):
        session.create_draft(
            RegionDraftSubmission(
                draft_id="fictionalco-too-large-region-v1",
                profile_version="reviewer-region-v1",
                reviewer_name="Test Reviewer",
                review_notes="This must be rejected.",
                page_number=1,
                x0=Decimal("0"),
                top=Decimal("0"),
                x1=metadata.pages[0].width + Decimal("1"),
                bottom=metadata.pages[0].height,
            )
        )


def test_draft_becomes_reextracted_candidate_then_explicitly_approved(tmp_path: Path) -> None:
    session = _session(tmp_path)
    metadata = session.metadata()
    draft, _ = session.create_draft(
        RegionDraftSubmission(
            draft_id="fictionalco-page-one-region-v2",
            profile_version="reviewer-region-v1",
            reviewer_name="Synthetic region reviewer",
            review_notes="Whole-page selection for controlled profile conversion.",
            page_number=1,
            x0=Decimal("0"),
            top=Decimal("0"),
            x1=metadata.pages[0].width,
            bottom=metadata.pages[0].height,
        )
    )
    draft_path = tmp_path / "reviewed-draft.json"
    draft_path.write_text(draft.model_dump_json(indent=2) + "\n", encoding="utf-8")
    saved_draft, saved_checksum = read_draft(draft_path)

    workflow = ReviewerProfileWorkflow(session)
    candidate = workflow.prepare_candidate(
        saved_draft,
        draft_file_checksum_sha256=saved_checksum,
        submission=ProfileCandidateSubmission(
            candidate_id="fictionalco-page-one-profile-candidate-v1",
            bundle_id="fictionalco-fy25-revenue-context-v2",
            profile_version="synthetic-reviewed-context-v1",
            context_id="revenue-note-context",
            table_id="synthetic_revenue_context",
            row_number=1,
            column_name="text",
            prepared_by="Synthetic profile preparer",
            prepared_at=_NOW,
        ),
    )

    assert candidate.status == "candidate"
    assert candidate.profile_spec.snippets[0].x0 == draft.x0
    assert candidate.extracted_context.snippets[0].text.startswith("Fictional Co")
    assert len(candidate_checksum(candidate)) == 64

    decision = workflow.approve_candidate(
        candidate,
        draft=saved_draft,
        draft_file_checksum_sha256=saved_checksum,
        decision_id="fictionalco-page-one-profile-approval-v1",
        reviewed_by="Synthetic profile approver",
        reviewed_at=_NOW,
        approval_policy_version="synthetic-profile-review-v1",
        review_rationale="Re-extracted synthetic region matches the intended context.",
    )

    assert decision.outcome == "approved"
    assert decision.approved_profile == candidate.profile_spec
    context = workflow.extract_approved_context(decision)
    assert context == candidate.extracted_context
    catalog = LocalReviewerProfileDecisionCatalog(tmp_path / "profile-decisions")
    assert catalog.register(decision) is True
    assert catalog.register(decision) is False

    rejection = workflow.reject_candidate(
        candidate,
        draft=saved_draft,
        draft_file_checksum_sha256=saved_checksum,
        decision_id="fictionalco-page-one-profile-rejection-v1",
        reviewed_by="Synthetic profile approver",
        reviewed_at=_NOW,
        approval_policy_version="synthetic-profile-review-v1",
        review_rationale="Reject the otherwise valid candidate for a documented semantic reason.",
        rejection_reasons=("Synthetic rejection-path coverage.",),
    )
    assert rejection.outcome == "rejected"
    assert rejection.approved_profile is None


def test_profile_approval_rejects_a_draft_that_changed_after_candidate_creation(
    tmp_path: Path,
) -> None:
    session = _session(tmp_path)
    metadata = session.metadata()
    draft, _ = session.create_draft(
        RegionDraftSubmission(
            draft_id="fictionalco-page-one-region-v3",
            profile_version="reviewer-region-v1",
            reviewer_name="Synthetic region reviewer",
            review_notes="Selection used to test post-candidate tampering.",
            page_number=1,
            x0=Decimal("0"),
            top=Decimal("0"),
            x1=metadata.pages[0].width,
            bottom=metadata.pages[0].height,
        )
    )
    draft_path = tmp_path / "draft-before-tampering.json"
    draft_path.write_text(draft.model_dump_json(indent=2) + "\n", encoding="utf-8")
    saved_draft, saved_checksum = read_draft(draft_path)
    workflow = ReviewerProfileWorkflow(session)
    candidate = workflow.prepare_candidate(
        saved_draft,
        draft_file_checksum_sha256=saved_checksum,
        submission=ProfileCandidateSubmission(
            candidate_id="fictionalco-page-one-profile-candidate-v2",
            bundle_id="fictionalco-fy25-revenue-context-v3",
            profile_version="synthetic-reviewed-context-v1",
            context_id="revenue-note-context-v2",
            table_id="synthetic_revenue_context",
            row_number=1,
            column_name="text",
            prepared_by="Synthetic profile preparer",
            prepared_at=_NOW,
        ),
    )
    changed_draft = saved_draft.model_copy(update={"review_notes": "Changed after conversion."})
    changed_path = tmp_path / "draft-after-tampering.json"
    changed_path.write_text(changed_draft.model_dump_json(indent=2) + "\n", encoding="utf-8")
    changed_saved_draft, changed_checksum = read_draft(changed_path)

    with pytest.raises(ValueError, match="profile candidate draft does not match"):
        workflow.approve_candidate(
            candidate,
            draft=changed_saved_draft,
            draft_file_checksum_sha256=changed_checksum,
            decision_id="fictionalco-page-one-profile-approval-v2",
            reviewed_by="Synthetic profile approver",
            reviewed_at=_NOW,
            approval_policy_version="synthetic-profile-review-v1",
            review_rationale="This must not approve a changed draft.",
        )


def _approved_profile(
    session: ProfileReviewSession,
) -> tuple[ReviewerProfileWorkflow, ReviewerProfileReviewDecision]:
    page = session.metadata().pages[0]
    draft, _ = session.create_draft(
        RegionDraftSubmission(
            draft_id="attachment-region-v1",
            profile_version="synthetic-v1",
            reviewer_name="Synthetic reviewer",
            review_notes="Synthetic region for attachment testing.",
            page_number=1,
            x0=Decimal(0),
            top=Decimal(0),
            x1=page.width,
            bottom=page.height,
        )
    )
    workflow = ReviewerProfileWorkflow(session)
    candidate = workflow.prepare_candidate(
        draft,
        draft_file_checksum_sha256="a" * 64,
        submission=ProfileCandidateSubmission(
            candidate_id="attachment-candidate-v1",
            bundle_id="source-context-v1",
            profile_version="synthetic-v1",
            context_id="revenue-note",
            table_id="synthetic_revenue_note",
            row_number=1,
            column_name="text",
            prepared_by="Synthetic preparer",
            prepared_at=_NOW,
        ),
    )
    decision = workflow.approve_candidate(
        candidate,
        draft=draft,
        draft_file_checksum_sha256="a" * 64,
        decision_id="attachment-approval-v1",
        reviewed_by="Synthetic reviewer",
        reviewed_at=_NOW,
        approval_policy_version="test-v1",
        review_rationale="Synthetic region checked for its assigned metric only.",
    )
    return workflow, decision


def _attach(
    workflow: ReviewerProfileWorkflow,
    decision: ReviewerProfileReviewDecision,
    target: DocumentOnboardingRequest,
) -> LocatorBoundContextBundle:
    return workflow.attach_approved_context(
        decision,
        target,
        bundle_id="attached-revenue-context-v1",
        attached_by="Synthetic operator",
        attached_at=_NOW,
        rationale="Use reviewed revenue context in the broader statement task.",
    )


@pytest.mark.parametrize("explicit_scope", [False, True])
def test_scoped_context_attaches_to_full_statement_with_original_lineage(
    tmp_path: Path, explicit_scope: bool
) -> None:
    session = _session(tmp_path)
    workflow, decision = _approved_profile(session)
    source = session.onboarding_request
    target = source.model_copy(
        update={
            "request_id": "fictional-full-statement",
            "target_scope": (
                OnboardingTargetScope(
                    scope_id="full-statement-v1",
                    metric_ids=(MetricId.REVENUE, MetricId.FINANCE_COST),
                    purpose="Synthetic statement scope.",
                )
                if explicit_scope
                else None
            ),
        }
    )
    original_decision = decision.model_dump_json()
    with pytest.raises(ValueError, match="request ID does not match"):
        PromptIsolatedOnboardingInputBuilder().build(
            target,
            input_id="unattached",
            policy=OnboardingModelInputPolicy(policy_version="test-v1"),
            context_bundle=decision.candidate.extracted_context,
        )
    attached = _attach(workflow, decision, target)
    assert attached.request_id == target.request_id
    assert attached.snippets == decision.candidate.extracted_context.snippets
    assert attached.snippets[0].metric_ids == (MetricId.REVENUE,)
    assert (
        attached.extraction_provenance == decision.candidate.extracted_context.extraction_provenance
    )
    provenance = attached.attachment_provenance
    assert provenance is not None
    assert provenance.source_request_id == source.request_id
    assert provenance.source_request_checksum_sha256 == onboarding_request_checksum(source)
    assert provenance.target_request_checksum_sha256 == onboarding_request_checksum(target)
    assert provenance.profile_decision_id == decision.decision_id
    assert decision.model_dump_json() == original_decision
    # New optional metadata cannot change the checksums of already saved approvals.
    legacy_candidate = decision.candidate.model_dump(mode="json")
    legacy_candidate["extracted_context"].pop("attachment_provenance")
    legacy_digest = hashlib.sha256(
        json.dumps(legacy_candidate, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert legacy_digest == decision.candidate_checksum_sha256

    changed_row = target.evidence_rows[0].model_copy(update={"raw_value": "999"})
    changed_target = target.model_copy(update={"evidence_rows": (changed_row,)})
    with pytest.raises(ValueError, match="target request checksum"):
        PromptIsolatedOnboardingInputBuilder().build(
            changed_target,
            input_id="changed-target",
            policy=OnboardingModelInputPolicy(policy_version="test-v1"),
            context_bundle=attached,
        )
    tampered = attached.model_dump(mode="json")
    tampered["attachment_provenance"]["source_context_checksum_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="original excerpt checksum"):
        LocatorBoundContextBundle.model_validate(tampered)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("company_id", "otherco"),
        ("document_id", "revised-document"),
        ("source_checksum_sha256", "b" * 64),
        ("source_reference_id", "different-source"),
        ("source_organization", "different-publisher"),
        ("document_type", DocumentType.OTHER),
        ("unit", "INR million"),
        (
            "period",
            ReportingPeriod(
                label="FY2024",
                period_type=PeriodType.ANNUAL,
                start_date=date(2023, 4, 1),
                end_date=date(2024, 3, 31),
            ),
        ),
        ("reporting_basis", ReportingBasis.STANDALONE),
    ],
)
def test_attachment_rejects_incompatible_accounting_identity(
    tmp_path: Path, field: str, value: object
) -> None:
    session = _session(tmp_path)
    workflow, decision = _approved_profile(session)
    target = session.onboarding_request.model_copy(
        update={"request_id": "other-task", field: value}
    )
    with pytest.raises(ValueError, match=f"incompatible target {field}"):
        _attach(workflow, decision, target)


def test_attachment_rejects_excluded_metric_rejection_and_changed_source(tmp_path: Path) -> None:
    session = _session(tmp_path)
    workflow, decision = _approved_profile(session)
    target = session.onboarding_request.model_copy(
        update={
            "request_id": "finance-only-task",
            "target_scope": OnboardingTargetScope(
                scope_id="finance-only",
                metric_ids=(MetricId.FINANCE_COST,),
                purpose="Exclude revenue from the synthetic target.",
            ),
        }
    )
    with pytest.raises(ValueError, match="outside the target metric scope"):
        _attach(workflow, decision, target)
    rejected = decision.model_copy(
        update={"outcome": "rejected", "approved_profile": None, "rejection_reasons": ("test",)}
    )
    with pytest.raises(ValueError, match="only an approved"):
        _attach(workflow, rejected, session.onboarding_request)
    source_path = session.raw_root / session.source_manifest.stored_relative_path
    source_path.chmod(0o600)
    source_path.write_bytes(b"Changed synthetic source for failure testing")
    with pytest.raises(ValueError, match="verification failed"):
        _attach(workflow, decision, session.onboarding_request)


def test_attachment_cli_persists_reusable_context_without_overwriting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = _session(tmp_path)
    _, decision = _approved_profile(session)
    target = session.onboarding_request.model_copy(
        update={"request_id": "full-statement-task", "target_scope": None}
    )
    artifacts = {
        "source-manifest": session.source_manifest,
        "request": session.onboarding_request,
        "page-discovery-input": session._page_discovery_input,
        "page-discovery-proposal": session._page_discovery_proposal,
        "decision": decision,
        "target-request": target,
    }
    args = ["attach-approved-reviewer-profile-context"]
    for name, artifact in artifacts.items():
        path = tmp_path / f"{name}.json"
        path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
        args.extend([f"--{name}", str(path)])
    output = tmp_path / "attached-context.json"
    args.extend(
        [
            "--bundle-id",
            "attached-cli-v1",
            "--attached-by",
            "Synthetic operator",
            "--attached-at",
            _NOW.isoformat(),
            "--rationale",
            "Reviewed context for full P&L.",
            "--output",
            str(output),
        ]
    )
    monkeypatch.setenv("ICA_DATA_DIRECTORY", str(tmp_path))
    assert main(args) == 0
    assert main(args) == 0
    attached = LocatorBoundContextBundle.model_validate_json(output.read_text())
    packet = PromptIsolatedOnboardingInputBuilder().build(
        target,
        input_id="full-statement-packet",
        policy=OnboardingModelInputPolicy(policy_version="test-v1"),
        context_bundle=attached,
    )
    assert packet.locator_bound_context == attached
    assert packet.untrusted_evidence_rows[0].raw_value == "100"
    assert attached.attachment_provenance is not None
    assert attached.attachment_provenance.source_request_id == session.onboarding_request.request_id
    args[args.index("--rationale") + 1] = "A different attachment record."
    with pytest.raises(ValueError, match="refusing to overwrite"):
        main(args)
