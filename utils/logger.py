"""
utils/logger.py
Logger estruturado com rotação de arquivo e saída em console.
"""

import logging
import logging.handlers
import os
from pathlib import Path

LOG_DIR   = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
FMT       = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:          # evita handlers duplicados em hot-reload
        return logger

    logger.setLevel(LOG_LEVEL)
    fmt = logging.Formatter(FMT, datefmt="%Y-%m-%d %H:%M:%S")

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    fh = logging.handlers.RotatingFileHandler(
        LOG_DIR / "pdm.log", maxBytes=5_242_880, backupCount=3, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger
