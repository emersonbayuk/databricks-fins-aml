"""
Database service for connecting to Databricks SQL
"""

import os
import asyncio
import logging
import json
import time
from typing import List, Dict, Any, Optional
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Simple in-memory cache (can be replaced with Redis in production)
_cache = {}
_cache_timestamps = {}

class DatabaseService:
    """Service for handling Databricks SQL connections and queries using SDK"""

    def __init__(self, warehouse_id: str, hostname: str = None):
        from backend import config
        self.warehouse_id = warehouse_id
        self.hostname = hostname or config.DATABRICKS_HOSTNAME
        self._client = None
        self._max_retries = 3
        logger.info("Initializing database service with Databricks SDK")

    def _get_workspace_client(self):
        """Get or create WorkspaceClient with proper authentication"""
        if self._client is None:
            client_id = os.getenv('DATABRICKS_CLIENT_ID')
            client_secret = os.getenv('DATABRICKS_CLIENT_SECRET')

            if client_id and client_secret:
                # Use Service Principal authentication (OAuth M2M)
                logger.info(f"Using Service Principal authentication (client_id: {client_id[:8]}...)")
                self._client = WorkspaceClient(
                    host=f"https://{self.hostname}",
                    client_id=client_id,
                    client_secret=client_secret,
                    auth_type='oauth-m2m'
                )
            else:
                # Fallback to default SDK auth chain with profile (for local development)
                logger.info("No SP credentials found, using default SDK authentication with profile")
                self._client = WorkspaceClient(
                    host=f"https://{self.hostname}",
                    profile='fevm-fins-demo'
                )
        return self._client

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None, cache_ttl: Optional[int] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query using SDK and return results as list of dictionaries"""
        # Check cache if TTL is specified
        if cache_ttl:
            cache_key = self._get_cache_key(query, params)
            cached_result = self._get_cached_result(cache_key, cache_ttl)
            if cached_result is not None:
                logger.info(f"Cache hit for query: {query[:50]}...")
                return cached_result

        last_error = None
        for attempt in range(self._max_retries):
            try:
                # Run SDK call in thread pool since it's sync
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self._execute_with_sdk,
                    query,
                    params
                )

                # Cache result if TTL is specified
                if cache_ttl:
                    self._cache_result(cache_key, result)
                    logger.info(f"Cached query result for {cache_ttl} seconds")

                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Query attempt {attempt + 1}/{self._max_retries} failed: {type(e).__name__}: {str(e)[:100]}")

                if attempt < self._max_retries - 1:
                    logger.info(f"Retrying in {2 ** attempt} seconds...")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

        # If we exhausted all retries
        logger.error(f"Query failed after {self._max_retries} attempts")
        logger.error(f"Query: {query[:200]}...")
        logger.error(f"Params: {params}")
        raise Exception(f"Database query failed after {self._max_retries} retries: {str(last_error)}")

    def _execute_with_sdk(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute query using Databricks SDK (synchronous)"""
        client = self._get_workspace_client()

        # Handle parameterized queries by substituting params into query
        if params:
            for key, value in params.items():
                # Simple parameter substitution - in production use proper SQL parameter binding
                if isinstance(value, str):
                    query = query.replace(f":{key}", f"'{value}'")
                else:
                    query = query.replace(f":{key}", str(value))

        logger.debug(f"Executing SQL query: {query[:100]}...")

        # Submit the statement
        try:
            response = client.statement_execution.execute_statement(
                warehouse_id=self.warehouse_id,
                statement=query,
                wait_timeout="0s"  # Immediate return, we poll manually
            )
        except Exception as e:
            raise Exception(f"Failed to submit SQL query: {str(e)}")

        statement_id = response.statement_id
        logger.debug(f"Statement submitted with ID: {statement_id}")

        # Poll for completion
        timeout = 180
        poll_interval = 2
        elapsed = 0

        while elapsed < timeout:
            try:
                status = client.statement_execution.get_statement(statement_id=statement_id)
            except Exception as e:
                raise Exception(f"Failed to check status: {str(e)}")

            state = status.status.state

            if state == StatementState.SUCCEEDED:
                return self._extract_results(status)

            if state == StatementState.FAILED:
                error_msg = status.status.error.message if status.status.error else "Unknown error"
                raise Exception(f"SQL query failed: {error_msg}")

            if state == StatementState.CANCELED:
                raise Exception("SQL query was canceled")

            # Still running, wait and poll again
            time.sleep(poll_interval)
            elapsed += poll_interval

        # Timeout reached
        try:
            client.statement_execution.cancel_execution(statement_id=statement_id)
        except:
            pass
        raise Exception(f"SQL query timed out after {timeout} seconds")

    def _extract_results(self, response) -> List[Dict[str, Any]]:
        """Extract results from a successful statement response"""
        if not response.result or not response.result.data_array:
            return []

        # Get column names from schema
        columns = []
        if response.manifest and response.manifest.schema and response.manifest.schema.columns:
            columns = [col.name for col in response.manifest.schema.columns]

        # Convert data array to list of dicts
        results = []
        for row in response.result.data_array:
            row_dict = {}
            for i, col_name in enumerate(columns):
                if i < len(row):
                    row_dict[col_name] = row[i]
            results.append(row_dict)

        return results

    def _get_cache_key(self, query: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key from query and parameters"""
        key_data = {"query": query, "params": params or {}}
        return str(hash(json.dumps(key_data, sort_keys=True)))

    def _get_cached_result(self, cache_key: str, ttl: int) -> Optional[List[Dict[str, Any]]]:
        """Get cached result if still valid"""
        if cache_key in _cache and cache_key in _cache_timestamps:
            cached_time = _cache_timestamps[cache_key]
            if datetime.now() - cached_time < timedelta(seconds=ttl):
                return _cache[cache_key]
        return None

    def _cache_result(self, cache_key: str, result: List[Dict[str, Any]]):
        """Cache query result with timestamp"""
        _cache[cache_key] = result
        _cache_timestamps[cache_key] = datetime.now()

    async def test_connection(self) -> bool:
        """Test database connection"""
        try:
            result = await self.execute_query("SELECT 1 as test")
            return len(result) == 1 and result[0]["test"] == 1
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    async def close(self):
        """Close database connection"""
        # SDK client doesn't need explicit closing
        self._client = None
        logger.info("Database service closed")