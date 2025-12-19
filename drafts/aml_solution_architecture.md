# Databricks AML Solution Architecture
## End-to-End Anti-Money Laundering Detection & Investigation Platform

**Author:** Kat Savchyn  
**Date:** December 2025  
**Version:** 1.0

---

## Executive Summary

This document outlines a comprehensive Anti-Money Laundering (AML) solution built on the Databricks Data Intelligence Platform. The solution addresses the full lifecycle from data ingestion through alert generation to AI-assisted investigation and SAR filing decisions. Building on the multi-agent compliance assistant demonstrated in our [financial crime detection blog](https://medium.com/@databricksfinserv/transforming-financial-crime-detection-918eeb281bca), this architecture extends the solution to include realistic source systems, data models, detection scenarios, operational dashboards, and a unified front-end application.

---

## 1. Solution Overview

### 1.1 Business Problem

Financial institutions face critical AML compliance challenges:

- **90-95% false positive rates** in traditional transaction monitoring systems
- **$61 billion annual compliance costs** in the US and Canada alone
- **Manual, siloed investigation workflows** spanning 2.5-4 hours per case
- **Regulatory pressure** from FinCEN, FATF, and regional regulators

### 1.2 Solution Components

| Layer | Databricks Component | Function |
|-------|---------------------|----------|
| Data Ingestion | Delta Live Tables (DLT) | Real-time and batch ETL from source systems |
| Data Storage | Unity Catalog + Delta Lake | Governed lakehouse with lineage |
| Risk Scoring | MLflow + Feature Store | Customer risk rating models |
| Alert Generation | Databricks SQL + Structured Streaming | Rule-based and ML-based alert creation |
| Dashboard | Databricks Dashboard (Lakeview) | Operational KPIs and alert triage |
| AI Investigation | Genie + Agent Bricks Multi-Agent | Conversational case investigation |
| Front-End | Databricks Apps | Unified analyst experience |
| Workflow | Databricks Workflows | Orchestration and scheduling |

---

## 2. Source Systems & Data Ingestion

### 2.1 Source Systems

A realistic AML implementation requires data from multiple banking systems:

| Source System | Data Type | Ingestion Method | Frequency |
|---------------|-----------|------------------|-----------|
| **Core Banking System (CBS)** | Customer master, accounts, products | CDC via Debezium/Kafka | Real-time |
| **Payment Hub** | Wire transfers, ACH, SWIFT messages | Streaming (Kafka/Event Hub) | Real-time |
| **Card Management** | Card transactions, authorizations | Streaming | Real-time |
| **KYC/Onboarding Platform** | Customer due diligence, documents | Batch API | Daily |
| **Case Management System** | Historical cases, SARs, dispositions | Batch/CDC | Daily |
| **Sanctions/Watchlist Provider** | OFAC, PEP, adverse media | Delta Sharing or API | Daily |
| **Core Deposit System** | Cash deposits, withdrawals, teller activity | CDC | Near real-time |
| **Trade Finance System** | Letters of credit, trade documentation | Batch | Daily |
| **External Data Vendors** | LexisNexis, Thomson Reuters, Experian | API/Batch | On-demand/Daily |

### 2.2 Delta Live Tables Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        BRONZE LAYER (Raw Ingestion)                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  bronze_transactions  │  bronze_customers  │  bronze_accounts  │  bronze_kyc │
│  bronze_wire_transfers│  bronze_sanctions  │  bronze_cases     │  bronze_pep │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     SILVER LAYER (Cleansed & Enriched)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  silver_transactions_enriched  │  silver_customer_360  │  silver_accounts   │
│  silver_wire_transfers_enriched│  silver_kyc_current   │  silver_entity_map │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                  GOLD LAYER (Analytics & Feature Store)                     │
├─────────────────────────────────────────────────────────────────────────────┤
│  gold_customer_risk_profile  │  gold_transaction_patterns  │  gold_alerts   │
│  gold_entity_network         │  gold_scenario_hits         │  gold_cases    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Key DLT Tables

#### Bronze Layer (Raw)

```python
@dlt.table(
    name="bronze_transactions",
    comment="Raw transaction events from core banking and payment systems"
)
def bronze_transactions():
    return (
        spark.readStream
        .format("kafka")
        .option("subscribe", "transactions")
        .load()
        .select(
            col("key").cast("string").alias("transaction_id"),
            from_json(col("value").cast("string"), transaction_schema).alias("data"),
            col("timestamp").alias("kafka_timestamp")
        )
        .select("transaction_id", "data.*", "kafka_timestamp")
    )
```

#### Silver Layer (Enriched)

```python
@dlt.table(
    name="silver_transactions_enriched",
    comment="Transactions enriched with customer, account, and geographic data"
)
@dlt.expect_or_drop("valid_amount", "transaction_amount > 0")
@dlt.expect_or_drop("valid_currency", "currency_code IS NOT NULL")
def silver_transactions_enriched():
    txns = dlt.read_stream("bronze_transactions")
    customers = dlt.read("silver_customer_360")
    accounts = dlt.read("silver_accounts")
    countries = dlt.read("ref_country_risk")
    
    return (
        txns
        .join(accounts, "account_id", "left")
        .join(customers, "customer_id", "left")
        .join(countries, txns.country_code == countries.iso_code, "left")
        .withColumn("transaction_hour", hour("transaction_timestamp"))
        .withColumn("transaction_day_of_week", dayofweek("transaction_timestamp"))
        .withColumn("is_high_risk_country", col("fatf_status") == "High Risk")
        .withColumn("is_round_amount", (col("transaction_amount") % 1000) == 0)
    )
```

#### Gold Layer (Analytics-Ready)

```python
@dlt.table(
    name="gold_customer_risk_profile",
    comment="Consolidated customer risk profile for AML monitoring"
)
def gold_customer_risk_profile():
    return (
        spark.sql("""
            SELECT 
                c.customer_id,
                c.customer_name,
                c.customer_type,
                c.onboarding_date,
                c.kyc_risk_rating,
                c.kyc_last_review_date,
                c.pep_status,
                c.sanctions_match_flag,
                
                -- Transaction behavior (rolling 90 days)
                COALESCE(t.total_transaction_count, 0) as txn_count_90d,
                COALESCE(t.total_transaction_amount, 0) as txn_amount_90d,
                COALESCE(t.cash_transaction_count, 0) as cash_txn_count_90d,
                COALESCE(t.wire_out_count, 0) as wire_out_count_90d,
                COALESCE(t.high_risk_country_txn_count, 0) as high_risk_country_txn_90d,
                
                -- Alerts and cases
                COALESCE(a.open_alert_count, 0) as open_alerts,
                COALESCE(a.sar_filed_count, 0) as historical_sars,
                
                -- Calculated risk score
                calculate_composite_risk_score(
                    c.kyc_risk_rating,
                    c.pep_status,
                    t.high_risk_country_txn_count,
                    a.sar_filed_count
                ) as composite_risk_score,
                
                current_timestamp() as profile_updated_at
            FROM silver_customer_360 c
            LEFT JOIN customer_transaction_aggregates t ON c.customer_id = t.customer_id
            LEFT JOIN customer_alert_history a ON c.customer_id = a.customer_id
        """)
    )
```

---

## 3. Data Model

### 3.1 Core Entities

#### Customer (Party)
```
customer_id (PK)
customer_type (INDIVIDUAL | BUSINESS | TRUST | FI)
legal_name
dba_name
tax_id_type
tax_id_hash
date_of_birth / incorporation_date
citizenship_countries[]
residence_country
occupation / industry_naics
employer / beneficial_owners[]
pep_status (NONE | DOMESTIC | FOREIGN | CLOSE_ASSOCIATE)
sanctions_match_flag
kyc_risk_rating (LOW | MEDIUM | HIGH | PROHIBITED)
kyc_last_review_date
customer_since_date
relationship_manager_id
```

#### Account
```
account_id (PK)
customer_id (FK)
account_type (CHECKING | SAVINGS | MONEY_MARKET | LOAN | INVESTMENT)
account_status (ACTIVE | DORMANT | CLOSED | FROZEN)
open_date
close_date
primary_currency
average_monthly_balance
expected_activity_profile
last_activity_date
```

#### Transaction
```
transaction_id (PK)
account_id (FK)
customer_id (FK)
transaction_type (CASH_DEPOSIT | CASH_WITHDRAWAL | WIRE_IN | WIRE_OUT | ACH | CHECK | CARD | INTERNAL_TRANSFER)
transaction_direction (CREDIT | DEBIT)
transaction_amount
transaction_currency
transaction_timestamp
originator_name
originator_account
originator_bank_id
originator_country
beneficiary_name
beneficiary_account
beneficiary_bank_id
beneficiary_country
transaction_purpose
channel (BRANCH | ATM | ONLINE | MOBILE | SWIFT)
branch_id
teller_id
is_structured_flag (derived)
```

#### Alert
```
alert_id (PK)
customer_id (FK)
scenario_id (FK)
alert_status (NEW | ASSIGNED | IN_REVIEW | ESCALATED | SAR_FILED | CLOSED_FP | CLOSED_NO_SAR)
alert_priority (LOW | MEDIUM | HIGH | CRITICAL)
alert_score
triggered_timestamp
assigned_to
assigned_timestamp
disposition_timestamp
disposition_reason
related_transaction_ids[]
escalated_to_case_id
```

#### Case
```
case_id (PK)
customer_id (FK)
case_type (INVESTIGATION | SAR_PREPARATION | ENHANCED_DUE_DILIGENCE)
case_status (OPEN | PENDING_INFO | UNDER_REVIEW | SAR_DRAFTED | SAR_FILED | CLOSED)
case_priority
opened_by
opened_timestamp
assigned_analyst
sar_filed_date
sar_confirmation_number
narrative_summary
supporting_documents[]
```

### 3.2 Reference Data

#### Country Risk Reference
```
iso_code (PK)
country_name
fatf_status (HIGH_RISK | MONITORED | STANDARD)
ofac_sanctioned
eu_high_risk_list
correspondent_banking_risk
tax_haven_flag
```

#### Scenario Configuration
```
scenario_id (PK)
scenario_name
scenario_category (STRUCTURING | RAPID_MOVEMENT | DORMANCY | HIGH_RISK_GEO | PEP | NETWORK)
scenario_description
rule_logic_sql
threshold_parameters (JSON)
risk_weight
is_active
effective_date
```

---

## 4. Risk Rating & Detection Scenarios

### 4.1 Customer Risk Rating Model

Customer risk ratings should be calculated using a weighted scoring approach:

**Risk Factors & Weights:**

| Factor Category | Factor | Weight | Values |
|----------------|--------|--------|--------|
| **Customer Type** | Entity Type | 15% | Individual=1, Business=2, Trust=3, FI=4, MSB=5 |
| **Geographic** | Residence Country | 20% | Low=1, Medium=2, High=3, FATF Blacklist=5 |
| **Product** | High-Risk Products | 10% | Standard=1, Private Banking=2, Trade Finance=3, Correspondent=4 |
| **Channel** | Delivery Channel | 10% | Branch=1, Online=2, Third-Party=3 |
| **PEP Status** | Political Exposure | 15% | None=0, Close Associate=3, Foreign=4, Domestic=5 |
| **Transaction Behavior** | Anomaly Score | 20% | ML-derived 0-100 |
| **Negative News** | Adverse Media | 10% | None=0, Minor=2, Major=4, Sanctions=5 |

```python
# MLflow model for customer risk scoring
import mlflow
from databricks.feature_store import FeatureStoreClient

fs = FeatureStoreClient()

# Feature engineering
customer_features = fs.create_training_set(
    df=training_labels,
    feature_lookups=[
        FeatureLookup(
            table_name="aml_feature_store.customer_transaction_features",
            feature_names=["txn_velocity_30d", "cash_ratio", "international_ratio"],
            lookup_key="customer_id"
        ),
        FeatureLookup(
            table_name="aml_feature_store.customer_network_features", 
            feature_names=["counterparty_risk_score", "network_density"],
            lookup_key="customer_id"
        )
    ]
)

# Model training with MLflow
with mlflow.start_run(run_name="customer_risk_model_v2"):
    model = XGBClassifier(
        objective='multi:softprob',
        num_class=4,  # LOW, MEDIUM, HIGH, CRITICAL
        max_depth=6,
        learning_rate=0.1
    )
    model.fit(X_train, y_train)
    
    # Log model
    mlflow.xgboost.log_model(
        model, 
        "customer_risk_model",
        registered_model_name="aml_customer_risk_classifier"
    )
```

### 4.2 AML Detection Scenarios

Based on your slides and industry standards, here are the key detection scenarios:

#### Category 1: Structuring / Smurfing
| Scenario ID | Name | Logic | Threshold |
|-------------|------|-------|-----------|
| STR-001 | Cash Deposit Structuring | Multiple cash deposits just below CTR threshold | ≥3 deposits of $9,000-$9,999 within 7 days |
| STR-002 | Cash Withdrawal Structuring | Multiple cash withdrawals below threshold | ≥3 withdrawals of $9,000-$9,999 within 7 days |
| STR-003 | Multi-Branch Structuring | Deposits across multiple branches same day | ≥2 cash deposits at different branches, total >$10K |

```sql
-- Example: STR-001 Cash Deposit Structuring
CREATE OR REPLACE TABLE aml_gold.scenario_str001_hits AS
SELECT 
    customer_id,
    COUNT(*) as deposit_count,
    SUM(transaction_amount) as total_amount,
    COLLECT_LIST(transaction_id) as related_transactions,
    MIN(transaction_timestamp) as first_transaction,
    MAX(transaction_timestamp) as last_transaction,
    'STR-001' as scenario_id,
    85 as base_score,  -- High confidence structuring indicator
    current_timestamp() as detection_timestamp
FROM aml_silver.transactions_enriched
WHERE transaction_type = 'CASH_DEPOSIT'
  AND transaction_amount BETWEEN 9000 AND 9999
  AND transaction_timestamp >= current_date() - INTERVAL 7 DAYS
GROUP BY customer_id
HAVING COUNT(*) >= 3;
```

#### Category 2: Rapid Movement
| Scenario ID | Name | Logic | Threshold |
|-------------|------|-------|-----------|
| RM-001 | Rapid Wire In-Out | Large wires in and out with minimal retention | Inflow + Outflow >$50K in 24hrs, ending balance <5% of inflow |
| RM-002 | Deposit-Withdrawal Cycling | Funds deposited and withdrawn same day | >$10K deposited and >90% withdrawn within 24hrs |
| RM-003 | Layering Pattern | Multiple transfers through intermediary accounts | ≥3 hops through internal accounts within 48hrs |

#### Category 3: Behavioral Anomalies
| Scenario ID | Name | Logic | Threshold |
|-------------|------|-------|-----------|
| BA-001 | Dormant Account Reactivation | Sudden activity after long dormancy | No activity 12+ months, then >$20K in 7 days |
| BA-002 | Transaction Velocity Spike | Unusual transaction volume | >3x average monthly transactions |
| BA-003 | Out-of-Pattern Activity | Activity inconsistent with profile | ML anomaly score >95th percentile |

#### Category 4: High-Risk Geography
| Scenario ID | Name | Logic | Threshold |
|-------------|------|-------|-----------|
| GEO-001 | FATF High-Risk Country Wire | Wire to/from FATF blacklisted country | Any wire >$10K to/from blacklisted jurisdiction |
| GEO-002 | Tax Haven Transfers | Transfers to financial secrecy jurisdictions | >$25K to tax haven without business justification |
| GEO-003 | Sanctioned Country Nexus | Transactions with OFAC-sanctioned regions | Any transaction with nexus to sanctioned country |

#### Category 5: Entity/Network
| Scenario ID | Name | Logic | Threshold |
|-------------|------|-------|-----------|
| ENT-001 | PEP Transaction | Transaction involving Politically Exposed Person | Any transaction >$5K involving PEP |
| ENT-002 | Shell Company Indicators | Transactions with apparent shell companies | Multiple indicators (nominee directors, registered agent address, etc.) |
| ENT-003 | Related Account Network | Suspicious patterns across linked accounts | Graph analysis detecting unusual network structures |

### 4.3 Alert Scoring & Prioritization

Combine scenario hits with contextual risk factors:

```sql
CREATE OR REPLACE TABLE aml_gold.alerts AS
SELECT 
    uuid() as alert_id,
    s.customer_id,
    s.scenario_id,
    sc.scenario_name,
    sc.scenario_category,
    
    -- Base score from scenario
    s.base_score,
    
    -- Risk multipliers
    CASE WHEN c.kyc_risk_rating = 'HIGH' THEN 1.3 
         WHEN c.kyc_risk_rating = 'MEDIUM' THEN 1.1 
         ELSE 1.0 END as kyc_multiplier,
    CASE WHEN c.pep_status != 'NONE' THEN 1.4 ELSE 1.0 END as pep_multiplier,
    CASE WHEN c.historical_sars > 0 THEN 1.5 ELSE 1.0 END as sar_history_multiplier,
    CASE WHEN c.sanctions_match_flag THEN 2.0 ELSE 1.0 END as sanctions_multiplier,
    
    -- Final prioritized score
    ROUND(s.base_score 
        * kyc_multiplier 
        * pep_multiplier 
        * sar_history_multiplier 
        * sanctions_multiplier, 0) as final_score,
    
    -- Priority assignment
    CASE 
        WHEN final_score >= 150 OR c.sanctions_match_flag THEN 'CRITICAL'
        WHEN final_score >= 100 THEN 'HIGH'
        WHEN final_score >= 70 THEN 'MEDIUM'
        ELSE 'LOW'
    END as alert_priority,
    
    'NEW' as alert_status,
    s.related_transactions,
    s.detection_timestamp as triggered_timestamp,
    current_timestamp() as created_at

FROM scenario_hits_combined s
JOIN aml_gold.customer_risk_profile c ON s.customer_id = c.customer_id
JOIN aml_ref.scenario_config sc ON s.scenario_id = sc.scenario_id
WHERE sc.is_active = true;
```

---

## 5. Dashboard & KPIs

### 5.1 Executive Dashboard

**Purpose:** Provide leadership visibility into AML program health and operational efficiency.

**Key Visualizations:**

1. **Alert Volume Trend** (Line chart)
   - Daily/weekly alert generation by priority
   - Comparison to prior period

2. **Alert Disposition Funnel** (Funnel chart)
   - New → Assigned → Reviewed → SAR Filed / Closed
   - Conversion rates at each stage

3. **False Positive Rate** (KPI card + trend)
   - Current FP rate vs. target
   - Trend over time by scenario

4. **SAR Filing Metrics** (KPI cards)
   - SARs filed MTD/YTD
   - Average days to file
   - SARs by category

5. **Scenario Effectiveness Matrix** (Heatmap)
   - Scenarios by alert volume vs. SAR conversion rate
   - Identify high-volume/low-conversion scenarios for tuning

### 5.2 Operations Dashboard

**Purpose:** Enable AML operations managers to monitor team workload and queue health.

**Key Visualizations:**

1. **Alert Queue by Priority** (Stacked bar)
   - Critical/High/Medium/Low by status
   - Aging buckets (0-1 day, 1-3 days, 3-7 days, 7+ days)

2. **Analyst Workload Distribution** (Bar chart)
   - Open cases per analyst
   - Cases closed this week per analyst

3. **Average Handle Time** (KPI cards by scenario)
   - Time from assignment to disposition
   - Benchmark vs. target SLA

4. **Alert Aging Report** (Table)
   - Alerts approaching SLA breach
   - Days in current status

5. **Scenario Hit Distribution** (Pie/Donut)
   - Alerts by scenario category
   - Identify dominant patterns

### 5.3 Analyst Triage Dashboard

**Purpose:** First screen analysts see - prioritized work queue with drill-down capability.

**Key Components:**

1. **My Assigned Alerts** (Filterable table)
   - Alert ID, Customer Name, Scenario, Priority, Score, Age
   - Click-through to investigation

2. **High Priority Queue** (Card list)
   - Critical and High priority unassigned alerts
   - Key risk indicators visible

3. **Customer Risk Summary** (On selection)
   - Customer profile snapshot
   - Recent transaction summary
   - Historical alert/SAR history

4. **Quick Stats** (KPI row)
   - My open alerts
   - My closed this week
   - Avg. disposition time

### 5.4 KPI Definitions

| KPI | Formula | Target | Frequency |
|-----|---------|--------|-----------|
| **Alert Generation Rate** | Alerts Generated / Total Transactions | <0.5% | Daily |
| **False Positive Rate** | (Closed as FP) / (Total Dispositioned) | <85% | Weekly |
| **SAR Conversion Rate** | SARs Filed / Total Alerts Reviewed | >5% | Monthly |
| **Average Investigation Time** | Avg(Disposition Time - Assigned Time) | <4 hours | Weekly |
| **Alert Aging (% >3 days)** | Alerts >3 days old / Open Alerts | <15% | Daily |
| **Analyst Productivity** | Cases Closed / Analyst / Day | >8 | Weekly |
| **Detection Coverage** | Known Typologies Detected / Total Typologies | >90% | Quarterly |
| **Model Drift (PSI)** | Population Stability Index on risk model | <0.1 | Monthly |

---

## 6. AI-Assisted Investigation

### 6.1 Current Multi-Agent Architecture

Your existing blog demonstrates a three-component system:

1. **Genie Space** (Structured Data Agent)
   - Queries transaction tables via natural language
   - Pre-configured with AML-specific SQL expressions

2. **Knowledge Assistant** (Policy Agent)
   - RAG over AML policies and red flag indicators
   - Retrieves relevant compliance guidance

3. **Multi-Agent Supervisor**
   - Orchestrates between Genie and Knowledge Assistant
   - Synthesizes findings into investigation narratives

### 6.2 Recommended Enhancements for Production

#### Enhancement 1: Case Context Tool

Add a tool that retrieves full case context when an analyst begins investigation:

```python
@tool
def get_case_context(alert_id: str) -> dict:
    """Retrieves comprehensive context for an alert investigation."""
    return {
        "alert_details": get_alert_by_id(alert_id),
        "customer_profile": get_customer_360(alert.customer_id),
        "triggered_transactions": get_related_transactions(alert.transaction_ids),
        "historical_alerts": get_customer_alert_history(alert.customer_id),
        "previous_sars": get_customer_sar_history(alert.customer_id),
        "related_entities": get_entity_relationships(alert.customer_id),
        "kyc_documents": get_kyc_document_summary(alert.customer_id)
    }
```

#### Enhancement 2: Investigation Workflow Actions

Enable the agent to take workflow actions:

```python
@tool
def update_alert_status(alert_id: str, new_status: str, notes: str) -> str:
    """Updates alert status with analyst notes."""
    # Validate status transition
    # Update in case management system
    # Log audit trail
    pass

@tool  
def request_additional_information(alert_id: str, request_type: str, details: str) -> str:
    """Creates a request for additional information (e.g., from relationship manager)."""
    pass

@tool
def draft_sar_narrative(alert_id: str) -> str:
    """Generates a draft SAR narrative based on investigation findings."""
    pass
```

#### Enhancement 3: Entity Network Visualization

Integrate graph analysis for entity relationships:

```python
@tool
def analyze_entity_network(customer_id: str, depth: int = 2) -> dict:
    """Analyzes the network of related entities for a customer."""
    # Query graph database or use GraphX
    # Return network visualization data
    # Identify suspicious patterns (circular flows, shell company indicators)
    pass
```

### 6.3 Genie Space Configuration for AML

**Tables to Include:**

- `aml_gold.customer_risk_profile`
- `aml_gold.alerts`
- `aml_silver.transactions_enriched`
- `aml_gold.cases`
- `aml_ref.country_risk`
- `aml_ref.scenario_config`

**Sample SQL Expressions:**

```sql
-- High-risk transactions
CREATE SQL EXPRESSION high_risk_transactions AS
SELECT * FROM aml_silver.transactions_enriched
WHERE is_high_risk_country = true 
   OR transaction_amount > 50000 
   OR is_round_amount = true;

-- Structuring candidates
CREATE SQL EXPRESSION potential_structuring AS
SELECT customer_id, 
       COUNT(*) as deposit_count,
       SUM(transaction_amount) as total_amount
FROM aml_silver.transactions_enriched
WHERE transaction_type = 'CASH_DEPOSIT'
  AND transaction_amount BETWEEN 8000 AND 9999
  AND transaction_timestamp >= current_date() - INTERVAL 7 DAYS
GROUP BY customer_id
HAVING COUNT(*) >= 2;

-- Customer 360 view
CREATE SQL EXPRESSION customer_360 AS
SELECT 
    c.*,
    COALESCE(a.open_alert_count, 0) as current_open_alerts,
    COALESCE(a.sar_count, 0) as historical_sars
FROM aml_gold.customer_risk_profile c
LEFT JOIN (
    SELECT customer_id, 
           COUNT(CASE WHEN alert_status IN ('NEW','ASSIGNED','IN_REVIEW') THEN 1 END) as open_alert_count,
           COUNT(CASE WHEN alert_status = 'SAR_FILED' THEN 1 END) as sar_count
    FROM aml_gold.alerts 
    GROUP BY customer_id
) a ON c.customer_id = a.customer_id;
```

**Sample Instructions for Genie:**

```
This Genie Space supports AML (Anti-Money Laundering) investigations.

Key terminology:
- CTR: Currency Transaction Report, required for cash transactions >$10,000
- SAR: Suspicious Activity Report, filed for suspected money laundering
- Structuring: Breaking transactions into smaller amounts to avoid reporting thresholds
- PEP: Politically Exposed Person
- FATF: Financial Action Task Force, sets international AML standards

When asked about suspicious transactions:
1. Consider transactions involving high-risk countries (FATF blacklist)
2. Look for patterns of structuring (multiple transactions $9,000-$9,999)
3. Check for rapid movement of funds (in/out within 24-48 hours)
4. Review customer risk rating and PEP status

Currency is in USD unless otherwise specified.
```

---

## 7. Databricks App Architecture

### 7.1 Application Structure

```
aml-investigation-app/
├── app.py                 # Main Gradio/Streamlit application
├── pages/
│   ├── dashboard.py       # Operational dashboard (embedded Lakeview)
│   ├── queue.py           # Alert queue and triage
│   ├── investigation.py   # AI-assisted investigation chat
│   └── case_management.py # Case details and SAR workflow
├── components/
│   ├── customer_card.py   # Customer profile component
│   ├── transaction_table.py
│   ├── alert_details.py
│   └── chat_interface.py  # Genie/Agent integration
├── utils/
│   ├── databricks_client.py
│   ├── agent_client.py
│   └── auth.py
└── static/
    └── styles.css
```

### 7.2 User Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AML INVESTIGATION APP                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │  Dashboard   │───▶│  Alert Queue │───▶│Investigation │                   │
│  │   (Genie)    │    │   (Triage)   │    │   (Chat)     │                   │
│  └──────────────┘    └──────────────┘    └──────────────┘                   │
│         │                   │                   │                            │
│         │                   │                   │                            │
│         ▼                   ▼                   ▼                            │
│  ┌──────────────────────────────────────────────────────┐                   │
│  │                  Case Management                       │                   │
│  │  • Update status    • Add notes    • Draft SAR        │                   │
│  │  • Request info     • Escalate     • File SAR         │                   │
│  └──────────────────────────────────────────────────────┘                   │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 7.3 Key App Components

#### Dashboard Page (Genie Integration)

```python
# pages/dashboard.py
import gradio as gr
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.dashboards import GenieAPI

def create_dashboard_page():
    """
    Embeds Lakeview dashboard and provides Genie chat for ad-hoc queries.
    """
    with gr.Column():
        # Embedded Lakeview Dashboard
        gr.HTML("""
            <iframe 
                src="https://your-workspace.cloud.databricks.com/sql/dashboards/aml-operations" 
                width="100%" 
                height="600px"
            ></iframe>
        """)
        
        # Genie Chat for discovery
        gr.Markdown("### Ask questions about your AML data")
        genie_chat = gr.Chatbot(label="Genie Assistant")
        genie_input = gr.Textbox(placeholder="e.g., Show me high-priority alerts from this week")
        genie_submit = gr.Button("Ask")
        
        genie_submit.click(
            fn=query_genie_space,
            inputs=[genie_input, genie_chat],
            outputs=[genie_chat]
        )
    
    return dashboard_page
```

#### Investigation Page (Multi-Agent Chat)

```python
# pages/investigation.py
import gradio as gr
from utils.agent_client import AMLAgentClient

def create_investigation_page(alert_id: str):
    """
    AI-assisted investigation interface using Multi-Agent system.
    """
    agent = AMLAgentClient()
    
    # Load alert context
    context = agent.get_case_context(alert_id)
    
    with gr.Row():
        # Left panel: Case context
        with gr.Column(scale=1):
            gr.Markdown(f"## Alert {alert_id}")
            customer_card = create_customer_card(context["customer_profile"])
            transaction_table = create_transaction_table(context["triggered_transactions"])
            alert_history = create_alert_history(context["historical_alerts"])
        
        # Right panel: Investigation chat
        with gr.Column(scale=2):
            gr.Markdown("## Investigation Assistant")
            
            # Pre-populate with alert summary
            initial_message = agent.generate_alert_summary(context)
            
            chatbot = gr.Chatbot(
                value=[(None, initial_message)],
                label="Investigation Chat"
            )
            msg_input = gr.Textbox(
                placeholder="Ask about this case, e.g., 'What other transactions did this customer make to high-risk countries?'"
            )
            
            with gr.Row():
                submit_btn = gr.Button("Send", variant="primary")
                clear_btn = gr.Button("Clear")
            
            # Action buttons
            gr.Markdown("### Quick Actions")
            with gr.Row():
                gr.Button("Mark as False Positive")
                gr.Button("Escalate to Case")
                gr.Button("Draft SAR Narrative")
    
    return investigation_page
```

### 7.4 Integration Points

| Component | Integration Method | Notes |
|-----------|-------------------|-------|
| Lakeview Dashboard | Embed via iframe | Use dashboard sharing with SSO |
| Genie Space | REST API / SDK | `databricks.sdk.service.dashboards.GenieAPI` |
| Multi-Agent | Agent Bricks serving endpoint | REST API to deployed agent |
| Alert Updates | SQL Warehouse API | Direct table updates with audit logging |
| Case Management | Unity Catalog tables | CRUD operations via SQL |
| SAR Filing | External API integration | Connect to FinCEN filing system |

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)
- [ ] Set up Unity Catalog schema (`aml_bronze`, `aml_silver`, `aml_gold`, `aml_ref`)
- [ ] Implement core DLT pipelines for transaction ingestion
- [ ] Create reference data tables (country risk, scenario config)
- [ ] Build silver layer enrichment logic

### Phase 2: Detection (Weeks 5-8)
- [ ] Implement 5 core detection scenarios (STR-001, RM-001, BA-001, GEO-001, ENT-001)
- [ ] Build alert scoring and prioritization logic
- [ ] Create customer risk rating model (MLflow)
- [ ] Set up feature store for real-time scoring

### Phase 3: Dashboard (Weeks 9-10)
- [ ] Build Lakeview operational dashboard
- [ ] Create analyst triage views
- [ ] Implement KPI tracking tables and visualizations
- [ ] Set up alert workflows

### Phase 4: AI Investigation (Weeks 11-14)
- [ ] Configure Genie Space with AML tables and expressions
- [ ] Set up Knowledge Assistant with policy documents
- [ ] Deploy Multi-Agent Supervisor
- [ ] Test investigation workflows

### Phase 5: Application (Weeks 15-18)
- [ ] Build Databricks App framework
- [ ] Integrate dashboard, queue, and investigation pages
- [ ] Implement action handlers (status updates, SAR drafting)
- [ ] User acceptance testing

### Phase 6: Production (Weeks 19-20)
- [ ] Security review and penetration testing
- [ ] Performance optimization
- [ ] Documentation and training
- [ ] Production deployment

---

## 9. Appendix

### A. Sample Data Generators

For demo purposes, synthetic data can be generated using Databricks Labs Data Generator (dbldatagen):

```python
import dbldatagen as dg

# Transaction data generator
transaction_spec = (
    dg.DataGenerator(spark, name="transactions", rows=1_000_000)
    .withColumn("transaction_id", "string", template=r"TXN-\d{12}")
    .withColumn("customer_id", "string", template=r"CUST-\d{8}")
    .withColumn("transaction_type", "string", 
                values=["CASH_DEPOSIT", "WIRE_OUT", "WIRE_IN", "ACH", "CARD"],
                weights=[0.3, 0.1, 0.1, 0.3, 0.2])
    .withColumn("transaction_amount", "decimal(12,2)", 
                minValue=10, maxValue=500000, distribution="normal")
    .withColumn("transaction_timestamp", "timestamp",
                begin="2024-01-01", end="2024-12-31")
    .withColumn("country_code", "string",
                values=["US", "GB", "CH", "SG", "RU", "IR", "CN"],
                weights=[0.6, 0.1, 0.1, 0.1, 0.05, 0.02, 0.03])
)

transactions_df = transaction_spec.build()
```

### B. Regulatory References

- **FinCEN**: Bank Secrecy Act (BSA) requirements
- **FATF**: 40 Recommendations on Money Laundering
- **FFIEC**: BSA/AML Examination Manual
- **OCC**: Risk Management Guidance for AML

### C. External Data Vendor Integration

| Vendor | Data Type | Integration Method |
|--------|-----------|-------------------|
| LexisNexis | Identity verification, risk scores | REST API |
| Thomson Reuters World-Check | PEP/Sanctions screening | SFTP/API |
| Dow Jones Risk & Compliance | Adverse media, sanctions | API |
| Refinitiv | Entity data, ownership | API |
| Experian | Credit/identity data | Batch/API |

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Dec 2025 | Kat Savchyn | Initial architecture document |
