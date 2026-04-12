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
    ├── test_connection.py   # Serial connection test + manual JSON input
    └── sequenz.py           # Position-based movement sequence
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