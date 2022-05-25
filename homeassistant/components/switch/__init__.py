"""Component to interface with switches that can be controlled remotely."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging

import voluptuous as vol

from homeassistant.backports.enum import StrEnum
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SERVICE_TOGGLE,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.config_validation import (  # noqa: F401
    PLATFORM_SCHEMA,
    PLATFORM_SCHEMA_BASE,
)
from homeassistant.helpers.entity import (
    ToggleEntity,
    ToggleEntityDescription,
    state_filter,
)
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import bind_hass

from .const import DOMAIN

SCAN_INTERVAL = timedelta(seconds=30)

ENTITY_ID_FORMAT = DOMAIN + ".{}"

MIN_TIME_BETWEEN_SCANS = timedelta(seconds=10)

_LOGGER = logging.getLogger(__name__)


class SwitchDeviceClass(StrEnum):
    """Device class for switches."""

    OUTLET = "outlet"
    SWITCH = "switch"


DEVICE_CLASSES_SCHEMA = vol.All(vol.Lower, vol.Coerce(SwitchDeviceClass))

# DEVICE_CLASS* below are deprecated as of 2021.12
# use the SwitchDeviceClass enum instead.
DEVICE_CLASSES = [cls.value for cls in SwitchDeviceClass]
DEVICE_CLASS_OUTLET = SwitchDeviceClass.OUTLET.value
DEVICE_CLASS_SWITCH = SwitchDeviceClass.SWITCH.value


@bind_hass
def is_on(hass: HomeAssistant, entity_id: str) -> bool:
    """Return if the switch is on based on the statemachine.

    Async friendly.
    """
    return hass.states.is_state(entity_id, STATE_ON)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Track states and offer events for switches."""
    component = hass.data[DOMAIN] = EntityComponent(
        _LOGGER, DOMAIN, hass, SCAN_INTERVAL
    )
    await component.async_setup(config)

    async def async_handle_switch_off_service(
        switch: SwitchEntity, call: ServiceCall
    ) -> None:
        """Handle turning off a light."""
        # pylint: disable-next=protected-access
        switch._context_filter = state_filter(STATE_OFF)
        await switch.async_turn_off()

    async def async_handle_switch_on_service(
        switch: SwitchEntity, call: ServiceCall
    ) -> None:
        """Handle turning off a light."""
        # pylint: disable-next=protected-access
        switch._context_filter = state_filter(STATE_ON)
        await switch.async_turn_on()

    async def async_handle_toggle_service(
        switch: SwitchEntity, call: ServiceCall
    ) -> None:
        """Handle toggling a light."""
        if switch.is_on:
            await async_handle_switch_off_service(switch, call)
        else:
            await async_handle_switch_on_service(switch, call)

    component.async_register_entity_service(
        SERVICE_TURN_OFF, {}, async_handle_switch_off_service
    )
    component.async_register_entity_service(
        SERVICE_TURN_ON, {}, async_handle_switch_on_service
    )
    component.async_register_entity_service(
        SERVICE_TOGGLE, {}, async_handle_toggle_service
    )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    component: EntityComponent = hass.data[DOMAIN]
    return await component.async_setup_entry(entry)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    component: EntityComponent = hass.data[DOMAIN]
    return await component.async_unload_entry(entry)


@dataclass
class SwitchEntityDescription(ToggleEntityDescription):
    """A class that describes switch entities."""

    device_class: SwitchDeviceClass | str | None = None


class SwitchEntity(ToggleEntity):
    """Base class for switch entities."""

    entity_description: SwitchEntityDescription
    _attr_device_class: SwitchDeviceClass | str | None

    @property
    def device_class(self) -> SwitchDeviceClass | str | None:
        """Return the class of this entity."""
        if hasattr(self, "_attr_device_class"):
            return self._attr_device_class
        if hasattr(self, "entity_description"):
            return self.entity_description.device_class
        return None
