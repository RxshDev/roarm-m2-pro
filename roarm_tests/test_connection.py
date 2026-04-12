import serial
import threading

# Global serial connection, matching the official Waveshare demo pattern.
ser = serial.Serial('/dev/ttyUSB0', baudrate=115200, dsrdtr=None)
ser.setRTS(False)
ser.setDTR(False)

# Continuously read responses from the arm on a background thread.
def read_serial():
    while True:
        data = ser.readline().decode('utf-8')
        if data:
            print(f"Response from the arm: {data}", end='')

# Start the background reader thread.
thread = threading.Thread(target=read_serial)
thread.daemon = True
thread.start()

# Prompt the user for commands and forward them to the serial device.
print("Connected. Enter JSON commands (Ctrl+C to exit):")

# Main loop to read user input and send commands to the arm.
try:
    while True:
        command = input("")
        ser.write(command.encode() + b'\n')
except KeyboardInterrupt:
    pass
finally:
    # Always close the serial connection before exiting.
    ser.close()
