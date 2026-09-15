# Open decisions

**Status:** Open unless an accepted decision and rationale are recorded here or in an architecture decision record.

| Decision | Current provisional default | What must be resolved |
|---|---|---|
| Primary user persona | Retail investor or research analyst | Highest-value job, required depth, compliance boundary, and willingness to pay |
| Initial pilot company | Infosys suggested | Confirm final company after a manual evidence teardown |
| Peer-selection rules | TCS, HCLTech, Wipro, Tech Mahindra suggested | Candidate filters, similarity weights, exclusions, expert override, and evaluation set |
| Product mode | Investor Mode | Whether and when Management/CFO or credit modes enter scope |
| Valuation inclusion | Deferred | Always included, optional, or excluded until legal and methodological review |
| Model/provider | None | Hosted/local model, privacy, cost, evaluation, and failure handling |
| Orchestration framework | Framework-neutral protocols | Evidence required before adopting an orchestration framework |
| Interface sequence | Local CLI first for the POC | Whether API or web UI follows and what user workflow it supports |
| Data storage | Versioned local files | When DuckDB, object storage, or another catalog becomes necessary |
| Document parsing | Manual/synthetic inputs first | PDF/XBRL toolchain, table accuracy, OCR, validation, and licensing |
| Long-term licensed provider | None | Coverage, lineage, point-in-time history, rights, reliability, and cost per deck |
| Deck visual identity | None | House style, user branding, accessibility, and chart conventions |
| Product success metrics | Not selected | Extraction accuracy, analyst time saved, trust, forecast performance, conversion, or a weighted set |
| Initial sector pair | IT services first; cement suggested later | Confirm after data-feasibility tests; financial institutions remain separate |
| Historical depth | Five annual periods and eight quarters suggested | Availability, restatements, and minimum usable history |
| Report visibility/retention | Local and private | Public/private access, evidence retention, deletion, and correction obligations |

## Decision process

Material choices require evidence, alternatives, trade-offs, an owner, and a review date. Architectural choices that change system boundaries or dependencies should also receive a record in `docs/architecture/DECISIONS.md`.
