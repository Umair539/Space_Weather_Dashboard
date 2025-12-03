import os
import logging
from src.utils.logging_utils import setup_logger
from typing import Dict, Literal


# Create a Custom Exception for Database Config errors
class DatabaseConfigError(Exception):
    pass


# Configure the logger
logger = setup_logger(__name__, "database.log", level=logging.DEBUG)


def load_db_config() -> Dict[
    str,
    Dict[
        Literal["dbname", "user", "password", "host", "port", "schema"],
        str,
    ],
]:
    """
    Load database configuration from environment variables
    Set this with the appropriate values in the .env file
    or in the deployment environment.
    Run with the ENV environment variable set to the
    appropriate environment, so for dev environment:
        run_etl dev
    Other environments are test and prod
    :return: Dictionary containing source and target database
    connection parameters.
    """

    config: Dict[
        str,
        Dict[
            Literal["dbname", "user", "password", "host", "port", "schema"],
            str,
        ],
    ] = {
        "source_database": {
            "dbname": os.getenv("SOURCE_DB_NAME", "error"),
            "user": os.getenv("SOURCE_DB_USER", "error"),
            "password": os.getenv("SOURCE_DB_PASSWORD", ""),
            "host": os.getenv("SOURCE_DB_HOST", "error"),
            "port": os.getenv("SOURCE_DB_PORT", "5432"),
            "schema": os.getenv("SOURCE_DB_SCHEMA", "public"),
        },
        # "target_database": {
        #     "dbname": os.getenv("TARGET_DB_NAME", "error"),
        #     "user": os.getenv("TARGET_DB_USER", "error"),
        #     "password": os.getenv("TARGET_DB_PASSWORD", ""),
        #     "host": os.getenv("TARGET_DB_HOST", "error"),
        #     "port": os.getenv("TARGET_DB_PORT", "5432"),
        # },
    }

    validate_db_config(config)

    return config


def validate_db_config(config):
    for db_key, db_config in config.items():
        for key, value in db_config.items():
            if value == "error":
                logger.error(
                    f"Configuration error: {db_key} {key} is set to 'error'"
                )
                raise DatabaseConfigError(
                    f"Configuration error: {db_key} {key} is set to 'error'"
                )
