import sys
import threading

import serial

from logging_config import setup_logging

logger, log_file_path = setup_logging(__name__, "roarm_debug.log")


def read_serial(ser: serial.Serial) -> None:
    """Continuously read responses from the arm on a background thread."""
    while ser.is_open:
        try:
            data = ser.readline().decode("utf-8", errors="ignore")
            if data:
                logger.info(f"Response from the arm: {data.strip()}")
        except serial.SerialException as e:
            logger.error(f"Serial read failed: {e}")
            return


def open_connection(
    port: str = "/dev/ttyUSB0", baudrate: int = 115200
) -> serial.Serial | None:
    """Open and return a configured serial connection, or None on failure."""
    try:
        logger.info(f"Attempting to connect to {port} at {baudrate} baud...")
        ser = serial.Serial(port, baudrate=baudrate, dsrdtr=None)
        ser.setRTS(False)
        ser.setDTR(False)
        logger.info("Serial connection established.")
        return ser
    except serial.SerialException as e:
        logger.error(f"Failed to open serial port: {e}")
        return None


def main() -> int:
    logger.info("=== RoArm Serial Communication Test ===")
    logger.info(f"Log file: {log_file_path}")

    answer = input("Do you want to connect to the arm? (yes/no): ").strip().lower()
    if answer not in ("yes", "y"):
        logger.info("Connection cancelled by user.")
        return 0

    ser = open_connection()
    if ser is None:
        return 1

    try:
        reader = threading.Thread(target=read_serial, args=(ser,), daemon=True)
        reader.start()

        logger.info("Connected. Enter JSON commands (Ctrl+C to exit):")
        while True:
            command = input("Command: ").strip()
            if command:
                logger.debug(f"Sending command: {command}")
                ser.write(command.encode() + b"\n")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received.")
    finally:
        if ser.is_open:
            logger.info("Closing serial connection...")
            ser.close()
        logger.info("=== Test completed ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
