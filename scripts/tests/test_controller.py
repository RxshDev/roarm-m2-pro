"""Behavioural tests for ``RoArm`` against a fake transport (no hardware)."""

import json

from conftest import FakeTransport, position

from roarm import RoArm


def written_commands(transport: FakeTransport) -> list[dict]:
    return [json.loads(line) for line in transport.written]


# --- command construction ---------------------------------------------------


def test_move_joints_builds_rad_control_command(arm: RoArm, transport: FakeTransport):
    arm.move_joints(base=0.1, shoulder=0.2, elbow=0.3, hand=0.4, spd=600, acc=12, wait=False)

    cmd = json.loads(transport.written[-1])
    assert cmd == {
        "T": 102,
        "base": 0.1,
        "shoulder": 0.2,
        "elbow": 0.3,
        "hand": 0.4,
        "spd": 600,
        "acc": 12,
    }


def test_home_sends_move_init(arm: RoArm, transport: FakeTransport):
    arm.home()
    assert json.loads(transport.written[-1]) == {"T": 100}


def test_set_torque_on_and_off(arm: RoArm, transport: FakeTransport):
    arm.set_torque(True)
    assert json.loads(transport.written[-1]) == {"T": 210, "cmd": 1}
    arm.set_torque(False)
    assert json.loads(transport.written[-1]) == {"T": 210, "cmd": 0}


# --- tolerance check --------------------------------------------------------


def test_within_tolerance_just_inside():
    target = {"base": 1.0, "shoulder": 0.0, "elbow": 1.6, "hand": 3.14}
    pos = {"b": 1.05, "s": 0.0, "e": 1.6, "t": 3.14}
    assert RoArm._joints_within_tolerance(target, pos, 0.08) is True


def test_within_tolerance_just_outside():
    target = {"base": 1.0, "shoulder": 0.0, "elbow": 1.6, "hand": 3.14}
    pos = {"b": 1.2, "s": 0.0, "e": 1.6, "t": 3.14}  # base off by 0.2 > 0.08
    assert RoArm._joints_within_tolerance(target, pos, 0.08) is False


# --- feedback ---------------------------------------------------------------


def test_get_feedback_parses_position(arm: RoArm, transport: FakeTransport):
    transport.script_feedback(position(0.0, 0.0, 1.6, 3.14))
    pos = arm.get_feedback()
    assert pos is not None
    assert pos["b"] == 0.0 and pos["e"] == 1.6


def test_get_feedback_returns_none_without_response(arm: RoArm):
    assert arm.get_feedback() is None


def test_verify_connection_true_with_response(arm: RoArm, transport: FakeTransport):
    transport.script_feedback(position(0.0, 0.0, 1.6, 3.14))
    assert arm.verify_connection() is True


def test_verify_connection_false_without_response(arm: RoArm):
    assert arm.verify_connection() is False


# --- feedback-driven completion --------------------------------------------


def test_wait_succeeds_after_two_stable_readings(arm: RoArm, transport: FakeTransport):
    target = {"T": 102, "base": 0.0, "shoulder": 0.0, "elbow": 1.6, "hand": 3.14}
    # Two identical in-tolerance readings -> stable -> reached.
    transport.script_feedback(
        position(0.0, 0.0, 1.6, 3.14),
        position(0.0, 0.0, 1.6, 3.14),
    )
    assert arm.wait_until_reached(target) is True


def test_wait_resets_stability_on_out_of_tolerance(arm: RoArm, transport: FakeTransport):
    target = {"T": 102, "base": 0.0, "shoulder": 0.0, "elbow": 1.6, "hand": 3.14}
    # near (count 1), far (reset), near, near (count 2) -> reached.
    transport.script_feedback(
        position(0.0, 0.0, 1.6, 3.14),
        position(1.0, 0.0, 1.6, 3.14),
        position(0.0, 0.0, 1.6, 3.14),
        position(0.0, 0.0, 1.6, 3.14),
    )
    assert arm.wait_until_reached(target) is True


def test_wait_times_out_without_feedback(transport: FakeTransport):
    arm = RoArm(transport, poll_interval=0.0, send_delay=0.0, timeout=0.05)
    target = {"T": 102, "base": 0.0, "shoulder": 0.0, "elbow": 1.6, "hand": 3.14}
    assert arm.wait_until_reached(target) is False
