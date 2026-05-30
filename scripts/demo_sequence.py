import json
import sys
import time
from typing import Any

import serial

from logging_config import setup_logging

logger, log_file_path = setup_logging(__name__, "roarm_sequence.log")

# Map command keys -> feedback keys returned in the T:1051 response.
JOINT_KEYS: dict[str, str] = {
    "base": "b",
    "shoulder": "s",
    "elbow": "e",
    "hand": "t",
}


def verify_connection(ser: serial.Serial) -> bool:
    """Send a position feedback request to verify the arm is responsive."""
    logger.debug("Testing connection...")
    try:
        ser.flushInput()
        ser.write((json.dumps({"T": 105}) + "\n").encode())
        ser.flush()
        time.sleep(0.3)

        if ser.in_waiting:
            response = ser.readline().decode().strip()
            logger.info(f"Connection established. Response: {response}")
            return True
        logger.warning("No response from arm during connection test.")
        return False
    except (serial.SerialException, UnicodeDecodeError) as e:
        logger.error(f"Connection test failed: {e}")
        return False


def _joints_within_tolerance(
target: dict[str, Any], pos: dict[str, Any], tolerance: float
) -> bool:
    return all(
        abs(float(target.get(cmd_key, 0)) - float(pos.get(fb_key, 0))) < tolerance
        for cmd_key, fb_key in JOINT_KEYS.items()
    )


def wait_until_reached_position(
    ser: serial.Serial,
    command: dict[str, Any],
    tolerance: float = 0.08,
    timeout: float = 10.0,
    stable_threshold: int = 2,
) -> bool:
    """Poll {"T":105} feedback until joints are within tolerance for `stable_threshold` consecutive reads."""
    start = time.time()
    last_print = 0.0
    stable_count = 0
    last_pos: dict[str, Any] | None = None

    while True:
        elapsed = time.time() - start
        if elapsed > timeout:
            logger.error(f"Timeout waiting for target position after {timeout}s")
            return False

        ser.write((json.dumps({"T": 105}) + "\n").encode())
        ser.flush()
        time.sleep(0.25)

        pos: dict[str, Any] | None = None
        while ser.in_waiting:
            try:
                line = ser.readline().decode().strip()
                if not line:
                    continue
                data = json.loads(line)
                if "b" in data:  # T:1051 position response
                    pos = data
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.debug(f"Error parsing position response: {e}")

        if pos is None:
            stable_count = 0
            last_pos = None
            time.sleep(0.15)
            continue

        if _joints_within_tolerance(command, pos, tolerance):
            if last_pos == pos:
                stable_count += 1
                if stable_count >= stable_threshold:
                    logger.info("Target position reached (stable).")
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
            time.sleep(0.1)


def send_command(ser: serial.Serial, command: dict[str, Any]) -> None:
    """Send a JSON command. If it targets joints, block until the arm reaches the pose."""
    ser.flushInput()
    message = json.dumps(command) + "\n"
    ser.write(message.encode())
    ser.flush()
    logger.debug(f"Command sent: {message.strip()}")
    print(f"Sent: {message.strip()}")
    time.sleep(0.2)

    while ser.in_waiting:
        try:
            response = ser.readline().decode().strip()
            if response:
                logger.debug(f"Response received: {response}")
        except UnicodeDecodeError:
            continue

    if any(key in command for key in JOINT_KEYS):
        wait_until_reached_position(ser, command)


sequence: list[tuple[str, dict[str, Any]]] = [
    ("Home position",
     {"T": 102, "base": 0, "shoulder": 0, "elbow": 1.6, "hand": 3.14, "spd": 500, "acc": 10}),
    ("Base 90 degrees left",
     {"T": 102, "base": 1.5708, "shoulder": 0, "elbow": 1.6, "hand": 3.14, "spd": 600, "acc": 12}),
    ("Elbow down",
     {"T": 102, "base": 1.5708, "shoulder": 0, "elbow": 2.2, "hand": 3.14, "spd": 500, "acc": 10}),
    ("Gripper open",
     {"T": 102, "base": 1.5708, "shoulder": 0, "elbow": 2.2, "hand": 1.5, "spd": 700, "acc": 10}),
    ("Gripper close",
     {"T": 102, "base": 1.5708, "shoulder": 0, "elbow": 2.2, "hand": 3.14, "spd": 700, "acc": 10}),
    ("Return to home position",
     {"T": 100}),
]


def main() -> int:
    logger.info("=== RoArm Movement Sequence Test Started ===")
    logger.info(f"Log file: {log_file_path}")

    try:
        ser = serial.Serial("/dev/ttyUSB0", baudrate=115200, dsrdtr=None)
        ser.setRTS(False)
        ser.setDTR(False)
        time.sleep(1)
        ser.flushInput()
        logger.info("Serial port opened: /dev/ttyUSB0")
    except serial.SerialException as e:
        logger.error(f"Failed to open serial port: {e}")
        logger.error("Check if the arm is connected and powered on.")
        return 1

    try:
        if not verify_connection(ser):
            logger.error("Connection test failed. Exiting.")
            return 1

        print("\n" + "=" * 50)
        print("RoArm-M2-Pro Movement Sequence")
        print("=" * 50)
        logger.info(f"Sequence contains {len(sequence)} steps")

        try:
            input("\nPress ENTER to start the sequence (or Ctrl+C to cancel)... ")
        except KeyboardInterrupt:
            logger.info("Sequence cancelled by user.")
            return 0

        logger.info("=== Sequence started ===")
        for step, (description, command) in enumerate(sequence, 1):
            logger.info(f"Step {step}/{len(sequence)}: {description}")
            send_command(ser, command)
        logger.info("=== Sequence completed successfully ===")
    except KeyboardInterrupt:
        logger.warning("Sequence interrupted by user.")
    finally:
        ser.close()
        logger.info("Serial connection closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
