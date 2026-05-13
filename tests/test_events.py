"""
Tests for the EventBus and the event dataclasses in events.py.
"""

import pytest

from events import (
    CoinCollected,
    CoinStreakBonus,
    EventBus,
    Event,
    GameOver,
    MilestoneCrossed,
    RingCollected,
    ScoreAwarded,
    ScoreZoneCleared,
    WolfRescued,
)


# --- EventBus -------------------------------------------------------------


def test_subscribe_then_emit_calls_handler():
    bus = EventBus()
    received = []
    bus.subscribe(CoinCollected, received.append)
    event = CoinCollected(x=10, y=20, points=2)
    bus.emit(event)
    assert received == [event]


def test_emit_with_no_subscribers_is_noop():
    bus = EventBus()
    bus.emit(GameOver(score=0))  # must not raise


def test_multiple_subscribers_all_receive_in_order():
    bus = EventBus()
    order = []
    bus.subscribe(RingCollected, lambda e: order.append("a"))
    bus.subscribe(RingCollected, lambda e: order.append("b"))
    bus.subscribe(RingCollected, lambda e: order.append("c"))
    bus.emit(RingCollected(x=0, y=0, combo=1, bonus=1))
    assert order == ["a", "b", "c"]


def test_event_types_are_isolated():
    """ A subscriber to RingCollected should NOT see CoinCollected events. """
    bus = EventBus()
    rings = []
    coins = []
    bus.subscribe(RingCollected, rings.append)
    bus.subscribe(CoinCollected, coins.append)
    bus.emit(CoinCollected(x=0, y=0, points=2))
    assert rings == []
    assert len(coins) == 1


def test_unsubscribe_stops_further_delivery():
    bus = EventBus()
    received = []
    handler = received.append
    bus.subscribe(GameOver, handler)
    bus.emit(GameOver(score=5))
    bus.unsubscribe(GameOver, handler)
    bus.emit(GameOver(score=10))
    assert len(received) == 1
    assert received[0].score == 5


def test_unsubscribe_unknown_handler_is_noop():
    bus = EventBus()
    bus.unsubscribe(GameOver, lambda e: None)  # never subscribed
    bus.unsubscribe(CoinCollected, lambda e: None)  # event type never seen


def test_clear_removes_all_subscribers():
    bus = EventBus()
    received = []
    bus.subscribe(RingCollected, received.append)
    bus.subscribe(CoinCollected, received.append)
    bus.clear()
    bus.emit(RingCollected(x=0, y=0, combo=1, bonus=1))
    bus.emit(CoinCollected(x=0, y=0, points=2))
    assert received == []


def test_handler_subscribing_during_dispatch_does_not_fire_in_same_emit():
    """ A handler added mid-dispatch should not receive the in-flight event,
    but should receive subsequent ones. """
    bus = EventBus()
    received = []

    def late_handler(e):
        received.append("late")

    def adder(e):
        bus.subscribe(GameOver, late_handler)

    bus.subscribe(GameOver, adder)
    bus.emit(GameOver(score=1))
    assert received == []  # late_handler did not see the in-flight event
    bus.emit(GameOver(score=2))
    assert received == ["late"]


def test_handler_unsubscribing_during_dispatch_does_not_break_iteration():
    bus = EventBus()
    received = []

    def first(e):
        received.append("first")
        bus.unsubscribe(GameOver, second)

    def second(e):
        received.append("second")

    bus.subscribe(GameOver, first)
    bus.subscribe(GameOver, second)
    # second is still in the snapshot, so it fires this round.
    bus.emit(GameOver(score=1))
    assert received == ["first", "second"]
    received.clear()
    # Next emit, second is gone.
    bus.emit(GameOver(score=2))
    assert received == ["first"]


def test_handler_self_unsubscribing_in_dispatch():
    bus = EventBus()
    received = []

    def once(e):
        received.append(e.score)
        bus.unsubscribe(GameOver, once)

    bus.subscribe(GameOver, once)
    bus.emit(GameOver(score=1))
    bus.emit(GameOver(score=2))
    assert received == [1]


# --- Event dataclasses ----------------------------------------------------


def test_events_are_frozen():
    event = CoinCollected(x=1, y=2, points=3)
    with pytest.raises(Exception):
        event.points = 99  # type: ignore[misc]


def test_events_compare_by_value():
    a = RingCollected(x=1, y=2, combo=3, bonus=4)
    b = RingCollected(x=1, y=2, combo=3, bonus=4)
    c = RingCollected(x=1, y=2, combo=3, bonus=5)
    assert a == b
    assert a != c


def test_all_event_types_inherit_marker():
    for cls in (
        ScoreAwarded,
        MilestoneCrossed,
        ScoreZoneCleared,
        RingCollected,
        CoinCollected,
        CoinStreakBonus,
        WolfRescued,
        GameOver,
    ):
        assert issubclass(cls, Event)
