"""Runtime controller for the BK215 hybrid controller integration."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
import logging
import math
import time

from homeassistant.const import STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_call_later,
    async_track_state_change_event,
    async_track_time_interval,
)

from .const import (
    APSYSTEMS_HYSTERESIS,
    BOOST_POST_CYCLE_DELAY,
    DEFAULT_DT_CLAMP_THRESHOLD,
    DEFAULT_DT_DEFAULT,
    DEFAULT_INTEGRAL_LIMIT_PCT,
    DEYE_BOOST_HYSTERESIS,
    DEYE_PID_HYSTERESIS,
    MIN_APSYSTEMS_POWER_DUAL,
    MIN_APSYSTEMS_POWER_SINGLE,
    PID_POST_CYCLE_DELAY,
    UPDATE_DEBOUNCE,
)
from .models import ControllerConfig, InverterConfig, RuntimeState

_LOGGER = logging.getLogger(__name__)


class BK215HybridController:
    """Controller that replaces the script-based pipeline."""

    def __init__(self, hass: HomeAssistant, config: ControllerConfig) -> None:
        """Initialize the controller."""
        self.hass = hass
        self.config = config
        self.state = RuntimeState()
        self._unsubs: list[Callable[[], None]] = []
        self._state_listeners: list[Callable[[], None]] = []
        self._lock = asyncio.Lock()
        self._rerun_requested = False
        self._stopped = False
        self._debounce_unsub: Callable[[], None] | None = None

    async def async_start(self) -> None:
        """Start listeners and the periodic loop."""
        self.state.automatic_enabled = self.config.automatic_enabled
        self.state.boost_enabled = False
        self.state.inverter1_manual = self.config.inverter1_manual
        self.state.inverter2_manual = self.config.inverter2_manual
        self.state.inverter3_manual = self.config.inverter3_manual
        self.state.inverter4_manual = self.config.inverter4_manual
        if self.state.automatic_enabled:
            self.state.system_state = "inv_off"
            self.state.inverter1_helper = self._is_on(
                self.config.inverter1.switch_entity
            )
            self.state.inverter2_helper = self.config.inverter2.exists and self._is_on(
                self.config.inverter2.switch_entity
            )
            self.state.inverter3_helper = self.config.inverter3.exists and self._is_on(
                self.config.inverter3.switch_entity
            )
            self.state.inverter4_helper = self.config.inverter4.exists and self._is_on(
                self.config.inverter4.switch_entity
            )
        else:
            self.state.system_state = "inactive"
            self.state.inverter1_helper = False
            self.state.inverter2_helper = False
            self.state.inverter3_helper = False
            self.state.inverter4_helper = False

        tracked_entities = [
            self.config.power_sensor_entity,
            self.config.avg_battery_soc,
            self.config.inverter1.switch_entity,
        ]
        if self.config.inverter2.exists:
            tracked_entities.append(self.config.inverter2.switch_entity)
        if self.config.tower2_enabled:
            tracked_entities.append(self.config.avg_battery_soc_2)
        if self.config.inverter3.exists:
            tracked_entities.append(self.config.inverter3.switch_entity)
        if self.config.inverter4.exists:
            tracked_entities.append(self.config.inverter4.switch_entity)

        self._unsubs.append(
            async_track_state_change_event(
                self.hass,
                [entity for entity in tracked_entities if entity],
                self._handle_state_change,
            )
        )
        self._unsubs.append(
            async_track_time_interval(
                self.hass,
                self._handle_interval,
                self.config.interval,
            )
        )
        self._request_control_cycle()

    async def async_stop(self) -> None:
        """Stop listeners."""
        self._stopped = True
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        if self._debounce_unsub:
            self._debounce_unsub()
            self._debounce_unsub = None

    @callback
    def async_add_state_listener(
        self, listener: Callable[[], None]
    ) -> Callable[[], None]:
        """Register a listener for controller state updates."""
        self._state_listeners.append(listener)

        @callback
        def _remove_listener() -> None:
            if listener in self._state_listeners:
                self._state_listeners.remove(listener)

        return _remove_listener

    @callback
    def _notify_state_listeners(self) -> None:
        """Notify entities that controller state changed."""
        for listener in tuple(self._state_listeners):
            listener()

    @property
    def boost_active(self) -> bool:
        """Return whether boost mode is currently active."""
        return self.state.boost_enabled

    @property
    def inverter1_active(self) -> bool:
        """Return whether inverter 1 is currently active."""
        return self.state.inverter1_helper

    @property
    def inverter2_active(self) -> bool:
        """Return whether inverter 2 is currently active."""
        return self.config.inverter2.exists and self.state.inverter2_helper

    @property
    def inverter1_switch_on(self) -> bool:
        """Return the actual on/off state of the inverter 1 switch entity."""
        return self._is_on(self.config.inverter1.switch_entity)

    @property
    def possible_system_power(self) -> float:
        """Return the sum of rated power of all configured, non-manual inverters."""
        return (
            (
                self.config.inverter1.rated_power
                if not self.state.inverter1_manual
                else 0.0
            )
            + (
                self.config.inverter2.rated_power
                if self.config.inverter2.exists and not self.state.inverter2_manual
                else 0.0
            )
            + (
                self.config.inverter3.rated_power
                if self.config.inverter3.exists and not self.state.inverter3_manual
                else 0.0
            )
            + (
                self.config.inverter4.rated_power
                if self.config.inverter4.exists and not self.state.inverter4_manual
                else 0.0
            )
        )

    @property
    def inverter1_last_output(self) -> float:
        """Return the last written output value of inverter 1 control entity."""
        return self._get_float(self.config.inverter1.control_entity)

    @property
    def inverter2_last_output(self) -> float:
        """Return the last written output value of inverter 2 control entity."""
        return self._get_float(self.config.inverter2.control_entity)

    @property
    def inverter3_last_output(self) -> float:
        """Return the last written output value of inverter 3 control entity."""
        return self._get_float(self.config.inverter3.control_entity)

    @property
    def inverter4_last_output(self) -> float:
        """Return the last written output value of inverter 4 control entity."""
        return self._get_float(self.config.inverter4.control_entity)

    @property
    def inverter2_switch_on(self) -> bool:
        """Return the actual on/off state of the inverter 2 switch entity."""
        return self.config.inverter2.exists and self._is_on(
            self.config.inverter2.switch_entity
        )

    @property
    def has_inverter2(self) -> bool:
        """Return whether a second inverter is configured."""
        return self.config.inverter2.exists

    @property
    def has_inverter3(self) -> bool:
        """Return whether a third inverter (tower 2) is configured."""
        return self.config.inverter3.exists

    @property
    def has_inverter4(self) -> bool:
        """Return whether a fourth inverter (tower 2) is configured."""
        return self.config.inverter4.exists

    @property
    def inverter3_active(self) -> bool:
        """Return whether inverter 3 is currently active."""
        return self.config.inverter3.exists and self.state.inverter3_helper

    @property
    def inverter4_active(self) -> bool:
        """Return whether inverter 4 is currently active."""
        return self.config.inverter4.exists and self.state.inverter4_helper

    @property
    def inverter3_switch_on(self) -> bool:
        """Return the actual on/off state of the inverter 3 switch entity."""
        return self.config.inverter3.exists and self._is_on(
            self.config.inverter3.switch_entity
        )

    @property
    def inverter4_switch_on(self) -> bool:
        """Return the actual on/off state of the inverter 4 switch entity."""
        return self.config.inverter4.exists and self._is_on(
            self.config.inverter4.switch_entity
        )

    @property
    def inverter3_helper_enabled(self) -> bool:
        """Return the internal helper state for inverter 3."""
        return self.config.inverter3.exists and self.state.inverter3_helper

    @property
    def inverter4_helper_enabled(self) -> bool:
        """Return the internal helper state for inverter 4."""
        return self.config.inverter4.exists and self.state.inverter4_helper

    @property
    def inverter3_manual_enabled(self) -> bool:
        """Return whether inverter 3 is manually disabled."""
        return self.config.inverter3.exists and self.state.inverter3_manual

    @property
    def inverter4_manual_enabled(self) -> bool:
        """Return whether inverter 4 is manually disabled."""
        return self.config.inverter4.exists and self.state.inverter4_manual

    @property
    def inverter1_helper_enabled(self) -> bool:
        """Return the internal helper state for inverter 1."""
        return self.state.inverter1_helper

    @property
    def inverter2_helper_enabled(self) -> bool:
        """Return the internal helper state for inverter 2."""
        return self.config.inverter2.exists and self.state.inverter2_helper

    @property
    def inverter1_manual_enabled(self) -> bool:
        """Return whether inverter 1 is manually disabled."""
        return self.state.inverter1_manual

    @property
    def inverter2_manual_enabled(self) -> bool:
        """Return whether inverter 2 is manually disabled."""
        return self.config.inverter2.exists and self.state.inverter2_manual

    @property
    def automatic_enabled(self) -> bool:
        """Return whether automatic control is enabled."""
        return self.state.automatic_enabled

    @property
    def boost_enabled(self) -> bool:
        """Return the internal boost switch state."""
        return self.state.boost_enabled

    @property
    def deadband_min_value(self) -> float:
        """Return the active deadband minimum."""
        return self.config.deadband_min

    @property
    def deadband_max_value(self) -> float:
        """Return the active deadband maximum."""
        return self.config.deadband_max

    @property
    def offset_value(self) -> float:
        """Return the active offset value."""
        return self.config.offset

    @property
    def charge_limit_start_value(self) -> float:
        """Return the active charge start limit for tower 1."""
        return self.config.charge_limit_start

    @property
    def charge_limit_start_2_value(self) -> float:
        """Return the active charge start limit for tower 2."""
        return self.config.charge_limit_start_2

    @property
    def max_power_inverter_value(self) -> float:
        """Return the active maximum inverter power."""
        return min(self.config.max_power_inverter, self.max_power_inverter_limit_value)

    @property
    def max_power_inverter_limit_value(self) -> float:
        """Return the configured upper limit for the max power number entity."""
        return self.config.max_power_inverter_limit

    @property
    def min_power_inverter_value(self) -> float:
        """Return the active minimum inverter power."""
        return min(self.config.min_power_inverter, self.min_power_inverter_limit_value)

    @property
    def min_power_inverter_limit_value(self) -> float:
        """Return the configured upper limit for the min power number entity."""
        return self.config.min_power_inverter_limit

    @callback
    def async_set_boost_enabled(self, enabled: bool) -> None:
        """Set the internal boost switch state."""
        if enabled and not self.state.automatic_enabled:
            return
        self.state.boost_enabled = enabled
        self._notify_state_listeners()
        self._request_control_cycle()

    @callback
    def async_set_automatic_enabled(self, enabled: bool) -> None:
        """Enable or disable the automatic control loop."""
        self.state.automatic_enabled = enabled
        self._rerun_requested = False
        if not enabled:
            self.state.boost_enabled = False
            self.state.inverter1_helper = False
            self.state.inverter2_helper = False
            self.state.inverter3_helper = False
            self.state.inverter4_helper = False
            self.state.integral = 0.0
            self.state.last_target = 0.0
            self.state.last_error = 0.0
            self.state.deadband_filtered_error = 0.0
            self.state.deadband_state = "neutral"
            self.state.system_state = "inactive"
            self.state.hold_until = 0.0
        self._notify_state_listeners()
        if enabled:
            self._request_control_cycle()

    @callback
    def async_set_deadband_min(self, value: float) -> None:
        """Set the active deadband minimum."""
        self.config.deadband_min = value
        self._notify_state_listeners()
        self._request_control_cycle()

    @callback
    def async_set_deadband_max(self, value: float) -> None:
        """Set the active deadband maximum."""
        self.config.deadband_max = value
        self._notify_state_listeners()
        self._request_control_cycle()

    @callback
    def async_set_offset(self, value: float) -> None:
        """Set the active offset value."""
        self.config.offset = value
        self._notify_state_listeners()
        self._request_control_cycle()

    @callback
    def async_set_charge_limit_start(self, value: float) -> None:
        """Set the active charge start limit for tower 1."""
        self.config.charge_limit_start = value
        self._notify_state_listeners()
        self._request_control_cycle()

    @callback
    def async_set_charge_limit_start_2(self, value: float) -> None:
        """Set the active charge start limit for tower 2."""
        self.config.charge_limit_start_2 = value
        self._notify_state_listeners()
        self._request_control_cycle()

    @callback
    def async_set_max_power_inverter(self, value: float) -> None:
        """Set the active maximum inverter power."""
        self.config.max_power_inverter = value
        self._notify_state_listeners()
        self._request_control_cycle()

    @callback
    def async_set_min_power_inverter(self, value: float) -> None:
        """Set the active minimum inverter power."""
        self.config.min_power_inverter = value
        self._notify_state_listeners()
        self._request_control_cycle()

    @callback
    def async_set_inverter1_helper(self, enabled: bool) -> None:
        """Set the internal helper state for inverter 1."""
        self.state.inverter1_helper = enabled
        self._notify_state_listeners()
        self._request_control_cycle()

    @callback
    def async_set_inverter2_helper(self, enabled: bool) -> None:
        """Set the internal helper state for inverter 2."""
        if not self.config.inverter2.exists:
            return
        self.state.inverter2_helper = enabled
        self._notify_state_listeners()
        self._request_control_cycle()

    @callback
    def async_set_inverter1_manual(self, enabled: bool) -> None:
        """Enable or disable manual mode for inverter 1."""
        self.state.inverter1_manual = enabled
        self._notify_state_listeners()
        self._request_control_cycle()

    @callback
    def async_set_inverter2_manual(self, enabled: bool) -> None:
        """Enable or disable manual mode for inverter 2."""
        if not self.config.inverter2.exists:
            return
        self.state.inverter2_manual = enabled
        self._notify_state_listeners()
        self._request_control_cycle()

    @callback
    def async_set_inverter3_helper(self, enabled: bool) -> None:
        """Set the internal helper state for inverter 3."""
        if not self.config.inverter3.exists:
            return
        self.state.inverter3_helper = enabled
        self._notify_state_listeners()
        self._request_control_cycle()

    @callback
    def async_set_inverter4_helper(self, enabled: bool) -> None:
        """Set the internal helper state for inverter 4."""
        if not self.config.inverter4.exists:
            return
        self.state.inverter4_helper = enabled
        self._notify_state_listeners()
        self._request_control_cycle()

    @callback
    def async_set_inverter3_manual(self, enabled: bool) -> None:
        """Enable or disable manual mode for inverter 3."""
        if not self.config.inverter3.exists:
            return
        self.state.inverter3_manual = enabled
        self._notify_state_listeners()
        self._request_control_cycle()

    @callback
    def async_set_inverter4_manual(self, enabled: bool) -> None:
        """Enable or disable manual mode for inverter 4."""
        if not self.config.inverter4.exists:
            return
        self.state.inverter4_manual = enabled
        self._notify_state_listeners()
        self._request_control_cycle()

    @callback
    def _request_control_cycle(self) -> None:
        """Request a control cycle if automatic mode is enabled."""
        if not self.state.automatic_enabled:
            return
        self.hass.async_create_task(self._run_control_cycle())

    def _helper_state_for(self, inverter: InverterConfig) -> bool:
        """Return the internal helper state for an inverter."""
        if inverter is self.config.inverter1:
            return self.state.inverter1_helper
        if inverter is self.config.inverter2:
            return self.state.inverter2_helper
        if inverter is self.config.inverter3:
            return self.state.inverter3_helper
        return self.state.inverter4_helper

    def _is_manual(self, inverter: InverterConfig) -> bool:
        """Return whether the inverter is user-disabled via the manual switch."""
        if inverter is self.config.inverter1:
            return self.state.inverter1_manual
        if inverter is self.config.inverter2:
            return self.config.inverter2.exists and self.state.inverter2_manual
        if inverter is self.config.inverter3:
            return self.config.inverter3.exists and self.state.inverter3_manual
        return self.config.inverter4.exists and self.state.inverter4_manual

    def _set_helper_state_for(self, inverter: InverterConfig, enabled: bool) -> None:
        """Set the internal helper state for an inverter."""
        if inverter is self.config.inverter1:
            self.state.inverter1_helper = enabled
        elif inverter is self.config.inverter2 and self.config.inverter2.exists:
            self.state.inverter2_helper = enabled
        elif inverter is self.config.inverter3 and self.config.inverter3.exists:
            self.state.inverter3_helper = enabled
        elif inverter is self.config.inverter4 and self.config.inverter4.exists:
            self.state.inverter4_helper = enabled

    @callback
    def _handle_interval(self, _now: datetime) -> None:
        """Handle the periodic trigger."""
        if not self.state.automatic_enabled:
            return
        self._schedule_run(immediate=True)

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        """Handle relevant entity changes."""
        if not self.state.automatic_enabled:
            return
        self._schedule_run(immediate=False)

    @callback
    def _schedule_run(self, immediate: bool) -> None:
        """Debounce control cycle execution."""
        if immediate:
            self.hass.async_create_task(self._run_control_cycle())
            return

        if self._debounce_unsub:
            return

        self._debounce_unsub = async_call_later(
            self.hass,
            UPDATE_DEBOUNCE,
            self._debounced_run,
        )

    @callback
    def _debounced_run(self, _now: datetime) -> None:
        """Run a delayed control cycle."""
        self._debounce_unsub = None
        self.hass.async_create_task(self._run_control_cycle())

    async def _run_control_cycle(self) -> None:
        """Ensure only one control cycle runs at a time."""
        if self._stopped or not self.state.automatic_enabled:
            return
        if self._lock.locked():
            self._rerun_requested = True
            return

        async with self._lock:
            while True:
                self._rerun_requested = False
                await self._async_control_cycle()
                self._notify_state_listeners()
                if not self._rerun_requested:
                    break

    async def _async_control_cycle(self) -> None:
        """Execute one full control cycle."""
        started_any = await self._async_start_inverters_if_needed()
        if started_any:
            self.state.integral = 0.0
            self.state.last_error = 0.0
            self.state.last_target = 0.0

        previous_state = self.state.system_state
        self.state.system_state = self._calculate_system_state()

        if self.state.system_state != previous_state:
            await self._apply_protection_state(self.state.system_state)

        if self.state.system_state in {
            "soc_low",
            "inv_off",
            "failure",
            "both_manual",
        }:
            await self._ensure_safe_outputs()
            return

        boost_on = self.state.boost_enabled

        if not boost_on:
            self._update_deadband_state()

        if self.state.deadband_state == "neutral" and not boost_on:
            self.state.integral = round(self.state.integral * 0.98, 2)
            return

        if boost_on:
            await self._async_apply_boost()
            await asyncio.sleep(BOOST_POST_CYCLE_DELAY)
            return

        await self._async_apply_pid()
        await asyncio.sleep(PID_POST_CYCLE_DELAY)

    async def _async_start_inverters_if_needed(self) -> bool:
        """Start inverters when SOC is above the configured start limit."""
        started_any = False

        # Tower 1 — independent start check
        avg_soc = self._get_float(self.config.avg_battery_soc)
        limit_a = self._get_float(self.config.discharge_limit_a)
        limit_b = self._get_float(self.config.discharge_limit_b)
        if (
            avg_soc >= self.charge_limit_start_value
            and avg_soc > max(limit_a, limit_b) + self.config.buffer_soc
        ):
            started_any |= await self._async_start_single_inverter(
                self.config.inverter1
            )
            if self.config.inverter2.exists:
                started_any |= await self._async_start_single_inverter(
                    self.config.inverter2
                )

        # Tower 2 — independent start check
        if self.config.tower2_enabled:
            avg_soc_2 = self._get_float(self.config.avg_battery_soc_2)
            limit_a2 = self._get_float(self.config.discharge_limit_a_2)
            limit_b2 = self._get_float(self.config.discharge_limit_b_2)
            if (
                avg_soc_2 >= self.config.charge_limit_start_2
                and avg_soc_2 > max(limit_a2, limit_b2) + self.config.buffer_soc
            ):
                if self.config.inverter3.exists:
                    started_any |= await self._async_start_single_inverter(
                        self.config.inverter3
                    )
                if self.config.inverter4.exists:
                    started_any |= await self._async_start_single_inverter(
                        self.config.inverter4
                    )

        return started_any

    async def _async_start_single_inverter(self, inverter: InverterConfig) -> bool:
        """Start one inverter if needed."""
        if not inverter.exists or not inverter.switch_entity:
            return False
        if self._is_manual(inverter):
            return False
        if self._helper_state_for(inverter) and self._is_on(inverter.switch_entity):
            return False
        if not self._is_state_available(inverter.switch_entity):
            return False

        await self.hass.services.async_call(
            "switch",
            "turn_on",
            {"entity_id": inverter.switch_entity},
            blocking=True,
        )
        self._set_helper_state_for(inverter, True)
        return True

    def _manual_state_tower1(
        self,
        inv1_on: bool,
        inv1_manual: bool,
        inv2_exists: bool,
        inv2_on: bool,
        inv2_manual: bool,
    ) -> str | None:
        """Return the Tower 1 manual system state, or None if no manual state applies."""
        if not inv1_manual and not inv2_manual:
            return None
        if inv1_manual:
            if inv2_exists and inv2_manual:
                return "both_manual_tower1"
            if not inv2_exists:
                return "inv1_manual"
            return "inv1_manual_inv2_on" if inv2_on else "inv1_manual"
        return "inv2_manual_inv1_on" if inv1_on else "inv2_manual"

    def _manual_state_tower2(
        self,
        inv3_on: bool,
        inv3_exists: bool,
        inv3_manual: bool,
        inv4_exists: bool,
        inv4_on: bool,
        inv4_manual: bool,
    ) -> str | None:
        """Return the Tower 2 manual system state, or None if no manual state applies."""
        if not inv3_exists:
            return None
        if inv3_manual:
            if inv4_exists and inv4_manual:
                return "both_manual_tower2"
            if not inv4_exists:
                return "inv3_manual"
            return "inv3_manual_inv4_on" if inv4_on else "inv3_manual"
        if inv4_manual:
            return "inv4_manual_inv3_on" if inv3_on else "inv4_manual"
        return None

    def _calculate_system_state(self) -> str:
        """Calculate the current protection state."""
        # Tower 1 SOC check
        avg_soc = self._get_float(self.config.avg_battery_soc)
        limit_a = self._get_float(self.config.discharge_limit_a)
        limit_b = self._get_float(self.config.discharge_limit_b)
        soc1_low = avg_soc <= (max(limit_a, limit_b) + self.config.buffer_soc)

        # Tower 2 SOC check
        soc2_low = False
        if self.config.tower2_enabled:
            avg_soc_2 = self._get_float(self.config.avg_battery_soc_2)
            la2 = self._get_float(self.config.discharge_limit_a_2)
            lb2 = self._get_float(self.config.discharge_limit_b_2)
            soc2_low = avg_soc_2 <= (max(la2, lb2) + self.config.buffer_soc)

        if soc1_low and soc2_low:
            return "soc_low"
        if soc1_low:
            return "tower1_soc_low"
        if soc2_low:
            return "tower2_soc_low"

        inv1_manual = self._is_manual(self.config.inverter1)
        inv1_on = self.state.inverter1_helper
        inv2_exists = self.config.inverter2.exists
        inv2_manual = inv2_exists and self._is_manual(self.config.inverter2)
        inv2_on = self.state.inverter2_helper if inv2_exists else False

        inv3_exists = self.config.inverter3.exists
        inv3_manual = inv3_exists and self._is_manual(self.config.inverter3)
        inv3_on = self.state.inverter3_helper if inv3_exists else False
        inv4_exists = self.config.inverter4.exists
        inv4_manual = inv4_exists and self._is_manual(self.config.inverter4)
        inv4_on = self.state.inverter4_helper if inv4_exists else False

        # Both towers fully manual
        t1_all_manual = inv1_manual and (not inv2_exists or inv2_manual)
        t2_all_manual = inv3_exists and inv3_manual and (not inv4_exists or inv4_manual)
        if t1_all_manual and t2_all_manual:
            return "both_manual"

        # Per-tower manual states
        if t1_state := self._manual_state_tower1(
            inv1_on, inv1_manual, inv2_exists, inv2_on, inv2_manual
        ):
            return t1_state
        if t2_state := self._manual_state_tower2(
            inv3_on, inv3_exists, inv3_manual, inv4_exists, inv4_on, inv4_manual
        ):
            return t2_state

        # Normal operation states
        t1_on = inv1_on or inv2_on
        t2_on = inv3_on or inv4_on

        if not inv2_exists and not inv3_exists:
            return "inv_on" if inv1_on else "inv_off"

        if not inv3_exists:
            if not inv1_on and not inv2_on:
                return "inv_off"
            if inv1_on and inv2_on:
                return "inv_on"
            if inv1_on:
                return "inv1_on_inv2_failure"
            return "inv2_on_inv1_failure"

        t1_state = self._tower_state(inv1_on, inv2_on, inv2_exists)
        t2_state = self._tower_state(inv3_on, inv4_on, inv4_exists)

        if t1_state == "on" and t2_state == "on":
            return "inv_on"
        if t1_state == "off" and t2_state == "off":
            return "inv_off"
        if t1_state == "failure" or t2_state == "failure":
            return "failure"
        if t1_state == "partial_failure":
            return "inv1_on_inv2_failure" if inv1_on else "inv2_on_inv1_failure"
        if t2_state == "partial_failure":
            return "inv3_on_inv4_failure" if inv3_on else "inv4_on_inv3_failure"
        return "inv_on" if (t1_on or t2_on) else "inv_off"

    def _tower_state(self, wr_a_on: bool, wr_b_on: bool, has_wr_b: bool) -> str:
        """Return a simplified tower state string."""
        if not has_wr_b:
            return "on" if wr_a_on else "off"
        if wr_a_on and wr_b_on:
            return "on"
        if not wr_a_on and not wr_b_on:
            return "off"
        return "partial_failure"

    def _get_shutdown_targets(
        self, system_state: str
    ) -> list[tuple[InverterConfig, bool]]:
        """Return (inverter, only_if_running) pairs for a protection state.

        only_if_running=False: unconditional safety shutdown (e.g. soc_low).
        only_if_running=True:  shut down only if the controller started the inverter.
        """
        c = self.config
        all_inv = [
            i for i in (c.inverter1, c.inverter2, c.inverter3, c.inverter4) if i.exists
        ]
        t1_inv = [i for i in (c.inverter1, c.inverter2) if i.exists]
        t2_inv = [i for i in (c.inverter3, c.inverter4) if i.exists]
        match system_state:
            case "soc_low" | "failure":
                return [(i, False) for i in all_inv]
            case "inv_off":
                return [(i, True) for i in all_inv]
            case "tower1_soc_low":
                return [(i, True) for i in t1_inv]
            case "tower2_soc_low":
                return [(i, True) for i in t2_inv]
            case "inv1_on_inv2_failure":
                return [(c.inverter2, False)] if c.inverter2.exists else []
            case "inv2_on_inv1_failure":
                return [(c.inverter1, False)]
            case "inv1_manual" | "inv1_manual_inv2_on":
                return [(c.inverter1, True)]
            case "both_manual":
                return [(i, True) for i in all_inv]
            case "both_manual_tower1":
                return [(i, True) for i in t1_inv]
            case "inv2_manual" | "inv2_manual_inv1_on":
                return [(c.inverter2, True)] if c.inverter2.exists else []
            case "inv3_on_inv4_failure":
                return [(c.inverter4, False)] if c.inverter4.exists else []
            case "inv4_on_inv3_failure":
                return [(c.inverter3, False)] if c.inverter3.exists else []
            case "inv3_manual" | "inv3_manual_inv4_on":
                return [(c.inverter3, True)] if c.inverter3.exists else []
            case "both_manual_tower2":
                return [(i, True) for i in t2_inv]
            case "inv4_manual" | "inv4_manual_inv3_on":
                return [(c.inverter4, True)] if c.inverter4.exists else []
            case _:
                return []

    async def _apply_protection_state(self, system_state: str) -> None:
        """Apply side effects for protection-state transitions."""
        if system_state == "inv_on":
            return

        self.state.integral = 0.0
        self.state.last_error = 0.0
        self.state.last_target = 0.0

        for inverter, only_if_running in self._get_shutdown_targets(system_state):
            if not only_if_running or self._helper_state_for(inverter):
                await self._async_shutdown_inverter(inverter)

        self.state.boost_enabled = False

    async def _ensure_safe_outputs(self) -> None:
        """Ensure all inverter setpoints are at their safe fallback values."""
        if not self._is_manual(self.config.inverter1):
            await self._async_set_inverter_output(self.config.inverter1, 0.0)
        if self.config.inverter2.exists and not self._is_manual(self.config.inverter2):
            await self._async_set_inverter_output(self.config.inverter2, 0.0)
        if self.config.inverter3.exists and not self._is_manual(self.config.inverter3):
            await self._async_set_inverter_output(self.config.inverter3, 0.0)
        if self.config.inverter4.exists and not self._is_manual(self.config.inverter4):
            await self._async_set_inverter_output(self.config.inverter4, 0.0)

    async def _async_shutdown_inverter(self, inverter: InverterConfig) -> None:
        """Reset one inverter and switch it off."""
        await self._async_set_inverter_output(inverter, 0.0)
        if inverter.switch_entity and self._is_state_available(inverter.switch_entity):
            await self.hass.services.async_call(
                "switch",
                "turn_off",
                {"entity_id": inverter.switch_entity},
                blocking=True,
            )
        self._set_helper_state_for(inverter, False)

    def _update_deadband_state(self) -> None:
        """Update deadband state and filtered error."""
        grid_sensor_p = self._get_float(self.config.power_sensor_entity)
        self.state.last_grid_power = round(grid_sensor_p, 1)
        offset = self.config.offset
        grid_p = grid_sensor_p - offset

        state = self.state.deadband_state
        db_min = self.config.deadband_min
        db_max = self.config.deadband_max

        if state == "neutral":
            if grid_p > db_max:
                new_state = "import"
            elif grid_p < db_min:
                new_state = "export"
            else:
                new_state = "neutral"
        elif state == "import":
            new_state = "neutral" if grid_p < db_max else "import"
        elif state == "export":
            new_state = "neutral" if grid_p > db_min else "export"
        else:
            new_state = "neutral"

        if state == "neutral" and new_state == "import":
            self.state.integral = 0.0

        self.state.deadband_state = new_state

        if grid_p > db_max:
            filtered_error = -(grid_p - db_max)
        elif grid_p < db_min:
            filtered_error = -(grid_p - db_min)
        else:
            filtered_error = 0.0

        self.state.deadband_filtered_error = round(filtered_error, 2)

    async def _async_apply_boost(self) -> None:
        """Apply boost output distribution."""
        inv1_on = self.state.inverter1_helper
        inv2_on = self.state.inverter2_helper if self.config.inverter2.exists else False
        inv3_on = self.state.inverter3_helper if self.config.inverter3.exists else False
        inv4_on = self.state.inverter4_helper if self.config.inverter4.exists else False
        p_sum = (
            (self.config.inverter1.rated_power if inv1_on else 0.0)
            + (self.config.inverter2.rated_power if inv2_on else 0.0)
            + (self.config.inverter3.rated_power if inv3_on else 0.0)
            + (self.config.inverter4.rated_power if inv4_on else 0.0)
        )
        p_max_pow_inv = self.max_power_inverter_value
        boost_power = min(p_sum, p_max_pow_inv)
        if boost_power <= 0:
            return  # No active inverters — nothing to boost

        p1, p2, p3, p4 = self._split_target(
            boost_power, inv1_on, inv2_on, inv3_on, inv4_on
        )
        if not self._is_manual(self.config.inverter1):
            await self._async_set_inverter_output(
                self.config.inverter1, p1, deye_threshold=DEYE_BOOST_HYSTERESIS
            )
        if self.config.inverter2.exists and not self._is_manual(self.config.inverter2):
            await self._async_set_inverter_output(
                self.config.inverter2, p2, deye_threshold=DEYE_BOOST_HYSTERESIS
            )
        if self.config.inverter3.exists and not self._is_manual(self.config.inverter3):
            await self._async_set_inverter_output(
                self.config.inverter3, p3, deye_threshold=DEYE_BOOST_HYSTERESIS
            )
        if self.config.inverter4.exists and not self._is_manual(self.config.inverter4):
            await self._async_set_inverter_output(
                self.config.inverter4, p4, deye_threshold=DEYE_BOOST_HYSTERESIS
            )

        self.state.integral = 0.0
        self.state.last_error = 0.0
        self.state.deadband_filtered_error = 0.0
        self.state.last_target = boost_power

    async def _async_apply_pid(self) -> None:
        """Apply the PID control loop."""
        now_monotonic = time.monotonic()
        if self.state.last_run_monotonic == 0.0:
            dt = DEFAULT_DT_DEFAULT
        else:
            dt = now_monotonic - self.state.last_run_monotonic
            if dt > DEFAULT_DT_CLAMP_THRESHOLD:
                dt = DEFAULT_DT_DEFAULT
        self.state.last_run_monotonic = now_monotonic

        if now_monotonic < self.state.hold_until:
            return

        inv1_on = self.state.inverter1_helper
        inv2_on = self.state.inverter2_helper if self.config.inverter2.exists else False
        inv3_on = self.state.inverter3_helper if self.config.inverter3.exists else False
        inv4_on = self.state.inverter4_helper if self.config.inverter4.exists else False
        p_sum = (
            (self.config.inverter1.rated_power if inv1_on else 0.0)
            + (self.config.inverter2.rated_power if inv2_on else 0.0)
            + (self.config.inverter3.rated_power if inv3_on else 0.0)
            + (self.config.inverter4.rated_power if inv4_on else 0.0)
        )
        p_max_pow_inv = self.max_power_inverter_value
        p_max_pow = min(p_sum, p_max_pow_inv)
        if p_max_pow <= 0:
            return  # No active inverters — do not update state
        p_min_pow = self._calculate_min_power()

        inv1_current = self._current_inverter_power(self.config.inverter1, inv1_on)
        inv2_current = self._current_inverter_power(self.config.inverter2, inv2_on)
        inv3_current = self._current_inverter_power(self.config.inverter3, inv3_on)
        inv4_current = self._current_inverter_power(self.config.inverter4, inv4_on)
        total_curr = inv1_current + inv2_current + inv3_current + inv4_current
        error = self.state.deadband_filtered_error

        kp_err_factor = min(
            1.0, (abs(error) / max(self.config.kp_error_scale, 1.0)) ** 0.7
        )
        kp_eff = (
            self.config.kp_min
            + (self.config.kp_max - self.config.kp_min) * kp_err_factor
        )
        kaw = self.config.ki / kp_eff if kp_eff > 0 else 0.0
        integ_limit = p_max_pow * DEFAULT_INTEGRAL_LIMIT_PCT

        u_raw = kp_eff * error + self.state.integral
        u_sat = 0.0 if u_raw < 0 else min(u_raw, p_max_pow)
        raw_new_integral = (
            self.state.integral
            + self.config.ki * error * dt
            + kaw * (u_sat - u_raw) * dt
        )
        new_integral = max(-integ_limit, min(raw_new_integral, integ_limit))

        kd_err_factor = min(1.0, abs(error) / max(self.config.kd_error_scale, 1.0))
        kd_dt_factor = self.config.kd_dt_ref / dt if dt > 0 else 0.0
        kd_eff = self.config.kd * kd_err_factor * kd_dt_factor
        raw_derivative = (
            kd_eff * ((error - self.state.last_error) / dt) if dt > 0 else 0.0
        )
        derivative = max(-self.config.kd_max, min(raw_derivative, self.config.kd_max))

        p_offset = kp_eff * error + new_integral + derivative
        raw_target_p = total_curr - p_offset
        diff = raw_target_p - self.state.last_target
        delta_up = max(500.0, diff * 0.7) if diff > 0 else 0.0
        delta_down = max(200.0, (-diff) * 0.4) if diff < 0 else 0.0
        target_p_raw = self.state.last_target + sorted([-delta_down, diff, delta_up])[1]
        target_p = max(p_min_pow, min(target_p_raw, p_max_pow))

        p1, p2, p3, p4 = self._split_target(
            target_p, inv1_on, inv2_on, inv3_on, inv4_on
        )
        prev_inv1 = (
            self._get_float(self.config.inverter1.control_entity)
            if inv1_on and self.config.inverter1.control_entity
            else 0.0
        )
        prev_inv2 = (
            self._get_float(self.config.inverter2.control_entity)
            if inv2_on and self.config.inverter2.control_entity
            else 0.0
        )
        prev_inv3 = (
            self._get_float(self.config.inverter3.control_entity)
            if inv3_on and self.config.inverter3.control_entity
            else 0.0
        )
        prev_inv4 = (
            self._get_float(self.config.inverter4.control_entity)
            if inv4_on and self.config.inverter4.control_entity
            else 0.0
        )
        if not self._is_manual(self.config.inverter1):
            await self._async_set_inverter_output(
                self.config.inverter1, p1, deye_threshold=DEYE_PID_HYSTERESIS
            )
        if self.config.inverter2.exists and not self._is_manual(self.config.inverter2):
            await self._async_set_inverter_output(
                self.config.inverter2, p2, deye_threshold=DEYE_PID_HYSTERESIS
            )
        if self.config.inverter3.exists and not self._is_manual(self.config.inverter3):
            await self._async_set_inverter_output(
                self.config.inverter3, p3, deye_threshold=DEYE_PID_HYSTERESIS
            )
        if self.config.inverter4.exists and not self._is_manual(self.config.inverter4):
            await self._async_set_inverter_output(
                self.config.inverter4, p4, deye_threshold=DEYE_PID_HYSTERESIS
            )

        val_inv1 = self._target_control_value(self.config.inverter1, p1, inv1_on)
        val_inv2 = self._target_control_value(self.config.inverter2, p2, inv2_on)
        val_inv3 = self._target_control_value(self.config.inverter3, p3, inv3_on)
        val_inv4 = self._target_control_value(self.config.inverter4, p4, inv4_on)
        if (
            self._entering_run_mode(self.config.inverter1, prev_inv1, val_inv1, inv1_on)
            or self._entering_run_mode(
                self.config.inverter2, prev_inv2, val_inv2, inv2_on
            )
            or self._entering_run_mode(
                self.config.inverter3, prev_inv3, val_inv3, inv3_on
            )
            or self._entering_run_mode(
                self.config.inverter4, prev_inv4, val_inv4, inv4_on
            )
        ):
            self.state.hold_until = now_monotonic + self.config.hold_time
            self.state.integral = 0.0
            self.state.last_error = 0.0
            return

        self.state.integral = round(new_integral, 2)
        self.state.last_error = round(error, 2)
        self.state.last_target = round(target_p, 2)

    def _calculate_min_power(self) -> float:
        """Calculate the minimum controller power."""
        min_power = self.min_power_inverter_value
        inv2_exists = self.config.inverter2.exists
        if inv2_exists:
            if self.config.inverter1.is_deye and self.config.inverter2.is_deye:
                return max(min_power, 0.0)
            return max(min_power, MIN_APSYSTEMS_POWER_DUAL)
        if self.config.inverter1.is_apsystems:
            return max(min_power, MIN_APSYSTEMS_POWER_SINGLE)
        return max(min_power, 0.0)

    def _current_inverter_power(self, inverter: InverterConfig, is_on: bool) -> float:
        """Return the current inverter output in watts."""
        if not inverter.exists or not is_on or not inverter.control_entity:
            return 0.0
        if inverter.is_deye:
            return (
                self._get_float(inverter.control_entity) / 100.0 * inverter.rated_power
            )
        if inverter.power_sensor_entity:
            return self._get_float(
                inverter.power_sensor_entity, self._get_float(inverter.control_entity)
            )
        return self._get_float(inverter.control_entity)

    def _split_target(
        self,
        target_power: float,
        inv1_on: bool,
        inv2_on: bool,
        inv3_on: bool = False,
        inv4_on: bool = False,
    ) -> tuple[float, float, float, float]:
        """Split target power proportionally between all active inverters."""
        total = (
            (self.config.inverter1.rated_power if inv1_on else 0.0)
            + (self.config.inverter2.rated_power if inv2_on else 0.0)
            + (self.config.inverter3.rated_power if inv3_on else 0.0)
            + (self.config.inverter4.rated_power if inv4_on else 0.0)
        )
        if total <= 0.0:
            return 0.0, 0.0, 0.0, 0.0
        p1 = (
            round(target_power * self.config.inverter1.rated_power / total, 1)
            if inv1_on
            else 0.0
        )
        p2 = (
            round(target_power * self.config.inverter2.rated_power / total, 1)
            if inv2_on
            else 0.0
        )
        p3 = (
            round(target_power * self.config.inverter3.rated_power / total, 1)
            if inv3_on
            else 0.0
        )
        p4 = (
            round(target_power * self.config.inverter4.rated_power / total, 1)
            if inv4_on
            else 0.0
        )
        return p1, p2, p3, p4

    async def _async_set_inverter_output(
        self,
        inverter: InverterConfig,
        target_power: float,
        *,
        deye_threshold: float = DEYE_BOOST_HYSTERESIS,
    ) -> None:
        """Write one inverter control value."""
        if not inverter.exists or not inverter.control_entity:
            return

        value = self._target_control_value(
            inverter, target_power, self._helper_state_for(inverter)
        )
        current = self._get_float(inverter.control_entity)
        threshold = deye_threshold if inverter.is_deye else APSYSTEMS_HYSTERESIS
        if math.fabs(value - current) <= threshold:
            return

        await self.hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": inverter.control_entity, "value": value},
            blocking=True,
        )

    def _target_control_value(
        self, inverter: InverterConfig, target_power: float, is_on: bool
    ) -> float:
        """Translate target power to the inverter control value."""
        if not inverter.exists or not is_on:
            return 0.0 if inverter.is_deye else MIN_APSYSTEMS_POWER_SINGLE
        if inverter.is_deye:
            if inverter.rated_power <= 0:
                return 0.0
            return min(round(target_power / inverter.rated_power * 100, 1), 100.0)
        if inverter.rated_power >= MIN_APSYSTEMS_POWER_SINGLE:
            return max(
                min(int(target_power), int(inverter.rated_power)),
                MIN_APSYSTEMS_POWER_SINGLE,
            )
        return MIN_APSYSTEMS_POWER_SINGLE

    def _entering_run_mode(
        self,
        inverter: InverterConfig,
        previous_value: float,
        new_value: float,
        is_on: bool,
    ) -> bool:
        """Return whether an inverter has just been ramped from idle to active."""
        if not inverter.exists or not is_on:
            return False
        if inverter.is_deye:
            return previous_value == 0 and new_value != 0
        return previous_value <= MIN_APSYSTEMS_POWER_SINGLE < new_value

    def _get_float(self, entity_id: str | None, default: float = 0.0) -> float:
        """Read a float state with a fallback."""
        if not entity_id:
            return default
        state = self.hass.states.get(entity_id)
        if state is None:
            return default
        try:
            return float(state.state)
        except (TypeError, ValueError):
            return default

    def _is_on(self, entity_id: str | None) -> bool:
        """Return whether an entity is currently on."""
        if not entity_id:
            return False
        state = self.hass.states.get(entity_id)
        return state is not None and state.state == STATE_ON

    def _is_state_available(self, entity_id: str | None) -> bool:
        """Return whether an entity has an actionable state."""
        if not entity_id:
            return False
        state = self.hass.states.get(entity_id)
        return state is not None and state.state not in {
            "",
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
        }
