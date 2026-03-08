#!/usr/bin/env python3
"""Test standalone: sweep del servo PWM (low -> high -> center)."""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
