#!/usr/bin/env python3
import argparse
import configparser
import logging
import pmpctrl.logging_config
import signal
import sys
import uvicorn

from functools import partial
from pmpctrl.auto_setpoint import AutoSetpoint
from pmpctrl.control_data import ControlData
from pmpctrl.pmpctrl_api import PmpctrlAPI
from pmpctrl.pressure_control import PressureControl
from pmpctrl.pressure_sensor import PressureSensor
from pmpctrl.pump_control import PumpControl
from pmpctrl.session_control import SessionControl
from pmpctrl.valve_control import ValveControl
from threading import Thread
from time import sleep

class Settings:
    # logging
    LOG_LEVEL = logging.WARNING
    # api
    API_PORT = 8000
    # pressure_control
    PRESSURE_CONTROL_CYCLE_TIME = 0.01
    PRESSURE_CONTROL_TOLERANCE_PLUS = 0.0
    PRESSURE_CONTROL_TOLERANCE_MINUS = 10.0
    PRESSURE_CONTROL_SETPOINT = 962.9274
    PRESSURE_CONTROL_PRESSURE_MAX = 1084.0
    PRESSURE_CONTROL_PRESSURE_MIN = 450.0
    # pressure_sensor
    PRESSURE_SENSOR_CYCLE_TIME = 0.01
    PRESSURE_SENSOR_BUS_NR = 1
    PRESSURE_SENSOR_I2C_ADR = 0x76
    # pump_control
    PUMP_CONTROL_CYCLE_TIME = 0.5
    PUMP_CONTROL_PIN_NUMBER = 24
    # valve_coontrol
    VALVE_CONTROL_CYCLE_TIME = 0.1
    VALVE_CONTROL_PIN_NUMBER = 23
    # mode_hold
    MODE_HOLD_PRESSURE_TARGET = 875.0
    # mode_interval
    MODE_INTERVAL_PEAK_PRESSURE = 790.0
    MODE_INTERVAL_INTERVAL_TIME = 20.0
    # mode_pulsating
    MODE_PULSATING_PUMP_TIME = 2.7
    MODE_PULSATING_RELEASE_TIME = 1.7


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='config file', required=True)
    return parser.parse_args()


def parse_config(config_file: str) -> Settings:
    logger = logging.getLogger(__name__)
    settings = Settings
    config = configparser.ConfigParser()
    config.read(config_file)

    try:
        # parse all parameters
        ini_logging_log_level = config.get('logging', 'log_level')
        ini_api_port = config.getint('api', 'port')
        ini_pressure_control_cycle_time = config.getfloat('pressure_control', 'cycle_time')
        ini_pressure_control_tolerance_plus = config.getfloat('pressure_control', 'tolerance_plus')
        ini_pressure_control_tolerance_minus = config.getfloat('pressure_control', 'tolerance_minus')
        ini_pressure_control_setpoint = config.getfloat('pressure_control', 'setpoint')
        ini_pressure_control_pressure_max = config.getfloat('pressure_control', 'pressure_max')
        ini_pressure_control_pressure_min = config.getfloat('pressure_control', 'pressure_min')
        ini_pressure_sensor_cycle_time = config.getfloat('pressure_sensor', 'cycle_time')
        ini_pressure_sensor_bus_nr = config.getint('pressure_sensor', 'smbus_nr')
        ini_pressure_sensor_i2c_adr = int(config.get('pressure_sensor', 'i2c_address'), 0)
        ini_pump_control_cycle_time = config.getfloat('pump_control', 'cycle_time')
        ini_pump_control_pin_number = config.getint('pump_control', 'pin_number')
        ini_valve_control_cycle_time = config.getfloat('valve_control', 'cycle_time')
        ini_valve_control_pin_number = config.getint('valve_control', 'pin_number')
        ini_mode_hold_pressure_target = config.getfloat('mode_hold', 'pressure_target')
        ini_mode_interval_peak_pressure = config.getfloat('mode_interval', 'peak_pressure')
        ini_mode_interval_interval_time = config.getfloat('mode_interval', 'interval_time')
        ini_mode_pulsating_pump_time = config.getfloat('mode_pulsating', 'pump_time')
        ini_mode_pulsating_release_time = config.getfloat('mode_pulsating', 'release_time')
    

        # [logging]
        # check if in loglevels
        logging_log_levels = logging.getLevelNamesMapping().items()
        logging_log_level_false = True
        for key, value in logging_log_levels:
            if ini_logging_log_level in key:
                settings.log_level = value
                logging_log_level_false = False
        if logging_log_level_false:
            logger.error(f"config.ini: {ini_logging_log_level} is not a valid log level, using default value {settings.LOG_LEVEL}")
        # [api]
        # check if port is in range
        if 1024 < ini_api_port <= 65535:
            settings.API_PORT = ini_api_port
        else:
            logger.error(f"config.ini: API port not in range (1025-65535), using default value {settings.API_PORT}")

        # [pressure_control]
        # cycle_time
        # TODO
        settings.PRESSURE_CONTROL_CYCLE_TIME = ini_pressure_control_cycle_time

        # tolerance_plus
        # check if in range
        if 0.0 <= ini_pressure_control_tolerance_plus <= 50.0:
            settings.PRESSURE_CONTROL_TOLERANCE_PLUS = ini_pressure_control_tolerance_plus
        else:
            logger.error(f"config.ini: pressure target tolerance PLUS+ not in range (0-50), using default value {settings.PRESSURE_CONTROL_TOLERANCE_PLUS}")
            
        # tolerance_minus
        # check if in range
        if 0.0 <= ini_pressure_control_tolerance_minus <= 50.0:
            settings.PRESSURE_CONTROL_TOLERANCE_MINUS = ini_pressure_control_tolerance_minus
        else:
            logger.error(f"config.ini: pressure target tolerance MINUS- not in range (0-50), using default value {settings.PRESSURE_CONTROL_TOLERANCE_MINUS}")
            
        # setpoint
        # TODO
        # check if in range, but what range? min/max?
        settings.PRESSURE_CONTROL_SETPOINT = ini_pressure_control_setpoint
        
        # [pressure_sensor]
        # TODO
        settings.PRESSURE_SENSOR_CYCLE_TIME = ini_pressure_sensor_cycle_time
        settings.PRESSURE_SENSOR_BUS_NR = ini_pressure_sensor_bus_nr
        settings.PRESSURE_SENSOR_I2C_ADR = ini_pressure_sensor_i2c_adr

        # [pump_control]
        # TODO
        settings.PUMP_CONTROL_CYCLE_TIME = ini_pump_control_cycle_time
        settings.PUMP_CONTROL_PIN_NUMBER = ini_pump_control_pin_number

        # [valve_control]
        # TODO
        settings.VALVE_CONTROL_CYCLE_TIME = ini_valve_control_cycle_time
        settings.VALVE_CONTROL_PIN_NUMBER = ini_valve_control_pin_number

        # [mode_hold]
        # TODO
        # target between min/max
        settings.MODE_HOLD_PRESSURE_TARGET = ini_mode_hold_pressure_target
        
        # [mode_interval]
        # peak_pressure
        # TODO
        # in range min/max
        settings.MODE_INTERVAL_PEAK_PRESSURE = ini_mode_interval_peak_pressure
        # interval_time
        # >0s?
        settings.MODE_INTERVAL_INTERVAL_TIME = ini_mode_interval_interval_time

        # [mode_pulsating]
        # pump_time
        # >0s?
        settings.MODE_PULSATING_PUMP_TIME = ini_mode_pulsating_pump_time
        # release_time
        # >0s? but smaller than overheating valve[]
        settings.MODE_PULSATING_RELEASE_TIME = ini_mode_pulsating_release_time
    except Exception as e:
        logger.error(f"config.ini: non-valid values, using defaults")
        logger.error(f"config.ini: {e}")

    return settings

def apply_settings(control_data: ControlData, settings: Settings):
    # [logging]
    control_data.set_log_level(settings.LOG_LEVEL)
    # [pressure_control]
    control_data.set_pressure_target_tolerance_plus(settings.PRESSURE_CONTROL_TOLERANCE_PLUS)
    control_data.set_pressure_target_tolerance_plus(settings.PRESSURE_CONTROL_TOLERANCE_MINUS)
    control_data.set_pressure_setpoint(settings.PRESSURE_CONTROL_SETPOINT)
    control_data.set_pressure_max(settings.PRESSURE_CONTROL_PRESSURE_MAX)
    control_data.set_pressure_min(settings.PRESSURE_CONTROL_PRESSURE_MIN)
    # [mode_hold]
    control_data.set_pressure_target(settings.MODE_HOLD_PRESSURE_TARGET)
    # [mode_interval]
    control_data.set_mode_interval_peak_pressure(settings.MODE_INTERVAL_PEAK_PRESSURE)
    control_data.set_mode_interval_time(settings.MODE_INTERVAL_INTERVAL_TIME)
    # [mode_pulsating]
    control_data.set_mode_pulsating_pump_time(settings.MODE_PULSATING_PUMP_TIME)
    control_data.set_mode_pulsating_release_time(settings.MODE_PULSATING_RELEASE_TIME)


def init_pressure_sensore(control_data: ControlData, settings: Settings) -> Thread:
    pressure_sensor = PressureSensor(control_data=control_data,
                                     cycle_time=settings.PRESSURE_SENSOR_CYCLE_TIME,
                                     smbus_nr=settings.PRESSURE_SENSOR_BUS_NR,
                                     i2c_addr=settings.PRESSURE_SENSOR_I2C_ADR)
    pressure_sensor_thread = Thread(target=pressure_sensor.run)
    pressure_sensor_thread.start()
    return pressure_sensor_thread


def init_pressure_control(control_data: ControlData, settings: Settings) -> Thread:
    pressure_ctrl = PressureControl(control_data=control_data,
                                    cycle_time=settings.PRESSURE_CONTROL_CYCLE_TIME)
    pressure_ctrl_thread = Thread(target=pressure_ctrl.run)
    pressure_ctrl_thread.start()
    return pressure_ctrl_thread


def init_valve_control(control_data: ControlData, settings: Settings) -> Thread:
    valve_ctrl = ValveControl(control_data=control_data,
                              pin_number=settings.VALVE_CONTROL_PIN_NUMBER,
                              cycle_time=settings.VALVE_CONTROL_CYCLE_TIME)
    valve_ctrl_thread = Thread(target=valve_ctrl.run)
    valve_ctrl_thread.start()
    return valve_ctrl_thread

def init_pump_control(control_data: ControlData, settings: Settings) -> Thread:
    pump_ctrl = PumpControl(control_data=control_data,
                            pin_number=settings.PUMP_CONTROL_PIN_NUMBER,
                            cycle_time=settings.PUMP_CONTROL_CYCLE_TIME)
    pump_ctrl_thread = Thread(target=pump_ctrl.run)
    pump_ctrl_thread.start()
    return pump_ctrl_thread

def init_auto_setpoint(control_data: ControlData) -> Thread:
    auto_setpoint = AutoSetpoint(control_data=control_data)
    auto_setpoint_thread = Thread(target=auto_setpoint.run)
    auto_setpoint_thread.start()
    return auto_setpoint_thread

def init_api(control_data: ControlData, settings: Settings) -> tuple:
    api = PmpctrlAPI(control_data)
    # https://github.com/encode/uvicorn/issues/506#issuecomment-561071254
    api_server_config = uvicorn.Config(api,
                                       host="0.0.0.0",
                                       port=settings.API_PORT,
                                       log_level=settings.LOG_LEVEL,
                                       loop='none')
    api_server_config.log_config['formatters']['access']['fmt'] = '%(asctime)s.%(msecs)03dZ | %(levelname)-8s | %(name)-16s | %(funcName)-16s | %(message)s'
    api_server_config.log_config['formatters']['access']['datefmt'] = '%Y-%m-%dT%H:%M:%S'
    api_server = uvicorn.Server(config=api_server_config)
    api_server_thread = Thread(target=api_server.run)
    api_server_thread.start()
    return api_server, api_server_thread

def init_session_control(control_data: ControlData) -> Thread:
    session_control = SessionControl(control_data)
    session_control_thread = Thread(target=session_control.run)
    session_control_thread.start()
    return session_control_thread


def shutdown(signum, frame, control_data: ControlData):
    logger = logging.getLogger(__name__)
    logger.info('SIGTERM recived')
    control_data.event_run.clear()


def run(control_data: ControlData, settings: Settings):
    try:
        logger = logging.getLogger(__name__)
        logger.setLevel(settings.LOG_LEVEL)

        pressure_sensor = init_pressure_sensore(control_data, settings)
        pressure_control = init_pressure_control(control_data, settings)
        pump_control = init_pump_control(control_data, settings)
        valve_control = init_valve_control(control_data, settings)
        auto_setpoint = init_auto_setpoint(control_data)
        api_server, api_server_thread = init_api(control_data, settings)
        session_control = init_session_control(control_data)
    
        while control_data.event_run.is_set():
            session_on = ' ON' if control_data.event_session_on.is_set() else 'OFF'
            pressure_actual = control_data.get_pressure_actual()
            pressure_target = control_data.get_pressure_target()
            pressure_target_tolerance_plus = control_data.get_pressure_target_tolerance_plus()
            pressure_target_tolerance_minus = control_data.get_pressure_target_tolerance_minus()
            events = f'SESSION = {session_on}'
            pressure = f'Pressue: ACT = {pressure_actual:.2f}, TGT = {pressure_target:.2f} +{pressure_target_tolerance_plus:.2f}/-{pressure_target_tolerance_minus:.2f}'
            logger.info(f"Session: {session_on} | {pressure}")
            sleep(1.0)
    except KeyboardInterrupt:
            logger.info('Program stopped by user through keyboard interrupt.')
            control_data.event_run.clear()
    finally:
        api_server.should_exit = True
        api_server_thread.join()
        pressure_sensor.join()
        pressure_control.join()
        valve_control.join()
        auto_setpoint.join()
        session_control.join()


def main():
    args = parse_arguments()
    control_data = ControlData()
    settings = parse_config(args.config)
    apply_settings(control_data, settings)
    control_data.event_run.set()
    sigterm_handler = partial(shutdown, control_data=control_data)
    signal.signal(signal.SIGTERM, sigterm_handler)
    run(control_data, settings)
    if not control_data.event_error.is_set():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    #ctrl_data.set_mode(ControlData.MODE_EXPERIMENTAL)
    main()