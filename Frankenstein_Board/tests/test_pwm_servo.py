#!/usr/bin/env python3
"""Test standalone: sweep del servo PWM (low -> high -> center). Requiere sudo (acceso I2C/GPIO)."""

import sys, os, time

if os.geteuid() != 0:
    print("Este test necesita acceso a hardware. Ejecuta con: sudo python3 ...")
    sys.exit(1)

# Raíz del repo (contiene la carpeta Frankenstein_Board/)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from Frankenstein_Board.board import FrankensteinPwmServoDriver

CHANNEL = 1
LOW, CENTER, HIGH = 1100, 1500, 1900
DURATION_MS = 400
HOLD = 0.5

servo = FrankensteinPwmServoDriver(channel=CHANNEL, center_pulse=CENTER)
try:
    servo.set_pulse(LOW, DURATION_MS)
    print(f"  Pulso bajo: {LOW} us")
    time.sleep(HOLD)

    servo.set_pulse(HIGH, DURATION_MS)
    print(f"  Pulso alto: {HIGH} us")
    time.sleep(HOLD)

    servo.center(DURATION_MS)
    print(f"  Centro: {CENTER} us")
    time.sleep(HOLD)

    print("PASS | Sweep completado")
except Exception as exc:
    print(f"FAIL | {exc!r}")
    sys.exit(1)
finally:
    servo.shutdown()
