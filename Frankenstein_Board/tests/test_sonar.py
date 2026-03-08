#!/usr/bin/env python3
"""Test standalone: 5 lecturas de distancia del sonar."""

import sys, os, time
# Raíz del repo (contiene la carpeta Frankenstein_Board/)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from Frankenstein_Board.board import FrankensteinSonarDriver

SAMPLES = 5
DELAY = 0.2

sonar = FrankensteinSonarDriver()
try:
    values = []
    for i in range(SAMPLES):
        d = sonar.get_distance_mm()
        values.append(d)
        print(f"  Muestra {i+1}: {d} mm ({sonar.get_distance_cm():.1f} cm)")
        time.sleep(DELAY)

    valid = [v for v in values if 0 < v <= sonar.MAX_RANGE_MM]
    if not valid:
        print(f"FAIL | Sin lecturas válidas: {values}")
        sys.exit(1)

    avg = sum(valid) / len(valid)
    print(f"PASS | Promedio: {avg:.1f} mm ({avg/10:.1f} cm)")
except Exception as exc:
    print(f"FAIL | {exc!r}")
    sys.exit(1)
finally:
    sonar.shutdown()
