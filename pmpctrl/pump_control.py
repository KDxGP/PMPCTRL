import logging
import pmpctrl.logging_config
import RPi.GPIO as GPIO

from pmpctrl.control_data import ControlData
from threading import Event
from time import sleep


class PumpControl:
    """
    A class that controls a pump connected via relai/MOSFET to a Raspberry Pi
    GPIO pin based on input events.

    Parameters:
        control_cata (ControlData):
            An instance of ControlData containing event objects for
            controlling the pump.
        pin_number (int):
            The GPIO pin number to which the relais/MOSFET is connected
            (using BCM numbering).
        cycle_time (float, optional):
            The time in seconds between checking for events.
            Defaults to 0.1 seconds.

    Methods:
        _power_on(): Sets the specified GPIO pin to HIGH, turning the pump on,
            and updates the control_data events accordingly.
        
        _power_off(): Sets the specified GPIO pin to LOW, turning the pump
            off, and updates the control_data events accordingly.
        
        run(): The main loop that runs as long as the 'event_run' in
            control_data is set. This method checks for events to turn the
            pump on or off, adjusts the pump state according to the events,
            and waits for the given cycle_time before checking again.
            On KeyboardInterrupt exception, the pump is turned off,
            the 'event_run' flag is cleared and GPIO resources are cleaned up.
    """
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
        self._cycle_time = cycle_time
        self._control_data = control_data
        self._pin_number = pin_number

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pin_number, GPIO.OUT)
        GPIO.output(self._pin_number, GPIO.LOW)


    def _power_on(self):
        """
        Sets the specified GPIO pin to HIGH, turning the pump on,
        and updates the internal control data events.

        Updates:
            - Sets the GPIO output at `_pin_number` to GPIO.HIGH.
            - Sets the `event_pump_state_on` in `_control_data`.
            - Clears the `event_pump_turn_on` in `_control_data`.

        Returns:
            None
        """
        self._logger.debug(f'setting pin {self._pin_number} to HIGH')
        GPIO.output(self._pin_number, GPIO.HIGH)
        self._control_data.event_pump_state_on.set()
        self._control_data.event_pump_turn_on.clear()


    def _power_off(self):
        """
        Sets the specified GPIO pin to LOW, turning the pump off,
        and updates the internal control data events.

        Updates:
            - Sets the GPIO output at `_pin_number` to GPIO.LOW.
            - Clears the `event_pump_state_on` in `_control_data`.
            - Clears the `event_pump_turn_off` in `_control_data`.

        Returns:
            None
        """
        self._logger.debug(f'setting pin {self._pin_number} to LOW')
        GPIO.output(self._pin_number, GPIO.LOW)
        self._control_data.event_pump_state_on.clear()
        self._control_data.event_pump_turn_off.clear()


    def run(self):
        """
        The main loop that runs until the `event_run` in `_control_data` is
        cleared.

        This method continuously monitors the following events:
            - If `event_pump_turn_on` is set and `event_pump_state_on`
              is not set, it calls `_power_on()`.
            - If `event_pump_turn_off` is set, it calls `_power_off()`.

        Sleeps for the duration specified in `_cycle_time` between each
        iteration.

        In case of a `KeyboardInterrupt`, the pump is turned off,
        the `event_run` flag is cleared, and GPIO resources are cleaned up.

        Returns:
            None
        """
        try:
            while self._control_data.event_run.is_set():
                if self._control_data.event_pump_turn_on.is_set():
                    self._logger.debug('EVENT_PUMP_TURN_ON was set')
                    if not self._control_data.event_pump_state_on.is_set():
                        self._logger.debug('EVENT_PUMP_STATE_ON is not set -> turning power ON')
                        self._power_on()
                elif self._control_data.event_pump_turn_off.is_set():
                    self._logger.debug('EVENT_PUMP_TURN_OFF is set -> Turning PUMP OFF')
                    self._power_off()
                sleep(self._cycle_time)
            self._logger.info('EVENT_RUN is NOT set -> Exiting')
        except KeyboardInterrupt:
            self._logger.info('Program stopped by user through keyboard interrupt.')
            self._control_data.event_run.clear()
        finally:
            self._power_off()
            GPIO.cleanup(self._pin_number)