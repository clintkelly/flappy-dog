"""
Tests for the difficulty curve in difficulty.py.
"""

import pytest

from difficulty import difficulty_t, gap_factor, lerp, spacing_factor


def test_lerp_returns_a_at_t_zero():
    assert lerp(10, 20, 0.0) == 10


def test_lerp_returns_b_at_t_one():
    assert lerp(10, 20, 1.0) == 20


def test_lerp_midpoint():
    assert lerp(10, 20, 0.5) == 15


def test_difficulty_t_zero_at_score_zero():
    assert difficulty_t(score=0, ramp_score=30) == 0.0


def test_difficulty_t_one_at_ramp():
    assert difficulty_t(score=30, ramp_score=30) == 1.0


def test_difficulty_t_clamps_to_one_above_ramp():
    assert difficulty_t(score=100, ramp_score=30) == 1.0


def test_difficulty_t_half_at_midpoint():
    assert difficulty_t(score=15, ramp_score=30) == 0.5


def test_difficulty_t_treats_zero_ramp_as_peak():
    """ ramp_score = 0 should mean "always at peak". """
    assert difficulty_t(score=0, ramp_score=0) == 1.0


@pytest.mark.parametrize(
    "score,expected",
    [
        (0, 1.30),    # easier start
        (15, 0.975),  # half-way: lerp(1.30, 0.65, 0.5)
        (30, 0.65),   # peak
        (60, 0.65),   # clamped
    ],
)
def test_gap_factor_curve(score, expected):
    factor = gap_factor(score, ramp_score=30, ratio_at_start=1.30, ratio_at_max=0.65)
    assert abs(factor - expected) < 1e-9


@pytest.mark.parametrize(
    "score,expected",
    [
        (0, 1.20),
        (15, 0.975),  # lerp(1.20, 0.75, 0.5)
        (30, 0.75),
        (45, 0.75),   # clamped
    ],
)
def test_spacing_factor_curve(score, expected):
    factor = spacing_factor(score, ramp_score=30, ratio_at_start=1.20, ratio_at_max=0.75)
    assert abs(factor - expected) < 1e-9
