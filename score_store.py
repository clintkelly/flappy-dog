"""
JSON-backed score history for Skywing Ruins.

Pure-Python, no arcade dependency — so it can be unit-tested in isolation
without an OpenGL context.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

DEFAULT_PROFILE = "Player"


class ScoreStore:
    """ Persistent record of game scores keyed by profile name. """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.data: dict = {"current_profile": DEFAULT_PROFILE, "scores": []}

    @classmethod
    def load(cls, path) -> "ScoreStore":
        """ Read from disk if the file exists, otherwise return a default store. """
        store = cls(Path(path))
        if store.path.exists():
            with store.path.open() as f:
                store.data = json.load(f)
            store.data.setdefault("current_profile", DEFAULT_PROFILE)
            store.data.setdefault("scores", [])
        return store

    def save(self) -> None:
        """ Atomically write the store to disk via a temp-file rename. """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w") as f:
            json.dump(self.data, f, indent=2)
        tmp.replace(self.path)

    @property
    def current_profile(self) -> str:
        return self.data["current_profile"]

    @current_profile.setter
    def current_profile(self, name: str) -> None:
        self.data["current_profile"] = name

    def record(self, profile: str, score) -> None:
        """ Append a new score entry. Caller decides when to save(). """
        self.data["scores"].append({
            "profile": profile,
            "score": int(score),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        })

    def personal_best(self, profile: str) -> int:
        scores = [s["score"] for s in self.data["scores"] if s["profile"] == profile]
        return max(scores, default=0)

    def all_time_best(self) -> int:
        scores = [s["score"] for s in self.data["scores"]]
        return max(scores, default=0)

    def top_scores(self, n: int = 10, profile: str | None = None) -> list[dict]:
        scores = self.data["scores"]
        if profile is not None:
            scores = [s for s in scores if s["profile"] == profile]
        return sorted(scores, key=lambda s: s["score"], reverse=True)[:n]

    def known_profiles(self) -> list[str]:
        profiles = {s["profile"] for s in self.data["scores"]}
        profiles.add(self.current_profile)
        return sorted(profiles)
