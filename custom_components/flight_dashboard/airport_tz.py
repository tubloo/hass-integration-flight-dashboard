"""Airport timezone helpers.

MVP approach:
- Built-in mapping for common airports
- User overrides via config entry options (airport_timezone_overrides)
- Fallback to Home Assistant local timezone (viewer tz)
"""
from __future__ import annotations

from typing import Any

# Extend this over time. Keep it small + useful.
DEFAULT_AIRPORT_TZ: dict[str, str] = {
    # India
    "DEL": "Asia/Kolkata",
    "BOM": "Asia/Kolkata",
    "BLR": "Asia/Kolkata",
    "MAA": "Asia/Kolkata",
    "HYD": "Asia/Kolkata",
    "CCU": "Asia/Kolkata",
    "AMD": "Asia/Kolkata",
    # Nordics / Europe common
    "CPH": "Europe/Copenhagen",
    "ARN": "Europe/Stockholm",
    "GOT": "Europe/Stockholm",
    "OSL": "Europe/Oslo",
    "HEL": "Europe/Helsinki",
    "FRA": "Europe/Berlin",
    "MUC": "Europe/Berlin",
    "LHR": "Europe/London",
    "LGW": "Europe/London",
    "MAD": "Europe/Madrid",
    "BCN": "Europe/Madrid",
    "CDG": "Europe/Paris",
    "AMS": "Europe/Amsterdam",
    "ZRH": "Europe/Zurich",
    # US
    "LAX": "America/Los_Angeles",
    "ATL": "America/New_York",
    "ORD": "America/Chicago",
    "BOS": "America/New_York",
    # China
    "CAN": "Asia/Shanghai",
    # Spain
    "AGP": "Europe/Madrid",
    # UAE
    "DXB": "Asia/Dubai",
}

DEFAULT_AIRPORT_INFO: dict[str, dict[str, str]] = {
    # Europe
    "CDG": {"name": "Paris Charles de Gaulle Airport", "city": "Paris", "tz": "Europe/Paris"},
    "CPH": {"name": "Copenhagen Airport", "city": "Copenhagen", "tz": "Europe/Copenhagen"},
    "AGP": {"name": "Malaga Airport", "city": "Malaga", "tz": "Europe/Madrid"},
    # US
    "ATL": {"name": "Hartsfield-Jackson Atlanta International Airport", "city": "Atlanta", "tz": "America/New_York"},
    "ORD": {"name": "Chicago O'Hare International Airport", "city": "Chicago", "tz": "America/Chicago"},
    "BOS": {"name": "Logan International Airport", "city": "Boston", "tz": "America/New_York"},
    # China
    "CAN": {"name": "Guangzhou Baiyun International Airport", "city": "Guangzhou", "tz": "Asia/Shanghai"},
    # UAE
    "DXB": {"name": "Dubai International Airport", "city": "Dubai", "tz": "Asia/Dubai"},
}


def get_airport_tz(iata: str | None, options: dict[str, Any] | None) -> str | None:
    """Return IANA tz string for airport IATA code, if known."""
    if not iata:
        return None
    code = str(iata).strip().upper()
    if not code:
        return None

    opts = options or {}
    overrides = opts.get("airport_timezone_overrides") or {}
    if isinstance(overrides, dict):
        tz = overrides.get(code)
        if isinstance(tz, str) and tz.strip():
            return tz.strip()

    return DEFAULT_AIRPORT_TZ.get(code)


def get_airport_info(iata: str | None, options: dict[str, Any] | None) -> dict[str, str] | None:
    """Return static airport info (name/city/tz) if known."""
    if not iata:
        return None
    code = str(iata).strip().upper()
    if not code:
        return None
    return DEFAULT_AIRPORT_INFO.get(code)
