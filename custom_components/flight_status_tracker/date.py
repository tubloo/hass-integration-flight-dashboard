"""Date entity for Flight Status Tracker built-in add-flight inputs."""
from __future__ import annotations

from datetime import date

from homeassistant.components.date import DateEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .ui_inputs_store import KEY_DATE, async_load_inputs, async_set_input


class FlightStatusTrackerFlightDate(DateEntity):
    _attr_has_entity_name = True
    _attr_unique_id = f"{DOMAIN}_input_flight_date"
    _attr_name = "Add flight date"
    _attr_icon = "mdi:calendar"
    _attr_suggested_object_id = f"{DOMAIN}_add_flight_date"

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._value: date | None = None

    @property
    def native_value(self) -> date | None:
        return self._value

    async def async_added_to_hass(self) -> None:
        inputs = await async_load_inputs(self.hass)
        raw = str(inputs.get(KEY_DATE) or "").strip()
        self._value = None
        if raw:
            try:
                self._value = date.fromisoformat(raw)
            except Exception:
                self._value = None
        self.async_write_ha_state()

    async def async_set_value(self, value: date) -> None:
        self._value = value
        await async_set_input(self.hass, KEY_DATE, value.isoformat())
        self.async_write_ha_state()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    async_add_entities([FlightStatusTrackerFlightDate(hass)])
