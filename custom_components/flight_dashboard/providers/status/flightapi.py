"""FlightAPI.io status/schedule provider.

Docs: https://docs.flightapi.io/
Endpoint used: GET /airline/{apiKey}?num=XX&date=YYYYMMDD&name=YY
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .base import FlightStatus


def _error_type(status: int, payload: Any) -> str:
    msg = ""
    if isinstance(payload, dict):
        msg = str(payload.get("message") or payload.get("error") or "")
    msg_l = msg.lower()
    if status in (401, 403) or "api key" in msg_l or "unauthorized" in msg_l:
        return "auth_error"
    if status == 429 or "rate" in msg_l or "limit" in msg_l:
        return "rate_limited"
    if status == 402 or "quota" in msg_l or "credits" in msg_l:
        return "quota_exceeded"
    if status == 400 or "invalid" in msg_l:
        return "bad_request"
    return "provider_error"


def _date_to_yyyymmdd(s: str | None) -> str | None:
    if not s or len(s) < 10:
        return None
    try:
        d = datetime.fromisoformat(s[:10]).date()
        return d.strftime("%Y%m%d")
    except Exception:
        return None


def _parse_iso(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _iso(dt: datetime | None) -> str | None:
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _parse_human_time(s: str | None, base_date: date | None, tz_hint) -> str | None:
    if not s or not base_date:
        return None
    raw = s.strip()
    if not raw:
        return None
    patterns = (
        "%I:%M %p, %b %d",  # 10:45 PM, Jan 25
        "%H:%M, %b %d",     # 14:55, Jul 16
    )
    for fmt in patterns:
        try:
            dt = datetime.strptime(raw, fmt)
            dt = dt.replace(year=base_date.year)
            if tz_hint:
                dt = dt.replace(tzinfo=tz_hint)
            return _iso(dt)
        except Exception:
            continue
    return None


def _pick_dep_arr(payload: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(payload, list) or len(payload) == 0:
        return None, None
    if len(payload) == 1:
        return payload[0], None
    # Prefer entries with known arrival/departure hints
    dep = None
    arr = None
    for item in payload:
        if not isinstance(item, dict):
            continue
        if item.get("outGateTime") or item.get("offGroundTime"):
            dep = item
        if item.get("inGateTime") or item.get("onGroundTime"):
            arr = item
    if not dep:
        dep = payload[0]
    if not arr and len(payload) > 1:
        arr = payload[1]
    return dep, arr


class FlightAPIStatusProvider:
    def __init__(self, hass: HomeAssistant, api_key: str) -> None:
        self.hass = hass
        self.api_key = api_key.strip()

    async def async_get_status(self, flight: dict[str, Any]) -> FlightStatus | None:
        airline = (flight.get("airline_code") or "").strip().upper()
        number = str(flight.get("flight_number") or "").strip()
        if not airline or not number:
            return None

        # Prefer scheduled_departure if provided, else dep.scheduled
        sched = flight.get("scheduled_departure") or (flight.get("dep") or {}).get("scheduled")
        yyyymmdd = _date_to_yyyymmdd(sched)
        if not yyyymmdd:
            return None

        url = f"https://api.flightapi.io/airline/{self.api_key}"
        params = {"num": number, "date": yyyymmdd, "name": airline}

        session = async_get_clientsession(self.hass)
        async with session.get(url, params=params, timeout=25) as resp:
            payload = await resp.json(content_type=None)
            retry_after = resp.headers.get("Retry-After")

        if resp.status >= 400:
            err_type = _error_type(resp.status, payload)
            details = {"provider": "flightapi", "state": "unknown", "error": err_type}
            if retry_after and retry_after.isdigit():
                details["retry_after"] = int(retry_after)
            return FlightStatus(provider="flightapi", state="unknown", details=details)

        # Some errors are returned in JSON even with 200
        if isinstance(payload, dict) and (payload.get("error") or payload.get("message")):
            err_type = _error_type(400, payload)
            details = {
                "provider": "flightapi",
                "state": "unknown",
                "error": err_type,
                "error_message": str(payload.get("error") or payload.get("message")),
            }
            return FlightStatus(provider="flightapi", state="unknown", details=details)

        dep_obj, arr_obj = _pick_dep_arr(payload)
        if not dep_obj and not arr_obj:
            return None

        base_dt = _parse_iso((dep_obj or {}).get("departureDateTime"))
        base_date = base_dt.date() if base_dt else None
        dep_tz_hint = base_dt.tzinfo if base_dt else None
        arr_dt_hint = _parse_iso((arr_obj or {}).get("arrivalDateTime"))
        arr_tz_hint = arr_dt_hint.tzinfo if arr_dt_hint else None

        dep_sched = _parse_human_time((dep_obj or {}).get("scheduledTime"), base_date, dep_tz_hint) or _iso(base_dt)
        arr_sched = _parse_human_time((arr_obj or {}).get("scheduledTime"), base_date, arr_tz_hint) or _iso(arr_dt_hint)
        dep_est = _parse_human_time((dep_obj or {}).get("estimatedTime"), base_date, dep_tz_hint)
        arr_est = _parse_human_time((arr_obj or {}).get("estimatedTime"), base_date, arr_tz_hint)
        dep_act = _parse_human_time((dep_obj or {}).get("offGroundTime") or (dep_obj or {}).get("outGateTime"), base_date, dep_tz_hint)
        arr_act = _parse_human_time((arr_obj or {}).get("onGroundTime") or (arr_obj or {}).get("inGateTime"), base_date, arr_tz_hint)

        details = {
            "provider": "flightapi",
            "state": (dep_obj or {}).get("status") or (arr_obj or {}).get("status") or "unknown",
            "dep_scheduled": dep_sched,
            "dep_estimated": dep_est,
            "dep_actual": dep_act,
            "arr_scheduled": arr_sched,
            "arr_estimated": arr_est,
            "arr_actual": arr_act,
            "dep_iata": (dep_obj or {}).get("airportCode"),
            "arr_iata": (arr_obj or {}).get("airportCode"),
            "airline_name": (dep_obj or {}).get("airlineName") or (arr_obj or {}).get("airlineName"),
            "terminal_dep": (dep_obj or {}).get("terminal"),
            "gate_dep": (dep_obj or {}).get("gate"),
            "terminal_arr": (arr_obj or {}).get("terminal"),
            "gate_arr": (arr_obj or {}).get("gate"),
        }

        return FlightStatus(provider="flightapi", state=details["state"], details=details)
