"""Binary sensor platform for the BK215 hybrid controller integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .controller import BK215HybridController

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class BK215HybridControllerBinarySensorEntityDescription(BinarySensorEntityDescription):
    """Describe a controller binary sensor."""

    value_fn: Callable[[BK215HybridController], bool]
    requires_inverter2: bool = False
    requires_inverter3: bool = False
    requires_inverter4: bool = False


BINARY_SENSOR_DESCRIPTIONS: tuple[
    BK215HybridControllerBinarySensorEntityDescription, ...
] = (
    BK215HybridControllerBinarySensorEntityDescription(
        key="automatic_active",
        name=None,
        translation_key="automatic_active",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.automatic_enabled,
    ),
    BK215HybridControllerBinarySensorEntityDescription(
        key="boost_active",
        name=None,
        translation_key="boost_active",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.boost_active,
    ),
    BK215HybridControllerBinarySensorEntityDescription(
        key="inverter1_helper_active",
        name=None,
        translation_key="inverter1_helper_active",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.inverter1_active,
    ),
    BK215HybridControllerBinarySensorEntityDescription(
        key="inverter2_helper_active",
        name=None,
        translation_key="inverter2_helper_active",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.inverter2_active,
        requires_inverter2=True,
    ),
    BK215HybridControllerBinarySensorEntityDescription(
        key="inverter1_switch",
        name=None,
        translation_key="inverter1_switch",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.inverter1_switch_on,
    ),
    BK215HybridControllerBinarySensorEntityDescription(
        key="inverter2_switch",
        name=None,
        translation_key="inverter2_switch",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.inverter2_switch_on,
        requires_inverter2=True,
    ),
    BK215HybridControllerBinarySensorEntityDescription(
        key="inverter1_manual",
        name=None,
        translation_key="inverter1_manual",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.inverter1_manual_enabled,
    ),
    BK215HybridControllerBinarySensorEntityDescription(
        key="inverter2_manual",
        name=None,
        translation_key="inverter2_manual",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.inverter2_manual_enabled,
        requires_inverter2=True,
    ),
    BK215HybridControllerBinarySensorEntityDescription(
        key="inverter3_helper_active",
        name=None,
        translation_key="inverter3_helper_active",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.inverter3_active,
        requires_inverter3=True,
    ),
    BK215HybridControllerBinarySensorEntityDescription(
        key="inverter4_helper_active",
        name=None,
        translation_key="inverter4_helper_active",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.inverter4_active,
        requires_inverter4=True,
    ),
    BK215HybridControllerBinarySensorEntityDescription(
        key="inverter3_switch",
        name=None,
        translation_key="inverter3_switch",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.inverter3_switch_on,
        requires_inverter3=True,
    ),
    BK215HybridControllerBinarySensorEntityDescription(
        key="inverter4_switch",
        name=None,
        translation_key="inverter4_switch",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.inverter4_switch_on,
        requires_inverter4=True,
    ),
    BK215HybridControllerBinarySensorEntityDescription(
        key="inverter3_manual",
        name=None,
        translation_key="inverter3_manual",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.inverter3_manual_enabled,
        requires_inverter3=True,
    ),
    BK215HybridControllerBinarySensorEntityDescription(
        key="inverter4_manual",
        name=None,
        translation_key="inverter4_manual",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.inverter4_manual_enabled,
        requires_inverter4=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up controller binary sensors from a config entry."""
    controller: BK215HybridController = entry.runtime_data
    async_add_entities(
        BK215HybridControllerBinarySensor(controller, entry, description)
        for description in BINARY_SENSOR_DESCRIPTIONS
        if not description.requires_inverter2 or controller.has_inverter2
        if not description.requires_inverter3 or controller.has_inverter3
        if not description.requires_inverter4 or controller.has_inverter4
    )


class BK215HybridControllerBinarySensor(BinarySensorEntity):
    """Representation of one controller runtime binary sensor."""

    _attr_has_entity_name = True
    entity_description: BK215HybridControllerBinarySensorEntityDescription

    def __init__(
        self,
        controller: BK215HybridController,
        entry: ConfigEntry,
        description: BK215HybridControllerBinarySensorEntityDescription,
    ) -> None:
        """Initialize the binary sensor."""
        self.entity_description = description
        self._controller = controller
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
        """Return if the binary sensor is available."""
        return (
            not self.entity_description.requires_inverter2
            or self._controller.has_inverter2
        )

    @property
    def is_on(self) -> bool:
        """Return the current binary sensor value."""
        return self.entity_description.value_fn(self._controller)

    async def async_added_to_hass(self) -> None:
        """Register for controller state updates."""
        self.async_on_remove(
            self._controller.async_add_state_listener(self._handle_controller_update)
        )

    @callback
    def _handle_controller_update(self) -> None:
        """Handle updated controller runtime state."""
        self.async_write_ha_state()
