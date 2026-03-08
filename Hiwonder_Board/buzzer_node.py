import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool

from turbopy_hw import BuzzerDriver


class BuzzerDriverNode(Node):
    """Nodo ROS2 que controla el buzzer a partir de /buzzer_cmd (Bool)."""

    def __init__(self) -> None:
        super().__init__('turbopy_buzzer_driver')

        try:
            self._buzzer = BuzzerDriver()
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f'No se pudo inicializar el driver de buzzer: {exc!r}')
            raise

        self._sub = self.create_subscription(
            Bool,
            'buzzer_cmd',
            self._on_cmd,
            10,
        )

        self.get_logger().info('turbopy_buzzer_driver listo. Esperando en /buzzer_cmd (std_msgs/Bool).')

    def _on_cmd(self, msg: Bool) -> None:
        self._buzzer.set_state(bool(msg.data))


def main(args=None) -> None:  # noqa: D401
    rclpy.init(args=args)
    node = BuzzerDriverNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
