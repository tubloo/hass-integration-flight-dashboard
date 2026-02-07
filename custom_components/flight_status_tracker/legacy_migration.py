"""Legacy data migration helpers.

Supports importing manual flights from the old integration domain:
- legacy store key: flight_dashboard.manual_flights
- new store key:    flight_status_tracker.manual_flights

This is intentionally non-destructive: it copies/merges flights into the new
store and leaves the legacy store intact.
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import DOMAIN, SIGNAL_MANUAL_FLIGHTS_UPDATED
from .manual_store import async_list_manual_flights, async_save_manual_flights

_LOGGER = logging.getLogger(__name__)

_LEGACY_STORE_VERSION = 1
_LEGACY_STORE_KEY = "flight_dashboard.manual_flights"


def _ensure_flight_key(f: dict[str, Any]) -> str | None:
    fk = (f.get("flight_key") or "").strip()
    if fk:
        return fk

    airline = (f.get("airline_code") or f.get("airline") or "").strip().upper()
    fnum = (f.get("flight_number") or "").strip()
    dep = (f.get("dep_airport") or "").strip().upper()

    dep_iso = (f.get("scheduled_departure") or "").strip()
    if not dep_iso and isinstance(f.get("dep"), dict):
        dep_iso = str((f.get("dep") or {}).get("scheduled") or "").strip()

    if not (airline and fnum and dep and dep_iso and len(dep_iso) >= 10):
        return None

    dep_date = dep_iso[:10]
    return f"{airline}-{fnum}-{dep}-{dep_date}"


async def _load_legacy_manual_flights(hass: HomeAssistant) -> list[dict[str, Any]]:
    data = await Store(hass, _LEGACY_STORE_VERSION, _LEGACY_STORE_KEY).async_load() or {}
    if not isinstance(data, dict):
        return []
    flights = data.get("flights") or []
    if not isinstance(flights, list):
        return []
    out: list[dict[str, Any]] = []
    for f in flights:
        if isinstance(f, dict):
            out.append(f)
    return out


async def async_import_legacy_manual_flights(hass: HomeAssistant) -> dict[str, int]:
    """Import legacy manual flights. Returns counts."""
    legacy = await _load_legacy_manual_flights(hass)
    if not legacy:
        return {"imported": 0, "skipped": 0}

    current = await async_list_manual_flights(hass)
    existing = {str(f.get("flight_key") or "").strip() for f in current if isinstance(f, dict)}

    imported = 0
    skipped = 0
    merged = list(current)

    for raw in legacy:
        if not isinstance(raw, dict):
            skipped += 1
            continue
        fk = _ensure_flight_key(raw)
        if not fk:
            skipped += 1
            continue
        if fk in existing:
            skipped += 1
            continue
        rec = dict(raw)
        rec["flight_key"] = fk
        # normalize source label (harmless if unused)
        rec.setdefault("source", "manual")
        merged.append(rec)
        existing.add(fk)
        imported += 1

    if imported:
        await async_save_manual_flights(hass, merged)
        async_dispatcher_send(hass, SIGNAL_MANUAL_FLIGHTS_UPDATED)
        _LOGGER.info("Imported %s legacy flights into %s", imported, f"{DOMAIN}.manual_flights")

    return {"imported": imported, "skipped": skipped}

