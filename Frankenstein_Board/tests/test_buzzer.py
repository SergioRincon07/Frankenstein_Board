#!/usr/bin/env python3
"""Test standalone: 3 beeps cortos."""

import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Frankenstein_Board.board import FrankensteinBuzzerDriver

BEEPS = 3
ON_TIME = 0.2

buzzer = FrankensteinBuzzerDriver()
try:
    for i in range(BEEPS):
        buzzer.on()
        time.sleep(ON_TIME)
        buzzer.off()
        time.sleep(ON_TIME)
    print(f"PASS | {BEEPS} beeps completados")
except Exception as exc:
    print(f"FAIL | {exc!r}")
    sys.exit(1)
finally:
    buzzer.shutdown()
