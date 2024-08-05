"""
Logger Setup Module

This module provides a utility function to configure and set up logging for an application.
The `setup_logger` function allows for customizable logging levels and output destinations,
either to a file or to the console.

Available log levels:
- DEBUG
- INFO
- WARNING
- ERROR
- CRITICAL

Example usage:
    from setup_logger import setup_logger
    import logging

    # Set up the logger to log to a file with INFO level
    logger = setup_logger(log_level="INFO", log_to_file=True)

    # Log some messages
    logger.info("This is an info message")
    logger.error("This is an error message")

Functions:
    setup_logger(log_level="WARNING", log_to_file=False):
        Configures and returns a logger with the specified log level and output destination.

Attributes:
    LOG_LEVELS (dict): A dictionary mapping log level names to their corresponding logging constants.
"""
import logging

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

def setup_logger(file_name,  log_level="WARNING", log_to_file=False,):
    """
    Set up a logger with the specified log level and log destination.

    Args:
        log_level (str, optional): The desired log level. Defaults to "WARNING".
        log_to_file (bool, optional): Whether to log to a file. Defaults to False.

    Returns:
        logger: The configured logger object.

    Raises:
        ValueError: If an invalid log level is provided.
    """
    if log_level.upper() not in LOG_LEVELS:
        raise ValueError(f"Invalid log level: {log_level}")
    if log_to_file:
        logging.basicConfig(
            filename=file_name,
            format="%(levelname)s: %(message)s (%(asctime)s)",
            datefmt="%m/%d/%Y %I:%M:%S %p",
            level=LOG_LEVELS[log_level.upper()],
        )
    else:
        logging.basicConfig(
            format="%(levelname)s: %(message)s (%(asctime)s)",
            datefmt="%m/%d/%Y %I:%M:%S %p",
            level=LOG_LEVELS[log_level.upper()],
        )

    logger = logging.getLogger(__name__)
    return logger