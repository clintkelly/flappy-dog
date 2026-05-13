"""
Frame-paced animation cycler.

A small helper that walks through a list of frames (typically textures) at
a fixed frame duration. Replaces the ``frame`` + ``time`` + advance/wrap
state-machine that bird/ring/coin animations all duplicated.

Pure Python, no arcade dependency — testable against an in-memory list of
mock items.
"""

from __future__ import annotations


class AnimationCycler:
    """ Cycle through ``frames`` at ``frame_duration`` seconds each.

    Tick once per frame with ``delta_time``, then read ``current`` for the
    active item. Wraps to ``frames[0]`` after the last frame. Handles
    arbitrarily large delta_time (e.g. a frame skip) by advancing
    multiple frames in one tick.
    """

    def __init__(self, frames, frame_duration: float):
        if not frames:
            raise ValueError("frames must be non-empty")
        if frame_duration <= 0:
            raise ValueError(f"frame_duration must be > 0, got {frame_duration}")
        self.frames = list(frames)
        self.frame_duration = frame_duration
        self.index = 0
        self._accumulator = 0.0

    @property
    def current(self):
        return self.frames[self.index]

    def tick(self, delta_time: float) -> None:
        self._accumulator += delta_time
        while self._accumulator >= self.frame_duration:
            self._accumulator -= self.frame_duration
            self.index = (self.index + 1) % len(self.frames)

    def reset(self) -> None:
        """ Restart at the first frame with no accumulated time. """
        self.index = 0
        self._accumulator = 0.0
