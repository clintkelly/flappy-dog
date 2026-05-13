"""
Movement strategies for sprite-like objects (the Strategy pattern from
*Game Programming Patterns*).

Each strategy mutates an object with ``center_x`` and ``center_y`` attributes
(typically an ``arcade.Sprite``) every frame. Pure Python with no arcade
dependency, so each strategy is unit-testable against a small mock sprite.

Conventions:
- Per-frame velocities (``vx``, ``vy``) match the existing scroll constants
  in main.py (e.g. ``PIPE_SPEED = 3 px/frame``).
- Time-based rates (``angular_speed``) are radians/second and are multiplied
  by ``delta_time`` in ``update`` so they're frame-rate independent.
"""

from __future__ import annotations

import math


class Motion:
    """ Base class. Subclasses implement ``update(sprite, delta_time)``. """

    def update(self, sprite, delta_time: float) -> None:
        raise NotImplementedError


class LinearMotion(Motion):
    """ Constant per-frame velocity. """

    def __init__(self, vx: float = 0.0, vy: float = 0.0):
        self.vx = vx
        self.vy = vy

    def update(self, sprite, delta_time: float) -> None:
        sprite.center_x += self.vx
        sprite.center_y += self.vy


class CircularMotion(Motion):
    """ Orbit a center point that itself drifts at constant per-frame velocity.

    The orbit has a fixed radius and angular speed (radians/sec). Phase
    advances by ``angular_speed * delta_time`` each frame so the orbital
    motion is time-based; the orbit's center drifts by ``(vx, vy)`` per frame
    so it scrolls in lock-step with other obstacles when ``vx == -PIPE_SPEED``.
    """

    def __init__(
        self,
        base_x: float,
        base_y: float,
        radius: float,
        angular_speed: float,
        phase: float = 0.0,
        vx: float = 0.0,
        vy: float = 0.0,
    ):
        self.base_x = base_x
        self.base_y = base_y
        self.radius = radius
        self.angular_speed = angular_speed
        self.phase = phase
        self.vx = vx
        self.vy = vy

    def place(self, sprite) -> None:
        """ Snap the sprite to the current orbit point without advancing the
        motion. Useful immediately after constructing the motion so the sprite
        appears at the right starting position. """
        sprite.center_x = self.base_x + self.radius * math.cos(self.phase)
        sprite.center_y = self.base_y + self.radius * math.sin(self.phase)

    def update(self, sprite, delta_time: float) -> None:
        self.base_x += self.vx
        self.base_y += self.vy
        self.phase += self.angular_speed * delta_time
        self.place(sprite)


class SineMotion(Motion):
    """ Scroll horizontally at a constant per-frame velocity while bobbing
    vertically on a sine wave around ``base_y``.

    Used by floating obstacles (boulders, oscillating column gaps, animated
    rings) that all share the same kind of motion. ``amplitude == 0`` is a
    legal "still" configuration that effectively reduces to LinearMotion;
    that's how the bonus ring near the floor works.
    """

    def __init__(
        self,
        base_y: float,
        amplitude: float,
        phase_speed: float,
        phase: float = 0.0,
        vx: float = 0.0,
    ):
        self.base_y = base_y
        self.amplitude = amplitude
        self.phase_speed = phase_speed
        self.phase = phase
        self.vx = vx

    def place(self, sprite) -> None:
        """ Snap the sprite's y to the current sine position without
        advancing the phase. The x stays where the caller set it. """
        sprite.center_y = self.base_y + self.amplitude * math.sin(self.phase)

    def update(self, sprite, delta_time: float) -> None:
        sprite.center_x += self.vx
        self.phase += self.phase_speed * delta_time
        sprite.center_y = self.base_y + self.amplitude * math.sin(self.phase)
