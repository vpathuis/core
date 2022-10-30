"""The Landis+Gyr Heat Meter integration."""
from __future__ import annotations

import logging

from ultraheat_api import HeatMeterService, UltraheatReader

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    CONF_BATTERY_OPERATED,
    DOMAIN,
    POLLING_INTERVAL_BATTERY,
    POLLING_INTERVAL_MAINS,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up heat meter from a config entry."""

    _LOGGER.debug("Initializing %s integration on %s", DOMAIN, entry.data[CONF_DEVICE])
    reader = UltraheatReader(entry.data[CONF_DEVICE])

    api = HeatMeterService(reader)

    async def async_update_data():
        """Fetch data from the API."""
        _LOGGER.info("Polling on %s", entry.data[CONF_DEVICE])
        return await hass.async_add_executor_job(api.read)

    # Polling is only daily to prevent battery drain.
    if CONF_BATTERY_OPERATED in entry.data and entry.data[CONF_BATTERY_OPERATED]:
        polling_interval = POLLING_INTERVAL_BATTERY
    else:
        polling_interval = POLLING_INTERVAL_MAINS

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="ultraheat_gateway",
        update_method=async_update_data,
        update_interval=polling_interval,
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
