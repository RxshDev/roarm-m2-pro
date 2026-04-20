import serial
import json
import time
import sys
from logging_config import setup_logging

# Setup logging
logger, log_file_path = setup_logging(__name__, 'roarm_sequence.log')

def test_connection(ser):
    """Test if the arm responds to commands"""
    logger.debug("Testing connection...")
    print("  Testing connection...")
    try:
        ser.flushInput()
        ser.write((json.dumps({"T": 105}) + '\n').encode())
        ser.flush()  # Ensure data is sent immediately
        time.sleep(0.3)  # Reduced from 0.5s for faster response
        
        if ser.in_waiting:
            response = ser.readline().decode().strip()
            logger.info(f"Connection established with response: {response}")
            print(f"  Connection established")
            print(f"  Response: {response}")
            return True
        else:
            logger.warning("No response from arm during connection test")
            print("  No response from arm")
            return False
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        print(f"  Connection test failed: {e}")
        return False


def wait_until_reached_position(ser, command, tolerance=0.08, timeout=10):
    """Requests the current position of all joints and waits until they are within the specified tolerance of the target command."""
    start_time = time.time()
    position_stable_count = 0  # Counter for stable readings
    stable_threshold = 2  # Require 2 stable readings before confirming
    last_pos = None
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            logger.error(f"Timeout waiting for target position after {timeout}s")
            print("  Timeout while waiting for target position.")
            return False

        ser.write((json.dumps({"T": 105}) + '\n').encode())
        ser.flush()  # Ensure command is sent immediately
        time.sleep(0.25)  # Optimized timing for faster response

        # Read all available lines and find the position response
        pos = None
        while ser.in_waiting:
            try:
                line = ser.readline().decode().strip()
                if line:
                    data = json.loads(line)
                    if "b" in data:  # This is the position response T:1051
                        pos = data
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.debug(f"Error parsing position response: {e}")
                continue

        if pos is None:
            position_stable_count = 0
            last_pos = None
            time.sleep(0.15)
            continue

        # Check if all joints are within tolerance
        base_match = abs(float(command.get("base", 0)) - float(pos.get("b", 0))) < tolerance
        shoulder_match = abs(float(command.get("shoulder", 0)) - float(pos.get("s", 0))) < tolerance
        elbow_match = abs(float(command.get("elbow", 0)) - float(pos.get("e", 0))) < tolerance
        hand_match = abs(float(command.get("hand", 0)) - float(pos.get("t", 0))) < tolerance
        
        if base_match and shoulder_match and elbow_match and hand_match:
            # Check if position is stable (same as last reading)
            if last_pos == pos:
                position_stable_count += 1
                if position_stable_count >= stable_threshold:
                    logger.info("Target position reached (stable)")
                    print()
                    print("  Target position reached.")
                    return True
            else:
                position_stable_count = 1
                last_pos = pos
        else:
            position_stable_count = 0
            last_pos = None
            # Only print every other iteration to reduce output overhead
            if int((time.time() - start_time) * 4) % 2 == 0:
                print()
                print(f"  Waiting... base:{pos.get('b',0):.3f} shoulder:{pos.get('s',0):.3f} elbow:{pos.get('e',0):.3f} hand:{pos.get('t',0):.3f} ({elapsed:.1f}s)")
            time.sleep(0.1)


def send_command(ser, command: dict):
    """
    Sends a JSON command and waits for the movement to complete.
    command: Python dictionary sent as JSON
    """
    ser.flushInput()
    message = json.dumps(command) + '\n'
    ser.write(message.encode())
    ser.flush()  # Ensure command is sent immediately
    logger.debug(f"Command sent: {message.strip()}")
    print(f"Sent: {message.strip()}")
    time.sleep(0.2)  # Reduced from 0.5s for faster response (allows ARM to start processing immediately)

    # Read feedback if available
    while ser.in_waiting:
        try:
            response = ser.readline().decode().strip()
            if response:
                logger.debug(f"Response received: {response}")
                print(f"  Response: {response}")
        except UnicodeDecodeError:
            continue

    # Wait until the target position is reached (only if movement command)
    if "base" in command or "shoulder" in command or "elbow" in command or "hand" in command:
        wait_until_reached_position(ser, command)


# Define movement sequence
# Each entry: (description, command)
# Speed (spd) and acceleration (acc) are tuned for optimal movement quality
sequence = [
    ("Home position",
     {"T":102,"base":0,"shoulder":0,"elbow":1.6,"hand":3.14,"spd":500,"acc":10}),

    ("Base 90 degrees left",
     {"T":102,"base":1.5708,"shoulder":0,"elbow":1.6,"hand":3.14,"spd":600,"acc":12}),

    ("Elbow down",
     {"T":102,"base":1.5708,"shoulder":0,"elbow":2.2,"hand":3.14,"spd":500,"acc":10}),

    ("Gripper open",
     {"T":102,"base":1.5708,"shoulder":0,"elbow":2.2,"hand":1.5,"spd":700,"acc":10}),

    ("Gripper close",
     {"T":102,"base":1.5708,"shoulder":0,"elbow":2.2,"hand":3.14,"spd":700,"acc":10}),

    ("Return to home position",
     {"T":100}),
]


def main():
    logger.info("=== RoArm Movement Sequence Test Started ===")
    logger.info(f"Log file: {log_file_path}")
    print(f"\n📁 Logs are being saved to: {log_file_path}\n")
    
    # Open serial connection
    try:
        ser = serial.Serial('/dev/ttyUSB0', baudrate=115200, dsrdtr=None)
        ser.setRTS(False)
        ser.setDTR(False)
        time.sleep(1)  # Reduced from 2s - sufficient for ARM initialization
        ser.flushInput()
        print()
        logger.info("Serial port opened: /dev/ttyUSB0")
    except serial.SerialException as e:
        logger.error(f"Failed to open serial port: {e}")
        logger.error("Check if the arm is connected and powered on.")
        print(f"  Failed to open serial port: {e}")
        print("  Check if the arm is connected and powered on.")
        sys.exit(1)

    # Test connection
    if not test_connection(ser):
        logger.error("Connection test failed. Exiting.")
        print("\nConnection test failed. Exiting.")
        ser.close()
        sys.exit(1)

    print("\n" + "="*50)
    print("RoArm-M2-Pro Movement Sequence")
    print("="*50)
    logger.info(f"Sequence contains {len(sequence)} steps")
    print(f"\nSequence contains {len(sequence)} steps")
    print()
    
    # Wait for user input
    try:
        input("Press ENTER to start the sequence (or Ctrl+C to cancel)... ")
    except KeyboardInterrupt:
        logger.info("Sequence cancelled by user.")
        print("\n\nSequence cancelled by user.")
        ser.close()
        sys.exit(0)

    # Execute sequence
    logger.info("=== Sequence started ===")
    print("\n=== Sequence started ===\n")

    try:
        for step, (description, command) in enumerate(sequence, 1):
            print(f"Step {step}/{len(sequence)}: {description}")
            logger.info(f"Step {step}/{len(sequence)}: {description}")
            send_command(ser, command)
            print()

        logger.info("=== Sequence completed successfully ===")
        print("=== Sequence completed ===")
    except KeyboardInterrupt:
        logger.warning("Sequence interrupted by user.")
        print("\n\nSequence interrupted by user.")
    finally:
        ser.close()
        logger.info("Serial connection closed.")
        print("\nSerial connection closed.")


if __name__ == "__main__":
    main()