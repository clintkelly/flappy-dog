"""
Very trivial version of flappy bird, starring a dog!

"""


import arcade
import random

# Constants
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Flappy Dog"

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


class TitleView(arcade.View):
    """ Title screen shown at startup and after R from game-over. """

    def __init__(self):
        super().__init__()
        self.title_text = arcade.Text(
            "FLAPPY DOG",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 + 60,
            color=arcade.color.YELLOW,
            font_size=72,
            anchor_x="center",
            anchor_y="center",
        )
        self.prompt_text = arcade.Text(
            "Press SPACE to start\nPress Q to quit",
            x=WINDOW_WIDTH // 2,
            y=WINDOW_HEIGHT // 2 - 60,
            color=arcade.color.WHITE,
            font_size=24,
            anchor_x="center",
            anchor_y="center",
            multiline=True,
            width=WINDOW_WIDTH,
            align="center",
        )

    def on_draw(self):
        self.clear()
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

        self.player_texture = None

        self.jump_sound = arcade.load_sound(":resources:sounds/jump1.wav")
        self.gameover_sound = arcade.load_sound(":resources:sounds/gameover1.wav")

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

        player_texture_left = arcade.load_texture(":resources:images/enemies/bee.png")
        player_texture_right = player_texture_left.flip_left_right()

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

        # Create the player sprite
        self.player_sprite = arcade.Sprite(player_texture_right)
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

    def make_top_pipe(self, gap_center, gap_size):
        pipe = arcade.SpriteSolidColor(
            width=PIPE_WIDTH,
            height=WINDOW_HEIGHT - (gap_center + gap_size // 2),
            color=arcade.color.GREEN,
        )
        pipe.center_x = WINDOW_WIDTH + PIPE_WIDTH // 2
        pipe.center_y = WINDOW_HEIGHT - (pipe.height // 2)
        return pipe


    def make_bottom_pipe(self, gap_center, gap_size):
        pipe = arcade.SpriteSolidColor(
            width=PIPE_WIDTH,
            height=gap_center - gap_size // 2,
            color=arcade.color.GREEN,
        )
        pipe.center_x = WINDOW_WIDTH + PIPE_WIDTH // 2
        pipe.center_y = pipe.height // 2
        return pipe

    def make_middle_pipe(self, gap_center, gap_size):
        """ Used only for scoring - invisible pipe in the gap that the player has to pass through """
        pipe = arcade.SpriteSolidColor(
            width=PIPE_WIDTH,
            height=gap_size,
            color=arcade.color.RED,
        )
        pipe.center_x = WINDOW_WIDTH + PIPE_WIDTH // 2
        pipe.center_y = gap_center
        pipe.visible = False
        return pipe



    def spawn_pipes(self):
        if not self.should_generate_new_pipe():
            return

        # Pick a fresh gap size and gap center for this pipe
        gap_size = random.randint(MIN_PIPE_CENTER_GAP, MAX_PIPE_CENTER_GAP)
        gap_center = random.randint(MIN_PIPE_CENTER_GAP_Y, MAX_PIPE_CENTER_GAP_Y)

        top_pipe = self.make_top_pipe(gap_center, gap_size)
        bottom_pipe = self.make_bottom_pipe(gap_center, gap_size)
        middle_pipe = self.make_middle_pipe(gap_center, gap_size)

        self.scene.add_sprite("Pipes", top_pipe)
        self.scene.add_sprite("Pipes", bottom_pipe)
        self.scene.add_sprite("ScoreZones", middle_pipe)

        # Pick the spacing until the next pipe spawn
        self.next_pipe_spacing = random.randint(MIN_PIPE_SPACING, MAX_PIPE_SPACING)



    def move_and_remove_existing_pipes(self):
        for sprite_list_name in ("Pipes", "ScoreZones"):
            for pipe in self.scene.get_sprite_list(sprite_list_name):
                pipe.center_x -= PIPE_SPEED 
                if pipe.right < 0:
                    pipe.remove_from_sprite_lists()


    def on_draw(self):
        self.clear()
        self.gui_camera.use()
        self.scene.draw()
        self.score_text.draw()
        if self.is_game_over:
            self.game_over_text.draw()


def main():
    """ Main method """
    window = arcade.Window(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)
    window.show_view(TitleView())
    arcade.run()


if __name__ == "__main__":
    main()