"""
Hardware drivers for TurboPi robot.

This module provides simple, direct access to the TurboPi hardware components:
- Motors (4-wheel drive)
- RGB LEDs
- Buzzer
- Battery monitoring

All classes interface directly with HiwonderSDK.Board module.
"""

import os
import sys

# Add HiwonderSDK to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import HiwonderSDK.Board as Board
from HiwonderSDK.Mecanum import MecanumChassis

class ChachisMecanum:
    """Wrapper para controlar el chassis Mecanum del TurboPi.
    
    Proporciona una interfaz simplificada que convierte velocidades normalizadas
    [-1.0, 1.0] a velocidades físicas en mm/s que espera MecanumChassis.
    
    Soporta tanto coordenadas polares (velocidad + dirección + rotación)
    como coordenadas cartesianas (velocity_x, velocity_y).
    
    Args:
        max_speed: Velocidad máxima en mm/s (default: 100)
    
    Example:
        >>> chassis = ChachisMecanum(max_speed=100)
        >>> chassis.translation(0.5, 0.0)  # Mueve a la derecha al 50%
        >>> chassis.set_velocity(50, 90, 0)  # 50mm/s hacia adelante (90°)
    """

    def __init__(self, max_speed: int = 100):
        """Initialize mecanum chassis wrapper.
        
        Args:
            max_speed: Velocidad máxima en mm/s (1-200 recomendado)
        """
        self.max_speed = max(1, int(max_speed))
        try:
            self._chassis = MecanumChassis()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f'No se pudo inicializar MecanumChassis: {exc!r}') from exc

    def set_velocity(self, velocity, direction, angular_rate, fake=False):
        """Control del chassis usando coordenadas polares.
        
        Args:
            velocity: Velocidad normalizada [-1.0, 1.0] de traslación
            direction: Dirección en grados (0-360°)
                      0° = derecha, 90° = adelante, 180° = izquierda, 270° = atrás
            angular_rate: Velocidad angular normalizada [-1.0, 1.0]
                         Positivo = giro horario, Negativo = antihorario
            fake: Si True, solo calcula sin enviar comandos al hardware
        """
        # Convertir velocidad normalizada a mm/s
        velocity_mms = velocity * self.max_speed
        
        # Enviar comando al chassis de bajo nivel
        self._chassis.set_velocity(velocity_mms, direction, angular_rate, fake)

    def translation(self, velocity_x, velocity_y, fake=False):
        """Control del chassis usando coordenadas cartesianas.
        
        Args:
            velocity_x: Velocidad normalizada en X [-1.0, 1.0]
                       Positivo = derecha, Negativo = izquierda
            velocity_y: Velocidad normalizada en Y [-1.0, 1.0]
                       Positivo = adelante, Negativo = atrás
            fake: Si True, solo calcula sin enviar comandos al hardware
        
        Example:
            >>> chassis.translation(0.0, 1.0)  # Adelante 100%
            >>> chassis.translation(0.5, 0.5)  # Diagonal 45° adelante-derecha
            >>> chassis.translation(-1.0, 0.0) # Lateral izquierda 100%
        """
        # Clamp velocities to valid range
        velocity_x = max(-1.0, min(1.0, velocity_x))
        velocity_y = max(-1.0, min(1.0, velocity_y))
        
        # Convert to hardware speed values (mm/s)
        velocity_x_mms = velocity_x * self.max_speed
        velocity_y_mms = velocity_y * self.max_speed

        # Send command to hardware
        self._chassis.translation(velocity_x_mms, velocity_y_mms, fake)


class MotorDriver:
    """Control Indepedniente the 4 motors of the TurboPi robot.
    
    Uses HiwonderSDK.Board.setMotor() to control motor speeds.
    Speed values are normalized to [-1.0, 1.0] range.
    
    Args:
        max_speed: Maximum speed value sent to hardware (default: 100)
    
    Example:
        >>> motors = MotorDriver()
        >>> motors.set_motor_speed(1, 0.5)  # Motor 1 at 50% forward
        >>> motors.set_motor_speed(2, -0.3) # Motor 2 at 30% backward
        >>> motors.stop_all()  # Stop all motors
    """

    def __init__(self, max_speed: int = 100):
        """Initialize motor driver.
        
        Args:
            max_speed: Maximum speed value (1-100)
        """
        if Board is None:
            raise RuntimeError("HiwonderSDK.Board not available")
        self.max_speed = max(1, int(max_speed))

    def set_motor_speed(self, motor_id: int, speed: float) -> None:
        """Set speed for a specific motor.
        
        Args:
            motor_id: Motor ID (1-4)
            speed: Normalized speed [-1.0, 1.0]
                  -1.0 = full backward
                   0.0 = stop
                   1.0 = full forward
        """
        # Clamp speed to valid range
        speed = max(-1.0, min(1.0, speed))
        
        # Convert to hardware speed value
        hw_speed = int(speed * self.max_speed)
        
        # Send command to hardware
        Board.setMotor(motor_id, hw_speed)

    def stop_all(self) -> None:
        """Stop all 4 motors immediately."""
        for motor_id in (1, 2, 3, 4):
            Board.setMotor(motor_id, 0)


class LedDriver:
    """Controls RGB LEDs on the TurboPi robot.
    
    The robot has 2 RGB LEDs that can display any color.
    Uses HiwonderSDK.Board.RGB for LED control.
    
    Example:
        >>> leds = LedDriver()
        >>> leds.set_pixel(0, 255, 0, 0)  # LED 0 red
        >>> leds.set_pixel(1, 0, 0, 255)  # LED 1 blue
        >>> leds.show()  # Update LEDs
        >>> leds.clear()  # Turn off all LEDs
    """

    def __init__(self):
        """Initialize LED driver."""
        if Board is None:
            raise RuntimeError("HiwonderSDK.Board not available")

    def set_pixel(self, index: int, r: int, g: int, b: int) -> None:
        """Set color for a specific LED pixel.
        
        Args:
            index: LED index (0 or 1)
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)
        """
        # Clamp RGB values
        r = max(0, min(255, int(r)))
        g = max(0, min(255, int(g)))
        b = max(0, min(255, int(b)))
        
        # Set pixel color
        Board.RGB.setPixelColor(index, Board.PixelColor(r, g, b))

    def show(self) -> None:
        """Update LEDs with buffered colors.
        
        Call this after set_pixel() to apply changes.
        """
        Board.RGB.show()

    def clear(self) -> None:
        """Turn off all LEDs."""
        for i in (0, 1):
            Board.RGB.setPixelColor(i, Board.PixelColor(0, 0, 0))
        Board.RGB.show()


class BuzzerDriver:
    """Controls the buzzer on the TurboPi robot.
    
    Simple on/off control for the piezo buzzer.
    Uses HiwonderSDK.Board.setBuzzer().
    
    Example:
        >>> buzzer = BuzzerDriver()
        >>> buzzer.on()   # Turn buzzer on
        >>> buzzer.off()  # Turn buzzer off
    """

    def __init__(self):
        """Initialize buzzer driver."""
        if Board is None:
            raise RuntimeError("HiwonderSDK.Board not available")

    def set_state(self, on: bool) -> None:
        """Set buzzer state.
        
        Args:
            on: True to turn on, False to turn off
        """
        Board.setBuzzer(1 if on else 0)

    def on(self) -> None:
        """Turn buzzer on."""
        self.set_state(True)

    def off(self) -> None:
        """Turn buzzer off."""
        self.set_state(False)


class BatteryMonitor:
    """Monitors battery voltage on the TurboPi robot.
    
    Reads battery voltage from HiwonderSDK.Board.getBattery().
    The SDK returns voltage in millivolts (mV).
    
    Example:
        >>> battery = BatteryMonitor()
        >>> voltage = battery.get_voltage()  # Returns voltage in volts
        >>> print(f"Battery: {voltage:.2f}V")
    """

    def __init__(self):
        """Initialize battery monitor."""
        if Board is None:
            raise RuntimeError("HiwonderSDK.Board not available")

    def get_voltage(self) -> float:
        """Read current battery voltage.
        
        Returns:
            Battery voltage in volts (V)
        """
        # SDK returns millivolts
        millivolts = float(Board.getBattery())
        
        # Convert to volts
        return millivolts / 1000.0
