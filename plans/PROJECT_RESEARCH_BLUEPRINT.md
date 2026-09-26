# Indian Company Analysis Agent — Research Blueprint

**Status:** Initial brainstorming document  
**Last updated:** 23 August 2026  
**Current phase:** Pre-research and product discovery; no final product or model decisions yet

## 1. Working idea

Build a chat-based agent or web application where a user enters the name of an Indian listed company and receives a source-backed, sector-aware analysis of:

- the company's business and present financial condition;
- suitable listed peers and an explanation of why they are comparable;
- financial, operating, governance, and valuation comparisons;
- strengths, weaknesses, risks, and potential areas for improvement;
- historical trends and the reasons behind them;
- forward scenarios or forecasts produced by an explainable algorithm; and
- the evidence, assumptions, dates, and confidence level behind every important conclusion.

The long-term opportunity is not simply another stock screener. The product can become a **financial research copilot** that connects company filings, accounting analysis, sector economics, competitive strategy, and forecasting in one auditable workflow.

## 2. Recommended product principles

1. **Evidence before opinion:** Every material fact and conclusion should link to its source and carry an `as_of_date`.
2. **Numbers should be deterministic:** Code should calculate financial metrics. A language model may explain the result but should not invent or manually calculate core figures.
3. **Sector-aware analysis:** Banks, insurers, IT services, cement companies, retailers, and manufacturers cannot be judged using one common template.
4. **Consolidated and standalone accounts must not be mixed:** The system should state which basis it uses and why.
5. **Fact, calculation, inference, and forecast must be visibly separated.**
6. **Forecasts should be ranges, not false precision:** Use base, bull, and bear cases with explicit drivers.
7. **Peer selection must be explainable:** “Same exchange industry” is insufficient.
8. **Current condition and investment attractiveness are different questions:** A good company can be expensive; a weak company can look statistically cheap.
9. **Uncertainty is a feature:** Missing, stale, conflicting, or low-quality data should lower the confidence score rather than be silently filled.
10. **Point-in-time integrity:** Backtests and historical recommendations must use only information that was available on the relevant date.

## 3. Who might use it?

Potential users include:

- retail investors seeking structured research;
- research analysts who want a faster first draft;
- wealth managers or advisers preparing company comparisons;
- founders and strategy teams benchmarking against listed competitors;
- lenders, vendors, and job seekers assessing company quality; and
- students learning how financial statements connect to business performance.

### Product decision still required

The first target user matters. A retail investing product, an analyst workbench, and a corporate-strategy tool require different depth, workflows, compliance, data licences, and user interfaces.

## 4. Candidate user journeys

### A. Company snapshot

“Analyse Infosys.”

Return the business profile, recent performance, key changes, financial quality, risks, valuation context, selected peers, and questions requiring deeper investigation.

### B. Peer comparison

“Compare Infosys with TCS, HCLTech, Wipro, and Tech Mahindra.”

Return standardized operating and valuation metrics, trend charts, explanations of material differences, and a peer-selection rationale.

### C. Diagnostic analysis

“Why has this company's ROCE declined?”

Decompose the change into margin, asset turnover, acquisitions, working capital, capacity utilization, financing, and accounting effects.

### D. Strategic improvement

“What could management improve?”

Produce recommendations derived from evidence—for example pricing, product mix, working-capital discipline, asset utilization, debt structure, distribution, capital allocation, or governance—not generic advice.

### E. Scenario and forecast

“What could the next three years look like?”

Return driver-based base, bull, and bear cases, the assumptions that distinguish them, forecast ranges, and the indicators a user should monitor.

### F. Filing-change monitor (later phase)

Explain what changed after a new result, annual report, rating action, acquisition, resignation, shareholding filing, or regulatory announcement.

## 5. Proposed end-to-end research process

### Step 1 — Resolve the company correctly

Map the user's text to a canonical entity containing:

- legal company name;
- NSE symbol and/or BSE scrip code;
- ISIN and CIN where available;
- listing status and exchange;
- industry and sub-industry;
- subsidiaries, material associates, and past names; and
- consolidated versus standalone reporting availability.

This prevents mistakes involving similarly named companies, renamed companies, multiple securities, and parent/subsidiary confusion.

### Step 2 — Gather primary evidence

Collect, timestamp, hash, and preserve the original documents:

- annual reports and audited financial statements;
- quarterly and annual results, preferably structured XBRL where usable;
- notes to accounts and accounting policies;
- exchange announcements and corporate actions;
- investor presentations and earnings-call material;
- shareholding patterns and promoter pledges;
- corporate-governance and BRSR filings;
- credit-rating rationales and debt disclosures;
- offer documents, schemes of arrangement, and material acquisition filings; and
- sector, regulator, and macroeconomic data.

### Step 3 — Normalize the financial history

Create a comparable time series while retaining reported values. The normalization layer must deal with:

- units, currencies, fiscal periods, and quarter/year boundaries;
- revised or restated results;
- Ind AS transitions and changes in accounting policies;
- standalone versus consolidated statements;
- exceptional items and discontinued operations;
- acquisitions, demergers, and changes in segment reporting;
- financial-company versus non-financial-company statement structures; and
- taxonomy changes and inconsistent company labels.

Never overwrite the raw reported figure. Store the reported value, normalized value, adjustment, reason, source, and effective date separately.

### Step 4 — Identify the business archetype and sector template

Before calculating a score, classify the company using both its industry and its economic model, such as:

- asset-light services;
- consumer brand/distribution;
- commodity producer;
- capital-intensive manufacturer;
- project/EPC business;
- regulated utility;
- platform or marketplace;
- bank, NBFC, insurer, or other financial institution; or
- diversified conglomerate requiring sum-of-the-parts analysis.

### Step 5 — Select peers

Use a two-stage process:

1. Generate candidates using industry classification, product descriptions, segments, revenue mix, geography, and business model.
2. Rank and review them using operating similarity, size, customer type, capital intensity, growth stage, margin structure, and data availability.

Possible peer groups:

- **operating peers:** most similar businesses;
- **valuation peers:** businesses priced by the market on similar drivers;
- **aspirational peers:** stronger companies that reveal improvement opportunities; and
- **historical self-comparison:** often more informative than a weak external peer set.

The result should explain why every company was included or excluded. The user should also be able to override the peer set.

### Step 6 — Perform accounting and financial analysis

Use the general and sector-specific frameworks in Sections 6 and 7.

### Step 7 — Perform strategic analysis

Connect financial outcomes to industry structure, competitive advantage, management choices, and external conditions.

### Step 8 — Generate scenarios and forecasts

Forecast operating drivers first, financial statements second, and valuation last. Retain the model version and every input used.

### Step 9 — Validate and compose the answer

Before presenting an answer:

- reconcile derived totals to source statements;
- flag conflicting filings and restatements;
- ensure peer periods and definitions are comparable;
- attach citations to material claims;
- label facts, calculations, inferences, and forecasts;
- state missing information and limitations; and
- run consistency checks across the narrative, tables, and charts.

## 6. General analytical framework

### A. Growth and operating performance

- revenue and volume growth over 1, 3, 5, and 10 years where meaningful;
- organic versus acquired growth;
- price, volume, mix, currency, and capacity contributions;
- segment and geographic growth;
- order book, bookings, same-store sales, utilization, churn, or other business KPIs;
- cyclicality and sensitivity to macro variables; and
- market-share movement where reliable data exists.

### B. Profitability

- gross, EBITDA, EBIT, PBT, and PAT margins;
- contribution margin or unit economics where available;
- incremental margin and operating leverage;
- segment margins;
- peer margin gap and its causes; and
- normalized earnings after removing clearly identified non-recurring effects.

### C. Returns and capital efficiency

- ROIC, ROCE, ROE, and return on tangible capital;
- asset turnover and fixed-asset turnover;
- DuPont decomposition;
- working-capital intensity;
- reinvestment rate and incremental return on invested capital; and
- value creation compared with the cost of capital.

### D. Cash flow and earnings quality

- cash flow from operations versus PAT and EBITDA;
- free cash flow and owner-earnings style measures;
- receivable, inventory, payable, and cash-conversion cycles;
- maintenance versus growth capital expenditure where estimable;
- capitalized costs and development expenditure;
- recurring versus non-recurring “other income”; and
- multi-year accrual indicators.

### E. Balance-sheet and solvency risk

- net debt, debt/equity, and lease liabilities;
- interest and fixed-charge coverage;
- debt maturity profile, security, currency, and rate exposure;
- contingent liabilities, guarantees, and commitments;
- liquidity, covenant, refinancing, and customer-concentration risk; and
- financial assets, treasury investments, and trapped cash.

### F. Shareholder outcomes and capital allocation

- retained earnings versus value created;
- capex outcomes and utilization;
- acquisitions, disposals, and impairment history;
- dividends, buybacks, debt reduction, and equity issuance;
- ESOP dilution and changes in share count; and
- minority interests and value leakage across group entities.

### G. Valuation

- P/E, EV/EBITDA, EV/EBIT, P/B, price/sales, and free-cash-flow yield as appropriate;
- historical-band and peer comparison;
- DCF with transparent operating drivers;
- reverse DCF to identify expectations embedded in the current price;
- sum-of-the-parts for diversified businesses; and
- scenario-based value ranges rather than one unexplained target price.

Valuation must use aligned dates. A current price must not be combined casually with stale trailing data or a forecast produced before a material event.

## 7. Chartered-accountant and forensic review layer

This should be a core differentiator, not an appendix. Review:

- auditor opinion, emphasis of matter, qualifications, and Key Audit Matters;
- auditor resignation or frequent auditor changes;
- revenue-recognition policies and changes;
- related-party transactions, loans, guarantees, and group-company balances;
- contingent liabilities and commitments relative to net worth;
- exceptional items that appear repeatedly;
- receivable growth versus revenue growth and ageing disclosures;
- inventory growth, write-downs, and obsolescence;
- capitalization of expenses, CWIP ageing, and delayed projects;
- goodwill, intangibles, and impairment assumptions;
- unexplained divergence between PAT and operating cash flow;
- unusual tax rates, deferred-tax assets, and uncertain tax positions;
- subsidiary/JV losses and non-controlling interests;
- promoter shareholding, pledges, dilution, and preferential allotments;
- debt covenants, defaults, rating changes, and refinancing dependencies;
- changes in useful lives, depreciation, estimates, or segment definitions;
- restatements, delayed filings, and regulatory observations; and
- board independence, key-manager turnover, and remuneration alignment.

The system should produce **risk flags**, not allegations. A flag is a question requiring investigation and must show the underlying evidence and materiality.

## 8. Sector-specific modules

A universal scoring model will fail. Each major sector needs its own metric dictionary, accounting rules, peer logic, and forecast drivers.

| Sector/archetype | Examples of important additional metrics |
|---|---|
| Banks | NIM, CASA, GNPA/NNPA, slippages, credit cost, provision coverage, capital adequacy, deposit and loan mix, liquidity, cost/income |
| NBFCs | AUM growth/mix, spreads, borrowing cost, ALM gaps, stage 2/3 assets, credit cost, capital adequacy, collection efficiency |
| Life insurance | APE, VNB, VNB margin, persistency, product/channel mix, solvency, embedded value |
| General insurance | Gross written premium, combined ratio, loss ratio, expense ratio, solvency, investment income |
| IT services | Constant-currency growth, deal wins, attrition, utilization, onsite/offshore mix, employee cost, client concentration |
| Consumer/FMCG | Volume growth, realization, gross margin, distribution reach, ad spend, rural/urban mix, working capital |
| Retail | Same-store growth, sales per square foot, store additions/closures, inventory turns, lease-adjusted returns |
| Cement/metals/commodities | Capacity, utilization, realization, unit cost, energy/input cost, logistics, capex cycle, net debt per unit |
| Auto/auto components | Volumes, market share, content per vehicle, product mix, dealer inventory, capacity utilization, warranty costs |
| Pharma | Geography and therapy mix, ANDA/pipeline, R&D intensity, plant observations, price erosion, product concentration |
| EPC/infrastructure | Order book quality, book-to-bill, execution, working capital, retention money, claims, mobilization advances |
| Telecom | ARPU, subscribers, churn, data usage, spectrum liabilities, capex intensity, net debt |
| Utilities | Regulated asset base, plant load factor, availability, receivable days, tariff orders, fuel adjustment, regulated ROE |

Financial institutions should probably be excluded from the first non-financial MVP and built as a separate analytical engine.

## 9. Strategy and competitive analysis

The strategy layer should answer:

- What customer problem does the company solve?
- Where does it sit in the industry value chain and profit pool?
- What drives customer choice and switching?
- Does it possess scale, brand, distribution, data, technology, licences, cost advantages, network effects, or scarce assets?
- How durable are those advantages, and what evidence supports them?
- How concentrated are customers, suppliers, products, and geographies?
- What substitutes or regulatory changes threaten the model?
- Is management gaining profitable share or purchasing unprofitable growth?
- Is capital allocation consistent with management's stated strategy?
- Which leading indicators would reveal improvement or deterioration early?

Useful frameworks include value-chain analysis, Five Forces, profit-pool mapping, unit economics, competitive-advantage durability, management execution scorecards, and scenario planning. Frameworks should organize evidence rather than replace it.

## 10. Turning analysis into improvement recommendations

Recommendations should be generated through a measurable **gap tree**:

1. Identify the outcome gap—for example ROCE is 600 bps below the relevant peer median.
2. Decompose it—operating margin, asset turnover, working capital, capacity utilization, or financing.
3. Find the business driver—pricing, mix, procurement, inventory, receivables, distribution, project execution, or capital allocation.
4. Check management control—distinguish controllable actions from commodity, macro, or regulatory effects.
5. Estimate potential impact and time horizon.
6. State evidence, dependencies, implementation risks, and confidence.

Example structure:

> Receivable days are materially above comparable peers and have risen for three years. If this reflects execution rather than business mix, tighter credit terms and collection discipline could release working capital. Confidence: medium; customer and segment ageing data should be checked before concluding.

## 11. Proposed scoring system

Do not begin with one opaque “company score.” First show separate dimensions:

- growth quality;
- profitability and operating efficiency;
- return on capital;
- cash conversion and earnings quality;
- balance-sheet resilience;
- governance and reporting quality;
- competitive position;
- capital allocation;
- valuation; and
- data quality/confidence.

Later, a 0–100 composite score can be introduced with:

- sector-specific weights;
- percentile ranks within a suitable peer universe;
- absolute safety thresholds;
- explicit handling of missing values;
- winsorization of extreme observations;
- a separate confidence score; and
- versioned definitions and weights.

Scores from different sectors should not be treated as directly comparable until the methodology has been validated.

## 12. Forecasting and prediction approach

### What to predict first

Start with variables that can be explained and tested:

- revenue or volume range;
- EBITDA/EBIT margin range;
- PAT and EPS range;
- operating cash flow and free cash flow;
- working-capital requirements;
- ROCE/ROE trajectory;
- leverage and liquidity; and
- scenario valuation range.

Direct short-term share-price prediction should not be the MVP. Prices incorporate expectations, liquidity, flows, risk appetite, and surprises that are much harder to model reliably. A better first product explains what operating outcome appears priced in and what would have to happen for upside or downside scenarios.

### Model-development stages

#### Version 0 — Rules and deterministic diagnostics

- standardized ratio calculations;
- trend, peer-percentile, and threshold flags;
- accounting-quality checks;
- driver trees; and
- transparent sector scorecards.

#### Version 1 — Driver-based financial forecast

- revenue = volume/customer/capacity driver × price/realization;
- margins linked to mix, utilization, input costs, and operating leverage;
- working capital linked to operating assumptions;
- capex, depreciation, interest, and taxes modeled explicitly; and
- integrated P&L, balance sheet, and cash-flow checks.

#### Version 2 — Statistical/ML assistance

- cross-sectional peer ranking;
- probability of margin expansion/contraction;
- financial-distress or earnings-quality risk;
- estimate ranges based on comparable historical states;
- anomaly detection in filings and financial time series; and
- extraction/classification of qualitative disclosures.

ML should augment the causal model, not hide it. For each forecast, retain top drivers, prediction interval, model version, training cutoff, and known limitations.

### Backtesting requirements

- point-in-time filings and prices;
- delisted, merged, and failed companies to avoid survivorship bias;
- filing publication dates rather than only fiscal period-end dates;
- restatement handling;
- walk-forward validation rather than random time-series splits;
- sector and market-regime evaluation;
- comparison with simple baselines;
- error metrics for both magnitude and direction; and
- calibration testing for probability statements and prediction intervals.

## 13. Initial data-source map

### Tier 1 — Primary and official sources

- [SEBI corporate-filings directory](https://www.sebi.gov.in/curation/corporate_filings.html): routes to exchange filings including results, governance, shareholding, and BRSR.
- [NSE financial-results filings](https://www.nseindia.com/companies-listing/corporate-filings-financial-results): company results and structured filing access.
- [NSE corporate announcements](https://www.nseindia.com/companies-listing/corporate-filings-announcements): material announcements and attachments.
- [NSE annual-report filings](https://www.nseindia.com/companies-listing/corporate-filings-annual-reports): annual reports submitted by listed companies.
- [NSE XBRL information](https://www.nseindia.com/static/companies-listing/xbrl-information): filing taxonomies and XBRL information.
- [BSE financial results](https://www.bseindia.com/corporates/Comp_Resultsnew.aspx): exchange-filed results and XBRL links.
- Company investor-relations websites: presentations, transcripts, policies, annual reports, and management commentary. Exchange copies should be preferred when versions conflict.
- MCA21: company master data and public documents, subject to access, payment, automation, and reuse terms.
- [RBI Database on Indian Economy](https://data.rbi.org.in/): macro, banking, financial-market, and corporate-sector series.
- Sector regulators and ministries, selected by industry—for example IRDAI, TRAI, CERC/CEA, PPAC, DGCA, PNGRB, NPPA, and ministries publishing industry statistics.
- [Competition Commission of India](https://www.cci.gov.in/combination): combination orders can contain useful market definitions, competitor context, and industry evidence.

### Tier 2 — Licensed structured data

Evaluate commercial feeds for normalized fundamentals, identifiers, prices, corporate actions, estimates, ownership, and transcripts. Candidate categories include exchange-licensed data and established Indian corporate databases. Selection should follow a formal proof of concept rather than assuming a retail website can be used as a production API.

NSE currently publishes separate [corporate-data subscription](https://www.nseindia.com/static/market-data/corporate-data-subscription), [usage-policy](https://www.nseindia.com/static/market-data/nse-data-policy), and [product-tariff](https://www.nseindia.com/static/market-data/products-tariff) pages. Commercial design must account for licensing, redistribution, non-display use, derived data, caching, and user display rights.

### Tier 3 — Secondary and alternative evidence

- credit-rating agencies;
- industry associations and trade publications;
- company customers, suppliers, and competitors;
- government tender and procurement portals;
- import/export and commodity data;
- patents, trademarks, hiring, app, web-traffic, store/location, and channel checks;
- reputable news and interview archives; and
- sell-side or specialist research where the licence permits use.

Secondary sources should supplement, not silently override, filed information.

### Data-source evaluation checklist

For every provider, test:

- legal right to ingest, store, transform, display, and redistribute;
- historical depth and point-in-time availability;
- coverage of delisted and renamed entities;
- consolidated/standalone and segment coverage;
- revision and restatement handling;
- identifiers and corporate-action history;
- accuracy, completeness, latency, and uptime;
- bulk export/API limits and production reliability;
- source lineage and auditability; and
- pricing at expected user and query volumes.

## 14. Suggested technical/research architecture

### A. Source layer

Immutable documents and structured feeds with source URL, publisher, retrieval timestamp, filing timestamp, reporting period, checksum, licence metadata, and parser version.

### B. Canonical company and security master

Entity IDs connected to names, symbols, ISINs, CINs, exchanges, securities, sectors, subsidiaries, and corporate actions.

### C. Normalized facts layer

Versioned financial facts containing statement type, metric, value, unit, period, consolidated/standalone flag, reported/adjusted flag, source location, and confidence.

### D. Metric and model layer

Deterministic calculations, sector templates, peer models, driver trees, forecasts, valuation models, and backtests.

### E. Evidence retrieval layer

Search/indexing for narrative documents with page/section references. Tables and numeric facts should come from structured stores when possible, not from semantic search alone.

### F. Agent/reasoning layer

Potential components:

- company/entity resolver;
- source retrieval and freshness checker;
- financial normalization service;
- accounting-quality reviewer;
- sector and strategy analyst;
- peer-selection engine;
- forecast and valuation engine;
- claim/evidence validator; and
- answer composer.

The first version does not need many autonomous agents. A controlled orchestrator calling deterministic data and calculation services will be easier to test, cheaper, and more reliable. Use language-model reasoning for document interpretation, comparison, questioning, and explanation; use code for identities, arithmetic, accounting relationships, scoring, and model execution.

## 15. Output structure for a company analysis

1. Company identity and analysis `as_of_date`
2. Executive assessment
3. Business model and segments
4. Recent developments
5. Historical financial dashboard
6. Cash flow and earnings quality
7. Balance-sheet and solvency review
8. Auditor, accounting, governance, and promoter flags
9. Peer set with selection rationale
10. Peer comparison and driver-based explanation
11. Industry and competitive position
12. Management strategy and capital allocation
13. Evidence-based improvement opportunities
14. Base, bull, and bear scenarios
15. Valuation context or reverse DCF
16. Key risks, catalysts, and thesis-breakers
17. Monitoring checklist
18. Sources, assumptions, missing data, and confidence

Every table should define its units, period, consolidated/standalone basis, formula, and source.

## 16. Compliance, legal, and trust requirements

This area must be researched before public launch. A system that publishes security-specific research, recommendations, model portfolios, target values, or return claims may enter regulated territory in India. Product wording alone is not a substitute for determining the actual activity being performed.

As of this document's date, the relevant starting points include:

- [SEBI Research Analysts Regulations, last amended 25 November 2025](https://www.sebi.gov.in/legal/regulations/nov-2025/securities-and-exchange-board-of-india-research-analysts-regulations-2014-last-amended-on-november-25-2025-_98248.html); and
- [SEBI Master Circular for Research Analysts dated 6 February 2026](https://www.sebi.gov.in/legal/master-circulars/feb-2026/master-circular-for-research-analysts_99571.html).

Before deciding features, obtain specialist legal/compliance advice on:

- whether the product or operator requires Research Analyst registration or other authorization;
- the boundary between education, impersonal research, a research report, a recommendation, and personalized investment advice;
- required disclosures, conflicts management, recordkeeping, certification, complaints, and audit obligations;
- AI accountability, client-data security, and model-output responsibility;
- advertising, performance claims, backtests, model portfolios, and public-media rules;
- exchange data licensing and redistribution;
- privacy, consent, retention, cybersecurity, and cross-border services; and
- how generated reports, chat history, model versions, and supporting evidence must be retained.

The product should include audit logs, conflict disclosures, source provenance, model-version records, user-visible limitations, correction mechanisms, and human escalation for high-risk outputs. A generic “not investment advice” disclaimer is not an adequate compliance strategy.

## 17. Recommended MVP

### Proposed scope

- 30–50 liquid Indian listed companies;
- two non-financial sectors with different economics—one asset-light and one capital-intensive;
- five annual periods and eight recent quarters, subject to source availability;
- consolidated financials as the default, with clearly separated standalone views;
- explainable peer selection with manual override;
- general and sector-specific financial analysis;
- accounting-quality and governance flags;
- deterministic peer scorecards;
- driver-based three-year scenarios;
- valuation context without short-term trading calls;
- citations and source timestamps for every material claim; and
- no personalized portfolio recommendation in the initial version.

### Possible pilot sectors

- **IT services:** relatively clear listed peers, asset-light economics, useful operating KPIs.
- **Cement:** capital intensity, capacity cycles, regional economics, commodity/input costs.

Together they will test whether the architecture genuinely supports different business models. Banks/NBFCs can follow as a separate model after the non-financial pipeline is reliable.

### What not to include initially

- all Indian listed companies;
- intraday signals;
- autonomous buy/sell execution;
- personalized portfolio advice;
- an unexplained universal score;
- precise short-term price targets; or
- data scraped from sources without confirmed production-use rights.

## 18. Pre-research workstreams

### Workstream 1 — Product and user discovery

- select the primary user and their highest-value decision;
- interview representative users;
- collect sample questions and ideal outputs;
- determine acceptable latency, depth, and price; and
- decide whether this is research, strategy benchmarking, education, or a regulated recommendation product.

### Workstream 2 — Data feasibility spike

- choose one IT company and one cement company;
- manually build a source inventory for each;
- extract five years of statements and important notes;
- measure completeness, revision frequency, parsing effort, and licensing constraints;
- compare free-primary-source and licensed-data workflows; and
- produce a data coverage and cost matrix.

### Workstream 3 — Accounting taxonomy

- define canonical statements and metric formulas;
- map common XBRL/company labels;
- define adjustments and restatement rules;
- create reconciliation tests; and
- obtain CA review of definitions and red-flag logic.

### Workstream 4 — Sector and peer methodology

- define business archetypes;
- create the first two sector metric dictionaries;
- design peer candidate generation and ranking;
- compare algorithmic peers with expert-selected peers; and
- document exceptions such as conglomerates and recent demergers.

### Workstream 5 — Forecast experiment

- build a simple driver model for selected pilot companies;
- reconstruct point-in-time forecasts historically;
- compare against naive baselines;
- measure error and interval calibration; and
- identify which drivers are unavailable or unreliable.

### Workstream 6 — Trust and compliance

- obtain legal classification of proposed features;
- map data-provider rights;
- define disclosures, logs, retention, and correction workflows;
- threat-model sensitive and licensed data; and
- define the human-review boundary.

## 19. Main decisions to discuss next

1. Who is the first user: retail investor, professional analyst, or corporate strategy team?
2. Is the first product descriptive research, forward research, or explicit investment recommendation?
3. What forecast horizon matters: next quarter, 1–3 years, or 5+ years?
4. Should valuation and market price be included in the MVP?
5. What is the initial company universe and sector pair?
6. Are we willing to pay for licensed structured data, or must the prototype use public filings only?
7. How current must the product be: real time, end of day, or after each filing?
8. Will outputs be public, behind login, or used only internally during validation?
9. What level of analyst/CA human review is available during development?
10. What constitutes success: extraction accuracy, analyst time saved, forecast accuracy, user trust, or paid conversion?

## 20. Suggested immediate next step

Run a **single-company research teardown** before choosing the UI or technology stack:

1. Select one pilot company.
2. List every source needed to answer the proposed output structure.
3. Manually create a high-quality benchmark report.
4. Mark which parts are deterministic, which require sector judgment, and which require forecasting.
5. Test peer selection and accounting normalization on three to five peers.
6. Convert the benchmark into a data schema, evaluation set, and product requirements.

This will reveal the real data and reasoning problems much faster than building a generic chat interface first.

## 21. Professional-lens operating model

“CA perspective” and “financial consultant perspective” are useful starting ideas, but both labels cover several different professions. The product should use a shared fact base and expose distinct analytical lenses.

| Lens | Primary question | Core output |
|---|---|---|
| Accounting/CA | Can the reported numbers be trusted and interpreted correctly? | Reporting basis, accounting quality, audit matters, cash conversion, tax, related parties, contingencies, controls and governance flags |
| CFO/FP&A | Why did performance change and what is likely to happen next? | Driver trees, variance analysis, profitability, budgets, forecasts, scenarios and management KPIs |
| Strategy consultant | Where should the company compete and how can it improve its position? | Industry structure, customer value, competitive advantage, portfolio choices, growth options and capability gaps |
| Operations/value-creation adviser | Which practical initiatives can improve revenue, margin, cash and ROIC? | Pricing, procurement, productivity, footprint, working-capital and execution initiatives |
| Corporate-finance adviser | How should capital be funded, deployed or returned? | Capex, M&A/divestment, debt/equity, portfolio optimization, dividends, buybacks and balance-sheet choices |
| Equity-research analyst | What does the evidence imply for an outside investor? | Thesis, expectations, catalysts, risks, forecasts, valuation and monitoring triggers |
| Credit/risk analyst | Can the company withstand adverse conditions and service obligations? | Liquidity, leverage, coverage, refinancing, covenant and downside analysis |

### Recommended product presentation

Do not ask separate agents to produce repetitive “CA” and “consultant” essays. Present one integrated analysis in five sections:

1. **Financial Truth:** reported basis, accounting reliability and red flags.
2. **Performance Diagnosis:** growth, margins, returns, cash and their root drivers.
3. **Strategic Position:** industry economics, competition, advantages and threats.
4. **Value-Creation Plan:** quantified improvement hypotheses and required actions.
5. **Investor/Credit Outlook:** scenarios, valuation, risks and monitoring indicators.

### Example: one issue through different lenses

If receivable days increase from 45 to 85 days:

| Lens | Questions and interpretation |
|---|---|
| Accounting/CA | Test revenue recognition, ageing, expected-credit-loss provisions, concentration and audit disclosures. |
| CFO/FP&A | Locate collection delays, invoice disputes, credit-policy gaps and the effect on cash forecasting. |
| Strategy | Determine whether weak bargaining power, customer mix or growth bought through generous credit is the cause. |
| Operations/value creation | Evaluate order-to-cash ownership, billing accuracy, collections and revised credit terms. |
| Credit | Measure the additional funding need, interest burden and liquidity downside. |
| Equity research | Reduce earnings-quality confidence if appropriate and test whether valuation reflects the cash-conversion risk. |

This multi-lens interpretation should be implemented as a linked issue tree, not six unrelated observations.

## 22. Reference library of publicly described consulting frameworks

The following is a synthesis of capabilities and frameworks that the firms describe publicly. It is a benchmark for product design—not a claim to reproduce their proprietary methods, benchmarks, client data, or advice.

### Deloitte — finance transformation and value creation

Deloitte publicly groups finance transformation around:

- business finance: performance management, planning, budgeting, forecasting, cost/profitability management, reporting and business partnering;
- finance strategy: capital management, IPO readiness, major events and turnarounds;
- operational finance: order-to-cash, procure-to-pay, fixed assets, close/consolidate/report and shared services;
- finance operating-model design;
- controllership and treasury;
- M&A finance; and
- value-creation work focused on cash generation, profitability and execution.

**Product translation:**

- historical-versus-plan analysis when internal budgets are available;
- revenue, margin and ROIC driver trees;
- product/customer/segment profitability diagnostics;
- cash-conversion and working-capital modules;
- finance-process and reporting-quality maturity checks;
- treasury, liquidity and balance-sheet diagnostics; and
- event modules for IPOs, acquisitions, separations and turnarounds.

Sources: [Deloitte India finance transformation](https://www.deloitte.com/in/en/services/financial-advisory/services/finance-transformation.html), [Deloitte India corporate finance advisory](https://www.deloitte.com/in/en/services/consulting/services/strategy-transactions/corporate-finance-advisory.html), and [Deloitte India value creation](https://www.deloitte.com/in/en/services/financial-advisory/services/value-creation-services.html).

### EY/EY-Parthenon — corporate finance and strategic alternatives

EY publicly describes a corporate-finance agenda covering:

- capital allocation and project prioritization;
- strategic alternatives;
- business portfolio optimization;
- forecasting and scenario planning;
- balance-sheet and working-capital optimization;
- board advice;
- M&A, divestments and capital markets; and
- valuation, modeling and economic analysis.

Its financial-accounting advisory capabilities also emphasize accounting, reporting, transaction accounting, treasury, corporate governance, transparency and finance data.

**Product translation:**

- segment-level capital-allocation and incremental-ROIC assessment;
- “invest, improve, harvest, divest or investigate” portfolio hypotheses;
- base, bull and bear operating scenarios;
- balance-sheet optimization and funding-risk analysis;
- acquisition/divestment history and post-deal outcome tracking;
- DCF, reverse DCF and sum-of-the-parts tools; and
- accounting/reporting confidence and governance modules.

Sources: [EY India corporate finance](https://www.ey.com/en_in/services/strategy-transactions/corporate-finance), [EY India strategy and transactions](https://www.ey.com/en_in/services/strategy-transactions), and [EY India financial accounting advisory](https://www.ey.com/en_in/services/financial-accounting-advisory-services).

### KPMG — finance transformation and target operating model

KPMG India publicly organizes its finance-transformation capabilities around:

- finance strategy and transformation;
- enterprise performance management;
- AI in finance;
- finance operations/platform transformation;
- profitability and cost management;
- performance improvement;
- driver-based planning, integrated planning and forecasting;
- finance-function benchmarking; and
- continuous risk, controls and anomaly monitoring.

Its described target operating model contains six interacting layers: **process, people, service-delivery model, technology, performance insights, and governance/controls**.

**Product translation:**

- driver-based rather than simple trend-extrapolation forecasts;
- profitability and cost-to-serve decomposition;
- peer benchmarking with sector and scale controls;
- a CFO-mode maturity assessment across the six operating-model layers;
- anomaly and continuous-control flags;
- scenario-based cash, liquidity and capital-allocation tools; and
- explicit separation of diagnostic insights from implementation capabilities.

Sources: [KPMG India finance transformation](https://kpmg.com/in/en/services/advisory/consulting/business-consulting/finance-transformation.html) and [KPMG India Finance of the Future](https://kpmg.com/in/en/services/advisory/consulting/business-consulting/finance-transformation/finance-of-the-future.html).

### PwC/Strategy& — finance effectiveness and value creation

PwC India publicly describes finance-effectiveness capabilities including:

- enterprise performance management;
- integrated planning and budgeting;
- management information and analytics;
- financial and business analysis;
- costing design;
- finance-process assessment and benchmarking;
- policies, controls, close and reporting optimization;
- working-capital and cash forecasting;
- accounts-receivable and accounts-payable process engineering;
- agile finance operating models and digital enablement; and
- shared services, IPO readiness and post-merger integration.

PwC's value-creation work also frames situations around low profitability, slow growth, high costs, low ROIC, an excessive asset base, low valuation, deals and enterprise-wide transformation.

**Product translation:**

- a value-driver decomposition starting with growth, margin, invested capital and valuation perception;
- finance-effectiveness and reporting-process diagnostics in management mode;
- integrated business planning and cash-forecast modules;
- deal, IPO and post-merger event templates; and
- explicit differentiation between operational underperformance and investor-perception gaps.

Sources: [PwC India finance effectiveness](https://www.pwc.in/consulting/management-consulting/finance-effectiveness.html), [PwC India finance transformation](https://www.pwc.in/consulting/transformation-consulting/finance-transformation.html), and [PwC India value creation](https://www.pwc.in/services/deals/value-creation.html).

### McKinsey — CFO excellence, strategy and enterprise value

McKinsey publicly describes eight CFO/value levers:

1. define and focus the agenda;
2. allocate capital with conviction;
3. steer performance in real time;
4. reshape the operating model;
5. rebuild finance with AI;
6. strengthen the investor narrative;
7. navigate complexity and risk; and
8. unlock value beyond the core through M&A, partnerships and portfolio actions.

Its strategy work also emphasizes economic-profit performance, industry position, company endowment, major strategic moves, and data-based assessment of the odds of a strategy.

**Product translation:**

- an executive agenda containing only the few material issues;
- economic-profit, ROIC and capital-allocation analysis;
- leading indicators and performance steering rather than backward-looking ratios alone;
- strategy-versus-results tracking using management's earlier commitments;
- an investor-narrative consistency checker;
- portfolio/M&A and “beyond the core” analysis; and
- a probability-and-evidence approach to strategic forecasts.

Sources: [McKinsey CFO and Finance Excellence](https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/how-we-help-clients/cfo-and-finance-excellence), [McKinsey strategy](https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/how-we-help-clients/strategy), and [McKinsey Strategy & Corporate Finance Insights](https://www.mckinsey.com/capabilities/strategy-and-corporate-finance/how-we-help-clients/scfinsights).

### BCG — corporate finance, strategy and finance-function excellence

BCG publicly describes corporate-finance and strategy capabilities around:

- corporate and business strategy;
- value-creation strategy;
- strategic planning;
- finance-function excellence;
- value delivery and investor attractiveness;
- capital/cash-conversion transparency; and
- cost transparency.

Its finance-function approach includes four major themes: **finance vision and strategy, finance operating model and organization, digitization in finance, and financial steering excellence**, including automated driver-based planning and advanced decision support.

**Product translation:**

- connect corporate strategy to measurable financial value drivers;
- assess finance vision, organization and digital maturity only when internal evidence is available;
- create driver-based forecasts with explainability and bias/error tracking;
- analyze cash conversion and capital deployment; and
- separate the quality of the business from the quality of the market's expectations.

Sources: [BCG corporate finance and strategy](https://www.bcg.com/capabilities/corporate-finance-strategy/overview) and [BCG finance-function excellence](https://www.bcg.com/capabilities/corporate-finance-strategy/finance-function-excellence).

### Bain — full-potential strategy, customers, cost and cash

Bain publicly emphasizes several useful themes:

- leadership in the core business and disciplined moves into close adjacencies;
- future-back scenarios around a small number of critical uncertainties;
- linkage between strategy and operational/financial planning;
- rapid feedback using a few important metrics;
- customer value, product differentiation and pricing;
- go-to-market effectiveness and customer/product profitability;
- sustainable cost transformation aligned with strategy; and
- working-capital optimization to release cash, reduce leverage and fund growth.

**Product translation:**

- distinguish core growth from distant diversification;
- test whether expansion follows demonstrated capabilities;
- connect customer value and pricing power to margins and market share;
- create commercial-excellence diagnostics for mix, price, channel and cost-to-serve;
- avoid recommending uniform cost cuts that may damage competitive strengths;
- prioritize cash release and working-capital ownership; and
- attach a short KPI feedback loop to every recommended initiative.

Sources: [Bain beliefs on strategy](https://media.bain.com/bain-beliefs-in-strategy/), [Bain Elements of Value](https://integrationcms.bain.com/consulting-services/customer-strategy-and-marketing/elements-of-value/), [Bain go-to-market strategy](https://preprodcms.bain.com/consulting-services/customer-strategy-and-marketing/go-to-market-strategy/), [Bain sustained cost transformation](https://www.bain.com/insights/getting-a-competitive-edge-through-cost-transformation), and [Bain working-capital management](https://preprodcms.bain.com/consulting-services/performance-improvement/working-capital-management/).

## 23. Unified value-creation framework for this product

The product should synthesize the common logic without copying a firm's branding or proprietary methodology.

### Stage 1 — Establish a trusted baseline

- resolve the entity, periods and reporting basis;
- reconcile financial statements and important KPIs;
- adjust or label exceptional/accounting effects;
- establish historical, peer and industry baselines; and
- assign data-quality and accounting-confidence scores.

### Stage 2 — Diagnose the value drivers

Decompose enterprise value creation into:

- revenue: market, share, volume, price, mix and acquisitions;
- margin: gross margin, productivity, overhead and operating leverage;
- capital: working capital, fixed assets, capex and portfolio;
- funding: debt, equity, liquidity, tax and cost of capital;
- duration and risk: competitive advantage, resilience, governance and uncertainty; and
- market expectations: forecast assumptions and valuation multiple.

### Stage 3 — Quantify the value at stake

For each material gap:

- compare against a valid peer, historical best, management target or sector benchmark;
- calculate the financial effect of partially closing the gap;
- avoid assuming that the top peer's outcome is fully attainable;
- show sensitivity ranges; and
- state the constraints and internal data required.

### Stage 4 — Form improvement hypotheses

Classify potential actions into:

- pricing and mix;
- customer/channel and go-to-market;
- procurement, operations and supply chain;
- cost structure and organization;
- working capital and cash;
- capex and asset productivity;
- portfolio, M&A and divestment;
- funding and capital returns;
- finance processes, data and controls; and
- governance, risk and disclosure.

### Stage 5 — Prioritize and monitor

Rank hypotheses using:

- financial impact;
- confidence in the diagnosis;
- time to impact;
- implementation difficulty;
- required investment;
- strategic fit;
- downside/second-order risk; and
- measurability through public or internal KPIs.

Every accepted initiative should receive an owner, baseline, target, milestones, leading indicators and outcome metrics when the product is used in Management Mode.

## 24. Standard recommendation object

Every system-generated suggestion should follow one auditable schema:

| Field | Purpose |
|---|---|
| Observation | The specific change, gap or anomaly detected |
| Evidence | Filing, table, page, metric and comparison supporting it |
| Materiality | Size relative to revenue, profit, cash, capital or risk |
| Root-cause hypotheses | Ranked explanations; not unsupported certainty |
| Recommended action | The decision or investigation management could consider |
| Value mechanism | How it could affect growth, margin, cash, ROIC, risk or valuation |
| Indicative impact range | Scenario range with assumptions, not false precision |
| Time horizon | Immediate, 6–12 months, 1–3 years or longer |
| Execution difficulty | Low, medium or high with a reason |
| Dependencies and risks | What must be true and what could go wrong |
| Internal data required | Evidence unavailable from public sources |
| Monitoring KPIs | Leading and lagging measures |
| Confidence | Data confidence and analytical confidence shown separately |

### Language guardrail

When only public information is available, recommendations are **outside-in hypotheses**. For example:

> Receivable performance indicates a potential working-capital opportunity. Customer-level ageing, contract terms and billing-dispute data are required to confirm the cause and select an intervention.

The system should not invent precise internal actions such as changing every customer's credit terms by a fixed number of days without supporting data.

## 25. Future product modes

### Public Investor Mode

- uses only properly licensed public information;
- focuses on accounting quality, competitive position, scenarios, valuation and monitoring;
- labels management-improvement ideas as outside-in hypotheses; and
- does not claim access to confidential operational causes.

### Management/CFO Mode

- adds budgets, forecasts, customer/product/channel/plant data, contracts and management KPIs;
- enables profitability, working-capital, planning and operating-model diagnostics;
- produces an initiative roadmap, owners, targets and benefit tracking; and
- requires stronger privacy, security, access-control and data-retention architecture.

### Due-diligence/Credit Mode

- emphasizes quality of earnings, normalization, contingencies, debt, liquidity, downside and deal risks;
- supports an evidence request list and unresolved-question tracker; and
- avoids using absence of public evidence as evidence of absence.

---

## Working hypothesis

The defensible product is likely to be the combination of:

> **reliable Indian-company data lineage + sector-specific accounting logic + explainable peer/driver analysis + auditable scenario forecasting**

The chat interface is the access layer. The durable value will come from the normalized data, methodologies, evaluation system, and trustworthiness underneath it.
