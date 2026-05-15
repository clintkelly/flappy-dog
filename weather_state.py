"""
State machine for the rain / lightning / gust weather cycle.

Pure Python (no arcade) so the transitions and timer math can be tested
deterministically with a seeded ``random.Random`` instance. The arcade-side
``WeatherController`` in main.py composes this state machine with the visual
rain system, wind gusts, sound playback, and flash overlay.

Cycle:
    CLEAR (waiting) -> ONSET (lightning flash + delayed thunder pre-roll)
    -> STORM (rain + periodic lightning + occasional wind gusts) -> CLEAR

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
STORM_ONSET_FLASH_DELAY = 0.6       # seconds from onset-flash to thunder
STORM_ONSET_RAIN_DELAY = 1.4        # seconds from thunder to rain begin
LIGHTNING_INTERVAL_MIN = 4.0        # seconds between in-storm lightning events
LIGHTNING_INTERVAL_MAX = 9.0
LIGHTNING_FIRST_DELAY_MIN = 2.0     # delay before the FIRST in-storm lightning
LIGHTNING_FIRST_DELAY_MAX = 4.5
THUNDER_DELAY_MIN = 0.4             # seconds between a flash and its thunder
THUNDER_DELAY_MAX = 1.1
GUST_SPAWN_INTERVAL_MIN = 5.0
GUST_SPAWN_INTERVAL_MAX = 11.0


# --- Events ---------------------------------------------------------------


class WeatherEvent:
    """ Marker base class for state-machine events. """


class FlashLightning(WeatherEvent):
    """ Caller should set the full-screen flash overlay alpha to max. """


class PlayThunder(WeatherEvent):
    """ Caller should play the thunder sound effect now. """


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
        # ONSET sub-stage timer: 0 = waiting for thunder-after-flash, 1 = waiting for rain.
        self.onset_stage = 0
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
                self._begin_onset(events)
        elif self.state == self.ONSET:
            self._update_onset(delta_time, events)
        elif self.state == self.STORM:
            self._update_storm(delta_time, events)

        return events

    # ---- helpers (private) ----

    def _begin_onset(self, events: list[WeatherEvent]) -> None:
        self.state = self.ONSET
        self.onset_stage = 0
        self.onset_timer = 0.0
        events.append(FlashLightning())
        # Thunder follows after STORM_ONSET_FLASH_DELAY seconds.
        self.pending_thunder_in = STORM_ONSET_FLASH_DELAY

    def _update_onset(self, delta_time: float, events: list[WeatherEvent]) -> None:
        self.onset_timer += delta_time
        if self.onset_stage == 0 and self.onset_timer >= STORM_ONSET_FLASH_DELAY:
            self.onset_stage = 1
            self.onset_timer = 0.0
        elif self.onset_stage == 1 and self.onset_timer >= STORM_ONSET_RAIN_DELAY:
            # Transition to STORM.
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
