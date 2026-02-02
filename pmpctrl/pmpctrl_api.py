from fastapi import APIRouter
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pmpctrl.control_data import ControlData
from pydantic import BaseModel
from typing import Literal


class ErrorMessage(BaseModel):
    status: int
    title: str
    detail: str

class PressureTarget(BaseModel):
    target: float | None = None
    tolerance_minus: float | None = None
    tolerance_plus: float | None = None

class Setpoint(BaseModel):
    auto_setpoint: bool | None = None
    setpoint: float | None = None

class Mode(BaseModel):
    mode: Literal['hold', 'interval', 'pulsating']

class ModeInterval(BaseModel):
    peak_pressure: float
    interval_time: float

class ModePulsating(BaseModel):
    pump_time: float
    release_time: float

class ApiError(HTTPException):
    def __init__(self, msg:ErrorMessage):
        detail = f'{msg.title}: {msg.detail}'
        super().__init__(status_code=msg.status, detail=detail)

class ApiErrorSessionOn(ApiError):
    def __init__(self):
        error_msg = ErrorMessage(
            status=409,
            title='Operation not allowed during session',
            detail='Stop session first to perform this operation'
        )
        super().__init__(error_msg)

class PmpctrlAPI(FastAPI):
    _control_data: ControlData
    _router: APIRouter()

    def __init__(self, control_data: ControlData):
        super().__init__()
        self._control_data = control_data

        # CORS
        origins = ['*']
        self.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )

        self._router = APIRouter()
        self._router.add_api_route('/', self.get_root, methods=['GET'])
        
        self._router.add_api_route('/pressure', self.get_pressure, tags=['pressure'], methods=['GET'])
        self._router.add_api_route('/pressure/actual', self.get_pressure_actual, tags=['pressure'], methods=['GET'])
        self._router.add_api_route('/pressure/target', self.get_pressure_target, tags=['pressure'], methods=['GET'])
        self._router.add_api_route('/pressure/target', self.put_pressure_target, tags=['pressure'], methods=['PUT'])
        self._router.add_api_route('/pressure/setpoint', self.get_pressure_setpoint, tags=['pressure'], methods=['GET'])
        self._router.add_api_route('/pressure/setpoint', self.put_pressure_setpoint, tags=['pressure'], methods=['PUT'])
        
        self._router.add_api_route('/session', self.get_session, tags=['session'], methods=['GET'])
        self._router.add_api_route('/session/start', self.put_session_start, tags=['session'], methods=['PUT'])
        self._router.add_api_route('/session/stop', self.put_session_stop, tags=['session'], methods=['PUT'])

        self._router.add_api_route('/pump', self.get_pump, tags=['pump'], methods=['GET'])
        self._router.add_api_route('/pump/on', self.put_pump_on, tags=['pump'], methods=['PUT'])
        self._router.add_api_route('/pump/off', self.put_pump_off, tags=['pump'], methods=['PUT'])

        self._router.add_api_route('/valve', self.get_valve, tags=['valve'], methods=['GET'])
        self._router.add_api_route('/valve/open', self.put_valve_open, tags=['valve'], methods=['PUT'])
        self._router.add_api_route('/valve/close', self.put_valve_close, tags=['valve'], methods=['PUT'])

        self._router.add_api_route('/mode', self.get_mode, tags=['mode'], methods=['GET'])
        self._router.add_api_route('/mode', self.put_mode, tags=['mode'], methods=['PUT'])
        self._router.add_api_route('/mode/interval', self.put_mode_interval, tags=['mode'], methods=['PUT'])
        self._router.add_api_route('/mode/pulsating', self.put_mode_pulsating, tags=['mode'], methods=['PUT'])
        
        self.include_router(self._router)
        
    def _get_session_state(self) -> str:
        return 'on' if self._control_data.event_session_on.is_set() else 'off'

    def _get_pump_state(self) -> str:
        return 'on' if self._control_data.event_pump_state_on.is_set() else 'off'

    def _get_valve_state(self) -> str:
        return 'closed' if self._control_data.event_valve_state_closed.is_set() else 'open'

    def _get_auto_setpoint(self) -> bool:
        return True if self._control_data.event_auto_setpoint.is_set() else False

    def _get_active_mode(self) -> str:
        mode = self._control_data.get_mode()
        mode_str = 'unknown'
        if mode == ControlData.MODE_PRESSURE_HOLD:
            mode_str = 'hold'
        elif mode == ControlData.MODE_INTERVAL:
            mode_str = 'interval'
        elif mode == ControlData.MODE_PULSATING:
            mode_str = 'pulsating'
        return mode_str
    
    def get_root(self) -> dict:
        self._control_data.set_time_utc_now()
        startSession = None
        lastSessionDuration = None
        if self._control_data.get_time_utc_session_start() is not None:
            startSession = self._control_data.get_time_utc_session_start().isoformat()
        if self._control_data.get_last_session_duration() is not None:
            lastSessionDuration = self._control_data.get_last_session_duration()
        return {
            'session' : self._get_session_state(),
            'pump' : self._get_pump_state(),
            'valve' : self._get_valve_state(),
            'time_utc_now' : self._control_data.get_time_utc_now().isoformat(),
            'time_utc_session_start' : startSession,
            'last_session_duration' : lastSessionDuration,
            'pressure': {
                'actual' : self._control_data.get_pressure_actual(),
                'setpoint' : self._control_data.get_pressure_setpoint(),
                'auto_setpoint' : self._get_auto_setpoint(),
                'min' : self._control_data.get_pressure_min(),
                'max' : self._control_data.get_pressure_max(),
                'target' : self.get_pressure_target()
            },
            'mode' : self.get_mode()
        }

    def get_pressure(self) -> dict:
        return {
            'pressure': {
                'actual' : self._control_data.get_pressure_actual(),
                'setpoint' : self._control_data.get_pressure_setpoint(),
                'auto_setpoint' : self._get_auto_setpoint(),
                'min' : self._control_data.get_pressure_min(),
                'max' : self._control_data.get_pressure_max(),
                'target' : self.get_pressure_target()
            }
        }

    def get_pressure_actual(self) -> dict:
        return { 'actual' : self._control_data.get_pressure_actual() }

    def get_pressure_target(self) -> dict:
        return {
            'target' : self._control_data.get_pressure_target(),
            'tolerance_minus' : self._control_data.get_pressure_target_tolerance_minus(),
            'tolerance_plus' : self._control_data.get_pressure_target_tolerance_plus()
        }
        
    def put_pressure_target(self, target_new: PressureTarget) -> dict:
        target = self._control_data.get_pressure_target()
        pressure_min = self._control_data.get_pressure_min()
        pressure_max = self._control_data.get_pressure_max()

        # TODO: decide if to check in min/max range taking tolerance +/- into considaration
        #   - e.g. min=300, tolerance_minus=10 and target should be 305
        #   - as of today (2025-01-17) there's no mechanism using min/max values

        if target_new.target is not None:
            if pressure_min <= target_new.target <= pressure_max:
                self._control_data.set_pressure_target(target_new.target)
            else:
                error = ErrorMessage(
                    status = 400,
                    title = 'Pressure target out of range',
                    detail = f'The new pressure target is not within range of min={pressure_min} to max={pressure_max}'
                )
                raise ApiError(error)

        if target_new.tolerance_minus is not None:
            error = ErrorMessage(
                    status = 400,
                    title = 'Pressure tolerances must be defined as >= 0',
                    detail = f'e.g. Set as 5.6, not -5.6'
                )
            if target_new.tolerance_minus < 0:
                raise ApiError(error)
            self._control_data.set_pressure_target_tolerance_minus(target_new.tolerance_minus)
        if target_new.tolerance_plus is not None:
            if target_new.tolerance_plus < 0:
                raise ApiError(error)
            self._control_data.set_pressure_target_tolerance_plus(target_new.tolerance_plus)

        return self.get_pressure_target()
        
    def get_pressure_setpoint(self) -> dict:
        return { 'setpoint' : self._control_data.get_pressure_setpoint() }
    
    def put_pressure_setpoint(self, setpoint: Setpoint | None = None):
        if self._control_data.event_session_on.is_set():
            raise ApiErrorSessionOn()

        if setpoint is None:
            self._control_data.event_set_setpoint.set()
        else:
            if setpoint.auto_setpoint is not None:
                if setpoint.auto_setpoint:
                    self._control_data.event_auto_setpoint.set()
                else:
                    self._control_data.event_auto_setpoint.clear()
            if setpoint.setpoint is not None:
                # TODO check if within min/max range
                self._control_data.set_pressure_setpoint(setpoint.setpoint)

    def get_session(self) -> dict:
        return { 'session' : self._get_session_state() }
        
    def put_session_start(self) -> dict:
        if self._control_data.event_session_on.is_set():
            raise ApiErrorSessionOn()
        self._control_data.event_session_on.set()
        self._control_data.set_time_utc_session_start()
        return self.get_session()

    def put_session_stop(self) -> dict:
        if not self._control_data.event_session_on.is_set():
            error = ErrorMessage(
                status = 409,
                title = 'No session in progress',
                detail = 'Start a session first to stop it'
            )
            raise ApiError(error)
        self._control_data.event_session_on.clear()
        self._control_data.set_last_session_duration()
        # TODO: put in own function in ControlData to keep API clear of logic
        if self._control_data.event_pump_state_on.is_set():
            self._control_data.event_pump_turn_off.set()
        if not self._control_data.event_valve_state_closed.is_set():
            self._control_data.event_valve_close.set()
        return self.get_session()

    def get_valve(self) -> dict:
        return { 'valve' : self._get_valve_state() }

    def put_valve_open(self):
        if self._control_data.event_session_on.is_set():
            raise ApiErrorSessionOn()
        elif not self._control_data.event_valve_state_closed.is_set():
            error = ErrorMessage(
                status = 409,
                title = 'Valve is already open',
                detail = 'Close valve first to open it'
            )
            raise ApiError(error)
        self._control_data.event_valve_open.set()
        # TODO: race condition -> either return nothing or wait until state change
        #return self.get_valve()

    def put_valve_close(self):
        if self._control_data.event_session_on.is_set():
            raise ApiErrorSessionOn()
        elif self._control_data.event_valve_state_closed.is_set():
            error = ErrorMessage(
                status = 409,
                title = 'Valve is already closed',
                detail = 'Open valve first to close it'
            )
            raise ApiError(error)
        self._control_data.event_valve_close.set()
        # TODO: race condition -> either return nothing or wait until state change
        #return self.get_valve()

    def get_pump(self) -> dict:
        return { 'pump' : self._get_pump_state() }

    def put_pump_on(self):
        if self._control_data.event_session_on.is_set():
            raise ApiErrorSessionOn()
        elif self._control_data.event_pump_state_on.is_set():
            error = ErrorMessage(
                status = 409,
                title = 'Pump is already on',
                detail = 'Turn pump off first'
            )
            raise ApiError(error)
        self._control_data.event_pump_turn_off.clear()
        self._control_data.event_pump_turn_on.set()
        # TODO: race condition -> either return nothing or wait until state change
        #return self.get_pump()

    def put_pump_off(self):
        if self._control_data.event_session_on.is_set():
            raise ApiErrorSessionOn()
        elif not self._control_data.event_pump_state_on.is_set():
            error = ErrorMessage(
                status = 409,
                title = 'Pump is already off',
                detail = 'Turn pump on first'
            )
            raise ApiError(error)
        self._control_data.event_pump_turn_on.clear()
        self._control_data.event_pump_turn_off.set()
        # TODO: race condition -> either return nothing or wait until state change
        #return self.get_pump()

    def get_mode(self):
        available_modes = ['hold', 'interval', 'pulsating']
        return {
            'active' : self._get_active_mode(),
            'available' : available_modes,
            'interval': {
                'peak_pressure' : self._control_data.get_mode_interval_peak_pressure(),
                'interval_time' : self._control_data.get_mode_interval_time()
            },
            'pulsating': {
                'pump_time' : self._control_data.get_mode_pulsating_pump_time(),
                'release_time' : self._control_data.get_mode_pulsating_release_time()
            }
        }
    
    def put_mode(self, mode: Mode):
        if mode.mode == 'hold':
            self._control_data.set_mode(ControlData.MODE_PRESSURE_HOLD)
        elif mode.mode == 'interval':
            self._control_data.set_mode(ControlData.MODE_INTERVAL)
        elif mode.mode == 'pulsating':
            self._control_data.set_mode(ControlData.MODE_PULSATING)

    def put_mode_interval(self, settings: ModeInterval):
        self._control_data.set_mode_interval_peak_pressure(settings.peak_pressure)
        self._control_data.set_mode_interval_time(settings.interval_time)

    def put_mode_pulsating(self, settings: ModePulsating):
        self._control_data.set_mode_pulsating_pump_time(settings.pump_time)
        self._control_data.set_mode_pulsating_release_time(settings.release_time)