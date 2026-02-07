"""Text entities for Flight Status Tracker built-in add-flight inputs."""
from __future__ import annotations

from homeassistant.components.text import TextEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .ui_inputs_store import (
    KEY_AIRLINE,
    KEY_DEP_AIRPORT,
    KEY_FLIGHT_NUMBER,
    KEY_NOTES,
    KEY_TRAVELLERS,
    async_load_inputs,
    async_set_input,
)


class _BaseInputText(TextEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        unique_id: str,
        suggested_object_id: str,
        name: str,
        icon: str,
        key: str,
        max_len: int = 255,
    ) -> None:
        self.hass = hass
        self._key = key
        self._attr_unique_id = unique_id
        self._attr_suggested_object_id = suggested_object_id
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_max = max_len
        self._attr_native_min = 0
        self._value = ""

    @property
    def native_value(self) -> str:
        return self._value

    async def async_added_to_hass(self) -> None:
        inputs = await async_load_inputs(self.hass)
        val = inputs.get(self._key, "")
        self._value = str(val or "")
        self.async_write_ha_state()

    async def async_set_value(self, value: str) -> None:
        v = (value or "").strip()
        self._value = v
        await async_set_input(self.hass, self._key, v)
        self.async_write_ha_state()


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    async_add_entities(
        [
            _BaseInputText(
                hass,
                unique_id=f"{DOMAIN}_input_airline",
                suggested_object_id=f"{DOMAIN}_add_flight_airline",
                name="Add flight airline",
                icon="mdi:airplane",
                key=KEY_AIRLINE,
                max_len=3,
            ),
            _BaseInputText(
                hass,
                unique_id=f"{DOMAIN}_input_flight_number",
                suggested_object_id=f"{DOMAIN}_add_flight_number",
                name="Add flight number",
                icon="mdi:numeric",
                key=KEY_FLIGHT_NUMBER,
                max_len=8,
            ),
            _BaseInputText(
                hass,
                unique_id=f"{DOMAIN}_input_dep_airport",
                suggested_object_id=f"{DOMAIN}_add_flight_dep_airport",
                name="Add flight departure airport (optional)",
                icon="mdi:airport",
                key=KEY_DEP_AIRPORT,
                max_len=4,
            ),
            _BaseInputText(
                hass,
                unique_id=f"{DOMAIN}_input_travellers",
                suggested_object_id=f"{DOMAIN}_add_flight_travellers",
                name="Add flight travellers (optional)",
                icon="mdi:account-multiple",
                key=KEY_TRAVELLERS,
                max_len=255,
            ),
            _BaseInputText(
                hass,
                unique_id=f"{DOMAIN}_input_notes",
                suggested_object_id=f"{DOMAIN}_add_flight_notes",
                name="Add flight notes (optional)",
                icon="mdi:note-text-outline",
                key=KEY_NOTES,
                max_len=255,
            ),
        ]
    )
