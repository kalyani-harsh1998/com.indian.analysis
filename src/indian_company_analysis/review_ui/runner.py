"""Local server bootstrap for one verified PDF review session."""

from __future__ import annotations

from pathlib import Path

from indian_company_analysis.data.extraction.page_discovery import (
    PageDiscoveryInput,
    PageDiscoveryProposal,
)
from indian_company_analysis.data.ingestion.models import RawDocumentManifest
from indian_company_analysis.data.onboarding.models import DocumentOnboardingRequest
from indian_company_analysis.review_ui.app import create_app
from indian_company_analysis.review_ui.service import ProfileReviewSession


def load_profile_review_session(
    *,
    source_manifest_path: Path,
    request_path: Path,
    page_discovery_input_path: Path,
    page_discovery_proposal_path: Path,
    raw_root: Path,
    draft_root: Path,
) -> ProfileReviewSession:
    """Load one identity-bound profile-review session from local JSON artifacts."""

    return ProfileReviewSession(
        source_manifest=RawDocumentManifest.model_validate_json(
            source_manifest_path.read_text(encoding="utf-8")
        ),
        onboarding_request=DocumentOnboardingRequest.model_validate_json(
            request_path.read_text(encoding="utf-8")
        ),
        page_discovery_input=PageDiscoveryInput.model_validate_json(
            page_discovery_input_path.read_text(encoding="utf-8")
        ),
        page_discovery_proposal=PageDiscoveryProposal.model_validate_json(
            page_discovery_proposal_path.read_text(encoding="utf-8")
        ),
        raw_root=raw_root,
        draft_root=draft_root,
    )


def run_profile_reviewer(
    *,
    source_manifest_path: Path,
    request_path: Path,
    page_discovery_input_path: Path,
    page_discovery_proposal_path: Path,
    raw_root: Path,
    draft_root: Path,
    host: str,
    port: int,
) -> None:
    """Start a local Uvicorn process only after validating all review-session inputs."""

    from uvicorn import run

    session = load_profile_review_session(
        source_manifest_path=source_manifest_path,
        request_path=request_path,
        page_discovery_input_path=page_discovery_input_path,
        page_discovery_proposal_path=page_discovery_proposal_path,
        raw_root=raw_root,
        draft_root=draft_root,
    )
    run(create_app(session), host=host, port=port)
