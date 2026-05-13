"""
Tests for scoring math in scoring.py.
"""

import pytest

from scoring import coin_streak_bonus, combo_bonus, combo_pitch, crossed_milestone


# --- combo_bonus ---------------------------------------------------------


@pytest.mark.parametrize(
    "combo,expected",
    [
        (1, 2),   # first ring = base
        (2, 3),
        (3, 4),
        (5, 6),
        (10, 11),
    ],
)
def test_combo_bonus_linear_with_step_one(combo, expected):
    assert combo_bonus(combo, base_points=2, bonus_step=1) == expected


def test_combo_bonus_step_zero_means_flat_base():
    for n in range(1, 6):
        assert combo_bonus(n, base_points=5, bonus_step=0) == 5


def test_combo_bonus_rejects_zero_or_negative():
    with pytest.raises(ValueError):
        combo_bonus(0, base_points=2, bonus_step=1)
    with pytest.raises(ValueError):
        combo_bonus(-1, base_points=2, bonus_step=1)


# --- combo_pitch ---------------------------------------------------------


def test_combo_pitch_first_ring_is_base():
    assert combo_pitch(1, pitch_step=0.06, pitch_max=1.9) == 1.0


def test_combo_pitch_increments_per_combo_step():
    assert abs(combo_pitch(2, pitch_step=0.06, pitch_max=1.9) - 1.06) < 1e-9
    assert abs(combo_pitch(5, pitch_step=0.06, pitch_max=1.9) - 1.24) < 1e-9


def test_combo_pitch_capped_at_max():
    # large combo should clamp
    assert combo_pitch(50, pitch_step=0.06, pitch_max=1.9) == 1.9


def test_combo_pitch_rejects_zero_or_negative():
    with pytest.raises(ValueError):
        combo_pitch(0, pitch_step=0.06, pitch_max=1.9)


# --- crossed_milestone ---------------------------------------------------


def test_crossed_milestone_returns_value_at_threshold():
    assert crossed_milestone(old_score=9, new_score=10, threshold=10) == 10


def test_crossed_milestone_none_when_not_crossed():
    assert crossed_milestone(old_score=11, new_score=12, threshold=10) is None
    assert crossed_milestone(old_score=0, new_score=9, threshold=10) is None


def test_crossed_milestone_picks_highest_when_jumping_multiple():
    """ A big combo can skip past several milestones; only celebrate the highest. """
    assert crossed_milestone(old_score=5, new_score=25, threshold=10) == 20


def test_crossed_milestone_handles_zero_threshold():
    assert crossed_milestone(old_score=0, new_score=10, threshold=0) is None


def test_crossed_milestone_handles_negative_threshold():
    assert crossed_milestone(old_score=0, new_score=10, threshold=-5) is None


def test_crossed_milestone_no_score_change():
    assert crossed_milestone(old_score=10, new_score=10, threshold=10) is None


# --- coin_streak_bonus ---------------------------------------------------


@pytest.mark.parametrize(
    "combo,expected",
    [
        (10, 10),   # tier 1: base
        (20, 20),   # tier 2: 2x
        (30, 40),   # tier 3: 4x
        (40, 80),   # tier 4: 8x (also matches cap)
        (50, 80),   # tier 5: capped
        (100, 80),  # tier 10: still capped
    ],
)
def test_coin_streak_bonus_doubles_then_caps(combo, expected):
    assert coin_streak_bonus(combo, threshold=10, base_bonus=10, cap=80) == expected


@pytest.mark.parametrize("combo", [1, 5, 9, 11, 19, 21, 99])
def test_coin_streak_bonus_returns_none_off_threshold(combo):
    assert coin_streak_bonus(combo, threshold=10, base_bonus=10, cap=80) is None


def test_coin_streak_bonus_zero_combo_is_none():
    assert coin_streak_bonus(0, threshold=10, base_bonus=10, cap=80) is None


def test_coin_streak_bonus_negative_combo_is_none():
    assert coin_streak_bonus(-10, threshold=10, base_bonus=10, cap=80) is None


def test_coin_streak_bonus_invalid_threshold_is_none():
    assert coin_streak_bonus(10, threshold=0, base_bonus=10, cap=80) is None
    assert coin_streak_bonus(10, threshold=-1, base_bonus=10, cap=80) is None


def test_coin_streak_bonus_invalid_base_is_none():
    assert coin_streak_bonus(10, threshold=10, base_bonus=0, cap=80) is None


def test_coin_streak_bonus_respects_custom_threshold():
    # Threshold = 5, base = 4, cap = 100: tier 1 fires at 5, tier 2 at 10.
    assert coin_streak_bonus(5, threshold=5, base_bonus=4, cap=100) == 4
    assert coin_streak_bonus(10, threshold=5, base_bonus=4, cap=100) == 8
    assert coin_streak_bonus(15, threshold=5, base_bonus=4, cap=100) == 16
    assert coin_streak_bonus(6, threshold=5, base_bonus=4, cap=100) is None
