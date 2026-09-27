"""Generate the deterministic synthetic PDF used by Phase 2C extraction tests."""

from __future__ import annotations

import argparse
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


def generate(output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    document = canvas.Canvas(
        str(output),
        pagesize=A4,
        invariant=1,
        pageCompression=0,
    )
    page_width, page_height = A4
    document.setTitle("Fictional Co Limited - Synthetic Annual Report")
    document.setAuthor("Indian Company Analysis POC")

    document.setFont("Helvetica-Bold", 18)
    document.drawString(72, page_height - 80, "Fictional Co Limited")
    document.setFont("Helvetica", 12)
    document.drawString(72, page_height - 104, "Synthetic Annual Report 2024-25")
    document.drawString(72, page_height - 126, "Statement of Profit and Loss")
    document.setFont("Helvetica-Oblique", 9)
    document.drawRightString(page_width - 72, page_height - 144, "INR million")

    table_left = 72
    table_top = page_height - 170
    table_width = page_width - 144
    label_width = 320
    row_height = 32
    rows = (
        ("Particulars", "FY2025"),
        ("Revenue from operations", "1000"),
        ("Profit before tax", "180"),
        ("Tax expense", "45"),
        ("Profit for the year", "135"),
    )

    document.setLineWidth(1)
    for index in range(len(rows) + 1):
        y = table_top - index * row_height
        document.line(table_left, y, table_left + table_width, y)
    for x in (table_left, table_left + label_width, table_left + table_width):
        document.line(x, table_top, x, table_top - len(rows) * row_height)

    for index, (label, value) in enumerate(rows):
        baseline = table_top - index * row_height - 21
        document.setFont("Helvetica-Bold" if index == 0 else "Helvetica", 10)
        document.drawString(table_left + 8, baseline, label)
        document.drawRightString(table_left + table_width - 8, baseline, value)

    document.setFont("Helvetica", 8)
    document.drawCentredString(
        page_width / 2,
        40,
        "Synthetic fixture only - not company evidence | Page 1",
    )
    document.showPage()

    document.setFont("Helvetica-Bold", 18)
    document.drawString(72, page_height - 80, "Consolidated Statement of Profit and Loss")
    document.setFont("Helvetica-Oblique", 9)
    document.drawRightString(page_width - 72, page_height - 112, "In INR million")
    document.setStrokeColorRGB(0.75, 0.2, 0.15)
    document.setLineWidth(1.2)
    document.line(72, page_height - 126, page_width - 72, page_height - 126)

    document.setFillColorRGB(0, 0, 0)
    document.setFont("Helvetica-Bold", 10)
    document.drawString(72, page_height - 146, "Particulars")
    document.drawString(350, page_height - 146, "Note")
    document.drawRightString(470, page_height - 146, "2026")
    document.drawRightString(535, page_height - 146, "2025")

    aligned_rows = (
        ("Revenue from operations", "2.18", "1200", "1000"),
        ("Profit before tax", "", "220", "180"),
        ("Tax expense", "2.17", "55", "45"),
        ("Profit for the year", "", "165", "135"),
    )
    first_baseline = page_height - 180
    aligned_row_height = 34
    document.setLineWidth(0.5)
    document.setStrokeColorRGB(0.6, 0.6, 0.6)
    for index, (label, note, current_value, prior_value) in enumerate(aligned_rows):
        baseline = first_baseline - index * aligned_row_height
        document.setFont("Helvetica", 10)
        document.drawString(72, baseline, label)
        if note:
            document.drawString(350, baseline, note)
        document.drawRightString(470, baseline, current_value)
        document.drawRightString(535, baseline, prior_value)
        document.line(72, baseline - 10, page_width - 72, baseline - 10)

    document.setFont("Helvetica", 8)
    document.drawCentredString(
        page_width / 2,
        40,
        "Synthetic aligned-table fixture only - not company evidence | Page 2",
    )
    document.showPage()
    document.save()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tests/fixtures/documents/fictional_annual_report.pdf"),
    )
    args = parser.parse_args()
    generate(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
