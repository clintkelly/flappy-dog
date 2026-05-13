"""
Tests for the FlameThrowerCycle in flame_thrower.py.
"""

import pytest

from flame_thrower import (
    DORMANT,
    EXTENDING,
    FlameThrowerCycle,
    HOLDING,
    RECEDING,
    WARMING,
)


def _make(**overrides):
    """ Helper: build a cycle with short, easy-to-reason-about durations. """
    defaults = dict(
        max_segments=5,
        dormant_duration=2.0,
        warming_duration=0.3,
        extending_duration=0.5,
        holding_duration=1.0,
        receding_duration=0.4,
    )
    defaults.update(overrides)
    return FlameThrowerCycle(**defaults)


def test_starts_in_dormant_with_no_segments():
    c = _make()
    assert c.state == DORMANT
    assert c.segment_count == 0


def test_transitions_dormant_to_warming():
    c = _make()
    c.update(2.0 + 0.001)
    assert c.state == WARMING
    assert c.segment_count == 1  # single wisp


def test_warming_lasts_for_its_duration():
    c = _make()
    c.update(2.0 + 0.001)      # -> WARMING
    c.update(0.29)             # still WARMING
    assert c.state == WARMING
    c.update(0.02)             # tip into EXTENDING
    assert c.state == EXTENDING


def test_extending_grows_segment_count_from_one_to_max():
    c = _make()
    c.update(2.0 + 0.3 + 0.001)    # well into EXTENDING
    assert c.state == EXTENDING
    assert c.segment_count == 1    # tiny elapsed -> still 1
    c.update(0.25)                 # midpoint of extending
    assert 2 <= c.segment_count <= 4
    c.update(0.3)                  # past end -> HOLDING
    assert c.state == HOLDING
    assert c.segment_count == 5


def test_holding_is_full_height():
    c = _make()
    c.update(2.0 + 0.3 + 0.5 + 0.001)   # just into HOLDING
    assert c.state == HOLDING
    assert c.segment_count == 5
    c.update(0.5)                       # midway through holding
    assert c.state == HOLDING
    assert c.segment_count == 5


def test_receding_shrinks_segment_count_to_zero():
    c = _make()
    c.update(2.0 + 0.3 + 0.5 + 1.0 + 0.001)  # just into RECEDING
    assert c.state == RECEDING
    assert c.segment_count == 5
    c.update(0.2)              # mid recede
    assert c.segment_count < 5
    c.update(0.3)              # past end -> DORMANT
    assert c.state == DORMANT
    assert c.segment_count == 0


def test_full_cycle_returns_to_dormant():
    c = _make()
    total = 2.0 + 0.3 + 0.5 + 1.0 + 0.4
    c.update(total + 0.001)
    assert c.state == DORMANT


def test_two_full_cycles_still_lands_in_dormant():
    c = _make()
    total = 2.0 + 0.3 + 0.5 + 1.0 + 0.4
    c.update(2 * total + 0.001)
    assert c.state == DORMANT


def test_initial_phase_advances_the_state_machine():
    # Start each instance partway through dormant so they fire out of sync.
    a = _make(initial_phase=0.0)
    b = _make(initial_phase=1.5)
    assert a.state == DORMANT
    assert b.state == DORMANT
    # After 0.6s more: a still dormant (0.6 < 2.0), b should be WARMING
    # (1.5 + 0.6 = 2.1 > 2.0).
    a.update(0.6)
    b.update(0.6)
    assert a.state == DORMANT
    assert b.state == WARMING


def test_initial_phase_pushes_into_warming():
    c = _make(initial_phase=2.1)
    assert c.state == WARMING


def test_just_ignited_only_on_warming_to_extending():
    c = _make()
    c.update(2.0 + 0.001)      # -> WARMING
    assert not c.just_ignited(DORMANT)
    c.update(0.3 + 0.001)      # -> EXTENDING
    assert c.just_ignited(WARMING) is True
    assert c.just_ignited(EXTENDING) is False
    assert c.just_ignited(DORMANT) is False


def test_huge_delta_time_eventually_returns():
    """ A pathological frame-skip should not infinite-loop. """
    c = _make()
    c.update(1_000_000.0)
    # State is well-defined and segment_count is bounded.
    assert c.state in {DORMANT, WARMING, EXTENDING, HOLDING, RECEDING}
    assert 0 <= c.segment_count <= c.max_segments


def test_rejects_invalid_max_segments():
    with pytest.raises(ValueError):
        FlameThrowerCycle(max_segments=0)


def test_rejects_non_positive_duration():
    with pytest.raises(ValueError):
        FlameThrowerCycle(dormant_duration=0)
    with pytest.raises(ValueError):
        FlameThrowerCycle(warming_duration=-1)
