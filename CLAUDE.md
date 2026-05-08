# Project: Flappy-style Arcade game

This is a tiny first Python Arcade game. The goal is learning and momentum, not architecture.

## Constraints

- Keep the code simple and beginner-readable.
- Prefer one file for now unless I explicitly ask to split it.
- Use Python Arcade 3.x APIs.
- Do not introduce a physics engine for Flappy-style movement.
- Use manual gravity and velocity.
- Do not add major new systems unless asked.
- Make small, reviewable changes.
- Explain changes briefly after editing.

## Current design

- Player is a bee/dog/plane sprite.
- Space makes the player flap upward.
- Gravity pulls the player down.
- Pipes/obstacles scroll from right to left.
- Invisible score zones are used to count when the player passes pipe pairs.
- Game should remain very simple.