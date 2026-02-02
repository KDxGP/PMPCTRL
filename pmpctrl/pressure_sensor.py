import logging
import pmpctrl.logging_config

from bmp280 import BMP280
from pmpctrl.control_data import ControlData
from smbus2 import SMBus
from statistics import fmean
from time import sleep

class PressureSensor:
    _logger: logging.Logger
    _control_data: ControlData
    _cycle_time: float
    _bus_nr: int
    _bus: SMBus
    _i2c_addr: int
    _bmp280: BMP280

    def __init__(self,
                 control_data: ControlData,
                 cycle_time: float=0.01,
                 smbus_nr: int=1,
                 i2c_addr: int=0x76):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.setLevel(control_data.get_log_level())
        self._control_data = control_data
        self._cycle_time = cycle_time
        self._bus_nr = smbus_nr
        self._i2c_addr = i2c_addr
        self._bmp280_setup()

        
    def _bmp280_setup(self):
        try:
            self._bus = SMBus(self._bus_nr)
            self._bmp280 = BMP280(i2c_dev=self._bus, i2c_addr=self._i2c_addr)
            self._bmp280.setup(mode="forced")
        except Exception as e:
            self._logger.error(f'Failed to setup I2C sensor: {e}')
            raise


    def _read(self, retries_max: int=3) -> float:
        for retry in range(retries_max):
            try:
                pressure = self._bmp280.get_pressure()
                if pressure is not None:
                    self._logger.debug(f'pressure reading: {self._control_data.get_pressure_actual()}')
                    self._control_data.set_pressure_actual(pressure)
                    return pressure
            except Exception as e:
                self._logger.warning(f'Could not read pressure, re-initalizing I2C, retry={retry}')
                self._bus.close()
                self._bmp280.setup()
                sleep(1)
                continue
        self._logger.error('Retries for reading pressure exceeded -> STOPPING')
        self._control_data.event_session_on.clear()
        self._control_data.event_run.clear()
        self._control_data.event_error.set()
        return None


    def _set_setpoint(self,
                      sample_count: int=10,
                      wait_between_samples: float=1.0):
        self._logger.info('Getting pressure zero point...')
        samples = []
        for i in range(0, sample_count):
            sample = self._read()
            if sample is not None:
                samples.append(sample)
                self._logger.debug(f'sample {i} = {sample}')
            sleep(wait_between_samples)
        
        zero_point = fmean(samples)
        self._logger.info(f'New zero point is  {zero_point}')
        self._control_data.set_pressure_setpoint(zero_point)


    def run(self):
        try:
            while self._control_data.event_run.is_set():
                if self._control_data.event_set_setpoint.is_set():
                    self._set_setpoint()
                    self._control_data.event_set_setpoint.clear()
                else:
                    self._read()
                    sleep(self._cycle_time)
            self._logger.info('run event is FALSE -> Exiting')
        except KeyboardInterrupt:
            self._logger.info('Program stopped by user through keyboard interrupt.')
            self._control_data.event_run.clear()
        finally:
            self._bus.close()