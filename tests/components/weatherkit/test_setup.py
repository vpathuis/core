"""Test the WeatherKit setup process."""
from unittest.mock import patch

from apple_weatherkit.client import (
    WeatherKitApiClientAuthenticationError,
    WeatherKitApiClientError,
)
import pytest

from homeassistant import config_entries
from homeassistant.components.weatherkit import async_setup_entry
from homeassistant.components.weatherkit.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from . import EXAMPLE_CONFIG_DATA

from tests.common import MockConfigEntry


async def test_auth_error_handling(hass: HomeAssistant) -> None:
    """Test that we handle authentication errors at setup properly."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        unique_id="0123456",
        data=EXAMPLE_CONFIG_DATA,
    )

    with patch(
        "homeassistant.components.weatherkit.WeatherKitApiClient.get_weather_data",
        side_effect=WeatherKitApiClientAuthenticationError,
    ), patch(
        "homeassistant.components.weatherkit.WeatherKitApiClient.get_availability",
        side_effect=WeatherKitApiClientAuthenticationError,
    ):
        entry.add_to_hass(hass)
        setup_result = await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert setup_result is False


async def test_client_error_handling(hass: HomeAssistant) -> None:
    """Test that we handle API client errors at setup properly."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Home",
        unique_id="0123456",
        data=EXAMPLE_CONFIG_DATA,
    )

    with pytest.raises(ConfigEntryNotReady), patch(
        "homeassistant.components.weatherkit.WeatherKitApiClient.get_weather_data",
        side_effect=WeatherKitApiClientError,
    ), patch(
        "homeassistant.components.weatherkit.WeatherKitApiClient.get_availability",
        side_effect=WeatherKitApiClientError,
    ):
        entry.add_to_hass(hass)
        config_entries.current_entry.set(entry)
        await async_setup_entry(hass, entry)
        await hass.async_block_till_done()
