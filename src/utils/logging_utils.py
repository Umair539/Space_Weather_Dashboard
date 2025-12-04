from pathlib import Path
import logging
from typing import Optional, Tuple


def _ensure_log_directory(base_path: Optional[str] = None) -> Path:
    """Create logs directory if it doesn't exist.

    Args:
        base_path: Base path for log directory. Defaults to project root.

    Returns:
        Path to the logs directory.
    """
    project_root = Path(base_path or __file__).resolve().parent.parent
    log_directory = project_root / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    return log_directory


def _create_formatter() -> logging.Formatter:
    """Create standard log formatter with timestamp and level.

    Returns:
        Configured logging formatter.
    """
    return logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def _create_handlers(
    log_directory: Path, log_file: str, level: int
) -> Tuple[logging.FileHandler, logging.StreamHandler]:
    """Create configured file and console logging handlers.

    Args:
        log_directory: Directory where log files will be stored.
        log_file: Name of the log file.
        level: Logging level for both handlers.

    Returns:
        Tuple of file handler and console handler.
    """
    file_handler = logging.FileHandler(log_directory / log_file)
    file_handler.setLevel(level)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    formatter = _create_formatter()
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    return file_handler, console_handler


def setup_logger(
    name: str,
    log_file: str,
    level: int = logging.DEBUG,
    base_path: Optional[str] = None,
) -> logging.Logger:
    """Configure logger with file and console output.

    Args:
        name: Logger name, typically __name__.
        log_file: Name of the log file.
        level: Logging level. Defaults to DEBUG.
        base_path: Base path for log directory.

    Returns:
        Configured logger instance.
    """
    log_directory = _ensure_log_directory(base_path)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        file_handler, console_handler = _create_handlers(
            log_directory, log_file, level
        )
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


def log_extract_success(
    logger: logging.Logger,
    type: str,
    shape: Tuple[int, int],
    execution_time: float,
    expected_rate: float,
) -> None:
    """Log successful data extraction with performance analysis.

    Args:
        logger: Logger instance to use for output.
        type: Description of the data type extracted.
        shape: Tuple of (rows, columns) extracted.
        execution_time: Time taken for extraction in seconds.
        expected_rate: Expected time per row threshold.
    """
    logger.info(f"Data extraction successful for {type}!")
    logger.info(f"Extracted {shape[0]} rows " f"and {shape[1]} columns")
    logger.info(f"Execution time: {execution_time} seconds")

    if execution_time / shape[0] <= expected_rate:
        logger.info(
            "Execution time per row: " f"{execution_time / shape[0]} seconds"
        )
    else:
        logger.warning(
            f"Execution time per row exceeds {expected_rate}: "
            f"{execution_time / shape[0]} seconds"
        )
