#!/usr/bin/env python3
"""Test standalone: gira cada motor 1 s y lee encoder."""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Frankenstein_Board.board import FrankensteinMotorDriver

MOTOR_TYPE = 3
TEST_SPEED = 400
RUN_SECONDS = 1.0

driver = FrankensteinMotorDriver(motor_type=MOTOR_TYPE)
try:
    if not driver.scan():
        print("FAIL | Motor board no responde en I2C 0x26")
        sys.exit(1)

    for mid in (1, 2, 3, 4):
        args = {"m1": 0, "m2": 0, "m3": 0, "m4": 0}
        args[f"m{mid}"] = TEST_SPEED
        driver.set_speed(**args)
        time.sleep(RUN_SECONDS)
        enc = driver.read_encoder_10ms()
        driver.stop()
        print(f"  Motor {mid}: encoder_10ms = {enc.get(mid, 0)}")
        time.sleep(0.2)

    print("PASS | Todos los motores giraron")
except Exception as exc:
    print(f"FAIL | {exc!r}")
    sys.exit(1)
finally:
    driver.shutdown()
