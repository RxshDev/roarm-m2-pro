# RoArm-M2-Pro Control

> Learning path from raw serial communication to ROS2, Computer Vision and autonomous manipulation.

## Hardware

| Component | Details |
|---|---|
| Robotic Arm | Waveshare RoArm-M2-Pro |
| Controller | ESP32 (onboard) |
| Communication | USB/UART Serial @ 115200 baud |
| Protocol | JSON commands |
| Camera | IMX335 5MP 2K (eye-in-hand, USB) |
| Host | ThinkPad T14 Gen5 — Arch Linux |

### Joint Configuration

| Joint | Servo | DOF | Note |
|---|---|---|---|
| Base | ST3235 | 1 | 360° rotation |
| Shoulder | ST3235 × 2 | 1 | Dual-drive, doubled torque |
| Elbow | ST3235 | 1 | Carbon fiber segment |
| EoAT / Gripper | ST3215-HS | 1 | Precise grip force control |

## Project Structure

```
roarm-m2-pro/
└── roarm_tests/
    ├── logging_config.py      # Centralized logging configuration
    ├── test_connection.py      # Serial connection test + manual JSON input
    ├── sequenz.py              # Position-based movement sequence
    ├── .gitignore              # Exclude logs and cache from git
    └── logs/                   # Runtime logs (auto-generated, not in git)
        ├── roarm_debug.log     # Logs from test_connection.py
        └── roarm_sequence.log  # Logs from sequenz.py
```

## Getting Started

### Requirements

```bash
pip install pyserial
```

### Connect the Arm

1. Connect 12V 5A power supply
2. Connect USB cable to ThinkPad
3. Power on the arm — joints move to home position
4. Verify connection:

```bash
ls /dev/ttyUSB0
```

### Run the Connection Test

```bash
python roarm_tests/test_connection.py
```

Type JSON commands directly in the terminal:

```json
{"T":105}
{"T":100}
{"T":210,"cmd":0}
```

### Run the Movement Sequence

```bash
python roarm_tests/sequenz.py
```

The arm executes 6 steps with position-based control — each step waits until the target position is confirmed before proceeding.

## Logging

Both scripts automatically log all operations to the `logs/` directory:

- **`roarm_debug.log`** — Connection tests and manual command execution
- **`roarm_sequence.log`** — Movement sequence execution and timing

Log files are automatically rotated when they exceed 5MB. The last 5 backups are preserved.

**Log levels:**
- `DEBUG` — Detailed command/response info (file only)
- `INFO` — Important events (console + file)
- `WARNING` — Warnings like user cancellations (console + file)
- `ERROR` — Critical failures (console + file)

Example log entry:
```
2026-04-20 14:32:15 - __main__ - INFO - Serial port opened: /dev/ttyUSB0
2026-04-20 14:32:16 - __main__ - INFO - Step 1/6: Home position
2026-04-20 14:32:20 - __main__ - INFO - Target position reached (stable)
```

The `logs/` directory is excluded from git via `.gitignore` to keep the repository clean.

## Optimizations

The control scripts have been optimized for reliability and performance:

**Serial Communication**
- Immediate buffer flushing after commands for faster responsiveness
- Reduced communication delays (0.5s → 0.2s for commands)
- Optimized polling rate for position feedback

**Position Control**
- Stability verification (2 consecutive stable readings before confirming target)
- Smart output filtering (reduces console spam during movement)
- Individual joint tolerance checking

**Code Quality**
- Centralized logging configuration (`logging_config.py`) — DRY principle
- Comprehensive error handling with detailed logging
- Guard against duplicate logging handlers

## JSON Command Reference

| Command | Type | Description |
|---|---|---|
| `{"T":100}` | CMD_MOVE_INIT | All joints to home position |
| `{"T":102,"base":0,"shoulder":0,"elbow":1.6,"hand":3.14,"spd":500,"acc":10}` | CMD_SERVO_RAD_CTRL | Control all joints simultaneously |
| `{"T":105}` | CMD_SERVO_RAD_FEEDBACK | Get current position of all joints |
| `{"T":210,"cmd":0}` | CMD_TORQUE_LOCK | Torque off (manual movement) |
| `{"T":210,"cmd":1}` | CMD_TORQUE_LOCK | Torque on |

## Joint Direction Conventions

| Joint | Positive (+) | Negative (−) | Home |
|---|---|---|---|
| Base | Left | Right | 0 rad |
| Shoulder | Forward / down | Backward / up | ~0 rad |
| Elbow | Down | Up | ~1.6 rad |
| EoAT / Gripper | Closed | Open | 3.14 rad |

**Angle conversion:** `degrees × (π / 180) = radians`

Common values:
- 45° = 0.7854 rad
- 90° = 1.5708 rad
- 180° = 3.1416 rad

## Feedback Response Format

```json
{
  "T": 1051,
  "x": 307.47, "y": -16.52, "z": 231.49,
  "b": -0.053, "s": -0.009, "e": 1.599, "t": 3.147,
  "torB": 149, "torS": -25, "torE": 85, "torH": 16
}
```

| Field | Meaning | Unit |
|---|---|---|
| x, y, z | EoAT position in space | mm |
| b | Base angle | rad |
| s | Shoulder angle | rad |
| e | Elbow angle | rad |
| t | EoAT / Gripper angle | rad |
| torB/S/E/H | Current load per joint | raw |

## Roadmap

- [x] Serial connection established
- [x] JSON command communication
- [x] Position-based movement control
- [x] Multi-step movement sequence
- [ ] Camera integration (IMX335)
- [ ] Object detection (YOLOv8)
- [ ] Hand/face tracking
- [ ] ROS2 integration
- [ ] Autonomous pick & place

## References

- [Waveshare RoArm-M2-S Wiki](https://www.waveshare.com/wiki/RoArm-M2-S)
- [JSON Command Reference](https://www.waveshare.com/wiki/RoArm-M2-S_JSON_Command_Meaning)
- [Waveshare GitHub](https://github.com/waveshareteam/roarm_m2)