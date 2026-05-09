"""
Skywing Ruins — a tiny Flappy-Bird-style game.

"""


from pathlib import Path

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
        self.scene.add_sprite_list("ScoreZones")

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
        self.move_and_remove_existing_pipes()

        # Spawn new pipes
        self.spawn_pipes()

        # Drift mountains and clouds for parallax depth
        self.move_mountains()
        self.move_clouds()

        # Collision detection
        if arcade.check_for_collision_with_list(
            self.player_sprite, self.scene["Pipes"]
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

        if self.player_sprite.bottom < 0 or self.player_sprite.top > WINDOW_HEIGHT:
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
        pipes = self.scene.get_sprite_list("Pipes")
        if len(pipes) == 0:
            return True
        last_pipe = pipes[-1]
        return last_pipe.center_x < WINDOW_WIDTH - self.next_pipe_spacing

    def make_top_column(self, center_x, gap_top):
        """ Column hanging from the ceiling. Cap sits flush above the gap; mid tiles stack upward. """
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
        next_bottom = cap.top - COLUMN_TILE_VERTICAL_OVERLAP
        while next_bottom < WINDOW_HEIGHT:
            mid = arcade.Sprite(
                random.choice(self.column_mid_textures),
                scale=COLUMN_TILE_SCALE,
            )
            mid.center_x = center_x
            mid.center_y = next_bottom + COLUMN_TILE_RENDERED // 2
            tiles.append(mid)
            next_bottom = mid.top - COLUMN_TILE_VERTICAL_OVERLAP

        return tiles

    def make_bottom_column(self, center_x, gap_bottom):
        """ Column rising from the floor. Cap sits flush below the gap; mid tiles stack downward. """
        tiles = []

        cap = arcade.Sprite(
            random.choice(self.column_floor_cap_textures),
            scale=COLUMN_TILE_SCALE,
        )
        cap.center_x = center_x
        cap.center_y = gap_bottom - COLUMN_TILE_RENDERED // 2
        tiles.append(cap)

        next_top = cap.bottom + COLUMN_TILE_VERTICAL_OVERLAP
        while next_top > 0:
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
        gap_factor = 1.0 + (GAP_RATIO_AT_MAX_DIFFICULTY - 1.0) * t
        spacing_factor = 1.0 + (SPACING_RATIO_AT_MAX_DIFFICULTY - 1.0) * t

        # Pick a fresh gap size and gap center for this pipe (scaled by difficulty)
        gap_size = random.randint(
            int(MIN_PIPE_CENTER_GAP * gap_factor),
            int(MAX_PIPE_CENTER_GAP * gap_factor),
        )
        gap_center = random.randint(MIN_PIPE_CENTER_GAP_Y, MAX_PIPE_CENTER_GAP_Y)
        gap_top = gap_center + gap_size // 2
        gap_bottom = gap_center - gap_size // 2

        # Spawn just off the right edge of the screen
        column_x = WINDOW_WIDTH + COLUMN_TILE_RENDERED // 2

        top_tiles = self.make_top_column(column_x, gap_top)
        bottom_tiles = self.make_bottom_column(column_x, gap_bottom)
        middle_pipe = self.make_middle_pipe(column_x, gap_center, gap_size)

        for tile in top_tiles + bottom_tiles:
            self.scene.add_sprite("Pipes", tile)
        self.scene.add_sprite("ScoreZones", middle_pipe)

        # Pick the spacing until the next pipe spawn (also scaled by difficulty)
        self.next_pipe_spacing = random.randint(
            int(MIN_PIPE_SPACING * spacing_factor),
            int(MAX_PIPE_SPACING * spacing_factor),
        )



    def move_and_remove_existing_pipes(self):
        for sprite_list_name in ("Pipes", "ScoreZones"):
            for pipe in self.scene.get_sprite_list(sprite_list_name):
                pipe.center_x -= PIPE_SPEED
                if pipe.right < 0:
                    pipe.remove_from_sprite_lists()

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