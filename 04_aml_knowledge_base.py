# Databricks notebook source
# MAGIC %md
# MAGIC # AML Knowledge Base - Unstructured Document Generation
# MAGIC
# MAGIC This notebook generates synthetic unstructured documents to populate the Knowledge Assistant:
# MAGIC - SAR Narratives (linked to customers with filed SARs)
# MAGIC - Investigation Case Notes
# MAGIC - EDD Memoranda
# MAGIC - Adverse Media Screening Results
# MAGIC - Customer Correspondence Logs
# MAGIC
# MAGIC These documents provide historical context that enables the AI agent to answer questions like:
# MAGIC - "What previous filings do we have on this customer?"
# MAGIC - "Are there any previous notes on this entity?"
# MAGIC - "What gaps exist in our documentation for this customer?"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

CATALOG = "fins_aml"
SCHEMA = "data_generation"
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/knowledge_base"

# Create volume for knowledge base documents
spark.sql(f"CREATE VOLUME IF NOT EXISTS {CATALOG}.{SCHEMA}.knowledge_base")

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

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Generate SAR Narratives

# COMMAND ----------

def generate_sar_narrative(customer_info, sar_info, transactions):
    """Generate a realistic SAR narrative for a customer."""
    
    customer_id = customer_info["customer_id"]
    customer_name = f"{customer_info.get('first_name', '')} {customer_info.get('last_name', '')}".strip()
    if not customer_name:
        customer_name = customer_info.get("business_name", "Unknown Entity")
    
    activity_type = sar_info["activity_type"]
    amount_involved = sar_info["amount_involved"]
    activity_start = sar_info["activity_start"]
    activity_end = sar_info["activity_end"]
    
    # Build transaction summary
    txn_summary = []
    for txn in transactions[:10]:
        txn_summary.append(f"- {str(txn['transaction_date'])[:10]}: {txn['transaction_type'].replace('_', ' ').title()} of ${txn['amount']:,.2f}")
    
    narrative = f"""SAR NARRATIVE

SAR ID: {sar_info['sar_id']}
FinCEN DCN: {sar_info['fincen_dcn']}
Filing Date: {sar_info['filing_date']}
Filing Type: {sar_info['filing_type'].upper()}

SUBJECT INFORMATION:
Name: {customer_name}
Customer ID: {customer_id}
Date of Birth: {customer_info.get('date_of_birth', 'N/A')}
Address: {customer_info.get('address_line1', '')}, {customer_info.get('address_city', '')}, {customer_info.get('address_state', '')} {customer_info.get('address_zip', '')}
Occupation: {customer_info.get('occupation', 'N/A')}
Relationship Since: {customer_info.get('onboarding_date', 'N/A')}

ACTIVITY SUMMARY:
Activity Type: {activity_type}
Activity Period: {activity_start} to {activity_end}
Total Amount Involved: ${amount_involved:,.2f}

NARRATIVE:

ABC National Bank is filing this Suspicious Activity Report to report suspected {activity_type.lower()} activity conducted by {customer_name}, Customer ID {customer_id}.

{customer_name} has maintained a banking relationship with the institution since {customer_info.get('onboarding_date', 'unknown')}. The customer's stated occupation is "{customer_info.get('occupation', 'not specified')}" with an annual income of ${customer_info.get('annual_income', 0):,.0f}.

During the activity period from {activity_start} to {activity_end}, the following suspicious transactions were identified:

{chr(10).join(txn_summary)}

Total suspicious activity: ${amount_involved:,.2f}

"""

    # Add scenario-specific content
    if "structuring" in activity_type.lower():
        narrative += f"""
The pattern of deposits is consistent with structuring designed to evade Currency Transaction Report (CTR) filing requirements. The customer made multiple cash deposits in amounts just below the $10,000 reporting threshold, often at different branch locations within short time periods.

When questioned by branch staff, {customer_name} stated the cash was from "{random.choice(['business sales', 'personal savings', 'antique sales', 'car sales'])}." The customer was unable or unwilling to provide supporting documentation when requested.

The volume of cash activity is inconsistent with the customer's stated occupation and income profile.
"""
    
    elif "rapid" in activity_type.lower():
        narrative += f"""
The transaction pattern indicates rapid movement of funds with minimal retention. Large incoming wire transfers were received and substantially equivalent amounts were wired out within 24-48 hours, leaving minimal balance in the account.

This pass-through activity suggests the account may be used as a conduit for layering funds. The beneficiaries of outgoing wires include entities in multiple jurisdictions with no apparent business connection to the customer's stated activities.
"""

    elif "geo" in activity_type.lower() or "country" in activity_type.lower():
        narrative += f"""
The customer initiated wire transfers to jurisdictions identified as high-risk for money laundering and sanctions evasion. The destination countries include those subject to OFAC sanctions programs or identified by FATF as having strategic AML/CFT deficiencies.

The customer's stated business activities do not appear to justify transactions with these jurisdictions. When asked about the business purpose, the customer provided vague explanations inconsistent with legitimate trade or investment activities.
"""
    
    elif "third" in activity_type.lower() or "party" in activity_type.lower():
        narrative += f"""
Multiple cash deposits were made to the customer's account by third parties who are not authorized signers or known associates. The third-party depositors provided limited identification and stated they were "helping a friend."

This pattern raises concerns about potential nominee or funnel account activity. The account holder has been unable to provide a satisfactory explanation for why unrelated individuals are depositing cash into the account.
"""
    else:
        narrative += f"""
The activity pattern is inconsistent with the customer's known profile and stated business purpose. The transaction volumes and patterns observed during the activity period represent a significant departure from historical account behavior.

Despite requests, the customer has been unable to provide adequate documentation or explanation for the activity.
"""

    # Standard closing
    narrative += f"""

ACTIONS TAKEN:
- Transaction monitoring alert escalated to BSA/AML team
- Enhanced due diligence review conducted
- Customer interview attempted via Relationship Manager
- Account placed under enhanced monitoring

RECOMMENDATION:
Based on the investigation findings, this SAR is being filed due to activity consistent with {activity_type.lower()}. The pattern of transactions, combined with the customer's inability to provide adequate documentation or explanation, warrants reporting to FinCEN.

{random.choice(['Enhanced monitoring will continue.', 'Account restrictions have been implemented.', 'Account is under review for potential closure.'])}

{random.choice(['No law enforcement contact at this time.', 'Information shared with local law enforcement per their request.'])}

All supporting documentation maintained at: Compliance Department, Investigation File #{sar_info['case_id']}

Prepared by: {random.choice(['Sarah Chen', 'Michael Rodriguez', 'Emily Thompson', 'David Park'])}, AML Analyst
Reviewed by: {random.choice(['James Wong', 'Lisa Martinez', 'Robert Chen'])}, BSA Officer
"""
    
    return narrative

# COMMAND ----------

# Generate SAR narratives
sar_dir = f"{VOLUME_PATH}/sar_narratives"
dbutils.fs.mkdirs(sar_dir)

sar_count = 0
for _, sar in sars_df.iterrows():
    customer_id = sar["customer_id"]
    customer = customers_df[customers_df["customer_id"] == customer_id]
    
    if customer.empty:
        continue
    
    customer = customer.iloc[0].to_dict()
    cust_txns = transactions_df[transactions_df["customer_id"] == customer_id].to_dict('records')
    
    narrative = generate_sar_narrative(customer, sar.to_dict(), cust_txns)
    
    filename = f"SAR_{sar['fincen_dcn']}_customer_{customer_id:04d}.txt"
    filepath = f"{sar_dir}/{filename}"
    
    dbutils.fs.put(filepath, narrative, overwrite=True)
    sar_count += 1

print(f"Generated {sar_count} SAR narrative documents")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Generate Investigation Case Notes

# COMMAND ----------

def generate_case_notes(case_info, customer_info, transactions):
    """Generate investigation case notes."""
    
    customer_id = customer_info["customer_id"]
    customer_name = f"{customer_info.get('first_name', '')} {customer_info.get('last_name', '')}".strip()
    if not customer_name:
        customer_name = customer_info.get("business_name", "Unknown Entity")
    
    analyst = case_info.get("assigned_analyst", "Analyst")
    supervisor = case_info.get("supervisor", "Supervisor")
    open_date = datetime.fromisoformat(str(case_info["open_date"])[:19])
    
    notes = f"""INVESTIGATION CASE NOTES

Case ID: CASE-{case_info['case_id']:06d}
Customer: {customer_name} (ID: {customer_id})
Alert Scenario: {case_info['case_type'].upper()}-001
Date Opened: {open_date.strftime('%B %d, %Y')}
Assigned Analyst: {analyst}
Supervisor: {supervisor}
Priority: {case_info['priority'].upper()}
Status: {case_info['case_status'].replace('_', ' ').title()}

================================================================================

--- {open_date.strftime('%B %d, %Y')} - Initial Alert Review ({analyst}) ---

Alert triggered for {case_info['case_type'].replace('_', ' ')} pattern. Customer flagged by automated detection system.

Customer Profile Review:
- Customer since: {customer_info.get('onboarding_date', 'N/A')}
- Risk Rating: {customer_info.get('risk_rating', 'N/A').upper()}
- KYC Status: {customer_info.get('kyc_status', 'N/A').title()}
- Occupation: {customer_info.get('occupation', 'N/A')}
- Annual Income: ${customer_info.get('annual_income', 0):,.0f}

Initial Assessment: {random.choice(['HIGH RISK - Pattern consistent with known ML typologies', 'MEDIUM RISK - Unusual activity requires further review', 'ELEVATED RISK - Continuing activity after prior alerts'])}

Action Items:
1. Pull full transaction history (90 days)
2. Review prior alerts and SARs
3. Request updated KYC from Relationship Manager

"""
    
    # Day 2 notes
    day2 = open_date + timedelta(days=1)
    num_txns = len(transactions)
    total_amount = sum(t.get('amount', 0) for t in transactions[:20])
    
    notes += f"""--- {day2.strftime('%B %d, %Y')} - Transaction Analysis ({analyst}) ---

Completed 90-day transaction history review. Key findings:

Transaction Summary:
- Total transactions reviewed: {num_txns}
- Total volume: ${total_amount:,.2f}
- Cash deposits: {sum(1 for t in transactions if t.get('transaction_type') == 'cash_deposit')}
- Wire transfers: {sum(1 for t in transactions if 'wire' in str(t.get('transaction_type', '')))}

Red Flags Identified:
- Activity inconsistent with customer profile
- Unable to verify stated source of funds
- Unusual transaction patterns detected
- Documentation gaps in customer file

Documentation: Transaction logs saved to case file (Exhibit A)

"""
    
    # Day 3 notes
    day3 = open_date + timedelta(days=2)
    notes += f"""--- {day3.strftime('%B %d, %Y')} - KYC/CDD Review ({analyst}) ---

Relationship Manager provided customer update:
- Customer visited branch on {(day3 - timedelta(days=1)).strftime('%B %d, %Y')}
- Customer stated {random.choice(['"business has expanded"', '"funds from legitimate sources"', '"helping family members"', '"normal business operations"'])}
- {random.choice(['Customer declined to provide additional documentation', 'Customer provided incomplete business records', 'Customer unable to verify source of funds'])}

KYC File Review:
- Last KYC refresh: {customer_info.get('kyc_date', 'N/A')}
- Source of wealth documentation: {random.choice(['On file - dated', 'Missing', 'Incomplete', 'Requires update'])}
- Business verification: {random.choice(['Not verified', 'Partially verified', 'Unable to verify online presence'])}

"""
    
    # Escalation notes
    day4 = open_date + timedelta(days=3)
    notes += f"""--- {day4.strftime('%B %d, %Y')} - Supervisor Escalation ({analyst}) ---

Escalating to BSA Officer {supervisor} for SAR filing recommendation.

Evidence Package Compiled:
- Transaction logs (Exhibit A)
- Prior alert history (Exhibit B)
- KYC documentation review (Exhibit C)
- Customer interview notes from RM (Exhibit D)

Recommendation: {random.choice(['File SAR - activity consistent with ML indicators', 'File SAR - continuing suspicious activity', 'Enhanced monitoring - insufficient evidence for SAR'])}

"""
    
    # Supervisor review if closed
    if case_info['case_status'] in ['sar_filed', 'closed_no_action']:
        day5 = open_date + timedelta(days=5)
        notes += f"""--- {day5.strftime('%B %d, %Y')} - BSA Officer Review ({supervisor}) ---

Case reviewed. {case_info.get('disposition', 'Pending determination')}.

Rationale: {case_info.get('disposition_reason', 'See case documentation.')}

Account Action: {case_info.get('account_action', 'None').replace('_', ' ').title()}

Case Status: {case_info['case_status'].replace('_', ' ').upper()}

================================================================================
END OF CASE NOTES
================================================================================
"""
    
    return notes

# COMMAND ----------

# Generate case notes
case_notes_dir = f"{VOLUME_PATH}/case_notes"
dbutils.fs.mkdirs(case_notes_dir)

notes_count = 0
for _, case in cases_df.iterrows():
    customer_id = case["customer_id"]
    customer = customers_df[customers_df["customer_id"] == customer_id]
    
    if customer.empty:
        continue
        
    customer = customer.iloc[0].to_dict()
    cust_txns = transactions_df[transactions_df["customer_id"] == customer_id].to_dict('records')
    
    notes = generate_case_notes(case.to_dict(), customer, cust_txns)
    
    filename = f"CASE_{case['case_id']:06d}_customer_{customer_id:04d}.txt"
    filepath = f"{case_notes_dir}/{filename}"
    
    dbutils.fs.put(filepath, notes, overwrite=True)
    notes_count += 1

print(f"Generated {notes_count} case note documents")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Generate EDD Memoranda

# COMMAND ----------

def generate_edd_memo(customer_info):
    """Generate Enhanced Due Diligence memorandum for high-risk customers."""
    
    customer_id = customer_info["customer_id"]
    customer_name = f"{customer_info.get('first_name', '')} {customer_info.get('last_name', '')}".strip()
    if not customer_name:
        customer_name = customer_info.get("business_name", "Unknown Entity")
    
    review_date = fake.date_between(start_date="-6m", end_date="today")
    
    memo = f"""ENHANCED DUE DILIGENCE MEMORANDUM

Date: {review_date.strftime('%B %d, %Y')}
Customer: {customer_name}
Customer ID: {customer_id}
Risk Rating: {customer_info.get('risk_rating', 'N/A').upper()}
Prepared By: {random.choice(['Maria Garcia', 'John Smith', 'Amanda Lee'])}, KYC Analyst

================================================================================

PURPOSE:
Enhanced due diligence review triggered by:
- {customer_info.get('risk_rating', 'elevated').title()} risk customer classification
- {'Politically Exposed Person (PEP) status' if customer_info.get('pep_flag') else 'Periodic EDD refresh requirement'}
- Elevated transaction activity

================================================================================

CUSTOMER PROFILE:

Name: {customer_name}
Customer Type: {customer_info.get('customer_type', 'N/A').title()}
Date of Birth: {customer_info.get('date_of_birth', 'N/A')}
Address: {customer_info.get('address_line1', '')}, {customer_info.get('address_city', '')}, {customer_info.get('address_state', '')} {customer_info.get('address_zip', '')}
Country: {customer_info.get('address_country', 'US')}
Occupation: {customer_info.get('occupation', 'N/A')}
Employer: {customer_info.get('employer', 'N/A')}
Annual Income: ${customer_info.get('annual_income', 0):,.0f}
Relationship Since: {customer_info.get('onboarding_date', 'N/A')}
PEP Status: {'Yes - ' + str(customer_info.get('pep_relationship', 'Direct')) if customer_info.get('pep_flag') else 'No'}

================================================================================

SOURCE OF FUNDS/WEALTH:

Customer states source of funds as: "{customer_info.get('source_of_wealth', 'Not documented')}"

Verification Status: {random.choice(['Verified via tax returns', 'Partially verified', 'Unable to fully verify', 'Documentation pending'])}

Supporting Documentation on File:
- {random.choice(['Tax returns (2 years)', 'Business financials', 'Employment verification', 'Investment statements'])}
- {random.choice(['Bank statements', 'Property records', 'Business registration', 'None'])}

================================================================================

TRANSACTION ACTIVITY REVIEW:

Review Period: Last 12 months
Average Monthly Volume: ${random.randint(5000, 500000):,}
Transaction Types: {random.choice(['Primarily wire transfers', 'Mix of cash and electronic', 'Heavy cash activity', 'Standard banking activity'])}

Notable Patterns:
- {random.choice(['Activity consistent with stated business', 'Volume exceeds stated income', 'International transfers noted', 'No unusual patterns observed'])}

================================================================================

ADVERSE MEDIA / NEGATIVE NEWS:

Search Conducted: {review_date.strftime('%B %d, %Y')}
Search Sources: LexisNexis, Google News, Public Records

Results: {random.choice(['No adverse media identified', 'Minor references found - not material', 'Potential match requiring further review', 'Clear - no negative information'])}

================================================================================

RECOMMENDATION:

Based on this EDD review:
- Risk Rating: {random.choice(['Maintain current rating', 'Upgrade to HIGH', 'Downgrade to MEDIUM', 'Maintain HIGH rating'])}
- Monitoring: {random.choice(['Standard monitoring', 'Enhanced monitoring recommended', 'Daily transaction review', 'Quarterly EDD refresh'])}
- Account Action: {random.choice(['None required', 'Request updated documentation', 'Schedule customer interview', 'Escalate to BSA Officer'])}

Next Review Due: {(review_date + timedelta(days=random.choice([90, 180, 365]))).strftime('%B %d, %Y')}

================================================================================

APPROVAL:

Prepared By: {random.choice(['Maria Garcia', 'John Smith', 'Amanda Lee'])}, KYC Analyst
Reviewed By: {random.choice(['James Wong', 'Lisa Martinez', 'Robert Chen'])}, BSA Officer
Approval Date: {(review_date + timedelta(days=random.randint(1, 5))).strftime('%B %d, %Y')}
"""
    
    return memo

# COMMAND ----------

# Generate EDD memos for high/medium risk customers
edd_dir = f"{VOLUME_PATH}/edd_memos"
dbutils.fs.mkdirs(edd_dir)

edd_count = 0
high_risk_customers = customers_df[customers_df["risk_rating"].isin(["high", "medium"])]

for _, customer in high_risk_customers.iterrows():
    customer_id = customer["customer_id"]
    
    memo = generate_edd_memo(customer.to_dict())
    
    filename = f"EDD_customer_{customer_id:04d}_{fake.date_between(start_date='-6m', end_date='today').strftime('%Y%m%d')}.txt"
    filepath = f"{edd_dir}/{filename}"
    
    dbutils.fs.put(filepath, memo, overwrite=True)
    edd_count += 1

print(f"Generated {edd_count} EDD memoranda")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. Generate Adverse Media Screening Results

# COMMAND ----------

def generate_adverse_media_report(customer_info):
    """Generate adverse media screening report."""
    
    customer_id = customer_info["customer_id"]
    customer_name = f"{customer_info.get('first_name', '')} {customer_info.get('last_name', '')}".strip()
    if not customer_name:
        customer_name = customer_info.get("business_name", "Unknown Entity")
    
    screening_date = fake.date_between(start_date="-3m", end_date="today")
    
    report = f"""ADVERSE MEDIA SCREENING REPORT

Date: {screening_date.strftime('%B %d, %Y')}
Customer: {customer_name}
Customer ID: {customer_id}
Screening System: LexisNexis WorldCompliance
Analyst: {random.choice(['Tom Richards', 'Sarah Chen', 'Michael Rodriguez'])}

================================================================================

SEARCH PARAMETERS:

Name Searched: {customer_name}
Date of Birth: {customer_info.get('date_of_birth', 'N/A')}
Location: {customer_info.get('address_city', '')}, {customer_info.get('address_state', '')}
Search Scope: Global news, regulatory actions, legal proceedings, sanctions lists

================================================================================

SEARCH RESULTS:

"""
    
    # Generate random number of results
    num_results = random.randint(0, 3)
    
    if num_results == 0:
        report += """No adverse media or negative news identified for this customer.

Search covered:
- Global news sources (past 5 years)
- Regulatory enforcement actions
- Legal proceedings and judgments
- Sanctions and watchlists

ASSESSMENT: CLEAR - No derogatory information found.
"""
    else:
        for i in range(num_results):
            relevance = random.choice(["High", "Moderate", "Low", "Uncertain"])
            source = random.choice(["Financial Times", "Reuters", "Wall Street Journal", "Local News", "Court Records", "Regulatory Database"])
            article_date = fake.date_between(start_date="-3y", end_date="-6m")
            
            report += f"""Result {i+1} - {relevance} Relevance
Source: {source}
Date: {article_date.strftime('%B %d, %Y')}
Headline: "{fake.sentence(nb_words=8)}"
Summary: {fake.paragraph(nb_sentences=2)}
Match Confidence: {random.randint(40, 95)}%

"""
        
        report += f"""================================================================================

ANALYST ASSESSMENT:

{random.choice([
    'Results reviewed and determined to be false positives based on name similarity only.',
    'Result 1 represents potential reputational risk. Recommend escalation for further review.',
    'Matches appear to reference different individuals. No action required.',
    'Minor references found but not material to banking relationship. Continue monitoring.'
])}

Recommendation: {random.choice([
    'Clear for continued relationship',
    'Flag for BSA Officer review',
    'Schedule enhanced monitoring',
    'Request additional customer information'
])}
"""
    
    report += f"""
================================================================================

SCREENING CERTIFIED BY:

Analyst: {random.choice(['Tom Richards', 'Sarah Chen', 'Michael Rodriguez'])}
Date: {screening_date.strftime('%B %d, %Y')}
Next Screening Due: {(screening_date + timedelta(days=365)).strftime('%B %d, %Y')}
"""
    
    return report

# COMMAND ----------

# Generate adverse media reports
media_dir = f"{VOLUME_PATH}/adverse_media"
dbutils.fs.mkdirs(media_dir)

media_count = 0

# Generate for all high-risk and some medium-risk customers
for _, customer in customers_df.iterrows():
    customer_id = customer["customer_id"]
    
    # Generate for high-risk, 50% of medium-risk
    if customer["risk_rating"] == "high" or (customer["risk_rating"] == "medium" and random.random() < 0.5):
        report = generate_adverse_media_report(customer.to_dict())
        
        filename = f"screening_customer_{customer_id:04d}_{fake.date_between(start_date='-3m', end_date='today').strftime('%Y%m%d')}.txt"
        filepath = f"{media_dir}/{filename}"
        
        dbutils.fs.put(filepath, report, overwrite=True)
        media_count += 1

print(f"Generated {media_count} adverse media screening reports")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 5. Generate Customer Correspondence Logs

# COMMAND ----------

def generate_correspondence_log(customer_info):
    """Generate customer correspondence/interaction log."""
    
    customer_id = customer_info["customer_id"]
    customer_name = f"{customer_info.get('first_name', '')} {customer_info.get('last_name', '')}".strip()
    if not customer_name:
        customer_name = customer_info.get("business_name", "Unknown Entity")
    
    contact_date = fake.date_between(start_date="-60d", end_date="today")
    
    contact_types = [
        ("Branch Visit", "Main Street Branch", "Jennifer Adams (Personal Banker)"),
        ("Phone Call", "Customer Service", "Mark Thompson (CSR)"),
        ("Branch Visit", "Oak Avenue Branch", "Linda Chen (Branch Manager)"),
        ("Email Correspondence", "Online Banking", "System Generated"),
    ]
    
    contact_type, location, staff = random.choice(contact_types)
    
    log = f"""CUSTOMER CORRESPONDENCE LOG

Customer: {customer_name} (ID: {customer_id})
Account: XXXXX{random.randint(1000, 9999)}
Date: {contact_date.strftime('%B %d, %Y')}
Contact Type: {contact_type}
Location: {location}
Staff: {staff}

================================================================================

SUMMARY OF INTERACTION:

"""
    
    # Generate interaction content based on customer risk
    if customer_info.get("risk_rating") == "high":
        interactions = [
            f"""Customer visited branch to make a cash deposit of $9,500. When informed about CTR requirements for deposits over $10,000, customer asked "what if I deposit less?"

Staff explained that structuring deposits to avoid reporting is illegal. Customer stated "I'm not trying to avoid anything, I just have cash from my business."

When asked about business documentation, customer became defensive and stated "This is my money, I don't need to prove anything."

Customer ultimately deposited $9,500.""",
            
            f"""Customer called to inquire about wire transfer limits. Specifically asked about transfers to {random.choice(['Dubai', 'Hong Kong', 'Singapore', 'Cyprus'])}.

When asked about the purpose of the transfer, customer provided vague response about "business investments." Customer was unable to provide details about the receiving party.

Customer was advised that additional documentation may be required for international wires.""",
            
            f"""Customer visited branch requesting to add authorized signer to account. The proposed signer was not present and customer could not provide their identification.

Staff explained that the authorized signer must be present with valid ID. Customer became frustrated and stated "this is ridiculous, they're family."

Customer left without adding authorized signer."""
        ]
    else:
        interactions = [
            f"""Customer visited branch to update contact information. New address and phone number verified and updated in system.

Customer also inquired about savings account options. Provided information on current rates and account types.

Pleasant interaction, no concerns noted.""",
            
            f"""Customer called regarding recent transaction that didn't recognize. After review, confirmed it was a subscription service customer had forgotten about.

Customer thanked representative for the assistance. No fraud suspected.""",
            
            f"""Customer visited branch to deposit check from insurance settlement. Check amount: ${random.randint(5000, 50000):,}.

Customer provided documentation explaining source of funds (insurance claim). Documentation copied and retained per policy.

Normal transaction, no concerns."""
        ]
    
    log += random.choice(interactions)
    
    log += f"""

================================================================================

ACTIONS TAKEN:

- {random.choice(['Interaction logged in CRM', 'Documentation retained in customer file', 'Suspicious activity referral submitted', 'No action required'])}
- {random.choice(['Customer file updated', 'Manager notified', 'Standard processing', 'Follow-up scheduled'])}

PRIOR INTERACTIONS:
- {random.choice(['No prior notable interactions', 'Similar inquiry on ' + fake.date_between(start_date="-6m", end_date="-1m").strftime("%B %d, %Y"), 'Previous cash deposit discussion on file'])}

================================================================================

Logged By: {staff.split('(')[0].strip()}
Date: {contact_date.strftime('%B %d, %Y')}
"""
    
    return log

# COMMAND ----------

# Generate correspondence logs
correspondence_dir = f"{VOLUME_PATH}/correspondence"
dbutils.fs.mkdirs(correspondence_dir)

correspondence_count = 0

# Generate for customers with alerts or high risk
alert_customer_ids = set(alerts_df["customer_id"].unique())

for _, customer in customers_df.iterrows():
    customer_id = customer["customer_id"]
    
    # Generate for customers with alerts, high-risk, or random 10%
    if customer_id in alert_customer_ids or customer["risk_rating"] == "high" or random.random() < 0.1:
        log = generate_correspondence_log(customer.to_dict())
        
        filename = f"correspondence_customer_{customer_id:04d}_{fake.date_between(start_date='-60d', end_date='today').strftime('%Y%m%d')}.txt"
        filepath = f"{correspondence_dir}/{filename}"
        
        dbutils.fs.put(filepath, log, overwrite=True)
        correspondence_count += 1

print(f"Generated {correspondence_count} correspondence logs")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------

# Count all generated documents
print("=" * 60)
print("Knowledge Base Document Generation Summary")
print("=" * 60)

directories = ["sar_narratives", "case_notes", "edd_memos", "adverse_media", "correspondence"]

for dir_name in directories:
    try:
        files = dbutils.fs.ls(f"{VOLUME_PATH}/{dir_name}")
        print(f"{dir_name.upper()}: {len(files)} documents")
    except:
        print(f"{dir_name.upper()}: 0 documents")

print("=" * 60)
print(f"\nAll documents saved to: {VOLUME_PATH}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC
# MAGIC 1. **Configure Knowledge Assistant** - Point the vector store to this volume
# MAGIC 2. **Set chunking strategy** - Recommend ~500 token chunks with 50 token overlap
# MAGIC 3. **Add metadata** - Include customer_id, document_type, date for filtering
# MAGIC 4. **Test retrieval** - Query for specific customers to verify linkage