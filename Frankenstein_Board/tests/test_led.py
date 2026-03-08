#!/usr/bin/env python3
"""Test standalone: ciclo de colores en los 2 LEDs RGB. Requiere sudo (acceso GPIO /dev/mem)."""

import sys, os, time

if os.geteuid() != 0:
    print("Este test necesita acceso a GPIO. Ejecuta con: sudo python3 ...")
    sys.exit(1)

# Raíz del repo (contiene la carpeta Frankenstein_Board/)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from Frankenstein_Board.board import FrankensteinLedDriver

STEP = 0.4
COLORS = [
    ("rojo",    255, 0,   0),
    ("verde",   0,   255, 0),
    ("azul",    0,   0,   255),
    ("blanco",  255, 255, 255),
    ("apagado", 0,   0,   0),
]

led = FrankensteinLedDriver()
try:
    for name, r, g, b in COLORS:
        for i in range(led.NUM_PIXELS):
            led.set_pixel(i, r, g, b)
        led.show()
        print(f"  {name}")
        time.sleep(STEP)
    print("PASS | Secuencia RGB completada")
except Exception as exc:
    print(f"FAIL | {exc!r}")
    sys.exit(1)
finally:
    led.shutdown()
