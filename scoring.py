"""
Score math for Skywing Ruins.

Pure functions for combo bonuses, sound-pitch ramps, and milestone-crossing
detection. Kept arcade-free so the math is unit-testable in isolation.
"""

from __future__ import annotations


def combo_bonus(combo_count: int, base_points: int, bonus_step: int) -> int:
    """ Points awarded for the *N*-th consecutive ring in a combo.

    The first ring (combo_count = 1) awards ``base_points``. Each subsequent
    ring adds ``bonus_step`` on top.

    Example: base=2, step=1 → 2, 3, 4, 5, ...
    """
    if combo_count < 1:
        raise ValueError(f"combo_count must be >= 1, got {combo_count}")
    return base_points + (combo_count - 1) * bonus_step


def combo_pitch(combo_count: int, pitch_step: float, pitch_max: float) -> float:
    """ ``speed`` multiplier for ``arcade.play_sound`` that pitches the chime
    up on each consecutive ring. Capped at ``pitch_max``. Combo 1 is 1.0.
    """
    if combo_count < 1:
        raise ValueError(f"combo_count must be >= 1, got {combo_count}")
    return min(1.0 + (combo_count - 1) * pitch_step, pitch_max)


def crossed_milestone(old_score: int, new_score: int, threshold: int) -> int | None:
    """ Return the milestone value crossed by going from ``old_score`` to
    ``new_score``, or ``None`` if no multiple of ``threshold`` was crossed.

    Used to fire a celebration once when the score crosses 10, 20, 30, …
    A single increment that jumps multiple thresholds (e.g. 5 → 25) returns
    the *highest* milestone touched (20), so we don't stack celebrations.
    """
    if threshold <= 0:
        return None
    if new_score // threshold > old_score // threshold:
        return (new_score // threshold) * threshold
    return None
