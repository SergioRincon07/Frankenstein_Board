# Frankenstein Board

Board unificada: control de motores (Yahboom/Janbun) + periféricos HiWonder (buzzer, LED, PWM servo, sonar, batería). Este documento define la API, las direcciones de cada placa y cómo ejecutar los tests.

---

## 1) Direcciones de cada placa

Todas las placas comparten el **bus I2C 1** en la Raspberry Pi (por defecto). Algunos periféricos usan GPIO.

| Placa / periférico | Dirección | Bus | Acceso | Notas |
|--------------------|-----------|-----|--------|--------|
| **Yahboom / Janbun (motores)** | `0x26` | 1 | I2C | 4 motores DC + encoders |
| **Sonar ultrasónico** | `0x77` | 1 | I2C | Distancia en mm (reg 0x00, 2 bytes) |
| **HiWonder expansión** | `0x7A` | 1 | I2C | Batería (reg 0), PWM servo (reg 40) |
| **LED RGB (WS2812)** | — | — | GPIO 12 | 2 píxeles, vía HiwonderSDK |
| **Buzzer** | — | — | GPIO 31 | On/off, vía HiwonderSDK |

### Registros I2C — Placa de motores (0x26)

| Reg | Nombre | R/W | Tamaño | Uso |
|-----|--------|-----|--------|-----|
| 0x01 | MOTOR_TYPE | W | 1 B | Tipo de motor (1–5) |
| 0x02 | DEADZONE | W | 2 B | Zona muerta uint16 |
| 0x03 | PULSE_LINE | W | 2 B | Líneas encoder uint16 |
| 0x04 | PULSE_PHASE | W | 2 B | Reducción uint16 |
| 0x05 | WHEEL_DIA | W | 4 B | Diámetro rueda mm (float LE) |
| 0x06 | SPEED | W | 8 B | Velocidad M1–M4 (4× int16, -1000..1000) |
| 0x07 | PWM | W | 8 B | PWM M1–M4 (4× int16, -3600..3600) |
| 0x10–0x13 | ENC_10MS | R | 2 B c/u | Encoder 10 ms M1–M4 |
| 0x20–0x27 | ENC_ALL | R | 4 B por motor | Encoder total M1–M4 (high+low) |

### Registros I2C — Sonar (0x77)

| Reg | Uso | R/W | Tamaño |
|-----|-----|-----|--------|
| 0x00 | Distancia en mm | W+RD | 2 B (uint16 LE), máx. 5000 |

### HiWonder (0x7A) — vía HiwonderSDK

- **Reg 0**: lectura batería (2 B, mV).
- **Reg 40**: comando servo PWM (tiempo + canal + pulso en µs).
- LED y buzzer se controlan por GPIO (12 y 31), no por I2C.

### Comprobar direcciones desde la terminal (Raspberry Pi)

```bash
sudo apt install i2c-tools   # si no está instalado
sudo i2cdetect -y 1          # lista dispositivos en bus 1 (deberías ver 26, 77, 7a)
```

---

## 2) Drivers y contrato mínimo

### `FrankensteinMotorDriver`
- `scan() -> bool`
- `configure(motor_type: int) -> None`
- `set_speed(m1, m2, m3, m4) -> None` (rango: `-1000..1000`)
- `set_pwm(m1, m2, m3, m4) -> None` (rango: `-3600..3600`)
- `read_encoder_10ms() -> Dict[int, int]`
- `read_encoder_total() -> Dict[int, int]`
- `stop() -> None`
- `shutdown() -> None`

### `FrankensteinLedDriver`
- `set_pixel(index, r, g, b) -> None`
- `show() -> None`
- `clear() -> None`
- `shutdown() -> None`

### `FrankensteinBuzzerDriver`
- `set_state(on: bool) -> None`
- `on() -> None`
- `off() -> None`
- `shutdown() -> None`

### `FrankensteinSonarDriver`
- `get_distance_mm() -> int`
- `get_distance_cm() -> float`
- `shutdown() -> None`

### `FrankensteinPwmServoDriver`
- `set_pulse(pulse: int, duration_ms: int) -> None`
- `center(duration_ms: int) -> None`
- `shutdown() -> None`

---

## 3) Cómo correr los tests

Desde la **raíz del repositorio** (carpeta `Frankenstein_Board` que contiene `Frankenstein_Board/` y `tests/`).

### Tests standalone (sin ROS2)

Requieren acceso a I2C/GPIO, por eso se ejecutan con `sudo`:

```bash
cd /ruta/a/Frankenstein_Board

# Motor: gira cada rueda 1 s y muestra encoder
sudo python3 tests/test_motor.py

# Buzzer: 3 beeps
sudo python3 tests/test_buzzer.py

# LED: ciclo rojo / verde / azul / blanco / apagado
sudo python3 tests/test_led.py

# Sonar: 5 lecturas de distancia
sudo python3 tests/test_sonar.py

# PWM servo: barrido bajo / alto / centro
sudo python3 tests/test_pwm_servo.py
```

Cada script imprime `PASS | ...` o `FAIL | ...` y hace shutdown seguro al terminar.

### Tests con nodos ROS2

Con ROS2 y el workspace configurado (source del overlay):

```bash
# En terminales separadas, desde la raíz del repo:
python3 Frankenstein_Board/motor_test_node.py
python3 Frankenstein_Board/led_test_node.py
python3 Frankenstein_Board/buzzer_test_node.py
python3 Frankenstein_Board/sonar_test_node.py
python3 Frankenstein_Board/pwm_servo_test_node.py
```

Para lanzar una prueba por comando (publicar en el tópico de comando):

```bash
ros2 topic pub --once /frankenstein/test_command std_msgs/msg/String "{data: motor}"
ros2 topic pub --once /frankenstein/test_command std_msgs/msg/String "{data: led}"
ros2 topic pub --once /frankenstein/test_command std_msgs/msg/String "{data: buzzer}"
ros2 topic pub --once /frankenstein/test_command std_msgs/msg/String "{data: sonar}"
ros2 topic pub --once /frankenstein/test_command std_msgs/msg/String "{data: pwm}"
```

Resultados en: `/frankenstein/test_result` (formato `modulo|PASS|detalle` o `modulo|FAIL|detalle`).

---

## 4) Convenciones para migración C++

- Usar nombres y firmas equivalentes a Python.
- Cierre seguro: motor `stop()` antes de cerrar; LED `clear()`; buzzer `off()`; servo `center()`.
- Encoders: ventana 10 ms y acumulado total como lecturas separadas.
- Evitar mapeo físico en el driver; dejarlo en nodo de test o aplicación.

---

## 5) Protocolo ROS2 de orquestación

- **Comando:** `/frankenstein/test_command` (`std_msgs/String`)
- **Resultado:** `/frankenstein/test_result` (`std_msgs/String`)
- **Valores de comando:** `motor`, `led`, `buzzer`, `sonar`, `pwm` (o `all` para el que lo soporte)
