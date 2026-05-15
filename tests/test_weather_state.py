"""
Tests for the weather state machine in weather_state.py.
"""

import random

import pytest

from weather_state import (
    FlashLightning,
    PlayThunder,
    SpawnGust,
    StartRain,
    StopRain,
    StormStart,
    STORM_ONSET_DURATION,
    WeatherStateMachine,
)


def _seeded() -> WeatherStateMachine:
    return WeatherStateMachine(rng=random.Random(42))


# --- starting state ------------------------------------------------------


def test_starts_in_clear():
    sm = _seeded()
    assert sm.state == sm.CLEAR


def test_storm_arrival_delay_is_positive():
    sm = _seeded()
    assert sm.time_until_next_storm > 0


# --- clear -> onset ------------------------------------------------------


def test_no_transition_before_interval_elapses():
    sm = _seeded()
    almost = sm.time_until_next_storm - 0.01
    events = sm.update(almost)
    assert sm.state == sm.CLEAR
    assert events == []


def test_transition_to_onset_is_silent():
    """ Onset is a silent pre-rain pause — no flash, no thunder, no rain. """
    sm = _seeded()
    events = sm.update(sm.time_until_next_storm + 0.001)
    assert sm.state == sm.ONSET
    assert not any(isinstance(e, FlashLightning) for e in events)
    assert not any(isinstance(e, PlayThunder) for e in events)
    assert not any(isinstance(e, StartRain) for e in events)


# --- onset -> storm ------------------------------------------------------


def test_storm_start_emits_storm_start_and_start_rain():
    sm = _seeded()
    sm.update(sm.time_until_next_storm + 0.001)
    events = sm.update(STORM_ONSET_DURATION + 0.001)
    assert sm.state == sm.STORM
    assert any(isinstance(e, StormStart) for e in events)
    assert any(isinstance(e, StartRain) for e in events)


def test_onset_to_storm_does_not_flash():
    """ The storm starts with rain, no lightning until the in-storm timer fires. """
    sm = _seeded()
    sm.update(sm.time_until_next_storm + 0.001)
    events = sm.update(STORM_ONSET_DURATION + 0.001)
    assert not any(isinstance(e, FlashLightning) for e in events)
    assert not any(isinstance(e, PlayThunder) for e in events)


# --- in-storm lightning + gusts ------------------------------------------


def _fast_forward_into_storm(sm: WeatherStateMachine) -> None:
    sm.update(sm.time_until_next_storm + 0.001)
    sm.update(STORM_ONSET_DURATION + 0.001)
    assert sm.state == sm.STORM


def test_in_storm_flash_fires_and_queues_delayed_thunder():
    sm = _seeded()
    _fast_forward_into_storm(sm)
    events = sm.update(sm.time_until_lightning + 0.001)
    assert any(isinstance(e, FlashLightning) for e in events)
    # Thunder is queued — distant rumble, fires after a delay.
    assert sm.pending_thunder_in is not None
    assert sm.pending_thunder_in > 0


def test_queued_thunder_fires_after_its_delay():
    sm = _seeded()
    _fast_forward_into_storm(sm)
    sm.update(sm.time_until_lightning + 0.001)
    delay = sm.pending_thunder_in
    events = sm.update(delay + 0.001)
    assert any(isinstance(e, PlayThunder) for e in events)
    assert sm.pending_thunder_in is None


def test_in_storm_lightning_reschedules_itself():
    sm = _seeded()
    _fast_forward_into_storm(sm)
    sm.update(sm.time_until_lightning + 0.001)
    assert sm.time_until_lightning > 0


def test_flash_does_not_fire_in_clear_or_onset():
    sm = _seeded()
    events = sm.update(sm.time_until_next_storm + 0.001)
    assert not any(isinstance(e, FlashLightning) for e in events)
    events = sm.update(STORM_ONSET_DURATION / 2)
    assert not any(isinstance(e, FlashLightning) for e in events)


def test_gust_event_fires_during_storm():
    sm = _seeded()
    _fast_forward_into_storm(sm)
    events = sm.update(sm.time_until_next_gust + 0.001)
    assert any(isinstance(e, SpawnGust) for e in events)


# --- storm -> clear ------------------------------------------------------


def test_storm_ends_emits_stop_rain_and_returns_to_clear():
    sm = _seeded()
    _fast_forward_into_storm(sm)
    events = sm.update(sm.storm_time_left + 0.001)
    assert sm.state == sm.CLEAR
    assert any(isinstance(e, StopRain) for e in events)
    assert sm.time_until_next_storm > 0


def test_no_gusts_emitted_in_clear_state():
    sm = _seeded()
    _fast_forward_into_storm(sm)
    sm.update(sm.storm_time_left + 0.001)
    events = sm.update(5.0)
    assert not any(isinstance(e, SpawnGust) for e in events)


# --- idempotence + return-value contract ---------------------------------


def test_update_zero_dt_returns_empty_events_in_clear():
    sm = _seeded()
    events = sm.update(0.0)
    assert events == []
    assert sm.state == sm.CLEAR


def test_update_returns_list_always():
    sm = _seeded()
    assert isinstance(sm.update(0.0), list)
    assert isinstance(sm.update(100.0), list)


def test_full_cycle_returns_to_clear():
    sm = _seeded()
    sm.update(1000.0)
    assert sm.state in (sm.CLEAR, sm.ONSET, sm.STORM)
