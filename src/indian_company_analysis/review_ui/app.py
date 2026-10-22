"""FastAPI outer adapter for the local PDF-region reviewer."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response

from indian_company_analysis.review_ui.models import RegionDraftSubmission
from indian_company_analysis.review_ui.service import ProfileReviewSession

_STATIC_ROOT = Path(__file__).with_name("static")


def create_app(session: ProfileReviewSession) -> FastAPI:
    """Create one local-only app bound to a single verified review session."""

    app = FastAPI(
        title="Indian Company Analysis - PDF Profile Reviewer",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(_STATIC_ROOT / "index.html")

    @app.get("/static/reviewer.js", include_in_schema=False)
    def reviewer_javascript() -> FileResponse:
        return FileResponse(_STATIC_ROOT / "reviewer.js", media_type="text/javascript")

    @app.get("/static/reviewer.css", include_in_schema=False)
    def reviewer_css() -> FileResponse:
        return FileResponse(_STATIC_ROOT / "reviewer.css", media_type="text/css")

    @app.get("/api/session")
    def session_metadata() -> dict[str, object]:
        return session.metadata().model_dump(mode="json")

    @app.get("/api/pages/{page_number}.png")
    def page_image(page_number: int) -> Response:
        try:
            return Response(content=session.render_page_png(page_number), media_type="image/png")
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.post("/api/region-drafts")
    def create_region_draft(submission: RegionDraftSubmission) -> dict[str, object]:
        try:
            draft, preview_text = session.create_draft(submission)
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return {"draft": draft.model_dump(mode="json"), "preview_text": preview_text}

    return app
