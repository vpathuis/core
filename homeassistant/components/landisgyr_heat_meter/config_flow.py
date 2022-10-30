"""Config flow for Landis+Gyr Heat Meter integration."""
from __future__ import annotations

import logging
import os

import async_timeout
import serial
import serial.tools.list_ports
from ultraheat_api import HeatMeterService, UltraheatReader
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_DEVICE
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .const import CONF_BATTERY_OPERATED, DOMAIN, ULTRAHEAT_TIMEOUT

_LOGGER = logging.getLogger(__name__)

CONF_MANUAL_PATH = "Enter Manually"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Ultraheat Heat Meter."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the ConfigFlow."""
        super().__init__()
        self.dev_path = None
        self.battery_operated = None

    async def async_step_user(self, user_input=None):
        """Step when setting up serial configuration."""
        errors = {}

        if user_input is not None:
            if user_input[CONF_DEVICE] == CONF_MANUAL_PATH:
                return await self.async_step_setup_serial_manual_path()

            self.dev_path = await self.hass.async_add_executor_job(
                get_serial_by_id, user_input[CONF_DEVICE]
            )
            _LOGGER.debug("Using this path : %s", self.dev_path)

            return await self.async_step_battery_or_mains()

        ports = await self.get_ports()

        schema = vol.Schema({vol.Required(CONF_DEVICE): vol.In(ports)})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_setup_serial_manual_path(self, user_input=None):
        """Set path manually."""
        errors = {}

        if user_input is not None:
            self.dev_path = user_input[CONF_DEVICE]

            return await self.async_step_battery_or_mains()

        schema = vol.Schema({vol.Required(CONF_DEVICE): str})
        return self.async_show_form(
            step_id="setup_serial_manual_path",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_battery_or_mains(self, user_input=None):
        """Let the user choose if the device is battery operated."""
        errors = {}

        if user_input is not None:
            self.battery_operated = user_input[CONF_BATTERY_OPERATED]
            try:
                return await self.validate_and_create_entry()
            except CannotConnect:
                errors["base"] = "cannot_connect"

        schema = vol.Schema(
            {vol.Required(CONF_BATTERY_OPERATED, default=True): cv.boolean}
        )
        return self.async_show_form(
            step_id="battery_or_mains",
            data_schema=schema,
            errors=errors,
        )

    async def validate_and_create_entry(self):
        """Try to connect to the device path and return an entry."""
        model, device_number = await self.validate_ultraheat(self.dev_path)

        _LOGGER.debug("Got model %s and device_number %s", model, device_number)
        await self.async_set_unique_id(device_number)
        self._abort_if_unique_id_configured()
        data = {
            CONF_DEVICE: self.dev_path,
            CONF_BATTERY_OPERATED: self.battery_operated,
            "model": model,
            "device_number": device_number,
        }
        return self.async_create_entry(
            title=model,
            data=data,
        )

    async def validate_ultraheat(self, port: str):
        """Validate the user input allows us to connect."""

        reader = UltraheatReader(port)
        heat_meter = HeatMeterService(reader)
        try:
            async with async_timeout.timeout(ULTRAHEAT_TIMEOUT):
                # validate and retrieve the model and device number for a unique id
                data = await self.hass.async_add_executor_job(heat_meter.read)
                _LOGGER.debug("Got data from Ultraheat API: %s", data)

        except Exception as err:
            _LOGGER.warning("Failed read data from: %s. %s", port, err)
            raise CannotConnect(f"Error communicating with device: {err}") from err

        _LOGGER.debug("Successfully connected to %s", port)
        return data.model, data.device_number

    async def get_ports(self) -> dict:
        """Get the available ports."""
        ports = await self.hass.async_add_executor_job(serial.tools.list_ports.comports)
        formatted_ports = {}
        for port in ports:
            formatted_ports[
                port.device
            ] = f"{port}, s/n: {port.serial_number or 'n/a'}" + (
                f" - {port.manufacturer}" if port.manufacturer else ""
            )
        formatted_ports[CONF_MANUAL_PATH] = CONF_MANUAL_PATH
        return formatted_ports


def get_serial_by_id(dev_path: str) -> str:
    """Return a /dev/serial/by-id match for given device if available."""
    by_id = "/dev/serial/by-id"
    if not os.path.isdir(by_id):
        return dev_path

    for path in (entry.path for entry in os.scandir(by_id) if entry.is_symlink()):
        if os.path.realpath(path) == dev_path:
            return path
    return dev_path


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""
