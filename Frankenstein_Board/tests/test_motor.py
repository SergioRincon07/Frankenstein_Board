#!/usr/bin/env python3
"""
Test interactivo: control de los 4 motores con flechas.
  - [m]: alternar modo   [s]: velocidad   [p]: PWM
  - Velocidad: -1000 a 1000   PWM: -3600 a 3600
  - Flecha arriba/abajo: subir/bajar valor (los 4 motores igual; si mantienes, sigue)
  - En pantalla: lectura de encoders (10 ms y total) por motor
  - [q]: salir (para motores)

Requiere sudo. Ejecutar en terminal: sudo python3 test_motor.py
"""

import sys
import os

if os.geteuid() != 0:
    print("Necesita acceso a hardware. Ejecuta con: sudo python3 ...")
    sys.exit(1)

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from Frankenstein_Board.board import FrankensteinMotorDriver

# Rangos (deben coincidir con board.py)
SPEED_MIN, SPEED_MAX = FrankensteinMotorDriver.SPEED_MIN, FrankensteinMotorDriver.SPEED_MAX
PWM_MIN, PWM_MAX = FrankensteinMotorDriver.PWM_MIN, FrankensteinMotorDriver.PWM_MAX

STEP_SPEED = 50
STEP_PWM = 150
MOTOR_TYPE = 3


def run(stdscr):
    import curses

    curses.curs_set(0)
    stdscr.keypad(True)
    stdscr.timeout(200)  # actualizar encoders cada 200 ms aunque no haya tecla

    driver = FrankensteinMotorDriver(motor_type=MOTOR_TYPE)
    if not driver.scan():
        stdscr.addstr(0, 0, "ERROR: Placa motor no responde (I2C 0x26). [q] salir.")
        stdscr.refresh()
        while stdscr.getch() not in (ord("q"), ord("Q")):
            pass
        return

    # modo: "speed" o "pwm"
    mode = "speed"
    value = 0  # valor actual (velocidad o pwm según modo)

    def apply():
        if mode == "speed":
            driver.set_speed(value, value, value, value)
        else:
            # La placa puede priorizar velocidad: poner a 0 para que use el PWM
            driver.set_speed(0, 0, 0, 0)
            driver.set_pwm(value, value, value, value)

    def draw():
        stdscr.erase()
        lo, hi = (SPEED_MIN, SPEED_MAX) if mode == "speed" else (PWM_MIN, PWM_MAX)
        stdscr.addstr(0, 0, "  [m] modo: {}   [Arriba/Abajo] valor   [q] salir".format(
            "VELOCIDAD" if mode == "speed" else "PWM (m=volver)"))
        stdscr.addstr(1, 0, "  Rango: {} a {}   Valor actual: {}".format(lo, hi, value))
        stdscr.addstr(2, 0, "  Los 4 motores reciben el mismo valor.")
        try:
            enc_10 = driver.read_encoder_10ms()
            enc_line = "  Encoder (10ms):  M1={:6d}  M2={:6d}  M3={:6d}  M4={:6d}".format(
                enc_10.get(1, 0), enc_10.get(2, 0), enc_10.get(3, 0), enc_10.get(4, 0))
            stdscr.addstr(3, 0, enc_line)
            tot = driver.read_encoder_total()
            tot_line = "  Encoder (total): M1={:8d}  M2={:8d}  M3={:8d}  M4={:8d}".format(
                tot.get(1, 0), tot.get(2, 0), tot.get(3, 0), tot.get(4, 0))
            stdscr.addstr(4, 0, tot_line)
        except Exception:
            stdscr.addstr(3, 0, "  Encoder: (error al leer)")
        stdscr.refresh()

    draw()

    while True:
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1
        if key == -1:
            draw()  # timeout: solo refrescar encoders
            continue

        if key in (ord("q"), ord("Q")):
            break

        # [m] alterna entre VELOCIDAD y PWM; [s]=velocidad, [p]=PWM directo
        if key in (ord("m"), ord("M"), ord("s"), ord("S"), ord("p"), ord("P")):
            driver.stop()
            if key in (ord("p"), ord("P")):
                mode = "pwm"
                value = 0
            elif key in (ord("s"), ord("S")):
                mode = "speed"
                value = 0
            else:
                # [m]: alternar
                mode = "pwm" if mode == "speed" else "speed"
                value = 0
            draw()
            continue

        if key == curses.KEY_UP:
            step = STEP_SPEED if mode == "speed" else STEP_PWM
            hi = SPEED_MAX if mode == "speed" else PWM_MAX
            value = min(hi, value + step)
            apply()
            draw()
            continue

        if key == curses.KEY_DOWN:
            step = STEP_SPEED if mode == "speed" else STEP_PWM
            lo = SPEED_MIN if mode == "speed" else PWM_MIN
            value = max(lo, value - step)
            apply()
            draw()
            continue

    driver.stop()
    driver.shutdown()


def main():
    try:
        import curses
    except ImportError:
        print("Se necesita el modulo 'curses'. Ejecuta en terminal: sudo python3 test_motor.py")
        sys.exit(1)

    try:
        curses.wrapper(run)
    except Exception as e:
        print("Error:", e)
        sys.exit(1)

    print("Motores parados.")


if __name__ == "__main__":
    main()
