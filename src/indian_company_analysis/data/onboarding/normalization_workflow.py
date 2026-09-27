"""Verified workflow for combining reviewed mappings and aggregations."""

from __future__ import annotations

import csv
from pathlib import Path

from pydantic import Field, model_validator

from indian_company_analysis.data.extraction.linking import verify_extraction_link
from indian_company_analysis.data.extraction.models import DocumentExtractionLink
from indian_company_analysis.data.extraction.serialization import CONTROLLED_CSV_COLUMNS
from indian_company_analysis.data.ingestion.models import RawDocumentManifest
from indian_company_analysis.data.normalization.models import (
    ExtractionReference,
    NormalizedFact,
)
from indian_company_analysis.data.normalization.numbers import parse_reported_decimal
from indian_company_analysis.data.onboarding.aggregation import (
    AggregatedNormalizedFact,
    execute_approved_aggregations,
)
from indian_company_analysis.data.onboarding.models import (
    ApprovedExclusion,
    ApprovedOnboardingConfiguration,
    DocumentOnboardingRequest,
)
from indian_company_analysis.data.onboarding.validation import validate_configuration_identity
from indian_company_analysis.domain.enums import ExtractionReviewStatus, ValueClassification
from indian_company_analysis.domain.models import DomainModel, MetricObservation, SourceReference


class OnboardingNormalizationIssue(DomainModel):
    """Explicit failure while producing one direct or aggregated fact."""

    stage: str = Field(min_length=1)
    decision_id: str = Field(min_length=1)
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    evidence_id: str | None = None


class OnboardingNormalizationBatch(DomainModel):
    """Persistable normalized output of one reviewed onboarding configuration."""

    document_id: str = Field(min_length=1)
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_reference: SourceReference
    extraction_link: DocumentExtractionLink
    configuration: ApprovedOnboardingConfiguration
    parser_version: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)
    total_evidence_rows: int = Field(ge=1)
    direct_facts: tuple[NormalizedFact, ...]
    aggregated_facts: tuple[AggregatedNormalizedFact, ...]
    exclusions: tuple[ApprovedExclusion, ...]
    issues: tuple[OnboardingNormalizationIssue, ...]
    analysis_blockers: tuple[str, ...]
    ready_for_analysis: bool

    @model_validator(mode="after")
    def lineage_and_readiness_are_consistent(self) -> OnboardingNormalizationBatch:
        if self.total_evidence_rows != len(self.evidence_ids):
            raise ValueError("total evidence rows must match the recorded evidence IDs")
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("normalization batch contains duplicate evidence IDs")
        if self.ready_for_analysis != (not self.issues and not self.analysis_blockers):
            raise ValueError("ready_for_analysis requires no issues or analysis blockers")
        if self.configuration.document_id != self.document_id:
            raise ValueError("configuration document must match the normalization batch")
        if self.configuration.source_checksum_sha256 != self.source_checksum_sha256:
            raise ValueError("configuration checksum must match the normalization batch")
        if self.source_reference.source_id != self.configuration.source_reference_id:
            raise ValueError("source reference must match the approved configuration")
        if self.extraction_link.extraction_id != self.configuration.extraction_id:
            raise ValueError("extraction link must match the approved configuration")
        if self.extraction_link.profile_version != self.configuration.extraction_profile_version:
            raise ValueError("extraction profile must match the approved configuration")
        if self.extraction_link.source_document_id != self.document_id:
            raise ValueError("extraction link source must match the normalization document")
        if self.extraction_link.source_checksum_sha256 != self.source_checksum_sha256:
            raise ValueError("extraction link checksum must match the normalization batch")
        if self.exclusions != self.configuration.exclusions:
            raise ValueError("batch exclusions must match the approved configuration")

        required_blockers = set(self.configuration.normalization_blockers)
        if not self.extraction_link.benchmark.passed:
            required_blockers.add("extraction benchmark did not meet its required exact-match rate")
        if self.extraction_link.review_status is not ExtractionReviewStatus.REVIEWED:
            required_blockers.add("extraction has not received an accepted human review")
        if not required_blockers <= set(self.analysis_blockers):
            raise ValueError("normalization batch omits a required analysis blocker")

        disposition_ids = [mapping.evidence_id for mapping in self.configuration.direct_mappings]
        for rule in self.configuration.aggregation_rules:
            disposition_ids.extend(component.evidence_id for component in rule.components)
        disposition_ids.extend(exclusion.evidence_id for exclusion in self.exclusions)
        if set(disposition_ids) != set(self.evidence_ids):
            raise ValueError("approved dispositions must cover every source evidence row")

        metric_ids = [fact.observation.metric_id for fact in self.direct_facts]
        metric_ids.extend(fact.observation.metric_id for fact in self.aggregated_facts)
        if len(metric_ids) != len(set(metric_ids)):
            raise ValueError("normalization batch contains duplicate canonical metrics")
        for direct_fact in self.direct_facts:
            if direct_fact.document_id != self.document_id:
                raise ValueError("direct facts must match the normalization document")
            if direct_fact.source_checksum_sha256 != self.source_checksum_sha256:
                raise ValueError("direct facts must match the normalization checksum")
        for aggregated_fact in self.aggregated_facts:
            if aggregated_fact.document_id != self.document_id:
                raise ValueError("aggregated facts must match the normalization document")
            if aggregated_fact.source_checksum_sha256 != self.source_checksum_sha256:
                raise ValueError("aggregated facts must match the normalization checksum")
        return self


class OnboardingNormalizationWorkflow:
    """Verify Phase 2C lineage and materialize all approved Phase 2D facts."""

    parser_version = "reviewed-onboarding-v1"

    def normalize(
        self,
        *,
        source_manifest: RawDocumentManifest,
        extraction_manifest: RawDocumentManifest,
        extraction_link: DocumentExtractionLink,
        request: DocumentOnboardingRequest,
        configuration: ApprovedOnboardingConfiguration,
        raw_root: Path,
    ) -> OnboardingNormalizationBatch:
        verification = verify_extraction_link(
            extraction_link,
            source_manifest,
            extraction_manifest,
            raw_root,
        )
        if not verification.valid:
            raise ValueError(f"extraction link verification failed: {verification.message}")
        self._validate_source_identity(source_manifest, extraction_link, request)
        validate_configuration_identity(request, configuration)
        self._validate_controlled_csv(extraction_manifest, request, raw_root)
        self._validate_dispositions(request, configuration)

        extraction_reference = ExtractionReference(
            extraction_id=extraction_link.extraction_id,
            extraction_document_id=extraction_link.extraction_document_id,
            extraction_checksum_sha256=extraction_link.extraction_checksum_sha256,
        )
        direct_facts, direct_issues = self._normalize_direct_mappings(
            request,
            configuration,
            extraction_reference,
        )
        aggregated_facts: tuple[AggregatedNormalizedFact, ...] = ()
        aggregation_issues: list[OnboardingNormalizationIssue] = []
        if configuration.aggregation_rules:
            aggregation_result = execute_approved_aggregations(request, configuration)
            aggregated_facts = aggregation_result.facts
            aggregation_issues.extend(
                OnboardingNormalizationIssue(
                    stage="aggregation",
                    decision_id=issue.rule_id,
                    code=issue.code,
                    message=issue.message,
                    evidence_id=issue.evidence_id,
                )
                for issue in aggregation_result.issues
            )

        blockers: list[str] = list(configuration.normalization_blockers)
        if not extraction_link.benchmark.passed:
            blockers.append("extraction benchmark did not meet its required exact-match rate")
        if extraction_link.review_status is not ExtractionReviewStatus.REVIEWED:
            blockers.append("extraction has not received an accepted human review")

        issues = (*direct_issues, *aggregation_issues)
        parsed_source = source_manifest.source_reference.model_copy(
            update={"parser_version": self.parser_version}
        )
        return OnboardingNormalizationBatch(
            document_id=request.document_id,
            source_checksum_sha256=request.source_checksum_sha256,
            source_reference=parsed_source,
            extraction_link=extraction_link,
            configuration=configuration,
            parser_version=self.parser_version,
            evidence_ids=tuple(row.evidence_id for row in request.evidence_rows),
            total_evidence_rows=len(request.evidence_rows),
            direct_facts=direct_facts,
            aggregated_facts=aggregated_facts,
            exclusions=configuration.exclusions,
            issues=issues,
            analysis_blockers=tuple(blockers),
            ready_for_analysis=not issues and not blockers,
        )

    @staticmethod
    def persist(batch: OnboardingNormalizationBatch, output: Path) -> None:
        """Write a versioned batch without overwriting different prior output."""

        output.parent.mkdir(parents=True, exist_ok=True)
        serialized = batch.model_dump_json(indent=2) + "\n"
        if output.exists() and output.read_text(encoding="utf-8") != serialized:
            raise ValueError(f"refusing to overwrite different normalized output: {output}")
        output.write_text(serialized, encoding="utf-8")

    def _normalize_direct_mappings(
        self,
        request: DocumentOnboardingRequest,
        configuration: ApprovedOnboardingConfiguration,
        extraction_reference: ExtractionReference,
    ) -> tuple[tuple[NormalizedFact, ...], tuple[OnboardingNormalizationIssue, ...]]:
        evidence_by_id = {row.evidence_id: row for row in request.evidence_rows}
        facts: list[NormalizedFact] = []
        issues: list[OnboardingNormalizationIssue] = []
        for mapping in configuration.direct_mappings:
            evidence = evidence_by_id.get(mapping.evidence_id)
            if evidence is None:
                issues.append(
                    OnboardingNormalizationIssue(
                        stage="direct_mapping",
                        decision_id=mapping.candidate_id,
                        code="unknown_evidence",
                        message="approved direct mapping evidence is absent from the request",
                        evidence_id=mapping.evidence_id,
                    )
                )
                continue
            if (
                evidence.source_locator != mapping.source_locator
                or evidence.reported_label != mapping.reported_label
                or evidence.raw_value != mapping.raw_value
            ):
                issues.append(
                    OnboardingNormalizationIssue(
                        stage="direct_mapping",
                        decision_id=mapping.candidate_id,
                        code="evidence_snapshot_mismatch",
                        message="request evidence differs from the approved direct mapping",
                        evidence_id=mapping.evidence_id,
                    )
                )
                continue
            try:
                value = parse_reported_decimal(evidence.raw_value)
            except ValueError as error:
                issues.append(
                    OnboardingNormalizationIssue(
                        stage="direct_mapping",
                        decision_id=mapping.candidate_id,
                        code="invalid_numeric_value",
                        message=str(error),
                        evidence_id=mapping.evidence_id,
                    )
                )
                continue

            locator = evidence.source_locator
            fact_id = (
                f"{request.document_id}:{locator.table_id}:"
                f"{locator.row_number}:{locator.column_name}"
            )
            observation = MetricObservation(
                observation_id=fact_id,
                company_id=request.company_id,
                metric_id=mapping.metric_id,
                value=value * mapping.sign_multiplier,
                unit=request.unit,
                period=request.period,
                reporting_basis=request.reporting_basis,
                value_classification=ValueClassification.REPORTED,
                source_reference_ids=(request.source_reference_id,),
            )
            facts.append(
                NormalizedFact(
                    fact_id=fact_id,
                    document_id=request.document_id,
                    source_checksum_sha256=request.source_checksum_sha256,
                    source_locator=locator,
                    reported_label=evidence.reported_label,
                    raw_value=evidence.raw_value,
                    observation=observation,
                    parser_version=self.parser_version,
                    mapping_version=configuration.configuration_version,
                    mapping_method="model_assisted_reviewed",
                    mapping_confidence=mapping.confidence,
                    extraction_reference=extraction_reference,
                )
            )
        return tuple(facts), tuple(issues)

    @staticmethod
    def _validate_source_identity(
        source_manifest: RawDocumentManifest,
        extraction_link: DocumentExtractionLink,
        request: DocumentOnboardingRequest,
    ) -> None:
        expected = (
            source_manifest.document_id,
            source_manifest.company_id,
            source_manifest.checksum_sha256,
            source_manifest.source_reference.source_id,
            source_manifest.source_reference.source_organization,
            source_manifest.document_type,
            extraction_link.extraction_id,
            extraction_link.profile_version,
        )
        actual = (
            request.document_id,
            request.company_id,
            request.source_checksum_sha256,
            request.source_reference_id,
            request.source_organization,
            request.document_type,
            request.extraction_id,
            request.extraction_profile_version,
        )
        if actual != expected:
            raise ValueError("onboarding request identity does not match reviewed source lineage")

    @staticmethod
    def _validate_dispositions(
        request: DocumentOnboardingRequest,
        configuration: ApprovedOnboardingConfiguration,
    ) -> None:
        evidence_ids = [mapping.evidence_id for mapping in configuration.direct_mappings]
        for rule in configuration.aggregation_rules:
            evidence_ids.extend(component.evidence_id for component in rule.components)
        evidence_ids.extend(exclusion.evidence_id for exclusion in configuration.exclusions)
        request_ids = [row.evidence_id for row in request.evidence_rows]
        if len(evidence_ids) != len(set(evidence_ids)) or set(evidence_ids) != set(request_ids):
            raise ValueError(
                "approved configuration must dispose of every request evidence row once"
            )

    @staticmethod
    def _validate_controlled_csv(
        extraction_manifest: RawDocumentManifest,
        request: DocumentOnboardingRequest,
        raw_root: Path,
    ) -> None:
        stored_path = raw_root / extraction_manifest.stored_relative_path
        with stored_path.open(encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            fieldnames = set(reader.fieldnames or ())
            missing = sorted(set(CONTROLLED_CSV_COLUMNS) - fieldnames)
            if missing:
                raise ValueError(
                    "controlled extraction is missing required columns: " + ", ".join(missing)
                )
            rows = list(reader)
        if len(rows) != len(request.evidence_rows):
            raise ValueError("controlled extraction row count differs from onboarding evidence")

        for record_number, (row, evidence) in enumerate(
            zip(rows, request.evidence_rows, strict=True), start=2
        ):
            locator = evidence.source_locator
            expected = {
                "company_id": request.company_id,
                "page_number": str(locator.page_number),
                "table_id": locator.table_id,
                "row_number": str(locator.row_number),
                "column_name": locator.column_name,
                "reported_label": evidence.reported_label,
                "value": evidence.raw_value,
                "unit": request.unit,
                "period_label": request.period.label,
                "period_type": request.period.period_type.value,
                "period_start_date": request.period.start_date.isoformat(),
                "period_end_date": request.period.end_date.isoformat(),
                "reporting_basis": request.reporting_basis.value,
            }
            actual = {column: row.get(column) for column in CONTROLLED_CSV_COLUMNS}
            if actual != expected:
                raise ValueError(
                    f"controlled extraction record {record_number} differs from onboarding evidence"
                )
