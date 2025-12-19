# AML Solution Accelerator

An end-to-end Anti-Money Laundering (AML) solution built on Databricks, featuring synthetic data generation, multi-agent investigation workflows, and interactive dashboards.

## Repository Structure

```
fins-aml/
├── README.md
├── 01_aml_data_generation           # Core tables + alerts/cases/SARs + views
├── 02_aml_watchlist_screening       # Watchlist and sanctions screening
├── 03_aml_graph_model               # Graph nodes & edges for network viz
├── 04_aml_knowledge_base            # Unstructured docs for RAG
└── docs/
    └── erd.svg                      # Entity relationship diagram
```

## Notebook Execution Order

Run notebooks in this sequence — each depends on tables created by previous steps.

| Step | Notebook | Creates | Dependencies |
|------|----------|---------|--------------|
| 1 | `01_aml_data_generation` | `customers`, `accounts`, `transactions`, `alerts`, `cases`, `sar_filings`, `case_audit_log`, + 5 views | None |
| 2 | `02_aml_watchlist_screening` | `watchlists`, `watchlist_hits` | Step 1 |
| 3 | `03_aml_graph_model` | `graph_nodes`, `graph_edges` | Steps 1-2 |
| 4 | `04_aml_knowledge_base` | Knowledge base volume (RAG docs) | Step 1 |

## Entity Relationship Diagram

![AML ERD](docs/erd.svg)

```
                                    CORE ENTITIES
┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
│   CUSTOMERS     │──1:N─▶│    ACCOUNTS      │──1:N─▶│  TRANSACTIONS   │
│                 │       │                  │       │                 │
│ • customer_id   │       │ • account_id     │       │ • txn_id        │
│ • risk_rating   │       │ • account_type   │       │ • amount        │
│ • pep_flag      │       │ • status         │       │ • counterparty  │
└────────┬────────┘       └──────────────────┘       └─────────────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐       ┌──────────────────┐       ┌─────────────────┐
│     ALERTS      │──1:1─▶│      CASES       │──1:N─▶│   SAR_FILINGS   │
│                 │       │                  │       │                 │
│ • alert_id      │       │ • case_id        │       │ • sar_id        │
│ • scenario_type │       │ • case_status    │       │ • fincen_dcn    │
│ • priority      │       │ • disposition    │       │ • narrative     │
└─────────────────┘       └────────┬─────────┘       └─────────────────┘
                                   │ 1:N
                                   ▼
                          ┌──────────────────┐
                          │  CASE_AUDIT_LOG  │
                          └──────────────────┘

                               SCREENING
┌─────────────────┐       ┌──────────────────┐
│   WATCHLISTS    │──1:N─▶│  WATCHLIST_HITS  │◀─── CUSTOMERS
│                 │       │                  │
│ • list_type     │       │ • match_score    │
│ • entity_name   │       │ • status         │
└─────────────────┘       └──────────────────┘

                              GRAPH MODEL
┌─────────────────────┐              ┌─────────────────────────┐
│    GRAPH_NODES      │◀────────────▶│      GRAPH_EDGES        │
│                     │              │                         │
│ • node_id           │              │ • source_node_id        │
│ • node_type         │              │ • target_node_id        │
│ • risk_score        │              │ • edge_type             │
│ • properties (JSON) │              │ • weight                │
└─────────────────────┘              └─────────────────────────┘
```

## Detection Scenarios

Synthetic data includes pre-seeded patterns for 9 AML scenarios:

| Scenario | Customer IDs | Rule |
|----------|--------------|------|
| Structuring | 1-50 | ≥3 cash deposits $9K-$9,999 in 7 days |
| Rapid Movement | 51-100 | >$50K in/out within 24hrs, <5% retained |
| Dormant Reactivation | 101-150 | 12+ months inactive, then >$20K/week |
| High-Risk Geography | 151-200 | >$10K wire to FATF blacklisted country |
| Round Dollar | 201-250 | ≥10 round-dollar transfers/day |
| Beneficiary Mismatch | 251-300 | Payment to unrelated beneficiary |
| Third-Party Deposits | 301-350 | >3 third-party deposits in 7 days |
| Related Accounts | 351-400 | ≥3 transfers between linked accounts |
| PEP/Sanctions | 401-450 | Transaction with PEP or OFAC match |

## Knowledge Base Documents

The Knowledge Assistant uses a hybrid corpus of real regulatory documents and synthetic customer-specific documents.

### Regulatory & Policy Documents (Downloaded Automatically)

These publicly available documents are downloaded when running `04_aml_knowledge_base`:

| Category | Document | Source | Description |
|----------|----------|--------|-------------|
| **FFIEC** | [Appendix F - Red Flags](https://bsaaml.ffiec.gov/docs/manual/10_Appendices/07.pdf) | FFIEC | Money laundering and terrorist financing red flag indicators |
| **FFIEC** | [CIP Examination Manual](https://www.fdic.gov/news/financial-institution-letters/2021/fil21012b.pdf) | FDIC | Customer Identification Program requirements |
| **FinCEN** | [SAR Narrative Guidance](https://www.irs.gov/pub/irs-tege/itg_sarc_prep.pdf) | IRS/FinCEN | How to prepare complete SAR narratives (who/what/when/where/why) |
| **FinCEN** | [CTR Reference Guide](https://www.fincen.gov/system/files/shared/CTRPamphlet.pdf) | FinCEN | $10K threshold, aggregation rules, structuring examples |
| **FinCEN** | [CDD Rule FAQs](https://www.fincen.gov/system/files/2018-04/FinCEN_Guidance_CDD_FAQ_FINAL_508_2.pdf) | FinCEN | Customer Due Diligence requirements |
| **FinCEN** | [Beneficial Ownership FAQs](https://www.fincen.gov/system/files/2016-09/FAQs_for_CDD_Final_Rule_(7_15_16).pdf) | FinCEN | Beneficial ownership identification requirements |
| **OFAC** | [Compliance Framework](https://ofac.treasury.gov/media/16331/download?inline=) | Treasury | 5 pillars of sanctions compliance |
| **OFAC** | [Instant Payments Guidance](https://ofac.treasury.gov/system/files/126/instant_payment_systems_compliance_guidance_brochure.pdf) | Treasury | Risk-based sanctions compliance for instant payments |
| **Internal** | [VLS Finance AML Policy](https://www.vlsfinance.com/wp-content/uploads/2022/01/Anti-Money-Laundering-Policy.pdf) | VLS Finance | Sample institution AML policy with KYC procedures |
| **Internal** | [JAB AML Policy](https://www.jabholco.com/img/pdf/JAB_AML_Policy.pdf) | JAB Holding | Detailed red flags list for suspicious activity |
| **Internal** | [HRW AML Policy](https://www.hrw.org/sites/default/files/news_attachments/hrw-anti-money-laundering-policy-december2016.pdf) | Human Rights Watch | Donor/supplier due diligence procedures |
| **Internal** | [MultiChoice AML Policy](https://investors.multichoice.com/pdf/policies-and-charters/2024/mcg-anti-money-laundering-policy.pdf) | MultiChoice | Corporate AML framework (2024) |

### Synthetic Customer Documents (Generated)

These documents are generated from the structured data and linked to specific customers:

| Document Type | Folder | Description | Linked To |
|---------------|--------|-------------|-----------|
| **SAR Narratives** | `sar_narratives/` | Complete SAR filing narratives with regulatory citations | `customer_id`, `sar_id` |
| **Case Notes** | `case_notes/` | Investigation timelines with AI assistant query logs | `case_id`, `customer_id`, `alert_id` |
| **EDD Memoranda** | `edd_memos/` | Enhanced Due Diligence reviews for high-risk customers | `customer_id` |
| **Adverse Media** | `adverse_media/` | Media screening reports with disposition | `customer_id` |
| **Correspondence** | `correspondence/` | Customer interaction logs (branch visits, calls) | `customer_id` |

### Knowledge Base Folder Structure

```
/Volumes/fins_aml/data_generation/knowledge_base/
├── policies_and_regulations/
│   ├── ffiec/                    # FFIEC exam manual, red flags
│   ├── fincen/                   # SAR, CTR, CDD guidance
│   ├── ofac/                     # Sanctions compliance
│   └── internal/                 # Institution AML policies
├── sar_narratives/               # ~15-25 SAR narratives
├── case_notes/                   # ~30-50 investigation notes
├── edd_memos/                    # ~40-60 EDD reviews
├── adverse_media/                # ~50-80 screening reports
└── correspondence/               # ~40-70 interaction logs
```

## Configuration

All notebooks use:
```python
CATALOG = "fins_aml"
SCHEMA = "data_generation"
```

## Quick Start

1. Clone this repo to your Databricks workspace
2. Run notebooks 01 → 02 → 03 → 04 in order
3. Configure Knowledge Assistant to index the `knowledge_base` volume
4. Import Lakeview dashboards
5. Deploy investigation app

## Knowledge Assistant Configuration

When setting up the Knowledge Assistant, use these recommended settings:

- **Volume Path:** `/Volumes/fins_aml/data_generation/knowledge_base`
- **Chunking:** ~500 tokens with 50 token overlap
- **Metadata Fields:** `document_type`, `customer_id`, `source`
