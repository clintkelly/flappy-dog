# Skywing Ruins

A tiny Flappy-Bird-style game written in Python with the [Arcade](https://api.arcade.academy/) library. A learning project — the goal is simple, beginner-readable code in a single file.

![Title screen](assets/title.png)

## Install

This project uses [`uv`](https://docs.astral.sh/uv/) for dependency management. From the project root:

```bash
uv sync
```

## Run

```bash
uv run python main.py
```

## Controls

| Key | Action |
| --- | --- |
| `Space` | Flap |
| `Left` / `A` | Drift left |
| `Right` / `D` | Drift right |
| `R` | Return to title (on game-over) |
| `Q` | Quit (from title or game-over) |

Pass through the gaps between columns to score. Touching a column or flying off the top/bottom of the screen ends the game.
