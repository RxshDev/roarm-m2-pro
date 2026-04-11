import serial
import json
import time

# Open serial connection
ser = serial.Serial('/dev/ttyUSB0', baudrate=115200, dsrdtr=None)
ser.setRTS(False)
ser.setDTR(False)
time.sleep(2)
ser.flushInput()


def wait_until_reached_position(command, tolerance=0.08, timeout=10):
    """Requests the current position of all joints and waits until they are within the specified tolerance of the target command."""
    start_time = time.time()
    while True:
        if time.time() - start_time > timeout:
            print("  Timeout while waiting for target position.")
            return False
        ser.write((json.dumps({"T": 105}) + '\n').encode())
        time.sleep(0.4)
        pos = None
        while ser.in_waiting:
            line = ser.readline().decode().strip()
            try:
                data = json.loads(line)
                if "b" in data:
                    pos = data
            except json.JSONDecodeError:
                continue
        if pos is None:
            print("  Waiting for target position...")
            time.sleep(0.3)
            continue
        
        if abs(command.get("base", 0) - float(pos.get("b", 0))) < tolerance and \
        abs(command.get("shoulder", 0) - float(pos.get("s", 0))) < tolerance and \
        abs(command.get("elbow", 0) - float(pos.get("e", 0))) < tolerance and \
        abs(command.get("hand", 0) - float(pos.get("t", 0))) < tolerance:
            print("  Target position reached.")
            return True
        else:
            print("  Waiting for target position...")
            time.sleep(0.3)
        


def send_command(command: dict):
    """
    Sends a JSON command and waits for the movement to complete.
    command: Python dictionary sent as JSON
    wait:    seconds to wait after sending
    """
    ser.flushInput() # Clear input buffer before sending new command
    message = json.dumps(command) + '\n'
    ser.write(message.encode())
    print(f"Sent: {message.strip()}")
    time.sleep(0.5)  # Short delay to allow command processing

    # Read feedback if available
    while ser.in_waiting:
        response = ser.readline().decode().strip()
        if response:
            print(f"  Response: {response}")

    # Wait until the target position is reached
    if "base" in command:
        wait_until_reached_position(command)


# Define movement sequence
# Each entry: (description, command, wait_time) -> tuple with human-readable description, JSON command, and wait time after sending
sequence = [
    ("Home position",
     {"T":102,"base":0,"shoulder":0,"elbow":1.6,"hand":3.14,"spd":500,"acc":10}),

    ("Base 90 degrees left",
     {"T":102,"base":1.5708,"shoulder":0,"elbow":1.6,"hand":3.14,"spd":500,"acc":10}),

    ("Elbow down",
     {"T":102,"base":1.5708,"shoulder":0,"elbow":2.2,"hand":3.14,"spd":400,"acc":8}),

    ("Gripper open",
     {"T":102,"base":1.5708,"shoulder":0,"elbow":2.2,"hand":1.5,"spd":800,"acc":10}),

    ("Gripper close",
     {"T":102,"base":1.5708,"shoulder":0,"elbow":2.2,"hand":3.14,"spd":800,"acc":10}),

    ("Return to home position",
     {"T":100}),
]

# Execute sequence
def main():
    print()
    print("=== Sequence started ===\n")

    for step, (description, command) in enumerate(sequence, 1):
        print(f"Step {step}/{len(sequence)}: {description}")
        send_command(command)
        print()

    print("=== Sequence completed ===")
    ser.close()

if __name__ == "__main__":
    main()