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
