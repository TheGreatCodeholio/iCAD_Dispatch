#!/usr/bin/env python3
# Configuration

"""
Author: Ian Carey
Date: 2019-21-05
Description: This script loads configuration data from .env
Usage: In main script use load_dotenv() from python-dotenv

Requirements:
- Python 3.12+
- dotenv~=1.0.1
"""

import logging
import os

module_logger = logging.getLogger('icad_dispatch.config')

config_data_template = {
    "log_level": 1,
    "mysql": {
        "host": None,
        "port": 3306,
        "user": None,
        "password": None,
        "database": None
    },
    "redis": {
        "host": None,
        "port": 6379,
        "password": None,
        "db": 0,
        "mysql_cache_db": 4
    }
}


def load_config_data():
    """
    Loads the configuration data from a .env file and returns a populated config_data dict.

    Returns:
        dict: Configuration data populated with values from the .env file.

    Raises:
        ValueError: If required environment variables are missing.
    """

    # Populate config_data with environment variables
    config_data = config_data_template.copy()

    try:
        config_data["log_level"] = int(os.getenv("LOG_LEVEL", config_data["log_level"]))

        # MySQL Configuration
        config_data["mysql"]["host"] = os.getenv("MYSQL_HOST")
        config_data["mysql"]["port"] = int(os.getenv("MYSQL_PORT", config_data["mysql"]["port"]))
        config_data["mysql"]["user"] = os.getenv("MYSQL_USER")
        config_data["mysql"]["password"] = os.getenv("MYSQL_PASSWORD")
        config_data["mysql"]["database"] = os.getenv("MYSQL_DATABASE")

        # Redis Configuration
        config_data["redis"]["host"] = os.getenv("REDIS_HOST")
        config_data["redis"]["port"] = int(os.getenv("REDIS_PORT", config_data["redis"]["port"]))
        config_data["redis"]["password"] = os.getenv("REDIS_PASSWORD")
        config_data["redis"]["db"] = int(os.getenv("REDIS_DB", config_data["redis"]["db"]))
        config_data["redis"]["mysql_cache_db"] = int(
            os.getenv("REDIS_MYSQL_CACHE_DB", config_data["redis"]["mysql_cache_db"]))

        # Validate required fields
        required_fields = [
            ("MYSQL_HOST", config_data["mysql"]["host"]),
            ("MYSQL_USER", config_data["mysql"]["user"]),
            ("MYSQL_PASSWORD", config_data["mysql"]["password"]),
            ("MYSQL_DATABASE", config_data["mysql"]["database"]),
            ("REDIS_HOST", config_data["redis"]["host"]),
            ("REDIS_PASSWORD", config_data["redis"]["password"])
        ]

        for field_name, value in required_fields:
            if not value:
                raise ValueError(f"Missing required environment variable: {field_name}")

    except ValueError as e:
        module_logger.error(f"Error loading configuration: {e}")
        raise

    return config_data