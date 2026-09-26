"""Deterministic accuracy benchmark for extracted table rows."""

from __future__ import annotations

from decimal import Decimal

from indian_company_analysis.data.extraction.models import (
    ExpectedExtractionRow,
    ExtractionBenchmarkResult,
    PdfTableExtractionResult,
)


def benchmark_extraction(
    result: PdfTableExtractionResult,
    expected_rows: tuple[ExpectedExtractionRow, ...],
    *,
    benchmark_version: str,
    required_match_rate: Decimal = Decimal("1"),
) -> ExtractionBenchmarkResult:
    """Compare exact reported labels and values at stable row positions."""

    if not expected_rows:
        raise ValueError("at least one expected benchmark row is required")
    expected = {item.row_number: (item.reported_label, item.raw_value) for item in expected_rows}
    if len(expected) != len(expected_rows):
        raise ValueError("benchmark contains duplicate expected row numbers")
    actual = {item.row_number: (item.reported_label, item.raw_value) for item in result.rows}
    if len(actual) != len(result.rows):
        raise ValueError("extraction contains duplicate row numbers")

    mismatches: list[str] = []
    matched = 0
    for row_number, expected_value in expected.items():
        actual_value = actual.get(row_number)
        if actual_value == expected_value:
            matched += 1
        else:
            mismatches.append(
                f"row {row_number}: expected {expected_value!r}, actual {actual_value!r}"
            )
    for row_number in sorted(actual.keys() - expected.keys()):
        mismatches.append(f"row {row_number}: unexpected extracted row {actual[row_number]!r}")

    comparison_count = max(len(expected), len(actual))
    exact_match_rate = (Decimal(matched) / Decimal(comparison_count)).quantize(Decimal("0.000001"))
    return ExtractionBenchmarkResult(
        extraction_id=result.extraction_id,
        benchmark_version=benchmark_version,
        expected_row_count=len(expected),
        actual_row_count=len(actual),
        matched_row_count=matched,
        exact_match_rate=exact_match_rate,
        required_match_rate=required_match_rate,
        mismatches=tuple(mismatches),
        passed=exact_match_rate >= required_match_rate,
    )
