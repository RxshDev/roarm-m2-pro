import serial
import threading
import sys
from logging_config import setup_logging

# Setup logging
logger, log_file_path = setup_logging(__name__, 'roarm_debug.log')

# Global serial connection, matching the official Waveshare demo pattern.
ser = None


def read_serial():
    """Continuously read responses from the arm on a background thread."""
    global ser
    try:
        while True:
            if ser and ser.is_open:
                data = ser.readline().decode('utf-8', errors='ignore')
                if data:
                    logger.info(f"Response from the arm: {data.strip()}")
                    print(f"Response from the arm: {data}", end='')
    except Exception as e:
        logger.error(f"Error in read_serial: {e}")


def initialize_connection(port='/dev/ttyUSB0', baudrate=115200):
    """Initialize the serial connection to the arm."""
    global ser
    try:
        logger.info(f"Attempting to connect to {port} at {baudrate} baud...")
        ser = serial.Serial(port, baudrate=baudrate, dsrdtr=None)
        ser.setRTS(False)
        ser.setDTR(False)
        logger.info("Serial connection established successfully.")
        return True
    except serial.SerialException as e:
        logger.error(f"Failed to connect to serial port: {e}")
        return False


def start_reader_thread():
    """Start the background reader thread."""
    logger.debug("Starting reader thread...")
    thread = threading.Thread(target=read_serial)
    thread.daemon = True
    thread.start()
    logger.debug("Reader thread started.")
    return thread


def close_connection():
    """Close the serial connection."""
    global ser
    if ser and ser.is_open:
        logger.info("Closing serial connection...")
        ser.close()
        logger.info("Serial connection closed.")


def main():
    """Main function to run the serial communication interface."""
    logger.info("=== RoArm Serial Communication Test ===")
    logger.info(f"Log file: {log_file_path}")
    print(f"\n📁 Logs are being saved to: {log_file_path}\n")
    
    # Ask user for confirmation before connecting
    response = input("Do you want to connect to the arm? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        logger.info("Connection cancelled by user.")
        return
    
    # Try to initialize connection
    if not initialize_connection():
        logger.error("Failed to initialize connection. Exiting.")
        return
    
    # Start the background reader thread
    start_reader_thread()
    
    # Prompt the user for commands and forward them to the serial device.
    logger.info("Connected.")
    print("\nEnter JSON commands (Ctrl+C to exit):")
    
    # Main loop to read user input and send commands to the arm.
    try:
        while True:
            command = input("Command: ").strip()
            if command:
                logger.debug(f"Sending command: {command}")
                ser.write(command.encode() + b'\n')
            else:
                logger.debug("Empty command ignored.")
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received.")
    except Exception as e:
        logger.error(f"Unexpected error in main loop: {e}")
    finally:
        close_connection()
        logger.info("=== Test completed ===")


if __name__ == "__main__":
    main()
