# Indian Listed-Company Analysis — Initial Data-Source Strategy

**Status:** Initial source and licensing hypothesis for discussion  
**Last updated:** 23 August 2026  
**Related documents:** [PROJECT_RESEARCH_BLUEPRINT.md](../plans/PROJECT_RESEARCH_BLUEPRINT.md) and [PRESENTATION_OUTPUT_SPEC.md](../plans/PRESENTATION_OUTPUT_SPEC.md)

## 1. Objective

Define which sources can support a credible, scalable Indian-company analysis product and how the system should evaluate, acquire, store, reconcile, cite, and legally use them.

This document separates four questions:

1. **Credibility:** Is the publisher authoritative for the fact?
2. **Accuracy and completeness:** Is the specific record correct, current, and sufficiently detailed?
3. **Technical usability:** Can it be obtained consistently and processed at scale?
4. **Legal/commercial usability:** Do the terms permit ingestion, storage, transformation, model use, display, and redistribution?

A source can be credible without being licensed for commercial reuse. Publicly visible does not mean freely reusable.

## 2. Source hierarchy

### Tier 1 — Regulatory and exchange-filed primary evidence

- audited annual reports and financial statements;
- quarterly/annual financial results and XBRL filings;
- exchange announcements and corporate actions;
- shareholding, promoter pledge, governance, and BRSR filings;
- regulatory orders, licences, tariffs, and official statistics; and
- MCA company records.

Use Tier 1 for reported facts wherever possible.

### Tier 2 — Company first-party narrative

- investor presentations;
- earnings-call transcripts or recordings;
- management interviews;
- company press releases;
- sustainability reports; and
- website disclosures.

Tier 2 is authoritative for what management said, not independent proof that the claim is correct. Cross-check material statements against filings and external evidence.

### Tier 3 — Regulated or specialist third-party evidence

- credit-rating rationales;
- industry associations;
- government-recognized research bodies;
- specialist data providers;
- reputable news and trade publications; and
- licensed analyst estimates or transcripts.

Use Tier 3 to interpret and supplement primary evidence. Preserve copyright and licensing restrictions.

### Tier 4 — Alternative and observational data

- import/export activity;
- product prices;
- app/web traffic;
- hiring and employee data;
- store/location data;
- patents and trademarks;
- tenders and procurement; and
- channel or customer evidence.

Use only when provenance, legality, representativeness, and bias are understood.

### Tier 5 — Retail aggregators and informal sources

- retail finance websites;
- social media;
- discussion forums; and
- unofficial APIs or scraped datasets.

These may help discover questions or manually cross-check a prototype. They should not be treated as the production source of truth without a written licence and a demonstrated quality process.

## 3. Source credibility, API, and cost matrix

| Source | Credibility | Free public access? | Official API/bulk feed? | Production cost pattern | Best use and initial production position |
|---|---:|---|---|---|---|
| NSE/BSE company filings | Very high | Yes, through public webpages/manual downloads | Yes, paid exchange feeds; BSE advertises APIs, while NSE provides feed/SFTP products | Mainly annual subscription, data/display licence, connectivity and redistribution fees—not normally per hit | Results, reports, announcements, ownership and governance; production should use licensed or contractually permitted access |
| Company annual report/IR site | High, management-controlled | Usually yes | Usually no standardized API | Normally ₹0 to view; commercial crawling, storage and redistribution rights are not automatically free | Audited statements, notes, KPIs, strategy and commentary; cite/summarize and retain only as permitted |
| MCA21 | Very high for legal records | Master data is generally accessible; public documents require login/payment | No general public bulk API confirmed for this use case | Master lookup may be free; public-document fee is per company/request, with current checkout and bulk rights to be verified | Identity, directors, charges, annual returns and public documents; supplemental until automation/reuse rights are confirmed |
| SEBI | Very high | Yes | No normalized company-fundamentals API identified | ₹0 for public access; commercial data needs may route to exchanges | Regulations, orders, filing directories and market rules; use as authority and source router |
| RBI DBIE | Very high | Yes | Query/download tools are available; no general billable production API confirmed in this research | Public portal/download appears free; verify terms and any automation limits | Macro, banking, credit, rates and financial-sector data; preferred macro source with attribution and lineage |
| Data.gov.in/OGD | High | Yes | Yes for many datasets, using an API key; CSV and other downloads also available | Generally ₹0 for OGD resources; dataset-specific terms and rate limits must be checked | Official open datasets; strong production candidate where the dataset is covered by the Government Open Data Licence |
| Sector regulator/ministry | Very high | Usually yes | Varies; many provide only files/tables, not APIs | Often ₹0 for public publications; dataset-specific subscriptions or restrictions may exist | Sector demand, licences, tariffs, capacity and operating statistics; review one dataset at a time |
| Credit-rating agency | High | Many rating rationales can be viewed publicly | Commercial API/bulk access varies and is usually licensed | Public reading may be free; storage, bulk use, API and redistribution are normally quote/contract based | Debt, liquidity, covenants and credit risks; cite or license and do not republish wholesale |
| Licensed commercial database | Medium to very high | Usually trial/demo only | Usually yes through API, bulk feed, terminal or export, depending on product | Paid subscription/enterprise quote; may include user, API, record, display and redistribution charges | Normalized fundamentals, prices, estimates and identifiers; evaluate through proof of concept and contract review |
| Reputable news provider | Medium/high | Limited free articles may exist | Licensed APIs/feeds are commonly available | Subscription, per-user, per-request, volume or redistribution pricing | Events, investigations and external context; use licensed feeds and corroborate material claims |
| Retail finance website | Variable | Often free/freemium UI | Sometimes no official API; unofficial endpoints must not be assumed usable | Free/freemium for a human user; commercial/API use may be prohibited or separately licensed | Discovery and manual validation only unless written permission is obtained |
| Social media/forum | Low/variable | Often free/freemium UI | Platform APIs are mixed, limited, or paid | Free, subscription, or volume pricing depending on platform; moderation costs are material | Leads and sentiment only; never evidence without independent verification |

Prices and API status change. Every entry must carry a `pricing_verified_at` date and a link or contract reference.

## 4. Initial API and pricing register

**Pricing verification date:** 23 August 2026  
**Currency:** Indian rupees unless stated otherwise  
**Important:** Published fees may exclude taxes, connectivity, implementation, non-display, derived-data, website/app display, user/device, and redistribution charges.

| Provider/product | Access/interface | Free tier? | Billing unit | Current public indication | Literal per-hit cost available? |
|---|---|---:|---|---|---:|
| NSE public corporate-filing pages | Website/manual downloads | Yes, for public viewing | None for manual access | ₹0 to browse; this is not a production API licence | No |
| NSE Corporate Data | Dedicated leased-line feed | No | Subscription plus customer connectivity | Published domestic price: ₹10,60,000; confirm contract period, taxes, circuit and display/redistribution rights | No; amortize fixed cost |
| NSE End-of-Day Corporate Announcements | Daily internet/SFTP after 8:00 PM IST | No | Annual subscription | Published domestic price: ₹5,00,000 per annum | No; amortize fixed cost |
| NSE Corporate Bond Market Data | Dedicated leased-line feed | No | Subscription plus customer connectivity | Published domestic price: ₹3,40,000; verify full commercial terms | No; amortize fixed cost |
| NSE market/EOD/historical data | Product-specific feed/download | No production free tier assumed | Annual/product/location/display/non-display licence | Current tariff is published separately and became effective 1 April 2026; select the exact product before costing | Usually no |
| BSE Self Data Feed — equity/corporate/delayed data | API and, for some products, leased line | Limited trial advertised | Selected plan plus pricing agreement and usage rights | Free trial for selected feeds; production pricing requires plan/contract confirmation | Not publicly established |
| BSE market, corporate, EOD and historical products | Data feed/API/product files | No general production free tier assumed | Subscription/licence, product and usage category | BSE publishes a tariff sheet; obtain a current quotation covering generated-PPT display and redistribution | Not publicly established |
| MCA company master data | Web portal | Generally yes | Public lookup | ₹0 indicated for basic master-data access | Not applicable |
| MCA View Public Documents | Logged-in portal/download | No | Per company/request | Official MCA material has cited ₹50 per company, but verify the current live fee and reuse rights before budgeting | Per company rather than API hit |
| SEBI regulations/orders/directories | Website/download | Yes | None for public access | ₹0 to access public pages; no normalized company API | Not applicable |
| RBI DBIE | Web query/download | Yes | None publicly identified | ₹0 public access observed; confirm automation and reuse terms | No published per-hit fee |
| Data.gov.in/OGD APIs | API key and file download | Yes for OGD datasets | Free API/resource access subject to dataset terms and rate limits | ₹0 for covered resources; attribution required under the Government Open Data Licence | ₹0, subject to current limits |
| Sector regulators/ministries | Web files, tables, and occasional APIs | Usually | Dataset-specific | Often ₹0; record the status separately for every series | Usually no |
| Rating rationales | Public web/PDF plus possible commercial feeds | Public reading often yes | Commercial licence/quote for bulk, API, storage or redistribution | Unknown until provider quote | Provider-specific |
| Commercial fundamentals/estimates vendors | API, bulk feed, terminal, export | Demo/trial may exist | Annual licence, user, API, data package and usage rights | Quote required | Provider-specific |
| Licensed news/transcript provider | API/feed/platform | Trial or limited free access may exist | Subscription, request, article, token/word, user or redistribution | Quote/tariff required | Sometimes |

NSE prices above come from its [Paid Corporate Data page](https://www.nseindia.com/static/market-data/corporate-data-subscription), updated 11 June 2026. NSE publishes a separate [2026 products tariff](https://www.nseindia.com/static/market-data/products-tariff). BSE's [Self Data Feed](https://marketdata.bseindia.com/) advertises APIs, selected free trials, and paid pricing agreements. MCA's live fee should be reconfirmed because older official material cites ₹50 per company rather than providing a current API tariff.

### 4.1 Cost per generated report

Many important sources do not charge per API call. Estimate an effective source cost for each generated deck:

```text
effective_source_cost_per_deck
  = direct_per_request_or_document_fees
  + allocated_fixed_licence_cost
  + allocated_display_or_redistribution_fees
  + marginal_storage_and_egress
  + incremental_compute_and_parsing
  + incremental_human_review
```

Where:

```text
allocated_fixed_licence_cost
  = annual_fixed_source_cost / annual_decks_using_that_source
```

Also calculate costs per covered company, updated company-year, active user, and successful deck. A low API-call cost can still produce an expensive report when analyst review or document parsing is required.

### 4.2 Request-level cost observability

Record every external request in a source-usage ledger:

- provider and product;
- endpoint/feed/file;
- company, document and reporting period;
- timestamp and request ID;
- billable units returned;
- list-price and contracted cost rule;
- estimated marginal cost;
- cache hit or miss;
- retry/failure count;
- bytes stored and transferred;
- deck/user/job consuming the data; and
- licence/display category.

Use content-addressed storage and source-aware caching so the same annual report is not purchased, downloaded, or parsed repeatedly. Caching must remain within the provider's contractual retention and display terms.

### 4.3 Required cost fields in the provider register

- `public_ui_free`;
- `official_api_available`;
- `bulk_feed_available`;
- `trial_available` and expiry;
- billing model and billable unit;
- setup and connectivity cost;
- annual/monthly minimum;
- per-request, per-document, per-record, and overage cost;
- user/device/location fees;
- internal/non-display fees;
- website/app/PPT display fees;
- derived-data and redistribution fees;
- currency, taxes, escalation and renewal date;
- rate limits and service levels;
- expected annual usage;
- amortized cost per company and per deck; and
- `pricing_verified_at` plus source/contract reference.

## 5. Primary Indian source map

### 5.1 SEBI

- [SEBI corporate-filings directory](https://www.sebi.gov.in/curation/corporate_filings.html)
- [SEBI equity cash-market data directory](https://www.sebi.gov.in/curation/equity_cash_market.html)
- [SEBI securities-market data access and usage approach](https://www.sebi.gov.in/legal/circulars/feb-2022/approach-to-securities-market-data-access-and-terms-of-usage-of-data-provided-by-data-sources-in-indian-securities-market_56420.html)

Use SEBI as the authority for regulations, orders, official circulars, and links to exchange filings. Monitor regulatory changes affecting market data, research analysis, AI, and price-data sharing.

### 5.2 NSE

- [Financial results](https://www.nseindia.com/companies-listing/corporate-filings-financial-results)
- [Corporate announcements](https://www.nseindia.com/companies-listing/corporate-filings-announcements)
- [Annual-report filings](https://www.nseindia.com/companies-listing/corporate-filings-annual-reports)
- [XBRL information](https://www.nseindia.com/static/companies-listing/xbrl-information)
- [Corporate-data subscription](https://www.nseindia.com/static/market-data/corporate-data-subscription)
- [Data sharing and usage policy](https://www.nseindia.com/static/market-data/nse-data-policy)
- [Market-data product tariff](https://www.nseindia.com/static/market-data/products-tariff)

NSE is a preferred primary source, but production architecture must be based on an appropriate data agreement rather than undocumented website endpoints.

### 5.3 BSE

- [Financial results](https://www.bseindia.com/corporates/Comp_Resultsnew.aspx)
- [BSE market and corporate data products](https://marketdata.bseindia.com/)
- [BSE information-products tariff](https://www.bseindia.com/downloads1/Information_Products_Pricing_Sheet.pdf)

BSE offers market, corporate, delayed, and historical-data products. The product should compare NSE and BSE corporate coverage, identifiers, history, latency, correction handling, and commercial terms.

### 5.4 Company investor-relations sources

Use for:

- annual reports and notes;
- investor presentations;
- transcripts/recordings;
- policies and governance information;
- segment KPIs;
- management guidance; and
- strategy and capital-allocation commentary.

Prefer the exchange-filed copy when a company website copy differs. Store the checksum and publication/retrieval timestamps.

### 5.5 MCA21

Potential uses:

- CIN and legal identity;
- company status and incorporation data;
- directors and registered office;
- charges and secured borrowings;
- annual returns;
- corporate relationships; and
- public documents not present in exchange archives.

[MCA guidance](https://www.mca.gov.in/Ministry/pdf/MCAV2Release2_Help.pdf) describes public company documents and a login/payment workflow for viewing them. Before production use, confirm bulk-access, storage, derivative-use, and display rights.

### 5.6 RBI Database on Indian Economy

[RBI DBIE](https://data.rbi.org.in/) can support:

- rates and monetary conditions;
- inflation and exchange rates;
- credit and deposit growth;
- banking and payment indicators;
- corporate-sector aggregates;
- financial markets;
- external-sector data; and
- macroeconomic scenario variables.

Store RBI series identifiers, vintage/retrieval dates, units, frequency, seasonal status, and metadata.

### 5.7 Open Government Data Platform India

- [Data.gov.in policies](https://www.data.gov.in/policies)
- [Government Open Data Licence — India](https://ap.data.gov.in/godl)

The Government Open Data Licence permits commercial and non-commercial use, adaptation, derivative works, and publication subject to its conditions, including attribution. Confirm that each dataset is actually covered by the licence; do not generalize the licence to unrelated government web content.

### 5.8 Sector regulators and ministries

Build separate registries for:

- RBI — banks and NBFCs;
- IRDAI — insurance;
- TRAI — telecommunications;
- CEA/CERC and state regulators — electricity and utilities;
- PPAC/PNGRB — oil, gas, refining, and pipelines;
- DGCA and aviation ministries — aviation;
- NPPA/CDSCO — pharmaceuticals and regulation;
- Ministry of Commerce/DGFT — trade;
- Ministry of Road Transport and SIAM where licensed — vehicles;
- CCI — competition, combinations, and market definitions; and
- other industry-specific authorities.

Each sector module should identify the authoritative statistic, publication schedule, archive depth, revisions, format, and reuse terms.

## 6. Source selection by data element

| Data element | Preferred source | Secondary check |
|---|---|---|
| Legal company identity | Exchange security master + MCA | Company annual report |
| Financial statements | Latest revised NSE/BSE filing and XBRL | Audited annual report |
| Notes and accounting policies | Audited annual report | MCA filing where necessary |
| Segments and operating KPIs | Annual report/exchange-filed presentation | Earnings commentary and peers |
| Corporate announcements | Licensed NSE/BSE corporate feed | Company IR site |
| Corporate actions | Licensed exchange feed | Depository/company confirmation |
| Shareholding/promoter pledge | Exchange filing | Annual report |
| Market prices and volumes | Licensed NSE/BSE or authorized vendor | Second licensed vendor for QA |
| Index membership/history | Licensed index/exchange source | Vendor with explicit rights |
| Macro variables | RBI, NSO/MOSPI, OGD | Multilateral institution where useful |
| Sector operating data | Sector regulator/ministry | Industry association/licensed specialist |
| Debt and ratings | Exchange debt filings + rating rationale | Annual report and lender disclosures |
| Management guidance | Exchange-filed presentation/transcript | Company recording/IR site |
| Analyst consensus | Licensed estimates provider | Not applicable without suitable licence |
| News/events | Licensed reputable news provider | Primary filing or regulator confirmation |

## 7. Conflict-resolution rules

1. Preserve every raw version; never overwrite source documents.
2. Prefer the latest formally revised exchange filing for the relevant reporting period.
3. Reconcile annual reported totals to audited annual statements.
4. Keep standalone and consolidated values separate.
5. Do not mix period-end dates or fiscal-year definitions.
6. Record restatements and taxonomy/accounting-policy changes.
7. Use company presentations for operating KPIs only when definitions are captured.
8. Flag conflicts instead of silently selecting a convenient value.
9. Lower confidence when evidence is incomplete or definitions are incomparable.
10. Retain the value known at each historical date for point-in-time backtesting.

## 8. Minimum metadata for every fact

Every reported or derived data point should contain:

- canonical company ID;
- security and exchange identifiers;
- metric ID and company-reported label;
- value, currency, unit, and scale;
- reporting period and period type;
- filing/publication timestamp;
- retrieval timestamp;
- standalone/consolidated basis;
- audited/unaudited status;
- reported/normalized/derived classification;
- source publisher, URL, document ID, and page/table/section;
- checksum and raw-document version;
- revision/restatement status;
- parser and normalization-rule version;
- licence/source-usage category;
- reconciliation status; and
- data-quality confidence.

## 9. Licensing register

Maintain one record per source/provider containing:

- contracting entity;
- content/data products covered;
- permitted internal use;
- permitted model-training or analytical use;
- permitted caching and storage duration;
- permitted derived-data creation;
- permitted website/PPT/user display;
- redistribution rights;
- non-display usage rights;
- attribution requirements;
- user/location/device limits;
- historical-data rights;
- termination and deletion obligations;
- audit requirements;
- renewal date and cost;
- API/feed availability and free-trial status;
- billing unit and minimum commitment;
- per-call, per-document, per-record, overage and connectivity cost;
- display, non-display, derived-data and redistribution charges;
- expected volume and amortized cost per company/deck;
- pricing verification date and tariff/contract reference; and
- legal/compliance owner.

No source should enter production without an assigned licence category.

## 10. Candidate commercial-data evaluation

Potential categories for a formal proof of concept include:

- direct NSE/BSE market and corporate feeds;
- authorized exchange data vendors;
- Indian corporate-fundamentals databases;
- global market/fundamentals providers;
- transcript and analyst-estimate providers;
- news feeds; and
- sector-specific databases.

Possible vendors to investigate include CMIE Prowess, Capitaline, ACE Equity, S&P Capital IQ, Bloomberg, LSEG, and FactSet. This is an evaluation list, not an endorsement or assertion that a product includes the required API or redistribution rights.

Evaluate each provider using:

- Indian listed-company coverage;
- delisted, renamed, merged, and demerged company history;
- point-in-time and restated data;
- standalone/consolidated/segment depth;
- identifiers and corporate actions;
- financial-company support;
- data lineage;
- API and bulk-delivery reliability;
- update latency and service levels;
- historical depth;
- correction procedures;
- forecast/estimate methodology;
- display, derivation, and redistribution rights; and
- fixed, variable, connectivity and overage costs at expected query/user volume;
- whether generated-PPT display is explicitly permitted; and
- effective cost per covered company and generated deck.

## 11. Prototype versus production

### Prototype

- use a small, manually controlled company universe;
- obtain filings from official pages;
- retain URLs and citations;
- calculate normalized metrics internally;
- use end-of-day rather than real-time prices;
- avoid redistributing source documents;
- do not depend on undocumented endpoints; and
- use retail sites only for manual comparison, not as the database.

### Production

- use licensed exchange/vendor feeds;
- operate a canonical entity/security master;
- maintain immutable raw storage and revision history;
- automate reconciliations and data-quality checks;
- retain point-in-time data;
- implement licence-aware display and retention controls;
- monitor source failures and schema changes; and
- provide source citations and corrections to users.

## 12. Recommended MVP source stack

1. **Identity:** Exchange security master plus MCA identifiers.
2. **Financial facts:** NSE/BSE filings and XBRL, reconciled to annual reports.
3. **Narrative evidence:** Exchange-filed reports, presentations, and announcements.
4. **Market data:** Licensed end-of-day exchange or authorized-vendor feed.
5. **Macro:** RBI DBIE and specifically OGD-licensed government datasets.
6. **Sector:** One authoritative regulator/ministry source per pilot sector.
7. **Credit:** Exchange debt disclosures plus cited/licensed rating rationales.
8. **Normalization:** Initially internal calculations; compare against at least one licensed provider during evaluation.

Real-time prices are not required for the initial long-term company-analysis product.

## 13. Initial feasibility experiment

For one IT-services company and one cement company:

1. Build the canonical company/security record.
2. Retrieve five annual reports and eight quarterly results.
3. Extract and reconcile the three financial statements.
4. Capture segment and sector KPIs.
5. Assemble shareholding, governance, debt, and announcement histories.
6. Obtain five years of properly licensed end-of-day prices.
7. Link relevant RBI/sector series.
8. Record extraction time, missingness, conflicts, and revisions.
9. Compare internal normalized data with a commercial provider sample.
10. Produce a source coverage, quality, rights, and cost matrix.

## 14. Data-quality and unit-cost metrics

Track:

- coverage completeness;
- field accuracy against audited statements;
- statement reconciliation rate;
- freshness and publication-to-ingestion latency;
- percentage of facts with page-level lineage;
- revision detection time;
- entity-matching error rate;
- parser failure rate;
- peer-period comparability;
- point-in-time completeness; and
- source/licence classification completeness;
- API requests and billable units per deck;
- cache hit rate and duplicate-download avoidance;
- marginal data cost per deck;
- fully loaded data cost per deck;
- cost per successfully updated company; and
- data/analyst cost as a percentage of product revenue.

## 15. Decisions still required

1. What is the initial company universe?
2. Which two sectors will be piloted?
3. What is the annual data-licensing budget?
4. Is end-of-day pricing sufficient for every initial feature?
5. Do we require analyst consensus and transcripts in the MVP?
6. Will source documents be shown to users or only linked/cited?
7. How long must raw documents and user-generated decks be retained?
8. Will the system eventually accept confidential company data?
9. Which provider can contractually support generated PowerPoint display and redistribution?
10. Who will conduct the legal and compliance review of data terms?

---

## Initial recommendation

Use official exchange filings as the factual backbone, RBI/OGD and sector regulators for external drivers, and a licensed end-of-day price/corporate-data feed for production. Build our own transparent calculation layer, preserve raw evidence and revisions, and evaluate commercial normalized databases as accelerators—not as unquestioned sources of truth.
