"""Shared test fixtures.

``FakeTransport`` mirrors the public interface of ``SerialTransport`` but never
touches hardware. It records every line written and releases scripted feedback
responses only in reaction to a feedback request ({"T":105}), the same way the
real arm answers one line per poll.
"""

import json

import pytest

from roarm import RoArm

FEEDBACK_T_CODE = 105


class FakeTransport:
    def __init__(self) -> None:
        self.written: list[str] = []
        self._available: list[str] = []
        self._scripted: list[str] = []
        self.is_open = True

    # --- scripting helpers (test-only) ---
    def script_feedback(self, *lines: str) -> None:
        """Queue feedback lines; one is released per feedback request written."""
        self._scripted.extend(lines)

    # --- SerialTransport interface ---
    def open(self) -> None:
        self.is_open = True

    def close(self) -> None:
        self.is_open = False

    def write_line(self, text: str) -> None:
        self.written.append(text)
        try:
            command = json.loads(text)
        except json.JSONDecodeError:
            command = None
        if command and command.get("T") == FEEDBACK_T_CODE and self._scripted:
            self._available.append(self._scripted.pop(0))

    def read_line(self) -> str:
        return self._available.pop(0) if self._available else ""

    @property
    def in_waiting(self) -> int:
        return len(self._available)

    def flush_input(self) -> None:
        self._available.clear()

    def __enter__(self) -> "FakeTransport":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


@pytest.fixture
def transport() -> FakeTransport:
    return FakeTransport()


@pytest.fixture
def arm(transport: FakeTransport) -> RoArm:
    # Zero delays so the polling logic runs instantly under test.
    return RoArm(transport, poll_interval=0.0, send_delay=0.0)


def position(b: float, s: float, e: float, t: float) -> str:
    """Build a T:1051 feedback line as the arm would emit it."""
    return json.dumps({"T": 1051, "b": b, "s": s, "e": e, "t": t})
