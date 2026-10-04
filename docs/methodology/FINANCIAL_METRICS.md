# Financial metrics and accounting conventions

**Version:** 1.0.0  
**Scope:** Phase 1 non-financial company engine  
**Review status:** Engineering baseline; independent Chartered Accountant review is still required before use with real-company conclusions.

## 1. Purpose

This document defines the accounting contract used by deterministic calculations. It prevents formulas, signs, periods, reporting bases, restatements, and missing-data behavior from being chosen implicitly inside workflows or narrative prompts.

The engine is designed for ordinary non-financial companies. It is not appropriate for banks, NBFCs, insurers, or other financial institutions.

Phase 2D prompt contract v3 supplies these canonical definitions to the model through a versioned
onboarding catalog, with additional scope/uncertainty guidance. This does not change the formulas,
sign conventions, or review status below. A subtotal may be the full amount for its own target;
equivalent labels need not be exact aliases. Missing notes or competing profit/expense scopes
remain review questions, not permission to infer a value. See
[model-assisted onboarding](MODEL_ASSISTED_ONBOARDING.md#current-contract-v3).

## 2. Phase 1 boundaries

- Consolidated and standalone observations are stored separately and never combined.
- The synthetic golden dataset uses consolidated annual periods.
- Annual flows cover the stated start and end dates; balance-sheet values are period-end stocks.
- Monetary fixture values use `INR million`.
- Calculations may use only observations with the same company, reporting basis, compatible period type, and monetary unit.
- Quarterly, trailing-twelve-month, segment, normalized earnings, minority-interest, lease-adjusted, and per-share calculations are deferred.
- The engine calculates historical diagnostics, not forecasts, valuations, scores, or recommendations.

## 3. Source-of-truth hierarchy inside the engine

1. A current restated observation is used when it explicitly supersedes an older observation.
2. A superseded observation remains stored for audit and point-in-time reconstruction but is excluded from current calculations.
3. An analytical adjustment is stored separately from both reported observations. It never overwrites reported data.
4. Calculated values retain the IDs and source references of every reported input.

The Phase 1 fixture is entirely synthetic. Its company, statement values, restatement, and adjustment are fictional.

## 4. Sign conventions

| Item | Convention |
|---|---|
| Revenue and profits | Positive when income/profit is reported; losses may be negative |
| Depreciation and amortization | Positive expense |
| Finance cost | Positive expense |
| Tax expense | Positive expense; a tax credit may be negative |
| Operating cash flow | Statement sign: positive inflow, negative outflow |
| Capital expenditure | Positive cash outflow for the dedicated capex metric |
| Investing/financing cash flow | Statement sign: inflows positive, outflows negative |
| Debt, cash, receivables, inventory, payables, equity | Positive period-end balance unless the source legitimately reports otherwise |

Free cash flow therefore equals operating cash flow **minus** positive capital expenditure. Capital expenditure must not be supplied as a negative number to that formula.

## 5. Period and average-balance policy

- Growth compares consecutive annual observations on the same basis and unit.
- CAGR uses the number of annual end-date intervals, not the count of observations. Five annual observations therefore contain four compounding intervals.
- ROE, ROCE, and working-capital days use the simple average of opening and closing balance-sheet values.
- The first available annual period cannot produce an average-balance metric and returns `not_applicable`.
- Days ratios use the actual inclusive number of days in the current reporting period. Leap-year annual periods can therefore use 366 days.

## 6. Canonical formulas

Ratios are stored as decimal ratios: `0.25` means 25%.

| Metric | Formula | Important interpretation |
|---|---|---|
| Revenue growth | `current revenue / prior revenue - 1` | Not meaningful when prior revenue is zero |
| Revenue CAGR | `(ending revenue / beginning revenue)^(1 / years) - 1` | Requires positive beginning revenue and positive interval |
| EBITDA margin | `EBITDA / revenue` | Depends on a consistent EBITDA definition |
| EBIT margin | `EBIT / revenue` | EBIT is after depreciation and amortization |
| PAT margin | `profit after tax / revenue` | Uses unadjusted reported PAT in Phase 1 |
| CFO-to-PAT conversion | `operating cash flow / profit after tax` | Can be negative or volatile when PAT is small or negative |
| Free cash flow | `operating cash flow - capital expenditure` | Capex is a positive outflow |
| Free-cash-flow margin | `free cash flow / revenue` | Historical cash diagnostic, not distributable cash |
| Gross debt | `short-term debt + long-term debt` | Interest-bearing debt only in Phase 1 |
| Net debt | `gross debt - cash and equivalents` | A negative value means net cash |
| Debt to equity | `gross debt / total equity` | Not meaningful when equity is zero; negative equity needs separate interpretation |
| Interest coverage | `EBIT / finance cost` | Zero finance cost returns `zero_denominator`, not infinity |
| ROE | `PAT / average total equity` | Uses total equity and unadjusted PAT |
| Capital employed | `total equity + short-term debt + long-term debt - cash and equivalents` | Explicit POC convention; sector/company adjustments may be required later |
| ROCE | `EBIT / average capital employed` | Uses the capital-employed definition above |
| Receivable days | `average trade receivables / revenue × period days` | Revenue is a proxy for credit sales because credit-sales disclosure is usually unavailable |
| Inventory days | `average inventory / cost of revenue × period days` | Often immaterial for IT services; interpret only where inventory is operationally meaningful |
| Payable days | `average trade payables / cost of revenue × period days` | Validity depends on consistency between payable scope and cost-of-revenue scope |
| Cash-conversion cycle | `receivable days + inventory days - payable days` | Cross-company comparison requires comparable definitions |

## 7. Reconciliation rules

The engine runs four checks for each annual period:

1. `EBITDA - depreciation and amortization = EBIT`
2. `profit before tax - tax expense = profit after tax`
3. `total assets = total liabilities and equity`
4. `opening cash + CFO + investing cash flow + financing cash flow = closing cash`

The absolute monetary tolerance is `0.01` in the observation unit. A failed reconciliation does not mutate or discard a reported value; it produces a failed result with the difference and source lineage.

These checks are deliberately limited. A production accounting engine must also reconcile full statement subtotals, equity movements, non-cash items, foreign-exchange effects, acquisitions, disposals, and classification changes.

## 8. Calculation-result statuses

| Status | Meaning |
|---|---|
| `success` | Formula completed and produced a value |
| `missing_input` | At least one required observation is absent |
| `zero_denominator` | The formula denominator is zero |
| `incomparable_inputs` | Company, basis, unit, or period type is inconsistent |
| `not_applicable` | The formula is structurally or economically inappropriate for the supplied context |

Unavailable results are not silently omitted or converted to zero.

## 9. Precision and presentation

- Arithmetic uses Python `Decimal`, not binary floating point.
- Monetary and day outputs are quantized to two decimal places.
- Ratios are quantized to six decimal places.
- Quantization is an output convention, not evidence that the underlying source is that precise.
- Presentation layers may show fewer decimals but must not change stored results.

## 10. Restatements and adjustments

A restated observation must:

- have a positive revision number;
- identify the observation it supersedes;
- retain its own source reference;
- leave the superseded observation immutable.

An adjustment record must identify its original observation, adjustment amount, adjusted value, rationale, and evidence. The model verifies:

```text
original value + adjustment amount = adjusted value
```

Phase 1 stores adjustment records but continues to calculate reported metrics from current reported/restated observations. Normalized metrics using adjustments require a separately reviewed policy.

## 11. Aggregated reported components

When a filing presents one canonical concept as multiple reported rows, an approved versioned rule may combine those components deterministically. The initial rule supports only signed sums with coefficients of `1` or `-1`. For example:

```text
tax expense = current tax + deferred tax
```

Each component retains its source locator, raw value, parsed value, coefficient, and contribution. The aggregate is classified as `calculated`, even though all components are reported, and retains the source checksum/reference plus proposal, rule, configuration, and reviewer lineage. Company, document, unit, period, and reporting basis must match the approved configuration. Aggregation does not replace statement reconciliation; applicable equations must still pass before analytical reliance.

## 12. Review checklist before real-company use

- Confirm metric mappings against the company's notes and accounting policies.
- Confirm consolidated versus standalone basis.
- Confirm units, currency, fiscal dates, and revised filing status.
- Review every component and sign in an aggregation rule and confirm it is neither omitted nor reused.
- Reconcile statements and investigate differences above tolerance.
- Check whether finance cost includes lease interest or other items.
- Check whether cash should exclude restricted balances and include liquid investments.
- Review capital-employed and capex definitions for the business model.
- Validate receivable, inventory, payable, and cost-of-revenue scope.
- Separate exceptional items through evidence-backed adjustment records.
- Obtain independent CA review of formulas, mappings, and golden expected values.
