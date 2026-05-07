"""
utils/internet.py — Check internet connectivity.
"""

import requests
from utils.logger import get_logger

log = get_logger("internet")


def is_online(url: str = None, timeout: int = None) -> bool:
    """Return True if an outbound HTTP connection succeeds."""
    from config import INTERNET_CHECK_URL, INTERNET_CHECK_TIMEOUT
    url     = url     or INTERNET_CHECK_URL
    timeout = timeout or INTERNET_CHECK_TIMEOUT
    try:
        resp = requests.get(url, timeout=timeout)
        online = resp.status_code < 500
        log.debug(f"Internet check → {'ONLINE' if online else 'OFFLINE'}")
        return online
    except Exception:
        log.debug("Internet check → OFFLINE (connection error)")
        return False
