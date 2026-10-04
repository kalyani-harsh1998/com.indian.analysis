# OpenAI onboarding technical evaluation results

## APSEZ prompt v3 — 4 October 2026

**Qualification:** provisional internal technical evaluation, not CA-approved model quality.
**Outcome:** API request, structured response, validation and report persistence completed;
the frozen evaluation acceptance criteria **failed**. No mapping was approved or normalized.

The owner authorized one APSEZ request after the offline v3 checks. The run used `gpt-6-astra`,
prompt `onboarding-model-input-v3`, schema `openai-onboarding-proposal-v2`, `store=False`, a
4,000-token output limit, and explicit `max_retries=0`. Only 21 extracted evidence rows, their
request context, and the 25-entry application metric catalog were sent. No raw PDF, source note
excerpts, local paths, fixture expected answers, or API key were embedded in the input packet.
The SDK used the local key for authentication; it was not logged or persisted in artifacts.

### Observed results

- Structural validation: passed, with no issues.
- Evidence coverage: 21/21 rows accounted for; zero invented, duplicated, or unaccounted evidence IDs.
- Decisions: five direct mappings, zero aggregations, ten exclusions, six abstentions.
- Canonical-value comparisons: five of six matched the provisional fixture. Finance cost was
  unresolved, not returned as zero or as an interest-only substitute.
- PBT less tax equals PAT reconciliation: passed with zero difference.
- Reported PBT/PAT rows were mapped directly; the v2 duplicate-use failure did not recur in this run.
- Usage: 4,742 input tokens, 1,562 output tokens, 24,520 ms measured provider latency.
  Monetary cost was not reported or estimated by the adapter.

### Why acceptance still failed

1. **Missing finance-cost context.** Interest/bank charges, derivative loss, and FX loss were
   abstained because the packet did not establish their complete financing scope. The existing
   provisional fixture expects their aggregation. The model's deferral does not prove that the
   fixture is wrong; the source note and metric definition need review.
2. **Different tax evidence route.** The model used the reported total tax expense. Its value
   matched, but the fixture expects current/deferred-tax aggregation. Exact-decision scoring
   therefore fails even though the value and PBT-to-PAT reconciliation agree.
3. **Unspecified requested scope.** Operating, employee-benefit, and other-expense rows were
   abstained for possible cost-of-revenue relevance. The fixture expects exclusions, but the model
   receives all 25 eligible metrics without a caller-selected target subset. This is evidence of
   a scope mismatch to investigate, not a reason to require more confident guesses.

All six abstentions carry rationale and source IDs. `ready_for_review: true` means structurally
valid, not approved: unresolved abstentions still block configuration approval.

### Comparison with previous local runs

| Contract | Structural validation | Duplicate evidence IDs | Expected values matched | Finance-cost outcome |
|---|---|---:|---:|---|
| v1 | Passed | 0 | 5/6 | Interest-only amount differed from fixture |
| v2 | Failed | 3 | 6/6 | Matched fixture, but PBT/PAT reconstruction reused evidence |
| v3 | Passed | 0 | 5/6 | Unresolved; explicit deferral for missing context |

All three failed their complete evaluation criteria. Each is one observation, not a statistical
benchmark or proof of general accuracy. Numerical agreement is not independent semantic approval.

### Local audit references

Corpus: `apsez-fy2026-consolidated-profit-loss-corpus-v1`, version `provisional-internal-v1`.
Fixture checksum: `7269bf20a1336d9354af2d29fc53823fd21d91f9d71d345dd7d9d784c6fd8c0b`.

Reports remain ignored under
`data/interim/evaluations/provisional-internal-corpus/apsez-fy2026-consolidated-profit-loss-corpus-v1/provisional-internal-v1/`:

- v1: `apsez-fy2026-consolidated-profit-loss-onboarding-v1-openai-7b15c2ad0f45.json`
- v2: `apsez-fy2026-consolidated-profit-loss-onboarding-v1-openai-11f00ffd3f3d.json`
- v3: `apsez-fy2026-consolidated-profit-loss-onboarding-v1-openai-840214126be6.json`

V3 report SHA-256: `8bf0037d707c5c02eef22491339e996b79c551e078957f4bb779a6e74ced02b3`.
Recorded generation time: `2026-10-04T06:15:40.275870Z`.
Input-payload SHA-256: `366b90b4123c71e3f579542d5763094b0edbc8edc7483bc29a839d1276a9b625`.
Developer-instruction SHA-256: `4dc619285703475c8f1a78def898f48b9d4695125ad718afa2caa28dd85458fd`.

After the call, the deterministic input was reconstructed, matched to the report's exact input
and instruction hashes, and preserved without another model call at
`data/interim/model-inputs/apsez-fy2026-consolidated-profit-loss-onboarding-v1-openai-input-v3-366b90b4123c.json`.
The packet file is pretty-printed; the input hash binds `provider_user_payload()`, not those file bytes.

### Next work

- Add explicit caller-selected target metrics to the input and output constraints without exposing
  golden answers to the model. Preserve exact target selection in provenance.
- Supply bounded, locator-backed note/statement context for unresolved finance-cost scope.
- Review equivalent tax evidence routes before introducing a new fixture or evaluation policy;
  do not overwrite existing expectations or lower thresholds to make this run pass.
- Keep repeated and cross-company live runs separately authorized and bounded. No additional
  live call or automatic retry was performed in this test.

Existing source evidence, corpus versions, thresholds, and review gates were not changed.
