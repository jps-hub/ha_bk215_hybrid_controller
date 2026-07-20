"""Data models for the BK215 hybrid controller integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from .const import (
    DEFAULT_CHARGE_LIMIT_START,
    DEFAULT_MAX_POWER_INVERTER,
    DEFAULT_MAX_POWER_INVERTER_LIMIT,
    DEFAULT_MIN_POWER_INVERTER,
    DEFAULT_MIN_POWER_INVERTER_LIMIT,
    DEFAULT_OFFSET,
)


@dataclass(slots=True)
class InverterConfig:
    """Static inverter configuration."""

    inverter_type: str
    control_entity: str | None
    rated_power: float
    switch_entity: str | None
    power_sensor_entity: str | None

    @property
    def is_deye(self) -> bool:
        """Return whether the inverter is a Deye inverter."""
        return self.inverter_type == "Deye"

    @property
    def is_apsystems(self) -> bool:
        """Return whether the inverter is an APsystems inverter."""
        return self.inverter_type == "APsystems"

    @property
    def exists(self) -> bool:
        """Return whether the inverter is configured."""
        return bool(self.control_entity and self.switch_entity and self.rated_power > 0)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InverterConfig:
        """Create an inverter config from stored entry data."""
        return cls(
            inverter_type=str(data.get("inverter_type", "Deye")),
            control_entity=data.get("control_entity"),
            rated_power=float(data.get("rated_power", 0)),
            switch_entity=data.get("switch_entity"),
            power_sensor_entity=data.get("power_sensor_entity"),
        )

    def as_dict(self) -> dict[str, Any]:
        """Serialize the inverter config for storage."""
        return {
            "inverter_type": self.inverter_type,
            "control_entity": self.control_entity,
            "rated_power": self.rated_power,
            "switch_entity": self.switch_entity,
            "power_sensor_entity": self.power_sensor_entity,
        }


@dataclass(slots=True)
class ControllerConfig:
    """Full controller configuration."""

    automatic_enabled: bool
    avg_battery_soc: str
    charge_limit_start: float
    discharge_limit_a: str
    discharge_limit_b: str
    power_sensor_entity: str
    offset: float
    max_power_inverter: float
    max_power_inverter_limit: float
    min_power_inverter: float
    min_power_inverter_limit: float
    interval: timedelta
    deadband_min: float
    deadband_max: float
    buffer_soc: float
    hold_time: int
    kp_min: float
    kp_max: float
    kp_error_scale: float
    ki: float
    kd: float
    kd_error_scale: float
    kd_dt_ref: float
    kd_max: float
    inverter1: InverterConfig
    inverter2: InverterConfig
    tower2_enabled: bool = False
    avg_battery_soc_2: str = ""
    discharge_limit_a_2: str = ""
    discharge_limit_b_2: str = ""
    inverter3: InverterConfig = field(
        default_factory=lambda: InverterConfig.from_dict({})
    )
    inverter4: InverterConfig = field(
        default_factory=lambda: InverterConfig.from_dict({})
    )
    charge_limit_start_2: float = 10.0
    inverter1_manual: bool = False
    inverter2_manual: bool = False
    inverter3_manual: bool = False
    inverter4_manual: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ControllerConfig:
        """Create a controller config from stored entry data."""
        return cls(
            automatic_enabled=bool(data.get("automatic_enabled", False)),
            avg_battery_soc=str(data["avg_battery_soc"]),
            charge_limit_start=float(
                data.get("charge_limit_start", DEFAULT_CHARGE_LIMIT_START)
            ),
            discharge_limit_a=str(data["discharge_limit_a"]),
            discharge_limit_b=str(data["discharge_limit_b"]),
            power_sensor_entity=str(data["power_sensor_entity"]),
            offset=float(data.get("offset", DEFAULT_OFFSET)),
            max_power_inverter=float(
                data.get("max_power_inverter", DEFAULT_MAX_POWER_INVERTER)
            ),
            max_power_inverter_limit=float(
                data.get(
                    "max_power_inverter_limit",
                    DEFAULT_MAX_POWER_INVERTER_LIMIT,
                )
            ),
            min_power_inverter=float(
                data.get("min_power_inverter", DEFAULT_MIN_POWER_INVERTER)
            ),
            min_power_inverter_limit=float(
                data.get(
                    "min_power_inverter_limit",
                    DEFAULT_MIN_POWER_INVERTER_LIMIT,
                )
            ),
            interval=timedelta(seconds=int(data["interval_seconds"])),
            deadband_min=float(data["deadband_min"]),
            deadband_max=float(data["deadband_max"]),
            buffer_soc=float(data["buffer_soc"]),
            hold_time=int(data["hold_time"]),
            kp_min=float(data["kp_min"]),
            kp_max=float(data["kp_max"]),
            kp_error_scale=float(data["kp_error_scale"]),
            ki=float(data["ki"]),
            kd=float(data["kd"]),
            kd_error_scale=float(data["kd_error_scale"]),
            kd_dt_ref=float(data["kd_dt_ref"]),
            kd_max=float(data["kd_max"]),
            inverter1=InverterConfig.from_dict(data["inverter1"]),
            inverter2=InverterConfig.from_dict(data["inverter2"]),
            tower2_enabled=bool(data.get("tower2_enabled", False)),
            avg_battery_soc_2=str(data.get("avg_battery_soc_2", "")),
            discharge_limit_a_2=str(data.get("discharge_limit_a_2", "")),
            discharge_limit_b_2=str(data.get("discharge_limit_b_2", "")),
            inverter3=InverterConfig.from_dict(data.get("inverter3", {})),
            inverter4=InverterConfig.from_dict(data.get("inverter4", {})),
            charge_limit_start_2=float(
                data.get("charge_limit_start_2", DEFAULT_CHARGE_LIMIT_START)
            ),
            inverter1_manual=bool(data.get("inverter1_manual", False)),
            inverter2_manual=bool(data.get("inverter2_manual", False)),
            inverter3_manual=bool(data.get("inverter3_manual", False)),
            inverter4_manual=bool(data.get("inverter4_manual", False)),
        )


@dataclass(slots=True)
class RuntimeState:
    """In-memory controller state."""

    automatic_enabled: bool = False
    system_state: str = "inactive"
    deadband_state: str = "neutral"
    boost_enabled: bool = False
    inverter1_helper: bool = False
    inverter2_helper: bool = False
    inverter3_helper: bool = False
    inverter4_helper: bool = False
    inverter1_manual: bool = False
    inverter2_manual: bool = False
    inverter3_manual: bool = False
    inverter4_manual: bool = False
    integral: float = 0.0
    last_error: float = 0.0
    last_target: float = 0.0
    last_grid_power: float = 0.0
    deadband_filtered_error: float = 0.0
    hold_until: float = 0.0
    last_run_monotonic: float = 0.0
