"""RoArm-M2-Pro control library.

Two layers:
- ``SerialTransport`` — the wire: open/close/read/write over serial.
- ``RoArm`` — the arm's language: high-level joint commands and feedback-driven motion.
"""

from .controller import JOINT_KEYS, Command, RoArm
from .transport import SerialTransport

__all__ = ["RoArm", "SerialTransport", "Command", "JOINT_KEYS"]
