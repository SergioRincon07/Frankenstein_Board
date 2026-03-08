#!/usr/bin/env python3
"""
Test del sonar en bucle: muestra distancia actual, mín y máx.
Detener con Ctrl+C.
"""

import sys
import os
import time
import signal

# Raíz del repo (contiene la carpeta Frankenstein_Board/)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from Frankenstein_Board.board import FrankensteinSonarDriver

DELAY_S = 0.2
# El driver limita lecturas inválidas/error a MAX_RANGE_MM (5000 mm = 500 cm). No contar eso como lectura real.
MAX_VALID_MM = 4999  # por debajo del techo del driver

# Si no superas ~10 cm, revisa:
# - Dirección I2C del sensor (por defecto 0x77). Comprueba con: i2cdetect -y 1
# - Algunos sensores I2C devuelven la distancia en cm en 1 byte; leer 2 bytes puede dar valores raros
# - Cables y alimentación del sensor
# - Que no haya obstáculos fijos cerca (mínimo típico ~2–3 cm)

def main():
    sonar = FrankensteinSonarDriver()
    d_min = None
    d_max = None
    n = 0

    def on_stop(sig, frame):
        print("\n\n--- Detenido con Ctrl+C ---")
        if d_min is not None and d_max is not None:
            print(f"  Mín: {d_min} mm ({d_min/10:.1f} cm)")
            print(f"  Máx: {d_max} mm ({d_max/10:.1f} cm)")
            print(f"  Muestras: {n}")
        sonar.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, on_stop)
    print("Sonar en bucle (mín/máx). Ctrl+C para parar.\n")

    try:
        while True:
            d_mm = sonar.get_distance_mm()
            n += 1

            if 0 <= d_mm <= MAX_VALID_MM:
                if d_min is None or d_mm < d_min:
                    d_min = d_mm
                if d_max is None or d_mm > d_max:
                    d_max = d_mm

            d_cm = d_mm / 10.0
            min_str = f"{d_min/10:.1f} cm" if d_min is not None else "—"
            max_str = f"{d_max/10:.1f} cm" if d_max is not None else "—"
            print(f"  [{n:5d}] {d_mm:5d} mm ({d_cm:6.1f} cm)  |  mín: {min_str}  máx: {max_str}", end="\r")

            time.sleep(DELAY_S)
    finally:
        sonar.shutdown()

if __name__ == "__main__":
    main()
