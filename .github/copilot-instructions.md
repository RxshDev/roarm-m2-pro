# Copilot Instructions for `roarm-m2-pro`

## Build, test, and lint commands

This repository is script-based and currently has no dedicated build system, linter config, or automated test runner.

- Install dependency:
  - `pip install pyserial`
- Run the interactive serial connection test script:
  - `python roarm_tests/test_connection.py`
- Run the movement sequence script (acts as an end-to-end behavior check against hardware):
  - `python roarm_tests/sequenz.py`
- Single-test equivalent:
  - Use one JSON command in `test_connection.py` (for example `{"T":105}`) to validate one command/response path.

## High-level architecture

The codebase centers on direct serial JSON control of a Waveshare RoArm-M2-Pro over `/dev/ttyUSB0` at `115200` baud.

- `roarm_tests/test_connection.py` is an interactive command console:
  - Opens serial, starts a background reader thread, and forwards user-entered JSON commands line-by-line.
- `roarm_tests/sequenz.py` is a scripted motion runner:
  - Sends a predefined sequence of JSON movement commands and polls `{"T":105}` feedback until target joint positions are reached.
  - Position completion is treated as stable only after consecutive matching readings.
- `roarm_tests/logging_config.py` provides shared logging setup:
  - Creates `roarm_tests/logs/` automatically.
  - Uses rotating file logs (5MB, 5 backups) plus INFO-level console logging.

## Key conventions in this repo

- Serial initialization pattern is consistent across scripts: `serial.Serial(..., dsrdtr=None)` followed by `setRTS(False)` and `setDTR(False)`.
- Commands are newline-delimited JSON strings (`json.dumps(command) + '\n'`), and feedback is read line-by-line from serial.
- Movement completion is feedback-driven, not sleep-only: `sequenz.py` verifies per-joint tolerance against returned `b/s/e/t` values.
- Centralized logging is required: scripts call `setup_logging(__name__, <log_file>)` at module start and write runtime logs under `roarm_tests/logs/`.
- File naming includes `sequenz.py` (German spelling); preserve this name unless there is an explicit rename request.
