"""Scripted movement demo for the RoArm-M2-Pro.

Thin application layer: it configures logging and drives a ``RoArm`` instance
through a fixed sequence. Each ``move_joints`` call blocks until the pose is
confirmed via feedback (see ``roarm.controller``).
"""

import sys

import serial

from logging_config import setup_logging
from roarm.controller import RoArm

logger, log_file_path = setup_logging(__name__, "roarm_sequence.log")

# (description, joint keyword arguments) — radians, speed, acceleration.
SEQUENCE: list[tuple[str, dict[str, float]]] = [
    ("Home position",
     dict(base=0, shoulder=0, elbow=1.6, hand=3.14, spd=500, acc=10)),
    ("Base 90 degrees left",
     dict(base=1.5708, shoulder=0, elbow=1.6, hand=3.14, spd=600, acc=12)),
    ("Elbow down",
     dict(base=1.5708, shoulder=0, elbow=2.2, hand=3.14, spd=500, acc=10)),
    ("Gripper open",
     dict(base=1.5708, shoulder=0, elbow=2.2, hand=1.5, spd=700, acc=10)),
    ("Gripper close",
     dict(base=1.5708, shoulder=0, elbow=2.2, hand=3.14, spd=700, acc=10)),
]


def main() -> int:
    logger.info("=== RoArm Movement Sequence Test Started ===")
    logger.info(f"Log file: {log_file_path}")

    try:
        arm = RoArm.connect(logger=logger, settle=1.0)
        logger.info("Serial port opened: /dev/ttyUSB0")
    except serial.SerialException as e:
        logger.error(f"Failed to open serial port: {e}")
        logger.error("Check if the arm is connected and powered on.")
        return 1

    try:
        if not arm.verify_connection():
            logger.error("Connection test failed. Exiting.")
            return 1

        print("\n" + "=" * 50)
        print("RoArm-M2-Pro Movement Sequence")
        print("=" * 50)
        logger.info(f"Sequence contains {len(SEQUENCE)} steps")

        try:
            input("\nPress ENTER to start the sequence (or Ctrl+C to cancel)... ")
        except KeyboardInterrupt:
            logger.info("Sequence cancelled by user.")
            return 0

        logger.info("=== Sequence started ===")
        for step, (description, joints) in enumerate(SEQUENCE, 1):
            logger.info(f"Step {step}/{len(SEQUENCE)}: {description}")
            arm.move_joints(**joints)

        logger.info("Returning to home position")
        arm.home()
        logger.info("=== Sequence completed successfully ===")
    except KeyboardInterrupt:
        logger.warning("Sequence interrupted by user.")
    finally:
        arm.close()
        logger.info("Serial connection closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
