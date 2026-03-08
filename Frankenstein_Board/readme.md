# Frankenstein Board: contrato de portabilidad (Python -> C++)

Este documento define una API mínima estable para poder portar la capa de pruebas de Python a C++ sin cambiar la lógica de alto nivel.

## 1) Drivers y contrato mínimo

### `FrankensteinMotorDriver`
- `scan() -> bool`
- `configure(motor_type: int) -> None`
- `set_speed(m1: int, m2: int, m3: int, m4: int) -> None` (rango esperado: `-1000..1000`)
- `set_pwm(m1: int, m2: int, m3: int, m4: int) -> None` (rango esperado: `-3600..3600`)
- `read_encoder_10ms() -> Dict[int, int]`
- `read_encoder_total() -> Dict[int, int]`
- `stop() -> None`
- `shutdown() -> None`

### `FrankensteinLedDriver`
- `set_pixel(index: int, r: int, g: int, b: int) -> None`
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

## 2) Convenciones para migración C++

- Usar nombres y firmas equivalentes a Python.
- Mantener el patrón de cierre seguro:
  - Motor -> `stop()` antes de cerrar.
  - LED -> `clear()` antes de cerrar.
  - Buzzer -> `off()` antes de cerrar.
  - Servo -> `center()` antes de cerrar.
- Encoders:
  - Ventana corta (`10ms`) y acumulado (`total`) como lecturas separadas.
- Evitar lógica de mapeo físico dentro del driver base; mantenerla en el nodo de test o capa de aplicación.

## 3) Protocolo ROS2 de orquestación

Tópicos recomendados:
- Comando: `/frankenstein/test_command` (`std_msgs/String`)
- Resultado: `/frankenstein/test_result` (`std_msgs/String`)

Formato de resultado:
- `modulo|PASS|detalle`
- `modulo|FAIL|detalle`

Módulos esperados:
- `motor`, `led`, `buzzer`, `sonar`, `pwm`

## 4) Nodos de test actuales

- `frankenstein_motor_test_node.py`
- `frankenstein_led_test_node.py`
- `frankenstein_buzzer_test_node.py`
- `frankenstein_sonar_test_node.py`
- `frankenstein_pwm_servo_test_node.py`
- `frankenstein_test_orchestrator_node.py`

## 5) Ejecución rápida (referencia)

Terminales separadas:
- `python3 Frankenstein_Board/frankenstein_motor_test_node.py`
- `python3 Frankenstein_Board/frankenstein_led_test_node.py`
- `python3 Frankenstein_Board/frankenstein_buzzer_test_node.py`
- `python3 Frankenstein_Board/frankenstein_sonar_test_node.py`
- `python3 Frankenstein_Board/frankenstein_pwm_servo_test_node.py`
- `python3 Frankenstein_Board/frankenstein_test_orchestrator_node.py`

Prueba manual por comando:
- `ros2 topic pub --once /frankenstein/test_command std_msgs/msg/String "{data: motor}"`
- `ros2 topic pub --once /frankenstein/test_command std_msgs/msg/String "{data: led}"`
- `ros2 topic pub --once /frankenstein/test_command std_msgs/msg/String "{data: buzzer}"`
- `ros2 topic pub --once /frankenstein/test_command std_msgs/msg/String "{data: sonar}"`
- `ros2 topic pub --once /frankenstein/test_command std_msgs/msg/String "{data: pwm}"`
