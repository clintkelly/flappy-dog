"""
Tests for ScoreStore — the JSON-backed score history layer.
"""

import json
from pathlib import Path

import pytest

from score_store import DEFAULT_PROFILE, ScoreStore


@pytest.fixture
def store_path(tmp_path: Path) -> Path:
    return tmp_path / "scores.json"


def test_load_when_file_missing_returns_defaults(store_path):
    store = ScoreStore.load(store_path)
    assert store.current_profile == DEFAULT_PROFILE
    assert store.data["scores"] == []


def test_save_and_load_roundtrip(store_path):
    store = ScoreStore(store_path)
    store.current_profile = "Clint"
    store.record("Clint", 42)
    store.save()

    reloaded = ScoreStore.load(store_path)
    assert reloaded.current_profile == "Clint"
    assert len(reloaded.data["scores"]) == 1
    assert reloaded.data["scores"][0]["score"] == 42


def test_record_appends_entry_with_required_fields(store_path):
    store = ScoreStore(store_path)
    store.record("Alice", 7)

    entry = store.data["scores"][0]
    assert entry["profile"] == "Alice"
    assert entry["score"] == 7
    assert "timestamp" in entry


def test_record_coerces_score_to_int(store_path):
    store = ScoreStore(store_path)
    store.record("Alice", 7.9)
    assert store.data["scores"][0]["score"] == 7


def test_personal_best_filters_by_profile(store_path):
    store = ScoreStore(store_path)
    store.record("Alice", 10)
    store.record("Bob", 20)
    store.record("Alice", 5)

    assert store.personal_best("Alice") == 10
    assert store.personal_best("Bob") == 20


def test_personal_best_zero_when_no_scores(store_path):
    store = ScoreStore(store_path)
    assert store.personal_best("Nobody") == 0


def test_all_time_best_across_profiles(store_path):
    store = ScoreStore(store_path)
    store.record("Alice", 10)
    store.record("Bob", 30)
    store.record("Charlie", 20)

    assert store.all_time_best() == 30


def test_all_time_best_zero_when_no_scores(store_path):
    store = ScoreStore(store_path)
    assert store.all_time_best() == 0


def test_top_scores_sorted_descending(store_path):
    store = ScoreStore(store_path)
    for profile, score in [("A", 5), ("B", 20), ("C", 12), ("D", 8)]:
        store.record(profile, score)

    top = store.top_scores()
    assert [s["score"] for s in top] == [20, 12, 8, 5]


def test_top_scores_filtered_by_profile(store_path):
    store = ScoreStore(store_path)
    store.record("Alice", 100)
    store.record("Bob", 200)
    store.record("Alice", 50)

    alice_top = store.top_scores(profile="Alice")
    assert [s["score"] for s in alice_top] == [100, 50]


def test_top_scores_limit_respected(store_path):
    store = ScoreStore(store_path)
    for i in range(20):
        store.record("Alice", i)

    top = store.top_scores(n=5)
    assert len(top) == 5
    assert top[0]["score"] == 19


def test_known_profiles_includes_current_and_history(store_path):
    store = ScoreStore(store_path)
    store.current_profile = "Bob"
    store.record("Alice", 1)
    store.record("Charlie", 2)

    assert store.known_profiles() == ["Alice", "Bob", "Charlie"]


def test_save_creates_parent_directories(tmp_path):
    nested = tmp_path / "nested" / "dir" / "scores.json"
    store = ScoreStore(nested)
    store.record("Alice", 1)
    store.save()

    assert nested.exists()


def test_load_recovers_legacy_file_missing_keys(store_path):
    store_path.write_text(json.dumps({"scores": [{"profile": "Alice", "score": 1, "timestamp": "x"}]}))
    store = ScoreStore.load(store_path)
    assert store.current_profile == DEFAULT_PROFILE
    assert store.personal_best("Alice") == 1
