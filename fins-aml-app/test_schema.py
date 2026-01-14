import os
from databricks import sql

# Test the actual schema
def test_schema():
    token = os.getenv('DATABRICKS_TOKEN', 'dummy')
    warehouse_id = os.getenv('DATABRICKS_WAREHOUSE_ID', 'dummy')

    if token == 'dummy':
        print("No token available for testing")
        return

    try:
        with sql.connect(
            server_hostname='fe-vm-industry-solutions-buildathon.cloud.databricks.com',
            http_path=f'/sql/1.0/warehouses/{warehouse_id}',
            access_token=token
        ) as connection:

            cursor = connection.cursor()

            # Test alerts table structure
            print("=== ALERTS TABLE ===")
            cursor.execute("DESCRIBE fins_aml.data_generation.alerts")
            alerts_schema = cursor.fetchall()
            for col in alerts_schema:
                print(f"{col[0]}: {col[1]}")

            # Sample a few rows
            print("\n=== ALERTS SAMPLE ===")
            cursor.execute("SELECT * FROM fins_aml.data_generation.alerts LIMIT 3")
            alerts_sample = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            print("Columns:", columns)

            print("\n=== CASES TABLE ===")
            cursor.execute("DESCRIBE fins_aml.data_generation.cases")
            cases_schema = cursor.fetchall()
            for col in cases_schema:
                print(f"{col[0]}: {col[1]}")

            print("\n=== GRAPH NODES TABLE ===")
            cursor.execute("DESCRIBE fins_aml.data_generation.graph_nodes")
            nodes_schema = cursor.fetchall()
            for col in nodes_schema:
                print(f"{col[0]}: {col[1]}")

            print("\n=== GRAPH EDGES TABLE ===")
            cursor.execute("DESCRIBE fins_aml.data_generation.graph_edges")
            edges_schema = cursor.fetchall()
            for col in edges_schema:
                print(f"{col[0]}: {col[1]}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_schema()