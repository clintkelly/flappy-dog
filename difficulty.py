"""
Difficulty curve for Skywing Ruins.

A pure-function model of how the column-gap height and column-spacing
ratios change as the score climbs. At score 0 the player gets *easier*
than-base values (set by the ``*_AT_START`` knobs); at score >= ramp_score
they hit the tighter *peak* (set by the ``*_AT_MAX`` knobs). Linear lerp
in between.

This module is intentionally arcade-free so the curve can be plotted /
tweaked in a notebook and unit-tested in isolation.
"""

from __future__ import annotations


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def difficulty_t(score: int, ramp_score: int) -> float:
    """ Normalized progress through the difficulty ramp, clamped to ``[0, 1]``.

    ``ramp_score <= 0`` is treated as "always at peak" (return 1.0).
    """
    if ramp_score <= 0:
        return 1.0
    return min(score / ramp_score, 1.0)


def gap_factor(
    score: int,
    ramp_score: int,
    ratio_at_start: float,
    ratio_at_max: float,
) -> float:
    """ Multiplier applied to ``MIN_PIPE_CENTER_GAP``/``MAX_PIPE_CENTER_GAP``
    when picking the column gap height. Larger = easier. """
    return lerp(ratio_at_start, ratio_at_max, difficulty_t(score, ramp_score))


def spacing_factor(
    score: int,
    ramp_score: int,
    ratio_at_start: float,
    ratio_at_max: float,
) -> float:
    """ Multiplier applied to ``MIN_PIPE_SPACING``/``MAX_PIPE_SPACING``. """
    return lerp(ratio_at_start, ratio_at_max, difficulty_t(score, ramp_score))
