import logging
import pmpctrl.logging_config
import RPi.GPIO as GPIO

from pmpctrl.control_data import ControlData
from time import sleep

class ValveControl:
    _logger: logging.Logger
    _control_data: ControlData
    _cycle_time: float
    _pin_number: int

    
    def __init__(self,
                 control_data: ControlData,
                 pin_number: int,
                 cycle_time: float=0.1):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.setLevel(control_data.get_log_level())
        self._control_data = control_data
        self._cycle_time = cycle_time
        self._pin_number = pin_number
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin_number, GPIO.OUT)
        GPIO.output(self._pin_number, GPIO.LOW)
        
   
    def _open_valve(self) -> None:
        self._logger.info('openeing valve')
        GPIO.output(self._pin_number, GPIO.HIGH)
        self._control_data.event_valve_state_closed.clear()
        self._control_data.event_valve_open.clear()

    
    def _close_valve(self) -> None:
        self._logger.info('closing valve')
        GPIO.output(self._pin_number, GPIO.LOW)
        self._control_data.event_valve_state_closed.set()
        self._control_data.event_valve_close.clear()


    def run(self) -> None:
        try:
            while self._control_data.event_run.is_set():
                if self._control_data.event_valve_open.is_set():
                    self._logger.debug('EVENT_VALVE_OPEN is set -> openeing valve')
                    self._open_valve()
                if self._control_data.event_valve_close.is_set():
                    self._logger.debug('EVENT_VALVE_CLOSE is set -> closing valve')
                    self._close_valve()
                sleep(self._cycle_time)
            self._logger.info('run event is FALSE -> Exiting')
        except KeyboardInterrupt:
            self._logger.info('Program stopped by user through keyboard interrupt.')
            self._control_data.event_run.clear()
        finally:
            self._close_valve()
            GPIO.cleanup(self._pin_number)