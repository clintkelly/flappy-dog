"""
Skywing Ruins — a tiny Flappy-Bird-style game.

"""


from pathlib import Path
import math

import arcade
import random

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

# Floating "+N" text shown when a ring is collected.
FLOATING_TEXT_LIFETIME = 1.0       # seconds
FLOATING_TEXT_RISE_SPEED = 1.5     # pixels per frame


def lerp(a, b, t):
    return a + (b - a) * t


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
            "SPACE flap   •   LEFT/RIGHT drift   •   P pause",
            x=WINDOW_WIDTH // 2,
            y=28,
            color=arcade.color.WHITE,
            font_size=16,
            anchor_x="center",
            anchor_y="center",
        )

    def on_draw(self):
        self.clear()
        arcade.draw_sprite(self.title_image)
        self.title_text.draw()
        self.prompt_text.draw()
        self.controls_text.draw()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.SPACE:
            self.window.show_view(GameView())
        elif key == arcade.key.Q:
            self.window.close()


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
        self.scene.add_sprite_list("ScoreZones")
        self.scene.add_sprite_list("Particles")
        self.floating_texts = []

        self.player_sprite.change_y = 0
        self.moving_horizontally = False

        self.next_pipe_spacing = random.randint(MIN_PIPE_SPACING, MAX_PIPE_SPACING)


    def on_key_press(self, key, modifiers):
        """ Called whenever a key is pressed. """
        if self.is_game_over:
            if key == arcade.key.SPACE:
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


    def on_update(self, delta_time):
        """ Movement and game logic """
        if self.is_game_over or self.is_paused:
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

        ring_hits = arcade.check_for_collision_with_list(
            self.player_sprite,
            self.scene["Rings"],
        )
        for ring in ring_hits:
            self.spawn_ring_burst(ring.center_x, ring.center_y)
            self.ring_combo += 1
            bonus = RING_POINTS + (self.ring_combo - 1) * RING_COMBO_BONUS_STEP
            self.score += bonus
            self.score_text.text = f"Score: {self.score}"
            self.spawn_floating_text(ring.center_x, ring.center_y, f"+{bonus}")
            pitch = min(1.0 + (self.ring_combo - 1) * RING_PITCH_STEP, RING_PITCH_MAX)
            arcade.play_sound(self.ring_sound, speed=pitch)
            ring.remove_from_sprite_lists()

        if self.player_sprite.bottom < 0:
            self.game_over()

    def game_over(self):
        self.is_game_over = True
        self.game_over_text.text = (
            f"GAME OVER\n"
            f"Final score: {self.score}\n"
            f"Press SPACE to play again\n"
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
            # Use the existing spacing factor for the next spawn and bail.
            self.next_pipe_spacing = random.randint(
                int(MIN_PIPE_SPACING * spacing_factor),
                int(MAX_PIPE_SPACING * spacing_factor),
            )
            return

        if roll < RING_OBSTACLE_CHANCE + BOULDER_OBSTACLE_CHANCE:
            # Spawn a single oscillating boulder instead of a column pair.
            self.scene.add_sprite("Boulders", self.make_boulder(column_x))
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

    def make_boulder(self, x):
        boulder = arcade.Sprite(
            random.choice(self.boulder_textures),
            scale=BOULDER_SCALE,
        )
        boulder.center_x = x
        boulder.base_y = random.randint(BOULDER_BASE_Y_MIN, BOULDER_BASE_Y_MAX)
        boulder.amplitude = random.randint(BOULDER_AMPLITUDE_MIN, BOULDER_AMPLITUDE_MAX)
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

    def spawn_ring_burst(self, x, y):
        """ Spawn a starburst of small circles at the ring's collection point. """
        for _ in range(PARTICLES_PER_BURST):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(PARTICLE_SPEED_MIN, PARTICLE_SPEED_MAX)
            particle = arcade.SpriteCircle(
                radius=random.randint(PARTICLE_RADIUS_MIN, PARTICLE_RADIUS_MAX),
                color=random.choice(PARTICLE_COLORS),
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

    def spawn_floating_text(self, x, y, message, color=arcade.color.GOLD):
        text = arcade.Text(
            message,
            x=x,
            y=y,
            color=color,
            font_size=22,
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
        for text in self.floating_texts:
            text.draw()
        self.score_text.draw()
        if self.is_paused:
            self.paused_text.draw()
        if self.is_game_over:
            self.game_over_text.draw()


def main():
    """ Main method """
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    window.background_color = arcade.color.SKY_BLUE
    window.show_view(TitleView())
    arcade.run()


if __name__ == "__main__":
    main()