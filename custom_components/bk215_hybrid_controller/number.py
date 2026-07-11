"""Number platform for the BK215 hybrid controller integration."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    DEFAULT_CHARGE_LIMIT_START,
    DEFAULT_MAX_POWER_INVERTER,
    DEFAULT_MIN_POWER_INVERTER,
    DEFAULT_OFFSET,
    DOMAIN,
)
from .controller import BK215HybridController

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class BK215HybridControllerNumberEntityDescription(NumberEntityDescription):
    """Describe a controller number entity."""

    value_attr: str
    setter: str
    option_key: str
    requires_tower2: bool = False


NUMBER_DESCRIPTIONS: tuple[BK215HybridControllerNumberEntityDescription, ...] = (
    BK215HybridControllerNumberEntityDescription(
        key="charge_limit_start",
        name=None,
        translation_key="charge_limit_start",
        entity_category=EntityCategory.CONFIG,
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        mode=NumberMode.BOX,
        value_attr="charge_limit_start_value",
        setter="async_set_charge_limit_start",
        option_key="charge_limit_start",
    ),
    BK215HybridControllerNumberEntityDescription(
        key="charge_limit_start_2",
        name=None,
        translation_key="charge_limit_start_2",
        entity_category=EntityCategory.CONFIG,
        native_min_value=10,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement="%",
        mode=NumberMode.BOX,
        value_attr="charge_limit_start_2_value",
        setter="async_set_charge_limit_start_2",
        option_key="charge_limit_start_2",
        requires_tower2=True,
    ),
    BK215HybridControllerNumberEntityDescription(
        key="max_power_inverter",
        name=None,
        translation_key="max_power_inverter",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=1600,
        native_step=10,
        native_unit_of_measurement=UnitOfPower.WATT,
        mode=NumberMode.BOX,
        value_attr="max_power_inverter_value",
        setter="async_set_max_power_inverter",
        option_key="max_power_inverter",
    ),
    BK215HybridControllerNumberEntityDescription(
        key="min_power_inverter",
        name=None,
        translation_key="min_power_inverter",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=600,
        native_step=10,
        native_unit_of_measurement=UnitOfPower.WATT,
        mode=NumberMode.BOX,
        value_attr="min_power_inverter_value",
        setter="async_set_min_power_inverter",
        option_key="min_power_inverter",
    ),
    BK215HybridControllerNumberEntityDescription(
        key="offset",
        name=None,
        translation_key="offset",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-100,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=UnitOfPower.WATT,
        mode=NumberMode.BOX,
        value_attr="offset_value",
        setter="async_set_offset",
        option_key="offset",
    ),
    BK215HybridControllerNumberEntityDescription(
        key="deadband_min",
        name=None,
        translation_key="deadband_min",
        entity_category=EntityCategory.CONFIG,
        native_min_value=-150,
        native_max_value=0,
        native_step=1,
        native_unit_of_measurement=UnitOfPower.WATT,
        mode=NumberMode.BOX,
        value_attr="deadband_min_value",
        setter="async_set_deadband_min",
        option_key="deadband_min",
    ),
    BK215HybridControllerNumberEntityDescription(
        key="deadband_max",
        name=None,
        translation_key="deadband_max",
        entity_category=EntityCategory.CONFIG,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        native_unit_of_measurement=UnitOfPower.WATT,
        mode=NumberMode.BOX,
        value_attr="deadband_max_value",
        setter="async_set_deadband_max",
        option_key="deadband_max",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up controller number entities from a config entry."""
    controller: BK215HybridController = entry.runtime_data
    async_add_entities(
        BK215HybridControllerNumber(controller, entry, description)
        for description in NUMBER_DESCRIPTIONS
        if not description.requires_tower2 or controller.config.tower2_enabled
    )


class BK215HybridControllerNumber(NumberEntity):
    """Representation of one controller setting number."""

    _attr_has_entity_name = True
    entity_description: BK215HybridControllerNumberEntityDescription

    def __init__(
        self,
        controller: BK215HybridController,
        entry: ConfigEntry,
        description: BK215HybridControllerNumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
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
    def native_value(self) -> int:
        """Return the current number value."""
        value = getattr(self._controller, self.entity_description.value_attr)
        if value is None:
            match self.entity_description.option_key:
                case "charge_limit_start":
                    return int(DEFAULT_CHARGE_LIMIT_START)
                case "charge_limit_start_2":
                    return int(DEFAULT_CHARGE_LIMIT_START)
                case "max_power_inverter":
                    return int(DEFAULT_MAX_POWER_INVERTER)
                case "min_power_inverter":
                    return int(DEFAULT_MIN_POWER_INVERTER)
                case "offset":
                    return int(DEFAULT_OFFSET)
                case _:
                    return 0
        native_value = int(round(float(value)))
        if self.entity_description.option_key in {
            "max_power_inverter",
            "min_power_inverter",
        }:
            return min(native_value, int(round(self.native_max_value)))
        return native_value

    @property
    def native_max_value(self) -> float:
        """Return the dynamic max value for this number entity."""
        if self.entity_description.option_key == "max_power_inverter":
            return float(self._controller.max_power_inverter_limit_value)
        if self.entity_description.option_key == "min_power_inverter":
            return float(self._controller.min_power_inverter_limit_value)
        return float(self.entity_description.native_max_value or 0)

    async def async_set_native_value(self, value: float) -> None:
        """Update the runtime and persisted number value."""
        int_value = min(int(round(value)), int(round(self.native_max_value)))
        getattr(self._controller, self.entity_description.setter)(int_value)
        self.hass.config_entries.async_update_entry(
            self._entry,
            options={
                **dict(self._entry.options),
                self.entity_description.option_key: int_value,
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
