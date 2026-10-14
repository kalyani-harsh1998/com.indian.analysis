# PDF extraction lineage and review

## Purpose

Phase 2C establishes a verifiable relationship between an original source PDF and a derived controlled CSV. The source and extraction remain separate immutable artifacts with separate SHA-256 checksums. A `DocumentExtractionLink` records how they are related, which pages were used, the extraction tool and version, the extraction profile, benchmark result, and human-review status.

This slice contains two deliberately narrow deterministic profiles: one for simple two-column tables with visible ruled borders and one for a configured period column in a borderless, visually aligned statement. It is not a general annual-report parser and does not use OCR, fuzzy matching, an LLM, or inferred accounting semantics.

## Evidence chain

```text
source PDF manifest + checksum
        |
        v
explicit page/table extraction profile and coordinates
        |
        v
pdfplumber ruled-table or aligned-word extraction
        |
        v
derived controlled CSV manifest + different checksum
        |
        v
golden-row accuracy benchmark + human review
        |
        v
checksum-bound extraction link
        |
        v
Phase 2B exact-label normalization
```

The normalized observation cites the original PDF source reference. Its adjacent extraction reference identifies the derived CSV and its checksum. Both artifacts are re-verified before linked normalization.

## Extraction specification

The extractor requires the user to state:

- extraction ID and profile version;
- one-based source page number;
- stable table ID;
- exact label and value-column headings;
- unit, period label, type, start date, and end date; and
- consolidated or standalone reporting basis.

`ruled-two-column-v1` accepts only a ruled table with exactly two columns. Missing tables, unexpected headers, extra cells, and empty labels or values are explicit extraction issues.

`aligned-single-period-v1` groups PDF words into visual rows and applies explicit label/value column boundaries for one reporting period. Each profile may also set a bounded `word_x_tolerance` to join tightly spaced fragments from the same visual cell, such as a bold total rendered by the PDF as separate text fragments. It preserves Indian comma grouping and parentheses in the raw value. The normalization layer converts those formats deterministically to `Decimal`; dashes and ambiguous values remain explicit issues. Coordinates and word-spacing tolerance are configuration evidence, not universal company templates.

A result from either profile with any extraction issue cannot be serialized as a review-ready controlled CSV.

## Targeted note-context extraction

`PdfNoteContextExtractor` is a separate, narrower Phase 2D producer for context that may help a
model interpret an already extracted statement row. It accepts only a verified source-PDF manifest,
the identity-matching onboarding request with an explicit target scope, and a versioned
`PdfNoteContextExtractionSpec`. Each configured snippet uses an exact page/table/row/column
locator plus an explicit PDF rectangle and text-size limit. The extractor re-verifies the raw PDF,
extracts the configured region with `pdfplumber`, removes layout control whitespace, and returns a
checksummed `LocatorBoundContextBundle` carrying profile-version/checksum and tool provenance.

This is not a general note parser: it does not search a PDF for headings, infer the relevant note,
perform OCR, decide the accounting classification, or call an LLM. The output is still untrusted
source context, not a fact or approval. A profile must be separately prepared and reviewed for the
applicable report layout; the model receives the small bundle, never the raw PDF.

## Planned guided profile workflow

The target is to reduce manual setup without allowing a model to create financial evidence. The
planned workflow is: (1) an LLM proposes likely pages using a bounded, checksum-linked local page
index; (2) a reviewer sees the proposed page in a visual tool and selects the relevant text/table
rectangle; (3) that tool saves the selected coordinates as a new versioned profile; (4) Python
re-extracts the region from the verified PDF and applies the ordinary identity, bounds, parsing,
and validation controls; and (5) a reviewer approves or rejects the profile before it can be used
for a production extraction. A future model may propose coordinates as an additional convenience,
but they remain a review suggestion, not an executable profile or approved source evidence.

### Implemented page-index foundation

`PdfPageDiscoveryInputBuilder` now implements the first offline step of that workflow. It verifies
the source PDF and onboarding-request identity, derives generic lexical terms from the explicit
target scope and supplied evidence labels, ranks pages by distinct-term coverage, and selects a
bounded excerpt around the densest local match. `prepare-onboarding-page-discovery-input` persists
the resulting checksummed candidate-page packet with policy and PDF-tool provenance. It calls no
provider and cannot create coordinates, a profile, or a fact. A later provider may only choose from
these listed pages, subject to deterministic validation and human review.

`PageDiscoveryProposal` is the next completed contract: it records one to five unique page
selections, rationale, confidence, and model-run provenance, all bound to the exact candidate-page
packet. `validate_page_discovery_proposal` rejects mismatched identity/checksums and any page not
present in that packet. The current static provider proves the contract without network access; a
future live adapter must satisfy the same restriction.

`OpenAIPageDiscoveryProposalProvider` is now the optional live adapter for that restricted role.
`propose-openai-page-discovery` accepts one stored `PageDiscoveryInput`, sends its bounded packet
in a separate untrusted user message, and asks for strict structured selections only from its page
numbers. It makes one non-retrying, non-stored request and persists only a review-only proposal
with local identity/model-run provenance. The provider receives no raw-PDF bytes or local path; a
candidate excerpt can contain printed source values, but it is not a deterministic extraction or an
approved fact. The adapter cannot create coordinates, a profile, normalized facts, or approval.
The proposal is independently validated before it is written, and a reviewer must still inspect it.

The v2 packet carries a checksummed request context: required reporting basis, full fiscal period,
target canonical metrics, purpose, and existing statement-row anchors. The model must produce one
primary page or abstain; it may name limited supporting pages only where they are needed. Python
rejects a changed context checksum and a declared basis/period mismatch. It does not infer the
actual accounting basis of arbitrary PDF pages from text alone, so an apparent standalone versus
consolidated distinction remains a reviewer check until a controlled profile exists.

One explicitly authorized APSEZ v2 technical proposal selected page 729, the consolidated FY2026
finance-cost note, as its only primary page. It created no profile, coordinates, extracted facts,
or approval, and remains review-only integration evidence.

A separate Infosys v2 technical proposal selected the consolidated FY2026 income-tax note on page
329 as primary and the anchored consolidated statement on page 287 as supporting evidence. It
flagged the primary choice for full-page review because the bounded excerpt did not contain the
complete tax-component table. This likewise created no profile, coordinates, facts, or approval.

## Accuracy benchmark

`benchmark_extraction` compares extracted label/value pairs at stable row numbers with a manually reviewed golden set. It records expected, actual, and matched row counts, an exact-match rate, required threshold, mismatches, benchmark version, and pass status.

The synthetic fixture requires a 100% exact match. That demonstrates deterministic test behavior only; it does not establish accuracy on real annual reports. Before using a real-company document profile, create a representative permitted benchmark corpus and have the golden values independently reviewed.

## Human-review gate

An extraction link can be `unreviewed`, `reviewed`, or `rejected`. Reviewed and rejected links require the reviewer identity and review timestamp. Linked normalization is ready for analysis only when:

1. both stored files still match their manifests;
2. the link IDs and checksums match both manifests;
3. the benchmark meets its required exact-match rate;
4. the review status is `reviewed`; and
5. every controlled CSV row passes Phase 2B normalization.

An unreviewed or failed extraction is retained for diagnosis but produces an explicit analysis blocker.

## Synthetic benchmark fixture

The committed synthetic PDF is generated by `scripts/generate_synthetic_pdf_fixture.py`. It is visibly labelled as synthetic and contains a ruled two-column table and a borderless four-column statement. Its purpose is to prove checksum lineage and deterministic extraction behavior; it is not evidence about a real company.

## Local real-document validation

The aligned profile was also exercised locally against the user-supplied Infosys Integrated Annual Report 2025-26, SHA-256 `602f04ec2abfacbf28ca8ff6e592db51942c620af4c12287d3a717edb6cd078f`. On PDF page 287, a configured FY2026 column produced 19 label/value candidates with no structural issues and matched a local manual golden set 19/19. Deterministic numeric parsing converted `1,78,650` to `178650` and `(1,246)` to `-1246`. The report, golden set, and derived local records remain ignored by Git, its licence category remains `unassessed`, and this one-document result is not a general accuracy claim. Semantic mappings and accounting aggregation still require review.

## Model-assisted onboarding foundation

Phase 2D now defines the provider-neutral request, proposal, deterministic-validation, and human-approval boundary for future LLM assistance. The current implementation accepts a review-ready extraction and may represent proposals for:

- the document and statement type, relevant pages, and likely extraction profile;
- table bounds, label/value columns, period headings, units, currency, and reporting basis;
- mappings from reported labels to canonical metrics;
- component-to-total aggregation rules, such as current tax plus deferred tax to tax expense; and
- confidence, rationale, and alternatives for ambiguous proposals.

No live LLM is used by the PDF extraction workflow itself. The static test provider proves that the same proposal can be replayed without network access. A separate optional OpenAI adapter is limited to CA-gated corpus evaluation, receives only the bounded prompt-isolated packet rather than a raw PDF, and cannot publish normalized facts. The validator checks source identity, labels, locators, evidence coverage, duplicate use, canonical targets, and explicit exclusions before human review. Deterministic code parses the reported values, enforces period/unit/basis compatibility, executes approved signed-sum aggregation rules, and supplies calculated observations to the existing accounting reconciliations. Direct and aggregated facts can now be persisted together; broader operators and automatic handoff into the complete company-analysis workflow remain deferred.

Every model-assisted proposal must retain the source-document checksum, input locators or evidence excerpts, provider and model identifier, model version, prompt/schema version, generation timestamp, proposed configuration, rationale, confidence, validation results, reviewer or policy decision, and the final approved profile/mapping version. Once approved, the saved configuration can be replayed without asking the model to reinterpret the same layout on every run.

## Deferred work

- PDF-to-CSV command-line workflow and review UI;
- bounded LLM-assisted page-discovery and guided visual profile-builder workflow;
- representative reviewed evaluation corpus for proposal accuracy, abstention, reconciliation, cost, and latency;
- automatic coordinate/profile discovery and multiple periods in one extraction run;
- prompt-injection isolation, evidence minimization, privacy policy, and provider selection;
- merged cells, wrapped labels, footnotes, and continuation pages;
- scanned-document detection and OCR;
- XBRL and native exchange-file adapters;
- real-report accuracy, precision, recall, and reconciliation benchmarks;
- extraction-link revision history and reviewer authorization; and
- automatic handoff from the combined normalized batch into the complete company-analysis workflow.
