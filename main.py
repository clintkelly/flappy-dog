"""
Skywing Ruins — a tiny Flappy-Bird-style game.

"""


from pathlib import Path
import math

import arcade
import pyglet
import random

import difficulty
import geometry
import scoring
from animation import AnimationCycler
from assets import AssetLibrary
from events import (
    CoinCollected,
    CoinStreakBonus,
    EventBus,
    GameOver,
    MilestoneCrossed,
    RingCollected,
    ScoreZoneCleared,
    WolfRescued,
)
from motion import CircularMotion, LinearMotion, SineMotion
from player_state import NormalState, PlayerState
from score_store import DEFAULT_PROFILE, ScoreStore
from spawn_table import SpawnTable
from weather_state import (
    FlashLightning,
    PlayThunder,
    SpawnGust,
    StartRain,
    StopRain,
    StormStart,
    WeatherStateMachine,
)

# Constants
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Skywing Ruins"

PLAYER_MIN_X = 64
PLAYER_MAX_X = WINDOW_WIDTH - 128
PLAYER_X_SPEED = 5
PLAYER_X_FRICTION = 0.5

GRAVITY = 0.6
FLAP_VELOCITY = 10
# How far below the bottom edge the bird's center can dip before it counts as a
# crash. Gives the player a chance to flap back up after a near-miss with the floor.
BOTTOM_GRACE_PIXELS = 35

# Game-over card layout and the cooldown before replay input is accepted.
GAME_OVER_INPUT_DELAY = 2.0
GAME_OVER_CARD_LEFT = 240
GAME_OVER_CARD_BOTTOM = 130
GAME_OVER_CARD_WIDTH = WINDOW_WIDTH - 480       # 800
GAME_OVER_CARD_HEIGHT = WINDOW_HEIGHT - 260     # 460
GAME_OVER_CARD_FILL = (0, 0, 0, 225)
GAME_OVER_CARD_BORDER = arcade.color.GOLD

# Score zone is a thin trip-wire placed just past the right edge of the column.
# The bird only scores once it has fully cleared the column, and the zone is
# removed on first hit so the same gap can't be re-scored by reversing.
SCORE_ZONE_WIDTH = 8
SCORE_ZONE_X_OFFSET = 144  # column half-width + roughly bird half-width

PIPE_SPEED = 3

MIN_PIPE_CENTER_GAP = 220
MAX_PIPE_CENTER_GAP = 340

MIN_PIPE_CENTER_GAP_Y = 180
MAX_PIPE_CENTER_GAP_Y = WINDOW_HEIGHT - 180

MIN_PIPE_SPACING = 240
MAX_PIPE_SPACING = 360

# Difficulty progression. Both the vertical gap and the horizontal spacing
# scale by an interpolated factor: easier than base at score 0, then shrink
# past base to a tougher peak as the score climbs to DIFFICULTY_RAMP_SCORE.
# Higher *_AT_START = easier opening (e.g. 1.55 means gaps are 55% bigger than base).
# Lower *_AT_MAX_DIFFICULTY = harder peak (e.g. 0.65 = tightens to 65% of base).
DIFFICULTY_RAMP_SCORE = 60
GAP_RATIO_AT_START = 1.55
GAP_RATIO_AT_MAX_DIFFICULTY = 0.65
SPACING_RATIO_AT_START = 1.40
SPACING_RATIO_AT_MAX_DIFFICULTY = 0.75

PLAYER_ANIMATION_FRAME_DURATION = 0.05  # seconds per frame
ASSET_DIR = Path(__file__).parent / "assets"
SCORES_PATH = Path(__file__).parent / "scores.json"

MAX_PROFILE_NAME_LENGTH = 12

# Gamepad: deadzone applied to the left-stick X axis when emulating LEFT/RIGHT
# key presses. Below this threshold the stick is considered centered.
GAMEPAD_STICK_DEADZONE = 0.4

COLUMN_TILE_SIZE = 64  # native pixels per side
COLUMN_TILE_SCALE = 3
COLUMN_TILE_RENDERED = COLUMN_TILE_SIZE * COLUMN_TILE_SCALE
COLUMN_TILE_VERTICAL_OVERLAP = 6  # rendered pixels of overlap at tile seams

# Cloud parallax layer.
# Scale, drift speed, and tint are all interpolated from depth=0 (near) to depth=1 (far).
# Far clouds drift slowly, are smaller, and tinted toward the sky; depth also drives
# z-order so distant clouds draw behind near ones.
NUM_CLOUDS = 8
CLOUD_NEAR_SCALE = 3.0
CLOUD_FAR_SCALE = 1.5
CLOUD_NEAR_SPEED = 1.6             # near clouds drift faster (still slower than pipes at 3)
CLOUD_FAR_SPEED = 0.3               # far clouds barely move
CLOUD_NEAR_TINT = (255, 255, 255)  # pure white
CLOUD_FAR_TINT = (180, 200, 220)   # shifted toward sky-blue
CLOUD_Y_MIN = 200
CLOUD_Y_MAX = WINDOW_HEIGHT - 60

# Distant mountain layer — slowest scrolling, sits along the haze line at the bottom of the sky.
NUM_MOUNTAINS = 2
MOUNTAIN_SCALE = 1.5
MOUNTAIN_SPEED = 0.2
# Tuned so the asset's mist sits inside the sky haze (~y < 120) while peaks rise above it.
MOUNTAIN_Y_MIN = 100
MOUNTAIN_Y_MAX = 130

# Oscillating boulder obstacles — sometimes spawned in place of a column pair.
BOULDER_OBSTACLE_CHANCE = 0.2   # fraction of obstacle spawns that are boulders
BOULDER_SCALE = 3
BOULDER_BASE_Y_MIN = 240
BOULDER_BASE_Y_MAX = WINDOW_HEIGHT - 240
BOULDER_AMPLITUDE_MIN = 80
BOULDER_AMPLITUDE_MAX = 160
BOULDER_PHASE_SPEED_MIN = 1.5   # radians/sec
BOULDER_PHASE_SPEED_MAX = 2.5
# When paired with a bottom bonus ring, keep the boulder's lowest swing above
# this y so the bird never gets trapped between the rock and the floor.
BOULDER_LOWEST_Y_WITH_BONUS_RING = 320

# Oscillating column pairs — gap slides up/down while the column scrolls.
# Roll fires only when the boulder roll missed. ~0.25 -> 20% of all spawns.
OSCILLATING_PIPE_CHANCE = 0.25
PIPE_AMPLITUDE_MIN = 60
PIPE_AMPLITUDE_MAX = 120
PIPE_PHASE_SPEED_MIN = 0.8      # radians/sec — slower than boulders since the gap is the target
PIPE_PHASE_SPEED_MAX = 1.6

# Collectible bonus rings — non-fatal pickups that grant points.
RING_OBSTACLE_CHANCE = 0.20
RING_SCALE = 3
RING_BASE_Y_MIN = 240
RING_BASE_Y_MAX = WINDOW_HEIGHT - 240
RING_AMPLITUDE_MIN = 60
RING_AMPLITUDE_MAX = 140
RING_PHASE_SPEED_MIN = 1.0
RING_PHASE_SPEED_MAX = 2.0
RING_POINTS = 2
RING_ANIMATION_FRAME_DURATION = 0.05  # seconds per frame for the ring spin
RING_COMBO_BONUS_STEP = 1     # extra points added per consecutive ring beyond the first
RING_PITCH_STEP = 0.06        # play_sound speed delta per consecutive ring
RING_PITCH_MAX = 1.9          # cap so the chime doesn't go cartoonish
# Static "risk" rings placed near the floor under a boulder spawn.
BONUS_RING_Y_MIN = 80
BONUS_RING_Y_MAX = 130

# Ring-collection particle burst (code-only — uses SpriteCircle).
PARTICLES_PER_BURST = 12
PARTICLE_LIFETIME = 0.5            # seconds
PARTICLE_SPEED_MIN = 2.0           # pixels per frame
PARTICLE_SPEED_MAX = 6.0
PARTICLE_GRAVITY = 0.2
PARTICLE_RADIUS_MIN = 3
PARTICLE_RADIUS_MAX = 6
PARTICLE_COLORS = (
    arcade.color.GOLD,
    arcade.color.ORANGE,
    arcade.color.YELLOW,
    arcade.color.WHITE,
)

# Floating "+N" text shown when something is scored.
FLOATING_TEXT_LIFETIME = 1.0       # seconds
FLOATING_TEXT_RISE_SPEED = 1.5     # pixels per frame
FLOATING_TEXT_START_SIZE = 32
FLOATING_TEXT_END_SIZE = 60        # font_size grows over lifetime for a "pop" effect
FLOATING_TEXT_COLORS = (
    arcade.color.GOLD,
    arcade.color.ORANGE,
    arcade.color.MAGENTA,
    arcade.color.CYAN,
    arcade.color.YELLOW_GREEN,
    arcade.color.HOT_PINK,
    arcade.color.LIGHT_SKY_BLUE,
)

# Milestone celebration — fires whenever the score crosses a multiple of THRESHOLD.
MILESTONE_THRESHOLD = 10
MILESTONE_TEXT_LIFETIME = 1.5
MILESTONE_TEXT_START_SIZE = 80
MILESTONE_TEXT_END_SIZE = 140
MILESTONE_COLOR = arcade.color.GOLD
MILESTONE_VOLUME = 0.7

# Rescuable wolf — rare, floats in a shimmering bubble. Touch = free + big bonus.
WOLF_SPAWN_CHANCE = 0.05            # 5% of obstacle slots — rare and special
WOLF_SCALE = 3                      # 64 native -> 192 rendered
WOLF_POINTS = 50
WOLF_HOWL_VOLUME = 0.85
# Spawn either in the upper band or the lower band — off the safe central path
# so reaching the bubble is a deliberate altitude commitment.
WOLF_Y_LOW_MIN = 150
WOLF_Y_LOW_MAX = 250
WOLF_Y_HIGH_MIN = WINDOW_HEIGHT - 250
WOLF_Y_HIGH_MAX = WINDOW_HEIGHT - 150
# Bubble pulses around this radius; collision and visuals scale with it.
WOLF_BUBBLE_RADIUS = 110
WOLF_BUBBLE_PULSE_AMPLITUDE = 6
WOLF_BUBBLE_PULSE_SPEED = 2.5       # radians/sec
WOLF_BUBBLE_OUTLINE_COLOR = (255, 255, 255, 220)
WOLF_BUBBLE_FILL_INNER = (230, 245, 255, 85)
WOLF_BUBBLE_FILL_MIDDLE = (200, 230, 255, 55)
WOLF_BUBBLE_FILL_OUTER = (180, 220, 255, 35)
# Freed-wolf animation
WOLF_FREED_INITIAL_VELOCITY = 200   # px/sec upward at the moment of rescue
WOLF_FREED_RISE_ACCEL = 350         # px/sec/sec — accelerates upward
WOLF_FREED_LIFETIME = 1.6           # seconds before the wolf vanishes
# Celebration particle burst — much bigger than rings/coins
WOLF_PARTICLES_PER_BURST = 80
WOLF_PARTICLE_COLORS = (
    arcade.color.GOLD,
    arcade.color.ORANGE,
    arcade.color.MAGENTA,
    arcade.color.CYAN,
    arcade.color.WHITE,
    arcade.color.YELLOW,
    arcade.color.LIGHT_BLUE,
    arcade.color.HOT_PINK,
)
WOLF_CELEBRATION_COLOR = arcade.color.CYAN
# After a wolf, the very next column's gap_center is clamped to within this
# delta of the wolf's altitude so the player can actually reach it.
WOLF_REACHABLE_DELTA_Y = 200

# Spiky-ball obstacle. Uses the new Motion strategy (CircularMotion) — the
# ball orbits a base point at a fixed radius while the base scrolls leftward.
SPIKY_BALL_SPAWN_CHANCE = 0.06
SPIKY_BALL_SCALE = 3                  # 64 native -> 192 rendered
SPIKY_BALL_RADIUS_MIN = 90
SPIKY_BALL_RADIUS_MAX = 150
SPIKY_BALL_ANGULAR_SPEED_MIN = 1.8    # radians/sec
SPIKY_BALL_ANGULAR_SPEED_MAX = 2.8
SPIKY_BALL_BASE_Y_MIN = 250           # orbit-center y range (middle band)
SPIKY_BALL_BASE_Y_MAX = WINDOW_HEIGHT - 250
SPIKY_BALL_SPIN_DEGREES_PER_FRAME = 5  # purely visual sprite rotation

# Spawn distribution. Column-pair takes whatever weight is left after the
# others — keeps the table summing to 1.0 even when individual chances change.
_COLUMN_PAIR_SPAWN_WEIGHT = (
    1.0
    - WOLF_SPAWN_CHANCE
    - SPIKY_BALL_SPAWN_CHANCE
    - RING_OBSTACLE_CHANCE
    - BOULDER_OBSTACLE_CHANCE
)
OBSTACLE_SPAWN_TABLE = SpawnTable([
    ("wolf", WOLF_SPAWN_CHANCE),
    ("spiky", SPIKY_BALL_SPAWN_CHANCE),
    ("ring", RING_OBSTACLE_CHANCE),
    ("boulder", BOULDER_OBSTACLE_CHANCE),
    ("column", _COLUMN_PAIR_SPAWN_WEIGHT),
])

# Weather. RainSystem is a self-contained falling-rain effect; WeatherController
# composes it with a thunderstorm state machine (clear → storm-onset → storm → clear)
# and a flash overlay for lightning.
RAIN_DROP_COUNT = 220
RAIN_FALL_SPEED = 12               # pixels per frame downward
RAIN_WIND_SPEED = 18               # pixels per frame leftward — strong slant so it looks like
                                    # the bird is flying *into* the rain
RAIN_LENGTH_X = 20
RAIN_LENGTH_Y = 13
RAIN_COLOR = (240, 250, 255, 230)  # RGBA — near-white, mostly opaque against the sky
RAIN_THICKNESS = 2
RAIN_SOUND_VOLUME = 0.5

# Weather *visual* + *audio* tuning. The storm-cycle TIMING constants
# (STORM_INTERVAL_*, STORM_DURATION_*, LIGHTNING_INTERVAL_*, etc.) live in
# weather_state.py because they're behavioral and unit-tested there.
LIGHTNING_FLASH_ALPHA = 230
LIGHTNING_FLASH_DURATION = 0.25     # seconds for full-screen flash to fade to 0
THUNDER_VOLUME = 0.8

# Wind gust corridors — visible vertical columns of falling air that spawn
# during storms. The rectangle scrolls left with the world; the lines inside
# drift DOWNWARD to telegraph the downdraft force.
GUST_SCROLL_SPEED = 3               # px/frame — matches PIPE_SPEED so it travels with the world
GUST_WIDTH_MIN = 180                # narrower than tall — reads as a column
GUST_WIDTH_MAX = 300
GUST_HEIGHT_MIN = 320
GUST_HEIGHT_MAX = 500
GUST_Y_MARGIN = 60                  # don't spawn flush against the top or bottom
GUST_DOWNDRAFT = 0.35               # added to change_y per frame inside a gust (gravity is 0.6)
GUST_LINE_COUNT = 8                 # horizontal stripes visible inside the column
GUST_LINE_COLOR = (255, 255, 255, 235)
GUST_LINE_THICKNESS = 3
GUST_BACKDROP_COLOR = (210, 230, 255, 80)  # faint blue tint so the corridor is obvious
GUST_WAVE_AMPLITUDE = 7
GUST_WAVE_FREQUENCY = 0.03
GUST_WAVE_SPEED = 5.0               # wave-wobble rate (radians/sec)
GUST_FLOW_SPEED = 360               # px/sec — speed the stripes drift downward (faster = more
                                    # visibly "this is wind blowing DOWN")

# Collectible coins placed in a row between obstacle spawns.
COIN_SCALE = 1.5                   # 64 native -> 96 rendered
COIN_ANIMATION_FRAME_DURATION = 0.06
COINS_PER_CLUSTER = 3
COIN_CLUSTER_SPACING_X = 110       # pixels between coin centers in a cluster
COIN_Y_MIN = 200
COIN_Y_MAX = WINDOW_HEIGHT - 200
COIN_POINTS = 1
COIN_PARTICLES_PER_BURST = 8
# Streak bonus: every COIN_STREAK_THRESHOLD coins in a row fires an escalating
# bonus. Tier N pays base * 2**(N-1), clamped to COIN_STREAK_BONUS_CAP.
# A single missed coin (one that scrolls off-screen) resets the streak to 0.
COIN_STREAK_THRESHOLD = 10
COIN_STREAK_BASE_BONUS = 10
COIN_STREAK_BONUS_CAP = 80
COIN_STREAK_COLOR = arcade.color.GOLD
COIN_STREAK_SOUND_SPEED = 1.35      # pitch the milestone fanfare up so it sounds distinct
COIN_STREAK_SOUND_VOLUME = 0.7
# Streak text — smaller ramp than the milestone stamp and positioned in the
# upper third of the screen so the two celebrations don't pile on top of each
# other when a 50-point milestone coincides with a streak crossing.
COIN_STREAK_TEXT_START_SIZE = 24
COIN_STREAK_TEXT_END_SIZE = 36
COIN_STREAK_TEXT_Y = WINDOW_HEIGHT - 110


def lerp(a, b, t):
    return a + (b - a) * t


class RainSystem:
    """ Always-on falling-rain effect, drawn on top of the game world.

    Pure code, no sprites — each frame a batch of disconnected line segments
    is drawn via arcade.draw_lines (one GL call). Designed as a stand-alone
    effect so a future WeatherController can compose it with snow, lightning,
    fog etc. without changes here.
    """

    def __init__(self, count=RAIN_DROP_COUNT, width=WINDOW_WIDTH, height=WINDOW_HEIGHT):
        self.width = width
        self.height = height
        # Lists-of-lists so we can mutate (x, y) in place each frame.
        self.drops = [
            [random.uniform(0, width), random.uniform(0, height)]
            for _ in range(count)
        ]

    def reset_above_screen(self):
        """ Move every drop above (and right of) the screen so that when a storm
        begins the rain visibly falls in rather than appearing pre-populated. """
        for drop in self.drops:
            if random.random() < 0.5:
                drop[0] = random.uniform(0, self.width + 200)
                drop[1] = random.uniform(self.height, self.height + 500)
            else:
                drop[0] = random.uniform(self.width, self.width + 400)
                drop[1] = random.uniform(0, self.height)

    def update(self, delta_time):
        for drop in self.drops:
            drop[0] -= RAIN_WIND_SPEED
            drop[1] -= RAIN_FALL_SPEED
            if drop[0] < 0 or drop[1] < 0:
                # Recycle from either the top edge OR the right edge so the
                # right side stays populated despite the strong leftward wind.
                # 50/50 split is close enough to the actual edge-inflow ratio.
                if random.random() < 0.5:
                    drop[0] = random.uniform(0, self.width)
                    drop[1] = random.uniform(self.height, self.height + 200)
                else:
                    drop[0] = random.uniform(self.width, self.width + 200)
                    drop[1] = random.uniform(0, self.height)

    def draw(self):
        # arcade.draw_lines takes a flat list of (x, y) pairs treated as
        # alternating start/end points — one batched GL call for all drops.
        points = []
        for x, y in self.drops:
            points.append((x, y))
            points.append((x - RAIN_LENGTH_X, y - RAIN_LENGTH_Y))
        arcade.draw_lines(points, RAIN_COLOR, RAIN_THICKNESS)


class WindGust:
    """ A vertical wind column that scrolls left across the screen during storms.
    Horizontal stripes inside the column drift downward to visually telegraph
    the downdraft. While the bird is inside, a sustained downward force adds
    to its change_y each frame. Visuals are procedural — no asset. """

    def __init__(self, left, bottom, width, height):
        self.left = left
        self.bottom = bottom
        self.width = width
        self.height = height
        self.phase = random.uniform(0, 2 * math.pi)
        # Stripe-flow offset accumulates downward motion of the air inside the box.
        self.flow_offset = random.uniform(0, height)

    def update(self, delta_time):
        self.left -= GUST_SCROLL_SPEED
        self.phase += GUST_WAVE_SPEED * delta_time
        # Stripes drift downward continuously, wrapping through the column.
        self.flow_offset = (self.flow_offset + GUST_FLOW_SPEED * delta_time) % self.height

    def is_off_screen(self):
        return self.left + self.width < 0

    def contains(self, x, y):
        return (self.left <= x <= self.left + self.width
                and self.bottom <= y <= self.bottom + self.height)

    def draw(self):
        # Faint backdrop tint so the corridor edges are obvious even at a glance.
        arcade.draw_lbwh_rectangle_filled(
            self.left, self.bottom, self.width, self.height, GUST_BACKDROP_COLOR,
        )
        # Horizontal stripes spaced evenly through the column height, all drifting
        # downward by `flow_offset` so the air visibly flows down.
        spacing = self.height / GUST_LINE_COUNT
        top = self.bottom + self.height
        for i in range(GUST_LINE_COUNT):
            # Each stripe wraps independently; offset cycles through [0, height).
            offset = (i * spacing + self.flow_offset) % self.height
            y_base = top - offset
            points = []
            x = 0
            while x <= self.width:
                wave = math.sin(x * GUST_WAVE_FREQUENCY + self.phase + i * 0.6) * GUST_WAVE_AMPLITUDE
                points.append((self.left + x, y_base + wave))
                x += 16
            arcade.draw_line_strip(points, GUST_LINE_COLOR, GUST_LINE_THICKNESS)


class WeatherController:
    """ Arcade-side facade over the pure-Python ``WeatherStateMachine``.

    Owns the rain system, the active wind gusts, the flash overlay state,
    and the audio players. Each frame: ticks the state machine, then acts
    on whatever events it emits (play thunder, flash, start/stop rain,
    reset rain on storm start, spawn gust). All transition logic and
    timer math lives in weather_state.py for testability.
    """

    def __init__(self, rain_sound=None, thunder_sound=None):
        self.rain = RainSystem()
        self.rain_sound = rain_sound
        self.thunder_sound = thunder_sound
        self.rain_player = None
        self.state_machine = WeatherStateMachine()
        self.gusts: list[WindGust] = []
        # Flash overlay state — only the visual decay is owned here; the
        # state machine just tells us when to fire a new flash.
        self.flash_alpha = 0.0
        self.flash_decay_per_second = LIGHTNING_FLASH_ALPHA / LIGHTNING_FLASH_DURATION

    @property
    def state(self):
        return self.state_machine.state

    def shutdown(self):
        """ Stop the rain loop. Call from on_hide_view. """
        if self.rain_player is not None:
            arcade.stop_sound(self.rain_player)
            self.rain_player = None

    def update(self, delta_time):
        # Flash always decays regardless of state.
        if self.flash_alpha > 0:
            self.flash_alpha = max(0.0, self.flash_alpha - self.flash_decay_per_second * delta_time)

        # Active gusts continue to scroll and cull regardless of weather state,
        # so a gust spawned at the end of a storm still finishes its travel.
        for gust in self.gusts[:]:
            gust.update(delta_time)
            if gust.is_off_screen():
                self.gusts.remove(gust)

        # Tick the state machine and act on emitted events.
        for event in self.state_machine.update(delta_time):
            self._handle_event(event)

        # Rain only updates visually while the storm is actually raining.
        if self.state == WeatherStateMachine.STORM:
            self.rain.update(delta_time)

    def draw(self):
        if self.state == WeatherStateMachine.STORM:
            self.rain.draw()
        for gust in self.gusts:
            gust.draw()
        if self.flash_alpha > 0:
            arcade.draw_lbwh_rectangle_filled(
                0, 0, WINDOW_WIDTH, WINDOW_HEIGHT,
                (255, 255, 255, int(self.flash_alpha)),
            )

    def force_at(self, x, y):
        """ Sum of wind forces (fx, fy) from any gusts containing the point. """
        fx, fy = 0.0, 0.0
        for gust in self.gusts:
            if gust.contains(x, y):
                fy -= GUST_DOWNDRAFT
        return fx, fy

    # ----- event handlers -----

    def _handle_event(self, event):
        if isinstance(event, FlashLightning):
            self.flash_alpha = float(LIGHTNING_FLASH_ALPHA)
        elif isinstance(event, PlayThunder):
            if self.thunder_sound is not None:
                arcade.play_sound(self.thunder_sound, volume=THUNDER_VOLUME)
        elif isinstance(event, StartRain):
            if self.rain_sound is not None and self.rain_player is None:
                self.rain_player = arcade.play_sound(
                    self.rain_sound, volume=RAIN_SOUND_VOLUME, loop=True,
                )
        elif isinstance(event, StopRain):
            if self.rain_player is not None:
                arcade.stop_sound(self.rain_player)
                self.rain_player = None
        elif isinstance(event, StormStart):
            # Push all drops above/right so the storm visibly rolls in.
            self.rain.reset_above_screen()
        elif isinstance(event, SpawnGust):
            self._spawn_gust()

    def _spawn_gust(self):
        width = random.randint(GUST_WIDTH_MIN, GUST_WIDTH_MAX)
        height = random.randint(GUST_HEIGHT_MIN, GUST_HEIGHT_MAX)
        bottom = random.randint(GUST_Y_MARGIN, WINDOW_HEIGHT - GUST_Y_MARGIN - height)
        # Spawn just off the right edge so it scrolls into view.
        self.gusts.append(WindGust(WINDOW_WIDTH, bottom, width, height))


class TitleView(arcade.View):
    """ Title screen shown at startup and after R from game-over. """

    def __init__(self):
        super().__init__()
        # title_image needs the AssetLibrary which lives on the window;
        # built lazily in on_show_view since self.window isn't set yet.
        self.title_image: arcade.Sprite | None = None

        self.title_text = arcade.Text(
            "SKYWING RUINS",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT - 32,
            color=arcade.color.DARK_BLUE,
            font_size=42,
            anchor_x="center",
            anchor_y="center",
        )
        self.high_score_text = arcade.Text(
            "",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT - 78,
            color=arcade.color.GOLD,
            font_size=22,
            anchor_x="center",
            anchor_y="center",
        )
        self.profile_text = arcade.Text(
            "",
            x=WINDOW_WIDTH // 2,
            y=98,
            color=arcade.color.WHITE,
            font_size=18,
            anchor_x="center",
            anchor_y="center",
        )
        self.prompt_text = arcade.Text(
            "Press SPACE or A to start  •  Q or B to quit",
            x=WINDOW_WIDTH // 2,
            y=64,
            color=arcade.color.YELLOW,
            font_size=22,
            anchor_x="center",
            anchor_y="center",
        )
        self.controls_text = arcade.Text(
            "SPACE/A flap   •   ←→/Dpad drift   •   P/Start pause   •   N profile   •   H/Y scores",
            x=WINDOW_WIDTH // 2,
            y=28,
            color=arcade.color.WHITE,
            font_size=16,
            anchor_x="center",
            anchor_y="center",
        )

    def on_show_view(self):
        if self.title_image is None:
            self.title_image = arcade.Sprite(
                self.window.assets.title_texture,
                scale=3,
            )
            self.title_image.center_x = WINDOW_WIDTH // 2
            self.title_image.center_y = WINDOW_HEIGHT // 2
        store = self.window.score_store
        self.high_score_text.text = f"HIGH SCORE: {store.all_time_best()}"
        self.profile_text.text = f"PROFILE: {store.current_profile}"

    def on_draw(self):
        self.clear()
        arcade.draw_sprite(self.title_image)

        # Translucent panels behind the title-screen text so it stays legible
        # against the cloud-and-mountain title art.
        panel_color = (0, 0, 0, 170)
        arcade.draw_lbwh_rectangle_filled(0, 610, WINDOW_WIDTH, 110, panel_color)
        arcade.draw_lbwh_rectangle_filled(0, 0, WINDOW_WIDTH, 120, panel_color)

        self.title_text.draw()
        self.high_score_text.draw()
        self.profile_text.draw()
        self.prompt_text.draw()
        self.controls_text.draw()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.SPACE:
            self.window.show_view(GameView())
        elif key == arcade.key.Q:
            self.window.close()
        elif key == arcade.key.N:
            self.window.show_view(ProfilePickerView())
        elif key == arcade.key.H:
            self.window.show_view(HighScoreView())

    def on_button_press(self, button):
        if button in ("a", "start"):
            self.on_key_press(arcade.key.SPACE, 0)
        elif button in ("b", "back"):
            self.on_key_press(arcade.key.Q, 0)
        elif button == "x":
            self.on_key_press(arcade.key.N, 0)
        elif button == "y":
            self.on_key_press(arcade.key.H, 0)


class ProfilePickerView(arcade.View):
    """ List of known profiles to pick from, plus an inline "add new" option. """

    CARD_LEFT = 240
    CARD_BOTTOM = 90
    CARD_WIDTH = WINDOW_WIDTH - 480
    CARD_HEIGHT = WINDOW_HEIGHT - 180
    LINE_HEIGHT = 36
    LIST_TOP_Y = WINDOW_HEIGHT - 200
    MAX_VISIBLE = 12

    def __init__(self):
        super().__init__()
        self.title_text = arcade.Text(
            "CHOOSE PROFILE",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT - 130,
            color=arcade.color.GOLD,
            font_size=36,
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )
        self.hint_text = arcade.Text(
            "[↑↓ or Dpad] navigate   •   [Enter or A] select   •   [N keyboard] new   •   [Esc or B] cancel",
            x=WINDOW_WIDTH // 2,
            y=120,
            color=(200, 200, 200),
            font_size=16,
            anchor_x="center",
            anchor_y="center",
        )

        # Entries: known profiles + an "Add new" sentinel as the final row.
        self.entries: list[str] = []
        self.selected_index = 0
        self.entry_texts: list[arcade.Text] = []

        # Sub-mode for typing a brand-new name.
        self.entering_name = False
        self.name_buffer = ""
        self.name_prompt_text = arcade.Text(
            "",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2,
            color=arcade.color.WHITE,
            font_size=24,
            anchor_x="center",
            anchor_y="center",
            multiline=True,
            width=WINDOW_WIDTH - 120,
            align="center",
        )

    # ----- view lifecycle -----

    def on_show_view(self):
        store = self.window.score_store
        # Existing profiles, then a sentinel row to add a new one.
        self.entries = store.known_profiles() + ["+ Add new profile..."]
        try:
            self.selected_index = self.entries.index(store.current_profile)
        except ValueError:
            self.selected_index = 0
        self._refresh_entry_texts()

    def on_draw(self):
        self.clear()
        arcade.draw_lbwh_rectangle_filled(
            self.CARD_LEFT, self.CARD_BOTTOM, self.CARD_WIDTH, self.CARD_HEIGHT,
            (0, 0, 0, 210),
        )
        arcade.draw_lbwh_rectangle_outline(
            self.CARD_LEFT, self.CARD_BOTTOM, self.CARD_WIDTH, self.CARD_HEIGHT,
            arcade.color.GOLD, 3,
        )
        self.title_text.draw()
        for text in self.entry_texts:
            text.draw()
        self.hint_text.draw()
        if self.entering_name:
            arcade.draw_lbwh_rectangle_filled(
                self.CARD_LEFT + 30, WINDOW_HEIGHT // 2 - 60,
                self.CARD_WIDTH - 60, 120,
                (0, 0, 0, 235),
            )
            self.name_prompt_text.draw()

    def on_key_press(self, key, modifiers):
        if self.entering_name:
            self._handle_name_input_key(key)
            return

        if key == arcade.key.ESCAPE:
            self.window.show_view(TitleView())
        elif key in (arcade.key.UP, arcade.key.W):
            if self.entries:
                self.selected_index = (self.selected_index - 1) % len(self.entries)
                self._refresh_entry_texts()
        elif key in (arcade.key.DOWN, arcade.key.S):
            if self.entries:
                self.selected_index = (self.selected_index + 1) % len(self.entries)
                self._refresh_entry_texts()
        elif key == arcade.key.ENTER or key == arcade.key.RETURN:
            self._confirm_selection()
        elif key == arcade.key.N:
            self._start_name_input()

    def on_text(self, text):
        if not self.entering_name:
            return
        for ch in text:
            if len(self.name_buffer) >= MAX_PROFILE_NAME_LENGTH:
                break
            if ch.isprintable() and (ch.isalnum() or ch == " "):
                self.name_buffer += ch
        self._refresh_name_prompt()

    # ----- helpers -----

    def _confirm_selection(self):
        if not self.entries:
            return
        # The last row is always the "+ Add new" sentinel.
        if self.selected_index == len(self.entries) - 1:
            self._start_name_input()
            return
        store = self.window.score_store
        store.current_profile = self.entries[self.selected_index]
        store.save()
        self.window.show_view(TitleView())

    def _refresh_entry_texts(self):
        self.entry_texts = []
        visible = self.entries[: self.MAX_VISIBLE]
        for i, name in enumerate(visible):
            highlighted = i == self.selected_index
            color = arcade.color.GOLD if highlighted else arcade.color.WHITE
            prefix = "▶  " if highlighted else "    "
            text = arcade.Text(
                f"{prefix}{name}",
                x=WINDOW_WIDTH // 2,
                y=self.LIST_TOP_Y - i * self.LINE_HEIGHT,
                color=color,
                font_size=22,
                anchor_x="center",
                anchor_y="center",
                bold=highlighted,
            )
            self.entry_texts.append(text)

    def _start_name_input(self):
        self.entering_name = True
        self.name_buffer = ""
        self._refresh_name_prompt()

    def _refresh_name_prompt(self):
        self.name_prompt_text.text = (
            f"Enter new profile name (Enter to confirm, Esc to cancel):\n{self.name_buffer}_"
        )

    def _handle_name_input_key(self, key):
        if key == arcade.key.ESCAPE:
            self.entering_name = False
        elif key == arcade.key.ENTER or key == arcade.key.RETURN:
            name = self.name_buffer.strip()
            if name:
                store = self.window.score_store
                store.current_profile = name
                store.save()
                self.window.show_view(TitleView())
            else:
                self.entering_name = False
        elif key == arcade.key.BACKSPACE:
            self.name_buffer = self.name_buffer[:-1]
            self._refresh_name_prompt()

    def on_button_press(self, button):
        # While typing a new name, only "cancel" is available on the gamepad —
        # creating a new profile requires the keyboard.
        if self.entering_name:
            if button in ("b", "back"):
                self._handle_name_input_key(arcade.key.ESCAPE)
            return
        if button == "dpup":
            self.on_key_press(arcade.key.UP, 0)
        elif button == "dpdown":
            self.on_key_press(arcade.key.DOWN, 0)
        elif button in ("a", "start"):
            self.on_key_press(arcade.key.ENTER, 0)
        elif button in ("b", "back"):
            self.on_key_press(arcade.key.ESCAPE, 0)


class HighScoreView(arcade.View):
    """ List of top scores across all profiles, presented as a centered card. """

    CARD_LEFT = 160
    CARD_BOTTOM = 60
    CARD_WIDTH = WINDOW_WIDTH - 320
    CARD_HEIGHT = WINDOW_HEIGHT - 120
    ENTRY_LINE_HEIGHT = 38
    ENTRIES_TOP_Y = 540

    # Tiered colors so the podium reads at a glance.
    RANK_COLORS = {
        1: arcade.color.GOLD,
        2: (210, 210, 210),  # silver
        3: (205, 127, 50),   # bronze
    }

    def __init__(self):
        super().__init__()
        self.title_text = arcade.Text(
            "HIGH SCORES",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT - 100,
            color=arcade.color.GOLD,
            font_size=48,
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )
        self.back_text = arcade.Text(
            "Press Esc, A, or B to return",
            x=WINDOW_WIDTH // 2,
            y=95,
            color=(200, 200, 200),
            font_size=18,
            anchor_x="center",
            anchor_y="center",
        )
        self.no_scores_text = arcade.Text(
            "No scores yet — go play!",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2,
            color=arcade.color.WHITE,
            font_size=24,
            anchor_x="center",
            anchor_y="center",
        )
        self.entry_texts: list[arcade.Text] = []

    def on_show_view(self):
        store = self.window.score_store
        top = store.top_scores(n=10)
        self.entry_texts = []
        for rank, entry in enumerate(top, 1):
            date = entry.get("timestamp", "")[:10]
            color = self.RANK_COLORS.get(rank, arcade.color.WHITE)
            text = arcade.Text(
                f"{rank:2d}.  {entry['profile']}  —  {entry['score']}  ({date})",
                x=WINDOW_WIDTH // 2,
                y=self.ENTRIES_TOP_Y - (rank - 1) * self.ENTRY_LINE_HEIGHT,
                color=color,
                font_size=22,
                anchor_x="center",
                anchor_y="center",
            )
            self.entry_texts.append(text)

    def on_draw(self):
        self.clear()
        # Centered translucent card with a gold border so the text sits on a
        # solid backdrop instead of the sky-blue clear color.
        arcade.draw_lbwh_rectangle_filled(
            self.CARD_LEFT, self.CARD_BOTTOM, self.CARD_WIDTH, self.CARD_HEIGHT,
            (0, 0, 0, 210),
        )
        arcade.draw_lbwh_rectangle_outline(
            self.CARD_LEFT, self.CARD_BOTTOM, self.CARD_WIDTH, self.CARD_HEIGHT,
            arcade.color.GOLD, 3,
        )
        self.title_text.draw()
        if self.entry_texts:
            for text in self.entry_texts:
                text.draw()
        else:
            self.no_scores_text.draw()
        self.back_text.draw()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            self.window.show_view(TitleView())

    def on_button_press(self, button):
        if button in ("a", "b", "back", "start"):
            self.on_key_press(arcade.key.ESCAPE, 0)


class GameView(arcade.View):
    """
    Main gameplay screen.
    """

    def __init__(self):
        super().__init__()
        # Nothing asset-related happens here — self.window isn't available
        # until arcade calls show_view. setup() runs once from on_show_view
        # and pulls everything from self.window.assets.
        self.scene = None
        self._setup_complete = False

    def on_show_view(self):
        if not self._setup_complete:
            self.setup()
            self._setup_complete = True

    def setup(self):
        """ Called once when this GameView is first shown. Loads asset
        references off the window-owned AssetLibrary and initializes the
        full game state. Each new game gets a fresh GameView, so 'reset'
        is implicit — there's no need to support a second call. """
        assets = self.window.assets

        # Texture references (just aliases — AssetLibrary owns the actual textures).
        self.player_textures = assets.bird_textures
        self.column_ceiling_cap_textures = assets.column_ceiling_cap_textures
        self.column_floor_cap_textures = assets.column_floor_cap_textures
        self.column_mid_textures = assets.column_mid_textures
        self.boulder_textures = assets.boulder_textures
        self.ring_textures = assets.ring_textures
        self.coin_textures = assets.coin_textures
        self.cloud_textures = assets.cloud_textures
        self.mountain_texture = assets.mountain_texture
        self.wolf_standing_texture = assets.wolf_standing_texture
        self.wolf_howling_texture = assets.wolf_howling_texture
        self.spiky_ball_texture = assets.spiky_ball_texture

        # Sounds
        self.jump_sound = assets.jump_sound
        self.gameover_sound = assets.gameover_sound
        self.coin_sound = assets.coin_sound
        self.ring_sound = assets.ring_sound
        self.milestone_sound = assets.milestone_sound
        self.howl_sound = assets.howl_sound

        # Static sky background sprite (rebuilt per GameView — cheap).
        self.sky_sprite = arcade.Sprite(assets.sky_texture, scale=4)
        self.sky_sprite.center_x = WINDOW_WIDTH // 2
        self.sky_sprite.center_y = WINDOW_HEIGHT // 2

        # Weather: rain + thunderstorm cycle (sounds optional).
        self.weather = WeatherController(
            rain_sound=assets.rain_sound,
            thunder_sound=assets.thunder_sound,
        )

        # Animation cyclers replace the duplicated frame/time/wrap state
        # that used to live on the view for bird/ring/coin separately.
        self.bird_cycler = AnimationCycler(self.player_textures, PLAYER_ANIMATION_FRAME_DURATION)
        self.ring_cycler = AnimationCycler(self.ring_textures, RING_ANIMATION_FRAME_DURATION)
        self.coin_cycler = AnimationCycler(self.coin_textures, COIN_ANIMATION_FRAME_DURATION)

        # Event bus: scoring sites emit typed events; sound + visuals
        # subscribe independently. See _wire_event_subscribers below.
        self.events = EventBus()
        self._wire_event_subscribers()

        self.scene = arcade.Scene()
        self.is_game_over = False
        self.ring_combo = 0
        self.coin_combo = 0

        self.gui_camera = arcade.Camera2D()

        self.score = 0
        self.is_paused = False
        # Player state machine (Normal / Shielded / Invincible / Dashing).
        # NormalState is a no-op default; power-ups will swap this in later.
        self.player_state: PlayerState = NormalState()
        # Tracks whether the analog stick is currently "pushed" past the
        # deadzone — emulates LEFT/RIGHT keyboard press/release transitions.
        self._stick_left_pressed = False
        self._stick_right_pressed = False
        self.score_text = arcade.Text(f"Score: {self.score}", x=10, y=WINDOW_HEIGHT - 20, color=arcade.color.WHITE, font_size=14)
        self.paused_text = arcade.Text(
            "PAUSED  (P or A to resume)",
            x=WINDOW_WIDTH - 10,
            y=WINDOW_HEIGHT - 20,
            color=arcade.color.YELLOW,
            font_size=14,
            anchor_x="right",
        )
        # Game-over panel: hierarchy of separate text elements drawn over a card
        # so the screen reads as a finished, intentional state.
        self.game_over_heading_text = arcade.Text(
            "GAME OVER",
            x=WINDOW_WIDTH // 2, y=520,
            color=arcade.color.CRIMSON,
            font_size=72, anchor_x="center", anchor_y="center", bold=True,
        )
        self.game_over_score_text = arcade.Text(
            "", x=WINDOW_WIDTH // 2, y=435,
            color=arcade.color.WHITE,
            font_size=36, anchor_x="center", anchor_y="center", bold=True,
        )
        self.game_over_best_text = arcade.Text(
            "", x=WINDOW_WIDTH // 2, y=385,
            color=arcade.color.GOLD,
            font_size=26, anchor_x="center", anchor_y="center",
        )
        self.game_over_new_record_text = arcade.Text(
            "★  NEW RECORD!  ★", x=WINDOW_WIDTH // 2, y=345,
            color=arcade.color.HOT_PINK,
            font_size=22, anchor_x="center", anchor_y="center", bold=True,
        )
        self.game_over_replay_text = arcade.Text(
            "Press ENTER or A to play again",
            x=WINDOW_WIDTH // 2, y=270,
            color=arcade.color.WHITE,
            font_size=22, anchor_x="center", anchor_y="center", bold=True,
        )
        self.game_over_title_back_text = arcade.Text(
            "Press R or B for title",
            x=WINDOW_WIDTH // 2, y=230,
            color=(200, 200, 200),
            font_size=20, anchor_x="center", anchor_y="center",
        )
        self.game_over_quit_text = arcade.Text(
            "Press Q to quit",
            x=WINDOW_WIDTH // 2, y=195,
            color=(200, 200, 200),
            font_size=20, anchor_x="center", anchor_y="center",
        )
        self.is_new_record = False
        self.game_over_time = 0.0

        # Mountains sit furthest back — added first so they draw behind clouds.
        self.scene.add_sprite_list("Mountains")
        for i in range(NUM_MOUNTAINS):
            x = (WINDOW_WIDTH * i) // NUM_MOUNTAINS + random.randint(-150, 150)
            self.scene.add_sprite("Mountains", self.make_mountain(x))

        # Clouds drawn next so they float in front of the mountains.
        self.scene.add_sprite_list("Clouds")
        for _ in range(NUM_CLOUDS):
            self.scene.add_sprite(
                "Clouds",
                self.make_cloud(random.randint(0, WINDOW_WIDTH)),
            )

        # Create the player sprite
        self.player_sprite = arcade.Sprite(self.player_textures[0], scale=4)
        self.player_sprite.center_x = 64
        self.player_sprite.center_y = WINDOW_HEIGHT - 64
        self.scene.add_sprite("Player", self.player_sprite)
        self.scene.add_sprite_list("Pipes")
        self.scene.add_sprite_list("Boulders")
        self.scene.add_sprite_list("OrbitObstacles")
        self.scene.add_sprite_list("Rings")
        self.scene.add_sprite_list("Coins")
        self.scene.add_sprite_list("ScoreZones")
        self.scene.add_sprite_list("Particles")
        self.floating_texts = []
        # Wolves live outside the scene so we can draw their bubble glow
        # behind the wolf sprite at exactly the right z-order.
        self.wolves: list[arcade.Sprite] = []
        # When a wolf spawns, it stashes its y here so the *next* column's
        # gap_center is clamped near that altitude (reachable in one transition).
        self.next_gap_center_bias: float | None = None

        self.player_sprite.change_y = 0
        self.moving_horizontally = False

        self.next_pipe_spacing = random.randint(MIN_PIPE_SPACING, MAX_PIPE_SPACING)


    def on_key_press(self, key, modifiers):
        """ Called whenever a key is pressed. """
        if self.is_game_over:
            # Deliberately ignore SPACE here — players are usually still flapping
            # when they die and would otherwise blow past the game-over screen.
            # Replay is also gated on GAME_OVER_INPUT_DELAY so a mashed ENTER
            # right at death doesn't accidentally skip the score screen.
            if key == arcade.key.ENTER or key == arcade.key.RETURN:
                if self.game_over_time >= GAME_OVER_INPUT_DELAY:
                    self.window.show_view(GameView())
            elif key == arcade.key.R:
                self.window.show_view(TitleView())
            elif key == arcade.key.Q:
                self.window.close()
            return

        if key == arcade.key.P:
            self.is_paused = not self.is_paused
            return

        if self.is_paused:
            if key == arcade.key.SPACE:
                self.is_paused = False
            return

        if key == arcade.key.SPACE:
            self.player_sprite.change_y = FLAP_VELOCITY
            arcade.play_sound(self.jump_sound)
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.player_sprite.change_x = -PLAYER_X_SPEED
            self.moving_horizontally = True
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.player_sprite.change_x = PLAYER_X_SPEED
            self.moving_horizontally = True

    def on_key_release(self, key, modifiers):
        """ Called when the user releases a key. """
        if key == arcade.key.LEFT or key == arcade.key.A:
            #self.player_sprite.change_x = 0
            self.moving_horizontally = False
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            #self.player_sprite.change_x = 0
            self.moving_horizontally = False

    def on_button_press(self, button):
        # Game-over branch: A/Start = play again, B = back to title.
        if self.is_game_over:
            if button in ("a", "start"):
                self.on_key_press(arcade.key.ENTER, 0)
            elif button in ("b", "back"):
                self.on_key_press(arcade.key.R, 0)
            return
        # Pause branch: A/Start = unpause.
        if self.is_paused:
            if button in ("a", "start"):
                self.on_key_press(arcade.key.P, 0)
            return
        # Live gameplay.
        if button == "a":
            self.on_key_press(arcade.key.SPACE, 0)
        elif button == "start":
            self.on_key_press(arcade.key.P, 0)
        elif button == "dpleft":
            self.on_key_press(arcade.key.LEFT, 0)
        elif button == "dpright":
            self.on_key_press(arcade.key.RIGHT, 0)

    def on_button_release(self, button):
        if self.is_paused or self.is_game_over:
            return
        if button == "dpleft":
            self.on_key_release(arcade.key.LEFT, 0)
        elif button == "dpright":
            self.on_key_release(arcade.key.RIGHT, 0)

    def on_stick_motion(self, x, _y):
        """ Emulate LEFT/RIGHT key presses from the left-stick X axis. (Y unused.) """
        if self.is_paused or self.is_game_over:
            return
        pressed_left = x < -GAMEPAD_STICK_DEADZONE
        if pressed_left and not self._stick_left_pressed:
            self.on_key_press(arcade.key.LEFT, 0)
            self._stick_left_pressed = True
        elif not pressed_left and self._stick_left_pressed:
            self.on_key_release(arcade.key.LEFT, 0)
            self._stick_left_pressed = False
        pressed_right = x > GAMEPAD_STICK_DEADZONE
        if pressed_right and not self._stick_right_pressed:
            self.on_key_press(arcade.key.RIGHT, 0)
            self._stick_right_pressed = True
        elif not pressed_right and self._stick_right_pressed:
            self.on_key_release(arcade.key.RIGHT, 0)
            self._stick_right_pressed = False


    def on_hide_view(self):
        # Stop any active rain loop when leaving GameView (replay / back to title).
        self.weather.shutdown()

    def on_update(self, delta_time):
        """ Movement and game logic """
        if self.is_paused:
            return

        # Weather keeps cycling during game-over so the world still feels alive
        # on the frozen screen — but freeze entirely while paused.
        self.weather.update(delta_time)

        if self.is_game_over:
            self.game_over_time += delta_time
            return

        # Tick the player state machine. A state may self-transition when a
        # timer expires (e.g., invincibility wearing off back to normal).
        next_state = self.player_state.update(self.player_sprite, delta_time)
        if next_state is not None:
            self._transition_player_state(next_state)

        self.player_sprite.change_y -= GRAVITY
        # Wind gusts push the bird (downdraft) while it's inside their corridor.
        fx, fy = self.weather.force_at(self.player_sprite.center_x, self.player_sprite.center_y)
        self.player_sprite.change_x += fx
        self.player_sprite.change_y += fy
        self.player_sprite.center_y += self.player_sprite.change_y
        self.player_sprite.center_x += self.player_sprite.change_x

        # Clamp at the top of the screen — flying off the top no longer kills.
        if self.player_sprite.top > WINDOW_HEIGHT:
            self.player_sprite.top = WINDOW_HEIGHT
            self.player_sprite.change_y = 0

        # Cycle through the animation frames
        self.bird_cycler.tick(delta_time)
        self.player_sprite.texture = self.bird_cycler.current
        if self.player_sprite.change_x > 0 and not self.moving_horizontally:
            self.player_sprite.change_x -= PLAYER_X_FRICTION
            self.player_sprite.change_x = max(self.player_sprite.change_x, 0)
        elif self.player_sprite.change_x < 0 and not self.moving_horizontally:
            self.player_sprite.change_x += PLAYER_X_FRICTION
            self.player_sprite.change_x = min(self.player_sprite.change_x, 0)

        if self.player_sprite.center_x < PLAYER_MIN_X:
            self.player_sprite.center_x = PLAYER_MIN_X
        elif self.player_sprite.center_x > PLAYER_MAX_X:
            self.player_sprite.center_x = PLAYER_MAX_X

        # Move and remove existing pipes
        self.move_and_remove_existing_pipes(delta_time)
        self.move_boulders(delta_time)
        self.move_orbit_obstacles(delta_time)
        self.move_rings(delta_time)
        self.move_coins(delta_time)
        self.update_wolves(delta_time)
        self.update_particles(delta_time)
        self.update_floating_texts(delta_time)

        # Spawn new pipes
        self.spawn_pipes()

        # Drift mountains and clouds for parallax depth
        self.move_mountains()
        self.move_clouds()

        # Collision detection — pipes, boulders, or spiky balls. The current
        # player state decides what happens on contact (game over, shielded
        # absorb, or invincible plow-through).
        if (arcade.check_for_collision_with_list(self.player_sprite, self.scene["Pipes"])
                or arcade.check_for_collision_with_list(self.player_sprite, self.scene["Boulders"])
                or arcade.check_for_collision_with_list(self.player_sprite, self.scene["OrbitObstacles"])):
            result = self.player_state.on_collision(self.player_sprite)
            if result.game_over:
                self.game_over()
            if result.next_state is not None:
                self._transition_player_state(result.next_state)

        score_zone_hits = arcade.check_for_collision_with_list(
            self.player_sprite,
            self.scene["ScoreZones"],
        )

        for score_zone in score_zone_hits:
            score_zone.remove_from_sprite_lists()
            self._award_score(1)
            self.events.emit(ScoreZoneCleared(
                x=self.player_sprite.center_x,
                y=self.player_sprite.center_y,
            ))

        ring_hits = arcade.check_for_collision_with_list(
            self.player_sprite,
            self.scene["Rings"],
        )
        for ring in ring_hits:
            self.ring_combo += 1
            bonus = scoring.combo_bonus(self.ring_combo, RING_POINTS, RING_COMBO_BONUS_STEP)
            self._award_score(bonus)
            self.events.emit(RingCollected(
                x=ring.center_x, y=ring.center_y,
                combo=self.ring_combo, bonus=bonus,
            ))
            ring.remove_from_sprite_lists()

        coin_hits = arcade.check_for_collision_with_list(
            self.player_sprite,
            self.scene["Coins"],
        )
        for coin in coin_hits:
            self.coin_combo += 1
            self._award_score(COIN_POINTS)
            self.events.emit(CoinCollected(
                x=coin.center_x, y=coin.center_y, points=COIN_POINTS,
            ))
            streak_bonus = scoring.coin_streak_bonus(
                self.coin_combo,
                COIN_STREAK_THRESHOLD,
                COIN_STREAK_BASE_BONUS,
                COIN_STREAK_BONUS_CAP,
            )
            if streak_bonus is not None:
                self._award_score(streak_bonus)
                self.events.emit(CoinStreakBonus(
                    x=coin.center_x, y=coin.center_y,
                    combo=self.coin_combo, bonus=streak_bonus,
                ))
            coin.remove_from_sprite_lists()

        # Non-fatal: touching a caged wolf frees it for a big bonus.
        self.check_wolf_collisions()

        # Forgiving floor: bird can dip its center BOTTOM_GRACE_PIXELS past the
        # bottom edge and still flap back up.
        if self.player_sprite.center_y < -BOTTOM_GRACE_PIXELS:
            self.game_over()

    def _transition_player_state(self, new_state: PlayerState) -> None:
        """ Swap to a new player state, firing exit/enter hooks for visual
        or audio side effects (shield bubble on, star-trail off, etc.). """
        self.player_state.exit(self.player_sprite)
        self.player_state = new_state
        self.player_state.enter(self.player_sprite)

    def game_over(self):
        # Idempotent — collision and out-of-bounds checks can both fire on the
        # same frame, but we should only record one score and play one sound.
        if self.is_game_over:
            return
        self.is_game_over = True

        store = getattr(self.window, "score_store", None)
        profile = store.current_profile if store else DEFAULT_PROFILE
        previous_best = store.personal_best(profile) if store else 0
        if store:
            store.record(profile, self.score)
            store.save()

        new_best = max(previous_best, self.score)
        self.is_new_record = self.score > previous_best and self.score > 0
        self.game_over_score_text.text = f"Final score: {self.score}"
        self.game_over_best_text.text = f"Personal best: {new_best}"
        self.game_over_time = 0.0  # restart the input-cooldown clock
        self.events.emit(GameOver(score=self.score))


    def should_generate_new_pipe(self):
        # Look at the rightmost sprite across all spawnable slots so spacing is
        # consistent regardless of which kind was spawned last. For orbiting
        # obstacles, prefer the orbit center (motion.base_x) over the
        # currently-oscillating center_x — motions that don't track a
        # horizontal anchor fall back to center_x.
        last_x = -float("inf")
        for list_name in ("Pipes", "Boulders", "Rings", "OrbitObstacles"):
            sprites = self.scene.get_sprite_list(list_name)
            if sprites:
                anchor = sprites[-1]
                motion = getattr(anchor, "motion", None)
                if motion is not None and hasattr(motion, "base_x"):
                    x = motion.base_x
                else:
                    x = anchor.center_x
                last_x = max(last_x, x)
        if last_x == -float("inf"):
            return True
        return last_x < WINDOW_WIDTH - self.next_pipe_spacing

    def make_top_column(self, center_x, gap_top, extend_for_oscillation=0):
        """ Column hanging from the ceiling. Cap sits flush above the gap; mid tiles stack upward.
        extend_for_oscillation pads the column past the screen edge so it still covers when the
        gap slides downward. """
        centers = geometry.top_column_tile_centers(
            gap_top=gap_top,
            tile_size=COLUMN_TILE_RENDERED,
            overlap=COLUMN_TILE_VERTICAL_OVERLAP,
            target_top=WINDOW_HEIGHT + extend_for_oscillation,
        )
        tiles = []
        for i, center_y in enumerate(centers):
            if i == 0:
                texture = random.choice(self.column_ceiling_cap_textures)
            else:
                texture = random.choice(self.column_mid_textures)
            tile = arcade.Sprite(texture, scale=COLUMN_TILE_SCALE)
            tile.center_x = center_x
            tile.center_y = center_y
            tiles.append(tile)
        return tiles

    def make_bottom_column(self, center_x, gap_bottom, extend_for_oscillation=0):
        """ Column rising from the floor. Cap sits flush below the gap; mid tiles stack downward.
        extend_for_oscillation pads past the bottom of the screen for oscillating gaps. """
        centers = geometry.bottom_column_tile_centers(
            gap_bottom=gap_bottom,
            tile_size=COLUMN_TILE_RENDERED,
            overlap=COLUMN_TILE_VERTICAL_OVERLAP,
            target_bottom=-extend_for_oscillation,
        )
        tiles = []
        for i, center_y in enumerate(centers):
            if i == 0:
                texture = random.choice(self.column_floor_cap_textures)
            else:
                texture = random.choice(self.column_mid_textures)
            tile = arcade.Sprite(texture, scale=COLUMN_TILE_SCALE)
            tile.center_x = center_x
            tile.center_y = center_y
            tiles.append(tile)
        return tiles

    def make_middle_pipe(self, center_x, gap_center, gap_size):
        """ Thin invisible trip-wire placed past the right edge of the column. """
        pipe = arcade.SpriteSolidColor(
            width=SCORE_ZONE_WIDTH,
            height=gap_size,
            color=arcade.color.RED,
        )
        pipe.center_x = center_x + SCORE_ZONE_X_OFFSET
        pipe.center_y = gap_center
        pipe.visible = False
        return pipe



    def spawn_pipes(self):
        if not self.should_generate_new_pipe():
            return

        # Snapshot the wolf bias for THIS spawn, then clear so it only ever
        # affects the immediate next obstacle after a wolf.
        gap_bias = self.next_gap_center_bias
        self.next_gap_center_bias = None

        # Difficulty curves live in difficulty.py — pure functions that
        # interpolate from the *_AT_START values to *_AT_MAX_DIFFICULTY values
        # as the score climbs to DIFFICULTY_RAMP_SCORE.
        spacing_factor = difficulty.spacing_factor(
            self.score, DIFFICULTY_RAMP_SCORE,
            SPACING_RATIO_AT_START, SPACING_RATIO_AT_MAX_DIFFICULTY,
        )

        # Spawn just off the right edge of the screen
        column_x = WINDOW_WIDTH + COLUMN_TILE_RENDERED // 2

        # Single weighted roll picks wolf / spiky / ring / boulder / column-pair.
        # Branches stay flat instead of accumulating cumulative thresholds.
        kind = OBSTACLE_SPAWN_TABLE.pick(random.random())
        if kind == "wolf":
            # Rare rescue opportunity — wolf in a bubble at an off-center altitude.
            self.spawn_wolf(column_x)
        elif kind == "spiky":
            # Rotating spiky ball: deadly on contact, scores by clearing.
            ball = self.make_spiky_ball(column_x)
            self.scene.add_sprite("OrbitObstacles", ball)
            # Full-window-height score-zone trip-wire (like boulders).
            score_zone = arcade.SpriteSolidColor(
                width=SCORE_ZONE_WIDTH, height=WINDOW_HEIGHT, color=arcade.color.RED,
            )
            score_zone.center_x = column_x + SCORE_ZONE_X_OFFSET
            score_zone.center_y = WINDOW_HEIGHT // 2
            score_zone.visible = False
            score_zone.motion = LinearMotion(vx=-PIPE_SPEED)
            self.scene.add_sprite("ScoreZones", score_zone)
            # Make the next column reachable from the ball's orbit center.
            self.next_gap_center_bias = ball.motion.base_y
        elif kind == "ring":
            # Bonus ring spawn (non-fatal pickup).
            self.scene.add_sprite("Rings", self.make_ring(column_x))
        elif kind == "boulder":
            # Spawn a single oscillating boulder instead of a column pair. Constrain
            # its lowest swing so the bonus ring at the floor stays reachable.
            self.scene.add_sprite(
                "Boulders",
                self.make_boulder(column_x, min_lowest_y=BOULDER_LOWEST_Y_WITH_BONUS_RING),
            )
            # Boulder score zone spans the full window height — the bird scores by clearing
            # the boulder horizontally regardless of its y at the moment.
            score_zone = arcade.SpriteSolidColor(
                width=SCORE_ZONE_WIDTH,
                height=WINDOW_HEIGHT,
                color=arcade.color.RED,
            )
            score_zone.center_x = column_x + SCORE_ZONE_X_OFFSET
            score_zone.center_y = WINDOW_HEIGHT // 2
            score_zone.visible = False
            score_zone.motion = LinearMotion(vx=-PIPE_SPEED)
            self.scene.add_sprite("ScoreZones", score_zone)
            # Risk-reward: a static bonus ring near the floor, tempting the player to
            # fly *under* the boulder instead of over it.
            self.scene.add_sprite("Rings", self.make_bonus_ring(column_x))
        else:  # kind == "column"
            # Column pair (static or oscillating). Difficulty scaling applies in both cases.
            gap_factor_value = difficulty.gap_factor(
                self.score, DIFFICULTY_RAMP_SCORE,
                GAP_RATIO_AT_START, GAP_RATIO_AT_MAX_DIFFICULTY,
            )
            gap_size = random.randint(
                int(MIN_PIPE_CENTER_GAP * gap_factor_value),
                int(MAX_PIPE_CENTER_GAP * gap_factor_value),
            )

            oscillating = random.random() < OSCILLATING_PIPE_CHANCE
            if oscillating:
                # Keep the gap center far enough from screen edges that the oscillation never
                # pushes it off-screen.
                gap_y_min = MIN_PIPE_CENTER_GAP_Y + PIPE_AMPLITUDE_MAX
                gap_y_max = MAX_PIPE_CENTER_GAP_Y - PIPE_AMPLITUDE_MAX
            else:
                gap_y_min = MIN_PIPE_CENTER_GAP_Y
                gap_y_max = MAX_PIPE_CENTER_GAP_Y
            # If the previous spawn was a wolf, clamp the gap to be reachable
            # from the wolf's altitude so the player isn't stuck behind a column.
            if gap_bias is not None:
                gap_y_min = max(gap_y_min, int(gap_bias) - WOLF_REACHABLE_DELTA_Y)
                gap_y_max = min(gap_y_max, int(gap_bias) + WOLF_REACHABLE_DELTA_Y)
                if gap_y_min > gap_y_max:
                    gap_y_min = gap_y_max = (gap_y_min + gap_y_max) // 2
            gap_center = random.randint(gap_y_min, gap_y_max)
            if oscillating:
                amplitude = random.randint(PIPE_AMPLITUDE_MIN, PIPE_AMPLITUDE_MAX)
                phase = random.uniform(0, 2 * math.pi)
                phase_speed = random.uniform(PIPE_PHASE_SPEED_MIN, PIPE_PHASE_SPEED_MAX)
                extend = PIPE_AMPLITUDE_MAX
            else:
                amplitude = 0
                phase = 0
                phase_speed = 0
                extend = 0

            gap_top = gap_center + gap_size // 2
            gap_bottom = gap_center - gap_size // 2

            top_tiles = self.make_top_column(column_x, gap_top, extend_for_oscillation=extend)
            bottom_tiles = self.make_bottom_column(column_x, gap_bottom, extend_for_oscillation=extend)
            middle_pipe = self.make_middle_pipe(column_x, gap_center, gap_size)

            sprites = top_tiles + bottom_tiles + [middle_pipe]
            # Every column tile + score zone gets a Motion. Static columns
            # use LinearMotion; oscillating columns use SineMotion with all
            # tiles sharing the same amplitude/phase_speed/phase so they bob
            # in lock-step.
            for sprite in sprites:
                if oscillating:
                    sprite.motion = SineMotion(
                        base_y=sprite.center_y,
                        amplitude=amplitude,
                        phase_speed=phase_speed,
                        phase=phase,
                        vx=-PIPE_SPEED,
                    )
                    sprite.motion.place(sprite)
                else:
                    sprite.motion = LinearMotion(vx=-PIPE_SPEED)

            for tile in top_tiles + bottom_tiles:
                self.scene.add_sprite("Pipes", tile)
            self.scene.add_sprite("ScoreZones", middle_pipe)

        # Pick the spacing until the next spawn (also scaled by difficulty)
        self.next_pipe_spacing = random.randint(
            int(MIN_PIPE_SPACING * spacing_factor),
            int(MAX_PIPE_SPACING * spacing_factor),
        )

        # Drop a coin cluster halfway between this obstacle and the next one
        # (both will be moving leftward in lock-step, so relative spacing is preserved).
        coin_cluster_x = column_x + self.next_pipe_spacing // 2
        coin_cluster_y = random.randint(COIN_Y_MIN, COIN_Y_MAX)
        self.spawn_coin_cluster(coin_cluster_x, coin_cluster_y)



    def move_and_remove_existing_pipes(self, delta_time):
        # Every pipe + score zone has a Motion (LinearMotion for static,
        # SineMotion for oscillating); the loop is uniform.
        for sprite_list_name in ("Pipes", "ScoreZones"):
            for pipe in self.scene.get_sprite_list(sprite_list_name):
                pipe.motion.update(pipe, delta_time)
                if pipe.right < 0:
                    pipe.remove_from_sprite_lists()

    def make_boulder(self, x, min_lowest_y=None):
        """ Build a randomized oscillating boulder.

        If min_lowest_y is given, the chosen base_y and amplitude are clamped so
        that base_y - amplitude >= min_lowest_y (the boulder never dips below
        that point). Used when a bonus ring is parked under it so the boulder
        can't pin the bird against the floor.
        """
        amplitude = random.randint(BOULDER_AMPLITUDE_MIN, BOULDER_AMPLITUDE_MAX)
        base_y_min = BOULDER_BASE_Y_MIN
        if min_lowest_y is not None:
            base_y_min = max(base_y_min, min_lowest_y + amplitude)
            if base_y_min > BOULDER_BASE_Y_MAX:
                # Constraint can't fit at this amplitude — shrink amplitude to fit.
                amplitude = max(BOULDER_AMPLITUDE_MIN, BOULDER_BASE_Y_MAX - min_lowest_y)
                base_y_min = min_lowest_y + amplitude

        boulder = arcade.Sprite(
            random.choice(self.boulder_textures),
            scale=BOULDER_SCALE,
        )
        boulder.center_x = x
        boulder.motion = SineMotion(
            base_y=random.randint(base_y_min, BOULDER_BASE_Y_MAX),
            amplitude=amplitude,
            phase_speed=random.uniform(BOULDER_PHASE_SPEED_MIN, BOULDER_PHASE_SPEED_MAX),
            phase=random.uniform(0, 2 * math.pi),
            vx=-PIPE_SPEED,
        )
        boulder.motion.place(boulder)
        return boulder

    def move_boulders(self, delta_time):
        for boulder in self.scene.get_sprite_list("Boulders"):
            boulder.motion.update(boulder, delta_time)
            if boulder.right < 0:
                boulder.remove_from_sprite_lists()

    def make_spiky_ball(self, x):
        """ A spiky ball orbiting a center that scrolls left at PIPE_SPEED.
        Uses the Strategy-pattern CircularMotion from motion.py. """
        ball = arcade.Sprite(self.spiky_ball_texture, scale=SPIKY_BALL_SCALE)
        base_y = random.randint(SPIKY_BALL_BASE_Y_MIN, SPIKY_BALL_BASE_Y_MAX)
        radius = random.randint(SPIKY_BALL_RADIUS_MIN, SPIKY_BALL_RADIUS_MAX)
        angular_speed = random.uniform(SPIKY_BALL_ANGULAR_SPEED_MIN, SPIKY_BALL_ANGULAR_SPEED_MAX)
        if random.random() < 0.5:
            angular_speed = -angular_speed  # randomize CW vs CCW
        motion = CircularMotion(
            base_x=x, base_y=base_y,
            radius=radius, angular_speed=angular_speed,
            phase=random.uniform(0, 2 * math.pi),
            vx=-PIPE_SPEED,
        )
        motion.place(ball)
        ball.motion = motion
        return ball

    def move_orbit_obstacles(self, delta_time):
        """ Advance each orbit obstacle via its Motion strategy, spin the
        sprite visually, and cull when the orbit center is fully past the
        left edge. """
        for obstacle in self.scene.get_sprite_list("OrbitObstacles"):
            obstacle.motion.update(obstacle, delta_time)
            obstacle.angle += SPIKY_BALL_SPIN_DEGREES_PER_FRAME
            if obstacle.motion.base_x + obstacle.motion.radius < 0:
                obstacle.remove_from_sprite_lists()

    def make_ring(self, x):
        ring = arcade.Sprite(self.ring_textures[0], scale=RING_SCALE)
        ring.center_x = x
        ring.motion = SineMotion(
            base_y=random.randint(RING_BASE_Y_MIN, RING_BASE_Y_MAX),
            amplitude=random.randint(RING_AMPLITUDE_MIN, RING_AMPLITUDE_MAX),
            phase_speed=random.uniform(RING_PHASE_SPEED_MIN, RING_PHASE_SPEED_MAX),
            phase=random.uniform(0, 2 * math.pi),
            vx=-PIPE_SPEED,
        )
        ring.motion.place(ring)
        return ring

    def make_bonus_ring(self, x):
        """ Static low-altitude ring used as a risk-reward pickup under boulders.
        Uses SineMotion with amplitude=0 for a pinned y. """
        ring = arcade.Sprite(self.ring_textures[0], scale=RING_SCALE)
        ring.center_x = x
        ring.motion = SineMotion(
            base_y=random.randint(BONUS_RING_Y_MIN, BONUS_RING_Y_MAX),
            amplitude=0,
            phase_speed=0,
            vx=-PIPE_SPEED,
        )
        ring.motion.place(ring)
        return ring

    def spawn_burst(self, x, y, count=PARTICLES_PER_BURST, colors=PARTICLE_COLORS):
        """ Spawn an outward starburst of small circles at the collection point. """
        for _ in range(count):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(PARTICLE_SPEED_MIN, PARTICLE_SPEED_MAX)
            particle = arcade.SpriteCircle(
                radius=random.randint(PARTICLE_RADIUS_MIN, PARTICLE_RADIUS_MAX),
                color=random.choice(colors),
            )
            particle.center_x = x
            particle.center_y = y
            particle.change_x = math.cos(angle) * speed
            particle.change_y = math.sin(angle) * speed
            particle.lifetime = PARTICLE_LIFETIME
            self.scene.add_sprite("Particles", particle)

    def update_particles(self, delta_time):
        for particle in self.scene.get_sprite_list("Particles"):
            particle.change_y -= PARTICLE_GRAVITY
            particle.center_x += particle.change_x
            particle.center_y += particle.change_y
            particle.lifetime -= delta_time
            if particle.lifetime <= 0:
                particle.remove_from_sprite_lists()
            else:
                particle.alpha = int(255 * (particle.lifetime / PARTICLE_LIFETIME))

    def spawn_floating_text(self, x, y, message, color=None):
        if color is None:
            color = random.choice(FLOATING_TEXT_COLORS)
        text = arcade.Text(
            message,
            x=x,
            y=y,
            color=color,
            font_size=FLOATING_TEXT_START_SIZE,
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )
        text.lifetime = FLOATING_TEXT_LIFETIME
        text.base_rgb = tuple(color)[:3]
        text.is_milestone = False
        self.floating_texts.append(text)

    def spawn_celebration_text(
        self,
        message,
        color=MILESTONE_COLOR,
        start_size=MILESTONE_TEXT_START_SIZE,
        end_size=MILESTONE_TEXT_END_SIZE,
        x=None,
        y=None,
    ):
        """ Big centered "grow + fade" celebration text. Used by milestones,
        wolf rescues, and coin streaks. ``start_size``/``end_size`` override
        the default 80 → 140 ramp for callers whose message is too long to
        fit at the default size. ``x``/``y`` override the default screen
        center so banner-style stamps don't overlap each other when two fire
        on the same frame. """
        text = arcade.Text(
            message,
            x=WINDOW_WIDTH // 2 if x is None else x,
            y=WINDOW_HEIGHT // 2 if y is None else y,
            color=color,
            font_size=start_size,
            anchor_x="center",
            anchor_y="center",
            bold=True,
        )
        text.lifetime = MILESTONE_TEXT_LIFETIME
        text.base_rgb = tuple(color)[:3]
        text.is_milestone = True
        text.start_size = start_size
        text.end_size = end_size
        self.floating_texts.append(text)

    def spawn_milestone_text(self, value):
        self.spawn_celebration_text(f"{value}!", MILESTONE_COLOR)

    def _wire_event_subscribers(self):
        """ Register every visual / audio side effect against the event bus.

        Each handler does ONE thing (a sound, a particle burst, a floating
        text) so future subscribers — achievements, music ducking, stats —
        can attach without touching this code path or any scoring site. """
        bus = self.events

        # --- Sounds ---
        bus.subscribe(ScoreZoneCleared, lambda e: arcade.play_sound(self.coin_sound))
        bus.subscribe(CoinCollected, lambda e: arcade.play_sound(self.coin_sound))
        bus.subscribe(RingCollected, lambda e: arcade.play_sound(
            self.ring_sound,
            speed=scoring.combo_pitch(e.combo, RING_PITCH_STEP, RING_PITCH_MAX),
        ))
        bus.subscribe(WolfRescued, lambda e: arcade.play_sound(
            self.howl_sound, volume=WOLF_HOWL_VOLUME,
        ))
        bus.subscribe(MilestoneCrossed, lambda e: arcade.play_sound(
            self.milestone_sound, volume=MILESTONE_VOLUME,
        ))
        bus.subscribe(CoinStreakBonus, lambda e: arcade.play_sound(
            self.milestone_sound,
            speed=COIN_STREAK_SOUND_SPEED,
            volume=COIN_STREAK_SOUND_VOLUME,
        ))
        bus.subscribe(GameOver, lambda e: arcade.play_sound(self.gameover_sound))

        # --- Floating / celebration text ---
        # Score-zone text spawns at the bird so it's visible regardless of
        # the zone's height (boulder zones span the whole window).
        bus.subscribe(ScoreZoneCleared, lambda e: self.spawn_floating_text(
            self.player_sprite.center_x, self.player_sprite.center_y, "+1",
        ))
        bus.subscribe(RingCollected, lambda e: self.spawn_floating_text(
            e.x, e.y, f"+{e.bonus}",
        ))
        bus.subscribe(CoinCollected, lambda e: self.spawn_floating_text(
            e.x, e.y, f"+{e.points}",
        ))
        bus.subscribe(WolfRescued, lambda e: self.spawn_celebration_text(
            f"WOLF SAVED!  +{e.points}", WOLF_CELEBRATION_COLOR,
        ))
        bus.subscribe(MilestoneCrossed, lambda e: self.spawn_milestone_text(e.value))
        bus.subscribe(CoinStreakBonus, lambda e: self.spawn_celebration_text(
            f"COIN STREAK x{e.combo}!  +{e.bonus}",
            COIN_STREAK_COLOR,
            start_size=COIN_STREAK_TEXT_START_SIZE,
            end_size=COIN_STREAK_TEXT_END_SIZE,
            y=COIN_STREAK_TEXT_Y,
        ))

        # --- Particle bursts ---
        bus.subscribe(RingCollected, lambda e: self.spawn_burst(e.x, e.y))
        bus.subscribe(CoinCollected, lambda e: self.spawn_burst(
            e.x, e.y, count=COIN_PARTICLES_PER_BURST,
        ))
        bus.subscribe(WolfRescued, lambda e: self.spawn_burst(
            e.x, e.y, count=WOLF_PARTICLES_PER_BURST, colors=WOLF_PARTICLE_COLORS,
        ))

    def _award_score(self, points):
        """ Add points, refresh the HUD, and emit a MilestoneCrossed event
        when the new total crosses a multiple of MILESTONE_THRESHOLD. """
        old = self.score
        self.score += points
        self.score_text.text = f"Score: {self.score}"
        milestone = scoring.crossed_milestone(old, self.score, MILESTONE_THRESHOLD)
        if milestone is not None:
            self.events.emit(MilestoneCrossed(value=milestone))

    def update_floating_texts(self, delta_time):
        for text in self.floating_texts[:]:
            text.lifetime -= delta_time
            if text.lifetime <= 0:
                self.floating_texts.remove(text)
                continue
            if text.is_milestone:
                # Stays centered, grows from start to end size, fades over the
                # whole lifetime. No vertical drift — it's a flashy stamp.
                progress = 1.0 - (text.lifetime / MILESTONE_TEXT_LIFETIME)
                text.font_size = lerp(text.start_size, text.end_size, progress)
                alpha = int(255 * (text.lifetime / MILESTONE_TEXT_LIFETIME))
            else:
                text.y += FLOATING_TEXT_RISE_SPEED
                progress = 1.0 - (text.lifetime / FLOATING_TEXT_LIFETIME)
                text.font_size = lerp(
                    FLOATING_TEXT_START_SIZE, FLOATING_TEXT_END_SIZE, progress,
                )
                alpha = int(255 * (text.lifetime / FLOATING_TEXT_LIFETIME))
            text.color = (*text.base_rgb, alpha)

    def move_rings(self, delta_time):
        # Advance the shared spin animation once per frame.
        self.ring_cycler.tick(delta_time)
        current_texture = self.ring_cycler.current

        for ring in self.scene.get_sprite_list("Rings"):
            ring.motion.update(ring, delta_time)
            ring.texture = current_texture
            if ring.right < 0:
                # Ring scrolled off without being collected — combo breaks.
                self.ring_combo = 0
                ring.remove_from_sprite_lists()

    def spawn_coin_cluster(self, center_x, center_y):
        """ Add COINS_PER_CLUSTER coins in a horizontal row centered at (x, y). """
        offset = (COINS_PER_CLUSTER - 1) / 2
        for i in range(COINS_PER_CLUSTER):
            coin = arcade.Sprite(self.coin_textures[0], scale=COIN_SCALE)
            coin.center_x = center_x + (i - offset) * COIN_CLUSTER_SPACING_X
            coin.center_y = center_y
            self.scene.add_sprite("Coins", coin)

    def spawn_wolf(self, x):
        """ Spawn a caged-in-a-bubble wolf at the right edge, biased to upper
        or lower band so reaching it requires altitude commitment. Also stashes
        the y so the next column gap is constrained to be reachable. """
        if random.random() < 0.5:
            y = random.randint(WOLF_Y_LOW_MIN, WOLF_Y_LOW_MAX)
        else:
            y = random.randint(WOLF_Y_HIGH_MIN, WOLF_Y_HIGH_MAX)
        wolf = arcade.Sprite(self.wolf_standing_texture, scale=WOLF_SCALE)
        wolf.center_x = x
        wolf.center_y = y
        wolf.state = "caged"
        wolf.bubble_phase = random.uniform(0, 2 * math.pi)
        wolf.freed_velocity_y = 0.0
        wolf.freed_timer = 0.0
        self.wolves.append(wolf)
        self.next_gap_center_bias = y

    def update_wolves(self, delta_time):
        for wolf in self.wolves[:]:
            if wolf.state == "caged":
                wolf.center_x -= PIPE_SPEED
                wolf.bubble_phase += WOLF_BUBBLE_PULSE_SPEED * delta_time
                if wolf.right < 0:
                    self.wolves.remove(wolf)
            else:  # freed
                wolf.freed_velocity_y += WOLF_FREED_RISE_ACCEL * delta_time
                wolf.center_y += wolf.freed_velocity_y * delta_time
                wolf.center_x -= PIPE_SPEED
                wolf.freed_timer += delta_time
                if (wolf.freed_timer >= WOLF_FREED_LIFETIME
                        or wolf.bottom > WINDOW_HEIGHT):
                    self.wolves.remove(wolf)

    def draw_wolves(self):
        for wolf in self.wolves:
            if wolf.state == "caged":
                # Pulsing translucent bubble — three concentric glow rings + a
                # bright outline give it a "magical sphere" feel.
                pulse = math.sin(wolf.bubble_phase) * WOLF_BUBBLE_PULSE_AMPLITUDE
                r = WOLF_BUBBLE_RADIUS + pulse
                arcade.draw_circle_filled(wolf.center_x, wolf.center_y, r + 18, WOLF_BUBBLE_FILL_OUTER)
                arcade.draw_circle_filled(wolf.center_x, wolf.center_y, r + 9, WOLF_BUBBLE_FILL_MIDDLE)
                arcade.draw_circle_filled(wolf.center_x, wolf.center_y, r, WOLF_BUBBLE_FILL_INNER)
                arcade.draw_circle_outline(wolf.center_x, wolf.center_y, r, WOLF_BUBBLE_OUTLINE_COLOR, 2)
            arcade.draw_sprite(wolf)

    def check_wolf_collisions(self):
        # Collide against the bubble (the visible glow halo), not the wolf
        # sprite inside it. Trigger radius = max bubble extent + bird radius
        # so any visible overlap counts.
        bird_x = self.player_sprite.center_x
        bird_y = self.player_sprite.center_y
        # Approximate the bird as a circle using half its sprite width.
        bird_radius = self.player_sprite.width / 2
        bubble_max_radius = WOLF_BUBBLE_RADIUS + WOLF_BUBBLE_PULSE_AMPLITUDE
        trigger = bubble_max_radius + bird_radius
        trigger_sq = trigger * trigger
        for wolf in self.wolves:
            if wolf.state != "caged":
                continue
            dx = bird_x - wolf.center_x
            dy = bird_y - wolf.center_y
            if dx * dx + dy * dy < trigger_sq:
                self._rescue_wolf(wolf)

    def _rescue_wolf(self, wolf):
        wolf.state = "freed"
        wolf.texture = self.wolf_howling_texture
        wolf.freed_velocity_y = WOLF_FREED_INITIAL_VELOCITY
        self._award_score(WOLF_POINTS)
        self.events.emit(WolfRescued(
            x=wolf.center_x, y=wolf.center_y, points=WOLF_POINTS,
        ))

    def move_coins(self, delta_time):
        # Shared spin animation, like rings — every coin shows the same frame.
        self.coin_cycler.tick(delta_time)
        current_texture = self.coin_cycler.current

        for coin in self.scene.get_sprite_list("Coins"):
            coin.center_x -= PIPE_SPEED
            coin.texture = current_texture
            if coin.right < 0:
                # Coin scrolled off uncollected — streak breaks.
                self.coin_combo = 0
                coin.remove_from_sprite_lists()

    def make_mountain(self, x):
        mountain = arcade.Sprite(self.mountain_texture, scale=MOUNTAIN_SCALE)
        mountain.center_x = x
        mountain.center_y = random.randint(MOUNTAIN_Y_MIN, MOUNTAIN_Y_MAX)
        return mountain

    def move_mountains(self):
        for mountain in self.scene.get_sprite_list("Mountains"):
            mountain.center_x -= MOUNTAIN_SPEED
            if mountain.right < 0:
                mountain.center_x = WINDOW_WIDTH + mountain.width // 2
                mountain.center_y = random.randint(MOUNTAIN_Y_MIN, MOUNTAIN_Y_MAX)

    def _randomize_cloud(self, cloud):
        """ Roll a fresh depth and apply all derived visual + speed properties. """
        depth = random.random()
        cloud.depth = depth  # used to sort the sprite list so far clouds draw behind near ones
        cloud.texture = random.choice(self.cloud_textures)
        cloud.scale = lerp(CLOUD_NEAR_SCALE, CLOUD_FAR_SCALE, depth)
        cloud.center_y = random.randint(CLOUD_Y_MIN, CLOUD_Y_MAX)
        cloud.color = (
            int(lerp(CLOUD_NEAR_TINT[0], CLOUD_FAR_TINT[0], depth)),
            int(lerp(CLOUD_NEAR_TINT[1], CLOUD_FAR_TINT[1], depth)),
            int(lerp(CLOUD_NEAR_TINT[2], CLOUD_FAR_TINT[2], depth)),
        )
        cloud.change_x = -lerp(CLOUD_NEAR_SPEED, CLOUD_FAR_SPEED, depth)

    def make_cloud(self, x):
        cloud = arcade.Sprite(self.cloud_textures[0])
        self._randomize_cloud(cloud)
        cloud.center_x = x
        return cloud

    def move_clouds(self):
        """ Scroll clouds left at their per-cloud speed; recycle off-screen clouds. """
        recycled = False
        for cloud in self.scene.get_sprite_list("Clouds"):
            cloud.center_x += cloud.change_x
            if cloud.right < 0:
                self._randomize_cloud(cloud)
                cloud.center_x = WINDOW_WIDTH + cloud.width // 2
                recycled = True
        if recycled:
            # Far clouds (depth=1) draw first so near clouds (depth=0) sit on top.
            self.scene.get_sprite_list("Clouds").sort(key=lambda c: c.depth, reverse=True)


    def on_draw(self):
        self.clear()
        self.gui_camera.use()
        arcade.draw_sprite(self.sky_sprite)
        self.scene.draw()
        # Wolves sit on top of obstacles so the bubble glow reads cleanly.
        self.draw_wolves()
        # Weather sits in front of the game world (camera-lens style) — rain
        # plus any active lightning flash overlay — but behind the HUD so
        # floating text and the score remain legible.
        self.weather.draw()
        for text in self.floating_texts:
            text.draw()
        self.score_text.draw()
        if self.is_paused:
            self.paused_text.draw()
        if self.is_game_over:
            self._draw_game_over_panel()

    def _draw_game_over_panel(self):
        # Centered card backdrop with a gold border so the text sits on a solid
        # black panel instead of the busy game world.
        arcade.draw_lbwh_rectangle_filled(
            GAME_OVER_CARD_LEFT, GAME_OVER_CARD_BOTTOM,
            GAME_OVER_CARD_WIDTH, GAME_OVER_CARD_HEIGHT,
            GAME_OVER_CARD_FILL,
        )
        arcade.draw_lbwh_rectangle_outline(
            GAME_OVER_CARD_LEFT, GAME_OVER_CARD_BOTTOM,
            GAME_OVER_CARD_WIDTH, GAME_OVER_CARD_HEIGHT,
            GAME_OVER_CARD_BORDER, 3,
        )
        self.game_over_heading_text.draw()
        self.game_over_score_text.draw()
        self.game_over_best_text.draw()
        if self.is_new_record:
            self.game_over_new_record_text.draw()

        # Replay prompt fades in over the input-cooldown window so the player
        # can't accidentally mash past their score.
        progress = min(self.game_over_time / GAME_OVER_INPUT_DELAY, 1.0)
        alpha = int(60 + 195 * progress)  # 60 -> 255
        self.game_over_replay_text.color = (255, 255, 255, alpha)
        self.game_over_replay_text.draw()

        self.game_over_title_back_text.draw()
        self.game_over_quit_text.draw()


def _silence_macos_hid_keyerror():
    """ Some HID controllers (notably the Nintendo Switch Pro Controller) report
    element cookies that pyglet's macOS Controller mapping doesn't recognize.
    pyglet's PygletDevice.device_value_changed then raises KeyError, ctypes
    catches it but spams a traceback to stderr on every report. The unmapped
    element doesn't matter — every standard button/stick still works — so we
    patch the callback to swallow KeyError silently.
    """
    try:
        from pyglet.input.macos.darwin_hid import PygletDevice
    except Exception:
        return
    if getattr(PygletDevice, "_skywing_keyerror_patched", False):
        return
    original = PygletDevice.device_value_changed
    def safe_device_value_changed(self, hid_device, hid_value):
        try:
            original(self, hid_device, hid_value)
        except KeyError:
            pass
    PygletDevice.device_value_changed = safe_device_value_changed
    PygletDevice._skywing_keyerror_patched = True


def _setup_gamepad(window):
    """ Attach gamepad event handlers to `window` if a controller is connected.

    Routes button/stick events to the currently-active view via its
    `on_button_press` / `on_button_release` / `on_stick_motion` methods so each
    view defines its own gamepad → action mapping. If no controller is found
    (or pyglet can't open one) the function returns silently and the game
    falls back to keyboard-only input.
    """
    _silence_macos_hid_keyerror()
    try:
        controllers = pyglet.input.get_controllers()
    except Exception:
        return None
    if not controllers:
        return None
    controller = controllers[0]
    try:
        controller.open()
    except Exception:
        return None

    @controller.event
    def on_button_press(controller_, button):
        view = window.current_view
        if view is not None and hasattr(view, "on_button_press"):
            view.on_button_press(button)

    @controller.event
    def on_button_release(controller_, button):
        view = window.current_view
        if view is not None and hasattr(view, "on_button_release"):
            view.on_button_release(button)

    @controller.event
    def on_stick_motion(controller_, stick, vector):
        if stick != "leftstick":
            return
        view = window.current_view
        if view is not None and hasattr(view, "on_stick_motion"):
            view.on_stick_motion(vector.x, vector.y)

    # Keep a reference so the controller isn't garbage-collected.
    window._gamepad = controller
    return controller


class SkywingWindow(arcade.Window):
    """ The game's arcade.Window subclass. Holds the global game state
    (score store, asset library, gamepad) as typed attributes so views can
    access them via ``self.window.score_store`` / ``self.window.assets``
    without duck-typing surprises.
    """

    score_store: ScoreStore
    assets: AssetLibrary

    def __init__(self, score_store: ScoreStore):
        super().__init__(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
        self.background_color = arcade.color.SKY_BLUE
        self.score_store = score_store
        # Load assets AFTER super().__init__ so the GL context is ready.
        self.assets = AssetLibrary(ASSET_DIR)


def main():
    """ Main method """
    score_store = ScoreStore.load(SCORES_PATH)
    window = SkywingWindow(score_store)
    _setup_gamepad(window)
    window.show_view(TitleView())
    arcade.run()


if __name__ == "__main__":
    main()