"""Config flow for Minecraft Server integration."""
from contextlib import suppress
import ipaddress

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT

from . import MinecraftServer, helpers
from .const import DEFAULT_HOST, DEFAULT_NAME, DEFAULT_PORT, DOMAIN


class MinecraftServerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Minecraft Server."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            host = None
            port = DEFAULT_PORT
            # Split address at last occurrence of ':'.
            address_left, separator, address_right = user_input[CONF_HOST].rpartition(
                ":"
            )
            # If no separator is found, 'rpartition' return ('', '', original_string).
            if separator == "":
                host = address_right
            else:
                host = address_left
                with suppress(ValueError):
                    port = int(address_right)

            # Remove '[' and ']' in case of an IPv6 address.
            host = host.strip("[]")

            # Check if 'host' is a valid IP address and if so, get the MAC address.
            ip_address = None
            with suppress(ValueError):
                ip_address = ipaddress.ip_address(host)

            # Create server instance with configuration data and ping the server.
            config_data = {
                CONF_NAME: user_input[CONF_NAME],
                CONF_HOST: host,
                CONF_PORT: port,
            }
            server = MinecraftServer(self.hass, "dummy_unique_id", config_data)
            await server.async_check_connection()
            if not server.online:
                # Host or port invalid or server not reachable.
                errors["base"] = "cannot_connect"
            else:
                # Build config entry title.
                title = f"{host}:{port}"
                if ip_address is not None:
                    # Since IP addresses can change and therefore are not allowed
                    # in a unique_id, fall back to the MAC address and port (to
                    # support servers with same MAC address but different ports).
                    if ip_address.version == 6:
                        title = f"[{host}]:{port}"
                else:
                    # Check if 'host' is a valid SRV record.
                    srv_record = await helpers.async_check_srv_record(self.hass, host)
                    if srv_record is not None:
                        # Use only SRV host name in unique_id (does not change).
                        title = host

                # Configuration data are available and no error was detected,
                # create configuration entry.
                return self.async_create_entry(title=title, data=config_data)

        # Show configuration form (default form in case of no user_input,
        # form filled with user_input and eventually with errors otherwise).
        return self._show_config_form(user_input, errors)

    def _show_config_form(self, user_input=None, errors=None):
        """Show the setup form to the user."""
        if user_input is None:
            user_input = {}

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME, default=user_input.get(CONF_NAME, DEFAULT_NAME)
                    ): str,
                    vol.Required(
                        CONF_HOST, default=user_input.get(CONF_HOST, DEFAULT_HOST)
                    ): vol.All(str, vol.Lower),
                }
            ),
            errors=errors,
        )
