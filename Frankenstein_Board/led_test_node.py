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

from Frankenstein_Board.frankenstein_hw import FrankensteinLedDriver


class FrankensteinLedTestNode(Node):
    def __init__(self) -> None:
        super().__init__("frankenstein_led_test")
        self.declare_parameter("num_pixels", 2)
        self.declare_parameter("step_seconds", 0.4)
        self.declare_parameter("command_topic", "/frankenstein/test_command")
        self.declare_parameter("result_topic", "/frankenstein/test_result")
        self.declare_parameter("auto_run", False)

        self._led = FrankensteinLedDriver()
        self._num_pixels = int(self.get_parameter("num_pixels").value)
        self._step = float(self.get_parameter("step_seconds").value)

        cmd_topic = str(self.get_parameter("command_topic").value)
        result_topic = str(self.get_parameter("result_topic").value)
        self._pub = self.create_publisher(String, result_topic, 10)
        self._sub = self.create_subscription(String, cmd_topic, self._on_command, 10)

        self.get_logger().info("LED test node listo.")
        self._auto_timer = None
        if bool(self.get_parameter("auto_run").value):
            self._auto_timer = self.create_timer(1.0, self._auto_once)

    def _auto_once(self) -> None:
        if self._auto_timer is not None:
            self._auto_timer.cancel()
        self._run_test()

    def _publish_result(self, status: str, detail: str) -> None:
        msg = String()
        msg.data = f"led|{status}|{detail}"
        self._pub.publish(msg)

    def _on_command(self, msg: String) -> None:
        cmd = msg.data.strip().lower()
        if cmd in ("led", "all"):
            self._run_test()

    def _set_all(self, r: int, g: int, b: int) -> None:
        for i in range(self._num_pixels):
            self._led.set_pixel(i, r, g, b)
        self._led.show()

    def _run_test(self) -> None:
        try:
            colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255), (0, 0, 0)]
            for r, g, b in colors:
                self._set_all(r, g, b)
                time.sleep(self._step)
            self._publish_result("PASS", "secuencia_rgb_ok")
        except Exception as exc:  # noqa: BLE001
            self._publish_result("FAIL", f"error:{exc!r}")
        finally:
            self._led.clear()

    def destroy_node(self) -> bool:
        try:
            self._led.shutdown()
        except Exception:  # noqa: BLE001
            pass
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = FrankensteinLedTestNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
