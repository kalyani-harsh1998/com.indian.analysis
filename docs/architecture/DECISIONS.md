# Architecture decision log

## ADR-001 — Phase 1 financial-analysis accounting contract

**Status:** Accepted for the synthetic POC  
**Date:** 18 September 2026

### Context

The Phase 0 workflow returned successful ratios or an unexplained absence. Phase 1 needs auditable non-financial calculations that retain revisions, distinguish unavailable results, and prevent accidental mixing of accounting contexts.

### Decision

- Use canonical `MetricId` values and a versioned metric-definition registry.
- Keep reported observations immutable and exclude only records explicitly marked `superseded` from current calculations.
- Store restatements and analytical adjustments as different concepts.
- Return a `CalculationResult` for unavailable as well as successful metrics.
- Reconcile EBITDA/EBIT, PAT, balance-sheet totals, and cash roll-forward before downstream interpretation.
- Use consolidated annual synthetic statements for the golden Phase 1 dataset.
- Use `Decimal`, six decimal places for ratios, and two for money/days.
- Define Phase 1 ROCE as EBIT divided by average equity plus interest-bearing debt less cash.
- Keep the engine dependency-free beyond Pydantic and the standard library.

### Consequences

- Outputs are more verbose but explain missing, invalid, and incomparable calculations.
- Superseded values remain available for audit and future point-in-time analysis.
- The ROCE and working-capital conventions are explicit rather than falsely universal.
- Real filing ingestion, metric-label mapping, normalized earnings, and sector overrides remain future work.
- Independent CA validation is required before real-company conclusions or public release.

## ADR-002 — Phase 2A local immutable document intake

**Status:** Accepted for the POC
**Date:** 26 September 2026

### Context

The next vertical slice needs real-document lineage without creating an unreviewed downloader, scraper, or parsing pipeline. Raw evidence must remain available for later verification and must not be silently replaced.

### Decision

- Accept only a file that a user has already supplied locally through a permitted route.
- Copy, never move or edit, that file into `data/raw/` using its SHA-256 checksum as the storage key.
- Store a strict JSON manifest separately in ignored local storage, carrying source metadata, licence classification, content details, and the checksum.
- Reuse byte-identical content without overwriting it; reject a different manifest for an existing document ID.
- Make the stored raw copy read-only and provide independent byte-size and checksum verification.

### Consequences

- The POC gains auditable document identity and version preservation without external data access.
- A checksum validates stored-byte identity, not source authority, accounting accuracy, completeness, or legal rights.
- Users still must assess terms and manually acquire permitted documents.
- Parsing, table/page lineage, normalized facts, revisions, and conflict resolution are later Phase 2 slices.
