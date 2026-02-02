import logging
import pmpctrl.logging_config

from pmpctrl.control_data import ControlData
from time import sleep

class SessionControl:
    _logger: logging.Logger
    _control_data: ControlData
    _cycle_time: float

    def __init__(self, control_data: ControlData, cycle_time: float=0.01):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.setLevel(control_data.get_log_level())
        self._control_data = control_data
        self._cycle_time = cycle_time

    def _pump_on(self):
        if not self._control_data.event_pump_state_on.is_set():
            self._control_data.event_pump_turn_on.set()
            self._control_data.event_pump_turn_off.clear()

    def _pump_off(self):
        if self._control_data.event_pump_state_on.is_set():
            self._control_data.event_pump_turn_on.clear()
            self._control_data.event_pump_turn_off.set()

    def _open_valve(self):
        if self._control_data.event_valve_state_closed.is_set():
            self._control_data.event_valve_open.set()
            self._control_data.event_valve_close.clear()

    def _close_valve(self):
        if not self._control_data.event_valve_state_closed.is_set():
            self._control_data.event_valve_open.clear()
            self._control_data.event_valve_close.set()

    def run(self):
        try:
            while self._control_data.event_run.is_set():
                if self._control_data.event_session_on.is_set():
                    mode = self._control_data.get_mode()
                    # MODE_PRESSURE_HOLD
                    if mode == ControlData.MODE_PRESSURE_HOLD:
                        pass
                    # MODE_INTERVAL
                    elif mode == ControlData.MODE_INTERVAL:
                        interval = self._control_data.get_mode_interval_time()
                        base_pressure = self._control_data.get_pressure_target()
                        tolerance_plus = self._control_data.get_pressure_target_tolerance_plus()
                        while self._control_data.event_session_on.is_set() and self._control_data.get_mode() == ControlData.MODE_INTERVAL:
                            if interval >= 0:
                                sleep(self._cycle_time)
                                interval -= self._cycle_time
                                if base_pressure != self._control_data.get_pressure_target():
                                    base_pressure = self._control_data.get_pressure_target()
                                continue
                            else:
                                peak_target = self._control_data.get_mode_interval_peak_pressure()
                                self._control_data.set_pressure_target(peak_target)
                                self._control_data.set_pressure_target_tolerance_plus(0)
                                if self._control_data.get_pressure_actual() <= peak_target:
                                    break
                        # reset to original values
                        self._control_data.set_pressure_target(base_pressure)
                        self._control_data.set_pressure_target_tolerance_plus(tolerance_plus)
                    # MODE_PULSATING
                    elif mode == ControlData.MODE_PULSATING:
                        if not self._control_data.event_pump_state_on.is_set():
                            self._pump_on()
                        pump_time = self._control_data.get_mode_pulsating_pump_time()
                        release_time = self._control_data.get_mode_pulsating_release_time()
                        while self._control_data.event_session_on.is_set() and self._control_data.get_mode() == ControlData.MODE_PULSATING:
                            if pump_time >= 0:
                                sleep(self._cycle_time)
                                pump_time -= self._cycle_time
                                continue
                            else:
                                self._open_valve()
                                if release_time >= 0:
                                    sleep(self._cycle_time)
                                    release_time -= self._cycle_time
                                    continue
                                self._close_valve()
                                break
                    sleep(self._cycle_time)
                
            self._logger.info('run event is FALSE -> Exiting')
        except KeyboardInterrupt:
            self._logger.info('Program stopped by user through keyboard interrupt.')
            self._control_data.event_run.clear()