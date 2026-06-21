"""Config flow for the BK215 hybrid controller integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    DEFAULT_BUFFER_SOC,
    DEFAULT_CHARGE_LIMIT_START,
    DEFAULT_DEADBAND_MAX,
    DEFAULT_DEADBAND_MIN,
    DEFAULT_HOLD_TIME,
    DEFAULT_INTERVAL_SECONDS,
    DEFAULT_KD,
    DEFAULT_KD_DT_REF,
    DEFAULT_KD_ERROR_SCALE,
    DEFAULT_KD_MAX,
    DEFAULT_KI,
    DEFAULT_KP_ERROR_SCALE,
    DEFAULT_KP_MAX,
    DEFAULT_KP_MIN,
    DEFAULT_MAX_POWER_INVERTER,
    DEFAULT_MAX_POWER_INVERTER_LIMIT,
    DEFAULT_MIN_POWER_INVERTER,
    DEFAULT_MIN_POWER_INVERTER_LIMIT,
    DEFAULT_NAME,
    DOMAIN,
)
from .models import InverterConfig

_LOGGER = logging.getLogger(__name__)


def _entity(domain: str) -> EntitySelector:
    return EntitySelector(EntitySelectorConfig(domain=domain))


INVERTER_TYPE_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=["Deye", "APsystems"],
        mode=SelectSelectorMode.DROPDOWN,
    )
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._data: dict[str, Any] = {}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> BK215HybridControllerOptionsFlow:
        """Return the options flow handler."""
        return BK215HybridControllerOptionsFlow(config_entry)

    @staticmethod
    def _merge_general_defaults(data: dict[str, Any]) -> dict[str, Any]:
        """Merge defaults for optional general settings."""
        return {
            "charge_limit_start": DEFAULT_CHARGE_LIMIT_START,
            "interval_seconds": DEFAULT_INTERVAL_SECONDS,
            "max_power_inverter": DEFAULT_MAX_POWER_INVERTER,
            "max_power_inverter_limit": DEFAULT_MAX_POWER_INVERTER_LIMIT,
            "min_power_inverter": DEFAULT_MIN_POWER_INVERTER,
            "min_power_inverter_limit": DEFAULT_MIN_POWER_INVERTER_LIMIT,
            "deadband_min": DEFAULT_DEADBAND_MIN,
            "deadband_max": DEFAULT_DEADBAND_MAX,
            "buffer_soc": DEFAULT_BUFFER_SOC,
            "hold_time": DEFAULT_HOLD_TIME,
            **data,
        }

    @staticmethod
    def _merge_pid_defaults(data: dict[str, Any]) -> dict[str, Any]:
        """Merge defaults for optional PID settings."""
        return {
            "kp_min": DEFAULT_KP_MIN,
            "kp_max": DEFAULT_KP_MAX,
            "kp_error_scale": DEFAULT_KP_ERROR_SCALE,
            "ki": DEFAULT_KI,
            "kd": DEFAULT_KD,
            "kd_error_scale": DEFAULT_KD_ERROR_SCALE,
            "kd_dt_ref": DEFAULT_KD_DT_REF,
            "kd_max": DEFAULT_KD_MAX,
            **data,
        }

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect general plant settings."""
        if user_input is not None:
            self._data.update(self._merge_general_defaults(user_input))
            return await self.async_step_inverter1()

        schema = vol.Schema(
            {
                vol.Required("avg_battery_soc"): _entity("sensor"),
                vol.Required("discharge_limit_a"): _entity("number"),
                vol.Required("discharge_limit_b"): _entity("sensor"),
                vol.Required("power_sensor_entity"): _entity("sensor"),
                vol.Optional(
                    "interval_seconds", default=DEFAULT_INTERVAL_SECONDS
                ): NumberSelector(
                    NumberSelectorConfig(min=1, max=30, step=1, unit_of_measurement="s")
                ),
                vol.Optional(
                    "deadband_min", default=DEFAULT_DEADBAND_MIN
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=-150, max=0, step=1, unit_of_measurement="W"
                    )
                ),
                vol.Optional(
                    "deadband_max", default=DEFAULT_DEADBAND_MAX
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0, max=100, step=1, unit_of_measurement="W"
                    )
                ),
                vol.Optional("buffer_soc", default=DEFAULT_BUFFER_SOC): NumberSelector(
                    NumberSelectorConfig(min=0, max=10, step=1, unit_of_measurement="%")
                ),
                vol.Optional(
                    "max_power_inverter_limit",
                    default=DEFAULT_MAX_POWER_INVERTER_LIMIT,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=100,
                        max=2500,
                        step=1,
                        unit_of_measurement="W",
                    )
                ),
                vol.Optional(
                    "min_power_inverter_limit",
                    default=DEFAULT_MIN_POWER_INVERTER_LIMIT,
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0,
                        max=2500,
                        step=1,
                        unit_of_measurement="W",
                    )
                ),
                vol.Optional("hold_time", default=DEFAULT_HOLD_TIME): NumberSelector(
                    NumberSelectorConfig(min=5, max=60, step=1, unit_of_measurement="s")
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_inverter1(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect inverter 1 settings."""
        if user_input is not None:
            self._data["inverter1"] = user_input
            return await self.async_step_inverter2()

        schema = vol.Schema(
            {
                vol.Required("inverter_type", default="Deye"): INVERTER_TYPE_SELECTOR,
                vol.Required("control_entity"): _entity("number"),
                vol.Required("rated_power"): NumberSelector(
                    NumberSelectorConfig(
                        min=300, max=2500, step=100, unit_of_measurement="W"
                    )
                ),
                vol.Required("switch_entity"): _entity("switch"),
                vol.Optional("power_sensor_entity"): _entity("sensor"),
            }
        )
        return self.async_show_form(step_id="inverter1", data_schema=schema)

    async def async_step_inverter2(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect optional inverter 2 settings."""
        if user_input is not None:
            self._data["inverter2"] = {
                "inverter_type": "Deye",
                "rated_power": 0,
                **user_input,
            }
            return await self.async_step_pid()

        schema = vol.Schema(
            {
                vol.Optional("inverter_type", default="Deye"): INVERTER_TYPE_SELECTOR,
                vol.Optional("control_entity"): _entity("number"),
                vol.Optional("rated_power", default=0): NumberSelector(
                    NumberSelectorConfig(
                        min=0, max=2500, step=100, unit_of_measurement="W"
                    )
                ),
                vol.Optional("switch_entity"): _entity("switch"),
                vol.Optional("power_sensor_entity"): _entity("sensor"),
            }
        )
        return self.async_show_form(step_id="inverter2", data_schema=schema)

    async def async_step_pid(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect PID settings and finish the flow."""
        if user_input is not None:
            self._data.update(self._merge_pid_defaults(user_input))

            try:
                data = {
                    "avg_battery_soc": self._data["avg_battery_soc"],
                    "charge_limit_start": float(self._data["charge_limit_start"]),
                    "discharge_limit_a": self._data["discharge_limit_a"],
                    "discharge_limit_b": self._data["discharge_limit_b"],
                    "power_sensor_entity": self._data["power_sensor_entity"],
                    "max_power_inverter": min(
                        float(self._data["max_power_inverter"]),
                        float(self._data["max_power_inverter_limit"]),
                    ),
                    "max_power_inverter_limit": float(
                        self._data["max_power_inverter_limit"]
                    ),
                    "min_power_inverter": min(
                        float(self._data["min_power_inverter"]),
                        float(self._data["min_power_inverter_limit"]),
                    ),
                    "min_power_inverter_limit": float(
                        self._data["min_power_inverter_limit"]
                    ),
                    "interval_seconds": int(self._data["interval_seconds"]),
                    "deadband_min": float(self._data["deadband_min"]),
                    "deadband_max": float(self._data["deadband_max"]),
                    "buffer_soc": float(self._data["buffer_soc"]),
                    "hold_time": int(self._data["hold_time"]),
                    "kp_min": float(self._data["kp_min"]),
                    "kp_max": float(self._data["kp_max"]),
                    "kp_error_scale": float(self._data["kp_error_scale"]),
                    "ki": float(self._data["ki"]),
                    "kd": float(self._data["kd"]),
                    "kd_error_scale": float(self._data["kd_error_scale"]),
                    "kd_dt_ref": float(self._data["kd_dt_ref"]),
                    "kd_max": float(self._data["kd_max"]),
                    "inverter1": InverterConfig.from_dict(
                        self._data["inverter1"]
                    ).as_dict(),
                    "inverter2": InverterConfig.from_dict(
                        self._data.get("inverter2", {})
                    ).as_dict(),
                }

                await self.async_set_unique_id(DEFAULT_NAME)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=DEFAULT_NAME, data=data)
            except (KeyError, TypeError, ValueError):
                _LOGGER.exception("Failed to create config entry from config flow data")
                return self.async_show_form(
                    step_id="pid",
                    data_schema=vol.Schema(
                        {
                            vol.Optional(
                                "kp_min", default=self._data["kp_min"]
                            ): NumberSelector(
                                NumberSelectorConfig(min=0.01, max=2.0, step=0.01)
                            ),
                            vol.Optional(
                                "kp_max", default=self._data["kp_max"]
                            ): NumberSelector(
                                NumberSelectorConfig(min=0.05, max=3.0, step=0.01)
                            ),
                            vol.Optional(
                                "kp_error_scale", default=self._data["kp_error_scale"]
                            ): NumberSelector(
                                NumberSelectorConfig(min=50, max=3000, step=10)
                            ),
                            vol.Optional(
                                "ki", default=self._data["ki"]
                            ): NumberSelector(
                                NumberSelectorConfig(min=0.001, max=1.0, step=0.001)
                            ),
                            vol.Optional(
                                "kd", default=self._data["kd"]
                            ): NumberSelector(
                                NumberSelectorConfig(min=0.0, max=2.0, step=0.01)
                            ),
                            vol.Optional(
                                "kd_error_scale", default=self._data["kd_error_scale"]
                            ): NumberSelector(
                                NumberSelectorConfig(min=0, max=3000, step=10)
                            ),
                            vol.Optional(
                                "kd_dt_ref", default=self._data["kd_dt_ref"]
                            ): NumberSelector(
                                NumberSelectorConfig(min=0.1, max=10.0, step=0.1)
                            ),
                            vol.Optional(
                                "kd_max", default=self._data["kd_max"]
                            ): NumberSelector(
                                NumberSelectorConfig(min=0.0, max=100.0, step=0.01)
                            ),
                        }
                    ),
                    errors={"base": "unknown"},
                )

        schema = vol.Schema(
            {
                vol.Optional("kp_min", default=DEFAULT_KP_MIN): NumberSelector(
                    NumberSelectorConfig(min=0.01, max=2.0, step=0.01)
                ),
                vol.Optional("kp_max", default=DEFAULT_KP_MAX): NumberSelector(
                    NumberSelectorConfig(min=0.05, max=3.0, step=0.01)
                ),
                vol.Optional(
                    "kp_error_scale", default=DEFAULT_KP_ERROR_SCALE
                ): NumberSelector(NumberSelectorConfig(min=50, max=3000, step=10)),
                vol.Optional("ki", default=DEFAULT_KI): NumberSelector(
                    NumberSelectorConfig(min=0.001, max=1.0, step=0.001)
                ),
                vol.Optional("kd", default=DEFAULT_KD): NumberSelector(
                    NumberSelectorConfig(min=0.0, max=2.0, step=0.01)
                ),
                vol.Optional(
                    "kd_error_scale", default=DEFAULT_KD_ERROR_SCALE
                ): NumberSelector(NumberSelectorConfig(min=0, max=3000, step=10)),
                vol.Optional("kd_dt_ref", default=DEFAULT_KD_DT_REF): NumberSelector(
                    NumberSelectorConfig(min=0.1, max=10.0, step=0.1)
                ),
                vol.Optional("kd_max", default=DEFAULT_KD_MAX): NumberSelector(
                    NumberSelectorConfig(min=0.0, max=100.0, step=0.01)
                ),
            }
        )
        return self.async_show_form(step_id="pid", data_schema=schema)


class BK215HybridControllerOptionsFlow(config_entries.OptionsFlowWithReload):
    """Handle options for the BK215 hybrid controller integration."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._options: dict[str, Any] = dict(config_entry.options)
        self._config: dict[str, Any] = {
            **dict(config_entry.data),
            **dict(config_entry.options),
        }

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage general options."""
        if user_input is not None:
            self._options.update(user_input)
            max_power_limit = float(
                user_input.get(
                    "max_power_inverter_limit",
                    self._config.get(
                        "max_power_inverter_limit",
                        DEFAULT_MAX_POWER_INVERTER_LIMIT,
                    ),
                )
            )
            current_max_power = float(
                self._options.get(
                    "max_power_inverter",
                    self._config.get("max_power_inverter", DEFAULT_MAX_POWER_INVERTER),
                )
            )
            self._options["max_power_inverter"] = min(
                current_max_power,
                max_power_limit,
            )
            min_power_limit = float(
                user_input.get(
                    "min_power_inverter_limit",
                    self._config.get(
                        "min_power_inverter_limit",
                        DEFAULT_MIN_POWER_INVERTER_LIMIT,
                    ),
                )
            )
            current_min_power = float(
                self._options.get(
                    "min_power_inverter",
                    self._config.get("min_power_inverter", DEFAULT_MIN_POWER_INVERTER),
                )
            )
            self._options["min_power_inverter"] = min(
                current_min_power,
                min_power_limit,
            )
            return await self.async_step_inverter1()

        schema = vol.Schema(
            {
                vol.Required(
                    "avg_battery_soc",
                    default=self._config["avg_battery_soc"],
                ): _entity("sensor"),
                vol.Required(
                    "discharge_limit_a",
                    default=self._config["discharge_limit_a"],
                ): _entity("number"),
                vol.Required(
                    "discharge_limit_b",
                    default=self._config["discharge_limit_b"],
                ): _entity("sensor"),
                vol.Required(
                    "power_sensor_entity",
                    default=self._config["power_sensor_entity"],
                ): _entity("sensor"),
                vol.Optional(
                    "interval_seconds",
                    default=int(
                        self._config.get("interval_seconds", DEFAULT_INTERVAL_SECONDS)
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(min=1, max=30, step=1, unit_of_measurement="s")
                ),
                vol.Optional(
                    "buffer_soc",
                    default=float(self._config.get("buffer_soc", DEFAULT_BUFFER_SOC)),
                ): NumberSelector(
                    NumberSelectorConfig(min=0, max=10, step=1, unit_of_measurement="%")
                ),
                vol.Optional(
                    "max_power_inverter_limit",
                    default=float(
                        self._config.get(
                            "max_power_inverter_limit",
                            DEFAULT_MAX_POWER_INVERTER_LIMIT,
                        )
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=100,
                        max=2500,
                        step=10,
                        unit_of_measurement="W",
                    )
                ),
                vol.Optional(
                    "min_power_inverter_limit",
                    default=float(
                        self._config.get(
                            "min_power_inverter_limit",
                            DEFAULT_MIN_POWER_INVERTER_LIMIT,
                        )
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=0,
                        max=2500,
                        step=1,
                        unit_of_measurement="W",
                    )
                ),
                vol.Optional(
                    "hold_time",
                    default=int(self._config.get("hold_time", DEFAULT_HOLD_TIME)),
                ): NumberSelector(
                    NumberSelectorConfig(min=5, max=60, step=1, unit_of_measurement="s")
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

    async def async_step_inverter1(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage inverter 1 options."""
        if user_input is not None:
            self._options["inverter1"] = user_input
            return await self.async_step_inverter2()

        inverter1 = InverterConfig.from_dict(self._config["inverter1"]).as_dict()
        schema = self.add_suggested_values_to_schema(
            vol.Schema(
                {
                    vol.Required("inverter_type"): INVERTER_TYPE_SELECTOR,
                    vol.Required("control_entity"): _entity("number"),
                    vol.Required("rated_power"): NumberSelector(
                        NumberSelectorConfig(
                            min=300, max=2500, step=100, unit_of_measurement="W"
                        )
                    ),
                    vol.Required("switch_entity"): _entity("switch"),
                    vol.Optional("power_sensor_entity"): _entity("sensor"),
                }
            ),
            {key: value for key, value in inverter1.items() if value is not None},
        )
        return self.async_show_form(step_id="inverter1", data_schema=schema)

    async def async_step_inverter2(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage inverter 2 options."""
        if user_input is not None:
            self._options["inverter2"] = {
                "inverter_type": "Deye",
                "rated_power": 0,
                **user_input,
            }
            return await self.async_step_pid()

        inverter2 = InverterConfig.from_dict(
            self._config.get("inverter2", {})
        ).as_dict()
        schema = self.add_suggested_values_to_schema(
            vol.Schema(
                {
                    vol.Optional("inverter_type"): INVERTER_TYPE_SELECTOR,
                    vol.Optional("control_entity"): _entity("number"),
                    vol.Optional("rated_power"): NumberSelector(
                        NumberSelectorConfig(
                            min=0, max=2500, step=100, unit_of_measurement="W"
                        )
                    ),
                    vol.Optional("switch_entity"): _entity("switch"),
                    vol.Optional("power_sensor_entity"): _entity("sensor"),
                }
            ),
            {key: value for key, value in inverter2.items() if value is not None},
        )
        return self.async_show_form(step_id="inverter2", data_schema=schema)

    async def async_step_pid(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage PID options."""
        if user_input is not None:
            self._options.update(user_input)
            return self.async_create_entry(title="", data=self._options)

        schema = vol.Schema(
            {
                vol.Optional(
                    "kp_min",
                    default=float(self._config.get("kp_min", DEFAULT_KP_MIN)),
                ): NumberSelector(NumberSelectorConfig(min=0.01, max=2.0, step=0.01)),
                vol.Optional(
                    "kp_max",
                    default=float(self._config.get("kp_max", DEFAULT_KP_MAX)),
                ): NumberSelector(NumberSelectorConfig(min=0.05, max=3.0, step=0.01)),
                vol.Optional(
                    "kp_error_scale",
                    default=float(
                        self._config.get("kp_error_scale", DEFAULT_KP_ERROR_SCALE)
                    ),
                ): NumberSelector(NumberSelectorConfig(min=50, max=3000, step=10)),
                vol.Optional(
                    "ki",
                    default=float(self._config.get("ki", DEFAULT_KI)),
                ): NumberSelector(NumberSelectorConfig(min=0.001, max=1.0, step=0.001)),
                vol.Optional(
                    "kd",
                    default=float(self._config.get("kd", DEFAULT_KD)),
                ): NumberSelector(NumberSelectorConfig(min=0.0, max=2.0, step=0.01)),
                vol.Optional(
                    "kd_error_scale",
                    default=float(
                        self._config.get("kd_error_scale", DEFAULT_KD_ERROR_SCALE)
                    ),
                ): NumberSelector(NumberSelectorConfig(min=0, max=3000, step=10)),
                vol.Optional(
                    "kd_dt_ref",
                    default=float(self._config.get("kd_dt_ref", DEFAULT_KD_DT_REF)),
                ): NumberSelector(NumberSelectorConfig(min=0.1, max=10.0, step=0.1)),
                vol.Optional(
                    "kd_max",
                    default=float(self._config.get("kd_max", DEFAULT_KD_MAX)),
                ): NumberSelector(NumberSelectorConfig(min=0.0, max=100.0, step=0.01)),
            }
        )
        return self.async_show_form(step_id="pid", data_schema=schema)
