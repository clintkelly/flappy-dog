"""
Skywing Ruins — a tiny Flappy-Bird-style game.

"""


from pathlib import Path
import math

import arcade
import random

from score_store import DEFAULT_PROFILE, ScoreStore

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
# shrink toward these ratios as the score climbs to DIFFICULTY_RAMP_SCORE.
# Lower DIFFICULTY_RAMP_SCORE = harder faster.
# Lower *_AT_MAX_DIFFICULTY = harder peak (e.g. 0.50 means tightens to 50% of base).
DIFFICULTY_RAMP_SCORE = 30
GAP_RATIO_AT_MAX_DIFFICULTY = 0.65
SPACING_RATIO_AT_MAX_DIFFICULTY = 0.75

PLAYER_ANIMATION_FRAME_DURATION = 0.05  # seconds per frame
ASSET_DIR = Path(__file__).parent / "assets"
SCORES_PATH = Path(__file__).parent / "scores.json"

MAX_PROFILE_NAME_LENGTH = 12

COLUMN_TILE_SIZE = 64  # native pixels per side
COLUMN_TILE_SCALE = 3
COLUMN_TILE_RENDERED = COLUMN_TILE_SIZE * COLUMN_TILE_SCALE
COLUMN_TILE_VERTICAL_OVERLAP = 6  # rendered pixels of overlap at tile seams

# Cloud parallax layer.
# All four visual properties are interpolated from depth=0 (near) to depth=1 (far).
# Far clouds drift slowly, are smaller, more transparent, and tinted toward the sky.
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

# Weather cycle timings (seconds). Tuned so a typical 30-90 second run sees at
# least one full storm cycle.
STORM_INTERVAL_MIN = 5.0            # delay before first storm + between storms
STORM_INTERVAL_MAX = 18.0
STORM_DURATION_MIN = 30.0
STORM_DURATION_MAX = 60.0
STORM_ONSET_FLASH_DELAY = 0.6       # flash → thunder
STORM_ONSET_RAIN_DELAY = 1.4        # thunder → rain begins

# Lightning + thunder
LIGHTNING_FLASH_ALPHA = 230
LIGHTNING_FLASH_DURATION = 0.25     # seconds for full-screen flash to fade to 0
LIGHTNING_INTERVAL_MIN = 4.0        # seconds between lightning events during a storm
LIGHTNING_INTERVAL_MAX = 9.0
LIGHTNING_FIRST_DELAY_MIN = 2.0     # delay before the first in-storm lightning
LIGHTNING_FIRST_DELAY_MAX = 4.5
THUNDER_DELAY_MIN = 0.4             # delay between flash and the thunder clap
THUNDER_DELAY_MAX = 1.1
THUNDER_VOLUME = 0.8

# Collectible coins placed in a row between obstacle spawns.
COIN_SCALE = 1.5                   # 64 native -> 96 rendered
COIN_ANIMATION_FRAME_DURATION = 0.06
COINS_PER_CLUSTER = 3
COIN_CLUSTER_SPACING_X = 110       # pixels between coin centers in a cluster
COIN_Y_MIN = 200
COIN_Y_MAX = WINDOW_HEIGHT - 200
COIN_POINTS = 1
COIN_PARTICLES_PER_BURST = 8


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


class WeatherController:
    """ State machine cycling clear ↔ storm with lightning + thunder events.

    States:
        CLEAR      no rain, no flashes; waiting for the next storm to roll in
        ONSET      lightning flash → thunder → rain starts (transition into storm)
        STORM      rain falling + periodic lightning/thunder pairs
    """

    CLEAR = "clear"
    ONSET = "onset"
    STORM = "storm"

    def __init__(self, rain_sound=None, thunder_sound=None):
        self.rain = RainSystem()
        self.rain_sound = rain_sound
        self.thunder_sound = thunder_sound
        self.rain_player = None

        self.state = self.CLEAR
        self.time_until_next_storm = random.uniform(STORM_INTERVAL_MIN, STORM_INTERVAL_MAX)
        self.storm_time_left = 0.0

        # ONSET sub-stage timers: 0=flash phase, 1=post-thunder wait, 2=transition to STORM.
        self.onset_stage = 0
        self.onset_timer = 0.0

        # During STORM, time until next lightning event.
        self.time_until_lightning = 0.0
        # Delayed thunder fires this many seconds after its flash.
        self.pending_thunder_in = None

        # Flash overlay state.
        self.flash_alpha = 0.0
        self.flash_decay_per_second = LIGHTNING_FLASH_ALPHA / LIGHTNING_FLASH_DURATION

    # ----- lifecycle -----

    def shutdown(self):
        """ Stop the rain loop. Call from on_hide_view. """
        if self.rain_player is not None:
            arcade.stop_sound(self.rain_player)
            self.rain_player = None

    def update(self, delta_time):
        # Flash always decays regardless of state.
        if self.flash_alpha > 0:
            self.flash_alpha = max(0.0, self.flash_alpha - self.flash_decay_per_second * delta_time)

        # Delayed thunder fires regardless of state — it was scheduled at flash time.
        if self.pending_thunder_in is not None:
            self.pending_thunder_in -= delta_time
            if self.pending_thunder_in <= 0:
                if self.thunder_sound:
                    arcade.play_sound(self.thunder_sound, volume=THUNDER_VOLUME)
                self.pending_thunder_in = None

        if self.state == self.CLEAR:
            self.time_until_next_storm -= delta_time
            if self.time_until_next_storm <= 0:
                self._begin_onset()
        elif self.state == self.ONSET:
            self._update_onset(delta_time)
        elif self.state == self.STORM:
            self.rain.update(delta_time)
            self.storm_time_left -= delta_time
            self.time_until_lightning -= delta_time
            if self.time_until_lightning <= 0:
                self._trigger_lightning()
            if self.storm_time_left <= 0:
                self._end_storm()

    def draw(self):
        # Rain is only visible once the storm is fully underway — during ONSET
        # we're still in the flash/thunder pre-roll and rain hasn't begun yet.
        if self.state == self.STORM:
            self.rain.draw()
        if self.flash_alpha > 0:
            arcade.draw_lbwh_rectangle_filled(
                0, 0, WINDOW_WIDTH, WINDOW_HEIGHT,
                (255, 255, 255, int(self.flash_alpha)),
            )

    # ----- transitions -----

    def _begin_onset(self):
        self.state = self.ONSET
        self.onset_stage = 0
        self.onset_timer = 0.0
        self.rain.reset_above_screen()
        self._flash()
        # Schedule thunder some time after the flash.
        self.pending_thunder_in = STORM_ONSET_FLASH_DELAY

    def _update_onset(self, delta_time):
        self.onset_timer += delta_time
        if self.onset_stage == 0 and self.onset_timer >= STORM_ONSET_FLASH_DELAY:
            self.onset_stage = 1
            self.onset_timer = 0.0
        elif self.onset_stage == 1 and self.onset_timer >= STORM_ONSET_RAIN_DELAY:
            # Transition into the steady storm — start rain sound and visuals.
            self.onset_stage = 2
            self.state = self.STORM
            self.storm_time_left = random.uniform(STORM_DURATION_MIN, STORM_DURATION_MAX)
            # The *first* in-storm lightning fires sooner so the player sees the
            # periodic cadence right away rather than waiting for the long
            # randomized interval.
            self.time_until_lightning = random.uniform(LIGHTNING_FIRST_DELAY_MIN, LIGHTNING_FIRST_DELAY_MAX)
            self._start_rain_loop()

    def _end_storm(self):
        self.state = self.CLEAR
        self.time_until_next_storm = random.uniform(STORM_INTERVAL_MIN, STORM_INTERVAL_MAX)
        if self.rain_player is not None:
            arcade.stop_sound(self.rain_player)
            self.rain_player = None

    def _trigger_lightning(self):
        self._flash()
        if self.thunder_sound:
            self.pending_thunder_in = random.uniform(THUNDER_DELAY_MIN, THUNDER_DELAY_MAX)
        self.time_until_lightning = random.uniform(LIGHTNING_INTERVAL_MIN, LIGHTNING_INTERVAL_MAX)

    def _flash(self):
        self.flash_alpha = float(LIGHTNING_FLASH_ALPHA)

    def _start_rain_loop(self):
        if self.rain_sound is not None and self.rain_player is None:
            self.rain_player = arcade.play_sound(
                self.rain_sound, volume=RAIN_SOUND_VOLUME, loop=True,
            )


class TitleView(arcade.View):
    """ Title screen shown at startup and after R from game-over. """

    def __init__(self):
        super().__init__()
        self.title_image = arcade.Sprite(
            arcade.load_texture(ASSET_DIR / "title.png"),
            scale=3,
        )
        self.title_image.center_x = WINDOW_WIDTH // 2
        self.title_image.center_y = WINDOW_HEIGHT // 2

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
            "Press SPACE to start  •  Press Q to quit",
            x=WINDOW_WIDTH // 2,
            y=64,
            color=arcade.color.YELLOW,
            font_size=22,
            anchor_x="center",
            anchor_y="center",
        )
        self.controls_text = arcade.Text(
            "SPACE flap   •   LEFT/RIGHT drift   •   P pause   •   N profile   •   H high scores",
            x=WINDOW_WIDTH // 2,
            y=28,
            color=arcade.color.WHITE,
            font_size=16,
            anchor_x="center",
            anchor_y="center",
        )

    def on_show_view(self):
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
            "[↑↓] navigate   •   [Enter] select   •   [N] new   •   [Esc] cancel",
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
            "Press Esc to return",
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


class GameView(arcade.View):
    """
    Main gameplay screen.
    """

    def __init__(self):
        super().__init__()

        # Will eventually have all of the sprites
        self.scene = None

        self.player_textures = [
            arcade.load_texture(path)
            for path in sorted(ASSET_DIR.glob("bird_*.png"))
        ]

        # Column tiles use detailed hit boxes so collision tracks the visible art,
        # not the transparent padding around it.
        self.column_ceiling_cap_textures = [
            arcade.load_texture(p, hit_box_algorithm=arcade.hitbox.algo_detailed)
            for p in sorted(ASSET_DIR.glob("column_ceiling_cap_*.png"))
        ]
        self.column_floor_cap_textures = [
            arcade.load_texture(p, hit_box_algorithm=arcade.hitbox.algo_detailed)
            for p in sorted(ASSET_DIR.glob("column_floor_cap_*.png"))
        ]
        self.column_mid_textures = [
            arcade.load_texture(p, hit_box_algorithm=arcade.hitbox.algo_detailed)
            for p in sorted(ASSET_DIR.glob("column_mid_*.png"))
        ]

        self.boulder_textures = [
            arcade.load_texture(p, hit_box_algorithm=arcade.hitbox.algo_detailed)
            for p in sorted(ASSET_DIR.glob("boulder*.png"))
        ]

        # Rings are named ring1.png .. ring16.png — sort numerically so the spin animates smoothly.
        ring_paths = sorted(
            ASSET_DIR.glob("ring*.png"),
            key=lambda p: int(p.stem.replace("ring", "")),
        )
        self.ring_textures = [arcade.load_texture(p) for p in ring_paths]

        # Coins ship as the first half of a rotation (face -> side); the second half is
        # built by horizontally flipping the frames in reverse so the spin loops smoothly.
        coin_paths = sorted(
            ASSET_DIR.glob("coin*.png"),
            key=lambda p: int(p.stem.replace("coin", "")),
        )
        forward = [arcade.load_texture(p) for p in coin_paths]
        backward = [t.flip_left_right() for t in reversed(forward[:-1])]
        self.coin_textures = forward + backward

        self.cloud_textures = [
            arcade.load_texture(p)
            for p in sorted(ASSET_DIR.glob("cloud*.png"))
        ]

        self.mountain_texture = arcade.load_texture(ASSET_DIR / "mountain.png")

        # Static sky background. Native 320x180 scaled 4x to fill the 1280x720 window.
        self.sky_sprite = arcade.Sprite(
            arcade.load_texture(ASSET_DIR / "sky.png"),
            scale=4,
        )
        self.sky_sprite.center_x = WINDOW_WIDTH // 2
        self.sky_sprite.center_y = WINDOW_HEIGHT // 2

        self.jump_sound = arcade.load_sound(":resources:sounds/jump1.wav")
        self.gameover_sound = arcade.load_sound(":resources:sounds/gameover1.wav")
        self.coin_sound = arcade.load_sound(":resources:sounds/coin1.wav")
        self.ring_sound = arcade.load_sound(":resources:sounds/upgrade1.wav")

        # Weather: rain + thunderstorm cycle. Both sound files are optional;
        # drop assets/rain.{wav,ogg,mp3} and/or assets/thunder.{wav,ogg,mp3}
        # into the assets dir to enable them. Visuals come up either way.
        def _load_optional(stem):
            for ext in ("wav", "ogg", "mp3"):
                hits = list(ASSET_DIR.glob(f"{stem}.{ext}"))
                if hits:
                    return arcade.load_sound(hits[0])
            return None

        self.weather = WeatherController(
            rain_sound=_load_optional("rain"),
            thunder_sound=_load_optional("thunder"),
        )

        self.gui_camera = None
        self.score = 0
        self.score_text = None
        self.is_game_over = False
        self.moving_horizontally = False

        self.setup()


    def setup(self):
        """ Called whenever the game starts / resets """
        
        self.scene = arcade.Scene()
        self.is_game_over = False

        self.animation_frame = 0
        self.animation_time = 0.0
        self.ring_animation_frame = 0
        self.ring_animation_time = 0.0
        self.coin_animation_frame = 0
        self.coin_animation_time = 0.0
        self.ring_combo = 0

        self.gui_camera = arcade.Camera2D()

        self.score = 0
        self.is_paused = False
        self.score_text = arcade.Text(f"Score: {self.score}", x=10, y=WINDOW_HEIGHT - 20, color=arcade.color.WHITE, font_size=14)
        self.paused_text = arcade.Text(
            "PAUSED",
            x=WINDOW_WIDTH - 10,
            y=WINDOW_HEIGHT - 20,
            color=arcade.color.YELLOW,
            font_size=14,
            anchor_x="right",
        )
        self.game_over_text = arcade.Text(
            "GAME OVER",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2,
            color=arcade.color.RED,
            font_size=48,
            anchor_x="center",
            anchor_y="center",
            multiline=True,
            width=WINDOW_WIDTH,
            align="center",
        )

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
        self.scene.add_sprite_list("Rings")
        self.scene.add_sprite_list("Coins")
        self.scene.add_sprite_list("ScoreZones")
        self.scene.add_sprite_list("Particles")
        self.floating_texts = []

        self.player_sprite.change_y = 0
        self.moving_horizontally = False

        self.next_pipe_spacing = random.randint(MIN_PIPE_SPACING, MAX_PIPE_SPACING)


    def on_key_press(self, key, modifiers):
        """ Called whenever a key is pressed. """
        if self.is_game_over:
            # Deliberately ignore SPACE here — players are usually still flapping
            # when they die and would otherwise blow past the game-over screen.
            if key == arcade.key.ENTER or key == arcade.key.RETURN:
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
            return

        self.player_sprite.change_y -= GRAVITY
        self.player_sprite.center_y += self.player_sprite.change_y
        self.player_sprite.center_x += self.player_sprite.change_x

        # Clamp at the top of the screen — flying off the top no longer kills.
        if self.player_sprite.top > WINDOW_HEIGHT:
            self.player_sprite.top = WINDOW_HEIGHT
            self.player_sprite.change_y = 0

        # Cycle through the animation frames
        self.animation_time += delta_time
        if self.animation_time >= PLAYER_ANIMATION_FRAME_DURATION:
            self.animation_time -= PLAYER_ANIMATION_FRAME_DURATION
            self.animation_frame = (self.animation_frame + 1) % len(self.player_textures)
            self.player_sprite.texture = self.player_textures[self.animation_frame]
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
        self.move_rings(delta_time)
        self.move_coins(delta_time)
        self.update_particles(delta_time)
        self.update_floating_texts(delta_time)

        # Spawn new pipes
        self.spawn_pipes()

        # Drift mountains and clouds for parallax depth
        self.move_mountains()
        self.move_clouds()

        # Collision detection — pipes or boulders both kill the bird
        if arcade.check_for_collision_with_list(
            self.player_sprite, self.scene["Pipes"]
        ) or arcade.check_for_collision_with_list(
            self.player_sprite, self.scene["Boulders"]
        ):
            self.game_over()

        score_zone_hits = arcade.check_for_collision_with_list(
            self.player_sprite,
            self.scene["ScoreZones"],
        )

        for score_zone in score_zone_hits:
            score_zone.remove_from_sprite_lists()
            self.score += 1
            self.score_text.text = f"Score: {self.score}"
            arcade.play_sound(self.coin_sound)
            # Spawn the floating text at the bird so it's visible regardless of
            # the score zone's height (boulder zones span the whole window).
            self.spawn_floating_text(
                self.player_sprite.center_x,
                self.player_sprite.center_y,
                "+1",
            )

        ring_hits = arcade.check_for_collision_with_list(
            self.player_sprite,
            self.scene["Rings"],
        )
        for ring in ring_hits:
            self.spawn_burst(ring.center_x, ring.center_y)
            self.ring_combo += 1
            bonus = RING_POINTS + (self.ring_combo - 1) * RING_COMBO_BONUS_STEP
            self.score += bonus
            self.score_text.text = f"Score: {self.score}"
            self.spawn_floating_text(ring.center_x, ring.center_y, f"+{bonus}")
            pitch = min(1.0 + (self.ring_combo - 1) * RING_PITCH_STEP, RING_PITCH_MAX)
            arcade.play_sound(self.ring_sound, speed=pitch)
            ring.remove_from_sprite_lists()

        coin_hits = arcade.check_for_collision_with_list(
            self.player_sprite,
            self.scene["Coins"],
        )
        for coin in coin_hits:
            self.spawn_burst(coin.center_x, coin.center_y, count=COIN_PARTICLES_PER_BURST)
            self.score += COIN_POINTS
            self.score_text.text = f"Score: {self.score}"
            self.spawn_floating_text(coin.center_x, coin.center_y, f"+{COIN_POINTS}")
            arcade.play_sound(self.coin_sound)
            coin.remove_from_sprite_lists()

        if self.player_sprite.bottom < 0:
            self.game_over()

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
        is_new_record = self.score > previous_best and self.score > 0
        best_line = f"Personal best: {new_best}"
        if is_new_record:
            best_line += "  ★ NEW!"

        self.game_over_text.text = (
            f"GAME OVER\n"
            f"Final score: {self.score}\n"
            f"{best_line}\n"
            f"Press ENTER to play again\n"
            f"Press R for title\n"
            f"Press Q to quit"
        )
        arcade.play_sound(self.gameover_sound)


    def should_generate_new_pipe(self):
        # Look at the rightmost sprite across all spawnable slots so spacing is
        # consistent regardless of which kind was spawned last.
        last_x = -float("inf")
        for list_name in ("Pipes", "Boulders", "Rings"):
            sprites = self.scene.get_sprite_list(list_name)
            if sprites:
                last_x = max(last_x, sprites[-1].center_x)
        if last_x == -float("inf"):
            return True
        return last_x < WINDOW_WIDTH - self.next_pipe_spacing

    def make_top_column(self, center_x, gap_top, extend_for_oscillation=0):
        """ Column hanging from the ceiling. Cap sits flush above the gap; mid tiles stack upward.
        extend_for_oscillation pads the column past the screen edge so it still covers when the
        gap slides downward. """
        tiles = []

        cap = arcade.Sprite(
            random.choice(self.column_ceiling_cap_textures),
            scale=COLUMN_TILE_SCALE,
        )
        cap.center_x = center_x
        cap.center_y = gap_top + COLUMN_TILE_RENDERED // 2
        tiles.append(cap)

        # Stack mid tiles above the cap until the column extends past the top of the screen.
        # Each tile overlaps the one below by COLUMN_TILE_VERTICAL_OVERLAP to hide art seams.
        target_top = WINDOW_HEIGHT + extend_for_oscillation
        next_bottom = cap.top - COLUMN_TILE_VERTICAL_OVERLAP
        while next_bottom < target_top:
            mid = arcade.Sprite(
                random.choice(self.column_mid_textures),
                scale=COLUMN_TILE_SCALE,
            )
            mid.center_x = center_x
            mid.center_y = next_bottom + COLUMN_TILE_RENDERED // 2
            tiles.append(mid)
            next_bottom = mid.top - COLUMN_TILE_VERTICAL_OVERLAP

        return tiles

    def make_bottom_column(self, center_x, gap_bottom, extend_for_oscillation=0):
        """ Column rising from the floor. Cap sits flush below the gap; mid tiles stack downward.
        extend_for_oscillation pads past the bottom of the screen for oscillating gaps. """
        tiles = []

        cap = arcade.Sprite(
            random.choice(self.column_floor_cap_textures),
            scale=COLUMN_TILE_SCALE,
        )
        cap.center_x = center_x
        cap.center_y = gap_bottom - COLUMN_TILE_RENDERED // 2
        tiles.append(cap)

        target_bottom = -extend_for_oscillation
        next_top = cap.bottom + COLUMN_TILE_VERTICAL_OVERLAP
        while next_top > target_bottom:
            mid = arcade.Sprite(
                random.choice(self.column_mid_textures),
                scale=COLUMN_TILE_SCALE,
            )
            mid.center_x = center_x
            mid.center_y = next_top - COLUMN_TILE_RENDERED // 2
            tiles.append(mid)
            next_top = mid.bottom + COLUMN_TILE_VERTICAL_OVERLAP

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

        # Difficulty factor: 0 at score 0, 1 once score >= DIFFICULTY_RAMP_SCORE.
        t = min(self.score / DIFFICULTY_RAMP_SCORE, 1.0) if DIFFICULTY_RAMP_SCORE > 0 else 1.0
        spacing_factor = 1.0 + (SPACING_RATIO_AT_MAX_DIFFICULTY - 1.0) * t

        # Spawn just off the right edge of the screen
        column_x = WINDOW_WIDTH + COLUMN_TILE_RENDERED // 2

        # Single roll picks ring / boulder / column-pair so probabilities don't compound.
        roll = random.random()
        if roll < RING_OBSTACLE_CHANCE:
            # Bonus ring spawn (non-fatal pickup).
            self.scene.add_sprite("Rings", self.make_ring(column_x))
        elif roll < RING_OBSTACLE_CHANCE + BOULDER_OBSTACLE_CHANCE:
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
            self.scene.add_sprite("ScoreZones", score_zone)
            # Risk-reward: a static bonus ring near the floor, tempting the player to
            # fly *under* the boulder instead of over it.
            self.scene.add_sprite("Rings", self.make_bonus_ring(column_x))
        else:
            # Column pair (static or oscillating). Difficulty scaling applies in both cases.
            gap_factor = 1.0 + (GAP_RATIO_AT_MAX_DIFFICULTY - 1.0) * t
            gap_size = random.randint(
                int(MIN_PIPE_CENTER_GAP * gap_factor),
                int(MAX_PIPE_CENTER_GAP * gap_factor),
            )

            oscillating = random.random() < OSCILLATING_PIPE_CHANCE
            if oscillating:
                # Keep the gap center far enough from screen edges that the oscillation never
                # pushes it off-screen.
                gap_center = random.randint(
                    MIN_PIPE_CENTER_GAP_Y + PIPE_AMPLITUDE_MAX,
                    MAX_PIPE_CENTER_GAP_Y - PIPE_AMPLITUDE_MAX,
                )
                amplitude = random.randint(PIPE_AMPLITUDE_MIN, PIPE_AMPLITUDE_MAX)
                phase = random.uniform(0, 2 * math.pi)
                phase_speed = random.uniform(PIPE_PHASE_SPEED_MIN, PIPE_PHASE_SPEED_MAX)
                extend = PIPE_AMPLITUDE_MAX
            else:
                gap_center = random.randint(MIN_PIPE_CENTER_GAP_Y, MAX_PIPE_CENTER_GAP_Y)
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
            if oscillating:
                # Attach oscillation attrs to every tile and the score zone so they move as one.
                initial_offset = amplitude * math.sin(phase)
                for sprite in sprites:
                    sprite.base_y = sprite.center_y
                    sprite.amplitude = amplitude
                    sprite.phase = phase
                    sprite.phase_speed = phase_speed
                    sprite.center_y = sprite.base_y + initial_offset

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
        for sprite_list_name in ("Pipes", "ScoreZones"):
            for pipe in self.scene.get_sprite_list(sprite_list_name):
                pipe.center_x -= PIPE_SPEED
                # Oscillating pipes carry phase/amplitude/base_y attrs set in spawn_pipes.
                if hasattr(pipe, "phase_speed") and pipe.phase_speed:
                    pipe.phase += pipe.phase_speed * delta_time
                    pipe.center_y = pipe.base_y + pipe.amplitude * math.sin(pipe.phase)
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
        boulder.base_y = random.randint(base_y_min, BOULDER_BASE_Y_MAX)
        boulder.amplitude = amplitude
        boulder.phase = random.uniform(0, 2 * math.pi)
        boulder.phase_speed = random.uniform(BOULDER_PHASE_SPEED_MIN, BOULDER_PHASE_SPEED_MAX)
        boulder.center_y = boulder.base_y + boulder.amplitude * math.sin(boulder.phase)
        return boulder

    def move_boulders(self, delta_time):
        for boulder in self.scene.get_sprite_list("Boulders"):
            boulder.center_x -= PIPE_SPEED
            boulder.phase += boulder.phase_speed * delta_time
            boulder.center_y = boulder.base_y + boulder.amplitude * math.sin(boulder.phase)
            if boulder.right < 0:
                boulder.remove_from_sprite_lists()

    def make_ring(self, x):
        ring = arcade.Sprite(self.ring_textures[0], scale=RING_SCALE)
        ring.center_x = x
        ring.base_y = random.randint(RING_BASE_Y_MIN, RING_BASE_Y_MAX)
        ring.amplitude = random.randint(RING_AMPLITUDE_MIN, RING_AMPLITUDE_MAX)
        ring.phase = random.uniform(0, 2 * math.pi)
        ring.phase_speed = random.uniform(RING_PHASE_SPEED_MIN, RING_PHASE_SPEED_MAX)
        ring.center_y = ring.base_y + ring.amplitude * math.sin(ring.phase)
        return ring

    def make_bonus_ring(self, x):
        """ Static low-altitude ring used as a risk-reward pickup under boulders. """
        ring = arcade.Sprite(self.ring_textures[0], scale=RING_SCALE)
        ring.center_x = x
        ring.center_y = random.randint(BONUS_RING_Y_MIN, BONUS_RING_Y_MAX)
        ring.base_y = ring.center_y
        ring.amplitude = 0
        ring.phase = 0
        ring.phase_speed = 0
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
        self.floating_texts.append(text)

    def update_floating_texts(self, delta_time):
        for text in self.floating_texts[:]:
            text.y += FLOATING_TEXT_RISE_SPEED
            text.lifetime -= delta_time
            if text.lifetime <= 0:
                self.floating_texts.remove(text)
            else:
                progress = 1.0 - (text.lifetime / FLOATING_TEXT_LIFETIME)
                text.font_size = lerp(FLOATING_TEXT_START_SIZE, FLOATING_TEXT_END_SIZE, progress)
                alpha = int(255 * (text.lifetime / FLOATING_TEXT_LIFETIME))
                text.color = (*text.base_rgb, alpha)

    def move_rings(self, delta_time):
        # Advance the shared spin animation once per frame.
        self.ring_animation_time += delta_time
        if self.ring_animation_time >= RING_ANIMATION_FRAME_DURATION:
            self.ring_animation_time -= RING_ANIMATION_FRAME_DURATION
            self.ring_animation_frame = (self.ring_animation_frame + 1) % len(self.ring_textures)
        current_texture = self.ring_textures[self.ring_animation_frame]

        for ring in self.scene.get_sprite_list("Rings"):
            ring.center_x -= PIPE_SPEED
            ring.phase += ring.phase_speed * delta_time
            ring.center_y = ring.base_y + ring.amplitude * math.sin(ring.phase)
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

    def move_coins(self, delta_time):
        # Shared spin animation, like rings — every coin shows the same frame.
        self.coin_animation_time += delta_time
        if self.coin_animation_time >= COIN_ANIMATION_FRAME_DURATION:
            self.coin_animation_time -= COIN_ANIMATION_FRAME_DURATION
            self.coin_animation_frame = (self.coin_animation_frame + 1) % len(self.coin_textures)
        current_texture = self.coin_textures[self.coin_animation_frame]

        for coin in self.scene.get_sprite_list("Coins"):
            coin.center_x -= PIPE_SPEED
            coin.texture = current_texture
            if coin.right < 0:
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
            self.game_over_text.draw()


def main():
    """ Main method """
    score_store = ScoreStore.load(SCORES_PATH)
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    window.background_color = arcade.color.SKY_BLUE
    window.score_store = score_store
    window.show_view(TitleView())
    arcade.run()


if __name__ == "__main__":
    main()