"""
Tests for the player state machine in player_state.py.
"""

from player_state import (
    DashingState,
    InvincibleState,
    NormalState,
    PlayerState,
    ShieldedState,
)


class _MockPlayer:
    """ Stand-in for arcade.Sprite — none of the current states read from it,
    but the interface accepts a `player` for future state behavior. """


# --- NormalState ---------------------------------------------------------


def test_normal_collision_signals_game_over():
    state = NormalState()
    result = state.on_collision(_MockPlayer())
    assert result.game_over is True
    assert result.next_state is None


def test_normal_update_does_not_transition():
    state = NormalState()
    assert state.update(_MockPlayer(), delta_time=1.0) is None


def test_normal_is_not_invincible_and_does_not_absorb():
    state = NormalState()
    assert state.is_invincible() is False
    assert state.absorbs_obstacles() is False


# --- ShieldedState -------------------------------------------------------


def test_shielded_collision_absorbs_hit_and_transitions_to_normal():
    state = ShieldedState()
    result = state.on_collision(_MockPlayer())
    assert result.game_over is False
    assert isinstance(result.next_state, NormalState)


def test_shielded_update_does_not_self_transition():
    """ Shield persists until used — no timer. """
    state = ShieldedState()
    assert state.update(_MockPlayer(), delta_time=10.0) is None


def test_shielded_is_not_invincible():
    """ Shielded is a one-hit absorb, not collision-immune — the obstacle
    still counts and the state changes. is_invincible() reports False so
    the caller still performs collision detection. """
    state = ShieldedState()
    assert state.is_invincible() is False
    assert state.absorbs_obstacles() is False


# --- InvincibleState -----------------------------------------------------


def test_invincible_collision_no_game_over_no_transition():
    state = InvincibleState(duration=5.0)
    result = state.on_collision(_MockPlayer())
    assert result.game_over is False
    assert result.next_state is None


def test_invincible_update_decrements_timer():
    state = InvincibleState(duration=5.0)
    state.update(_MockPlayer(), delta_time=0.5)
    assert state.time_remaining == 4.5


def test_invincible_transitions_to_normal_when_time_expires():
    state = InvincibleState(duration=0.5)
    result = state.update(_MockPlayer(), delta_time=1.0)
    assert isinstance(result, NormalState)


def test_invincible_returns_none_while_still_active():
    state = InvincibleState(duration=5.0)
    assert state.update(_MockPlayer(), delta_time=0.5) is None


def test_invincible_reports_invincible_and_absorbs():
    state = InvincibleState()
    assert state.is_invincible() is True
    assert state.absorbs_obstacles() is True


def test_invincible_default_duration():
    state = InvincibleState()
    assert state.time_remaining == InvincibleState.DEFAULT_DURATION


# --- DashingState --------------------------------------------------------


def test_dashing_transitions_to_normal_when_expired():
    state = DashingState(duration=0.2)
    assert isinstance(state.update(_MockPlayer(), delta_time=0.3), NormalState)


def test_dashing_collision_still_kills_by_default():
    """ Future tuning may change this, but the placeholder keeps the
    behaviour conservative: dashing through a wall still hurts. """
    state = DashingState()
    result = state.on_collision(_MockPlayer())
    assert result.game_over is True


# --- Base class contract -------------------------------------------------


def test_base_player_state_defaults_are_safe():
    """ A bare PlayerState subclass should default to lethal collision and
    no transitions. New states only override what differs. """
    state = PlayerState()
    assert state.update(_MockPlayer(), delta_time=1.0) is None
    result = state.on_collision(_MockPlayer())
    assert result.game_over is True
    assert state.is_invincible() is False
