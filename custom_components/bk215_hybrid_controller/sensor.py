"""Sensor platform for the BK215 hybrid controller integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN
from .controller import BK215HybridController

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class BK215HybridControllerSensorEntityDescription(SensorEntityDescription):
    """Describe a controller sensor."""

    value_fn: Callable[[BK215HybridController], Any]


SENSOR_DESCRIPTIONS: tuple[BK215HybridControllerSensorEntityDescription, ...] = (
    BK215HybridControllerSensorEntityDescription(
        key="system_state",
        name=None,
        translation_key="system_state",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "inactive",
            "inv_off",
            "inv_on",
            "soc_low",
            "failure",
            "inv1_on_inv2_failure",
            "inv2_on_inv1_failure",
        ],
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.state.system_state,
    ),
    BK215HybridControllerSensorEntityDescription(
        key="deadband_state",
        name=None,
        translation_key="deadband_state",
        device_class=SensorDeviceClass.ENUM,
        options=["neutral", "import", "export"],
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.state.deadband_state,
    ),
    BK215HybridControllerSensorEntityDescription(
        key="integral_store",
        name=None,
        translation_key="integral_store",
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.state.integral,
    ),
    BK215HybridControllerSensorEntityDescription(
        key="last_target_store",
        name=None,
        translation_key="last_target_store",
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.state.last_target,
    ),
    BK215HybridControllerSensorEntityDescription(
        key="last_error_store",
        name=None,
        translation_key="last_error_store",
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.state.last_error,
    ),
    BK215HybridControllerSensorEntityDescription(
        key="filtered_error_store",
        name=None,
        translation_key="filtered_error_store",
        native_unit_of_measurement=UnitOfPower.WATT,
        suggested_display_precision=2,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda controller: controller.state.deadband_filtered_error,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up controller sensors from a config entry."""
    controller: BK215HybridController = entry.runtime_data
    async_add_entities(
        BK215HybridControllerSensor(controller, entry, description)
        for description in SENSOR_DESCRIPTIONS
    )


class BK215HybridControllerSensor(SensorEntity):
    """Representation of one controller runtime sensor."""

    _attr_has_entity_name = True
    entity_description: BK215HybridControllerSensorEntityDescription

    def __init__(
        self,
        controller: BK215HybridController,
        entry: ConfigEntry,
        description: BK215HybridControllerSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
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
    def native_value(self) -> Any:
        """Return the current sensor value."""
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
