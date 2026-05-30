"""High-level controller for the RoArm-M2-Pro.

Knows the arm's command vocabulary and feedback-driven motion, but delegates all
byte-level I/O to a transport (see :mod:`roarm.transport`). Decoupling the two
lets the motion logic be unit-tested against a fake transport, no hardware
required.
"""

import json
import logging
import time
from enum import IntEnum
from typing import Any

from .transport import SerialTransport

# Command-side joint name -> key in the T:1051 feedback response.
JOINT_KEYS: dict[str, str] = {
    "base": "b",
    "shoulder": "s",
    "elbow": "e",
    "hand": "t",
}


class Command(IntEnum):
    """JSON "T" command codes (replaces magic numbers)."""

    HOME = 100
    MOVE_RAD = 102
    FEEDBACK = 105
    TORQUE = 210


class RoArm:
    """Controls a RoArm-M2-Pro through an injected transport."""

    def __init__(
        self,
        transport: Any,
        *,
        logger: logging.Logger | None = None,
        tolerance: float = 0.08,
        timeout: float = 10.0,
        stable_threshold: int = 2,
        poll_interval: float = 0.25,
        send_delay: float = 0.2,
    ) -> None:
        self.transport = transport
        # No handlers attached here; an app configures logging and passes a logger in.
        self.logger = logger or logging.getLogger(__name__)
        self.tolerance = tolerance
        self.timeout = timeout
        self.stable_threshold = stable_threshold
        self.poll_interval = poll_interval
        self.send_delay = send_delay

    @classmethod
    def connect(
        cls,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 115200,
        *,
        settle: float = 0.0,
        **kwargs: Any,
    ) -> "RoArm":
        """Build a serial transport, open it, and return a ready controller.

        Args:
            settle: seconds to wait after opening before flushing input — gives
                the ESP32 time to come up after the DTR/RTS toggle.

        Raises:
            serial.SerialException: if the port cannot be opened.
        """
        transport = SerialTransport(port, baudrate)
        transport.open()
        if settle:
            time.sleep(settle)
        transport.flush_input()
        return cls(transport, **kwargs)

    # --- lifecycle ----------------------------------------------------------

    def close(self) -> None:
        self.transport.close()

    @property
    def is_open(self) -> bool:
        return self.transport.is_open

    def __enter__(self) -> "RoArm":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # --- low-level I/O ------------------------------------------------------

    def send(self, command: dict[str, Any]) -> None:
        """Send a JSON command and drain any immediate response into the log."""
        self.transport.flush_input()
        self.transport.write_line(json.dumps(command))
        self.logger.debug(f"Command sent: {command}")
        time.sleep(self.send_delay)
        while self.transport.in_waiting:
            response = self.transport.read_line()
            if response:
                self.logger.debug(f"Response received: {response}")

    def send_raw(self, text: str) -> None:
        """Forward a raw, user-typed line verbatim (used by the serial console)."""
        self.transport.write_line(text)

    def read_line(self) -> str:
        return self.transport.read_line()

    def get_feedback(self) -> dict[str, Any] | None:
        """Request {"T":105} and return the parsed T:1051 position, or None."""
        self.transport.flush_input()
        self.transport.write_line(json.dumps({"T": Command.FEEDBACK}))
        time.sleep(self.poll_interval)

        pos: dict[str, Any] | None = None
        while self.transport.in_waiting:
            line = self.transport.read_line()
            if not line:
                continue
            try:
                data = json.loads(line)
                if "b" in data:  # T:1051 position response
                    pos = data
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                self.logger.debug(f"Error parsing position response: {e}")
        return pos

    def verify_connection(self) -> bool:
        """Return True if the arm answers a feedback request."""
        self.logger.debug("Testing connection...")
        pos = self.get_feedback()
        if pos is not None:
            self.logger.info(f"Connection established. Response: {pos}")
            return True
        self.logger.warning("No response from arm during connection test.")
        return False

    # --- high-level motion --------------------------------------------------

    def move_joints(
        self,
        base: float,
        shoulder: float,
        elbow: float,
        hand: float,
        spd: int = 500,
        acc: int = 10,
        wait: bool = True,
    ) -> None:
        """Move all joints (radians). Blocks until the pose is reached if ``wait``."""
        command = {
            "T": int(Command.MOVE_RAD),
            "base": base,
            "shoulder": shoulder,
            "elbow": elbow,
            "hand": hand,
            "spd": spd,
            "acc": acc,
        }
        self.send(command)
        if wait:
            self.wait_until_reached(command)

    def home(self) -> None:
        """Send {"T":100}. Like the original sequence, this is fire-and-forget."""
        self.send({"T": int(Command.HOME)})

    def set_torque(self, on: bool) -> None:
        """Torque lock on (manual movement disabled) or off."""
        self.send({"T": int(Command.TORQUE), "cmd": 1 if on else 0})

    def wait_until_reached(self, target: dict[str, Any]) -> bool:
        """Poll feedback until joints hold within tolerance for two reads."""
        start = time.time()
        last_print = 0.0
        stable_count = 0
        last_pos: dict[str, Any] | None = None

        while True:
            elapsed = time.time() - start
            if elapsed > self.timeout:
                self.logger.error(
                    f"Timeout waiting for target position after {self.timeout}s"
                )
                return False

            pos = self.get_feedback()
            if pos is None:
                stable_count = 0
                last_pos = None
                continue

            if self._joints_within_tolerance(target, pos, self.tolerance):
                if last_pos == pos:
                    stable_count += 1
                    if stable_count >= self.stable_threshold:
                        self.logger.info("Target position reached (stable).")
                        return True
                else:
                    stable_count = 1
                    last_pos = pos
            else:
                stable_count = 0
                last_pos = None
                now = time.time()
                if now - last_print > 0.5:
                    last_print = now
                    print(
                        f"  Waiting... base:{pos.get('b', 0):.3f} "
                        f"shoulder:{pos.get('s', 0):.3f} "
                        f"elbow:{pos.get('e', 0):.3f} "
                        f"hand:{pos.get('t', 0):.3f} ({elapsed:.1f}s)"
                    )

    @staticmethod
    def _joints_within_tolerance(
        target: dict[str, Any], pos: dict[str, Any], tolerance: float
    ) -> bool:
        return all(
            abs(float(target.get(cmd_key, 0)) - float(pos.get(fb_key, 0))) < tolerance
            for cmd_key, fb_key in JOINT_KEYS.items()
        )
