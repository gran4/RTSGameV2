import arcade


class BaseBackground(arcade.Sprite):
    def __init__(self, x:float, y:float, file_name:str, scale:float):
        super().__init__(file_name, center_x=x, center_y=y, scale=scale)
        self.texture = arcade.load_texture(file_name)
        self.center_x = x
        self.center_y = y
        self.hit_box = self.texture.hit_box_points
    def save(self, game):
        pass
    def load(self, game):
        pass

class Land(BaseBackground):
    def __init__(self, game, x:float, y:float):
        super().__init__(x, y, "resources/Sprites/land.png", 1)
        self.typ = "Dirt"
        self.prev_typ = "Dirt"
    def load(self, game):
        if self.prev_typ== "Dirt":
            self.prev_texture = self.texture
        elif self.typ == "Sand":
            self.prev_texture = arcade.load_texture("resources/Sprites/Sand.png")
        else:
            self.prev_texture = arcade.load_texture("resources/Sprites/Snow.png")


        if self.typ == "Dirt":
            pass
        elif self.typ == "Sand":
            self.texture = arcade.load_texture("resources/Sprites/Sand.png")
        else:
            self.texture = arcade.load_texture("resources/Sprites/Snow.png")

    

class Sand(BaseBackground):
    def __init__(self, game, x:float, y:float):
        super().__init__(x, y, "resources/Sprites/Sand.png", 1)


class Stone(BaseBackground):
    def __init__(self, game, x:float, y:float):
        super().__init__(x, y, "resources/Sprites/Stone.png", 1)

class Sea(BaseBackground):
    def __init__(self, game, x:float, y:float):
        super().__init__(x, y, "resources/Sprites/Sea.png", .5)

class Tree(BaseBackground):
    def __init__(self, game, x:float, y:float):
        super().__init__(x, y, "resources/Sprites/Tree.png", .682)

class BerryBush(BaseBackground):
    def __init__(self, game, x:float, y:float):
        super().__init__(x, y, "resources/Sprites/berry_bush.png", 1)