import os
from typing import List
from dotenv import load_dotenv

ENVS = ["dev", "test", "prod"]


def setup_env(argv: List[str]) -> None:
    """
    Set up the environment for the ETL process.
    This function loads the appropriate environment
    variables based on the provided environment.
    It expects the first argument to be the environment
    name (e.g., 'dev', 'test', 'prod').
    It clears any previous environment variables
    related to database configurations to avoid
    conflicts when switching environments.
    This function should be called before loading
    new environment variables.
    It is particularly useful in a development
    or testing environment where the same script
    might be run multiple times with different
    configurations.
    In a production environment, this function
    is not necessary as the script is run once
    with a specific configuration.
    :param argv: List of command line arguments
    :raises ValueError: If the environment is not provided
    or is not one of the expected values.
    :raises KeyError: If the ENV variable is not set
    """
    if len(argv) != 2 or argv[1] not in ENVS:
        raise ValueError(
            "Please provide an environment: " f"{ENVS}. E.g. run_etl dev"
        )

    env = argv[1]

    cleanup_previous_env()
    os.environ["ENV"] = env

    env_file = ".env" if env == "prod" else f".env.{env}"

    if not os.path.exists(env_file):
        raise FileNotFoundError(f"Environment file '{env_file}' not found")

    print(f"Loading environment variables from: {env_file}")
    load_dotenv(env_file, override=True)


def cleanup_previous_env() -> None:
    """
    Clear relevant environment variables to avoid
    conflicts when switching environments.
    This is useful when running the ETL process
    multiple times with different configurations.
    This function should be called before loading
    new environment variables.
    It clears the environment variables related to
    database configurations to ensure that the
    new environment variables are loaded correctly.
    This is particularly important in a development
    or testing environment where the same script
    might be run multiple times with different
    configurations.
    This function is not necessary in a production
    environment where the script is run once
    with a specific configuration.
    It is a good practice to clear the environment
    variables to avoid any potential conflicts
    or confusion when switching between different
    environments.
    """
    keys_to_clear = [
        "SOURCE_DB_NAME",
        "SOURCE_DB_USER",
        "SOURCE_DB_PASSWORD",
        "SOURCE_DB_HOST",
        "SOURCE_DB_PORT",
        "TARGET_DB_NAME",
        "TARGET_DB_USER",
        "TARGET_DB_PASSWORD",
        "TARGET_DB_HOST",
        "TARGET_DB_PORT",
    ]
    for key in keys_to_clear:
        if key in os.environ:
            del os.environ[key]
