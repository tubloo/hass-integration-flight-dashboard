"""Airport/airline directory lookup with optional caching."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant

from .providers.directory.aviationstack import AviationstackDirectoryProvider
from .providers.directory.airlabs import AirLabsDirectoryProvider
from .providers.directory.fr24 import FR24DirectoryProvider
from .directory_store import (
    async_get_airport,
    async_get_airline,
    async_set_airport,
    async_set_airline,
    is_fresh,
)
from .airport_tz import get_airport_info
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


async def get_airport(hass: HomeAssistant, options: dict[str, Any], iata: str) -> dict[str, Any] | None:
    iata = (iata or "").strip().upper()
    if not iata:
        return None

    cache_enabled = bool(_get_option(options, "cache_directory", True))
    ttl_days = int(_get_option(options, "cache_ttl_days", 180))

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
    if av_key and not is_blocked(hass, "aviationstack"):
        providers.append(AviationstackDirectoryProvider(hass, av_key))
    if al_key and not is_blocked(hass, "airlabs"):
        providers.append(AirLabsDirectoryProvider(hass, al_key))
    if fr24_active_key and not is_blocked(hass, "fr24"):
        providers.append(FR24DirectoryProvider(hass, fr24_active_key, use_sandbox=fr24_use_sandbox, api_version=fr24_version))

    for p in providers:
        try:
            data = await p.async_get_airport(iata)
        except Exception as e:
            _LOGGER.debug("Directory provider failed for airport %s: %s", iata, e)
            data = None
        if data:
            # Merge with static fallback to fill missing fields (do not overwrite with nulls)
            fallback = get_airport_info(iata, options) or {}
            merged = dict(fallback)
            for k, v in data.items():
                if v is not None and v != "":
                    merged[k] = v
            if cache_enabled:
                await async_set_airport(hass, iata, merged)
            return merged

    # Static fallback map (name/city/tz) if providers miss
    fallback = get_airport_info(iata, options)
    if fallback:
        if cache_enabled:
            await async_set_airport(hass, iata, fallback)
        return fallback

    return None


async def get_airline(hass: HomeAssistant, options: dict[str, Any], iata: str) -> dict[str, Any] | None:
    iata = (iata or "").strip().upper()
    if not iata:
        return None

    cache_enabled = bool(_get_option(options, "cache_directory", True))
    ttl_days = int(_get_option(options, "cache_ttl_days", 180))

    if cache_enabled:
        cached = await async_get_airline(hass, iata)
        if is_fresh(cached, ttl_days):
            return cached

    av_key = (options.get("aviationstack_access_key") or "").strip()
    al_key = (options.get("airlabs_api_key") or "").strip()

    providers = []
    if av_key:
        providers.append(AviationstackDirectoryProvider(hass, av_key))
    if al_key:
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

    return None
