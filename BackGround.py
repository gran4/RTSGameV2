import random

import arcade

from Components import load_texture_grid


class BaseBackground(arcade.Sprite):
    def __init__(self, x: float, y: float, file_name: str, scale: float):
        super().__init__(file_name, center_x=x, center_y=y, scale=scale)
        self.texture_path = file_name

    def save(self, game):
        pass

    def load(self, game):
        pass


class Land(BaseBackground):
    def __init__(self, game, x: float, y: float):
        super().__init__(x, y, "resources/Sprites/land.png", 1)
        self.typ = "Dirt"
        self.prev_typ = "Dirt"

    def load(self, game):
        if self.prev_typ == "Dirt":
            self.prev_texture = self.texture
        elif self.typ == "Sand":
            self.prev_texture = arcade.load_texture(
                "resources/Sprites/Sand.png")
        else:
            self.prev_texture = arcade.load_texture(
                "resources/Sprites/Snow.png")

        if self.typ == "Dirt":
            pass
        elif self.typ == "Sand":
            self.texture = arcade.load_texture("resources/Sprites/Sand.png")
        else:
            self.texture = arcade.load_texture("resources/Sprites/Snow.png")

    def serialize_state(self) -> dict:
        return {
            "type": "Land",
            "x": self.center_x,
            "y": self.center_y,
            "typ": self.typ,
            "prev_typ": getattr(self, "prev_typ", "Dirt"),
        }

    def apply_state(self, state: dict) -> None:
        self.center_x = state.get("x", self.center_x)
        self.center_y = state.get("y", self.center_y)
        self.position = (self.center_x, self.center_y)
        self.typ = state.get("typ", "Dirt")
        self.prev_typ = state.get("prev_typ", "Dirt")
        self.load(None)


class Sand(BaseBackground):
    def __init__(self, game, x: float, y: float):
        super().__init__(x, y, "resources/Sprites/Sand.png", 1)

    def serialize_state(self) -> dict:
        return {"type": "Sand", "x": self.center_x, "y": self.center_y}

    def apply_state(self, state: dict) -> None:
        self.center_x = state.get("x", self.center_x)
        self.center_y = state.get("y", self.center_y)
        self.position = (self.center_x, self.center_y)


class Stone(BaseBackground):
    def __init__(self, game, x: float, y: float):
        super().__init__(x, y, "resources/Sprites/Stone.png", 1)

    def serialize_state(self) -> dict:
        return {"type": "Stone", "x": self.center_x, "y": self.center_y}

    def apply_state(self, state: dict) -> None:
        self.center_x = state.get("x", self.center_x)
        self.center_y = state.get("y", self.center_y)
        self.position = (self.center_x, self.center_y)


class Sea(BaseBackground):
    def __init__(self, game, x: float, y: float):
        super().__init__(x, y, "resources/Sprites/Sea.png", .5)

    def serialize_state(self) -> dict:
        return {"type": "Sea", "x": self.center_x, "y": self.center_y}

    def apply_state(self, state: dict) -> None:
        self.center_x = state.get("x", self.center_x)
        self.center_y = state.get("y", self.center_y)
        self.position = (self.center_x, self.center_y)


class Tree(BaseBackground):
    TEXTURE_PATH = "resources/Sprites/48x48 trees copy.png"
    DEFAULT_PATH = "resources/Sprites/Tree.png"
    TEXTURE_SIZE = 48
    TEXTURE_COLUMNS = 4
    TEXTURE_COUNT = 4
    _cached_textures = None

    @classmethod
    def _get_textures(cls):
        if cls._cached_textures is None:
            try:
                cls._cached_textures = load_texture_grid(
                    cls.TEXTURE_PATH,
                    cls.TEXTURE_SIZE,
                    cls.TEXTURE_SIZE,
                    cls.TEXTURE_COLUMNS,
                    cls.TEXTURE_COUNT,
                )
            except Exception:
                cls._cached_textures = []
        return cls._cached_textures

    def __init__(self, game, x: float, y: float):
        textures = self._get_textures()
        index = random.randrange(len(textures)) if textures else 0
        super().__init__(x, y, self.DEFAULT_PATH, .682)
        self.texture_path = self.TEXTURE_PATH if textures else self.DEFAULT_PATH
        self.texture_index = index
        self._apply_texture(index)

    def _apply_texture(self, index: int) -> None:
        textures = self._get_textures()
        if textures:
            self.texture_index = max(0, min(index, len(textures) - 1))
            self.texture = textures[self.texture_index]
        else:
            self.texture_index = 0

    def serialize_state(self) -> dict:
        return {
            "type": "Tree",
            "x": self.center_x,
            "y": self.center_y,
            "texture_index": getattr(self, "texture_index", 0),
        }

    def apply_state(self, state: dict) -> None:
        self.center_x = state.get("x", self.center_x)
        self.center_y = state.get("y", self.center_y)
        self.position = (self.center_x, self.center_y)
        self._apply_texture(state.get("texture_index", getattr(self, "texture_index", 0)))


class BerryBush(BaseBackground):
    def __init__(self, game, x: float, y: float):
        super().__init__(x, y, "resources/Sprites/berry_bush.png", 1)

    def serialize_state(self) -> dict:
        return {"type": "BerryBush", "x": self.center_x, "y": self.center_y}

    def apply_state(self, state: dict) -> None:
        self.center_x = state.get("x", self.center_x)
        self.center_y = state.get("y", self.center_y)
        self.position = (self.center_x, self.center_y)
