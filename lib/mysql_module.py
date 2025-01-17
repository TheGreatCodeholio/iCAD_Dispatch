#!/usr/bin/env python3
# MySQL

"""
Author: Ian Carey
Date: 2020-23-04
Description: A MySQL module with built-in query caching via Redis

Usage: In main script import and start MySQLDatabase
`db = MySQLDatabase(config_data)`

Requirements:
- Python 3.12+
- mysql-connector-python~=9.1.0
- redis~=5.2.1

"""

import datetime
import hashlib
import json
import logging
import math
import os
import re
from decimal import Decimal

import mysql.connector
import redis

module_logger = logging.getLogger('flask_login.mysql')

class MySQLDatabase:
    """
       Represents a MySQL database with on-demand connection creation and Redis caching.

       Attributes:
           dbconfig (dict): Configuration data for the MySQL connection.
           redis_host (str): Hostname for the Redis server.
           redis_port (int): Port for the Redis server.
           redis_password (str): Password for the Redis server.
           redis_client (redis.StrictRedis): Redis client instance for caching.
    """

    def __init__(self):
        """
        Initialize the MySQLDatabase with MySQL and Redis configuration data.

        Raises:
            ValueError: If any required configuration data is missing.
        """

        # Validate MySQL configuration
        required_mysql_keys = ["MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE", "MYSQL_PORT"]
        for key in required_mysql_keys:
            if not os.getenv(key):
                raise ValueError(f"Missing required MySQL environment variable: '{key}'")

        # Validate Redis configuration
        required_redis_keys = ["REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD", "REDIS_MYSQL_CACHE_DB"]
        for key in required_redis_keys:
            if not os.getenv(key):
                raise ValueError(f"Missing required Redis environment variable: '{key}'")

        # MySQL configuration
        self.dbconfig = {
            "host": os.getenv("MYSQL_HOST"),
            "user": os.getenv("MYSQL_USER"),
            "password": os.getenv("MYSQL_PASSWORD"),
            "database": os.getenv("MYSQL_DATABASE"),
            "port": int(os.getenv("MYSQL_PORT"))
        }

        # Redis configuration
        self.redis_host = os.getenv("REDIS_HOST")
        self.redis_port = int(os.getenv("REDIS_PORT"))
        self.redis_password = os.getenv("REDIS_PASSWORD")
        self.redis_client = redis.StrictRedis(
            host=self.redis_host,
            port=self.redis_port,
            password=self.redis_password,
            db=int(os.getenv("REDIS_MYSQL_CACHE_DB"))
        )

    def _cache_query(self, key, result, tables, params, ttl=86400):
        """
        Cache a query result in Redis and associate it with the involved tables.

        Args:
            key (str): Cache key for the query result.
            result (list): Query result to cache.
            tables (list): List of tables involved in the query.
            params (dict): Query parameters.
            ttl (int): Time-to-live for the cache entry in seconds.
        """
        try:
            module_logger.debug(f"Caching query into redis")

            serialized_result = json.dumps(result, default=self._convert_value)
            self.redis_client.setex(key, ttl, serialized_result)

            param_hash = self._generate_param_hash(params)
            for table in tables:
                table_key = f"table_cache:{table}:{param_hash}"
                self.redis_client.sadd(table_key, key)
        except redis.RedisError as e:
            module_logger.error(f"Failed to cache query result: {e}")

    def _generate_param_hash(self, params):
        """
        Generate a unique hash for query parameters.

        Args:
            params (dict): Query parameters.

        Returns:
            str: MD5 hash of the serialized parameters.
        """
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(param_str.encode()).hexdigest()

    def _get_cached_query(self, key):
        """
        Retrieve a cached query result from Redis.

        Args:
            key (str): Cache key for the query result.

        Returns:
            list or None: Cached query result or None if not found.
        """

        try:
            cached_result = self.redis_client.get(key)
            if cached_result:
                module_logger.debug(f"Got Cached Query Result: {cached_result}")
                return json.loads(cached_result)
            return None
        except redis.RedisError as e:
            module_logger.error(f"Failed to retrieve cached query result: {e}")
            return None

    def _generate_cache_key(self, query, params):
        """
        Generate a unique cache key for a query and its parameters.

        Args:
            query (str): SQL query string.
            params (dict): Query parameters.

        Returns:
            str: MD5 hash representing the cache key.
        """
        hash_input = f"{query}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(hash_input.encode()).hexdigest()

    def _invalidate_cache_for_table(self, table_name, params=None):
        """
        Invalidate cache entries associated with a table.

        Args:
            table_name (str): Name of the table to invalidate.
            params (dict, optional): Query parameters to limit cache invalidation.
        """

        try:
            if params:
                param_hash = self._generate_param_hash(params)
                table_key = f"table_cache:{table_name}:{param_hash}"
            else:
                # Invalidate all keys related to the table
                table_key = f"table_cache:{table_name}:*"

            cache_keys = self.redis_client.smembers(table_key)
            if cache_keys:
                self.redis_client.delete(*cache_keys)
                self.redis_client.delete(table_key)
                module_logger.info(f"Invalidated cache for table: {table_name} with params: {params}")

        except redis.RedisError as e:
            module_logger.error(f"Failed to invalidate cache for table {table_name}: {e}")

    def _extract_tables_from_query(self, query):
        """
        Extract table names from a SQL query.

        Args:
            query (str): SQL query string.

        Returns:
            list: Unique list of table names found in the query.
        """
        tables = []

        # Regex patterns for different SQL statements
        patterns = {
            'FROM': r'FROM\s+`?(\w+)`?',
            'UPDATE': r'UPDATE\s+`?(\w+)`?',
            'INTO': r'INSERT\s+INTO\s+`?(\w+)`?',
            'DELETE': r'DELETE\s+FROM\s+`?(\w+)`?'
        }

        # Check for each pattern in the query
        for clause, pattern in patterns.items():
            matches = re.findall(pattern, query, re.IGNORECASE)
            if matches:
                tables.extend(matches)

        # Return unique table names
        return list(set(tables))

    def _acquire_connection(self):
        """
        Acquire a new MySQL connection.

        Returns:
            mysql.connector.connection.MySQLConnection: MySQL connection object.

        Raises:
            mysql.connector.Error: If the connection cannot be established.
        """
        try:
            return mysql.connector.connect(**self.dbconfig)
        except mysql.connector.Error as err:
            module_logger.error(f"Error acquiring MySQL connection: {err}")
            raise

    def _release_connection(self, conn):
        """
        Release a MySQL connection.

        Args:
            conn (mysql.connector.connection.MySQLConnection): MySQL connection to release.
        """
        try:
            if conn.is_connected():
                conn.close()
        except mysql.connector.Error as err:
            module_logger.error(f"Error closing connection: {err}")

    def _convert_value(self, val):
        """
            Convert a value for JSON serialization.

            Args:
                val: Value to convert.

            Returns:
                JSON-serializable value.
        """

        if val is None:
            return None
        if isinstance(val, (str, bool, int, float)):
            return val
        if isinstance(val, Decimal):
            return float(val)
        if isinstance(val, datetime.datetime):
            return val.timestamp()
        if isinstance(val, datetime.date):
            return val.isoformat()
        if isinstance(val, (list, tuple, set)):
            return [self._convert_value(v) for v in val]
        if isinstance(val, dict):
            return {k: self._convert_value(v) for k, v in val.items()}
        try:
            return json.loads(val)
        except (ValueError, TypeError):
            pass
        try:
            if 'T' in val:
                return datetime.datetime.fromisoformat(val)
            else:
                return datetime.date.fromisoformat(val)
        except (ValueError, TypeError):
            return val

    def get_version(self) -> str:
        """
        Get the version of the MySQL server.

        Returns:
            str: Version string of the MySQL server.
        """
        result = self.execute_query("SELECT VERSION()", fetch_mode="one")
        return result['message']['VERSION()'] if result['success'] else ""

    def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.

        Args:
            table_name (str): Name of the table to check.

        Returns:
            bool: True if the table exists, False otherwise.
        """
        query = "SHOW TABLES LIKE %s"
        result = self.execute_query(query, params=(table_name,), fetch_mode="one")
        return bool(result['success'])

    def is_connected(self) -> bool:
        """
        Check if the MySQL database is reachable.

        Returns:
            bool: True if the database is reachable, False otherwise.
        """
        try:
            conn = self._acquire_connection()
            connected = conn.is_connected()
            self._release_connection(conn)
            return connected
        except mysql.connector.Error as error:
            module_logger.error(f"<<MySQL>> Connection Check Failed: {error}")
            return False

    def execute_query(self, query: str, params=None, fetch_mode="all", fetch_count=None, multi=False, use_cache=True, cache_ttl=86400):
        """
        Execute a SQL query and fetch results.
        Args:
            query (str): SQL query string.
            params (tuple or dict, optional): Query parameters.
            fetch_mode (str): Mode for fetching results ('all', 'many', 'one').
            fetch_count (int, optional): Number of rows to fetch for 'many' mode.
            multi (bool): Whether to execute multiple statements.
            use_cache (bool): Whether to use cached results.
            cache_ttl (int): Time-to-live for the cache entry in seconds.
        Returns:
            dict: Query execution result with 'success', 'message', and 'result' keys.
        """
        conn = self._acquire_connection()
        cursor = conn.cursor(dictionary=True)
        cached_result = None

        # Generate cache key
        cache_key = self._generate_cache_key(query, params)

        if use_cache and not multi:
            cached_result = self._get_cached_query(cache_key)
            if cached_result is not None:
                module_logger.debug(f"Retrieved cached result for query: {query} | Params: {params}")
                self._release_connection(conn)
                return {'success': True, 'message': 'MySQL Query Executed Successfully', 'result': cached_result}

        try:
            cursor.execute(query, params)

            if fetch_mode == "all":
                result = cursor.fetchall()
            elif fetch_mode == "many":
                result = cursor.fetchmany(fetch_count) if fetch_count else []
            elif fetch_mode == "one":
                result = cursor.fetchone()
            else:
                raise ValueError(f"Invalid fetch_mode: {fetch_mode}")

            if use_cache and not cached_result:
                tables = self._extract_tables_from_query(query)
                self._cache_query(cache_key, result, tables, params, cache_ttl)

            return {'success': True, 'message': 'MySQL Query Executed Successfully', 'result': result}

        except (mysql.connector.Error, ValueError) as error:
            module_logger.error(f"<<MySQL>> <<Query>> Execution Error: {error}")
            module_logger.error(query)
            module_logger.error(params)
            return {'success': False, 'message': str(error), 'result': []}
        finally:
            self._release_connection(conn)

    def execute_commit(self, query: str, params=None, return_row=False, return_count=False, invalidate_tables=True):
        """
            Execute a write query (INSERT, UPDATE, DELETE) and commit the transaction.
            Args:
                query (str): SQL query string.
                params (tuple or dict, optional): Query parameters.
                return_row (bool): Whether to return the last inserted row ID.
                return_count (bool): Whether to return the number of affected rows.
                invalidate_tables (bool): Whether to invalidate cache for affected tables.
            Returns:
                dict: Query execution result with 'success', 'message', and 'result' keys.
        """

        conn = self._acquire_connection()
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            conn.commit()

            module_logger.debug(f"<<MySQL>> <<Commit>> Executed Query: {query} | Params: {params}")

            if invalidate_tables:
                tables = self._extract_tables_from_query(query)
                for table in tables:
                    self._invalidate_cache_for_table(table)

            if return_row:
                result = cursor.lastrowid
            elif return_count:
                result = cursor.rowcount
            else:
                result = []

            return {'success': True, 'message': 'MySQL Commit Query Executed Successfully', 'result': result}
        except mysql.connector.Error as error:
            module_logger.error(f"<<MySQL>> <<Commit>> Execution Error: {error}")
            module_logger.error(query)
            module_logger.error(params)
            conn.rollback()
            return {'success': False, 'message': f'MySQL Commit Query Execution Error: {error}', 'result': []}
        finally:
            self._release_connection(conn)

    def execute_many_commit(self, query: str, data: list, batch_size: int = 1000):
        """
        Execute a batch of write queries in chunks.

        Args:
            query (str): SQL query string.
            data (list): List of parameter tuples for the query.
            batch_size (int): Number of rows to process in each batch.

        Returns:
            dict: Batch execution result with 'success', 'message', and 'result' keys.
        """
        if not data:
            module_logger.warning(f"<<MySQL>> No data provided for batch execution.")
            return {'success': False, 'message': 'No data provided for batch execution.', 'result': []}

        conn = self._acquire_connection()
        try:
            total_batches = math.ceil(len(data) / batch_size)
            cursor = conn.cursor(dictionary=True)

            for batch_num, i in enumerate(range(0, len(data), batch_size), start=1):
                batch_data = data[i:i + batch_size]
                cursor.executemany(query, batch_data)
                conn.commit()
                module_logger.info(f"<<MySQL>> Batch {batch_num} of {total_batches} Committed Successfully")

            return {'success': True, 'message': 'MySQL Multi-Commit Executed Successfully', 'result': []}
        except mysql.connector.Error as error:
            module_logger.error(f"<<MySQL>> <<Multi-Commit>> Error: {error} {query} {batch_data}")
            return {'success': False, 'message': f'MySQL Multi-Commit Error: {error}', 'result': []}
        finally:
            self._release_connection(conn)


