# Copilot Instructions for `roarm-m2-pro`

## Build, test, and lint commands

This repository is script-based. There is no build system or linter config, but
there is a pytest suite for the control library.

- Install runtime dependency:
  - `pip install -r requirements.txt`  (only `pyserial`)
- Install dev dependencies (use a venv on Arch / PEP 668):
  - `pip install -r requirements-dev.txt`  (adds `pytest`)
- Run the interactive serial command console:
  - `python scripts/serial_console.py`
- Run the movement demo (end-to-end behavior check against hardware):
  - `python scripts/demo_sequence.py`
- Run the unit tests (no hardware needed):
  - `pytest`  (config in `pyproject.toml`)
- Single-command equivalent against hardware:
  - Enter one JSON command in `serial_console.py` (for example `{"T":105}`) to validate one command/response path.

## High-level architecture

The codebase centers on direct serial JSON control of a Waveshare RoArm-M2-Pro
over `/dev/ttyUSB0` at `115200` baud. The arm-control logic lives in the
`scripts/roarm/` package, split into two layers; the scripts are thin apps.

- `scripts/roarm/transport.py` — `SerialTransport`: the only code that touches
  `serial.Serial`. `open()`/`close()`, `write_line()`, `read_line()`,
  `in_waiting`, `flush_input()`.
- `scripts/roarm/controller.py` — `RoArm`: high-level commands and feedback-driven
  motion (`move_joints`, `home`, `set_torque`, `get_feedback`,
  `verify_connection`, `wait_until_reached`). `RoArm.connect()` builds and opens a
  transport. Defines the `Command` IntEnum (T-codes) and `JOINT_KEYS`. A transport
  is injected, so the logic is testable without hardware.
- `scripts/serial_console.py` — interactive console: `RoArm.connect()`, a daemon
  reader thread logging `arm.read_line()`, user JSON forwarded via `arm.send_raw()`.
- `scripts/demo_sequence.py` — scripted runner: a `SEQUENCE` driven through
  `arm.move_joints(**kwargs)`; completion is stable only after consecutive matching
  readings (filters encoder jitter).
- `scripts/logging_config.py` — shared logging setup: creates `scripts/logs/`,
  rotating file logs (5MB, 5 backups) plus INFO console logging.
- `scripts/tests/` — pytest with a `FakeTransport` (in `conftest.py`).

## Key conventions in this repo

- Serial init pattern lives in `SerialTransport.open()`: `serial.Serial(..., dsrdtr=None)`
  then `setRTS(False)` and `setDTR(False)`. Prevents the ESP32 from auto-resetting on connect.
- Commands are newline-delimited JSON (`json.dumps(command) + '\n'`); `SerialTransport`
  is the only place that knows this wire format.
- Movement completion is feedback-driven, not sleep-only: `RoArm.wait_until_reached`
  verifies per-joint tolerance against the `b/s/e/t` values in the `T:1051` response.
  New motion methods must route through it.
- Joint mapping lives in `JOINT_KEYS` (`base→b`, `shoulder→s`, `elbow→e`, `hand→t`)
  in `roarm/controller.py` — add a new joint by extending this dict. T-codes are named
  in the `Command` IntEnum.
- The library does not configure logging: apps call `setup_logging(__name__, <log_file>)`
  at module start and pass the logger into `RoArm(..., logger=logger)`; runtime logs go
  under `scripts/logs/`.
