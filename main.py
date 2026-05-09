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

PIPE_WIDTH = 120

PIPE_SPEED = 3

MIN_PIPE_CENTER_GAP = 220
MAX_PIPE_CENTER_GAP = 340

MIN_PIPE_CENTER_GAP_Y = 180
MAX_PIPE_CENTER_GAP_Y = WINDOW_HEIGHT - 180

MIN_PIPE_SPACING = 240
MAX_PIPE_SPACING = 360

PLAYER_ANIMATION_FRAME_DURATION = 0.05  # seconds per frame
ASSET_DIR = Path(__file__).parent / "assets"

COLUMN_TILE_SIZE = 64  # native pixels per side
COLUMN_TILE_SCALE = 3
COLUMN_TILE_RENDERED = COLUMN_TILE_SIZE * COLUMN_TILE_SCALE
COLUMN_TILE_VERTICAL_OVERLAP = 6  # rendered pixels of overlap at tile seams

# Cloud parallax layer
NUM_CLOUDS = 8
CLOUD_SPEED = 1.0  # slower than pipes for parallax depth
CLOUD_ALPHA = 130  # 0..255 — lower = hazier
CLOUD_MIN_SCALE = 1.5
CLOUD_MAX_SCALE = 3.0
CLOUD_Y_MIN = 200
CLOUD_Y_MAX = WINDOW_HEIGHT - 60


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
            y=32,
            color=arcade.color.YELLOW,
            font_size=22,
            anchor_x="center",
            anchor_y="center",
        )

    def on_draw(self):
        self.clear()
        arcade.draw_sprite(self.title_image)
        self.title_text.draw()
        self.prompt_text.draw()

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
        self.score_text = arcade.Text(f"Score: {self.score}", x=10, y=WINDOW_HEIGHT - 20, color=arcade.color.WHITE, font_size=14)
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

        # Clouds drawn first so they sit behind everything else.
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
        if key == arcade.key.SPACE:
            self.player_sprite.change_y = FLAP_VELOCITY
            arcade.play_sound(self.jump_sound)

        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.player_sprite.change_x = -PLAYER_X_SPEED
            self.moving_horizontally = True
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.player_sprite.change_x = PLAYER_X_SPEED
            self.moving_horizontally = True

        if key == arcade.key.R and self.is_game_over:
            self.window.show_view(TitleView())
        elif key == arcade.key.Q and self.is_game_over:
            self.window.close()

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
        if self.is_game_over:
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

        # Drift clouds for parallax
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
        """ Used only for scoring - invisible pipe in the gap that the player has to pass through """
        pipe = arcade.SpriteSolidColor(
            width=PIPE_WIDTH,
            height=gap_size,
            color=arcade.color.RED,
        )
        pipe.center_x = center_x
        pipe.center_y = gap_center
        pipe.visible = False
        return pipe



    def spawn_pipes(self):
        if not self.should_generate_new_pipe():
            return

        # Pick a fresh gap size and gap center for this pipe
        gap_size = random.randint(MIN_PIPE_CENTER_GAP, MAX_PIPE_CENTER_GAP)
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

        # Pick the spacing until the next pipe spawn
        self.next_pipe_spacing = random.randint(MIN_PIPE_SPACING, MAX_PIPE_SPACING)



    def move_and_remove_existing_pipes(self):
        for sprite_list_name in ("Pipes", "ScoreZones"):
            for pipe in self.scene.get_sprite_list(sprite_list_name):
                pipe.center_x -= PIPE_SPEED
                if pipe.right < 0:
                    pipe.remove_from_sprite_lists()

    def make_cloud(self, x):
        cloud = arcade.Sprite(
            random.choice(self.cloud_textures),
            scale=random.uniform(CLOUD_MIN_SCALE, CLOUD_MAX_SCALE),
        )
        cloud.center_x = x
        cloud.center_y = random.randint(CLOUD_Y_MIN, CLOUD_Y_MAX)
        cloud.alpha = CLOUD_ALPHA
        return cloud

    def move_clouds(self):
        """ Scroll clouds left; recycle off-screen clouds back to the right edge. """
        for cloud in self.scene.get_sprite_list("Clouds"):
            cloud.center_x -= CLOUD_SPEED
            if cloud.right < 0:
                cloud.texture = random.choice(self.cloud_textures)
                cloud.scale = random.uniform(CLOUD_MIN_SCALE, CLOUD_MAX_SCALE)
                cloud.center_x = WINDOW_WIDTH + cloud.width // 2
                cloud.center_y = random.randint(CLOUD_Y_MIN, CLOUD_Y_MAX)
                cloud.alpha = CLOUD_ALPHA


    def on_draw(self):
        self.clear()
        self.gui_camera.use()
        arcade.draw_sprite(self.sky_sprite)
        self.scene.draw()
        self.score_text.draw()
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