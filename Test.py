from time import time
import arcade, random
from Components import *
from arcade.gui import UIWidget, Surface, UIEvent, UILabel, UIAnchorWidget

import math
#1/60

class Menu(arcade.View):
    def __init__(self, texture, time_in_between, max_index):

        super().__init__()
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)

        # Reset the viewport, necessary if we have a scrolling game and we need
        # to reset the viewport back to the start so we can see what we draw.
        #arcade.set_viewport(0, self.window.width, 0, self.window.height)
        #self.textures = arcade.load_spritesheet(texture, 15, 25, 4, 16, margin=9)

        #self.textures = arcade.load_spritesheet(texture, 64, 64, 16, 16, margin=0)
        wood_button = CustomUIFlatButton({}, text="", width=140, height=50, scale=1, x=0, y=50, text_offset_x = 16, text_offset_y=35, offset_x=75, offset_y=25)
        silver_button = CustomUIFlatButton({}, text="", width=140, height=50, scale=1, x=0, y=50, text_offset_x = 16, text_offset_y=35, offset_x=75, offset_y=25, Texture="resources/gui/Silver Button.png")
        gold_button = CustomUIFlatButton({}, text="", width=140, height=50, scale=1, x=0, y=50, text_offset_x = 16, text_offset_y=35, offset_x=75, offset_y=25, Texture="resources/gui/Gold Button.png")
        self.textures = [wood_button, silver_button, gold_button]

        self.time_in_bettween = time_in_between
        self.timer = 0
        self.index = 0
        self.max_index = max_index

        self.sprite = arcade.Sprite(center_x=200, center_y=200)
        self.sprite.texture = self.textures[0].sprite.texture

        

    def on_update(self, delta_time: float):
        self.timer += delta_time
        if self.timer > self.time_in_bettween:
            self.timer -= self.time_in_bettween
            self.index += 1
            if self.index >= self.max_index:
                self.index = 0
            self.sprite = self.textures[self.index].sprite

    def on_draw(self):
        """ Draw this view """
        arcade.start_render()
        self.sprite.draw()
def main():
    """Main method"""
    window = arcade.Window(750, 500, "BEEEN")
    StartMenu = Menu("", 5, 3)#MyGame()#StartMenu()
    window.show_view(StartMenu)
    arcade.run()

if __name__ == "__main__":
    main()