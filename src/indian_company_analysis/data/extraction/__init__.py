"""Verified PDF extraction, benchmarking, and source-to-artifact linkage."""

from indian_company_analysis.data.extraction.aligned_pdf import AlignedPdfStatementExtractor
from indian_company_analysis.data.extraction.benchmark import benchmark_extraction
from indian_company_analysis.data.extraction.linking import (
    ExtractionLinker,
    verify_extraction_link,
)
from indian_company_analysis.data.extraction.models import (
    AlignedPdfTableExtractionSpec,
    DocumentExtractionLink,
    ExpectedExtractionRow,
    ExtractedTableRow,
    ExtractionBenchmarkFixture,
    ExtractionBenchmarkResult,
    PdfTableExtractionResult,
    PdfTableExtractionSpec,
)
from indian_company_analysis.data.extraction.pdf_table import RuledPdfTableExtractor

__all__ = [
    "AlignedPdfStatementExtractor",
    "AlignedPdfTableExtractionSpec",
    "DocumentExtractionLink",
    "ExpectedExtractionRow",
    "ExtractionBenchmarkFixture",
    "ExtractionBenchmarkResult",
    "ExtractionLinker",
    "ExtractedTableRow",
    "PdfTableExtractionResult",
    "PdfTableExtractionSpec",
    "RuledPdfTableExtractor",
    "benchmark_extraction",
    "verify_extraction_link",
]
