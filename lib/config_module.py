#!/usr/bin/env python3
# Configuration

"""
Author: Ian Carey
Date: 2025-1-17
Description: This script loads configuration data from MySQL Database
"""

import logging

module_logger = logging.getLogger('icad_dispatch.config')

def init_config(db):
    default_config = [
    ]

def get_config(db, config_key=None):
    """
    Fetch configuration settings from the database and return as a dictionary.

    Args:
        db: Database connection object.
        config_key (str, optional): Specific config key to fetch. Fetches all if None.

    Returns:
        dict: Configuration settings as a dictionary where keys are `config_key` and values are `config_value`.
    """
    base_query = """
    SELECT 
      ac.config_key,
      ac.config_value,
      ac.description
    FROM
      app_config ac
    """

    params = None
    if config_key:
        base_query += " WHERE ac.config_key = %s"
        params = (config_key,)

    config_result = db.execute_query(base_query, params)

    if not config_result.get('success'):
        return {}

    # Convert result to a dictionary
    result = config_result.get('result', [])
    config_dict = {row['config_key']: row['config_value'] for row in result}

    return config_dict

def set_config(db, config_key, config_value, description=None):
    """
    Add or update a configuration setting in the database.

    Args:
        db: Database connection object.
        config_key (str): The configuration key.
        config_value (str): The configuration value.
        description (str, optional): Description of the configuration.

    Returns:
        dict: Operation result with success status and message.
    """
    # Check if the config key exists
    check_query = "SELECT 1 FROM app_config WHERE config_key = %s"
    result = db.execute_query(check_query, (config_key,), fetch_mode="one")

    if result.get('success') and result.get('result'):
        # Key exists, update it
        update_query = """
        UPDATE app_config 
        SET config_value = %s, description = %s
        WHERE config_key = %s
        """
        params = (config_value, description, config_key)
        return db.execute_query(update_query, params)
    else:
        # Key doesn't exist, insert it
        insert_query = """
        INSERT INTO app_config (config_key, config_value, description)
        VALUES (%s, %s, %s)
        """
        params = (config_key, config_value, description)
        return db.execute_query(insert_query, params)