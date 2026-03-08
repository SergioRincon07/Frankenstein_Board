import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from turbopy_hw import LedDriver


class LedDriverNode(Node):
    """Nodo ROS2 que recibe comandos simples por /leds_cmd y controla los LEDs."""

    def __init__(self) -> None:
        super().__init__('turbopy_led_driver')

        try:
            self._led = LedDriver()
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f'No se pudo inicializar el driver de LEDs: {exc!r}')
            raise

        self._num_pixels = self.declare_parameter('num_pixels', 2).get_parameter_value().integer_value

        self._sub = self.create_subscription(
            String,
            'leds_cmd',
            self._on_cmd,
            10,
        )

        self.get_logger().info('turbopy_led_driver listo. Esperando en /leds_cmd (std_msgs/String).')

    # ------------------------------------------------------------------
    # Comandos
    # ------------------------------------------------------------------

    def _set_all(self, r: int, g: int, b: int) -> None:
        for i in range(self._num_pixels):
            self._led.set_pixel(i, r, g, b)
        self._led.show()

    def _on_cmd(self, msg: String) -> None:
        cmd = msg.data.strip().lower()

        if cmd in ('off', 'apagar', 'none'):  # apagar
            self._led.clear()
            return

        if cmd in ('red', 'rojo'):
            self._set_all(255, 0, 0)
        elif cmd in ('green', 'verde'):
            self._set_all(0, 255, 0)
        elif cmd in ('blue', 'azul'):
            self._set_all(0, 0, 255)
        elif cmd in ('yellow', 'amarillo'):
            self._set_all(255, 255, 0)
        elif cmd in ('white', 'blanco'):
            self._set_all(255, 255, 255)
        else:
            self.get_logger().warn(f'Comando de LED no reconocido: {cmd!r}')


def main(args=None) -> None:  # noqa: D401
    rclpy.init(args=args)
    node = LedDriverNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
