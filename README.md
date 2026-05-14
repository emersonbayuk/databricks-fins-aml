<p align="center">
  <img src="assets/sherlock-logo.svg" alt="SherlockAML" width="100%"/>
</p>

<p align="center">
  <strong>An agentic AML investigation workspace, built on the Databricks Data Intelligence Platform.</strong>
</p>

<div align="center">

[![Databricks](https://img.shields.io/badge/Databricks-Platform-FF3621?style=flat&logo=databricks)](https://databricks.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-Databricks-FF3621)](LICENSE.md)

</div>

---

## The story

Anti-money-laundering is a $206B/year global compliance line item, and the people doing the work are drowning.

A typical AML investigator opens an alert and then spends **3–6 hours** chasing it. They sign into ten or more separate systems — KYC, transaction monitoring, sanctions screening, credit bureau, case management — copy data out by hand, map relationships on a notepad, and finally hand-draft a SAR narrative from scratch. **Ninety percent of those alerts turn out to be false positives**, but every one of them gets the full 3–6 hour treatment because nothing connects the dots automatically. The backlog grows faster than they can clear it.

Their boss has a different problem. The Head of AML is trying to demonstrate program effectiveness to regulators with flat budgets, increasing scrutiny, and the board asking pointed questions. **Forty-two percent of their time goes to compliance reporting**, and most of the underlying evidence is stitched together from Excel exports.

The pain isn't one tool. It's that AML investigation is a *data and reasoning* problem trapped inside ten siloed *systems* — and the analyst is the integration layer.

### Two personas, one workflow

> **Sarah Chen — AML Investigator** *(first-line user)*
> *"I spend 3–6 hours per case manually gathering data across 10+ systems. 90% of alerts are false positives but still require full investigation. I'm writing the same SAR narratives from scratch every week. The backlog is growing faster than I can clear it."*
>
> **Top KPIs:** False Positive Rate · Case Processing Time · SAR Quality Score

> **Marcus Johnson — AML Investigation Unit Lead** *(buyer)*
> *"It's hard to demonstrate AML program effectiveness to regulators while budgets stay flat. Forty-two percent of my time goes to compliance reporting. I'm afraid of enforcement actions and reputational damage. I need audit-ready documentation that shows our controls are working."*
>
> **Top KPIs:** Alert Backlog · Regulatory Exam Readiness · Detection Rate

---

## What SherlockAML changes

The Databricks Data Intelligence Platform collapses the ten siloed systems into one governed lakehouse, and lets a small set of AI agents do the data-gathering, pattern analysis, and narrative drafting that the human investigator used to do by hand. The human stays in the loop for judgment and sign-off — the agents do the busywork.

<p align="center">
  <img src="assets/investigation-process-transformation.png" alt="Investigation process transformation: from 3-6 hours of manual triage, data gathering, pattern analysis, and SAR drafting to ~10-20 minutes of agent-augmented review" width="90%"/>
</p>

| Investigation step | Before | After |
|---|---|---|
| Data gathering across 10+ systems | 60–90 min manual | <1 min via orchestrated data agents |
| Triage & filtering (90–95% false positives) | 30–45 min manual | 5–10 min via cognitive agents that score and surface only high-risk cases |
| Pattern analysis & link discovery | 60–120 min manual | 5–10 min via Agent Bricks matching against thousands of crime typologies |
| SAR narrative drafting | 60–120 min manual | 2–5 min via the supervisor agent → regulator-ready draft for human sign-off |
| **End-to-end** | **3–6 hours** | **~10–20 minutes** |

**Expected outcomes for a large institution:** 8–10x faster case processing · ~75% reduction in false positives · $5–10M annual efficiency gain · audit-ready SAR documentation by default.

---

## What's in this repo

SherlockAML is a complete, partner-deployable reference solution:

- **A FastAPI + React investigation app** — three surfaces (Executive Overview, Alert Investigation, Graph Explorer) backed by a Multi-Agent Supervisor over three Knowledge Assistants, two Genie Spaces, and an optional external web-search MCP server.
- **A self-contained data bundle** — synthetic AML data (customers, transactions, alerts, cases, SAR filings) plus an executive dashboard. Generated fresh on every deploy.
- **Automated agent provisioning** — the data bundle's pipeline ends by creating the full agent graph in the target workspace, so a partner gets the same investigator surface with no manual UI clicks.
- **Optional Lakebase backend** — graph queries can be served from a managed Postgres instance for sub-10ms reads when the workload demands it.

```
fins-aml-amer/
├── README.md                           ← you are here
├── LICENSE.md  NOTICE.md  CONTRIBUTING.md  SECURITY.md
├── assets/                             ← logo, diagrams
├── fins-aml-app-bundle/                ← the investigation app (FastAPI + React)
│   ├── app.yaml, databricks.yml        ← bundle + Apps runtime config
│   ├── main.py
│   ├── backend/                        ← FastAPI handlers
│   │   ├── api/                        ← chat, sar, investigation, graph endpoints
│   │   └── services/                   ← Delta SQL + Lakebase clients, auth
│   └── frontend/build/index.html       ← single-file React app
├── fins-aml-data-bundle/               ← synthetic data + agent provisioning
│   ├── databricks.yml
│   ├── notebooks/                      ← 01-04: data gen → screening → graph → KB docs
│   ├── export_agents.py                ← read-only introspection of the agent graph
│   ├── provision_agents.py             ← idempotent replay into any target workspace
│   └── agents/                         ← captured JSON specs (MAS, KAs, Genies, MCP)
└── legacy/neo4j-integration/           ← reference Neo4j graph backend (not active)
```

---

## Deploy

The repo ships as two Databricks Asset Bundles. Deploy the data bundle first (it creates the tables, volumes, dashboard, **and** the agents the app calls), then the app bundle.

### Prerequisites

- A Databricks workspace with Unity Catalog, Serverless compute, and Agent Bricks enabled
- Databricks CLI **v0.299.1 or newer** (`brew upgrade databricks` or [install instructions](https://docs.databricks.com/en/dev-tools/cli/install.html))
- A configured CLI profile pointing at your workspace
- A SQL warehouse you have CAN_USE permission on
- *(Optional)* A You.com API key, if you want web-search as a 6th sub-agent

### 1. Configure your target

Copy the `example` target in `fins-aml-app-bundle/databricks.yml` and fill in your workspace values:

```yaml
targets:
  my-workspace:
    mode: development
    default: true
    workspace:
      host: https://<your-workspace>.cloud.databricks.com
    variables:
      databricks_hostname: "<your-workspace>.cloud.databricks.com"
      workspace_id: "<numeric-workspace-id>"
      warehouse_id: "<sql-warehouse-id>"
      mas_endpoint_url: "https://<your-workspace>.cloud.databricks.com/serving-endpoints/<your-mas-endpoint>/invocations"
      dashboard_id: "<lakeview-dashboard-id>"   # filled in after step 2
```

### 2. Deploy and run the data bundle

```bash
cd fins-aml-data-bundle

# (Optional) Set up the You.com MCP secret first if you want web search.
databricks secrets create-scope youcom --profile <your-profile>
databricks secrets put-secret youcom api_key --profile <your-profile>

# Deploy resource definitions.
databricks bundle deploy --profile <your-profile> \
  --var catalog=<your-catalog> \
  --var schema=<your-schema> \
  --var warehouse_id=<your-warehouse-id> \
  --var force_rebuild=false \
  --var youcom_secret_scope=youcom \
  --var youcom_secret_key=api_key

# Run the pipeline. This generates data AND provisions the agent graph.
databricks bundle run aml_data_generation_pipeline --profile <your-profile>
```

The pipeline runs six tasks in order: `process_dashboard_template → generate_base_data → watchlist_screening → graph_model → knowledge_base → provision_agents`. Expect 30–60 minutes total; the last step (Knowledge Assistant indexing) is the longest. When it finishes you'll have:

- All tables under `<catalog>.<schema>.*`
- The `knowledge_base` volume populated with synthetic PDFs, SAR narratives, EDD memos, and adverse-media reports
- The "AML Executive Dashboard" deployed
- A working Multi-Agent Supervisor with 3 Knowledge Assistants, 2 Genie Spaces, and (if you set the You.com secret) 1 external MCP server — all ready for the app to call

If you skipped the You.com secret, the MAS comes up with 5 sub-agents instead of 6. You can add it later by setting the secret and re-running the pipeline.

### 3. Deploy the app

```bash
cd ../fins-aml-app-bundle
./deploy.sh my-workspace <your-profile>
```

`deploy.sh` resolves the `${var.xxx}` references in `app.yaml` for your target, uploads the resolved file to the workspace, and runs `databricks apps deploy`.

---

## Optional: Lakebase as the graph backend

For graph-heavy use cases — the customer subgraph view, the Graph Explorer — the app can read from a Lakebase Postgres instance instead of the SQL warehouse. Postgres queries land in single-digit milliseconds vs warehouse queries that often take 500ms–2s.

To turn it on:

1. Provision a Lakebase project and copy your graph tables into it. The recommended pattern is a UC → Lakebase synced table; for one-shot copies, see `fins-aml-data-bundle/notebooks/` for the schema.
2. Add the connection details to your target in `databricks.yml`:
   ```yaml
   use_lakebase: "true"
   lakebase_host: "ep-xxx.database.<region>.cloud.databricks.com"
   lakebase_database: "fins_aml_graph"
   lakebase_endpoint_path: "projects/<id>/branches/production/endpoints/primary"
   ```
3. Grant the app's service principal `LOGIN` on the database, and `SELECT` on the graph tables.
4. Redeploy the app.

The graph endpoints automatically fall back to the SQL warehouse if Lakebase is unreachable for any reason, so flipping the flag on is reversible without risk.

---

## Customization for partners

This repo is meant to be forked, cloned, or vendored. A partner taking this on:

- **Replace the synthetic data**: keep the data bundle structure, swap the generation notebooks for your own data sources. The downstream agent prompts and the app's queries reference the table schemas, not the data content.
- **Adjust the agent graph**: the MAS, its three KAs, two Genie Spaces, and the MCP connection are all captured as JSON under `fins-aml-data-bundle/agents/`. Edit those files (descriptions, instructions, table/document references) before running `bundle deploy` and you get a different agent graph in the target workspace.
- **Swap the graph backend**: a Neo4j reference implementation lives in [`legacy/neo4j-integration/`](legacy/neo4j-integration/README.md) for teams who'd prefer a labeled-property graph database over Delta/Lakebase.
- **Theme the frontend**: it's a single React file (`frontend/build/index.html`) using a Databricks-inspired dark theme. Style with vanilla CSS, no build pipeline.

---

## Architecture (one-line version)

User → React app → FastAPI → (Multi-Agent Supervisor over 3 KAs + 2 Genies + 1 MCP) and/or (Lakebase Postgres for graph reads) → Unity Catalog tables and volumes that the data bundle owns.

The agents are stateless; everything reproducible from the bundle.

---

## Demo, support, contributing

- **Live demo workspace**: `https://the-fins-aml-app-7474649573853836.aws.databricksapps.com` *(Databricks-internal)*
- **Issues / bugs**: open a GitHub issue on this repo
- **Contributing**: see [CONTRIBUTING.md](CONTRIBUTING.md). Bricksters only per FE policy
- **Security disclosures**: see [SECURITY.md](SECURITY.md)
- **License**: [Databricks License](LICENSE.md)

---

## Credits

Built by the Databricks FSI ProServ + AI Acceleration teams:
**Emerson Bayuk** · **Kateryna Savchyn** · **Mimi Park** · **Pavithra Rao**

Powered by Databricks Apps, Unity Catalog, Agent Bricks (Knowledge Assistants, Genie Spaces, Multi-Agent Supervisors), Vector Search, AI Gateway, and Lakebase.
