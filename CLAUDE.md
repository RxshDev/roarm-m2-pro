# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

Direct serial JSON control of a Waveshare RoArm-M2-Pro (ESP32-based 4-DOF arm) over `/dev/ttyUSB0` at 115200 baud. The top-level directory is currently called `ros2_ws` but contains no ROS2 code yet — the repo is plain Python scripts and is a learning path toward ROS2 + CV later (see Roadmap in README.md).

## Common commands

```bash
pip install -r requirements.txt              # only dependency is pyserial
python scripts/serial_console.py             # interactive: enter raw JSON, e.g. {"T":105}
python scripts/demo_sequence.py              # run the 6-step movement sequence
ls /dev/ttyUSB0                              # verify the arm is connected
```

There is no build, lint, or test runner. "Single-test equivalent" is sending one JSON command (e.g. `{"T":105}` for position feedback) via `serial_console.py`.

## Architecture

Three files in `scripts/`:

- **`logging_config.py`** — `setup_logging(name, log_file)` returns `(logger, path)`. Auto-creates `scripts/logs/`, uses `RotatingFileHandler` (5MB × 5 backups) for DEBUG-and-up, console handler for INFO-and-up. A module-level `_configured` dict guards against duplicate handler attachment and returns the cached `(logger, path)` on repeat calls.
- **`serial_console.py`** — interactive REPL. `open_connection()` returns a `serial.Serial` (or `None`); `read_serial(ser)` runs on a daemon thread and logs incoming lines. The `ser` handle is passed explicitly — no module-globals.
- **`demo_sequence.py`** — scripted motion. Sends a list of `{"T":102, ...}` commands and **feedback-polls** `{"T":105}` until the returned `b/s/e/t` joint angles are within `tolerance=0.08` rad of the target. Completion requires **2 consecutive matching readings** (`stable_threshold`) to filter encoder jitter — don't drop this without understanding why.

### Conventions that must be preserved

- **Serial init pattern**: `serial.Serial(port, baudrate=115200, dsrdtr=None)` then `setRTS(False)` + `setDTR(False)`. The DTR/RTS toggle prevents the ESP32 from auto-resetting on connect.
- **Wire format**: newline-delimited JSON — `json.dumps(cmd) + '\n'`, encoded to bytes. Responses are read with `readline().decode()`.
- **Movement completion is feedback-driven, not sleep-based**. If you add new motion commands, route them through `send_command()` in `demo_sequence.py` so they wait on `wait_until_reached_position()` — never assume a `time.sleep()` is enough.
- **All scripts must call `setup_logging(__name__, <log_file>)` at module top**; logs go to `scripts/logs/` (gitignored).
- **Joint key mapping**: `JOINT_KEYS = {"base": "b", "shoulder": "s", "elbow": "e", "hand": "t"}` in `demo_sequence.py` maps command-side names to T:1051 feedback keys. Adding a wrist/extra joint = one line.

## JSON command quick reference

| Command | Purpose |
|---|---|
| `{"T":100}` | All joints to home |
| `{"T":102,"base":..,"shoulder":..,"elbow":..,"hand":..,"spd":..,"acc":..}` | Radian control of all joints |
| `{"T":105}` | Request joint feedback (returns `T:1051` with `b/s/e/t` rad + `x/y/z` mm + torques) |
| `{"T":210,"cmd":0/1}` | Torque off / on |

Joint home angles: base 0, shoulder 0, elbow ~1.6, hand 3.14 (closed). Hand 1.5 ≈ open. See README.md for full direction conventions and the feedback response schema.
