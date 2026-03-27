"""
Database service for connecting to Databricks SQL using Service Principal auth
"""

import os
import asyncio
import logging
import json
import time
from typing import List, Dict, Any, Optional
from databricks import sql
from databricks.sql.exc import ServerOperationError, RequestError, SessionAlreadyClosedError
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Simple in-memory cache (can be replaced with Redis in production)
_cache = {}
_cache_timestamps = {}

class DatabaseService:
    """Service for handling Databricks SQL connections and queries"""

    def __init__(self, warehouse_id: str, token: str = None, hostname: str = None):
        from backend import config
        self.warehouse_id = warehouse_id
        self.hostname = hostname or config.DATABRICKS_HOSTNAME

        # Check for SP credentials first (injected by Databricks Apps runtime)
        self.client_id = os.getenv("DATABRICKS_CLIENT_ID") or config.DATABRICKS_CLIENT_ID
        self.client_secret = os.getenv("DATABRICKS_CLIENT_SECRET") or config.DATABRICKS_CLIENT_SECRET

        # Fall back to token if SP creds not available
        self.token = token or config.DATABRICKS_TOKEN

        self._connection = None
        self._last_connection_time = None
        self._connection_timeout = 300  # 5 minutes
        self._max_retries = 3

        # Log which auth method we're using
        if self.client_id and self.client_secret:
            logger.info(f"Using Service Principal authentication (client_id: {self.client_id[:8]}...)")
        elif self.token and self.token != "dummy_token":
            logger.info("Using token authentication")
        else:
            logger.warning("No valid authentication method available - will use dummy data")

    async def get_connection(self, force_refresh=False):
        """Get or create a database connection with automatic refresh"""
        # Check if we need to refresh the connection
        should_refresh = (
            force_refresh or
            not self._connection or
            (self._last_connection_time and
             time.time() - self._last_connection_time > self._connection_timeout)
        )

        if should_refresh:
            await self._close_connection()
            try:
                # Run connection creation in thread pool since databricks.sql is sync
                loop = asyncio.get_event_loop()

                # Use appropriate auth method
                if self.client_id and self.client_secret:
                    # Use Service Principal authentication
                    self._connection = await loop.run_in_executor(
                        None,
                        lambda: sql.connect(
                            server_hostname=self.hostname,
                            http_path=f"/sql/1.0/warehouses/{self.warehouse_id}",
                            # The Databricks Apps runtime handles OAuth automatically
                            # when DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET are set
                            auth_type="databricks-oauth"
                        )
                    )
                    logger.info("Database connection established using Service Principal")
                elif self.token and self.token != "dummy_token":
                    # Use token authentication
                    self._connection = await loop.run_in_executor(
                        None,
                        lambda: sql.connect(
                            server_hostname=self.hostname,
                            http_path=f"/sql/1.0/warehouses/{self.warehouse_id}",
                            access_token=self.token
                        )
                    )
                    logger.info("Database connection established using token")
                else:
                    logger.warning("No valid authentication available")
                    return None

                self._last_connection_time = time.time()
            except Exception as e:
                logger.error(f"Failed to create database connection: {e}")
                self._connection = None
                # Don't raise here - let the app fall back to dummy data
                return None
        return self._connection

    async def _close_connection(self):
        """Safely close existing connection"""
        if self._connection:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._connection.close)
            except Exception as e:
                logger.debug(f"Error closing old connection (may be already closed): {e}")
            finally:
                self._connection = None

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None, cache_ttl: Optional[int] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results as list of dictionaries with retry logic"""
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
                # Get connection (will refresh if needed)
                connection = await self.get_connection()

                if not connection:
                    logger.warning("No connection available, returning empty result")
                    return []

                # Execute query in thread pool
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self._execute_sync_query,
                    connection,
                    query,
                    params
                )

                # Cache the result if TTL is specified
                if cache_ttl and result is not None:
                    self._cache_result(cache_key, result, cache_ttl)

                return result

            except (ServerOperationError, RequestError, SessionAlreadyClosedError) as e:
                last_error = e
                logger.warning(f"Attempt {attempt + 1} failed with error: {e}")

                if attempt < self._max_retries - 1:
                    # Force connection refresh on next attempt
                    await self.get_connection(force_refresh=True)
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

            except Exception as e:
                logger.error(f"Unexpected error executing query: {e}")
                last_error = e
                break

        logger.error(f"Failed to execute query after {self._max_retries} attempts. Last error: {last_error}")
        return []  # Return empty list to trigger fallback data

    def _execute_sync_query(self, connection, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a synchronous query and return results"""
        cursor = connection.cursor()
        try:
            # Log the query being executed (truncate for readability)
            query_preview = query[:200] + "..." if len(query) > 200 else query
            logger.info(f"Executing query: {query_preview}")

            if params:
                # Use parameterized query
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Fetch all results
            rows = cursor.fetchall()

            # Convert to list of dictionaries
            if rows:
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in rows]
            else:
                return []

        finally:
            cursor.close()

    def _get_cache_key(self, query: str, params: Optional[Dict[str, Any]]) -> str:
        """Generate a cache key from query and params"""
        import hashlib
        key_str = f"{query}:{json.dumps(params, sort_keys=True) if params else ''}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _get_cached_result(self, cache_key: str, ttl: int) -> Optional[List[Dict[str, Any]]]:
        """Get cached result if still valid"""
        if cache_key in _cache and cache_key in _cache_timestamps:
            age = time.time() - _cache_timestamps[cache_key]
            if age < ttl:
                return _cache[cache_key]
        return None

    def _cache_result(self, cache_key: str, result: List[Dict[str, Any]], ttl: int):
        """Cache a query result"""
        _cache[cache_key] = result
        _cache_timestamps[cache_key] = time.time()

    async def close(self):
        """Close the database connection"""
        await self._close_connection()