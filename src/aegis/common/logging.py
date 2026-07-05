import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    """
    Central logging configuration for Aegis.

    Designed to be:
    - deterministic
    - dependency-free
    - reusable across CLI, jobs, and future LangGraph runtime
    """

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )


def get_logger(name: str) -> logging.Logger:
    """
    Returns a namespaced logger.

    Usage:
        logger = get_logger(__name__)
    """

    return logging.getLogger(name)
