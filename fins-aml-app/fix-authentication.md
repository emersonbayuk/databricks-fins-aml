# Fix Sherlock-AML Authentication Issues

## Quick Fix (No Neo4j, No Service Principal)

Your app isn't showing data because it needs proper Databricks authentication. Here's the minimal fix:

### Step 1: Generate a Databricks Personal Access Token (PAT)

1. Go to https://e2-demo-west.cloud.databricks.com
2. Click your username (top right) → User Settings
3. Access Tokens → Generate New Token
4. Give it a name like "sherlock-aml-app"
5. Set expiration (90 days recommended)
6. **SAVE THIS TOKEN** - you'll need it in Step 3

### Step 2: Check Dashboard Permissions

Your dashboard ID: `01f1175919d61bb89245b4ff377e7e1e`

1. Navigate to your dashboard in Databricks
2. Click "Share" button
3. Make sure it's shared with:
   - Your user account (kateryna.savchyn@databricks.com)
   - Set to "CAN RUN" permission

### Step 3: Set App Secret

1. Go to https://e2-demo-west.cloud.databricks.com
2. Navigate to: **Compute** → **Apps** → **sherlock-aml**
3. Click on **Configuration** or **Settings**
4. Under **Secrets**, set:
   - `secret`: [Paste your PAT token from Step 1]

### Step 4: Redeploy the App

Run this command:
```bash
# Upload your updated code (with Neo4j disabled)
databricks workspace import-dir ~/code/sherlock-aml \
  /Workspace/Users/kateryna.savchyn@databricks.com/sherlock-aml \
  --profile e2-demo-west-new --overwrite

# Restart the app to pick up the new secret
databricks apps stop sherlock-aml --profile e2-demo-west-new
databricks apps start sherlock-aml --profile e2-demo-west-new
```

### Step 5: Verify It's Working

1. Open: https://sherlock-aml-2556758628403379.aws.databricksapps.com
2. The dashboard and investigations should now load!

## Optional: Enable Graph Features with Neo4j

If you want the graph visualization features:

1. Create a free Neo4j Aura instance: https://neo4j.com/cloud/aura-free/
2. Update `app.yaml` to uncomment Neo4j settings and add your credentials
3. Set `secret-2` in the app configuration to your Neo4j password
4. Redeploy

## Troubleshooting

If still not working, check:

1. **SQL Warehouse Access**:
   - Go to SQL Warehouses → Select your warehouse
   - Permissions → Make sure your user has "CAN USE"

2. **Check Logs**:
   ```bash
   databricks apps get sherlock-aml --profile e2-demo-west-new
   ```

3. **Test the API directly**:
   ```bash
   curl https://sherlock-aml-2556758628403379.aws.databricksapps.com/api/auth/workspace-info
   ```

## About Service Principals (Advanced)

Service principals are only needed if you want:
- External users (without Databricks accounts) to access the dashboard
- Programmatic access without user authentication
- Dark mode dashboard embedding with the AIBI client

For internal use with your Databricks account, the PAT token is sufficient!