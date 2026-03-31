# FINS AML Data Bundle

This bundle creates the data pipeline and dashboard for the FINS AML (Anti-Money Laundering) demo application.

## Prerequisites

- Databricks CLI installed and configured
- Unity Catalog enabled workspace
- SQL Warehouse available
- Appropriate permissions to create tables and dashboards

## Deployment Instructions

### 1. Configure Your Databricks CLI Profile

Make sure you have a profile configured for your target workspace:
```bash
databricks configure --profile <your-profile-name>
```

### 2. Find Your SQL Warehouse ID

```bash
databricks warehouses list --profile <your-profile-name>
```
Note the ID of the warehouse you want to use.

### 3. Deploy the Data Bundle

```bash
databricks bundle deploy --profile <your-profile-name> \
  --var="catalog=<your-catalog>" \
  --var="schema=<your-schema>" \
  --var="warehouse_id=<your-warehouse-id>" \
  --var="force_rebuild=true"  # Use false to preserve existing data
```

Example:
```bash
databricks bundle deploy --profile fevm-fins-demo \
  --var="catalog=fins_aml" \
  --var="schema=data_generation" \
  --var="warehouse_id=192fe959f141d27c" \
  --var="force_rebuild=false"
```

### 4. Run the Data Generation Pipeline

```bash
databricks bundle run aml_data_generation_pipeline --profile <your-profile-name>
```

This will:
1. Process the dashboard template with your catalog/schema
2. Generate base AML data tables
3. Perform watchlist screening
4. Create graph features
5. Generate knowledge base documents (if not already present)

## Output for App Bundle Deployment

After successful deployment, provide these values to whoever is deploying the app bundle:

| Parameter | Value | Where to Find |
|-----------|-------|---------------|
| **catalog** | Your chosen catalog | Same as `--var="catalog=..."` |
| **schema** | Your chosen schema | Same as `--var="schema=..."` |
| **warehouse_id** | Your warehouse ID | Same as `--var="warehouse_id=..."` |
| **dashboard_id** | Dashboard ID | After deployment, go to Dashboards page and find "AML Executive Dashboard" |

### Tables Created

The pipeline creates these tables in `<catalog>.<schema>`:
- `customers` - Customer master data
- `transactions` - Transaction records
- `accounts` - Account information
- `alerts` - AML alerts
- `sars` - Suspicious Activity Reports
- `watchlist` - Watchlist screening results
- `graph_features` - Graph analytics features

### Knowledge Base Volume

Unstructured documents are stored in:
```
/Volumes/<catalog>/<schema>/aml_knowledge_base/
```

Including:
- SAR narratives
- Case notes
- EDD memos
- Adverse media reports
- Correspondence logs
- Policy documents

## Efficiency Features

The pipeline includes smart caching:
- **Dashboard Template**: Only regenerates when catalog/schema changes
- **Knowledge Base Documents**: Checks if files exist before regenerating (saves LLM processing time)
- **Force Rebuild**: Set to `false` to preserve existing data and only fill gaps

## Troubleshooting

### Authentication Error
Make sure your Databricks CLI profile is correctly configured and has access to the workspace.

### Warehouse Not Found
Verify the warehouse_id using:
```bash
databricks warehouses list --profile <your-profile-name>
```

### Dashboard Not Appearing
After the job completes, the dashboard should appear in the Dashboards section. If not, check the job logs for errors in the `process_dashboard_template` task.

### Knowledge Base Generation Slow
The knowledge base step uses LLMs to generate documents. If files already exist, it will skip regeneration. To force regeneration, delete the files in the Volume path first.

## Support

For issues or questions, please reach out to the FINS team.