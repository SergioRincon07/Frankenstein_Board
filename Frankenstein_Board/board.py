#!/usr/bin/env python3
"""
Frankenstein Board -- drivers unificados.

Combina dos placas sobre un mismo bus I2C:
  - Yahboom motor controller  (0x26): 4 motores DC con encoder
  - HiWonder expansion board  (0x7A): LED RGB, buzzer, PWM servo, batería
  - Sonar ultrasónico          (0x77): distancia en mm

Drivers exportados:
  FrankensteinMotorDriver
  FrankensteinSonarDriver
  FrankensteinLedDriver
  FrankensteinBuzzerDriver
  FrankensteinPwmServoDriver
  FrankensteinBoard           (facade que agrupa todos los anteriores)
"""

import errno
import os
import struct
import sys
import time
from typing import Dict, Optional

import smbus
from smbus2 import SMBus, i2c_msg

try:
    import Hiwonder_Board.board as _HwBoard
except ImportError:
    _HwBoard = None

try:
    import Yahboom_Board.board as _YHBoard
except ImportError:
    _YHBoard = None    

# ---------------------------------------------------------------------------
# Constantes globales
# ---------------------------------------------------------------------------
I2C_RETRY_DELAY = 0.05
I2C_MAX_RETRIES = 3
_RETRYABLE_CODES = {errno.EIO, getattr(errno, "EREMOTEIO", 121), 121}


def _is_retryable(exc: OSError) -> bool:
    return getattr(exc, "errno", None) in _RETRYABLE_CODES


# ═══════════════════════════════════════════════════════════════════════════
# 1. Motor Driver  (Yahboom I2C 0x26)
# ═══════════════════════════════════════════════════════════════════════════
class FrankensteinMotorDriver:
    """Control de 4 motores DC con encoder vía I2C (Yahboom board 0x26)."""

    REG_MOTOR_TYPE = 0x01
    REG_DEADZONE = 0x02
    REG_PULSE_LINE = 0x03
    REG_PULSE_PHASE = 0x04
    REG_WHEEL_DIA = 0x05
    REG_SPEED = 0x06
    REG_PWM = 0x07
    REG_ENC_10MS_M1 = 0x10
    REG_ENC_ALL_HIGH = 0x20
    REG_ENC_ALL_LOW = 0x21

    SPEED_MIN, SPEED_MAX = -1000, 1000
    PWM_MIN, PWM_MAX = -3600, 3600

    MOTOR_PROFILES = {
        1: {"type": 1, "phase": 30, "line": 11, "wheel_dia": 60.0, "deadzone": 1900},
        2: {"type": 2, "phase": 20, "line": 13, "wheel_dia": 48.0, "deadzone": 1600},
        3: {"type": 3, "phase": 45, "line": 13, "wheel_dia": 60.0, "deadzone": 1250},
        4: {"type": 4, "phase": 48, "line": 0,  "wheel_dia": 0.0,  "deadzone": 1000},
        5: {"type": 1, "phase": 40, "line": 11, "wheel_dia": 60.0, "deadzone": 1900},
    }

    def __init__(
        self,
        bus_num: int = 1,
        addr: int = 0x26,
        motor_type: Optional[int] = None,
    ) -> None:
        self._addr = int(addr)
        self._bus = smbus.SMBus(int(bus_num))
        self._motor_type: Optional[int] = None
        if motor_type is not None:
            self.configure(motor_type)

    # -- I2C primitivas -----------------------------------------------------

    def _i2c_write(self, reg: int, data) -> None:
        payload = list(data) if isinstance(data, (list, tuple)) else [int(data) & 0xFF]
        for attempt in range(I2C_MAX_RETRIES):
            try:
                self._bus.write_i2c_block_data(self._addr, reg, payload)
                return
            except OSError as exc:
                if _is_retryable(exc) and attempt < I2C_MAX_RETRIES - 1:
                    time.sleep(I2C_RETRY_DELAY)
                    continue
                raise

    def _i2c_read(self, reg: int, length: int):
        for attempt in range(I2C_MAX_RETRIES):
            try:
                return list(self._bus.read_i2c_block_data(self._addr, reg, length))
            except OSError as exc:
                if _is_retryable(exc) and attempt < I2C_MAX_RETRIES - 1:
                    time.sleep(I2C_RETRY_DELAY)
                    continue
                return [0] * length
        return [0] * length

    # -- Configuración del perfil de motor ----------------------------------

    def _set_motor_type(self, motor_type: int) -> None:
        self._i2c_write(self.REG_MOTOR_TYPE, [motor_type & 0xFF])
        time.sleep(0.1)

    def _set_pulse_phase(self, phase: int) -> None:
        self._i2c_write(self.REG_PULSE_PHASE, [(phase >> 8) & 0xFF, phase & 0xFF])
        time.sleep(0.1)

    def _set_pulse_line(self, line: int) -> None:
        self._i2c_write(self.REG_PULSE_LINE, [(line >> 8) & 0xFF, line & 0xFF])
        time.sleep(0.1)

    def _set_wheel_diameter(self, mm: float) -> None:
        self._i2c_write(self.REG_WHEEL_DIA, list(struct.pack("<f", float(mm))))
        time.sleep(0.1)

    def _set_deadzone(self, zone: int) -> None:
        self._i2c_write(self.REG_DEADZONE, [(zone >> 8) & 0xFF, zone & 0xFF])
        time.sleep(0.1)

    def configure(self, motor_type: int = 3) -> None:
        profile = self.MOTOR_PROFILES.get(int(motor_type))
        if profile is None:
            raise ValueError(f"Tipo de motor desconocido: {motor_type}")
        self._motor_type = int(motor_type)
        self._set_motor_type(profile["type"])
        self._set_pulse_phase(profile["phase"])
        if profile["line"]:
            self._set_pulse_line(profile["line"])
        if profile["wheel_dia"]:
            self._set_wheel_diameter(profile["wheel_dia"])
        self._set_deadzone(profile["deadzone"])

    # -- Control de movimiento ----------------------------------------------

    @staticmethod
    def _clamp(value: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, int(value)))

    @staticmethod
    def _pack_4x_int16(m1: int, m2: int, m3: int, m4: int):
        out = []
        for v in (m1, m2, m3, m4):
            v = v & 0xFFFF
            out.append((v >> 8) & 0xFF)
            out.append(v & 0xFF)
        return out

    def set_speed(self, m1: int = 0, m2: int = 0, m3: int = 0, m4: int = 0) -> None:
        values = [self._clamp(v, self.SPEED_MIN, self.SPEED_MAX) for v in (m1, m2, m3, m4)]
        self._i2c_write(self.REG_SPEED, self._pack_4x_int16(*values))

    def set_pwm(self, m1: int = 0, m2: int = 0, m3: int = 0, m4: int = 0) -> None:
        values = [self._clamp(v, self.PWM_MIN, self.PWM_MAX) for v in (m1, m2, m3, m4)]
        self._i2c_write(self.REG_PWM, self._pack_4x_int16(*values))

    def stop(self) -> None:
        self.set_speed(0, 0, 0, 0)
        self.set_pwm(0, 0, 0, 0)

    # -- Lectura de encoders ------------------------------------------------

    def read_encoder_10ms(self) -> Dict[int, int]:
        result = {}
        for i in range(4):
            buf = self._i2c_read(self.REG_ENC_10MS_M1 + i, 2)
            value = (buf[0] << 8) | buf[1]
            if value & 0x8000:
                value -= 0x10000
            result[i + 1] = value
        return result

    def read_encoder_total(self) -> Dict[int, int]:
        result = {}
        for i in range(4):
            high_reg = self.REG_ENC_ALL_HIGH + (i * 2)
            low_reg = self.REG_ENC_ALL_LOW + (i * 2)
            hb = self._i2c_read(high_reg, 2)
            lb = self._i2c_read(low_reg, 2)
            value = (hb[0] << 24) | (hb[1] << 16) | (lb[0] << 8) | lb[1]
            if value >= 0x80000000:
                value -= 0x100000000
            result[i + 1] = value
        return result

    # -- Utilidades ---------------------------------------------------------

    def scan(self) -> bool:
        try:
            self._bus.read_byte(self._addr)
            return True
        except OSError:
            return False

    def shutdown(self) -> None:
        if self._bus is None:
            return
        try:
            self.stop()
        except OSError:
            pass
        try:
            self._bus.close()
        except OSError:
            pass
        self._bus = None

    def __repr__(self) -> str:
        return f"FrankensteinMotorDriver(addr=0x{self._addr:02X}, type={self._motor_type})"


# ═══════════════════════════════════════════════════════════════════════════
# 2. Sonar Driver  (I2C 0x77)
# ═══════════════════════════════════════════════════════════════════════════
class FrankensteinSonarDriver:
    """Sensor ultrasónico I2C (distancia en mm/cm)."""

    MAX_RANGE_MM = 5000

    def __init__(self, bus_num: int = 1, addr: int = 0x77) -> None:
        self._i2c_addr = int(addr)
        self._bus_num = int(bus_num)

    def get_distance_mm(self) -> int:
        dist = 99999
        try:
            with SMBus(self._bus_num) as bus:
                bus.i2c_rdwr(i2c_msg.write(self._i2c_addr, [0]))
                read = i2c_msg.read(self._i2c_addr, 2)
                bus.i2c_rdwr(read)
                dist = int.from_bytes(bytes(list(read)), byteorder="little", signed=False)
                if dist > self.MAX_RANGE_MM:
                    dist = self.MAX_RANGE_MM
        except OSError:
            pass
        return int(dist)

    def get_distance_cm(self) -> float:
        return self.get_distance_mm() / 10.0

    def shutdown(self) -> None:
        pass

    def __repr__(self) -> str:
        return f"FrankensteinSonarDriver(addr=0x{self._i2c_addr:02X})"


# ═══════════════════════════════════════════════════════════════════════════
# 3. LED Driver  (HiwonderSDK -- WS2812, 2 píxeles)
# ═══════════════════════════════════════════════════════════════════════════
class FrankensteinLedDriver:
    """Control de LEDs RGB WS2812 via HiwonderSDK.Board."""

    NUM_PIXELS = 2

    def __init__(self) -> None:
        if _HwBoard is None:
            raise RuntimeError("HiwonderSDK.Board no disponible")

    def set_pixel(self, index: int, r: int, g: int, b: int) -> None:
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))
        _HwBoard.RGB.setPixelColor(int(index), _HwBoard.PixelColor(r, g, b))

    def show(self) -> None:
        _HwBoard.RGB.show()

    def clear(self) -> None:
        for i in range(self.NUM_PIXELS):
            _HwBoard.RGB.setPixelColor(i, _HwBoard.PixelColor(0, 0, 0))
        _HwBoard.RGB.show()

    def shutdown(self) -> None:
        try:
            self.clear()
        except Exception:  # noqa: BLE001
            pass


# ═══════════════════════════════════════════════════════════════════════════
# 4. Buzzer Driver  (HiwonderSDK -- GPIO 31)
# ═══════════════════════════════════════════════════════════════════════════
class FrankensteinBuzzerDriver:
    """Buzzer piezoeléctrico on/off via HiwonderSDK.Board."""

    def __init__(self) -> None:
        if _HwBoard is None:
            raise RuntimeError("HiwonderSDK.Board no disponible")

    def set_state(self, on: bool) -> None:
        _HwBoard.setBuzzer(1 if on else 0)

    def on(self) -> None:
        self.set_state(True)

    def off(self) -> None:
        self.set_state(False)

    def shutdown(self) -> None:
        try:
            self.off()
        except Exception:  # noqa: BLE001
            pass


# ═══════════════════════════════════════════════════════════════════════════
# 5. PWM Servo Driver  (HiwonderSDK -- I2C 0x7A, reg 40)
# ═══════════════════════════════════════════════════════════════════════════
class FrankensteinPwmServoDriver:
    """Servo PWM controlado por la placa de expansión HiWonder."""

    def __init__(self, channel: int = 1, center_pulse: int = 1500) -> None:
        if _HwBoard is None:
            raise RuntimeError("HiwonderSDK.Board no disponible")
        self._channel = int(channel)
        self._center_pulse = int(center_pulse)

    def set_pulse(self, pulse: int, duration_ms: int) -> None:
        _HwBoard.setPWMServoPulse(self._channel, int(pulse), int(duration_ms))

    def center(self, duration_ms: int = 500) -> None:
        self.set_pulse(self._center_pulse, duration_ms)

    def shutdown(self) -> None:
        try:
            self.center()
        except Exception:  # noqa: BLE001
            pass


# ═══════════════════════════════════════════════════════════════════════════
# 6. Batería  (HiwonderSDK -- I2C 0x7A, reg 0)
# ═══════════════════════════════════════════════════════════════════════════
class FrankensteinBatteryMonitor:
    """Lectura de voltaje de batería via HiwonderSDK.Board."""

    def __init__(self) -> None:
        if _HwBoard is None:
            raise RuntimeError("HiwonderSDK.Board no disponible")

    def get_voltage(self) -> float:
        return float(_HwBoard.getBattery()) / 1000.0


# ═══════════════════════════════════════════════════════════════════════════
# 7. Facade  (agrupa todos los drivers)
# ═══════════════════════════════════════════════════════════════════════════
class FrankensteinBoard:
    """Facade que instancia y agrupa todos los drivers de la Frankenstein Board."""

    def __init__(
        self,
        bus_num: int = 1,
        motor_addr: int = 0x26,
        sonar_addr: int = 0x77,
        motor_type: int = 3,
        servo_channel: int = 1,
        servo_center: int = 1500,
    ) -> None:
        self.motor = FrankensteinMotorDriver(bus_num=bus_num, addr=motor_addr, motor_type=motor_type)
        self.sonar = FrankensteinSonarDriver(bus_num=bus_num, addr=sonar_addr)
        self.led = FrankensteinLedDriver()
        self.buzzer = FrankensteinBuzzerDriver()
        self.servo = FrankensteinPwmServoDriver(channel=servo_channel, center_pulse=servo_center)
        self._battery = FrankensteinBatteryMonitor()

    def battery_voltage(self) -> float:
        return self._battery.get_voltage()

    def scan_all(self) -> Dict[str, bool]:
        return {
            "motor": self.motor.scan(),
            "sonar": self.sonar.get_distance_mm() < 99999,
        }

    def shutdown_all(self) -> None:
        for drv in (self.motor, self.servo, self.buzzer, self.led, self.sonar):
            try:
                drv.shutdown()
            except Exception:  # noqa: BLE001
                pass
