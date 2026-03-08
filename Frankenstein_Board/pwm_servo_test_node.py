#!/usr/bin/env python3
import os
import sys
import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.append(_ROOT)

from Frankenstein_Board.frankenstein_hw import FrankensteinPwmServoDriver


class FrankensteinPwmServoTestNode(Node):
    def __init__(self) -> None:
        super().__init__("frankenstein_pwm_servo_test")
        self.declare_parameter("channel", 1)
        self.declare_parameter("center_pulse", 1500)
        self.declare_parameter("low_pulse", 1100)
        self.declare_parameter("high_pulse", 1900)
        self.declare_parameter("duration_ms", 400)
        self.declare_parameter("hold_seconds", 0.5)
        self.declare_parameter("command_topic", "/frankenstein/test_command")
        self.declare_parameter("result_topic", "/frankenstein/test_result")
        self.declare_parameter("auto_run", False)

        self._servo = FrankensteinPwmServoDriver(
            channel=int(self.get_parameter("channel").value),
            center_pulse=int(self.get_parameter("center_pulse").value),
        )
        self._low = int(self.get_parameter("low_pulse").value)
        self._high = int(self.get_parameter("high_pulse").value)
        self._duration_ms = int(self.get_parameter("duration_ms").value)
        self._hold = float(self.get_parameter("hold_seconds").value)

        cmd_topic = str(self.get_parameter("command_topic").value)
        result_topic = str(self.get_parameter("result_topic").value)
        self._pub = self.create_publisher(String, result_topic, 10)
        self._sub = self.create_subscription(String, cmd_topic, self._on_command, 10)

        self.get_logger().info("PWM servo test node listo.")
        self._auto_timer = None
        if bool(self.get_parameter("auto_run").value):
            self._auto_timer = self.create_timer(1.0, self._auto_once)

    def _auto_once(self) -> None:
        if self._auto_timer is not None:
            self._auto_timer.cancel()
        self._run_test()

    def _publish_result(self, status: str, detail: str) -> None:
        msg = String()
        msg.data = f"pwm|{status}|{detail}"
        self._pub.publish(msg)

    def _on_command(self, msg: String) -> None:
        cmd = msg.data.strip().lower()
        if cmd in ("pwm", "all", "servo"):
            self._run_test()

    def _run_test(self) -> None:
        try:
            self._servo.set_pulse(self._low, self._duration_ms)
            time.sleep(self._hold)
            self._servo.set_pulse(self._high, self._duration_ms)
            time.sleep(self._hold)
            self._servo.center(self._duration_ms)
            time.sleep(self._hold)
            self._publish_result("PASS", "sweep_ok")
        except Exception as exc:  # noqa: BLE001
            self._publish_result("FAIL", f"error:{exc!r}")
        finally:
            self._servo.center(self._duration_ms)

    def destroy_node(self) -> bool:
        try:
            self._servo.shutdown()
        except Exception:  # noqa: BLE001
            pass
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = FrankensteinPwmServoTestNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
