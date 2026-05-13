"""
Tests for the movement strategies in motion.py.
"""

import math
from dataclasses import dataclass

from motion import CircularMotion, LinearMotion


@dataclass
class _MockSprite:
    center_x: float = 0.0
    center_y: float = 0.0


def test_linear_motion_applies_constant_velocity_per_frame():
    sprite = _MockSprite(center_x=100, center_y=50)
    motion = LinearMotion(vx=-3, vy=2)
    motion.update(sprite, delta_time=1 / 60)
    assert sprite.center_x == 97
    assert sprite.center_y == 52
    motion.update(sprite, delta_time=1.0)
    # vx/vy are per-frame regardless of delta_time
    assert sprite.center_x == 94
    assert sprite.center_y == 54


def test_circular_motion_place_at_phase_zero():
    sprite = _MockSprite()
    motion = CircularMotion(
        base_x=500, base_y=400, radius=100, angular_speed=2.0, phase=0.0,
    )
    motion.place(sprite)
    # cos(0)=1, sin(0)=0
    assert sprite.center_x == 600
    assert sprite.center_y == 400


def test_circular_motion_place_at_quarter_turn():
    sprite = _MockSprite()
    motion = CircularMotion(
        base_x=500, base_y=400, radius=100, angular_speed=2.0,
        phase=math.pi / 2,
    )
    motion.place(sprite)
    assert abs(sprite.center_x - 500) < 1e-9
    assert abs(sprite.center_y - 500) < 1e-9


def test_circular_motion_advances_phase_with_delta_time():
    sprite = _MockSprite()
    motion = CircularMotion(
        base_x=500, base_y=400, radius=100,
        angular_speed=math.pi / 2,   # quarter-turn per second
        phase=0.0,
    )
    motion.update(sprite, delta_time=1.0)
    # After 1 sec, phase should be pi/2 → cos=0, sin=1 → (500, 500).
    assert abs(sprite.center_x - 500) < 1e-9
    assert abs(sprite.center_y - 500) < 1e-9


def test_circular_motion_base_drifts_per_frame():
    sprite = _MockSprite()
    motion = CircularMotion(
        base_x=500, base_y=400, radius=100,
        angular_speed=0.0, phase=0.0, vx=-3, vy=0.0,
    )
    motion.update(sprite, delta_time=1 / 60)
    assert motion.base_x == 497   # vx is per-frame
    assert motion.base_y == 400
    # angular_speed=0 means phase stays at 0 → sprite is at (base_x + radius, base_y)
    assert sprite.center_x == 597
    assert sprite.center_y == 400


def test_circular_motion_combined_drift_and_orbit():
    sprite = _MockSprite()
    motion = CircularMotion(
        base_x=500, base_y=400, radius=100,
        angular_speed=math.pi, phase=0.0, vx=-3,
    )
    motion.update(sprite, delta_time=0.5)
    # base_x drifted to 497, phase advanced to pi/2 → (497, 500)
    assert motion.base_x == 497
    assert abs(motion.phase - math.pi / 2) < 1e-9
    assert abs(sprite.center_x - 497) < 1e-9
    assert abs(sprite.center_y - 500) < 1e-9
