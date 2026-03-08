import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import BatteryState

from turbopy_hw import MotorDriver, BatteryMonitor, ChachisMecanum


class BaseDriverNode(Node):
    """Driver de base simple para TurboPi.

    - Suscribe a /cmd_vel (geometry_msgs/Twist).
    - Controla los motores vía turbopy_hw.
    - Publica /battery (sensor_msgs/BatteryState).

    NOTA: La cinemática aquí es muy básica (todos los motores igual según
    linear.x). Más adelante se puede sustituir por un modelo de Mecanum
    completo reutilizando la misma interfaz de motor.
    """

    def __init__(self) -> None:
        super().__init__('turbopy_base_driver')

        try:
            self._motors = MotorDriver()
            self._battery = BatteryMonitor()
            self._chassis = ChachisMecanum()
        except Exception as exc:  # noqa: BLE001
            self.get_logger().error(f'No se pudo inicializar la capa de hardware: {exc!r}')
            raise

        self.declare_parameter('max_linear_speed', 0.1)  # m/s - ~10 cm/s | 1 m en ~10s
        self.declare_parameter('max_angular_speed', 2.0)  # rad/s - ~$114.59°/s | 360° en ~3.14s

        self._sub_cmd_vel = self.create_subscription(
            Twist,
            'cmd_vel',
            self._on_cmd_vel,
            10,
        )

        self._pub_battery = self.create_publisher(BatteryState, 'battery', 10)
        self._battery_timer = self.create_timer(1.0, self._publish_battery)

        self.get_logger().info('turbopy_base_driver listo. Suscrito a /cmd_vel, publicando /battery.')

    # ------------------------------------------------------------------
    # Control de base
    # ------------------------------------------------------------------

    def _on_cmd_vel(self, msg: Twist) -> None:
        max_linear = self.get_parameter('max_linear_speed').get_parameter_value().double_value
        max_angular = self.get_parameter('max_angular_speed').get_parameter_value().double_value


        """
        linear.x   → Velocidad adelante/atrás
        linear.y   → Velocidad lateral (strafing) - ¡Clave para mecanum!
        linear.z   → (No usado en robots terrestres)
        angular.x  → (No usado típicamente)
        angular.y  → (No usado típicamente)
        angular.z  → Velocidad de rotación (yaw)
        """

        linear_x = msg.linear.x
        linear_y = msg.linear.y
        angular_z = msg.angular.z

        # Clamp y normalizar valores a [-1, 1]
        lin_x = max(-max_linear, min(max_linear, linear_x))
        lin_y = max(-max_linear, min(max_linear, linear_y))
        ang_z = max(-max_angular, min(max_angular, angular_z))
        norm_x = lin_x / max_linear if max_linear > 0.0 else 0.0
        norm_y = lin_y / max_linear if max_linear > 0.0 else 0.0
        norm_ang = ang_z / max_angular if max_angular > 0.0 else 0.0

        # Enviar comando al chassis (ahora soporta movimiento completo)
        # TODO: Si necesitas rotación mientras te mueves, usa set_velocity() con coordenadas polares
        self._chassis.translation(norm_x, norm_y, False)

    # ------------------------------------------------------------------
    # Batería
    # ------------------------------------------------------------------

    def _publish_battery(self) -> None:
        try:
            voltage = float(self._battery.get_voltage())
        except Exception as exc:  # noqa: BLE001
            self.get_logger().warn(f'Error leyendo batería: {exc!r}')
            return

        msg = BatteryState()
        msg.voltage = voltage
        msg.present = True
        # El resto de campos se dejan sin rellenar de momento.

        self._pub_battery.publish(msg)


def main(args=None) -> None:  # noqa: D401
    rclpy.init(args=args)
    node = BaseDriverNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
