#!/usr/bin/env python3
import os
import sys
import time
from typing import List

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.append(_ROOT)

from Frankenstein_Board.frankenstein_hw import FrankensteinMotorDriver


class FrankensteinMotorTestNode(Node):
    def __init__(self) -> None:
        super().__init__("frankenstein_motor_test")
        self.declare_parameter("bus_num", 1)
        self.declare_parameter("addr", 0x26)
        self.declare_parameter("motor_type", 3)
        self.declare_parameter("mode", "speed")  # speed | pwm
        self.declare_parameter("test_value", 400)
        self.declare_parameter("step_seconds", 0.8)
        self.declare_parameter("command_topic", "/frankenstein/test_command")
        self.declare_parameter("result_topic", "/frankenstein/test_result")
        self.declare_parameter("motor_order", [1, 2, 3, 4])
        self.declare_parameter("motor_signs", [1, 1, 1, 1])
        self.declare_parameter("auto_run", False)

        self._driver = FrankensteinMotorDriver(
            bus_num=self.get_parameter("bus_num").value,
            addr=self.get_parameter("addr").value,
            motor_type=self.get_parameter("motor_type").value,
        )
        self._mode = str(self.get_parameter("mode").value).strip().lower()
        self._test_value = int(self.get_parameter("test_value").value)
        self._step_seconds = float(self.get_parameter("step_seconds").value)
        self._motor_order: List[int] = list(self.get_parameter("motor_order").value)
        self._motor_signs: List[int] = list(self.get_parameter("motor_signs").value)

        cmd_topic = str(self.get_parameter("command_topic").value)
        result_topic = str(self.get_parameter("result_topic").value)
        self._pub = self.create_publisher(String, result_topic, 10)
        self._sub = self.create_subscription(String, cmd_topic, self._on_command, 10)

        self.get_logger().info("Motor test node listo.")
        self._auto_timer = None
        if bool(self.get_parameter("auto_run").value):
            self._auto_timer = self.create_timer(1.0, self._auto_once)

    def _auto_once(self) -> None:
        if self._auto_timer is not None:
            self._auto_timer.cancel()
        self._run_test()

    def _publish_result(self, status: str, detail: str) -> None:
        msg = String()
        msg.data = f"motor|{status}|{detail}"
        self._pub.publish(msg)

    def _on_command(self, msg: String) -> None:
        cmd = msg.data.strip().lower()
        if cmd in ("motor", "all"):
            self._run_test()

    def _run_test(self) -> None:
        self.get_logger().info("Iniciando test de ruedas por canal...")
        try:
            if not self._driver.scan():
                self._publish_result("FAIL", "sin_respuesta_i2c")
                return

            details = []
            for idx, motor_id in enumerate(self._motor_order):
                sign = 1
                if idx < len(self._motor_signs):
                    sign = -1 if int(self._motor_signs[idx]) < 0 else 1
                value = int(self._test_value) * sign

                if self._mode == "pwm":
                    payload = {"m1": 0, "m2": 0, "m3": 0, "m4": 0}
                    payload[f"m{motor_id}"] = value
                    self._driver.set_pwm(**payload)
                else:
                    payload = {"m1": 0, "m2": 0, "m3": 0, "m4": 0}
                    payload[f"m{motor_id}"] = value
                    self._driver.set_speed(**payload)

                time.sleep(self._step_seconds)
                enc_10ms = self._driver.read_encoder_10ms()
                details.append(f"M{motor_id}:{enc_10ms.get(motor_id, 0)}")
                self._driver.stop()
                time.sleep(0.15)

            self._publish_result("PASS", ",".join(details))
        except Exception as exc:  # noqa: BLE001
            self._publish_result("FAIL", f"error:{exc!r}")
        finally:
            try:
                self._driver.stop()
            except Exception:  # noqa: BLE001
                pass

    def destroy_node(self) -> bool:
        try:
            self._driver.shutdown()
        except Exception:  # noqa: BLE001
            pass
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = FrankensteinMotorTestNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
