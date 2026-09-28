"""Tests for checksum-bound PDF extraction, benchmarking, and normalization lineage."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from indian_company_analysis.__main__ import main
from indian_company_analysis.data.extraction.aligned_pdf import (
    AlignedPdfStatementExtractor,
)
from indian_company_analysis.data.extraction.benchmark import benchmark_extraction
from indian_company_analysis.data.extraction.link_catalog import LocalExtractionLinkCatalog
from indian_company_analysis.data.extraction.linking import (
    ExtractionLinker,
    verify_extraction_link,
)
from indian_company_analysis.data.extraction.models import (
    AlignedPdfTableExtractionSpec,
    DocumentExtractionLink,
    ExpectedExtractionRow,
    ExtractionBenchmarkFixture,
    ExtractionBenchmarkResult,
    PdfTableExtractionResult,
    PdfTableExtractionSpec,
)
from indian_company_analysis.data.extraction.pdf_table import RuledPdfTableExtractor
from indian_company_analysis.data.ingestion.local_intake import ImmutableRawDocumentStore
from indian_company_analysis.data.ingestion.models import (
    LocalDocumentIntakeRequest,
    RawDocumentManifest,
)
from indian_company_analysis.data.normalization.csv_parser import ControlledCsvFinancialParser
from indian_company_analysis.data.normalization.models import MetricMappingSet
from indian_company_analysis.data.onboarding import (
    ApprovedOnboardingConfiguration,
    DocumentOnboardingProposal,
    DocumentOnboardingRequest,
    ExclusionCandidate,
    MappingCandidate,
    MetricAggregationCandidate,
    MetricAggregationComponent,
    ModelRunProvenance,
    OnboardingNormalizationBatch,
    OnboardingNormalizationWorkflow,
    approve_onboarding_proposal,
    build_onboarding_request,
)
from indian_company_analysis.domain.enums import (
    ConfidenceLevel,
    DocumentType,
    ExtractionReviewStatus,
    LicenceCategory,
    PeriodType,
    ReportingBasis,
    SourceKind,
)
from indian_company_analysis.domain.metrics import MetricId

_NOW = datetime(2026, 9, 26, 12, tzinfo=UTC)


def _intake(
    raw_root: Path,
    *,
    input_path: Path,
    document_id: str,
    document_type: DocumentType,
) -> RawDocumentManifest:
    request = LocalDocumentIntakeRequest(
        document_id=document_id,
        company_id="fictionalco",
        document_type=document_type,
        source_kind=SourceKind.SYNTHETIC,
        source_organization="Synthetic test fixture",
        source_document="Fictional Co FY25 annual report",
        source_locator=str(input_path),
        source_publication_date=date(2025, 5, 20),
        retrieved_at=_NOW,
        licence_category=LicenceCategory.INTERNAL_POC,
        input_path=input_path,
        is_synthetic=True,
    )
    return ImmutableRawDocumentStore(raw_root).ingest(request).manifest


def _spec() -> PdfTableExtractionSpec:
    return PdfTableExtractionSpec(
        extraction_id="fictionalco-fy25-profit-loss-extraction",
        page_number=1,
        table_id="profit_and_loss",
        label_column_name="Particulars",
        value_column_name="FY2025",
        unit="INR million",
        period_label="FY2025",
        period_type=PeriodType.ANNUAL,
        period_start_date=date(2024, 4, 1),
        period_end_date=date(2025, 3, 31),
        reporting_basis=ReportingBasis.CONSOLIDATED,
    )


def _aligned_spec() -> AlignedPdfTableExtractionSpec:
    return AlignedPdfTableExtractionSpec(
        extraction_id="fictionalco-fy26-aligned-profit-loss",
        page_number=2,
        table_id="aligned_profit_and_loss",
        label_column_name="Particulars",
        value_column_name="2026",
        unit="INR million",
        period_label="FY2026",
        period_type=PeriodType.ANNUAL,
        period_start_date=date(2025, 4, 1),
        period_end_date=date(2026, 3, 31),
        reporting_basis=ReportingBasis.CONSOLIDATED,
        data_top=Decimal("165"),
        data_bottom=Decimal("285"),
        label_x0=Decimal("60"),
        label_x1=Decimal("300"),
        value_x0=Decimal("430"),
        value_x1=Decimal("480"),
    )


def _expected_rows() -> tuple[ExpectedExtractionRow, ...]:
    fixture_path = Path("tests/fixtures/benchmarks/fictional_annual_report_profit_loss.json")
    fixture = ExtractionBenchmarkFixture.model_validate_json(
        fixture_path.read_text(encoding="utf-8")
    )
    return fixture.expected_rows


def _aligned_benchmark_fixture() -> ExtractionBenchmarkFixture:
    fixture_path = Path("tests/fixtures/benchmarks/fictional_aligned_profit_loss_fy2026.json")
    return ExtractionBenchmarkFixture.model_validate_json(fixture_path.read_text(encoding="utf-8"))


def _linked_artifacts(
    tmp_path: Path, *, reviewed: bool = True
) -> tuple[
    RawDocumentManifest,
    RawDocumentManifest,
    PdfTableExtractionResult,
    ExtractionBenchmarkResult,
    DocumentExtractionLink,
    Path,
]:
    raw_root = tmp_path / "raw"
    source_manifest = _intake(
        raw_root,
        input_path=Path("tests/fixtures/documents/fictional_annual_report.pdf"),
        document_id="fictionalco-fy25-annual-report-pdf",
        document_type=DocumentType.ANNUAL_REPORT,
    )
    extractor = RuledPdfTableExtractor()
    extraction_result = extractor.extract(source_manifest, raw_root, _spec())
    benchmark = benchmark_extraction(
        extraction_result,
        _expected_rows(),
        benchmark_version="fictional-golden-v1",
    )
    csv_path = tmp_path / "fictionalco-fy25-extraction.csv"
    csv_path.write_text(
        extractor.to_controlled_csv(extraction_result, company_id="fictionalco"),
        encoding="utf-8",
    )
    extraction_manifest = _intake(
        raw_root,
        input_path=csv_path,
        document_id="fictionalco-fy25-controlled-extraction",
        document_type=DocumentType.CONTROLLED_EXTRACTION,
    )
    review_status = (
        ExtractionReviewStatus.REVIEWED if reviewed else ExtractionReviewStatus.UNREVIEWED
    )
    link = ExtractionLinker(raw_root).link(
        source_manifest=source_manifest,
        extraction_manifest=extraction_manifest,
        extraction_result=extraction_result,
        benchmark=benchmark,
        extracted_at=_NOW,
        review_status=review_status,
        reviewed_by="Synthetic fixture reviewer" if reviewed else None,
        reviewed_at=_NOW if reviewed else None,
    )
    return source_manifest, extraction_manifest, extraction_result, benchmark, link, raw_root


def _approved_onboarding(
    source_manifest: RawDocumentManifest,
    extraction_result: PdfTableExtractionResult,
) -> tuple[DocumentOnboardingRequest, ApprovedOnboardingConfiguration]:
    request = build_onboarding_request(
        extraction_result,
        request_id="fictionalco-fy25-onboarding-v1",
        company_id=source_manifest.company_id,
        source_reference_id=source_manifest.source_reference.source_id,
        source_organization=source_manifest.source_reference.source_organization,
        document_type=source_manifest.document_type,
    )
    evidence_ids = [row.evidence_id for row in request.evidence_rows]
    proposal = DocumentOnboardingProposal(
        proposal_id="fictionalco-fy25-proposal-v1",
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
            provider="deterministic-test-provider",
            model_id="static-proposal",
            model_version="1",
            prompt_version="onboarding-prompt-v1",
            schema_version="onboarding-proposal-v1",
            generated_at=_NOW,
        ),
        mappings=(
            MappingCandidate(
                candidate_id="map-revenue",
                evidence_id=evidence_ids[0],
                reported_label="Revenue from operations",
                metric_id=MetricId.REVENUE,
                confidence=ConfidenceLevel.HIGH,
                rationale="Exact synthetic revenue label.",
            ),
        ),
        aggregations=(
            MetricAggregationCandidate(
                candidate_id="aggregate-tax-from-profit-identity",
                metric_id=MetricId.TAX_EXPENSE,
                components=(
                    MetricAggregationComponent(evidence_id=evidence_ids[1]),
                    MetricAggregationComponent(
                        evidence_id=evidence_ids[3], coefficient=Decimal("-1")
                    ),
                ),
                confidence=ConfidenceLevel.HIGH,
                rationale="Synthetic identity test: profit before tax less PAT equals tax.",
            ),
        ),
        exclusions=(
            ExclusionCandidate(
                evidence_id=evidence_ids[2],
                confidence=ConfidenceLevel.HIGH,
                rationale="Synthetic test excludes the reported total to avoid a duplicate target.",
            ),
        ),
    )
    configuration = approve_onboarding_proposal(
        request,
        proposal,
        configuration_version="fictionalco-fy25-onboarding-config-v1",
        aggregation_rule_version="signed-sum-v1",
        reviewed_by="Synthetic fixture reviewer",
        reviewed_at=_NOW,
        approval_policy_version="human-review-v1",
    )
    return request, configuration


def test_pdf_extraction_matches_golden_rows_and_retains_both_checksums(
    tmp_path: Path,
) -> None:
    source, extraction, result, benchmark, link, raw_root = _linked_artifacts(tmp_path)

    assert result.ready_for_review is True
    assert [row.raw_value for row in result.rows] == ["1000", "180", "45", "135"]
    assert benchmark.exact_match_rate == Decimal("1.000000")
    assert benchmark.passed is True
    assert link.source_checksum_sha256 == source.checksum_sha256
    assert link.extraction_checksum_sha256 == extraction.checksum_sha256
    assert verify_extraction_link(link, source, extraction, raw_root).valid is True


def test_linked_normalization_uses_pdf_as_evidence_and_csv_as_derivation(
    tmp_path: Path,
) -> None:
    source, extraction, _, _, link, raw_root = _linked_artifacts(tmp_path)
    mapping_path = Path("tests/fixtures/mappings/fictional_annual_report.json")
    mapping = MetricMappingSet.model_validate_json(mapping_path.read_text(encoding="utf-8"))

    batch = ControlledCsvFinancialParser().parse_linked(
        source_manifest=source,
        extraction_manifest=extraction,
        extraction_link=link,
        raw_root=raw_root,
        mapping_set=mapping,
    )

    assert batch.ready_for_analysis is True
    assert batch.document_id == source.document_id
    assert batch.source_checksum_sha256 == source.checksum_sha256
    assert batch.extraction_reference is not None
    assert batch.extraction_reference.extraction_checksum_sha256 == extraction.checksum_sha256
    assert batch.facts[0].observation.source_reference_ids == (source.source_reference.source_id,)


def test_reviewed_onboarding_persists_direct_and_aggregated_facts(
    tmp_path: Path,
) -> None:
    source, extraction, extraction_result, _, link, raw_root = _linked_artifacts(tmp_path)
    request, configuration = _approved_onboarding(source, extraction_result)
    workflow = OnboardingNormalizationWorkflow()

    batch = workflow.normalize(
        source_manifest=source,
        extraction_manifest=extraction,
        extraction_link=link,
        request=request,
        configuration=configuration,
        raw_root=raw_root,
    )
    output = tmp_path / "normalized" / "reviewed-onboarding-v1.json"
    workflow.persist(batch, output)
    restored = OnboardingNormalizationBatch.model_validate_json(output.read_text(encoding="utf-8"))

    assert batch.ready_for_analysis is True
    assert batch.total_evidence_rows == 4
    assert len(batch.direct_facts) == 1
    assert batch.direct_facts[0].mapping_method == "model_assisted_reviewed"
    assert batch.direct_facts[0].observation.metric_id is MetricId.REVENUE
    assert len(batch.aggregated_facts) == 1
    assert batch.aggregated_facts[0].observation.metric_id is MetricId.TAX_EXPENSE
    assert batch.aggregated_facts[0].observation.value == Decimal("45")
    assert batch.exclusions[0].reported_label == "Tax expense"
    assert restored == batch


def test_combined_onboarding_retains_unreviewed_extraction_blocker(tmp_path: Path) -> None:
    source, extraction, extraction_result, _, link, raw_root = _linked_artifacts(
        tmp_path, reviewed=False
    )
    request, configuration = _approved_onboarding(source, extraction_result)

    batch = OnboardingNormalizationWorkflow().normalize(
        source_manifest=source,
        extraction_manifest=extraction,
        extraction_link=link,
        request=request,
        configuration=configuration,
        raw_root=raw_root,
    )

    assert batch.ready_for_analysis is False
    assert batch.analysis_blockers == ("extraction has not received an accepted human review",)
    tampered = batch.model_dump()
    tampered["analysis_blockers"] = ()
    tampered["ready_for_analysis"] = True
    with pytest.raises(ValidationError, match="required analysis blocker"):
        OnboardingNormalizationBatch.model_validate(tampered)


def test_normalize_onboarding_command_persists_the_combined_batch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source, extraction, extraction_result, _, link, _ = _linked_artifacts(tmp_path)
    request, configuration = _approved_onboarding(source, extraction_result)
    artifacts = {
        "source.json": source,
        "extraction.json": extraction,
        "link.json": link,
        "request.json": request,
        "configuration.json": configuration,
    }
    for filename, artifact in artifacts.items():
        (tmp_path / filename).write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
    output = tmp_path / "processed" / "combined.json"
    monkeypatch.setenv("ICA_DATA_DIRECTORY", str(tmp_path))

    exit_code = main(
        [
            "normalize-onboarding",
            "--source-manifest",
            str(tmp_path / "source.json"),
            "--extraction-manifest",
            str(tmp_path / "extraction.json"),
            "--extraction-link",
            str(tmp_path / "link.json"),
            "--request",
            str(tmp_path / "request.json"),
            "--configuration",
            str(tmp_path / "configuration.json"),
            "--output",
            str(output),
        ]
    )
    batch = OnboardingNormalizationBatch.model_validate_json(output.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert batch.ready_for_analysis is True
    assert len(batch.direct_facts) == 1
    assert len(batch.aggregated_facts) == 1


def test_unreviewed_extraction_is_preserved_but_blocked_from_analysis(tmp_path: Path) -> None:
    source, extraction, _, _, link, raw_root = _linked_artifacts(tmp_path, reviewed=False)
    mapping_path = Path("tests/fixtures/mappings/fictional_annual_report.json")
    mapping = MetricMappingSet.model_validate_json(mapping_path.read_text(encoding="utf-8"))

    batch = ControlledCsvFinancialParser().parse_linked(
        source_manifest=source,
        extraction_manifest=extraction,
        extraction_link=link,
        raw_root=raw_root,
        mapping_set=mapping,
    )

    assert batch.ready_for_analysis is False
    assert batch.total_rows == 4
    assert not batch.issues
    assert batch.analysis_blockers == ("extraction has not received an accepted human review",)


def test_benchmark_mismatch_is_explicit(tmp_path: Path) -> None:
    _, _, extraction_result, _, _, _ = _linked_artifacts(tmp_path)
    expected_rows = _expected_rows()
    wrong_expected = expected_rows[:-1] + (
        ExpectedExtractionRow(
            row_number=4,
            reported_label="Profit for the year",
            raw_value="999",
        ),
    )
    benchmark = benchmark_extraction(
        extraction_result,
        wrong_expected,
        benchmark_version="fictional-golden-with-error-v1",
    )

    assert benchmark.exact_match_rate == Decimal("0.750000")
    assert benchmark.passed is False
    assert benchmark.mismatches == (
        "row 4: expected ('Profit for the year', '999'), actual ('Profit for the year', '135')",
    )


def test_extraction_link_catalog_is_append_only(tmp_path: Path) -> None:
    _, _, _, _, link, _ = _linked_artifacts(tmp_path)
    catalog = LocalExtractionLinkCatalog(tmp_path / "links")

    assert catalog.register(link) is True
    assert catalog.register(link) is False


def test_aligned_profile_extracts_and_normalizes_borderless_statement(
    tmp_path: Path,
) -> None:
    raw_root = tmp_path / "raw"
    source_manifest = _intake(
        raw_root,
        input_path=Path("tests/fixtures/documents/fictional_annual_report.pdf"),
        document_id="fictionalco-fy26-aligned-source",
        document_type=DocumentType.ANNUAL_REPORT,
    )
    extractor = AlignedPdfStatementExtractor()
    extraction_result = extractor.extract(source_manifest, raw_root, _aligned_spec())
    golden = _aligned_benchmark_fixture()
    benchmark = benchmark_extraction(
        extraction_result,
        golden.expected_rows,
        benchmark_version=golden.benchmark_version,
        required_match_rate=golden.required_match_rate,
    )
    csv_path = tmp_path / "fictionalco-fy26-aligned.csv"
    csv_path.write_text(
        extractor.to_controlled_csv(extraction_result, company_id="fictionalco"),
        encoding="utf-8",
    )
    extraction_manifest = _intake(
        raw_root,
        input_path=csv_path,
        document_id="fictionalco-fy26-aligned-extraction",
        document_type=DocumentType.CONTROLLED_EXTRACTION,
    )
    link = ExtractionLinker(raw_root).link(
        source_manifest=source_manifest,
        extraction_manifest=extraction_manifest,
        extraction_result=extraction_result,
        benchmark=benchmark,
        extracted_at=_NOW,
        review_status=ExtractionReviewStatus.REVIEWED,
        reviewed_by="Synthetic fixture reviewer",
        reviewed_at=_NOW,
    )
    mapping_path = Path("tests/fixtures/mappings/fictional_annual_report.json")
    mapping = MetricMappingSet.model_validate_json(mapping_path.read_text(encoding="utf-8"))
    batch = ControlledCsvFinancialParser().parse_linked(
        source_manifest=source_manifest,
        extraction_manifest=extraction_manifest,
        extraction_link=link,
        raw_root=raw_root,
        mapping_set=mapping,
    )

    assert extraction_result.ready_for_review is True
    assert [row.raw_value for row in extraction_result.rows] == ["1200", "220", "55", "165"]
    assert benchmark.passed is True
    assert batch.ready_for_analysis is True
    assert [str(fact.observation.value) for fact in batch.facts] == [
        "1200",
        "220",
        "55",
        "165",
    ]
