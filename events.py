"""
Pure-Python event bus for cross-cutting game side effects.

Scoring sites (ring collected, coin collected, wolf rescued, score-zone
cleared, milestone crossed) used to inline 3-5 lines of sound + particle +
floating-text + milestone-check calls each. With this bus they emit one
typed event; sound, visuals, and (in the future) achievements / music
ducking / stats subscribe independently without touching the scoring site.

No arcade dependency — easy to unit-test against a list-appending fake
subscriber.

Usage:
    bus = EventBus()
    bus.subscribe(RingCollected, lambda e: arcade.play_sound(ring_sound))
    bus.emit(RingCollected(x=100, y=200, combo=3, bonus=5))
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Callable


# --- Event types ----------------------------------------------------------


class Event:
    """ Marker base class for all bus events. """


@dataclass(frozen=True)
class ScoreAwarded(Event):
    """ Fired whenever the score increases. Subscribers can use this for
    HUD updates, stats tracking, or achievement progress without caring
    about the *source* of the points. """
    points: int
    new_total: int


@dataclass(frozen=True)
class MilestoneCrossed(Event):
    """ Fired when the score crosses a multiple of MILESTONE_THRESHOLD.
    ``value`` is the milestone reached (e.g. 10, 20, 30). """
    value: int


@dataclass(frozen=True)
class ScoreZoneCleared(Event):
    """ Player passed a pipe/obstacle's invisible scoring trip-wire. """
    x: float
    y: float


@dataclass(frozen=True)
class RingCollected(Event):
    x: float
    y: float
    combo: int
    bonus: int


@dataclass(frozen=True)
class CoinCollected(Event):
    x: float
    y: float
    points: int


@dataclass(frozen=True)
class WolfRescued(Event):
    x: float
    y: float
    points: int


@dataclass(frozen=True)
class GameOver(Event):
    score: int


# --- Bus ------------------------------------------------------------------


Handler = Callable[[Event], None]


class EventBus:
    """ Type-keyed pub/sub. Subscribers receive only events of the type
    they registered for; dispatch is synchronous and ordered by
    subscription order. """

    def __init__(self):
        self._subscribers: dict[type, list[Handler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: Handler) -> None:
        self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: type, handler: Handler) -> None:
        """ Remove a previously-registered handler. No-op if the handler
        was never subscribed for this event type. """
        handlers = self._subscribers.get(event_type)
        if handlers and handler in handlers:
            handlers.remove(handler)

    def emit(self, event: Event) -> None:
        # Snapshot so handlers can safely (un)subscribe during dispatch.
        for handler in list(self._subscribers.get(type(event), ())):
            handler(event)

    def clear(self) -> None:
        """ Drop every subscriber. Useful when restarting a game so
        handlers bound to the previous view don't linger. """
        self._subscribers.clear()
