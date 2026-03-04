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

# Tokens & Auth
# A single PAT is used for all Databricks API calls (SQL warehouse, serving
# endpoints, and dashboard-embedding fallback).  The Databricks Apps runtime
# injects this automatically via the ``secret`` resource in app.yaml.
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN")
DATABRICKS_WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID", "dummy_warehouse")
DATABRICKS_CLIENT_ID = os.getenv("DATABRICKS_CLIENT_ID")
DATABRICKS_CLIENT_SECRET = os.getenv("DATABRICKS_CLIENT_SECRET")

# MAS Agent Endpoint
MAS_ENDPOINT_URL = os.getenv(
    "MAS_ENDPOINT_URL",
    f"https://{DATABRICKS_HOSTNAME}/serving-endpoints/mas-e3a6f805-endpoint/invocations"
)

# Neo4j
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://398dd975.databases.neo4j.io")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Dashboard Embedding
DASHBOARD_ID = os.getenv("DATABRICKS_DASHBOARD_ID", "01f0ef2a97ed176dbe998b9ec4577b1b")

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
