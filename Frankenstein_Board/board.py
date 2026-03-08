#!/usr/bin/env python3
"""
Frankenstein Board -- capa intermediaria unificada.

Actúa como intermediario entre:
  - Yahboom_Board (0x26): 4 motores DC con encoder → clase Board
  - Hiwonder_Board (0x7A): LED RGB, buzzer, PWM servo, batería → módulo de funciones
  - Sonar ultrasónico (0x77): distancia en mm (driver propio)

Drivers exportados:
  FrankensteinMotorDriver   (delega en Yahboom_Board.Board)
  FrankensteinSonarDriver
  FrankensteinLedDriver     (delega en Hiwonder_Board)
  FrankensteinBuzzerDriver
  FrankensteinPwmServoDriver
  FrankensteinBatteryMonitor
  FrankensteinBoard        (facade que agrupa todos los anteriores)
"""

import sys
from typing import Dict, Optional

from smbus2 import SMBus, i2c_msg

# Integración Yahboom: clase Board para motores con encoder
try:
    from .Yahboom_Board import Board as YahboomBoard
except ImportError:
    try:
        import Yahboom_Board
        YahboomBoard = getattr(Yahboom_Board, "Board", None)
    except ImportError:
        YahboomBoard = None

# Integración HiWonder: módulo con LED, buzzer, servo PWM, batería
try:
    from . import Hiwonder_Board as _HwBoard
except ImportError:
    try:
        import Hiwonder_Board as _HwBoard
    except ImportError:
        _HwBoard = None


# ═══════════════════════════════════════════════════════════════════════════
# 1. Motor Driver — intermediario sobre Yahboom_Board.Board
# ═══════════════════════════════════════════════════════════════════════════
class FrankensteinMotorDriver:
    """Control de 4 motores DC con encoder. Delega en Yahboom_Board.Board."""

    # Rangos válidos: si se pasa, no se envía y se avisa
    SPEED_MIN, SPEED_MAX = -1000, 1000
    PWM_MIN, PWM_MAX = -3600, 3600

    def __init__(
        self,
        bus_num: int = 1,
        addr: int = 0x26,
        motor_type: Optional[int] = None,
    ) -> None:
        if YahboomBoard is None:
            raise RuntimeError("Yahboom_Board no disponible")
        self._yahboom = YahboomBoard(bus_num=int(bus_num), addr=addr)
        if motor_type is not None:
            self._yahboom.configure(motor_type=int(motor_type))

    def configure(self, motor_type: int = 3) -> None:
        self._yahboom.configure(motor_type=motor_type)

    def set_speed(self, m1: int = 0, m2: int = 0, m3: int = 0, m4: int = 0) -> None:
        vals = (m1, m2, m3, m4)
        for v in vals:
            if not (self.SPEED_MIN <= int(v) <= self.SPEED_MAX):
                sys.stderr.write(
                    "Motor: valor fuera de rango. Límite velocidad: {} a {}\n".format(
                        self.SPEED_MIN, self.SPEED_MAX
                    )
                )
                return
        self._yahboom.set_speed(m1, m2, m3, m4)

    def set_pwm(self, m1: int = 0, m2: int = 0, m3: int = 0, m4: int = 0) -> None:
        vals = (m1, m2, m3, m4)
        for v in vals:
            if not (self.PWM_MIN <= int(v) <= self.PWM_MAX):
                sys.stderr.write(
                    "Motor: valor fuera de rango. Límite PWM: {} a {}\n".format(
                        self.PWM_MIN, self.PWM_MAX
                    )
                )
                return
        self._yahboom.set_pwm(m1, m2, m3, m4)

    def stop(self) -> None:
        self._yahboom.stop()

    def read_encoder_10ms(self) -> Dict[int, int]:
        return self._yahboom.read_encoder_10ms()

    def read_encoder_total(self) -> Dict[int, int]:
        return self._yahboom.read_encoder_total()

    def scan(self) -> bool:
        return self._yahboom.scan()

    def shutdown(self) -> None:
        self._yahboom.close()

    def __repr__(self) -> str:
        return f"FrankensteinMotorDriver(backend=YahboomBoard, {self._yahboom!r})"


# ═══════════════════════════════════════════════════════════════════════════
# 2. Sonar Driver — propio (I2C 0x77, no pertenece a ninguna placa)
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
# 3–6. Drivers HiWonder — intermediarios sobre Hiwonder_Board
# ═══════════════════════════════════════════════════════════════════════════
class FrankensteinLedDriver:
    """Control de LEDs RGB WS2812. Delega en Hiwonder_Board."""

    NUM_PIXELS = 2

    def __init__(self) -> None:
        if _HwBoard is None:
            raise RuntimeError("Hiwonder_Board no disponible")

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


class FrankensteinBuzzerDriver:
    """Buzzer piezoeléctrico on/off. Delega en Hiwonder_Board."""

    def __init__(self) -> None:
        if _HwBoard is None:
            raise RuntimeError("Hiwonder_Board no disponible")

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


class FrankensteinPwmServoDriver:
    """Servo PWM. Delega en Hiwonder_Board (placa de expansión HiWonder)."""

    def __init__(self, channel: int = 1, center_pulse: int = 1500) -> None:
        if _HwBoard is None:
            raise RuntimeError("Hiwonder_Board no disponible")
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


class FrankensteinBatteryMonitor:
    """Lectura de voltaje de batería. Delega en Hiwonder_Board."""

    def __init__(self) -> None:
        if _HwBoard is None:
            raise RuntimeError("Hiwonder_Board no disponible")

    def get_voltage(self) -> float:
        return float(_HwBoard.getBattery()) / 1000.0


# ═══════════════════════════════════════════════════════════════════════════
# 7. Facade — agrupa todas las integraciones
# ═══════════════════════════════════════════════════════════════════════════
class FrankensteinBoard:
    """Facade: instancia los drivers que delegan en Yahboom_Board y Hiwonder_Board."""

    def __init__(
        self,
        bus_num: int = 1,
        motor_addr: int = 0x26,
        sonar_addr: int = 0x77,
        motor_type: int = 3,
        servo_channel: int = 1,
        servo_center: int = 1500,
    ) -> None:
        self.motor = FrankensteinMotorDriver(
            bus_num=bus_num, addr=motor_addr, motor_type=motor_type
        )
        self.sonar = FrankensteinSonarDriver(bus_num=bus_num, addr=sonar_addr)
        self.led = FrankensteinLedDriver()
        self.buzzer = FrankensteinBuzzerDriver()
        self.servo = FrankensteinPwmServoDriver(
            channel=servo_channel, center_pulse=servo_center
        )
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
