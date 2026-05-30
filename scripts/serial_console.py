"""Interactive serial console for the RoArm-M2-Pro.

Thin application layer: it configures logging and drives a ``RoArm`` instance.
All serial and command details live in the ``roarm`` package.
"""

import sys
import threading

import serial

from logging_config import setup_logging
from roarm.controller import RoArm

logger, log_file_path = setup_logging(__name__, "roarm_debug.log")


def _read_loop(arm: RoArm) -> None:
    """Continuously log responses from the arm on a background thread."""
    while arm.is_open:
        try:
            line = arm.read_line()
            if line:
                logger.info(f"Response from the arm: {line}")
        except serial.SerialException as e:
            logger.error(f"Serial read failed: {e}")
            return


def main() -> int:
    logger.info("=== RoArm Serial Communication Test ===")
    logger.info(f"Log file: {log_file_path}")

    answer = input("Do you want to connect to the arm? (yes/no): ").strip().lower()
    if answer not in ("yes", "y"):
        logger.info("Connection cancelled by user.")
        return 0

    try:
        logger.info("Attempting to connect...")
        arm = RoArm.connect(logger=logger)
        logger.info("Serial connection established.")
    except serial.SerialException as e:
        logger.error(f"Failed to open serial port: {e}")
        return 1

    try:
        reader = threading.Thread(target=_read_loop, args=(arm,), daemon=True)
        reader.start()

        logger.info("Connected. Enter JSON commands (Ctrl+C to exit):")
        while True:
            command = input("Command: ").strip()
            if command:
                logger.debug(f"Sending command: {command}")
                arm.send_raw(command)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received.")
    finally:
        if arm.is_open:
            logger.info("Closing serial connection...")
            arm.close()
        logger.info("=== Test completed ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
