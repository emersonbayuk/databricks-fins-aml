# FINS AML App Bundle — Deployment Guide

This document describes how to deploy the SherlockAML app to any Databricks workspace.

---

## Prerequisites

Before deploying, gather these values from your target workspace:

| Value | Where to find it |
|---|---|
| **Workspace hostname** | URL bar, e.g. `my-workspace.cloud.databricks.com` |
| **Workspace ID** | URL `?o=` parameter, or Workspace Settings |
| **SQL Warehouse ID** | SQL Warehouses page -> copy ID |
| **Dashboard ID** | Open dashboard -> ID in URL (`/dashboards/<id>`) |
| **MAS endpoint URL** | Serving Endpoints -> your MAS endpoint -> full invocation URL |
| **Neo4j URI / password** | Neo4j Aura console (if using graph features) |
| **Unity Catalog / Schema** | The catalog and schema where AML tables live |
| **Databricks CLI profile** | `~/.databrickscfg` profile name for the target workspace |

---

## Architecture

### Authentication

The app uses **OAuth M2M (service principal)** for all Databricks API calls:

- **SQL Warehouse queries** — Uses `databricks-sdk` credential provider (auto-refreshing tokens)
- **Serving endpoint calls** (MAS agent, SAR generation) — Uses OAuth token via `config.get_oauth_token()`
- **Dashboard embedding** — Uses service principal scoped token flow

The Databricks Apps runtime automatically injects `DATABRICKS_CLIENT_ID` and `DATABRICKS_CLIENT_SECRET` for the app's service principal. **No PAT token is required.**

A PAT (`DATABRICKS_TOKEN`) is supported as an optional fallback for local development only.

### Parameterization

All workspace-specific values in `app.yaml` use `${var.xxx}` bundle variable references. These are resolved from `databricks.yml` at deploy time. **You never need to edit `app.yaml` or `config.py` when deploying to a new workspace** — just add a target block to `databricks.yml`.

---

## Deploying to a New Workspace

### Step 1: Add a target to `databricks.yml`

Add a new block under `targets:`:

```yaml
targets:
  my-new-workspace:
    workspace:
      host: https://my-workspace.cloud.databricks.com
    variables:
      databricks_hostname: "my-workspace.cloud.databricks.com"
      workspace_id: "1234567890"
      warehouse_id: "abc123def456"
      catalog: "fins_aml"
      schema: "data_generation"
      mas_endpoint_url: "https://my-workspace.cloud.databricks.com/serving-endpoints/my-mas/invocations"
      dashboard_id: "your-dashboard-id"
      neo4j_uri: "neo4j+s://xxx.databases.neo4j.io"
```

Variables with defaults (`catalog`, `schema`, `neo4j_user`, `neo4j_database`, `mas_endpoint_url`, `neo4j_uri`, `dashboard_id`) can be omitted if the defaults are acceptable.

### Step 2: Deploy the bundle

```bash
# Validate
databricks bundle validate -t my-new-workspace --profile YOUR_PROFILE

# Deploy (uploads code to workspace)
databricks bundle deploy -t my-new-workspace --profile YOUR_PROFILE

# Start/restart the app
databricks apps deploy fins-aml-platform --profile YOUR_PROFILE \
  --source-code-path /Workspace/Users/YOUR_EMAIL/.bundle/fins-aml-platform/my-new-workspace/files
```

### Step 3: Configure app secrets

In the Databricks UI, navigate to **Apps -> fins-aml-platform -> Resources** and set:

- `secret-2` -> Your Neo4j password (required for graph features)

No PAT secret is needed — the app authenticates via the auto-injected service principal.

### Step 4: Grant permissions

The app's service principal needs:

1. **CAN USE** on the SQL warehouse
2. **CAN QUERY** on the MAS serving endpoint
3. **CAN RUN** on the published Lakeview dashboard (for embedding)

---

## Files Overview

| File | Purpose | Edit needed for new workspace? |
|---|---|---|
| `databricks.yml` | Bundle config with targets and variables | **Yes** — add a target block |
| `app.yaml` | App runtime config with `${var.xxx}` references | No |
| `backend/config.py` | Python config with OAuth M2M token management | No |
| `backend/api/agent.py` | MAS agent chat (OAuth auth) | No |
| `backend/api/sar.py` | SAR narrative generation (OAuth auth) | No |
| `backend/api/auth.py` | Dashboard embedding auth flow | No |
| `backend/services/database.py` | SQL warehouse connection (OAuth credential provider) | No |
| `main.py` | FastAPI app entrypoint | No |
| `requirements.txt` | Python dependencies (includes `databricks-sdk`) | No |
| `frontend/build/index.html` | React frontend (fetches config from API at runtime) | No |
| `.env.example` | Example env vars for local development | No |

---

## Environment Variables

### Auto-injected by Databricks Apps runtime
| Variable | Description |
|---|---|
| `DATABRICKS_HOST` | Workspace URL |
| `DATABRICKS_CLIENT_ID` | Service principal OAuth client ID |
| `DATABRICKS_CLIENT_SECRET` | Service principal OAuth secret |

### Resolved from bundle variables (via `app.yaml`)
| Variable | Bundle variable | Default |
|---|---|---|
| `DATABRICKS_HOSTNAME` | `databricks_hostname` | (required) |
| `DATABRICKS_WORKSPACE_ID` | `workspace_id` | (required) |
| `DATABRICKS_WAREHOUSE_ID` | (auto from sql_warehouse resource) | — |
| `DATABRICKS_CATALOG` | `catalog` | `fins_aml` |
| `DATABRICKS_SCHEMA` | `schema` | `data_generation` |
| `DATABRICKS_DASHBOARD_ID` | `dashboard_id` | `""` |
| `MAS_ENDPOINT_URL` | `mas_endpoint_url` | `""` |
| `NEO4J_URI` | `neo4j_uri` | `""` |
| `NEO4J_USER` | `neo4j_user` | `neo4j` |
| `NEO4J_DATABASE` | `neo4j_database` | `neo4j` |

### From app secrets
| Variable | Secret resource | Description |
|---|---|---|
| `NEO4J_PASSWORD` | `secret-2` | Neo4j Aura password |

---

## Local Development

For local development without the Databricks Apps runtime:

1. Copy `.env.example` to `.env`
2. Fill in `DATABRICKS_CLIENT_ID` and `DATABRICKS_CLIENT_SECRET` (or `DATABRICKS_TOKEN` as fallback)
3. Fill in all workspace-specific values
4. Run: `uvicorn main:app --host 0.0.0.0 --port 8000`

---

## Dashboard Setup

For the embedded executive dashboard to work:

1. **Create and publish** a Lakeview dashboard with the AML queries
2. **Share** the dashboard with the app's service principal (**CAN RUN**)
3. **Set** the `dashboard_id` variable in your target block
4. The dashboard theme is controlled by its `uiSettings.theme` — set the `light` mode colors for the embed view
