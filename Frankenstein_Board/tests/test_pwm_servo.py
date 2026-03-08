#!/usr/bin/env python3
"""
Test interactivo: control manual de 2 servos PWM con flechas.
  - Tecla 1 o 2: seleccionar servo
  - Flecha izquierda/derecha: bajar/subir pulso (si la mantienes, sigue moviendo)
  - q: salir (vuelve a centro)

Requiere sudo y ejecutar en una terminal (no en IDE). Ej: sudo python3 test_pwm_servo.py
"""

import sys
import os

if os.geteuid() != 0:
    print("Necesita acceso a hardware. Ejecuta con: sudo python3 ...")
    sys.exit(1)

# Raíz del repo
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from Frankenstein_Board.board import FrankensteinPwmServoDriver

# Rango físico (HiWonder 500–2500 us)
PULSE_ABS_MIN = 500
PULSE_ABS_MAX = 2500
CENTER_US = 1500
STEP_US = 30
DURATION_MS = 200

# Límites por servo (min_us, max_us). Calibrados:
#   servo 1: 2500 - 560 | 1500 centro
#   servo 2: 1830 - 1000 | 1500 centro
SERVO1_LIMITS = (560, 2500)
SERVO2_LIMITS = (1000, 1830)


def clamp_pulse(servo_id: int, pulse: int) -> int:
    limits = SERVO1_LIMITS if servo_id == 1 else SERVO2_LIMITS
    pulse = max(PULSE_ABS_MIN, min(PULSE_ABS_MAX, int(pulse)))
    if limits is not None:
        lo, hi = limits
        pulse = max(lo, min(hi, pulse))
    return pulse


def run(stdscr):
    import curses

    curses.curs_set(0)
    stdscr.nodelay(0)
    stdscr.keypad(True)

    servo1 = FrankensteinPwmServoDriver(channel=1, center_pulse=CENTER_US)
    servo2 = FrankensteinPwmServoDriver(channel=2, center_pulse=CENTER_US)
    pos = {1: CENTER_US, 2: CENTER_US}
    selected = 1

    def set_servo(servo_id: int, pulse_us: int):
        pulse_us = clamp_pulse(servo_id, pulse_us)
        pos[servo_id] = pulse_us
        s = servo1 if servo_id == 1 else servo2
        s.set_pulse(pulse_us, DURATION_MS)
        return pulse_us

    # Centrar al empezar
    set_servo(1, CENTER_US)
    set_servo(2, CENTER_US)

    def draw():
        stdscr.erase()
        h, w = stdscr.getmaxyx()
        stdscr.addstr(0, 0, "  [1] [2] = elegir servo   <-- --> = pulso   [q] = salir")
        stdscr.addstr(1, 0, "  Servo activo: {}".format(selected))
        stdscr.addstr(2, 0, "  Servo 1: {:4d} us   Servo 2: {:4d} us".format(pos[1], pos[2]))
        if SERVO1_LIMITS or SERVO2_LIMITS:
            stdscr.addstr(3, 0, "  Limites S1={}  S2={}".format(SERVO1_LIMITS, SERVO2_LIMITS))
        stdscr.refresh()

    draw()

    while True:
        try:
            key = stdscr.getch()
        except curses.error:
            continue

        if key in (ord("q"), ord("Q")):
            break

        if key == ord("1"):
            selected = 1
            draw()
            continue
        if key == ord("2"):
            selected = 2
            draw()
            continue

        if key == curses.KEY_LEFT:
            set_servo(selected, pos[selected] - STEP_US)
            draw()
            continue
        if key == curses.KEY_RIGHT:
            set_servo(selected, pos[selected] + STEP_US)
            draw()
            continue

    # Salir: centrar y cerrar
    servo1.center(DURATION_MS)
    servo2.center(DURATION_MS)
    servo1.shutdown()
    servo2.shutdown()


def main():
    try:
        import curses
    except ImportError:
        print("Se necesita el modulo 'curses'. Ejecuta este script en una terminal con: sudo python3 test_pwm_servo.py")
        sys.exit(1)

    try:
        curses.wrapper(run)
    except Exception as e:
        print("Error:", e)
        sys.exit(1)

    print("Salida. Posicion final en el script (centro = {} us).".format(CENTER_US))
    print("Cuando tengas minimo y maximo de cada servo, edita SERVO1_LIMITS y SERVO2_LIMITS en el script.")


if __name__ == "__main__":
    main()