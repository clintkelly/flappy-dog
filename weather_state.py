"""
State machine for the rain / lightning / gust weather cycle.

Pure Python (no arcade) so the transitions and timer math can be tested
deterministically with a seeded ``random.Random`` instance. The arcade-side
``WeatherController`` in main.py composes this state machine with the visual
rain system, wind gusts, sound playback, and flash overlay.

Cycle:
    CLEAR (waiting) -> ONSET (silent pre-rain pause)
    -> STORM (rain + periodic flashes + delayed distant thunder
              + occasional wind gusts) -> CLEAR

In-storm flashes pair with a delayed PlayThunder so the rumble lags the
flash like real distant thunder. The obstacle-side "lightning bolt"
obstacle (see main.py) has its own, separate close-strike sound that
fires synchronously — these are two different lightning systems.

Each call to ``update(delta_time)`` returns a list of events the caller
should act on this frame.
"""

from __future__ import annotations

import random


# Weather cycle timings (seconds). These are the *behavioral* constants used
# by the state machine; the visual rain / gust / flash tuning lives in main.py.
STORM_INTERVAL_MIN = 5.0
STORM_INTERVAL_MAX = 18.0
STORM_DURATION_MIN = 18.0
STORM_DURATION_MAX = 36.0
STORM_ONSET_DURATION = 2.0          # silent pause between "storm decided" and rain starts
LIGHTNING_INTERVAL_MIN = 4.0        # seconds between in-storm distant flashes
LIGHTNING_INTERVAL_MAX = 9.0
LIGHTNING_FIRST_DELAY_MIN = 2.0     # delay before the FIRST in-storm flash
LIGHTNING_FIRST_DELAY_MAX = 4.5
THUNDER_DELAY_MIN = 0.4             # seconds between a distant flash and its rumble
THUNDER_DELAY_MAX = 1.1
GUST_SPAWN_INTERVAL_MIN = 7.0
GUST_SPAWN_INTERVAL_MAX = 14.0


# --- Events ---------------------------------------------------------------


class WeatherEvent:
    """ Marker base class for state-machine events. """


class FlashLightning(WeatherEvent):
    """ Caller should set the full-screen flash overlay alpha to max. """


class PlayThunder(WeatherEvent):
    """ Caller should play the distant thunder sound effect now. """


class StartRain(WeatherEvent):
    """ Caller should start the looped rain sound. """


class StopRain(WeatherEvent):
    """ Caller should stop the rain loop. """


class StormStart(WeatherEvent):
    """ The storm has just transitioned from ONSET to STORM — caller may
    want to reset rain drops to "fall in from above" so the storm visibly
    rolls in instead of appearing pre-populated. """


class SpawnGust(WeatherEvent):
    """ Caller should spawn a new wind-gust corridor. """


# --- State machine --------------------------------------------------------


class WeatherStateMachine:
    """ State machine that cycles CLEAR <-> ONSET <-> STORM and emits events
    the caller should act on. """

    CLEAR = "clear"
    ONSET = "onset"
    STORM = "storm"

    def __init__(self, rng: random.Random | None = None):
        self.rng = rng if rng is not None else random.Random()
        self.state = self.CLEAR
        self.time_until_next_storm = self.rng.uniform(STORM_INTERVAL_MIN, STORM_INTERVAL_MAX)
        self.storm_time_left = 0.0
        self.onset_timer = 0.0
        # In-STORM timers
        self.time_until_lightning = 0.0
        self.time_until_next_gust: float = float("inf")
        # Scheduled thunder clap (seconds from now), or None if no thunder is queued.
        self.pending_thunder_in: float | None = None

    def update(self, delta_time: float) -> list[WeatherEvent]:
        events: list[WeatherEvent] = []

        # Delayed thunder fires whenever its delay elapses, regardless of state.
        if self.pending_thunder_in is not None:
            self.pending_thunder_in -= delta_time
            if self.pending_thunder_in <= 0:
                events.append(PlayThunder())
                self.pending_thunder_in = None

        if self.state == self.CLEAR:
            self.time_until_next_storm -= delta_time
            if self.time_until_next_storm <= 0:
                self._begin_onset()
        elif self.state == self.ONSET:
            self._update_onset(delta_time, events)
        elif self.state == self.STORM:
            self._update_storm(delta_time, events)

        return events

    # ---- helpers (private) ----

    def _begin_onset(self) -> None:
        # Onset is now silent — no flash, no thunder. Just a brief pause
        # before rain begins, so the storm rolls in instead of starting flat.
        self.state = self.ONSET
        self.onset_timer = 0.0

    def _update_onset(self, delta_time: float, events: list[WeatherEvent]) -> None:
        self.onset_timer += delta_time
        if self.onset_timer >= STORM_ONSET_DURATION:
            self.state = self.STORM
            self.storm_time_left = self.rng.uniform(STORM_DURATION_MIN, STORM_DURATION_MAX)
            self.time_until_lightning = self.rng.uniform(
                LIGHTNING_FIRST_DELAY_MIN, LIGHTNING_FIRST_DELAY_MAX,
            )
            self.time_until_next_gust = self.rng.uniform(
                GUST_SPAWN_INTERVAL_MIN, GUST_SPAWN_INTERVAL_MAX,
            )
            events.append(StormStart())
            events.append(StartRain())

    def _update_storm(self, delta_time: float, events: list[WeatherEvent]) -> None:
        self.storm_time_left -= delta_time
        self.time_until_lightning -= delta_time
        if self.time_until_lightning <= 0:
            # In-storm distant flash. Thunder rumble follows after a delay
            # so the screen-wide effect reads as far-off lightning rather
            # than a strike right overhead.
            events.append(FlashLightning())
            self.pending_thunder_in = self.rng.uniform(THUNDER_DELAY_MIN, THUNDER_DELAY_MAX)
            self.time_until_lightning = self.rng.uniform(
                LIGHTNING_INTERVAL_MIN, LIGHTNING_INTERVAL_MAX,
            )

        self.time_until_next_gust -= delta_time
        if self.time_until_next_gust <= 0:
            events.append(SpawnGust())
            self.time_until_next_gust = self.rng.uniform(
                GUST_SPAWN_INTERVAL_MIN, GUST_SPAWN_INTERVAL_MAX,
            )

        if self.storm_time_left <= 0:
            self.state = self.CLEAR
            self.time_until_next_storm = self.rng.uniform(
                STORM_INTERVAL_MIN, STORM_INTERVAL_MAX,
            )
            self.time_until_next_gust = float("inf")
            events.append(StopRain())
