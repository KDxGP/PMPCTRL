import datetime

from threading import Event
from threading import Lock

class ControlData:
    _instance = None
    _lock = Lock()

    _log_level = 20

    MODE_PRESSURE_HOLD = 0
    MODE_INTERVAL = 1
    MODE_PULSATING = 2
    MODE_EXPERIMENTAL = 666

    event_run: Event
    event_error: Event
    event_session_on: Event
    event_set_setpoint: Event
    event_auto_setpoint: Event
    event_pump_state_on: Event
    event_pump_turn_on: Event
    event_pump_turn_off: Event
    event_valve_state_closed: Event
    event_valve_open: Event
    event_valve_close: Event

    _time_utc_now: datetime.datetime
    _time_utc_session_start: datetime.datetime
    _last_session_duration: int
    
    _pressure_actual: float
    _pressure_setpoint: float
    _pressure_target: float
    _pressure_target_tolerance_minus: float
    _pressure_target_tolerance_plus: float
    _pressure_control: bool
    _pressure_max: float
    _pressure_min: float

    _mode: int
    _mode_interval_peak_pressure: float
    _mode_interval_time: float
    _mode_pulsating_pump_time: float
    _mode_pulsating_release_time: float

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    
                    cls.event_run = Event()
                    cls.event_error = Event()
                    cls.event_session_on = Event()
                    cls.event_set_setpoint = Event()
                    cls.event_auto_setpoint = Event()
                    cls.event_pump_state_on = Event()
                    cls.event_pump_turn_on = Event()
                    cls.event_pump_turn_off = Event()
                    cls.event_valve_state_closed = Event()
                    # normally closed valve, therefore event True on start
                    cls.event_valve_state_closed.set()
                    cls.event_valve_open = Event()
                    cls.event_valve_close = Event()

                    cls._time_utc_now = datetime.datetime.utcnow()
                    cls._time_utc_session_start = None
                    cls._last_session_duration = None

                    #cls._pressure_setpoint = 1013.25 # sea level
                    # avg. human population 435m above seal level, air pressure 20°C at 435m -> 962.9274mbar
                    cls._pressure_setpoint = 962.9274
                    cls._pressure_target_tolerance_minus = 10.0
                    #cls._pressure_tolerance_minus = 3.38639 # ~0.1inHg
                    cls._pressure_target_tolerance_plus = 10.0
                    #cls._pressure_tolerance_plus = 3.38639 # ~0.1inHg
                    cls._pressure_actual = -1.0
                    cls._pressure_target = 875.0
                    # auto control pressure to setpoint
                    cls._pressure_control = True
                    # ~highest ever recorded air pressure
                    cls._pressure_max = 1084.0
                    # roughly -15inHg of setpoint
                    cls._pressure_min = 450.0

                    # Default mode
                    cls._mode = ControlData.MODE_PRESSURE_HOLD
                    cls._mode_interval_peak_pressure = 790.0
                    cls._mode_interval_time = 20.0
                    cls._mode_pulsating_pump_time = 2.5
                    cls._mode_pulsating_release_time = 1.7

        return cls._instance

    def set_log_level(self, log_level: int):
        with self._lock:
            self._log_level = log_level

    def get_log_level(self) -> int:
        with self._lock:
            return self._log_level

    # mode
    def set_mode(self, mode: int):
        with self._lock:
            if mode == ControlData.MODE_PRESSURE_HOLD:
                self._mode = ControlData.MODE_PRESSURE_HOLD
                self._pressure_control = True
            elif mode == ControlData.MODE_INTERVAL:
                self._mode = ControlData.MODE_INTERVAL
                self._pressure_control = True
            elif mode == ControlData.MODE_PULSATING:
                self._mode = ControlData.MODE_PULSATING
                self._pressure_control = False
            elif mode == ControlData.MODE_EXPERIMENTAL:
                self._mode = ControlData.MODE_EXPERIMENTAL

    def get_mode(self) -> int:
        with self._lock:
            return self._mode

    # time / duration
    def get_time_utc_now(self) -> datetime.datetime:
        with self._lock:
            return self._time_utc_now

    def set_time_utc_now(self):
        with self._lock:
            self._time_utc_now = datetime.datetime.utcnow()

    def get_time_utc_session_start(self) -> datetime.datetime:
        with self._lock:
            if self._time_utc_session_start is None:
                return None
            return self._time_utc_session_start

    def set_time_utc_session_start(self):
        with self._lock:
            self._time_utc_session_start = datetime.datetime.utcnow()

    def get_last_session_duration(self) -> int:
        with self._lock:
            if self._last_session_duration is None:
                return None
            return self._last_session_duration

    def set_last_session_duration(self):
        with self._lock:
            self._last_session_duration = (self._time_utc_now - self._time_utc_session_start).seconds

    # pressure
    # pressure - actual
    def get_pressure_actual(self) -> float:
        with self._lock:
            return self._pressure_actual
    
    def set_pressure_actual(self, pressure_actual: float):
        with self._lock:
            self._pressure_actual = pressure_actual

    # pressure - setpoint
    def get_pressure_setpoint(self) -> float:
        with self._lock:
            return self._pressure_setpoint

    def set_pressure_setpoint(self, setpoint: float):
        with self._lock:
            self._pressure_setpoint = setpoint

    # pressure - target
    def get_pressure_target(self) -> float:
        with self._lock:
            return self._pressure_target
    
    def set_pressure_target(self, pressure_target: float):
        with self._lock:
            self._pressure_target = pressure_target

    # pressure - target - tolerance - minus
    def get_pressure_target_tolerance_minus(self) -> float:
        with self._lock:
            return self._pressure_target_tolerance_minus

    def set_pressure_target_tolerance_minus(self, tolerance_minus: float):
        with self._lock:
            self._pressure_target_tolerance_minus = abs(tolerance_minus)

    # pressure - target - tolerance - plus
    def get_pressure_target_tolerance_plus(self) -> float:
        with self._lock:
            return self._pressure_target_tolerance_plus

    def set_pressure_target_tolerance_plus(self, tolerance_plus: float):
        with self._lock:
            self._pressure_target_tolerance_plus = abs(tolerance_plus)

    # auto control pressure
    def get_pressure_control(self) -> bool:
        with self._lock:
            return self._pressure_control

    def set_pressure_control(self, pressure_control: bool):
        with self._lock:
            self._pressure_control = pressure_control

    # pressure - max
    def get_pressure_max(self) -> float:
        with self._lock:
            return self._pressure_max

    def set_pressure_max(self, max_pressure: float):
        with self._lock:
            self._pressure_max = abs(max_pressure)

    # pressure - min
    def get_pressure_min(self) -> float:
        with self._lock:
            return self._pressure_min

    def set_pressure_min(self, min_pressure: float):
        with self._lock:
            self._pressure_min = abs(min_pressure)

    # mode interval
    def get_mode_interval_peak_pressure(self) -> float:
        with self._lock:
            return self._mode_interval_peak_pressure

    def set_mode_interval_peak_pressure(self, peak_pressure: float):
        with self._lock:
            self._mode_interval_peak_pressure = peak_pressure

    def get_mode_interval_time(self) -> float:
        with self._lock:
            return self._mode_interval_time

    def set_mode_interval_time(self, interval_time: float):
        with self._lock:
            self._mode_interval_time = interval_time

    # mode pulsating
    def get_mode_pulsating_pump_time(self) -> float:
        with self._lock:
            return self._mode_pulsating_pump_time

    def set_mode_pulsating_pump_time(self, pump_time: float):
        with self._lock:
            self._mode_pulsating_pump_time = pump_time

    def get_mode_pulsating_release_time(self) -> float:
        with self._lock:
            return self._mode_pulsating_release_time

    def set_mode_pulsating_release_time(self, release_time: float):
        with self._lock:
            self._mode_pulsating_release_time = release_time

