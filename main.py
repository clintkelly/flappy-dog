"""
Very trivial version of flappy bird, starring a dog!

"""


import arcade

# Constants
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Platformer"

GRAVITY = 0.6
FLAP_VELOCITY = 10



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

        # Create the player sprite
        self.player_sprite = arcade.Sprite(player_texture_right)
        #self.player_sprite.scale_x = abs(self.player_sprite.scale_x)   # face right
        self.player_sprite.center_x = 64
        self.player_sprite.center_y = WINDOW_HEIGHT // 2
        self.scene.add_sprite("Player", self.player_sprite)

        self.player_sprite.change_y = 0


    def on_key_press(self, key, modifiers):
        """ Called whenever a key is pressed. """
        if key == arcade.key.SPACE:
            self.player_sprite.change_y = FLAP_VELOCITY
            arcade.play_sound(self.jump_sound)


    def on_update(self, delta_time):
        """ Movement and game logic """
        if self.game_over:
            return

        self.player_sprite.change_y -= GRAVITY
        self.player_sprite.center_y += self.player_sprite.change_y

        if self.player_sprite.bottom < 0 or self.player_sprite.top > WINDOW_HEIGHT:
            self.game_over = True
            arcade.play_sound(self.gameover_sound)


    def on_draw(self):
        self.clear()
        self.gui_camera.use()
        self.scene.draw()
        self.score_text.draw()


def main():
    """ Main method """
    window = GameView()
    window.setup()
    arcade.run()


if __name__ == "__main__":
    main()