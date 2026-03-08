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

from Frankenstein_Board.frankenstein_hw import FrankensteinBuzzerDriver


class FrankensteinBuzzerTestNode(Node):
    def __init__(self) -> None:
        super().__init__("frankenstein_buzzer_test")
        self.declare_parameter("on_seconds", 0.2)
        self.declare_parameter("repetitions", 3)
        self.declare_parameter("command_topic", "/frankenstein/test_command")
        self.declare_parameter("result_topic", "/frankenstein/test_result")
        self.declare_parameter("auto_run", False)

        self._buzzer = FrankensteinBuzzerDriver()
        self._on_seconds = float(self.get_parameter("on_seconds").value)
        self._repetitions = int(self.get_parameter("repetitions").value)

        cmd_topic = str(self.get_parameter("command_topic").value)
        result_topic = str(self.get_parameter("result_topic").value)
        self._pub = self.create_publisher(String, result_topic, 10)
        self._sub = self.create_subscription(String, cmd_topic, self._on_command, 10)

        self.get_logger().info("Buzzer test node listo.")
        self._auto_timer = None
        if bool(self.get_parameter("auto_run").value):
            self._auto_timer = self.create_timer(1.0, self._auto_once)

    def _auto_once(self) -> None:
        if self._auto_timer is not None:
            self._auto_timer.cancel()
        self._run_test()

    def _publish_result(self, status: str, detail: str) -> None:
        msg = String()
        msg.data = f"buzzer|{status}|{detail}"
        self._pub.publish(msg)

    def _on_command(self, msg: String) -> None:
        cmd = msg.data.strip().lower()
        if cmd in ("buzzer", "all"):
            self._run_test()

    def _run_test(self) -> None:
        try:
            for _ in range(self._repetitions):
                self._buzzer.on()
                time.sleep(self._on_seconds)
                self._buzzer.off()
                time.sleep(self._on_seconds)
            self._publish_result("PASS", f"beeps:{self._repetitions}")
        except Exception as exc:  # noqa: BLE001
            self._publish_result("FAIL", f"error:{exc!r}")
        finally:
            self._buzzer.off()

    def destroy_node(self) -> bool:
        try:
            self._buzzer.shutdown()
        except Exception:  # noqa: BLE001
            pass
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = FrankensteinBuzzerTestNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
