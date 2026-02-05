"""Airport/airline directory lookup with optional caching."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .providers.directory.aviationstack import AviationstackDirectoryProvider
from .providers.directory.airlabs import AirLabsDirectoryProvider
from .providers.directory.fr24 import FR24DirectoryProvider
from .providers.directory.openflights import (
    OPENFLIGHTS_AIRLINES_URL,
    OPENFLIGHTS_AIRPORTS_URL,
    async_get_airport as openflights_get_airport,
    async_get_airline as openflights_get_airline,
)
from .directory_store import (
    async_get_airport,
    async_get_airline,
    async_set_airport,
    async_set_airline,
    is_fresh,
    async_is_initialized,
    async_mark_initialized,
)
from .rate_limit import is_blocked

_LOGGER = logging.getLogger(__name__)

def airline_logo_url(iata: str | None) -> str | None:
    """Return a lightweight logo URL for airline IATA code."""
    if not iata:
        return None
    code = str(iata).strip().upper()
    if not code:
        return None
    return f"https://pics.avs.io/64/64/{code}.png"


def _get_option(options: dict[str, Any], key: str, default: Any) -> Any:
    val = options.get(key, default)
    return val if val is not None else default


def _directory_source(options: dict[str, Any]) -> str:
    src = str(options.get("directory_source", "auto") or "auto").strip().lower()
    return src


async def get_airport(hass: HomeAssistant, options: dict[str, Any], iata: str) -> dict[str, Any] | None:
    iata = (iata or "").strip().upper()
    if not iata:
        return None

    cache_enabled = bool(_get_option(options, "cache_directory", True))
    ttl_days = int(_get_option(options, "cache_ttl_days", 90))
    source = _directory_source(options)
    airports_url = str(_get_option(options, "directory_airports_url", "")).strip() or OPENFLIGHTS_AIRPORTS_URL

    def _is_complete_airport(data: dict[str, Any] | None) -> bool:
        if not isinstance(data, dict):
            return False
        return bool(data.get("name") and data.get("city") and data.get("tz"))

    if cache_enabled:
        cached = await async_get_airport(hass, iata)
        if is_fresh(cached, ttl_days) and _is_complete_airport(cached):
            return cached

    av_key = (options.get("aviationstack_access_key") or "").strip()
    al_key = (options.get("airlabs_api_key") or "").strip()
    fr24_key = (options.get("fr24_api_key") or "").strip()
    fr24_sandbox_key = (options.get("fr24_sandbox_key") or "").strip()
    fr24_use_sandbox = bool(options.get("fr24_use_sandbox", False))
    fr24_version = (options.get("fr24_api_version") or "v1").strip()
    fr24_active_key = fr24_sandbox_key if fr24_use_sandbox and fr24_sandbox_key else fr24_key

    providers = []
    if source in ("auto", "aviationstack") and av_key and not is_blocked(hass, "aviationstack"):
        providers.append(AviationstackDirectoryProvider(hass, av_key))
    if source in ("auto", "airlabs") and al_key and not is_blocked(hass, "airlabs"):
        providers.append(AirLabsDirectoryProvider(hass, al_key))
    if source in ("auto", "fr24") and fr24_active_key and not is_blocked(hass, "fr24"):
        providers.append(FR24DirectoryProvider(hass, fr24_active_key, use_sandbox=fr24_use_sandbox, api_version=fr24_version))

    for p in providers:
        try:
            data = await p.async_get_airport(iata)
        except Exception as e:
            _LOGGER.debug("Directory provider failed for airport %s: %s", iata, e)
            data = None
        if data:
            merged = {}
            for k, v in data.items():
                if v is not None and v != "":
                    merged[k] = v
            if cache_enabled:
                await async_set_airport(hass, iata, merged)
            return merged

    # Fallback: airports.dat (OpenFlights or user-provided URL)
    if source == "custom" and not airports_url:
        airports_url = OPENFLIGHTS_AIRPORTS_URL
    try:
        if source in ("auto", "openflights", "custom", "aviationstack", "airlabs", "fr24"):
            data = await openflights_get_airport(hass, iata, airports_url)
        else:
            data = None
        if data:
            if cache_enabled:
                await async_set_airport(hass, iata, data)
            return data
    except Exception as e:
        _LOGGER.debug("OpenFlights airport fallback failed for %s: %s", iata, e)

    return None


async def get_airline(hass: HomeAssistant, options: dict[str, Any], iata: str) -> dict[str, Any] | None:
    iata = (iata or "").strip().upper()
    if not iata:
        return None

    cache_enabled = bool(_get_option(options, "cache_directory", True))
    ttl_days = int(_get_option(options, "cache_ttl_days", 90))
    source = _directory_source(options)
    airlines_url = str(_get_option(options, "directory_airlines_url", "")).strip() or OPENFLIGHTS_AIRLINES_URL

    if cache_enabled:
        cached = await async_get_airline(hass, iata)
        if is_fresh(cached, ttl_days):
            return cached

    av_key = (options.get("aviationstack_access_key") or "").strip()
    al_key = (options.get("airlabs_api_key") or "").strip()

    providers = []
    if source in ("auto", "aviationstack") and av_key:
        providers.append(AviationstackDirectoryProvider(hass, av_key))
    if source in ("auto", "airlabs") and al_key:
        providers.append(AirLabsDirectoryProvider(hass, al_key))

    for p in providers:
        try:
            data = await p.async_get_airline(iata)
        except Exception as e:
            _LOGGER.debug("Directory provider failed for airline %s: %s", iata, e)
            data = None
        if data:
            if cache_enabled:
                await async_set_airline(hass, iata, data)
            return data

    # Fallback: airlines.dat (OpenFlights or user-provided URL)
    if source == "custom" and not airlines_url:
        airlines_url = OPENFLIGHTS_AIRLINES_URL
    try:
        if source in ("auto", "openflights", "custom", "aviationstack", "airlabs", "fr24"):
            data = await openflights_get_airline(hass, iata, airlines_url)
        else:
            data = None
        if data:
            if cache_enabled:
                await async_set_airline(hass, iata, data)
            return data
    except Exception as e:
        _LOGGER.debug("OpenFlights airline fallback failed for %s: %s", iata, e)

    return None


async def warm_directory_cache(hass: HomeAssistant, options: dict[str, Any], flights: list[dict[str, Any]]) -> None:
    """Populate local directory cache on first run using known flights only."""
    cache_enabled = bool(_get_option(options, "cache_directory", True))
    if not cache_enabled:
        return
    if await async_is_initialized(hass):
        return

    # Collect unique IATA codes from flights
    airport_codes: set[str] = set()
    airline_codes: set[str] = set()
    for f in flights:
        airline = (f.get("airline_code") or "").strip().upper()
        if airline:
            airline_codes.add(airline)
        dep_iata = ((f.get("dep") or {}).get("airport") or {}).get("iata")
        arr_iata = ((f.get("arr") or {}).get("airport") or {}).get("iata")
        if dep_iata:
            airport_codes.add(str(dep_iata).strip().upper())
        if arr_iata:
            airport_codes.add(str(arr_iata).strip().upper())

    # Populate cache (calls provider only if not already cached/stale)
    for code in sorted(airport_codes):
        try:
            await get_airport(hass, options, code)
        except Exception:
            pass
    for code in sorted(airline_codes):
        try:
            await get_airline(hass, options, code)
        except Exception:
            pass

    await async_mark_initialized(hass)
