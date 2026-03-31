# Stashed Neo4j Integration

These files contain the original Neo4j Aura graph database integration for SherlockAML. They were stashed (not deleted) when the graph visualization was migrated from Neo4j to native Databricks graph tables (`graph_nodes` / `graph_edges`).

## What's Here

| File | Purpose |
|---|---|
| `neo4j_service.py` | Neo4j Aura connection service — connects via `neo4j+s://` URI, queries Cypher, converts paths to Cytoscape format |
| `neo4j_graph.py` | FastAPI router with endpoints: `/graph/customer/{id}`, `/graph/transactions/{id}`, `/graph/network/{id}`, health checks |

## How to Restore

To re-enable Neo4j:

1. Copy the files back:
   ```bash
   cp _stashed_neo4j/neo4j_service.py backend/services/
   cp _stashed_neo4j/neo4j_graph.py backend/api/
   ```

2. In `main.py`, replace the Databricks graph router import with:
   ```python
   from backend.api.neo4j_graph import router as neo4j_router
   app.include_router(neo4j_router, prefix="/api", tags=["neo4j"])
   ```

3. In `frontend/build/index.html`, change the graph API URL from:
   ```
   /api/databricks-graph/graph/customer/...
   ```
   back to:
   ```
   /api/graph/customer/...
   ```

4. Add `neo4j>=5.26.0` back to `requirements.txt`

5. Re-add Neo4j env vars to `config.py` and `app.yaml`:
   ```python
   NEO4J_URI = os.getenv("NEO4J_URI", "")
   NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
   NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
   NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")
   ```

6. Add the `secret-2` resource back to `app.yaml` for Neo4j password injection

## Why It Was Stashed

The Neo4j integration required an external Neo4j Aura instance, adding deployment complexity and cost. The native Databricks approach queries `graph_nodes` and `graph_edges` tables directly via the SQL warehouse — no external dependency, same OAuth M2M auth as the rest of the app.

## Neo4j Aura Instance (for reference)

- Instance ID: `398dd975`
- URI: `neo4j+s://398dd975.databases.neo4j.io`
- Region: AWS US East (us-east-1)
- Type: AuraDB Professional
