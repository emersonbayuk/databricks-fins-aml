<div align="center">

# 🛡️ FINS AML Platform

<div style="background: linear-gradient(135deg, #5FA8D3 0%, #AB4057 100%); width: 72px; height: 72px; border-radius: 16px; display: flex; align-items: center; justify-content: center; margin: 0 auto 24px;">
  <svg width="36" height="36" viewBox="0 0 24 24" fill="white">
    <path d="M12,1L3,5V11C3,16.55 6.84,21.74 12,23C17.16,21.74 21,16.55 21,11V5L12,1M12,7C13.4,7 14.8,8.6 14.8,10.1V11H16V16H8V11H9.2V10.1C9.2,8.6 10.6,7 12,7M12,8.2C11.2,8.2 10.4,8.7 10.4,10.1V11H13.6V10.1C13.6,8.7 12.8,8.2 12,8.2Z"/>
  </svg>
</div>

**AI-powered Anti-Money Laundering investigation platform built on Databricks**
*Complete end-to-end solution with synthetic data generation, multi-agent investigation workflows, and interactive dashboards*

[![Databricks](https://img.shields.io/badge/Databricks-Platform-FF3621?style=flat&logo=databricks)](https://databricks.com/)
[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![React](https://img.shields.io/badge/React-18+-61DAFB?style=flat&logo=react&logoColor=black)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)

</div>

## 📁 Repository Structure

<div align="left">

```
fins-aml-amer/
├── 📄 README.md                     # This documentation
├── 🔢 fins-aml-datagen/             # Core data pipeline and analysis notebooks
│   ├── 🏗️  01_aml_data_generation    # Core tables + alerts/cases/SARs + views
│   ├── 🎯 02_aml_watchlist_screening # Watchlist and sanctions screening
│   ├── 🕸️  03_aml_graph_model        # Graph nodes & edges for network viz
│   ├── 📚 04_aml_knowledge_base     # Unstructured docs for RAG
│   └── 📋 docs/                     # Documentation and diagrams
│       ├── 🎨 banner.svg            # Platform banner
│       └── 📊 erd_updated.svg       # Entity relationship diagram
└── 🖥️  fins-aml-app/                # Interactive investigation application
    ├── ⚡ main.py                   # Databricks application entry point
    ├── 🔧 backend/                  # FastAPI backend services
    ├── 🎨 frontend/                 # React frontend components
    └── 📦 requirements.txt          # Python dependencies
```

</div>

## 🔄 Notebook Execution Order

> Run notebooks in this sequence — each depends on tables created by previous steps.

| Step | 📓 Notebook | 🏗️ Creates | 🔗 Dependencies |
|------|-------------|------------|-----------------|
| **1** | `01_aml_data_generation` | `customers`, `accounts`, `transactions`, `alerts`, `cases`, `sar_filings`, `case_audit_log`, + 5 views | None |
| **2** | `02_aml_watchlist_screening` | `watchlists`, `watchlist_hits` | Step 1 |
| **3** | `03_aml_graph_model` | `graph_nodes`, `graph_edges` | Steps 1-2 |
| **4** | `04_aml_knowledge_base` | Knowledge base volume (RAG docs) | Step 1 |

## 🖥️ Interactive Investigation Application

The `fins-aml-app/` folder contains a complete web-based investigation platform built on **Databricks App Framework**. The application provides:

<div align="left">

🤖 **Multi-agent Investigation Workflow** - AI-powered analyst, executive, and agent roles
📋 **Interactive Case Management** - Real-time case investigation with document analysis
🕸️ **Graph Visualization** - Network analysis for relationship mapping
📑 **SAR Generation** - Automated Suspicious Activity Report creation
🔍 **Knowledge Base Integration** - RAG-powered document search and analysis

</div>

> 💡 **Deployment**: Navigate to the `fins-aml-app/` directory and follow the deployment instructions in that folder's documentation.

## Entity Relationship Diagram

![AML ERD](fins-aml-datagen/docs/erd_updated.svg)

### Table Joins

| From Table | Join Key | To Table | Relationship |
|------------|----------|----------|--------------|
| `accounts` | `customer_id` | `customers` | Many-to-One |
| `transactions` | `customer_id` | `customers` | Many-to-One |
| `transactions` | `account_id` | `accounts` | Many-to-One |
| `alerts` | `customer_id` | `customers` | Many-to-One |
| `alerts` | `account_id` | `accounts` | Many-to-One |
| `alerts` | `related_transactions[]` | `transactions.transaction_id` | Many-to-Many (array) |
| `cases` | `alert_id` | `alerts` | One-to-One |
| `cases` | `customer_id` | `customers` | Many-to-One |
| `cases` | `evidence_transaction_ids[]` | `transactions.transaction_id` | Many-to-Many (array) |
| `sar_filings` | `case_id` | `cases` | Many-to-One |
| `sar_filings` | `customer_id` | `customers` | Many-to-One |
| `case_audit_log` | `case_id` | `cases` | Many-to-One |
| `watchlist_hits` | `customer_id` | `customers` | Many-to-One |
| `watchlist_hits` | `list_id` | `watchlists` | Many-to-One |
| `graph_edges` | `source_node_id` | `graph_nodes.node_id` | Many-to-One |
| `graph_edges` | `target_node_id` | `graph_nodes.node_id` | Many-to-One |

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

## 🚀 Quick Start

### 🔢 Data Pipeline Setup
1. **Clone** this repo to your Databricks workspace
2. **Navigate** to the `fins-aml-datagen/` folder
3. **Execute** notebooks 01 → 02 → 03 → 04 in order
4. **Configure** Knowledge Assistant to index the `knowledge_base` volume

### 🖥️ Application Deployment
5. **Navigate** to the `fins-aml-app/` folder
6. **Deploy** the interactive investigation application following the instructions in that directory
7. **Import** Lakeview dashboards for executive reporting

---

<div align="center">

**Built with ❤️ on Databricks** | **AI-Powered AML Solutions**

</div>
