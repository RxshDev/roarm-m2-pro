# Copilot Instructions for `roarm-m2-pro`

## Build, test, and lint commands

This repository is script-based and currently has no dedicated build system, linter config, or automated test runner.

- Install dependency:
  - `pip install -r requirements.txt`
- Run the interactive serial command console:
  - `python scripts/serial_console.py`
- Run the movement demo (end-to-end behavior check against hardware):
  - `python scripts/demo_sequence.py`
- Single-command equivalent:
  - Enter one JSON command in `serial_console.py` (for example `{"T":105}`) to validate one command/response path.

## High-level architecture

The codebase centers on direct serial JSON control of a Waveshare RoArm-M2-Pro over `/dev/ttyUSB0` at `115200` baud.

- `scripts/serial_console.py` is an interactive command console:
  - `open_connection()` returns a configured `serial.Serial`. A daemon reader thread (`read_serial`) logs every incoming line. User-entered JSON is forwarded byte-for-byte.
- `scripts/demo_sequence.py` is a scripted motion runner:
  - Sends a predefined sequence of JSON movement commands and polls `{"T":105}` feedback until target joint positions are reached.
  - Position completion is treated as stable only after consecutive matching readings (filters encoder jitter).
- `scripts/logging_config.py` provides shared logging setup:
  - Creates `scripts/logs/` automatically.
  - Uses rotating file logs (5MB, 5 backups) plus INFO-level console logging.

## Key conventions in this repo

- Serial initialization pattern is consistent across scripts: `serial.Serial(..., dsrdtr=None)` followed by `setRTS(False)` and `setDTR(False)`. This prevents the ESP32 from auto-resetting on connect.
- Commands are newline-delimited JSON strings (`json.dumps(command) + '\n'`), and feedback is read line-by-line from serial.
- Movement completion is feedback-driven, not sleep-only: `demo_sequence.py` verifies per-joint tolerance against the `b/s/e/t` values returned in the `T:1051` response.
- Joint mapping lives in `JOINT_KEYS` (`base→b`, `shoulder→s`, `elbow→e`, `hand→t`) — add a new joint by extending this dict.
- Centralized logging is required: scripts call `setup_logging(__name__, <log_file>)` at module start and write runtime logs under `scripts/logs/`.
