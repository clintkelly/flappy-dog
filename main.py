"""
Very trivial version of flappy bird, starring a dog!

"""


import arcade
import random

# Constants
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Platformer"

GRAVITY = 0.6
FLAP_VELOCITY = 10

PIPE_WIDTH = 100

PIPE_SPEED = 4
PIPE_CENTER_GAP = 250 # TODO: Make this random in a range

MIN_PIPE_CENTER_GAP_Y = 180
MAX_PIPE_CENTER_GAP_Y = WINDOW_HEIGHT - 180

PIPE_SPACING = 250 # TODO: Make this random in a range


class GameView(arcade.Window):
    """
    Main application code
    """

    def __init__(self):

        super().__init__(WINDOW_WIDTH, WINDOW_HEIGHT, WINDOW_TITLE)

        # Will eventually have all of the sprites
        self.scene = None

        self.player_texture = None

        self.jump_sound = arcade.load_sound(":resources:sounds/jump1.wav")
        self.gameover_sound = arcade.load_sound(":resources:sounds/gameover1.wav")

        self.gui_camera = None
        self.score = 0
        self.score_text = None
        self.game_over = False


    def setup(self):
        """ Called whenever the game starts / resets """
        
        self.scene = arcade.Scene()
        self.game_over = False

        player_texture_left = arcade.load_texture(":resources:images/enemies/bee.png")
        player_texture_right = player_texture_left.flip_left_right()

        self.gui_camera = arcade.Camera2D()

        self.score = 0
        self.score_text = arcade.Text(f"Score: {self.score}", x=10, y=WINDOW_HEIGHT - 20, color=arcade.color.WHITE, font_size=14)
        self.game_over_text = arcade.Text("GAME OVER", x=WINDOW_WIDTH // 2 - 50, y=WINDOW_HEIGHT - 20, color=arcade.color.RED, font_size=28)

        # Create the player sprite
        self.player_sprite = arcade.Sprite(player_texture_right)
        #self.player_sprite.scale_x = abs(self.player_sprite.scale_x)   # face right
        self.player_sprite.center_x = 64
        self.player_sprite.center_y = WINDOW_HEIGHT // 2
        self.scene.add_sprite("Player", self.player_sprite)
        self.scene.add_sprite_list("Pipes")

        self.player_sprite.change_y = 0


    def on_key_press(self, key, modifiers):
        """ Called whenever a key is pressed. """
        if key == arcade.key.SPACE:
            self.player_sprite.change_y = FLAP_VELOCITY
            arcade.play_sound(self.jump_sound)

        if key == arcade.key.R and self.game_over:
            self.setup()


    def on_update(self, delta_time):
        """ Movement and game logic """
        if self.game_over:
            return

        self.player_sprite.change_y -= GRAVITY
        self.player_sprite.center_y += self.player_sprite.change_y

        # Move and remove existing pipes
        self.move_and_remove_existing_pipes()


        # Spawn new pipes
        self.spawn_pipes()


        # Collision detection
        if arcade.check_for_collision_with_list(
            self.player_sprite, self.scene["Pipes"]
        ):

            self.game_over()
            arcade.play_sound(self.gameover_sound)
            self.reset_score = False
            self.setup()

        if self.player_sprite.bottom < 0 or self.player_sprite.top > WINDOW_HEIGHT:
            self.game_over()

    def game_over(self):
        self.game_over = True
        arcade.play_sound(self.gameover_sound)


    def should_generate_new_pipe(self):
        pipes = self.scene.get_sprite_list("Pipes")
        if len(pipes) == 0:
            return True
        last_pipe = pipes[-1]
        return last_pipe.center_x < WINDOW_WIDTH - PIPE_SPACING

    def make_top_pipe(self, gap_center):
        pipe = arcade.SpriteSolidColor(
            width=PIPE_WIDTH,
            height=WINDOW_HEIGHT - (gap_center + PIPE_CENTER_GAP // 2),
            color=arcade.color.GREEN,
        )
        pipe.center_x = WINDOW_WIDTH + PIPE_WIDTH // 2
        pipe.center_y = WINDOW_HEIGHT - (pipe.height // 2)
        return pipe


    def make_bottom_pipe(self, gap_center):
        pipe = arcade.SpriteSolidColor(
            width=PIPE_WIDTH,
            height=gap_center - PIPE_CENTER_GAP // 2,
            color=arcade.color.GREEN,
        )
        pipe.center_x = WINDOW_WIDTH + PIPE_WIDTH // 2
        pipe.center_y = pipe.height // 2
        return pipe

    def spawn_pipes(self):
        if not self.should_generate_new_pipe():
            return

        # Figure out the center of the gap
        gap_center = random.randint(MIN_PIPE_CENTER_GAP_Y, MAX_PIPE_CENTER_GAP_Y)

        top_pipe = self.make_top_pipe(gap_center)
        bottom_pipe = self.make_bottom_pipe(gap_center)

        self.scene.add_sprite("Pipes", top_pipe)
        self.scene.add_sprite("Pipes", bottom_pipe)



    def move_and_remove_existing_pipes(self):
        for pipe in self.scene.get_sprite_list("Pipes"):
            pipe.center_x -= PIPE_SPEED 
            if pipe.right < 0:
                pipe.remove_from_sprite_lists()


    def on_draw(self):
        self.clear()
        self.gui_camera.use()
        self.scene.draw()
        self.score_text.draw()
        if self.game_over:
            self.game_over_text.draw()


def main():
    """ Main method """
    window = GameView()
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()