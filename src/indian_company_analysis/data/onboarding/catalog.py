"""Append-only local storage for reviewed onboarding configurations and decisions."""

from __future__ import annotations

from pathlib import Path

from indian_company_analysis.data.onboarding.models import (
    ApprovedOnboardingConfiguration,
    DocumentOnboardingRequest,
    OnboardingReviewDecision,
)
from indian_company_analysis.data.onboarding.validation import validate_configuration_identity
from indian_company_analysis.domain.enums import DocumentType


def _safe_path_component(value: str, *, field_name: str) -> str:
    candidate = Path(value)
    if value in {"", ".", ".."} or candidate.name != value or value.startswith("."):
        raise ValueError(f"{field_name} must be a safe single path component")
    return value


class LocalOnboardingConfigurationCatalog:
    """Persist approved configurations once and retrieve them only for matching evidence."""

    def __init__(self, catalog_root: Path) -> None:
        self._catalog_root = catalog_root

    def register(self, configuration: ApprovedOnboardingConfiguration) -> bool:
        path = self.path_for(configuration)
        return self._write_once(path, configuration.model_dump_json(indent=2) + "\n")

    def get_for_request(
        self,
        request: DocumentOnboardingRequest,
        *,
        configuration_version: str,
    ) -> ApprovedOnboardingConfiguration:
        path = self._path_for_identity(
            company_id=request.company_id,
            document_type=request.document_type,
            extraction_profile_version=request.extraction_profile_version,
            configuration_version=configuration_version,
        )
        configuration = ApprovedOnboardingConfiguration.model_validate_json(
            path.read_text(encoding="utf-8")
        )
        validate_configuration_identity(request, configuration)
        return configuration

    def path_for(self, configuration: ApprovedOnboardingConfiguration) -> Path:
        return self._path_for_identity(
            company_id=configuration.company_id,
            document_type=configuration.document_type,
            extraction_profile_version=configuration.extraction_profile_version,
            configuration_version=configuration.configuration_version,
        )

    def _path_for_identity(
        self,
        *,
        company_id: str,
        document_type: DocumentType,
        extraction_profile_version: str,
        configuration_version: str,
    ) -> Path:
        version = _safe_path_component(
            configuration_version,
            field_name="configuration_version",
        )
        return (
            self._catalog_root
            / _safe_path_component(company_id, field_name="company_id")
            / _safe_path_component(document_type.value, field_name="document_type")
            / _safe_path_component(
                extraction_profile_version,
                field_name="extraction_profile_version",
            )
            / f"{version}.json"
        )

    @staticmethod
    def _write_once(path: Path, serialized: str) -> bool:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("x", encoding="utf-8") as catalog_file:
                catalog_file.write(serialized)
        except FileExistsError:
            if path.read_text(encoding="utf-8") != serialized:
                raise ValueError(f"catalog already contains a different record at {path}") from None
            return False
        return True


class LocalOnboardingReviewCatalog:
    """Persist reviewer decisions once; rejections and approvals remain separate artifacts."""

    def __init__(self, catalog_root: Path) -> None:
        self._catalog_root = catalog_root

    def register(self, decision: OnboardingReviewDecision) -> bool:
        decision_id = _safe_path_component(decision.decision_id, field_name="decision_id")
        path = self._catalog_root / f"{decision_id}.json"
        return LocalOnboardingConfigurationCatalog._write_once(
            path,
            decision.model_dump_json(indent=2) + "\n",
        )
