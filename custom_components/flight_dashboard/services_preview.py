"""Preview/confirm services for Flight Dashboard.

This module is intentionally self-contained and does not rely on a specific
resolver function name from status_resolver.py (which may change over time).

Preview flow:
1) User calls flight_dashboard.preview_flight with airline + flight_number + date
2) We store a preview object in storage immediately (so UI updates)
3) If a status/schedule provider is available, we attempt to enrich the preview
4) User calls flight_dashboard.confirm_add to persist as a manual flight
5) User calls flight_dashboard.clear_preview to clear preview
"""
from __future__ import annotations

import logging
from datetime import datetime
import re
from typing import Any, Callable

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.components import persistent_notification

from .const import (
    DOMAIN,
    SERVICE_PREVIEW_FLIGHT,
    SERVICE_CONFIRM_ADD,
    SERVICE_CLEAR_PREVIEW,
    SERVICE_ADD_FLIGHT,
    SIGNAL_PREVIEW_UPDATED,
)
from .manual_store import async_add_manual_flight_record
from .schedule_lookup import lookup_schedule
from .directory import airline_logo_url, get_airport, get_airline
from .tz_short import tz_short_name
from .airport_tz import get_airport_info
from .storage import async_load_preview, async_save_preview, async_clear_preview

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMA_PREVIEW = vol.Schema(
    {
        vol.Optional("query"): cv.string,            # legacy: "AI 157"
        vol.Optional("airline"): cv.string,          # IATA like "AI"
        vol.Optional("flight_number"): cv.string,    # "157"
        vol.Optional("date"): cv.string,             # "YYYY-MM-DD"
        vol.Optional("travellers", default=[]): vol.Any([cv.string], cv.string),
        vol.Optional("notes", default=""): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)


def _parse_query(query: str | None) -> tuple[str | None, str | None]:
    """Parse an airline+flight query like 'AI 157' or 'AI157'."""
    q = (query or "").strip().upper()
    if not q:
        return None, None
    q = q.replace("-", " ").replace("/", " ")
    # Prefer explicit space-separated input to avoid 2/3-char ambiguity
    m = re.match(r"^([A-Z0-9]{2,3})\s+([0-9]{1,4}[A-Z]?)$", q)
    if m:
        return m.group(1), m.group(2)
    m = re.match(r"^([A-Z0-9]{2,3})\s*([0-9]{1,4}[A-Z]?)$", q.replace(" ", ""))
    if m:
        return m.group(1), m.group(2)
    return None, None


def _norm_travellers(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x).strip() for x in val if str(x).strip()]
    s = str(val).strip()
    if not s:
        return []
    return [p.strip() for p in s.split(",") if p.strip()]


def _build_flight_key(airline: str, flight_number: str, dep_iata: str | None, date: str) -> str:
    # dep_iata may be unknown at preview-time. Use XXX so it's still stable.
    dep = (dep_iata or "XXX").upper()
    return f"{airline.upper()}-{flight_number}-{dep}-{date}"


def _preview_complete(flight: dict[str, Any] | None) -> tuple[bool, str | None]:
    """Return whether preview has minimum required fields to add."""
    if not isinstance(flight, dict):
        return False, "No preview flight data."
    dep_airport = ((flight.get("dep") or {}).get("airport") or {}).get("iata")
    arr_airport = ((flight.get("arr") or {}).get("airport") or {}).get("iata")
    dep = (flight.get("dep") or {})
    arr = (flight.get("arr") or {})
    dep_air = (dep.get("airport") or {})
    arr_air = (arr.get("airport") or {})
    dep_sched = dep.get("scheduled")
    arr_sched = arr.get("scheduled")
    if not dep_airport or not arr_airport:
        return False, "Missing departure/arrival airport. Try another provider or verify the date."
    if not dep_sched or not arr_sched:
        return False, "Missing scheduled departure/arrival time. Try another provider or verify the date."
    # Require name (or city) + tz, but allow missing city with warning
    if not (dep_air.get("name") or dep_air.get("city")) or not dep_air.get("tz"):
        return False, f"Missing departure airport details for {dep_airport}. Check directory provider keys."
    if not (arr_air.get("name") or arr_air.get("city")) or not arr_air.get("tz"):
        return False, f"Missing arrival airport details for {arr_airport}. Check directory provider keys."
    return True, None


async def _try_enrich_preview(
    hass: HomeAssistant,
    options: dict[str, Any],
    airline: str,
    flight_number: str,
    date_str: str,
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """Try to enrich preview using schedule lookup providers."""
    result = await lookup_schedule(hass, options, f"{airline} {flight_number}", date_str)
    if result.get("flight"):
        return result, None, None
    return None, result.get("error") or "no_match_or_no_provider", result.get("hint")


async def async_register_preview_services(
    hass: HomeAssistant,
    options_provider: Callable[[], dict[str, Any]],
) -> None:
    """Register preview/confirm/clear services."""
    async def _svc_preview(call: ServiceCall) -> None:
        """Build a preview record from minimal inputs and store it server-side."""
        airline = str(call.data.get("airline", "")).strip().upper()
        flight_number = str(call.data.get("flight_number", "")).strip()
        if not airline or not flight_number:
            q_airline, q_fnum = _parse_query(call.data.get("query"))
            airline = airline or (q_airline or "")
            flight_number = flight_number or (q_fnum or "")
        date_str = str(call.data.get("date", "")).strip()
        travellers = _norm_travellers(call.data.get("travellers"))
        notes = str(call.data.get("notes", "")).strip() or None

        if not date_str:
            preview = {
                "ready": False,
                "error": "bad_date",
                "hint": "Provide a date in YYYY-MM-DD.",
                "input": {
                    "airline": airline,
                    "flight_number": flight_number,
                    "date": date_str,
                    "travellers": travellers,
                    "notes": notes or "",
                },
                "flight": None,
                "status_raw": None,
            }
            await async_save_preview(hass, preview)
            async_dispatcher_send(hass, SIGNAL_PREVIEW_UPDATED)
            return

        if not airline or not flight_number:
            preview = {
                "ready": False,
                "error": "bad_query",
                "hint": "Provide airline + flight_number or a query like 'AI 157'.",
                "input": {
                    "airline": airline,
                    "flight_number": flight_number,
                    "date": date_str,
                    "travellers": travellers,
                    "notes": notes or "",
                },
                "flight": None,
                "status_raw": None,
            }
            await async_save_preview(hass, preview)
            async_dispatcher_send(hass, SIGNAL_PREVIEW_UPDATED)
            return

        preview: dict[str, Any] = {
            "ready": False,
            "error": None,
            "hint": None,
            "input": {
                "airline": airline,
                "flight_number": flight_number,
                "date": date_str,
                "travellers": travellers,
                "notes": notes or "",
            },
            "flight": None,
            "status_raw": None,
        }

        flight: dict[str, Any] = {
            "source": "preview",
            "flight_key": _build_flight_key(airline, flight_number, None, date_str),
            "airline_code": airline,
            "flight_number": flight_number,
            "travellers": travellers,
            "notes": notes,
            "status_state": "unknown",
            "airline_name": None,
            "airline_logo_url": airline_logo_url(airline),
            "aircraft_type": None,
            "dep": {
                "airport": {"iata": None, "name": None, "city": None, "tz": None, "tz_short": None},
                "scheduled": None,
                "estimated": None,
                "actual": None,
                "terminal": None,
                "gate": None,
            },
            "arr": {
                "airport": {"iata": None, "name": None, "city": None, "tz": None, "tz_short": None},
                "scheduled": None,
                "estimated": None,
                "actual": None,
                "terminal": None,
                "gate": None,
            },
        }

        options = options_provider()
        status_raw, err, hint = await _try_enrich_preview(hass, options, airline, flight_number, date_str)

        if status_raw:
            if isinstance(status_raw, dict) and isinstance(status_raw.get("flight"), dict):
                enriched = status_raw.get("flight")
                enriched["travellers"] = travellers
                enriched["notes"] = notes
                preview["flight"] = enriched
            else:
                preview["flight"] = flight
            preview["status_raw"] = status_raw
            # Enrich preview with directory data (airport/airline) before completeness check
            f = preview.get("flight") or {}
            dep = (f.get("dep") or {})
            arr = (f.get("arr") or {})
            dep_air = (dep.get("airport") or {})
            arr_air = (arr.get("airport") or {})

            if f.get("airline_code") and not f.get("airline_name"):
                airline = await get_airline(hass, options, f.get("airline_code"))
                if airline:
                    f["airline_name"] = airline.get("name") or f.get("airline_name")
                    if not f.get("airline_logo_url"):
                        f["airline_logo_url"] = airline.get("logo") or f.get("airline_logo_url")

            if dep_air.get("iata") and (not dep_air.get("name") or not dep_air.get("city") or not dep_air.get("tz")):
                airport = await get_airport(hass, options, dep_air.get("iata"))
                if airport:
                    dep_air["name"] = dep_air.get("name") or airport.get("name")
                    dep_air["city"] = dep_air.get("city") or airport.get("city")
                    dep_air["tz"] = dep_air.get("tz") or airport.get("tz")
            if arr_air.get("iata") and (not arr_air.get("name") or not arr_air.get("city") or not arr_air.get("tz")):
                airport = await get_airport(hass, options, arr_air.get("iata"))
                if airport:
                    arr_air["name"] = arr_air.get("name") or airport.get("name")
                    arr_air["city"] = arr_air.get("city") or airport.get("city")
                    arr_air["tz"] = arr_air.get("tz") or airport.get("tz")

            # Final fallback for missing city/name/tz from static map
            if dep_air.get("iata") and (not dep_air.get("name") or not dep_air.get("city") or not dep_air.get("tz")):
                info = get_airport_info(dep_air.get("iata"), options) or {}
                dep_air["name"] = dep_air.get("name") or info.get("name")
                dep_air["city"] = dep_air.get("city") or info.get("city")
                dep_air["tz"] = dep_air.get("tz") or info.get("tz")
            if arr_air.get("iata") and (not arr_air.get("name") or not arr_air.get("city") or not arr_air.get("tz")):
                info = get_airport_info(arr_air.get("iata"), options) or {}
                arr_air["name"] = arr_air.get("name") or info.get("name")
                arr_air["city"] = arr_air.get("city") or info.get("city")
                arr_air["tz"] = arr_air.get("tz") or info.get("tz")

            dep_sched = dep.get("scheduled")
            arr_sched = arr.get("scheduled")
            if dep_air.get("tz") and not dep_air.get("tz_short"):
                dep_air["tz_short"] = tz_short_name(dep_air.get("tz"), dep_sched)
            if arr_air.get("tz") and not arr_air.get("tz_short"):
                arr_air["tz_short"] = tz_short_name(arr_air.get("tz"), arr_sched)

            dep["airport"] = dep_air
            arr["airport"] = arr_air
            f["dep"] = dep
            f["arr"] = arr
            preview["flight"] = f

            ready, hint = _preview_complete(preview.get("flight"))
            preview["ready"] = ready
            preview["error"] = None if ready else "incomplete"
            preview["hint"] = None if ready else hint
            if not ready and hint:
                persistent_notification.async_create(
                    hass,
                    hint,
                    title="Flight Dashboard — Preview incomplete",
                    notification_id="flight_dashboard_preview_incomplete",
                )
            # Warn (but allow add) if logo is missing
            if ready:
                f = preview.get("flight") or {}
                if not f.get("airline_logo_url"):
                    f["airline_logo_url"] = airline_logo_url(airline)
                if not f.get("airline_logo_url"):
                    preview["warning"] = "Airline logo not available."
                    persistent_notification.async_create(
                        hass,
                        "Airline logo not available for this flight.",
                        title="Flight Dashboard — Preview warning",
                        notification_id="flight_dashboard_preview_warning",
                    )
                # Warn if city is missing but allow add
                dep_air = ((f.get("dep") or {}).get("airport") or {})
                arr_air = ((f.get("arr") or {}).get("airport") or {})
                missing_city = []
                if dep_air.get("iata") and not dep_air.get("city"):
                    missing_city.append(dep_air.get("iata"))
                if arr_air.get("iata") and not arr_air.get("city"):
                    missing_city.append(arr_air.get("iata"))
                if missing_city:
                    preview["warning"] = (preview.get("warning") + " " if preview.get("warning") else "") + (
                        "Airport city missing for: " + ", ".join(missing_city)
                    )
                    persistent_notification.async_create(
                        hass,
                        f"Airport city missing for: {', '.join(missing_city)}",
                        title="Flight Dashboard — Preview warning",
                        notification_id="flight_dashboard_preview_city_missing",
                    )
        else:
            preview["flight"] = flight
            preview["ready"] = False
            preview["error"] = err or "no_match_or_no_provider"
            preview["hint"] = hint or "Either no match was found for that date, or no provider API is configured/available."
            persistent_notification.async_create(
                hass,
                preview["hint"],
                title="Flight Dashboard — Preview incomplete",
                notification_id="flight_dashboard_preview_incomplete",
            )

        await async_save_preview(hass, preview)
        async_dispatcher_send(hass, SIGNAL_PREVIEW_UPDATED)
        persistent_notification.async_create(
            hass,
            f"{airline} {flight_number} on {date_str} (ready={preview['ready']})",
            title="Flight Dashboard — Preview updated",
            notification_id="flight_dashboard_preview_updated",
        )

    async def _svc_confirm(call: ServiceCall) -> None:
        """Persist the current preview as a manual flight."""
        preview = await async_load_preview(hass)
        if not (preview or {}).get("ready"):
            persistent_notification.async_create(
                hass,
                "Preview is incomplete. Run Preview again or check provider configuration.",
                title="Flight Dashboard — Add failed",
                notification_id="flight_dashboard_add_failed",
            )
            return
        f = (preview or {}).get("flight")
        if not isinstance(f, dict):
            persistent_notification.async_create(
                hass,
                "No preview available. Run Preview first.",
                title="Flight Dashboard — Add failed",
                notification_id="flight_dashboard_add_failed",
            )
            return

        try:
            flight_key = await async_add_manual_flight_record(hass, f)
            persistent_notification.async_create(
                hass,
                f"Saved {f.get('airline_code')} {f.get('flight_number')} (key: {flight_key})",
                title="Flight Dashboard — Added",
                notification_id="flight_dashboard_added",
            )
            await async_clear_preview(hass)
            async_dispatcher_send(hass, SIGNAL_PREVIEW_UPDATED)
        except Exception as e:
            _LOGGER.exception("Confirm add failed")
            persistent_notification.async_create(
                hass,
                str(e),
                title="Flight Dashboard — Add failed",
                notification_id="flight_dashboard_add_failed",
            )

    async def _svc_clear(call: ServiceCall) -> None:
        """Clear any stored preview."""
        await async_clear_preview(hass)
        async_dispatcher_send(hass, SIGNAL_PREVIEW_UPDATED)
        persistent_notification.async_create(
            hass,
            "Preview cleared.",
            title="Flight Dashboard — Preview cleared",
            notification_id="flight_dashboard_preview_cleared",
        )

    async def _svc_add_flight(call: ServiceCall) -> None:
        """Add a flight directly from minimal inputs without preview."""
        airline = str(call.data.get("airline", "")).strip().upper()
        flight_number = str(call.data.get("flight_number", "")).strip()
        if not airline or not flight_number:
            q_airline, q_fnum = _parse_query(call.data.get("query"))
            airline = airline or (q_airline or "")
            flight_number = flight_number or (q_fnum or "")
        date_str = str(call.data.get("date", "")).strip()
        travellers = _norm_travellers(call.data.get("travellers"))
        notes = str(call.data.get("notes", "")).strip() or None

        if not date_str:
            persistent_notification.async_create(
                hass,
                "Provide a date in YYYY-MM-DD.",
                title="Flight Dashboard — Add failed",
                notification_id="flight_dashboard_add_failed",
            )
            return
        if not airline or not flight_number:
            persistent_notification.async_create(
                hass,
                "Provide airline + flight_number or a query like 'AI 157'.",
                title="Flight Dashboard — Add failed",
                notification_id="flight_dashboard_add_failed",
            )
            return

        result = await lookup_schedule(hass, options_provider(), f"{airline} {flight_number}", date_str)
        flight = result.get("flight") if isinstance(result, dict) else None
        if isinstance(flight, dict):
            flight["travellers"] = travellers
            flight["notes"] = notes
            try:
                flight_key = await async_add_manual_flight_record(hass, flight)
                persistent_notification.async_create(
                    hass,
                    f"Saved {airline} {flight_number} (key: {flight_key})",
                    title="Flight Dashboard — Added",
                    notification_id="flight_dashboard_added",
                )
                return
            except Exception as e:
                _LOGGER.exception("Add flight failed")
                persistent_notification.async_create(
                    hass,
                    str(e),
                    title="Flight Dashboard — Add failed",
                    notification_id="flight_dashboard_add_failed",
                )
                return

        hint = result.get("hint") if isinstance(result, dict) else None
        persistent_notification.async_create(
            hass,
            hint or "No match found or no provider configured.",
            title="Flight Dashboard — Add failed",
            notification_id="flight_dashboard_add_failed",
        )

    hass.services.async_register(DOMAIN, SERVICE_PREVIEW_FLIGHT, _svc_preview, schema=SERVICE_SCHEMA_PREVIEW)
    hass.services.async_register(DOMAIN, SERVICE_CONFIRM_ADD, _svc_confirm)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_PREVIEW, _svc_clear)
    hass.services.async_register(DOMAIN, SERVICE_ADD_FLIGHT, _svc_add_flight, schema=SERVICE_SCHEMA_PREVIEW)

    _LOGGER.info(
        "Registered preview services: %s, %s, %s",
        SERVICE_PREVIEW_FLIGHT,
        SERVICE_CONFIRM_ADD,
        SERVICE_CLEAR_PREVIEW,
    )
