#!/usr/bin/env python3
"""Test standalone: 3 beeps cortos."""

import sys, os, time
# Raíz del repo (contiene la carpeta Frankenstein_Board/)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

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
