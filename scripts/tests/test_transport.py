"""Tests for ``SerialTransport`` line encoding/decoding, using a fake serial port."""

from roarm import SerialTransport


class FakeSerial:
    """Minimal stand-in for ``serial.Serial`` used to inspect wire bytes."""

    def __init__(self) -> None:
        self.written = b""
        self._lines: list[bytes] = []
        self.is_open = True
        self.flushed = False

    def queue_line(self, raw: bytes) -> None:
        self._lines.append(raw)

    def write(self, data: bytes) -> None:
        self.written += data

    def flush(self) -> None:
        self.flushed = True

    def readline(self) -> bytes:
        return self._lines.pop(0) if self._lines else b""

    @property
    def in_waiting(self) -> int:
        return len(self._lines)

    def reset_input_buffer(self) -> None:
        self._lines.clear()

    def close(self) -> None:
        self.is_open = False


def make_transport(fake: FakeSerial) -> SerialTransport:
    transport = SerialTransport()
    transport._serial = fake  # inject without opening a real port
    return transport


def test_write_line_appends_single_newline_utf8():
    fake = FakeSerial()
    make_transport(fake).write_line('{"T": 105}')
    assert fake.written == b'{"T": 105}\n'
    assert fake.flushed is True


def test_read_line_strips_and_decodes_tolerantly():
    fake = FakeSerial()
    fake.queue_line(b"  {\"T\": 1051} \r\n")
    fake.queue_line(b"\xff\xfe bad bytes \n")  # invalid UTF-8 -> ignored
    transport = make_transport(fake)
    assert transport.read_line() == '{"T": 1051}'
    assert transport.read_line() == "bad bytes"


def test_in_waiting_and_flush_input():
    fake = FakeSerial()
    fake.queue_line(b"a\n")
    transport = make_transport(fake)
    assert transport.in_waiting == 1
    transport.flush_input()
    assert transport.in_waiting == 0
