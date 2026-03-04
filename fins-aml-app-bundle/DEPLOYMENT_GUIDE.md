# FINS AML App Bundle — New Environment Deployment Guide

This document lists every file and line that must be edited to deploy this app to a new Databricks workspace.

---

## Prerequisites

Before editing config files, gather these values from your target workspace:

| Value | Where to find it |
|---|---|
| **Workspace hostname** | URL bar, e.g. `my-workspace.cloud.databricks.com` |
| **Workspace ID** | URL `?o=` parameter, or Workspace Settings |
| **SQL Warehouse ID** | SQL Warehouses page → copy ID |
| **Dashboard ID** | Open dashboard → ID in URL (`/dashboards/<id>`) |
| **MAS endpoint URL** | Serving Endpoints → your MAS endpoint → full invocation URL |
| **Service principal client ID** | Settings → Identity & Access → Service Principals |
| **Service principal secret** | Service principal → Secrets → Generate |
| **Neo4j URI / password** | Neo4j Aura console (if using graph features) |
| **Unity Catalog / Schema** | The catalog and schema where AML tables live |
| **Databricks CLI profile** | `~/.databrickscfg` profile name for the target workspace |

---

## Files to Edit

### 1. `databricks.yml` — Add a new target block

Add a new target under the `targets:` section (or modify an existing one).

**Lines 30–55** — Add a block like:

```yaml
targets:
  my-new-env:                        # choose a target name
    workspace:
      host: https://YOUR_HOSTNAME    # line: workspace.host
    variables:
      databricks_hostname: "YOUR_HOSTNAME"
      workspace_id: "YOUR_WORKSPACE_ID"
      warehouse_id: "YOUR_WAREHOUSE_ID"
      mas_endpoint_url: "https://YOUR_HOSTNAME/serving-endpoints/YOUR_MAS_ENDPOINT/invocations"
      neo4j_uri: "neo4j+s://YOUR_NEO4J_INSTANCE.databases.neo4j.io"
      dashboard_id: "YOUR_DASHBOARD_ID"
      catalog: "YOUR_CATALOG"
      schema: "YOUR_SCHEMA"
```

> Note: The bundle `variables` defined in `databricks.yml` are **not** automatically injected into the running app. They are only used by `databricks bundle` commands. The actual app reads env vars from `app.yaml` (see next step).

---

### 2. `app.yaml` — Update environment variable values

These are the env vars injected into the running Databricks App. Update every `value:` field to match your target workspace.

| Line | Env var | What to set |
|------|---------|-------------|
| 31 | `DATABRICKS_HOSTNAME` | Your workspace hostname (no `https://`) |
| 33 | `DATABRICKS_WORKSPACE_ID` | Your workspace ID |
| 35 | `DATABRICKS_DASHBOARD_ID` | Your published Lakeview dashboard ID |
| 37 | `DATABRICKS_CATALOG` | Unity Catalog name where AML tables live |
| 39 | `DATABRICKS_SCHEMA` | Schema name within that catalog |
| 41 | `MAS_ENDPOINT_URL` | Full MAS serving endpoint invocation URL |
| 43 | `NEO4J_URI` | Neo4j connection URI (or remove if not using) |

**Lines that are auto-resolved (do NOT hardcode):**
- Line 22: `DATABRICKS_WAREHOUSE_ID` — resolved from the `sql_warehouse` resource binding
- Line 24: `DATABRICKS_TOKEN` — injected automatically by Databricks Apps runtime
- Line 26: `NEO4J_PASSWORD` — injected from app secrets

**After deploying**, you must set the secrets via the Databricks Apps UI:
- `secret` → Your Databricks PAT or leave for Apps runtime auto-injection
- `secret-2` → Your Neo4j password

---

### 3. `backend/config.py` — Update default fallback values

These defaults are used when env vars are not set (e.g., local development). Update them to match your primary workspace, or leave them as-is if you always deploy via `app.yaml`.

| Line | Variable | Current default |
|------|----------|----------------|
| 12–13 | `DATABRICKS_HOSTNAME` | `fe-vm-industry-solutions-buildathon.cloud.databricks.com` |
| 16 | `DATABRICKS_WORKSPACE_ID` | `237438879023004` |
| 29–30 | `MAS_ENDPOINT_URL` | `https://{DATABRICKS_HOSTNAME}/serving-endpoints/mas-e3a6f805-endpoint/invocations` |
| 34 | `NEO4J_URI` | `neo4j+s://398dd975.databases.neo4j.io` |
| 40 | `DASHBOARD_ID` | `01f0ef2a97ed176dbe998b9ec4577b1b` |
| 43 | `CATALOG` | `fins_aml` |
| 44 | `SCHEMA` | `data_generation` |

> These defaults only matter for local dev. When deployed as a Databricks App, `app.yaml` env vars override all of them.

---

### 4. `backend/performance_improvements.py` — Hardcoded table names (known issue)

This file has **hardcoded** catalog.schema.table references instead of using `config.table()`. If your catalog/schema differ, update these lines:

| Line | Current value | Replace with |
|------|---------------|-------------|
| 139 | `fins_aml.data_generation.alerts` | `YOUR_CATALOG.YOUR_SCHEMA.alerts` |
| 140 | `fins_aml.data_generation.customers` | `YOUR_CATALOG.YOUR_SCHEMA.customers` |
| 188 | `fins_aml.data_generation.v_analyst_queue` | `YOUR_CATALOG.YOUR_SCHEMA.v_analyst_queue` |
| 201 | `fins_aml.data_generation.v_analyst_queue` | `YOUR_CATALOG.YOUR_SCHEMA.v_analyst_queue` |

> Ideally, refactor these to use `config.table()` like the rest of the codebase does.

---

### 5. `.env.example` — Update example values (optional)

If you want the example file to reflect the new environment, update lines 9–10, 19, 23–24, 27, 30, 33. This file is documentation only and does not affect the running app.

---

### 6. `frontend/build/index.html` — No changes needed

The frontend fetches workspace URL, workspace ID, and dashboard ID dynamically from the backend endpoint `/api/auth/workspace-info`. No hardcoded values need updating.

> Lines 19–20 contain old values in an HTML comment block (documentation only) — safe to ignore.

---

## Deployment Steps

```bash
# 1. Validate the bundle
databricks bundle validate -t my-new-env --profile YOUR_PROFILE

# 2. Deploy the bundle (uploads code to workspace)
databricks bundle deploy -t my-new-env --profile YOUR_PROFILE

# 3. Trigger the app deployment (starts/restarts the app)
databricks apps deploy fins-aml-platform --profile YOUR_PROFILE \
  --source-code-path /Workspace/Users/YOUR_EMAIL/.bundle/fins-aml-platform/my-new-env/files

# 4. Set app secrets in the Databricks UI
#    Navigate to: Apps → fins-aml-platform → Settings
#    - secret   → Databricks PAT (if not using Apps auto-injection)
#    - secret-2 → Neo4j password
```

---

## Dashboard Setup Checklist

For the embedded dashboard to work, you must also:

1. **Publish the Lakeview dashboard** — The embedding API uses `/published/tokeninfo`, which requires the dashboard to be published
2. **Create a service principal** — Settings → Identity & Access → Service Principals → Add
3. **Generate a secret** for the service principal and configure it as `DATABRICKS_CLIENT_ID` / `DATABRICKS_CLIENT_SECRET` in the app environment
4. **Grant dashboard access** — Share the dashboard with the service principal with **CAN RUN** permission
5. **Grant warehouse access** — The service principal needs **CAN USE** on the SQL warehouse

---

## Quick Reference — All Environment-Specific Values

| Value | `app.yaml` | `databricks.yml` | `backend/config.py` | `perf_improvements.py` |
|---|---|---|---|---|
| Hostname | line 31 | target → `databricks_hostname` | line 12–13 | — |
| Workspace ID | line 33 | target → `workspace_id` | line 16 | — |
| Warehouse ID | (auto-resolved) | target → `warehouse_id` | — | — |
| Dashboard ID | line 35 | target → `dashboard_id` | line 40 | — |
| Catalog | line 37 | target → `catalog` | line 43 | lines 139,140,188,201 |
| Schema | line 39 | target → `schema` | line 44 | lines 139,140,188,201 |
| MAS endpoint | line 41 | target → `mas_endpoint_url` | line 29–30 | — |
| Neo4j URI | line 43 | target → `neo4j_uri` | line 34 | — |
