"""
Tests for the weighted spawn picker in spawn_table.py.
"""

import random

import pytest

from spawn_table import SpawnTable


def test_single_entry_always_returns_that_key():
    table = SpawnTable([("WOLF", 1.0)])
    assert table.pick(0.0) == "WOLF"
    assert table.pick(0.5) == "WOLF"
    assert table.pick(0.999) == "WOLF"


def test_two_entries_split_at_correct_threshold():
    table = SpawnTable([("A", 0.25), ("B", 0.75)])
    assert table.pick(0.0) == "A"
    assert table.pick(0.249) == "A"
    assert table.pick(0.25) == "B"
    assert table.pick(0.999) == "B"


def test_picks_match_spawn_pipes_distribution():
    """ Mirror the actual spawn_pipes table. """
    table = SpawnTable([
        ("WOLF", 0.05),
        ("SPIKY", 0.06),
        ("RING", 0.20),
        ("BOULDER", 0.20),
        ("COLUMN", 0.49),
    ])
    # Cumulative thresholds: 0.05, 0.11, 0.31, 0.51, 1.0
    assert table.pick(0.00) == "WOLF"
    assert table.pick(0.05) == "SPIKY"
    assert table.pick(0.11) == "RING"
    assert table.pick(0.31) == "BOULDER"
    assert table.pick(0.51) == "COLUMN"
    assert table.pick(0.99) == "COLUMN"


def test_normalizes_raw_weights():
    """ Weights can be integers or other non-normalized values — the table
    should normalize them. """
    table = SpawnTable([("A", 1), ("B", 1), ("C", 2)])
    # cumulative: 0.25, 0.5, 1.0
    assert table.pick(0.0) == "A"
    assert table.pick(0.24) == "A"
    assert table.pick(0.25) == "B"
    assert table.pick(0.49) == "B"
    assert table.pick(0.5) == "C"
    assert table.pick(0.99) == "C"


def test_zero_weight_entries_are_never_picked():
    table = SpawnTable([("ZERO", 0), ("ONE", 1)])
    for roll in (0.0, 0.25, 0.5, 0.75, 0.999):
        assert table.pick(roll) == "ONE"


def test_empty_table_raises():
    with pytest.raises(ValueError):
        SpawnTable([])


def test_all_zero_weights_raises():
    with pytest.raises(ValueError):
        SpawnTable([("A", 0), ("B", 0)])


def test_negative_weight_raises():
    with pytest.raises(ValueError):
        SpawnTable([("A", -1), ("B", 1)])


def test_roll_out_of_range_raises():
    table = SpawnTable([("A", 1)])
    with pytest.raises(ValueError):
        table.pick(1.0)
    with pytest.raises(ValueError):
        table.pick(-0.1)


def test_statistical_distribution_over_many_rolls():
    """ Sanity-check: with 10000 rolls the keys should appear at roughly
    the right frequencies (within a generous tolerance). """
    table = SpawnTable([("A", 0.10), ("B", 0.30), ("C", 0.60)])
    rng = random.Random(42)  # seeded for reproducibility
    counts = {"A": 0, "B": 0, "C": 0}
    for _ in range(10000):
        counts[table.pick(rng.random())] += 1
    assert 800 < counts["A"] < 1200    # ~10%
    assert 2700 < counts["B"] < 3300   # ~30%
    assert 5700 < counts["C"] < 6300   # ~60%
