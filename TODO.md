# Skywing Ruins — TODO

Loose list of features and improvements we've talked about. Things at the
top are roughly "next up"; things further down are nice-to-haves. Nothing
is committed to any timeline.

## Gameplay

### Power-ups (player States are ready)
- [ ] **Shield power-up** — pickup spawns occasionally; on touch transition
      to `ShieldedState`. State already absorbs one hit and drops back to
      `NormalState`. Needs: a shield-pickup sprite, a small spawn-table
      entry, and a visible bubble/aura around the bird while shielded.
- [ ] **Star / invincibility power-up** — pickup transitions to
      `InvincibleState` for ~5 s. Collisions are ignored *and*
      `absorbs_obstacles()` is True, so we should detonate obstacles
      touched during invincibility (particle burst, score bonus, sound).
      Visible aura/flash effect on the bird. Music ducks?
- [ ] **Dash button** — pressing a dedicated key/button triggers
      `DashingState` for a short burst of forward velocity, then back to
      Normal. **Open design question:** dash might trivialize the
      flap-timing puzzle. Worth prototyping with a generous cooldown
      (say once per 5 seconds) and seeing how it feels. Could also be
      invincibility-during-dash like Hollow Knight.

### New obstacles
- [ ] **Flame jet / flame thrower** — wall-mounted torch (or similar) that
      cycles ON / OFF on a timer. Flames are lethal during ON, dormant
      during OFF — player times their passage. Assets already in
      `assets/flame*.png` (21 frames). State machine is straightforward;
      use the existing `Motion` strategy + a separate `EmitterTiming`
      attribute, or just a timer per emitter. Could spawn in pairs
      (top + bottom of screen) for a "shoot through the gap" puzzle.
- [ ] **Other motion patterns** — figure-8, pendulum, vertical bouncing
      ball. With the `Motion` strategy in place each new pattern is one
      subclass and a make_X helper.

### Shooting / projectile mechanics
- [ ] **Bird-fired projectile** — press a button to shoot something
      forward. Could break boulders/spiky-balls or just score bonus
      points. Need to decide what's destructible — making everything
      breakable removes the navigation challenge.
- [ ] **Enemy projectile** — a sprite or column that periodically launches
      something at the player.

### Levels & progression
- [ ] **Multiple levels** — different visual palettes, obstacle mixes, or
      tunings. Could be score-gated (every 50 points = next level) or
      profile-selectable (start fresh in a chosen level). Each level
      could re-skin sky, columns, mountain art, and rotate which
      obstacles appear.
- [ ] **Boss obstacles** — once every N points, a large unique obstacle
      that takes multiple hits / requires a specific path.

### Combo / scoring extensions
- [ ] Combo bonus that spans rings *and* coins, not just rings.
- [ ] "Perfect run" bonus for clearing a stretch with no near-misses.

## Atmosphere / polish

- [ ] **Rainbow after rain** — when a storm ends (`StopRain` event),
      briefly draw a rainbow arc across the sky for ~10 s, fading in
      and out. Pure code (`arcade.draw_arc_outline` or similar) or a
      single asset.
- [ ] **Day / night cycle** — sky tint shifts from blue → orange (sunset)
      → indigo (night with stars) → back. Mountains darken at night.
      No gameplay impact; pure atmosphere.
- [ ] **Background music** — looped track under the rain. Volume duck
      during thunder. Different tracks per level if we add levels.
- [ ] **Bird customization** — pick from a few bird skins on the profile
      picker. Asset work: 2-3 alternate bird sprite sets.
- [ ] **Particle "feathers"** when the bird flaps hard.
- [ ] **Cinematic death** — slow-mo for the last 200 ms before game over
      (the world freezes, the bird falls dramatically, then the panel
      appears).

## Meta

- [ ] **Achievements** — built on `ScoreStore`. Examples: first 50, first
      wolf rescue, 10-ring combo, no-miss minute, survive a full storm.
      Show a small toast when unlocked.
- [ ] **Settings UI** — master volume, SFX volume, music volume, mute
      toggle. Persist in scores.json.
- [ ] **Per-profile stats page** — total runs, average score, total
      wolves rescued, longest combo, etc. Built on the existing scores
      list.
- [ ] **Daily challenge** — a deterministic-seed run from a single
      starting state; compare your score to your previous tries.

## Architecture / tech debt

- [ ] **Event bus** for scoring side-effects. Today each scoring site
      open-codes sound + particles + floating text + milestone check.
      An `events.emit("score", {bonus, x, y, combo})` channel with
      subscribers would consolidate this and let achievements / music
      hooks attach without touching the scoring sites.
- [ ] **Sound mixer** — central master/SFX/music volumes; mute toggle.
      Currently `arcade.play_sound(...)` is scattered across ~10 sites
      with hard-coded volumes.
- [ ] **Texture-loading helper** at the top of `assets.py` (already
      consolidated there). Could shrink a few lines but low priority.
- [ ] **Architecture docstring** at the top of `main.py` (or a short
      `ARCHITECTURE.md`) describing each module and where each piece
      of logic lives.
- [ ] **Type hints throughout `GameView`** — the extracted modules have
      them, main.py mostly doesn't. Would help IDE auto-complete on
      `self.weather.`, `self.player_state.`, etc.
- [ ] **Resizable-window support** — UI positions are hard-coded for
      1280×720. Low priority unless we ever ship.

## Done (reference)

These are already implemented — keeping a record so the file shows
trajectory, not just what's missing.

- Pipes/columns with sprite tiles, gap variants, oscillating gaps
- Boulders (sine bob), spiky balls (circular orbit), rings (combo + pitch
  ramp + particle burst + floating text), coins (clusters), wolves
  (rescue in a bubble for +50 + howl), bonus rings under boulders
- Weather: rain visuals, optional rain audio, thunderstorm cycle with
  lightning flash + delayed thunder + wind gust corridors
- Player profiles + score history + leaderboard (`ScoreStore`)
- Gamepad support (per-view button handlers + analog stick deadzone)
- Title / profile picker / high-score / game-over screens with cards
- Difficulty curve interpolating from easier-than-base at score 0 to a
  tight peak at score 30
- State pattern for the player (Normal / Shielded / Invincible / Dashing)
- Strategy pattern for motion (Linear / Sine / Circular)
- Pure-Python extracted modules: `score_store`, `motion`,
  `player_state`, `difficulty`, `scoring`, `spawn_table`, `geometry`,
  `weather_state`, `animation`, `assets`
- ~120 unit tests covering the testable logic
