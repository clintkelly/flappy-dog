"""
Tests for the AnimationCycler in animation.py.
"""

import pytest

from animation import AnimationCycler


def test_starts_at_first_frame():
    cycler = AnimationCycler(["a", "b", "c"], frame_duration=0.1)
    assert cycler.current == "a"
    assert cycler.index == 0


def test_does_not_advance_before_frame_duration():
    cycler = AnimationCycler(["a", "b", "c"], frame_duration=0.1)
    cycler.tick(0.05)
    assert cycler.current == "a"


def test_advances_after_exactly_frame_duration():
    cycler = AnimationCycler(["a", "b", "c"], frame_duration=0.1)
    cycler.tick(0.1)
    assert cycler.current == "b"


def test_advances_with_accumulated_partial_ticks():
    """ Several sub-frame ticks should still advance once they add up. """
    cycler = AnimationCycler(["a", "b", "c"], frame_duration=0.1)
    for _ in range(2):
        cycler.tick(0.05)
    assert cycler.current == "b"


def test_wraps_to_first_frame_after_last():
    cycler = AnimationCycler(["a", "b"], frame_duration=0.1)
    cycler.tick(0.1)   # -> b
    cycler.tick(0.1)   # wraps -> a
    assert cycler.current == "a"


def test_handles_dt_jump_advancing_multiple_frames():
    """ A single big delta_time should advance multiple frames in one go. """
    cycler = AnimationCycler(["a", "b", "c", "d"], frame_duration=0.1)
    cycler.tick(0.25)  # 2.5 frames -> index = 2
    assert cycler.current == "c"


def test_handles_dt_jump_past_full_cycle():
    cycler = AnimationCycler(["a", "b", "c"], frame_duration=0.1)
    cycler.tick(0.4)  # 4 frames -> 4 % 3 = 1
    assert cycler.current == "b"


def test_reset_returns_to_first_frame():
    cycler = AnimationCycler(["a", "b", "c"], frame_duration=0.1)
    cycler.tick(0.5)
    cycler.reset()
    assert cycler.index == 0
    assert cycler.current == "a"


def test_reset_clears_partial_accumulator():
    cycler = AnimationCycler(["a", "b"], frame_duration=0.1)
    cycler.tick(0.07)  # not enough to advance
    cycler.reset()
    cycler.tick(0.05)
    assert cycler.current == "a"  # accumulator was cleared, still under threshold


def test_empty_frames_raises():
    with pytest.raises(ValueError):
        AnimationCycler([], frame_duration=0.1)


def test_zero_frame_duration_raises():
    with pytest.raises(ValueError):
        AnimationCycler(["a"], frame_duration=0)


def test_negative_frame_duration_raises():
    with pytest.raises(ValueError):
        AnimationCycler(["a"], frame_duration=-0.1)
