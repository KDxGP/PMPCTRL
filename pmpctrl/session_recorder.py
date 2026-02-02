import logging
import pmpctrl.logging_config
import pandas as pd
import datetime

from pmpctrl.control_data import ControlData
from time import sleep

class SessionRecoder:
    _logger: logging.Logger
    _cycle_time: float

    def __init__(self, control_data: ControlData, cycle_time=1.0):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.setLevel(control_data.get_log_level())
        self._control_data = control_data
        self._cycle_time = cycle_time
        
        self._session_data = []
        self._column_names = ['timestamp', 'pressure_mbar', 'setpoint_mbar', 'pressure_target_mbar']

    def run(self) -> None:
        while self._control_data.event_run.is_set():
            while self._control_data.event_session_on.is_set():
                timestamp = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
                pressure = self._control_data.get_pressure_actual()
                setpoint = self._control_data.get_pressure_setpoint()
                pressure_target = self._control_data.get_pressure_target()
                self._session_data.append([timestamp, pressure, setpoint, pressure_target])
        self._logger.info('run event and session is FALSE -> Exiting')