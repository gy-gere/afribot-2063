"""
utils/logger.py — Centralised logging for AfriBot-2063.
"""

import logging
import sys
from colorama import Fore, Style, init

init(autoreset=True)

_COLORS = {
    "DEBUG":    Fore.CYAN,
    "INFO":     Fore.GREEN,
    "WARNING":  Fore.YELLOW,
    "ERROR":    Fore.RED,
    "CRITICAL": Fore.MAGENTA,
}


class ColorFormatter(logging.Formatter):
    def format(self, record):
        color = _COLORS.get(record.levelname, "")
        prefix = f"{color}[{record.levelname}]{Style.RESET_ALL}"
        record.msg = f"{prefix} {record.msg}"
        return super().format(record)


def get_logger(name: str = "afribot") -> logging.Logger:
    from config import LOG_LEVEL, LOG_FILE

    logger = logging.getLogger(name)
    if logger.handlers:          # avoid duplicate handlers
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(ColorFormatter("%(asctime)s %(message)s", datefmt="%H:%M:%S"))
    logger.addHandler(ch)

    # File handler
    try:
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s — %(message)s"
        ))
        logger.addHandler(fh)
    except Exception:
        pass   # file logging is optional

    return logger
