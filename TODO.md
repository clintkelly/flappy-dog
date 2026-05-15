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
- [ ] **Horizontally traveling dragons** — large enemy sprite that
      enters from the right and crosses the screen at a steady (or
      slightly weaving) altitude faster than the world scroll. Lethal
      on contact. Visual: animated wing-flap frames. Open design
      questions: dragon altitude bias (clamp to bird's current y for
      threat, or random for variety), should it telegraph its entry
      with a "roar" sound a beat before appearing, can it be defeated
      with the future bird-fired projectile?
- [ ] **Ceiling lightning bolts** — reverse flame thrower hanging from
      the top. Same predictable cycle (dormant → warning glow → strike
      extending downward → hold → recede) but the "flame" segments are
      jagged white/blue bolts. Reuse the `FlameThrowerCycle` state
      machine wholesale; just flip the segment positioning to extend
      downward from a ceiling-mounted emitter. Pairs naturally with the
      existing floor flame thrower for vertical hazard variety.
- [ ] **Ceiling flame thrower / paired throwers** — mirror of the floor
      flame thrower hanging from the top, alternating phase with a
      floor instance to make a "shoot through the gap" puzzle.
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
- [ ] Unified pickup combo that spans rings *and* coins on one shared
      streak counter (coin streak and ring combo are independent today).
- [ ] "Perfect run" bonus for clearing a stretch with no near-misses.
- [ ] **Late-game difficulty escalation past score 400** — once the
      gap/spacing curve plateaus, layer in `PIPE_SPEED` increase,
      shorter flame-thrower dormant windows, or a higher flame-thrower
      spawn weight so the game keeps getting harder for top players.

## Atmosphere / polish

- [ ] **Day / night cycle** — sky tint shifts from blue → orange (sunset)
      → indigo (night with stars) → back. Mountains darken at night.
      No gameplay impact; pure atmosphere.
- [ ] **Background music** — looped track under the rain. Volume duck
      during thunder. Different tracks per level if we add levels.
- [ ] **Bird customization** — pick from a few bird skins on the profile
      picker. Asset work: 2-3 alternate bird sprite sets.
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
- Floor-mounted flame thrower with dormant -> warning wisp -> extending
  -> holding -> receding cycle; segments stack with overlap; randomized
  per-instance phase; ignition sound
- Weather: rain visuals, optional rain audio, thunderstorm cycle with
  lightning flash + delayed thunder + wind gust corridors, slate-blue
  dim overlay that ramps in/out with storm state, post-storm rainbow
  that paints in left-to-right and fades out
- Atmospheric cloud parallax: each cloud's depth drives scale, drift
  speed, tint, and z-order
- Particle trails on spiky balls (red/orange comet) and freed wolves
  (gold sparkle plume); pale flap-puff particles from the bird's tail
- Coin clusters and wolves placed onto the bird's expected flight path
  (gap center / previous obstacle's exit y), not at random altitudes
- Player profiles + score history + leaderboard (`ScoreStore`)
- HUD: profile name + score in 34pt bold gold, top-left of screen
- Gamepad support (per-view button handlers + analog stick deadzone)
- Title / profile picker / high-score / game-over screens with cards
- Difficulty curve interpolating from easier-than-base at score 0 to a
  tight peak at score 400 (gap and obstacle-spacing factors lerp together)
- State pattern for the player (Normal / Shielded / Invincible / Dashing)
- Strategy pattern for motion (Linear / Sine / Circular)
- Event bus for scoring side-effects (sound, particles, floating text,
  milestone celebration, game over) — scoring sites emit typed events,
  subscribers attach independently
- Escalating coin-streak bonus: every 10 coins in a row pays a doubling
  bonus capped at +80, with a gold banner stamp and pitched fanfare;
  one missed coin breaks the streak
- Pure-Python extracted modules: `score_store`, `motion`,
  `player_state`, `difficulty`, `scoring`, `spawn_table`, `geometry`,
  `weather_state`, `animation`, `assets`, `events`, `flame_thrower`
- ~165 unit tests covering the testable logic
