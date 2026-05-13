"""
State machine for one flame-thrower obstacle.

Cycle (per-instance, with a randomized initial phase so multiple throwers
fire out of sync):

    DORMANT (~2.5s, no flame)
    -> WARMING (~0.3s, 1 wisp at the base — warns the player)
    -> EXTENDING (~0.5s, segments grow upward from 1 to max)
    -> HOLDING (~1.0s, full-height flame)
    -> RECEDING (~0.4s, segments shrink back to 0)
    -> DORMANT (repeat)

Pure Python (no arcade) so transitions and ``segment_count`` derivation
can be tested deterministically. The main.py side composes this with the
base sprite + a pool of flame-segment sprites.
"""

from __future__ import annotations


DORMANT = "dormant"
WARMING = "warming"
EXTENDING = "extending"
HOLDING = "holding"
RECEDING = "receding"

_NEXT = {
    DORMANT: WARMING,
    WARMING: EXTENDING,
    EXTENDING: HOLDING,
    HOLDING: RECEDING,
    RECEDING: DORMANT,
}


class FlameThrowerCycle:
    """ Per-flame-thrower state + timer.

    ``initial_phase`` (seconds) advances the cycle so multiple throwers
    spawned at the same time don't all fire simultaneously. Pass a random
    value in ``[0, dormant_duration)`` for naturally staggered behavior.
    """

    def __init__(
        self,
        *,
        max_segments: int = 5,
        dormant_duration: float = 2.5,
        warming_duration: float = 0.3,
        extending_duration: float = 0.5,
        holding_duration: float = 1.0,
        receding_duration: float = 0.4,
        initial_phase: float = 0.0,
    ):
        if max_segments < 1:
            raise ValueError(f"max_segments must be >= 1, got {max_segments}")
        for name, value in (
            ("dormant_duration", dormant_duration),
            ("warming_duration", warming_duration),
            ("extending_duration", extending_duration),
            ("holding_duration", holding_duration),
            ("receding_duration", receding_duration),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be > 0, got {value}")
        self.max_segments = max_segments
        self.dormant_duration = dormant_duration
        self.warming_duration = warming_duration
        self.extending_duration = extending_duration
        self.holding_duration = holding_duration
        self.receding_duration = receding_duration

        self.state = DORMANT
        self.timer = 0.0
        # Advance into the cycle for stagger.
        if initial_phase > 0:
            self.update(initial_phase)

    @property
    def segment_count(self) -> int:
        """ Number of flame segments to draw this frame (0..max_segments). """
        if self.state == DORMANT:
            return 0
        if self.state == WARMING:
            return 1  # single wisp at the base — warning
        if self.state == EXTENDING:
            t = min(self.timer / self.extending_duration, 1.0)
            return max(1, int(round(t * self.max_segments)))
        if self.state == HOLDING:
            return self.max_segments
        if self.state == RECEDING:
            t = min(self.timer / self.receding_duration, 1.0)
            return max(0, self.max_segments - int(round(t * self.max_segments)))
        return 0

    def update(self, delta_time: float) -> None:
        """ Advance the state machine. Handles arbitrarily large delta_time
        (e.g. a frame skip) by walking through multiple state transitions. """
        self.timer += delta_time
        # Bound the loop so a pathological huge delta_time can't spin forever.
        for _ in range(64):
            duration = self._current_duration()
            if self.timer < duration:
                return
            self.timer -= duration
            self.state = _NEXT[self.state]

    def just_ignited(self, previous_state: str) -> bool:
        """ True when the state just transitioned from WARMING to EXTENDING
        (the "whoosh" moment — main.py uses this to play the ignition sound). """
        return previous_state == WARMING and self.state == EXTENDING

    def _current_duration(self) -> float:
        return {
            DORMANT: self.dormant_duration,
            WARMING: self.warming_duration,
            EXTENDING: self.extending_duration,
            HOLDING: self.holding_duration,
            RECEDING: self.receding_duration,
        }[self.state]
