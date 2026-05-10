from statistics import fmean
from statistics import stdev
from time import sleep

import logging

from pmpctrl.control_data import ControlData

import pmpctrl.logging_config


class AutoSetpoint:
    _logger: logging.Logger
    _cycle_time: float


    def __init__(self, control_data: ControlData, cycle_time: float=0.5):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.setLevel(control_data.get_log_level())
        self._control_data = control_data
        self._cycle_time = cycle_time
        self._pressure_readings = []


    def run(self):
        try:
            while self._control_data.event_run.is_set():
                if self._control_data.event_session_on.is_set():
                    self._control_data.event_auto_setpoint.clear()
                elif (
                    not self._control_data.event_session_on.is_set()
                    and self._control_data.event_auto_setpoint.is_set()
                ):
                    self._logger.debug("performing auto setpoint procedure")
                    if len(self._pressure_readings) >= 240:
                        self._pressure_readings.pop(0)
                    pressure_actual = self._control_data.get_pressure_actual()
                    if pressure_actual > 0:
                        self._pressure_readings.append(pressure_actual)
                    if len(self._pressure_readings) > 1:
                        setpoint = fmean(self._pressure_readings)
                        self._control_data.set_pressure_setpoint(setpoint)
                        log_msg = (
                            f"sample count: {len(self._pressure_readings)} ->"
                            f" new setpoint: {setpoint}, stdev: {stdev(self._pressure_readings)}"
                        )
                        self._logger.debug(log_msg)
                sleep(self._cycle_time)
            self._logger.info('run event is FALSE -> Exiting')

        except KeyboardInterrupt:
            self._logger.info('Program stopped by user through keyboard interrupt.')
            self._control_data.event_run.clear()
