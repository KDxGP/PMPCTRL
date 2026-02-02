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
    LOG_LEVEL = logging.WARNING
    API_PORT = 8000
    PRESSURE_CONTROL_CYCLE_TIME = 0.01
    PRESSURE_SENSOR_CYCLE_TIME = 0.01
    PRESSURE_SENSOR_BUS_NR = 1
    PRESSURE_SENSOR_I2C_ADR = 0x76
    PUMP_CONTROL_CYCLE_TIME = 0.5
    PUMP_CONTROL_PIN_NUMBER = 24
    VALVE_CONTROL_CYCLE_TIME = 0.1
    VALVE_CONTROL_PIN_NUMBER = 23


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='config file', required=True)
    return parser.parse_args()


def parse_config(control_data: ControlData, config_file: str) -> Settings:
    config = configparser.ConfigParser()
    config.read(config_file)
    settings = Settings

    config_log_level = config.get('logging', 'log_level')
    logging_log_levels = logging.getLevelNamesMapping().items()
    for key, value in logging_log_levels:
        if config_log_level in key:
            settings.LOG_LEVEL = value

    control_data.set_log_level(settings.LOG_LEVEL)

    settings.API_PORT = config.getint('api', 'port')
    settings.PRESSURE_CONTROL_CYCLE_TIME = config.getfloat('pressure_control', 'cycle_time')
    
    control_data.set_pressure_target_tolerance_plus(config.getfloat('pressure_control', 'tolerance_plus'))
    control_data.set_pressure_target_tolerance_minus(config.getfloat('pressure_control', 'tolerance_minus'))

    settings.PRESSURE_SENSOR_CYCLE_TIME = config.getfloat('pressure_sensor', 'cycle_time')
    settings.PRESSURE_SENSOR_BUS_NR = config.getint('pressure_sensor', 'smbus_nr')
    settings.PRESSURE_SENSOR_I2C_ADR = int(config.get('pressure_sensor', 'i2c_address'), 0)
    settings.PUMP_CONTROL_CYCLE_TIME = config.getfloat('pump_control', 'cycle_time')
    settings.PUMP_CONTROL_PIN_NUMBER = config.getint('pump_control', 'pin_number')
    settings.VALVE_CONTROL_CYCLE_TIME = config.getfloat('valve_control', 'cycle_time')
    settings.VALVE_CONTROL_PIN_NUMBER = config.getint('valve_control', 'pin_number')

    return settings


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
    control_data.event_run.set()
    sigterm_handler = partial(shutdown, control_data=control_data)
    signal.signal(signal.SIGTERM, sigterm_handler)
    settings = parse_config(control_data, args.config)
    run(control_data, settings)
    if not control_data.event_error.is_set():
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    #ctrl_data.set_mode(ControlData.MODE_EXPERIMENTAL)
    main()