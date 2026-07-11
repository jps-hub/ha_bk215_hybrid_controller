"""Set up the BK215 hybrid controller integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .controller import BK215HybridController
from .models import ControllerConfig

type BK215HybridControllerConfigEntry = ConfigEntry[BK215HybridController]


async def async_setup_entry(
    hass: HomeAssistant, entry: BK215HybridControllerConfigEntry
) -> bool:
    """Set up the integration from a config entry."""
    controller = BK215HybridController(
        hass,
        ControllerConfig.from_dict({**dict(entry.data), **dict(entry.options)}),
    )
    entry.runtime_data = controller
    await controller.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: BK215HybridControllerConfigEntry
) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_stop()
    return unload_ok
"""Set up the BK215 hybrid controller integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, PLATFORMS
from .controller import BK215HybridController
from .models import ControllerConfig

type BK215HybridControllerConfigEntry = ConfigEntry[BK215HybridController]


async def async_setup_entry(
    hass: HomeAssistant, entry: BK215HybridControllerConfigEntry
) -> bool:
    """Set up the integration from a config entry."""
    controller = BK215HybridController(
        hass,
        ControllerConfig.from_dict({**dict(entry.data), **dict(entry.options)}),
    )
    entry.runtime_data = controller
    await controller.async_start()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: BK215HybridControllerConfigEntry
) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.async_stop()
    return unload_ok
