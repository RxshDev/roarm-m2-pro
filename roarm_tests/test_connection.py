import serial
import threading

# Globale Serial-Verbindung - genau wie die offizielle Waveshare Demo
ser = serial.Serial('/dev/ttyUSB0', baudrate=115200, dsrdtr=None)
ser.setRTS(False)
ser.setDTR(False)

def read_serial():
    # Läuft in einem eigenen Thread - liest kontinuierlich alle Antworten
    while True:
        data = ser.readline().decode('utf-8')
        if data:
            print(f"Antwort vom Arm: {data}", end='')

# Read-Thread starten
thread = threading.Thread(target=read_serial)
thread.daemon = True
thread.start()

print("Verbunden. JSON-Befehl eingeben (Ctrl+C zum Beenden):")

try:
    while True:
        command = input("")
        ser.write(command.encode() + b'\n')
except KeyboardInterrupt:
    pass
finally:
    ser.close()
