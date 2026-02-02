import logging
import pmpctrl.logging_config

from pmpctrl.control_data import ControlData
from time import sleep

class PressureControl:
    _logger: logging.Logger
    _control_data: ControlData
    _cycle_time: float

    def __init__(self, control_data: ControlData, cycle_time: float=0.1):
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


    def _pressure_hold(self):
        pressure_is = self._control_data.get_pressure_actual()
        pressure_target = self._control_data.get_pressure_target()
        pressure_tolerance_minus = self._control_data.get_pressure_target_tolerance_minus()
        pressure_tolerance_plus = self._control_data.get_pressure_target_tolerance_plus()

        self._logger.debug(f'pressure is {pressure_is} and should be {pressure_target} +{pressure_tolerance_plus}/-{pressure_tolerance_minus}')

        if pressure_is < pressure_target - pressure_tolerance_minus:
            self._logger.debug('Pressure to LOW')
            if self._control_data.event_pump_state_on.is_set():
                self._logger.debug(f'Pressure to LOW and pump is ON -> signaling to turn power OFF')
                self._control_data.event_pump_turn_on.clear()
                self._control_data.event_pump_turn_off.set()
            if self._control_data.event_valve_state_closed.is_set():
                self._logger.debug(f'Pressure to LOW and valve is CLOSED -> signaling to OPEN valve')
                self._control_data.event_valve_close.clear()
                self._control_data.event_valve_open.set()
        elif pressure_is > pressure_target + pressure_tolerance_plus:
            self._logger.debug('Pressure to HIGH')
            if not self._control_data.event_pump_state_on.is_set():
                self._logger.debug('Pressure to HIGH and pump is OFF -> signaling to turn power ON')
                self._control_data.event_pump_turn_on.set()
                self._control_data.event_pump_turn_off.clear()
            if not self._control_data.event_valve_state_closed.is_set():
                self._logger.debug('Pressure to HIGH and valve is OPEN -> signaling to CLOSE valve')
                self._control_data.event_valve_open.clear()
                self._control_data.event_valve_close.set()
        else:
            self._logger.debug('Pressure is GOOD')
            if self._control_data.event_pump_state_on.is_set():
                self._logger.debug('Pressure is GOOD and pump is ON -> signaling to turn power OFF')
                self._control_data.event_pump_turn_on.clear()
                self._control_data.event_pump_turn_off.set()
            if not self._control_data.event_valve_state_closed.is_set():
                self._logger.debug('Pressure is GOOD and valve is OPEN -> signaling to CLOSE valve')
                self._control_data.event_valve_open.clear()
                self._control_data.event_valve_close.set()
        
    def run(self):
        try:
            while self._control_data.event_run.is_set():
                if self._control_data.event_session_on.is_set() and self._control_data.get_pressure_control():
                    self._pressure_hold()
                sleep(self._cycle_time)
            self._logger.info('run event is FALSE -> Exiting')
        except KeyboardInterrupt:
            self._logger.info('Program stopped by user through keyboard interrupt.')
            self._control_data.event_run.clear()