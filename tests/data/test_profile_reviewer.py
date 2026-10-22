"""Tests for the local, identity-bound PDF profile-review service."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

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
from indian_company_analysis.review_ui.models import RegionDraftSubmission
from indian_company_analysis.review_ui.service import ProfileReviewSession


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
