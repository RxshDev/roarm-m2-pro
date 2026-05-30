"""Serial transport layer for the RoArm-M2-Pro.

This is the only place in the project that touches ``serial.Serial`` directly.
It knows the *wire* (how bytes flow over the cable) but nothing about the arm's
command vocabulary.
"""

import serial


class SerialTransport:
    """Newline-delimited serial connection to the arm's ESP32 controller.

    The DTR/RTS toggle in :meth:`open` prevents the ESP32 from auto-resetting
    when the port is opened.
    """

    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 115200) -> None:
        self.port = port
        self.baudrate = baudrate
        self._serial: serial.Serial | None = None

    def open(self) -> None:
        """Open the serial port using the ESP32-safe init pattern.

        Raises:
            serial.SerialException: if the port cannot be opened.
        """
        self._serial = serial.Serial(self.port, baudrate=self.baudrate, dsrdtr=None)
        self._serial.setRTS(False)
        self._serial.setDTR(False)

    def close(self) -> None:
        if self._serial is not None and self._serial.is_open:
            self._serial.close()

    @property
    def is_open(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def write_line(self, text: str) -> None:
        """Write one newline-terminated line (the project's wire format)."""
        if self._serial is None:
            raise RuntimeError("Transport is not open.")
        self._serial.write((text + "\n").encode("utf-8"))
        self._serial.flush()

    def read_line(self) -> str:
        """Read one line, decoded tolerantly and stripped."""
        if self._serial is None:
            raise RuntimeError("Transport is not open.")
        return self._serial.readline().decode("utf-8", errors="ignore").strip()

    @property
    def in_waiting(self) -> int:
        return self._serial.in_waiting if self._serial is not None else 0

    def flush_input(self) -> None:
        if self._serial is not None:
            self._serial.reset_input_buffer()

    def __enter__(self) -> "SerialTransport":
        self.open()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
