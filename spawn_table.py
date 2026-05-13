"""
Weighted random picker for obstacle spawn types.

A small table of ``(key, weight)`` entries that returns one key on demand
proportional to its weight. Replaces the chained ``if/elif`` cascade in
``spawn_pipes`` so that adding a new obstacle type is one row instead of
recomputing several cumulative thresholds.

Pure Python, no arcade. The caller passes a random float in ``[0, 1)`` to
``pick`` (typically ``random.random()``) — this keeps the picker
deterministic for tests while letting the production code use the global
RNG.
"""

from __future__ import annotations

from typing import Iterable


class SpawnTable:
    """ Weighted-random table over a fixed set of keys.

    Construct with a list of ``(key, weight)`` tuples. Weights must be
    non-negative and sum to a positive value. Use ``pick(roll)`` to fetch
    the key whose cumulative range contains ``roll`` (a value in ``[0, 1)``).

    Weights are normalized internally so the caller can pass raw weights or
    probabilities — the table handles the math.
    """

    def __init__(self, entries: Iterable[tuple]):
        items = list(entries)
        if not items:
            raise ValueError("SpawnTable needs at least one entry")
        total = 0.0
        for key, weight in items:
            if weight < 0:
                raise ValueError(f"weight must be >= 0, got {weight} for {key!r}")
            total += weight
        if total <= 0:
            raise ValueError("weights must sum to a positive value")

        self.keys = [k for k, _ in items]
        # Pre-compute cumulative thresholds in [0, 1] for O(n) lookup.
        cumulative = []
        running = 0.0
        for _, weight in items:
            running += weight / total
            cumulative.append(running)
        # Snap the last entry to exactly 1.0 to defend against float drift.
        cumulative[-1] = 1.0
        self._thresholds = cumulative

    def pick(self, roll: float):
        """ Return the key for the given roll in ``[0, 1)``. """
        if not (0.0 <= roll < 1.0):
            raise ValueError(f"roll must be in [0, 1), got {roll}")
        for key, threshold in zip(self.keys, self._thresholds):
            if roll < threshold:
                return key
        # Shouldn't happen because the last threshold is 1.0, but be defensive.
        return self.keys[-1]
