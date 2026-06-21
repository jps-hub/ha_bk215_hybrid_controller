"""Switch platform for the BK215 hybrid controller integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .controller import BK215HybridController

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class BK215HybridControllerSwitchEntityDescription(SwitchEntityDescription):
    """Describe a controller helper switch."""

    enabled_attr: str
    setter: str
    option_key: str | None = None
    requires_inverter2: bool = False


SWITCH_DESCRIPTIONS: tuple[BK215HybridControllerSwitchEntityDescription, ...] = (
    BK215HybridControllerSwitchEntityDescription(
        key="automatic",
        name=None,
        translation_key="automatic",
        entity_category=EntityCategory.CONFIG,
        enabled_attr="automatic_enabled",
        setter="async_set_automatic_enabled",
        option_key="automatic_enabled",
    ),
    BK215HybridControllerSwitchEntityDescription(
        key="boost",
        name=None,
        translation_key="boost",
        entity_category=EntityCategory.CONFIG,
        enabled_attr="boost_enabled",
        setter="async_set_boost_enabled",
    ),
    BK215HybridControllerSwitchEntityDescription(
        key="inverter1_helper",
        name=None,
        translation_key="inverter1_helper",
        entity_category=EntityCategory.CONFIG,
        enabled_attr="inverter1_helper_enabled",
        setter="async_set_inverter1_helper",
    ),
    BK215HybridControllerSwitchEntityDescription(
        key="inverter2_helper",
        name=None,
        translation_key="inverter2_helper",
        entity_category=EntityCategory.CONFIG,
        enabled_attr="inverter2_helper_enabled",
        setter="async_set_inverter2_helper",
        requires_inverter2=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up helper switches from a config entry."""
    controller: BK215HybridController = entry.runtime_data
    entities = [
        BK215HybridControllerHelperSwitch(controller, entry, description)
        for description in SWITCH_DESCRIPTIONS
        if not description.requires_inverter2 or controller.has_inverter2
    ]
    async_add_entities(entities)


class BK215HybridControllerHelperSwitch(SwitchEntity):
    """Representation of an internal helper switch."""

    _attr_has_entity_name = True
    entity_description: BK215HybridControllerSwitchEntityDescription

    def __init__(
        self,
        controller: BK215HybridController,
        entry: ConfigEntry,
        description: BK215HybridControllerSwitchEntityDescription,
    ) -> None:
        """Initialize the helper switch."""
        self.entity_description = description
        self._controller = controller
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_translation_key = description.translation_key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="JPS",
            model="Hybrid Controller",
        )

    @property
    def available(self) -> bool:
        """Return if the helper entity is available."""
        return (
            not self.entity_description.requires_inverter2
            or self._controller.has_inverter2
        )

    @property
    def is_on(self) -> bool:
        """Return the current switch value."""
        return bool(getattr(self._controller, self.entity_description.enabled_attr))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the helper switch on."""
        getattr(self._controller, self.entity_description.setter)(True)
        if self.entity_description.option_key:
            self.hass.config_entries.async_update_entry(
                self._entry,
                options={
                    **dict(self._entry.options),
                    self.entity_description.option_key: True,
                },
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the helper switch off."""
        getattr(self._controller, self.entity_description.setter)(False)
        if self.entity_description.option_key:
            self.hass.config_entries.async_update_entry(
                self._entry,
                options={
                    **dict(self._entry.options),
                    self.entity_description.option_key: False,
                },
            )

    async def async_added_to_hass(self) -> None:
        """Register for controller state updates."""
        self.async_on_remove(
            self._controller.async_add_state_listener(self._handle_controller_update)
        )

    @callback
    def _handle_controller_update(self) -> None:
        """Handle updated controller runtime state."""
        self.async_write_ha_state()
