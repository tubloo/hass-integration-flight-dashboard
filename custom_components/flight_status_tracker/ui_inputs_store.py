"""Persisted UI input values for the built-in 'Add Flight' flow.

Home Assistant cannot (and should not) auto-create user scripts/automations.
To keep onboarding low-friction, we ship text/date entities that act like the
traditional helpers (input_text/input_datetime), backed by a Store.
"""
from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_STORE_VERSION = 1
_STORE_KEY = f"{DOMAIN}.ui_inputs"

# Keys used in stored dict
KEY_AIRLINE = "airline"
KEY_FLIGHT_NUMBER = "flight_number"
KEY_DEP_AIRPORT = "dep_airport"
KEY_TRAVELLERS = "travellers"
KEY_NOTES = "notes"
KEY_DATE = "date"  # YYYY-MM-DD

DEFAULT_INPUTS: dict[str, Any] = {
    KEY_AIRLINE: "",
    KEY_FLIGHT_NUMBER: "",
    KEY_DEP_AIRPORT: "",
    KEY_TRAVELLERS: "",
    KEY_NOTES: "",
    KEY_DATE: "",
}


def _store(hass: HomeAssistant) -> Store:
    return Store(hass, _STORE_VERSION, _STORE_KEY)


async def async_load_inputs(hass: HomeAssistant) -> dict[str, Any]:
    data = await _store(hass).async_load() or {}
    raw = data.get("inputs")
    if not isinstance(raw, dict):
        return dict(DEFAULT_INPUTS)
    merged = dict(DEFAULT_INPUTS)
    merged.update({k: raw.get(k, merged.get(k)) for k in DEFAULT_INPUTS})
    return merged


async def async_save_inputs(hass: HomeAssistant, inputs: dict[str, Any]) -> None:
    merged = dict(DEFAULT_INPUTS)
    for k in DEFAULT_INPUTS:
        merged[k] = inputs.get(k, merged[k])
    await _store(hass).async_save({"inputs": merged})


async def async_set_input(hass: HomeAssistant, key: str, value: Any) -> dict[str, Any]:
    inputs = await async_load_inputs(hass)
    inputs[key] = value
    await async_save_inputs(hass, inputs)
    return inputs

