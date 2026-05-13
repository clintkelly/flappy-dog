"""
Centralized texture + sound loading.

Constructed once at app startup; every view reads from the same instance.
Replaces ~30 ``arcade.load_texture(...)`` + ``arcade.load_sound(...)``
calls that used to be scattered through ``GameView.__init__`` and
``TitleView.__init__``.

Not unit-tested in isolation (depends on arcade and the asset files), but
its narrow surface — public attribute access only — makes it easy to mock
in tests that need to construct game views.
"""

from __future__ import annotations

from pathlib import Path

import arcade


def _natural_index(prefix: str, path: Path) -> int:
    return int(path.stem.replace(prefix, ""))


class AssetLibrary:
    """ Holds every texture and sound used by the game. Each attribute is
    typed implicitly by what arcade returns: ``Texture``, ``list[Texture]``,
    or ``Sound``. Optional sounds are ``Sound | None``. """

    def __init__(self, asset_dir: Path):
        self.dir = asset_dir
        detailed = arcade.hitbox.algo_detailed

        # Player frames
        self.bird_textures = self._load_glob("bird_*.png")

        # Column tiles — detailed hitbox so collision matches visible art
        self.column_ceiling_cap_textures = self._load_glob(
            "column_ceiling_cap_*.png", detailed=True,
        )
        self.column_floor_cap_textures = self._load_glob(
            "column_floor_cap_*.png", detailed=True,
        )
        self.column_mid_textures = self._load_glob(
            "column_mid_*.png", detailed=True,
        )

        # Boulders + spiky ball
        self.boulder_textures = self._load_glob("boulder*.png", detailed=True)
        self.spiky_ball_texture = arcade.load_texture(
            self.dir / "spiky_ball.png", hit_box_algorithm=detailed,
        )

        # Rings (numeric sort so the 16-frame spin animates smoothly)
        self.ring_textures = self._load_glob("ring*.png", numeric_sort=True)

        # Coins — 5 face→side frames, then auto-mirrored back-half so the
        # spin loops smoothly without an extra asset.
        coin_forward = self._load_glob("coin*.png", numeric_sort=True)
        self.coin_textures = coin_forward + [
            t.flip_left_right() for t in reversed(coin_forward[:-1])
        ]

        # Atmospheric
        self.cloud_textures = self._load_glob("cloud*.png")
        self.mountain_texture = arcade.load_texture(self.dir / "mountain.png")
        self.sky_texture = arcade.load_texture(self.dir / "sky.png")
        self.title_texture = arcade.load_texture(self.dir / "title.png")

        # Wolf
        self.wolf_standing_texture = arcade.load_texture(self.dir / "wolf_standing.png")
        self.wolf_howling_texture = arcade.load_texture(self.dir / "wolf_howling.png")

        # Sounds (always present — bundled with arcade or with the game)
        self.jump_sound = arcade.load_sound(":resources:sounds/jump1.wav")
        self.gameover_sound = arcade.load_sound(":resources:sounds/gameover1.wav")
        self.coin_sound = arcade.load_sound(":resources:sounds/coin1.wav")
        self.ring_sound = arcade.load_sound(":resources:sounds/upgrade1.wav")
        self.milestone_sound = arcade.load_sound(":resources:sounds/secret2.wav")
        self.howl_sound = arcade.load_sound(self.dir / "howl.wav")

        # Optional sounds (loaded only if the file is present — the game
        # falls back to silence rather than crashing).
        self.rain_sound = self._load_optional_sound("rain")
        self.thunder_sound = self._load_optional_sound("thunder")

    # ----- helpers -----

    def _load_glob(
        self,
        pattern: str,
        *,
        detailed: bool = False,
        numeric_sort: bool = False,
    ) -> list:
        if numeric_sort:
            prefix = pattern.split("*")[0]
            paths = sorted(self.dir.glob(pattern), key=lambda p: _natural_index(prefix, p))
        else:
            paths = sorted(self.dir.glob(pattern))
        if detailed:
            return [
                arcade.load_texture(p, hit_box_algorithm=arcade.hitbox.algo_detailed)
                for p in paths
            ]
        return [arcade.load_texture(p) for p in paths]

    def _load_optional_sound(self, stem: str):
        for ext in ("wav", "ogg", "mp3"):
            hits = list(self.dir.glob(f"{stem}.{ext}"))
            if hits:
                return arcade.load_sound(hits[0])
        return None
