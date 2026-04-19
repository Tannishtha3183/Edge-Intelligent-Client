from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "system.log")


def configure_logging() -> None:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return

    handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        "%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
