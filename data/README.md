# Local data layout

The POC is local-first. Data moves through these zones:

- `raw/`: immutable source evidence; never edit or commit source documents.
- `interim/`: reproducible parser or ingestion intermediates.
- `processed/`: normalized, calculated, or validated datasets traceable to raw evidence.
- `fixtures/demo/`: small, fictional datasets intentionally committed for tests and demos.

Only synthetic fixtures belong in Git. Real filings, vendor data, confidential information, and local databases must remain untracked. Every processed value must retain sufficient provenance to locate its inputs.
