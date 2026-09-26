# Local document intake

## Purpose

Phase 2A accepts a document that a user has already downloaded through a permitted route. It does not fetch websites, scrape exchanges, parse financial statements, or claim that a document is reliable merely because it was stored.

The intake command copies the input file into `data/raw/` under its SHA-256 checksum, makes that stored copy read-only, and writes a JSON manifest in `data/interim/manifests/`. Both locations are ignored by Git. The source file is copied, never moved or modified.

## Before intake

1. Confirm that the source is permitted for the intended storage and use.
2. Record the publisher, document title, original locator, publication date when available, and licence classification.
3. Download the document manually to a local location outside this repository where practical.
4. Do not use this process for credentials, confidential documents, or material that must not be retained locally.

`unassessed` is the safe default licence classification. It means rights have not yet been confirmed; it does not grant permission to redistribute or automate processing.

## Command

Run this from the repository root, substituting real metadata only after rights are checked:

```bash
uv run python -m indian_company_analysis intake \
  --file /path/to/downloaded-report.pdf \
  --document-id exampleco-fy25-annual-report \
  --company-id exampleco \
  --document-type annual_report \
  --source-kind annual_report \
  --source-organization "Example Co Limited" \
  --source-document "Annual Report 2024-25" \
  --source-locator "https://example.com/investors/annual-report-2025.pdf" \
  --publication-date 2025-05-20 \
  --licence-category unassessed
```

For a test-only input, use `--source-kind synthetic --synthetic`; synthetic input remains explicitly labelled throughout its manifest.

## What is recorded

Each manifest contains the document and company identifiers, document type, original filename, byte size, content type, SHA-256 checksum, content-addressed local path, retrieval time, source metadata, parser version (when parsing later exists), synthetic flag, and licence category. A repeated intake of identical bytes reuses the existing raw copy. A duplicate document ID with different manifest metadata is rejected rather than overwritten.

## Verification

The next slice will consume manifests for controlled parsing and normalized facts. Before that happens, it must run `verify_raw_document` to confirm the stored file exists and its bytes still match the recorded checksum. A valid checksum establishes byte identity only; it does not establish completeness, accounting accuracy, legal rights, or analytical suitability.
