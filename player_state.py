"""
Player state machine (the State pattern from *Game Programming Patterns*).

Each state encapsulates what happens when the bird flaps, collides with an
obstacle, or ticks one frame forward. Pure Python — testable against a
mock player object that doesn't need arcade.

Future power-ups slot in cleanly:
- A shield pickup transitions the player into ``ShieldedState``: the next
  obstacle hit gets absorbed and the player returns to ``NormalState``.
- A star pickup transitions into ``InvincibleState``: collisions are
  ignored entirely (caller can choose to detonate the obstacle), and the
  state self-times out back to Normal.
- A dash button would push the player into ``DashingState`` for a short
  burst, then back to Normal.

All four (Normal / Shielded / Invincible / Dashing) inherit from
``PlayerState`` and only override the methods that diverge from the
default behaviour.
"""

from __future__ import annotations


class CollisionResult:
    """ The outcome of a collision: did the game end, and what state next?

    Returned from ``PlayerState.on_collision`` so the GameView can decide
    whether to fire ``game_over()`` and/or transition states. ``next_state``
    is ``None`` if the player stays in the current state.
    """

    __slots__ = ("game_over", "next_state")

    def __init__(self, game_over: bool, next_state: "PlayerState | None" = None):
        self.game_over = game_over
        self.next_state = next_state


class PlayerState:
    """ Base class. Subclasses override only what differs from the default. """

    name = "base"

    def enter(self, player) -> None:
        """ Called when transitioning INTO this state. Hook for visual or
        audio side-effects (e.g., spawn a shield bubble around the bird). """
        return None

    def exit(self, player) -> None:
        """ Called when transitioning OUT of this state. """
        return None

    def update(self, player, delta_time: float) -> "PlayerState | None":
        """ Called once per frame while this state is active.

        Return a new state instance to transition, or ``None`` to stay. """
        return None

    def on_collision(self, player) -> CollisionResult:
        """ Player has overlapped a lethal obstacle. Default: game over. """
        return CollisionResult(game_over=True, next_state=None)

    def is_invincible(self) -> bool:
        """ While invincible, obstacles can still be touched but they don't
        kill — the caller may also choose to detonate them. """
        return False

    def absorbs_obstacles(self) -> bool:
        """ Star/invincibility power-up should *detonate* obstacles the bird
        collides with. This flag lets the caller distinguish a "shielded
        glance" (no detonation) from an "invincible plow-through". """
        return False


class NormalState(PlayerState):
    """ Default state: gravity applies, collisions are fatal, no special FX. """

    name = "normal"


class ShieldedState(PlayerState):
    """ One-hit shield: the next collision is absorbed and we drop back to
    NormalState. No timer — the shield lasts until used. """

    name = "shielded"

    def on_collision(self, player) -> CollisionResult:
        return CollisionResult(game_over=False, next_state=NormalState())


class InvincibleState(PlayerState):
    """ Time-limited invulnerability. Collisions don't end the game, and the
    state advertises both ``is_invincible`` and ``absorbs_obstacles`` so the
    caller can blow up whatever was touched. Decays to NormalState. """

    name = "invincible"
    DEFAULT_DURATION = 5.0

    def __init__(self, duration: float | None = None):
        super().__init__()
        self.time_remaining = self.DEFAULT_DURATION if duration is None else duration

    def update(self, player, delta_time: float) -> PlayerState | None:
        self.time_remaining -= delta_time
        if self.time_remaining <= 0:
            return NormalState()
        return None

    def on_collision(self, player) -> CollisionResult:
        return CollisionResult(game_over=False, next_state=None)

    def is_invincible(self) -> bool:
        return True

    def absorbs_obstacles(self) -> bool:
        return True


class DashingState(PlayerState):
    """ Brief forward burst (placeholder — not yet wired into gameplay).

    Holds an active timer. Collision behaviour matches Normal (deadly) by
    default, but a player who later wants invincibility-during-dash can
    swap this for a different ``on_collision``.
    """

    name = "dashing"
    DEFAULT_DURATION = 0.3
    DEFAULT_VX = 12.0  # forward velocity added per frame while dashing

    def __init__(self, duration: float | None = None, vx: float | None = None):
        super().__init__()
        self.time_remaining = self.DEFAULT_DURATION if duration is None else duration
        self.vx = self.DEFAULT_VX if vx is None else vx

    def update(self, player, delta_time: float) -> PlayerState | None:
        self.time_remaining -= delta_time
        if self.time_remaining <= 0:
            return NormalState()
        return None
