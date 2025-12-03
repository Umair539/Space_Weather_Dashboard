from pathlib import Path
import logging


def _ensure_log_directory(base_path=None):
    """Ensure the logs directory exists."""
    project_root = Path(base_path or __file__).resolve().parent.parent
    log_directory = project_root / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    return log_directory


def _create_formatter():
    """Create a standard log formatter."""
    return logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def _create_handlers(log_directory, log_file, level):
    """Create file and console handlers."""
    file_handler = logging.FileHandler(log_directory / log_file)
    file_handler.setLevel(level)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    formatter = _create_formatter()
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    return file_handler, console_handler


def setup_logger(name, log_file, level=logging.DEBUG, base_path=None):
    """Function to setup a logger; can be used in multiple modules."""
    log_directory = _ensure_log_directory(base_path)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        file_handler, console_handler = _create_handlers(
            log_directory,
            log_file,
            level,
        )
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
