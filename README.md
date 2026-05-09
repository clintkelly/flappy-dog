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
| `Space` | Flap (also: start game from title, play again on game-over) |
| `Left` / `A` | Drift left |
| `Right` / `D` | Drift right |
| `P` | Pause / unpause |
| `R` | Return to title (game-over only) |
| `Q` | Quit |

## How to play

Tap `Space` to flap upward against gravity. Drift through the gaps between stone columns — touching a column or flying off the top or bottom of the screen ends the game. You score one point each time you fully clear a column.

The game ramps in difficulty as your score climbs: column gaps shrink and columns spawn closer together, peaking around 30 points.

Press `P` any time during play to freeze the screen (handy for screenshots) and `Space` or `P` to resume.
