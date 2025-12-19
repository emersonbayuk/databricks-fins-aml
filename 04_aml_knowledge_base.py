# Databricks notebook source
# MAGIC %md
# MAGIC # AML Knowledge Base - Document Generation & Regulatory References
# MAGIC
# MAGIC This notebook builds the Knowledge Assistant document corpus with two types of content:
# MAGIC
# MAGIC **1. Regulatory & Policy Documents (Downloaded Automatically)**
# MAGIC - FFIEC BSA/AML Examination Manual sections
# MAGIC - FinCEN SAR/CTR filing guidance
# MAGIC - OFAC compliance frameworks
# MAGIC - Sample institution AML policies
# MAGIC
# MAGIC **2. Customer-Specific Documents (Generated Synthetically)**
# MAGIC - SAR Narratives (linked to customers with filed SARs)
# MAGIC - Investigation Case Notes
# MAGIC - EDD Memoranda
# MAGIC - Adverse Media Screening Results
# MAGIC - Customer Correspondence Logs
# MAGIC
# MAGIC **Folder Structure:**
# MAGIC ```
# MAGIC knowledge_base/
# MAGIC ├── policies_and_regulations/
# MAGIC │   ├── ffiec/           # BSA/AML exam manual, red flags, CIP
# MAGIC │   ├── fincen/          # SAR, CTR, CDD guidance
# MAGIC │   ├── ofac/            # Sanctions compliance framework
# MAGIC │   └── internal/        # Institution AML policies
# MAGIC ├── sar_narratives/      # Customer SAR filings
# MAGIC ├── case_notes/          # Investigation notes
# MAGIC ├── edd_memos/           # Enhanced due diligence
# MAGIC ├── adverse_media/       # Media screening results
# MAGIC └── correspondence/      # Customer interaction logs
# MAGIC ```

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

CATALOG = "fins_aml"
SCHEMA = "data_generation"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/knowledge_base"

# Create volume for knowledge base documents
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.knowledge_base")

print(f"Knowledge base volume: {VOLUME_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part 1: Download Regulatory & Policy Documents

# COMMAND ----------

import requests
import os

# =============================================================================
# REGULATORY DOCUMENTS TO DOWNLOAD
# =============================================================================

REGULATORY_DOCS = {
    # FFIEC / Federal Regulator Guidance
    "ffiec": [
        {
            "name": "appendix_f_red_flags.pdf",
            "url": "https://bsaaml.ffiec.gov/docs/manual/10_Appendices/07.pdf",
            "description": "FFIEC BSA/AML Red Flags for Money Laundering"
        },
        {
            "name": "ffiec_cip_manual.pdf",
            "url": "https://www.fdic.gov/news/financial-institution-letters/2021/fil21012b.pdf",
            "description": "FFIEC Customer Identification Program Manual"
        }
    ],
    
    # FinCEN Guidance
    "fincen": [
        {
            "name": "sar_narrative_guidance.pdf",
            "url": "https://www.irs.gov/pub/irs-tege/itg_sarc_prep.pdf",
            "description": "FinCEN SAR Narrative Guidance"
        },
        {
            "name": "ctr_reference_guide.pdf",
            "url": "https://www.fincen.gov/system/files/shared/CTRPamphlet.pdf",
            "description": "CTR Reference Guide"
        },
        {
            "name": "cdd_rule_faqs.pdf",
            "url": "https://www.fincen.gov/system/files/2018-04/FinCEN_Guidance_CDD_FAQ_FINAL_508_2.pdf",
            "description": "Customer Due Diligence Rule FAQs"
        },
        {
            "name": "cdd_beneficial_ownership_faqs.pdf",
            "url": "https://www.fincen.gov/system/files/2016-09/FAQs_for_CDD_Final_Rule_(7_15_16).pdf",
            "description": "Beneficial Ownership FAQs"
        }
    ],
    
    # OFAC / Sanctions
    "ofac": [
        {
            "name": "compliance_framework.pdf",
            "url": "https://ofac.treasury.gov/media/16331/download?inline=",
            "description": "OFAC Compliance Framework"
        },
        {
            "name": "instant_payments_guidance.pdf",
            "url": "https://ofac.treasury.gov/system/files/126/instant_payment_systems_compliance_guidance_brochure.pdf",
            "description": "OFAC Instant Payments Guidance"
        }
    ],
    
    # Sample Institution Policies
    "internal": [
        {
            "name": "vls_finance_aml_policy.pdf",
            "url": "https://www.vlsfinance.com/wp-content/uploads/2022/01/Anti-Money-Laundering-Policy.pdf",
            "description": "VLS Finance AML Policy"
        },
        {
            "name": "jab_aml_policy.pdf",
            "url": "https://www.jabholco.com/img/pdf/JAB_AML_Policy.pdf",
            "description": "JAB Holding AML Policy with Red Flags"
        },
        {
            "name": "hrw_aml_policy.pdf",
            "url": "https://www.hrw.org/sites/default/files/news_attachments/hrw-anti-money-laundering-policy-december2016.pdf",
            "description": "HRW AML Policy"
        },
        {
            "name": "multichoice_aml_policy.pdf",
            "url": "https://investors.multichoice.com/pdf/policies-and-charters/2024/mcg-anti-money-laundering-policy.pdf",
            "description": "MultiChoice AML Policy 2024"
        }
    ]
}

# COMMAND ----------

def download_regulatory_docs():
    """Download regulatory documents from public sources."""
    
    # Use direct filesystem path for Volumes (not dbfs:/)
    base_path = f"{VOLUME_PATH}/policies_and_regulations"
    
    # Create directory structure using os.makedirs (works with Volume paths)
    for category in ["ffiec", "fincen", "ofac", "internal"]:
        dir_path = f"{base_path}/{category}"
        os.makedirs(dir_path, exist_ok=True)
        print(f"Created directory: {dir_path}")
    
    download_results = []
    
    for category, docs in REGULATORY_DOCS.items():
        print(f"\n{'='*60}")
        print(f"Downloading {category.upper()} documents...")
        print(f"{'='*60}")
        
        for doc in docs:
            try:
                print(f"\n  Downloading: {doc['name']}")
                
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = requests.get(doc["url"], timeout=60, allow_redirects=True, headers=headers)
                response.raise_for_status()
                
                # Write directly to Volume path (no dbutils.fs.cp needed)
                filepath = f"{base_path}/{category}/{doc['name']}"
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                
                size_kb = len(response.content) / 1024
                download_results.append({
                    "category": category,
                    "file": doc["name"],
                    "description": doc["description"],
                    "status": "Success",
                    "size_kb": round(size_kb, 1)
                })
                print(f"  Saved ({size_kb:.1f} KB)")
                
            except Exception as e:
                download_results.append({
                    "category": category,
                    "file": doc["name"],
                    "description": doc["description"],
                    "status": f"Failed: {str(e)[:40]}",
                    "size_kb": 0
                })
                print(f"  Failed: {str(e)[:50]}")
    
    return download_results

print("=" * 70)
print("DOWNLOADING REGULATORY & POLICY DOCUMENTS")
print("=" * 70)
results = download_regulatory_docs()

# COMMAND ----------

# Display results
import pandas as pd
results_df = pd.DataFrame(results)
display(results_df)

success_count = len([r for r in results if r["status"] == "Success"])
print(f"\nTotal: {success_count}/{len(results)} documents downloaded")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Part 2: Generate Synthetic Customer Documents

# COMMAND ----------

from datetime import datetime, timedelta
from faker import Faker
import random

fake = Faker()
Faker.seed(42)
random.seed(42)

# Load reference data
customers_df = spark.table(f"{CATALOG}.{SCHEMA}.customers").toPandas()
transactions_df = spark.table(f"{CATALOG}.{SCHEMA}.transactions").toPandas()
sars_df = spark.table(f"{CATALOG}.{SCHEMA}.sar_filings").toPandas()
cases_df = spark.table(f"{CATALOG}.{SCHEMA}.cases").toPandas()
alerts_df = spark.table(f"{CATALOG}.{SCHEMA}.alerts").toPandas()

print(f"Loaded: {len(customers_df)} customers, {len(sars_df)} SARs, {len(cases_df)} cases")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 2.1 Generate SAR Narratives

# COMMAND ----------

def generate_sar_narrative(customer_info, sar_info, transactions):
    """Generate a realistic SAR narrative."""
    
    customer_id = customer_info["customer_id"]
    customer_name = f"{customer_info.get('first_name', '')} {customer_info.get('last_name', '')}".strip()
    if not customer_name:
        customer_name = customer_info.get("business_name", "Unknown Entity")
    
    activity_type = sar_info["activity_type"]
    amount_involved = sar_info["amount_involved"]
    
    txn_summary = []
    for txn in transactions[:10]:
        txn_summary.append(f"- {str(txn['transaction_date'])[:10]}: {txn['transaction_type'].replace('_', ' ').title()} of ${txn['amount']:,.2f}")
    
    narrative = f"""SAR NARRATIVE
================================================================================

SAR ID: {sar_info['sar_id']}
FinCEN DCN: {sar_info['fincen_dcn']}
Filing Date: {sar_info['filing_date']}
Filing Type: {sar_info['filing_type'].upper()}

SUBJECT INFORMATION:
Name: {customer_name}
Customer ID: {customer_id}
Address: {customer_info.get('address_city', '')}, {customer_info.get('address_state', '')}
Occupation: {customer_info.get('occupation', 'N/A')}

ACTIVITY SUMMARY:
Activity Type: {activity_type}
Activity Period: {sar_info['activity_start']} to {sar_info['activity_end']}
Total Amount: ${amount_involved:,.2f}

================================================================================
NARRATIVE
================================================================================

ABC National Bank files this SAR for suspected {activity_type.lower()} by {customer_name}.

Suspicious transactions identified:
{chr(10).join(txn_summary)}

"""

    if "structuring" in activity_type.lower():
        narrative += """
ANALYSIS: Pattern consistent with structuring per FFIEC BSA/AML Appendix F:
- Multiple deposits just under $10,000 CTR threshold
- Deposits at multiple branches
- Activity inconsistent with stated income
"""
    elif "rapid" in activity_type.lower():
        narrative += """
ANALYSIS: Rapid fund movement consistent with layering:
- Funds retained less than 48 hours
- Wire recipients in multiple jurisdictions
- No apparent business purpose
"""
    elif "geo" in activity_type.lower():
        narrative += """
ANALYSIS: High-risk geography transactions per OFAC guidance:
- Transfers to FATF-deficient jurisdictions
- Customer unable to explain business purpose
- OFAC screening flagged potential concerns
"""

    narrative += f"""
================================================================================
ACTIONS TAKEN
================================================================================
- Alert escalated to BSA/AML team
- Enhanced due diligence conducted
- Account placed under monitoring

Prepared by: {random.choice(['Sarah Chen', 'Michael Rodriguez', 'Emily Thompson'])}, AML Analyst
Reviewed by: {random.choice(['James Wong', 'Lisa Martinez'])}, BSA Officer
"""
    
    return narrative

# Generate SAR narratives
sar_dir = f"{VOLUME_PATH}/sar_narratives"
os.makedirs(sar_dir, exist_ok=True)

sar_count = 0
for _, sar in sars_df.iterrows():
    customer = customers_df[customers_df["customer_id"] == sar["customer_id"]]
    if customer.empty:
        continue
    
    customer = customer.iloc[0].to_dict()
    cust_txns = transactions_df[transactions_df["customer_id"] == sar["customer_id"]].to_dict('records')
    
    narrative = generate_sar_narrative(customer, sar.to_dict(), cust_txns)
    filename = f"SAR_{sar['fincen_dcn']}_customer_{sar['customer_id']:04d}.txt"
    
    with open(f"{sar_dir}/{filename}", 'w') as f:
        f.write(narrative)
    sar_count += 1

print(f"Generated {sar_count} SAR narratives")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 2.2 Generate Case Notes

# COMMAND ----------

def generate_case_notes(case_info, customer_info, alert_info):
    """Generate investigation case notes."""
    
    customer_name = f"{customer_info.get('first_name', '')} {customer_info.get('last_name', '')}".strip() or "Unknown"
    
    notes = f"""INVESTIGATION CASE NOTES
================================================================================

Case ID: {case_info['case_id']}
Alert ID: {alert_info.get('alert_id', 'N/A')}
Customer: {customer_name} (ID: {customer_info['customer_id']})
Scenario: {alert_info.get('scenario_name', 'Unknown')}
Priority: {case_info['priority'].upper()}
Status: {case_info['case_status'].replace('_', ' ').title()}

Assigned: {case_info['assigned_analyst']}
Supervisor: {case_info['supervisor']}
Opened: {case_info['open_date']}

================================================================================
TIMELINE
================================================================================

[{case_info['open_date']}] CASE OPENED
- Alert score: {alert_info.get('alert_score', 'N/A')}
- Flagged amount: ${alert_info.get('total_amount', 0):,.2f}

[+2 hours] INITIAL REVIEW
- Risk rating: {customer_info.get('risk_rating', 'N/A').upper()}
- KYC status: {customer_info.get('kyc_status', 'N/A')}
- PEP: {'Yes' if customer_info.get('pep_flag') else 'No'}

================================================================================
AI ASSISTANT QUERIES
================================================================================

Query: "Red flags for {alert_info.get('scenario_name', 'this scenario')}?"
- Agent: Knowledge Assistant
- Source: FFIEC Appendix F, JAB AML Policy

Query: "Prior SARs for customer {customer_info['customer_id']}?"
- Agent: Genie
- Result: {random.choice(['None', '1 prior SAR', 'Multiple alerts'])}

================================================================================
STATUS
================================================================================

Disposition: {case_info.get('disposition', 'Pending')}
SAR Required: {'Yes' if case_info.get('sar_required') else 'TBD'}

Updated: {datetime.now().strftime('%Y-%m-%d')}
"""
    return notes

# Generate case notes
case_dir = f"{VOLUME_PATH}/case_notes"
os.makedirs(case_dir, exist_ok=True)

case_count = 0
for _, case in cases_df.iterrows():
    customer = customers_df[customers_df["customer_id"] == case["customer_id"]]
    alert = alerts_df[alerts_df["alert_id"] == case["alert_id"]]
    if customer.empty:
        continue
    
    notes = generate_case_notes(case.to_dict(), customer.iloc[0].to_dict(), 
                                alert.iloc[0].to_dict() if not alert.empty else {})
    filename = f"case_{case['case_id']:04d}_customer_{case['customer_id']:04d}.txt"
    
    with open(f"{case_dir}/{filename}", 'w') as f:
        f.write(notes)
    case_count += 1

print(f"Generated {case_count} case notes")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 2.3 Generate EDD Memoranda

# COMMAND ----------

def generate_edd_memo(customer_info, transactions):
    """Generate EDD memorandum."""
    
    customer_name = f"{customer_info.get('first_name', '')} {customer_info.get('last_name', '')}".strip() or "Unknown"
    review_date = fake.date_between(start_date="-90d", end_date="today")
    
    memo = f"""ENHANCED DUE DILIGENCE MEMORANDUM
================================================================================

Customer: {customer_name} (ID: {customer_info['customer_id']})
Type: {customer_info.get('customer_type', 'Individual').title()}
Risk Rating: {customer_info.get('risk_rating', 'N/A').upper()}
Review Date: {review_date}

================================================================================
SOURCE OF FUNDS
================================================================================

Occupation: {customer_info.get('occupation', 'N/A')}
Annual Income: ${customer_info.get('annual_income', 0):,.0f}
Verification: {random.choice(['Verified', 'Pending', 'Documented'])}

================================================================================
TRANSACTION ANALYSIS (90 DAYS)
================================================================================

Total Volume: ${sum(t.get('amount', 0) for t in transactions):,.2f}
Transaction Count: {len(transactions)}

================================================================================
SCREENING
================================================================================

OFAC: {random.choice(['Clear', 'Clear', 'Reviewed - Clear'])}
PEP: {'Match - Documented' if customer_info.get('pep_flag') else 'Clear'}
Adverse Media: {random.choice(['Clear', 'Clear', 'Minor - Non-material'])}

================================================================================
RECOMMENDATION
================================================================================

{random.choice([
    'MAINTAIN current risk rating. No action required.',
    'UPGRADE to HIGH risk. Enhanced monitoring recommended.',
    'REQUEST additional documentation within 30 days.'
])}

Next Review: {(review_date + timedelta(days=random.choice([90, 180, 365]))).strftime('%Y-%m-%d')}

Prepared by: {random.choice(['Sarah Chen', 'Michael Rodriguez'])}, AML Analyst
"""
    return memo

# Generate EDD memos
edd_dir = f"{VOLUME_PATH}/edd_memos"
os.makedirs(edd_dir, exist_ok=True)

edd_count = 0
for _, customer in customers_df.iterrows():
    if customer["risk_rating"] == "high" or (customer["risk_rating"] == "medium" and random.random() < 0.3):
        cust_txns = transactions_df[transactions_df["customer_id"] == customer["customer_id"]].to_dict('records')
        memo = generate_edd_memo(customer.to_dict(), cust_txns)
        filename = f"edd_{customer['customer_id']:04d}_{fake.date_between(start_date='-90d', end_date='today').strftime('%Y%m%d')}.txt"
        
        with open(f"{edd_dir}/{filename}", 'w') as f:
            f.write(memo)
        edd_count += 1

print(f"Generated {edd_count} EDD memoranda")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 2.4 Generate Adverse Media Reports

# COMMAND ----------

def generate_adverse_media(customer_info):
    """Generate adverse media screening report."""
    
    customer_name = f"{customer_info.get('first_name', '')} {customer_info.get('last_name', '')}".strip() or "Unknown"
    screening_date = fake.date_between(start_date="-30d", end_date="today")
    has_findings = random.random() < 0.15
    
    report = f"""ADVERSE MEDIA SCREENING REPORT
================================================================================

Subject: {customer_name} (ID: {customer_info['customer_id']})
Date: {screening_date}
Sources: LexisNexis, Dow Jones, Google News

================================================================================
RESULTS
================================================================================

"""
    if has_findings:
        report += f"""FINDINGS: 1 potential match

Source: {random.choice(['Civil Litigation', 'Business News', 'Regulatory Filing'])}
Date: {fake.date_between(start_date='-3y', end_date='-6m').strftime('%B %Y')}
Assessment: {random.choice(['LOW - Different individual', 'LOW - Matter resolved'])}
Disposition: CLEARED
"""
    else:
        report += "FINDINGS: NONE\n\nNo adverse media identified.\n"
    
    report += f"""
================================================================================

Result: {'CLEARED' if not has_findings or random.random() > 0.5 else 'NOTED'}
Next Screening: {(screening_date + timedelta(days=180)).strftime('%Y-%m-%d')}

Reviewed by: {random.choice(['Sarah Chen', 'Emily Thompson'])}
"""
    return report

# Generate adverse media
media_dir = f"{VOLUME_PATH}/adverse_media"
os.makedirs(media_dir, exist_ok=True)

media_count = 0
for _, customer in customers_df.iterrows():
    if customer["risk_rating"] == "high" or (customer["risk_rating"] == "medium" and random.random() < 0.5):
        report = generate_adverse_media(customer.to_dict())
        filename = f"screening_{customer['customer_id']:04d}_{fake.date_between(start_date='-30d', end_date='today').strftime('%Y%m%d')}.txt"
        
        with open(f"{media_dir}/{filename}", 'w') as f:
            f.write(report)
        media_count += 1

print(f"Generated {media_count} adverse media reports")

# COMMAND ----------

# MAGIC %md
# MAGIC ### 2.5 Generate Correspondence Logs

# COMMAND ----------

def generate_correspondence(customer_info):
    """Generate customer correspondence log."""
    
    customer_name = f"{customer_info.get('first_name', '')} {customer_info.get('last_name', '')}".strip() or "Unknown"
    contact_date = fake.date_between(start_date="-60d", end_date="today")
    
    if customer_info.get("risk_rating") == "high":
        interaction = random.choice([
            "Customer deposited $9,500 cash. Asked about CTR threshold. Explained structuring is illegal.",
            "Customer inquired about international wires. Vague about purpose. Noted for review.",
            "Customer requested to add signer without proper ID. Declined per CIP requirements."
        ])
    else:
        interaction = random.choice([
            "Customer updated contact information. Routine inquiry about savings rates.",
            "Customer called about unrecognized transaction. Confirmed legitimate. No concerns.",
            "Customer deposited insurance check with documentation. Normal transaction."
        ])
    
    log = f"""CUSTOMER CORRESPONDENCE LOG
================================================================================

Customer: {customer_name} (ID: {customer_info['customer_id']})
Date: {contact_date}
Type: {random.choice(['Branch Visit', 'Phone Call', 'Email'])}

================================================================================
SUMMARY
================================================================================

{interaction}

Action: {random.choice(['Logged', 'Flagged for review', 'No action needed'])}
Staff: {random.choice(['Jennifer Adams', 'Mark Thompson', 'Linda Chen'])}
"""
    return log

# Generate correspondence
corr_dir = f"{VOLUME_PATH}/correspondence"
os.makedirs(corr_dir, exist_ok=True)

corr_count = 0
alert_customers = set(alerts_df["customer_id"].unique())
for _, customer in customers_df.iterrows():
    if customer["customer_id"] in alert_customers or customer["risk_rating"] == "high" or random.random() < 0.1:
        log = generate_correspondence(customer.to_dict())
        filename = f"corr_{customer['customer_id']:04d}_{fake.date_between(start_date='-60d', end_date='today').strftime('%Y%m%d')}.txt"
        
        with open(f"{corr_dir}/{filename}", 'w') as f:
            f.write(log)
        corr_count += 1

print(f"Generated {corr_count} correspondence logs")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

print("=" * 70)
print("KNOWLEDGE BASE GENERATION COMPLETE")
print("=" * 70)

directories = {
    "policies_and_regulations/ffiec": "FFIEC Guidance",
    "policies_and_regulations/fincen": "FinCEN Guidance", 
    "policies_and_regulations/ofac": "OFAC Compliance",
    "policies_and_regulations/internal": "Institution Policies",
    "sar_narratives": "SAR Narratives",
    "case_notes": "Case Notes",
    "edd_memos": "EDD Memoranda",
    "adverse_media": "Adverse Media",
    "correspondence": "Correspondence"
}

total = 0
for path, label in directories.items():
    try:
        full_path = f"{VOLUME_PATH}/{path}"
        files = os.listdir(full_path)
        count = len(files)
        total += count
        print(f"{label:25} {count:5} docs")
    except:
        print(f"{label:25}     0 docs")

print("-" * 40)
print(f"{'TOTAL':25} {total:5} docs")
print(f"\nLocation: {VOLUME_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC 1. **Configure Knowledge Assistant** - Point vector store to this volume
# MAGIC 2. **Chunking** - ~500 tokens with 50 token overlap
# MAGIC 3. **Test queries**:
# MAGIC    - "What are the red flags for structuring?"
# MAGIC    - "What does our AML policy say about third-party deposits?"
# MAGIC    - "Show EDD memo for customer 25"