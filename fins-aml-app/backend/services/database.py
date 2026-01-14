"""
Database service for connecting to Databricks SQL
"""

import os
import asyncio
import logging
import json
from typing import List, Dict, Any, Optional
from databricks import sql
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Simple in-memory cache (can be replaced with Redis in production)
_cache = {}
_cache_timestamps = {}

class DatabaseService:
    """Service for handling Databricks SQL connections and queries"""

    def __init__(self, warehouse_id: str, token: str = None, hostname: str = "fe-vm-industry-solutions-buildathon.cloud.databricks.com"):
        self.warehouse_id = warehouse_id
        self.token = token or os.getenv('DATABRICKS_TOKEN') or "dummy_token"
        self.hostname = hostname
        self._connection = None

    async def get_connection(self):
        """Get or create a database connection"""
        if not self._connection:
            try:
                # Run connection creation in thread pool since databricks.sql is sync
                loop = asyncio.get_event_loop()
                self._connection = await loop.run_in_executor(
                    None,
                    lambda: sql.connect(
                        server_hostname=self.hostname,
                        http_path=f"/sql/1.0/warehouses/{self.warehouse_id}",
                        access_token=self.token
                    )
                )
                logger.info("Database connection established")
            except Exception as e:
                logger.error(f"Failed to create database connection: {e}")
                raise
        return self._connection

    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None, cache_ttl: Optional[int] = None) -> List[Dict[str, Any]]:
        """Execute a SQL query and return results as list of dictionaries"""
        try:
            # Check cache if TTL is specified
            if cache_ttl:
                cache_key = self._get_cache_key(query, params)
                cached_result = self._get_cached_result(cache_key, cache_ttl)
                if cached_result is not None:
                    logger.info(f"Cache hit for query: {query[:50]}...")
                    return cached_result

            connection = await self.get_connection()

            # Execute query in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._execute_sync_query,
                connection,
                query,
                params
            )

            # Cache result if TTL is specified
            if cache_ttl:
                self._cache_result(cache_key, result)
                logger.info(f"Cached query result for {cache_ttl} seconds")

            return result

        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Params: {params}")
            raise Exception(f"Database query failed: {str(e)}")

    def _execute_sync_query(self, connection, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Synchronous query execution (run in thread pool)"""
        with connection.cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            # Get column names
            columns = [col[0] for col in cursor.description] if cursor.description else []

            # Fetch all rows and convert to list of dicts
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]

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
        if self._connection:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, self._connection.close)
                logger.info("Database connection closed")
            except Exception as e:
                logger.error(f"Error closing connection: {e}")
            finally:
                self._connection = None