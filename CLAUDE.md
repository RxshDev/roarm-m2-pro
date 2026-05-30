# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

Direct serial JSON control of a Waveshare RoArm-M2-Pro (ESP32-based 4-DOF arm) over `/dev/ttyUSB0` at 115200 baud. The top-level directory is currently called `ros2_ws` but contains no ROS2 code yet — the repo is plain Python scripts and is a learning path toward ROS2 + CV later (see Roadmap in README.md).

## Common commands

```bash
pip install -r requirements.txt              # runtime: only dependency is pyserial
pip install -r requirements-dev.txt          # dev: adds pytest (use a venv on Arch)
python scripts/serial_console.py             # interactive: enter raw JSON, e.g. {"T":105}
python scripts/demo_sequence.py              # run the 6-step movement sequence
pytest                                       # run the unit tests (no hardware needed)
ls /dev/ttyUSB0                              # verify the arm is connected
```

There is no build or lint runner. Unit tests (`pytest`) cover the `RoArm` logic against a fake transport; the full end-to-end check still requires sending JSON to the real arm.

## Architecture

The arm-control logic lives in a small library package, `scripts/roarm/`, split into **two layers**. The two top-level scripts are thin apps that drive it.

- **`roarm/transport.py` — `SerialTransport`**: the *wire*. The only place that touches `serial.Serial`. Methods: `open()`/`close()`, `write_line(text)` (appends `\n`, encodes, flushes), `read_line()` (tolerant decode + strip), `in_waiting`, `flush_input()`. Context-manager capable.
- **`roarm/controller.py` — `RoArm`**: the arm's *language*. Holds an injected transport (not a raw serial handle). High-level methods: `move_joints(base, shoulder, elbow, hand, spd, acc, wait=True)`, `home()`, `set_torque(on)`, `get_feedback()`, `verify_connection()`, `wait_until_reached(target)`. `RoArm.connect(port, baudrate, settle=, **kwargs)` builds + opens a `SerialTransport` and returns a ready controller. Also defines the `Command` IntEnum (T-codes) and `JOINT_KEYS`.
- **`logging_config.py`** — `setup_logging(name, log_file)` returns `(logger, path)`. Auto-creates `scripts/logs/`, uses `RotatingFileHandler` (5MB × 5 backups) for DEBUG-and-up, console handler for INFO-and-up. A module-level `_configured` dict guards against duplicate handler attachment and returns the cached `(logger, path)` on repeat calls. **`RoArm` does not configure logging itself** — apps call `setup_logging(...)` and pass the logger into `RoArm(..., logger=logger)`.
- **`serial_console.py`** — interactive REPL. Calls `RoArm.connect()`, runs a daemon thread that logs `arm.read_line()`, forwards raw user JSON via `arm.send_raw(...)`.
- **`demo_sequence.py`** — scripted motion. A `SEQUENCE` of `(description, joint kwargs)` driven through `arm.move_joints(**kwargs)`; each call **feedback-polls** `{"T":105}` until the `b/s/e/t` angles are within `tolerance=0.08` rad. Completion requires **2 consecutive matching readings** (`stable_threshold`) to filter encoder jitter — don't drop this without understanding why.
- **`tests/`** — pytest. `conftest.py` provides `FakeTransport` (records writes, releases scripted feedback per `{"T":105}` request) and an `arm` fixture with zeroed delays. `test_controller.py` covers command construction, tolerance, and the stability/timeout logic; `test_transport.py` covers line encoding/decoding.

### Conventions that must be preserved

- **Serial init pattern** (in `SerialTransport.open()`): `serial.Serial(port, baudrate=115200, dsrdtr=None)` then `setRTS(False)` + `setDTR(False)`. The DTR/RTS toggle prevents the ESP32 from auto-resetting on connect.
- **Wire format** (in `SerialTransport`): newline-delimited JSON — `json.dumps(cmd) + '\n'`, encoded to bytes. Responses read with `readline().decode(...)`. Keep this the only place that knows the wire format.
- **Movement completion is feedback-driven, not sleep-based**. New motion methods on `RoArm` must block on `wait_until_reached()` (as `move_joints` does) — never assume a `time.sleep()` is enough.
- **Apps configure logging, the library doesn't**: scripts call `setup_logging(__name__, <log_file>)` at module top and pass the logger into `RoArm`; logs go to `scripts/logs/` (gitignored).
- **Joint key mapping**: `JOINT_KEYS = {"base": "b", "shoulder": "s", "elbow": "e", "hand": "t"}` in `roarm/controller.py` maps command-side names to T:1051 feedback keys. Adding a wrist/extra joint = one line.
- **T-codes are named** in the `Command` IntEnum (`HOME=100`, `MOVE_RAD=102`, `FEEDBACK=105`, `TORQUE=210`) — prefer it over raw magic numbers.

## JSON command quick reference

| Command | Purpose |
|---|---|
| `{"T":100}` | All joints to home |
| `{"T":102,"base":..,"shoulder":..,"elbow":..,"hand":..,"spd":..,"acc":..}` | Radian control of all joints |
| `{"T":105}` | Request joint feedback (returns `T:1051` with `b/s/e/t` rad + `x/y/z` mm + torques) |
| `{"T":210,"cmd":0/1}` | Torque off / on |

Joint home angles: base 0, shoulder 0, elbow ~1.6, hand 3.14 (closed). Hand 1.5 ≈ open. See README.md for full direction conventions and the feedback response schema.
