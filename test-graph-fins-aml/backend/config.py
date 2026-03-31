"""
Centralized configuration module for FINS AML Platform.

All environment-specific values are read from environment variables
with sensible defaults (current dev workspace values).
"""

import os

# Databricks Workspace
DATABRICKS_HOSTNAME = os.getenv(
    "DATABRICKS_HOSTNAME",
    "fe-vm-industry-solutions-buildathon.cloud.databricks.com"
)
DATABRICKS_WORKSPACE_URL = f"https://{DATABRICKS_HOSTNAME}"
DATABRICKS_WORKSPACE_ID = os.getenv("DATABRICKS_WORKSPACE_ID", "237438879023004")

# SQL Warehouse - injected by Databricks Apps runtime
DATABRICKS_WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "192fe959f141d27c")

# Service Principal Auth (if needed for other APIs)
# The Databricks Apps runtime automatically handles OAuth for SQL connections
DATABRICKS_CLIENT_ID = os.getenv("DATABRICKS_CLIENT_ID")
DATABRICKS_CLIENT_SECRET = os.getenv("DATABRICKS_CLIENT_SECRET")

# MAS Agent Endpoint
MAS_ENDPOINT_URL = os.getenv(
    "MAS_ENDPOINT_URL",
    f"https://{DATABRICKS_HOSTNAME}/serving-endpoints/mas-e3a6f805-endpoint/invocations"
)

# Dashboard Embedding
DASHBOARD_ID = os.getenv("DATABRICKS_DASHBOARD_ID", "01f127b9372c1c4f850385353803dd0f")

# Catalog / Schema
CATALOG = os.getenv("DATABRICKS_CATALOG", "fins_aml")
SCHEMA = os.getenv("DATABRICKS_SCHEMA", "data_generation")


def table(name: str) -> str:
    """Return fully-qualified table name."""
    return f"{CATALOG}.{SCHEMA}.{name}"


# Volume base path
VOLUME_BASE = f"/Volumes/{CATALOG}/{SCHEMA}/knowledge_base"
VOLUMES = {
    "edd": f"{VOLUME_BASE}/edd_memos/",
    "media": f"{VOLUME_BASE}/adverse_media/",
    "sar": f"{VOLUME_BASE}/sar_narratives/",
    "case_notes": f"{VOLUME_BASE}/case_notes/",
}
