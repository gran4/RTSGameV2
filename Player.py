import random
import time
from math import floor

import arcade
from arcade import math as arcade_math

from Components import *
from gui_compat import UIAnchorWidget

"""16, 15, 10, """


class Fire(arcade.Sprite):
    def __init__(self, game, x: float, y: float, strength):
        super().__init__("resources/Sprites/buildings/tree_farm.png", center_x=x,
                         center_y=y, scale=1, hit_box_algorithm="None")

        self.textures = load_texture_grid(
            "resources/Sprites/Fire Pixilart Sprite Sheet.png", 50, 50, 8, 8)
        self.texture = self.textures[floor(strength)]

        self.center_x = x
        self.center_y = y
        self.strength = strength
        self.fireUpdate = 0

    def update(self, game, delta_time):
        obj = self.obj
        obj.health -= self.strength*(1-obj.fire_resistence)*delta_time*.1
        self.strength += delta_time*.3*(1-obj.fire_resistence)

        if obj.health <= 0:
            obj.destroy(game)
            game.clear_uimanager()
            game.last = Bad_Cannoe(10000000, 1000000)
            self.remove_from_sprite_lists()
        elif random.random()*self.strength > .98:
            reach = round(self.strength/2)
            if reach == 0:
                return
            offset_x = random.randrange(-reach, reach)*50
            offset_y = random.randrange(-reach, reach)*50
            world_x = obj.center_x + offset_x
            world_y = obj.center_y + offset_y

            buildings = arcade.get_sprites_at_point(
                (world_x, world_y), game.Buildings)
            if buildings:
                target = buildings[0]
                if not getattr(target, "fire", None):
                    game.LightOnFire(target, self.strength/5)

            boats = arcade.get_sprites_at_point((world_x, world_y), game.Boats)
            if boats:
                target = boats[0]
                if not getattr(target, "fire", None):
                    game.LightOnFire(target, self.strength/5)
        self.fireUpdate += delta_time
        if self.fireUpdate >= 1:
            self.fireUpdate -= 1
            if self.strength > 8:
                self.strength = 7.9
            self.texture = self.textures[floor(self.strength)]

    def destroy(self, game):
        self.remove_from_sprite_lists()
        del self.obj.fire

    def save_state(self, building_lookup: dict, boat_lookup: dict) -> dict:
        owner_id = None
        owner_type = None
        owner = getattr(self, "obj", None)
        if owner in building_lookup:
            owner_id = building_lookup[owner]
            owner_type = "building"
        elif owner in boat_lookup:
            owner_id = boat_lookup[owner]
            owner_type = "boat"
        return {
            "x": self.center_x,
            "y": self.center_y,
            "strength": self.strength,
            "owner_id": owner_id,
            "owner_type": owner_type,
            "frame": floor(self.strength),
            "time": self.fireUpdate,
        }

    @classmethod
    def from_state(cls, game, state: dict, building_map: dict, boat_map: dict):
        fire = cls(game, state.get("x", 0), state.get(
            "y", 0), state.get("strength", 1))
        fire.fireUpdate = state.get("time", 0)
        owner_id = state.get("owner_id")
        owner_type = state.get("owner_type")
        owner = None
        if owner_type == "building":
            owner = building_map.get(owner_id)
        elif owner_type == "boat":
            owner = boat_map.get(owner_id)
        if owner is None:
            return None
        fire.obj = owner
        owner.fire = fire
        return fire


class BaseBoat(arcade.Sprite):
    def __init__(self, file_name, game, x: float, y: float, health: float, damage: float, range: int, capacity: int, scale: int = 1):
        super().__init__(file_name, center_x=x, center_y=y,
                         scale=scale, hit_box_algorithm="None")
        self.texture = arcade.load_texture(file_name)
        self.center_x = x
        self.center_y = y
        self.game = game

        self.damage = damage
        self.health = health
        self.max_health = health
        self.health_bar = HealthBar(game, position=self.position)
        self.health_bar.fullness = self.health/self.max_health
        self.range = range

        self.capacity = capacity
        self.list = []
        self.path = []
        self.movelist = [2]

        self.timer = 0
        self._pending_passengers: list[int] = []

    def add(self, sprite):
        if len(self.list) == self.capacity:
            return True
        if sprite in getattr(self.game, "People", []):
            self.game.People.remove(sprite)
        sprite.remove_from_sprite_lists()
        sprite.health_bar.visible = False
        self.list.append(sprite)
        sprite.host_boat = self
        if getattr(self.game, "last", None) is sprite:
            self.game.clear_uimanager()
            self.game.last = None
        return False

    def remove(self):
        if len(self.list) == 0:
            return None
        sprite = self.list[0]
        self.list.pop(0)
        sprite.position = self.position
        sprite.health_bar.visible = True
        sprite.host_boat = None
        if sprite not in getattr(self.game, "People", []):
            self.game.People.append(sprite)
        return sprite

    def update(self, game, delta_time):
        self.timer += delta_time
        self.health_bar.fullness = self.health/self.max_health
        if len(self.path) > 0:
            rot = rotation(self.center_x, self.center_y,
                           self.path[0][0], self.path[0][1], angle=self.angle+0, max_turn=360*delta_time)-0
            self.angle = rot
        if self.timer <= 2:
            return
        elif len(self.path) > 0:
            self.position = self.path[0]
            self.path.pop(0)
            self.health_bar.position = self.position
        self.timer = 0

    def clicked(self, game):
        game.clear_uimanager()
        if game.last == self:
            game.last = None
            return
        game.last = self
        button = CustomUIFlatButton(
            game.Alphabet_Textures, text="Move", width=140, height=50)
        button.on_click = game.Move
        wrapper = UIAnchorWidget(anchor_x="left", anchor_y="bottom",
                                 child=button, align_x=0, align_y=0)
        game.uimanager.add(wrapper)
        game.extra_buttons.append(wrapper)

        button = CustomUIFlatButton(
            game.Alphabet_Textures, text="Leave", width=140, height=50)
        button.on_click = game.leave
        button.obj = self
        wrapper = UIAnchorWidget(anchor_x="left", anchor_y="bottom",
                                 child=button, align_x=150, align_y=0)
        game.uimanager.add(wrapper)
        game.extra_buttons.append(wrapper)

        button = CustomUIFlatButton(
            game.Alphabet_Textures, text="Destroy", width=140, height=50)
        button.on_click = game.clean_destroy
        button.obj = self
        wrapper = UIAnchorWidget(anchor_x="left", anchor_y="bottom",
                                 child=button, align_x=300, align_y=0)
        game.uimanager.add(wrapper)
        game.extra_buttons.append(wrapper)

        self.clicked_override(game)

    def clicked_override(self, game):
        pass

    def destroy(self, game, menu_destroy: bool = False):
        for person in list(self.list):
            self._disembark_person(game, person)
        self.list.clear()
        self.health_bar.remove_from_sprite_lists()
        self.remove_from_sprite_lists()
        if getattr(game, "player", None) and game.player.boat is self:
            game.player.boat = None
            # Drop the player at the boat's final position if the tile is walkable
            tile = game.graph[int(self.center_x/50)][int(self.center_y/50)]
            if tile == 0:
                game.player.position = (self.center_x, self.center_y)
            else:
                # Find nearest walkable tile
                player_pos = game.player.position
                target, _ = get_closest_sprite(self.position, game.Lands)
                if target:
                    game.player.position = target.position
                else:
                    game.player.position = player_pos
        if getattr(game, "last", None) is self:
            game.clear_uimanager()
            game.last = None

    def _disembark_person(self, game, person):
        tile = None
        if getattr(game, "graph", None):
            try:
                tile = game.graph[int(self.center_x/50)][int(self.center_y/50)]
            except (IndexError, TypeError):
                tile = None
        if tile == 0:
            target_pos = (self.center_x, self.center_y)
        else:
            land, _ = get_closest_sprite(
                self.position, getattr(game, "Lands", []))
            target_pos = land.position if land else (
                self.center_x, self.center_y)

        person.host_boat = None
        person.position = target_pos
        person.health_bar.visible = True
        person.health_bar.position = target_pos
        if person not in getattr(game, "People", []):
            game.People.append(person)

    def serialize_state(self, person_ids: dict | None = None) -> dict:
        passengers: list[int] = []
        if person_ids:
            for person in self.list:
                pid = person_ids.get(person)
                if pid is not None:
                    passengers.append(pid)
        return {
            "type": type(self).__name__,
            "x": self.center_x,
            "y": self.center_y,
            "health": self.health,
            "max_health": self.max_health,
            "path": [list(pos) for pos in self.path],
            "passengers": passengers,
        }

    def apply_state(self, game, state: dict) -> None:
        self.center_x = state.get("x", self.center_x)
        self.center_y = state.get("y", self.center_y)
        self.position = (self.center_x, self.center_y)
        self.health = state.get("health", self.health)
        self.max_health = state.get("max_health", self.max_health)
        self.path = [tuple(pos) for pos in state.get("path", list(self.path))]
        self.health_bar.position = self.position
        self.health_bar.fullness = self.health / \
            self.max_health if self.max_health else 1
        self._pending_passengers = state.get("passengers", [])


class Bad_Cannoe(BaseBoat):
    def __init__(self, game, x: float, y: float):
        super().__init__("resources/Sprites/Arrow.png", game, x, y, 10, 0, 0, 2, scale=.5)


class Cannoe(BaseBoat):
    def __init__(self, game, x: float, y: float):
        super().__init__("resources/Sprites/Arrow.png", game, x, y, 10, 0, 0, 2)


class VikingLongShip(BaseBoat):
    def __init__(self, game, x: float, y: float):
        super().__init__("resources/Sprites/Arrow.png",
                         game, x, y, 20, 0, 0, 2, scale=0.78125)
        self.textures = load_texture_grid(
            "resources/Sprites/Viking Ship/sprPlayer_strip16.png", 64, 64, 16, 16, margin=0)
        self.texture = self.textures[0]
        self.rot = 0

    def update(self, game, delta_time):
        self.health_bar.fullness = self.health/self.max_health
        self.timer += delta_time
        if len(self.path) > 0:
            rot = rotation(self.center_x, self.center_y,
                           self.path[0][0], self.path[0][1], angle=self.rot+90, max_turn=360*delta_time)-90
            self.rot = rot

            angle = round(rot/22.5)
            if angle == 16:
                angle = 0
            self.texture = self.textures[angle]
        if self.timer <= 2:
            return
        elif len(self.path) > 0:
            self.position = self.path[0]
            self.path.pop(0)
            self.health_bar.position = self.position
        self.timer = 0


class Carrier(BaseBoat):
    def __init__(self, game, x: float, y: float):
        super().__init__("resources/Sprites/Arrow.png", game, x, y, 10, 0, 0, 2)


class Player(arcade.Sprite):
    def __init__(self, center_x: float = 0, center_y: float = 0):
        super().__init__(None, scale=2, center_x=center_x, center_y=center_y)
        textures = load_texture_grid(
            "resources/Sprites/Player Sprite Sheet.png", 24, 33, 4, 16)
        self.timer = 0
        self.index = 0
        self.key = "S"

        self.texture = textures[0]
        self.S_Texture = textures[:4]
        self.W_Texture = textures[4:8]
        self.D_Texture = textures[8:12]
        self.A_Texture = textures[12:16]
        self.boat = None

    def pressed_update(self):
        match self.key:
            case "S":
                self.texture = self.S_Texture[self.index]
            case "W":
                self.texture = self.W_Texture[self.index]
            case "A":
                self.texture = self.A_Texture[self.index]
            case "D":
                self.texture = self.D_Texture[self.index]

    def on_update(self, delta_time: float = 1 / 60):
        self.timer += delta_time
        if self.timer >= .5:
            self.timer -= random.randrange(3, 8)/10
            self.index += 1
            if self.index >= 4:
                self.index = 0
            match self.key:
                case "S":
                    self.texture = self.S_Texture[self.index]
                case "W":
                    self.texture = self.W_Texture[self.index]
                case "A":
                    self.texture = self.A_Texture[self.index]
                case "D":
                    self.texture = self.D_Texture[self.index]
        self.update_animation(delta_time)
        super().update(delta_time)
# odd movement


class Person(arcade.Sprite):
    def __init__(self, game, x: float, y: float, scale=1):
        super().__init__(center_x=x, center_y=y, scale=scale)
        self.game = game
        textures = load_texture_grid(
            "resources/Sprites/Elf Sprite Sheet.png", 24, 33, 4, 16)
        self._width = 24
        self._height = 33

        self.texture = textures[0]
        self.S_Texture = textures[:4]
        self.W_Texture = textures[4:8]
        self.D_Texture = textures[8:12]
        self.A_Texture = textures[12:16]
        self.index = 0
        self.key = "S"

        self.center_x = x
        self.center_y = y

        self._health = 1000000000
        self.max_health = 100
        self.health_bar = HealthBar(game, position=self.position)
        self._update_health_bar_fullness()
        self.var = None
        self.amount = 0

        self.path = []
        self.path_timer = 0
        self.next_time = 1
        self.timer = 0
        self.timer2 = 0

        self.skill = None

        self.laboring_skill = 1
        self.lumbering_skill = 1
        self.mining_skill = 1
        self.laboring_skill = 1
        self.farming_skill = 1
        self.building_skill = 1
        self.movelist = [0]
        self.in_building_id: int | None = None
        self.host_building = None
        self.host_boat = None

    def clicked(self, game):
        game.clear_uimanager()
        if game.last == self:
            game.last = None
            return
        game.last = self

        if self.host_boat is None:
            button = CustomUIFlatButton(
                game.Alphabet_Textures, text="Move", width=140, height=50)
            button.on_click = game.Move
            wrapper = UIAnchorWidget(anchor_x="left", anchor_y="bottom",
                                     child=button, align_x=0, align_y=0)
            game.uimanager.add(wrapper)
            game.extra_buttons.append(wrapper)

        self.clicked_override(game)

    def clicked_override(self, game):
        pass

    def update(self, game, delta_time):
        if self.health <= 0:
            self.destroy(game)
        self.timer += delta_time
        if self.timer > 1:
            self.timer -= 1
            if len(self.path) == 1:
                self.update_self(game)
            else:
                self.update_movement(game)
            self.harvest_resource(game)

        self.timer2 += delta_time
        if self.timer2 >= .5:
            self.timer2 -= random.randrange(3, 8)/10
            self.index += 1
            if self.index >= 4:
                self.index = 0
            match self.key:
                case "S":
                    self.texture = self.S_Texture[self.index]
                case "W":
                    self.texture = self.W_Texture[self.index]
                case "A":
                    self.texture = self.A_Texture[self.index]
                case "D":
                    self.texture = self.D_Texture[self.index]

        self._update_health_bar_fullness()

    def update_movement(self, game):
        if self.path != []:
            target = self.path[0]
            blocking_buildings = self._blocking_buildings_at(game, target)
            if blocking_buildings:
                self.path = []
                game.show_move_feedback("Path blocked", target[0], target[1])
                return
            if self.center_x < self.path[0][0]:
                self.key = "D"
            elif self.center_x > self.path[0][0]:
                self.key = "A"
            elif self.center_y < self.path[0][1]:
                self.key = "W"
            elif self.center_y > self.path[0][1]:
                self.key = "S"
            self.position = self.path[0]
            self.path.pop(0)

            self.health_bar.position = self.position
        else:
            self.key = "S"

    def update_self(self, game):
        prev_pos = self.position
        target = self.path[0]
        tile = game.graph[round(target[0]/50)][round(target[1]/50)]
        buildings_at_target = arcade.get_sprites_at_point(
            target, game.Buildings)
        blocking_buildings = self._blocking_buildings_at(game, target)
        boats_at_target = arcade.get_sprites_at_point(target, game.Boats)
        if tile not in self.movelist and not buildings_at_target and not boats_at_target:
            self.path = []
            game.show_move_feedback("Can't move there", target[0], target[1])
            return
        self.position = self.path.pop(0)
        self.health_bar.position = self.position
        destination = self.position

        refresh = getattr(game, "refresh_population", None)
        blocking_buildings = blocking_buildings if target == self.position else self._blocking_buildings_at(
            game, self.position)
        if blocking_buildings:
            building = blocking_buildings[0]
            self._cancel_move(game, prev_pos, destination,
                              "Can't enter that building")
            return

        buildings_at_point = buildings_at_target if target == self.position else arcade.get_sprites_at_point(
            self.position, game.Buildings)
        if buildings_at_point:
            building = buildings_at_point[0]
            if not getattr(building, "allows_people", True):
                self._cancel_move(game, prev_pos, destination,
                                  "Can't enter that building")
                return
            if not building.add(self):
                if callable(refresh):
                    refresh()
                return
            self._cancel_move(game, prev_pos, destination, "Building is full")
            return

        ships_at_point = boats_at_target if target == self.position else arcade.get_sprites_at_point(
            self.position, game.Boats)
        if ships_at_point:
            if not ships_at_point[0].add(self):
                if callable(refresh):
                    refresh()
                return
            # Boat full; move back to previous safe tile
            self.position = prev_pos
            self.health_bar.position = self.position
            self.path = []
            game.show_move_feedback(
                "Boat is full", destination[0], destination[1])
            return

    @property
    def health(self) -> float:
        return getattr(self, "_health", 0)

    @health.setter
    def health(self, value: float) -> None:
        self._health = value
        self._update_health_bar_fullness()

    def _update_health_bar_fullness(self) -> None:
        if not getattr(self, "health_bar", None):
            return
        max_health = getattr(self, "max_health", 0)
        if max_health:
            fullness = max(0.0, min(1.0, self.health / max_health))
        else:
            fullness = 1.0
        self.health_bar.fullness = fullness

    def harvest_resource(self, game):
        variables = vars(game)
        vars_self = vars(self)
        if self.var != None:
            if self.laboring_skill < 1.2:
                self.laboring_skill += .001
            if self.skill != None:
                if vars_self[self.skill] < 2:
                    vars_self[self.skill] += .005
                amount = self.amount*game.overall_multiplier
                variables[self.var] += amount*game.overall_multiplier

    def destroy(self, game, *, count_population: bool = True):
        host_building = getattr(self, "host_building", None)
        if host_building and self in getattr(host_building, "list_of_people", []):
            host_building.list_of_people.remove(self)
        self.host_building = None
        host_boat = getattr(self, "host_boat", None)
        if host_boat and self in getattr(host_boat, "list", []):
            host_boat.list.remove(self)
        self.host_boat = None
        self.health_bar.remove_from_sprite_lists()
        self.remove_from_sprite_lists()
        self.health = -100
        if count_population:
            game.population -= 1
        refresh = getattr(game, "refresh_population", None)
        if callable(refresh):
            refresh()

    def serialize_state(self) -> dict:
        return {
            "type": type(self).__name__,
            "x": self.center_x,
            "y": self.center_y,
            "health": self.health,
            "max_health": self.max_health,
            "var": self.var,
            "amount": self.amount,
            "skill": self.skill,
            "skills": {
                "laboring": self.laboring_skill,
                "lumbering": self.lumbering_skill,
                "mining": self.mining_skill,
                "farming": self.farming_skill,
                "building": self.building_skill,
            },
            "in_building": self.in_building_id,
        }

    def apply_state(self, game, state: dict) -> None:
        self.center_x = state.get("x", self.center_x)
        self.center_y = state.get("y", self.center_y)
        self.position = (self.center_x, self.center_y)
        self.health = state.get("health", self.health)
        self.max_health = state.get("max_health", self.max_health)
        skills = state.get("skills", {})
        self.laboring_skill = skills.get("laboring", self.laboring_skill)
        self.lumbering_skill = skills.get("lumbering", self.lumbering_skill)
        self.mining_skill = skills.get("mining", self.mining_skill)
        self.farming_skill = skills.get("farming", self.farming_skill)
        self.building_skill = skills.get("building", self.building_skill)
        self.var = state.get("var", self.var)
        self.amount = state.get("amount", self.amount)
        self.skill = state.get("skill", self.skill)
        self.in_building_id = state.get("in_building")
        if not getattr(self, "health_bar", None):
            self.health_bar = HealthBar(game, position=self.position)
        self._update_health_bar_fullness()
        self.health_bar.position = self.position

    def _blocking_buildings_at(self, game, target):
        buildings = arcade.get_sprites_at_point(target, game.Buildings)
        return [building for building in buildings if not getattr(building, "allows_people", True)]

    def _cancel_move(self, game, prev_pos, destination, message):
        self.position = prev_pos
        self.health_bar.position = self.position
        self.path = []
        game.show_move_feedback(message, destination[0], destination[1])


class People_that_attack(Person):
    def __init__(self, game, filename, x, y, damage, range, health, scale=1):
        super().__init__(game, x, y, scale=scale)
        self.texture = arcade.load_texture(filename)
        self.damage = damage
        self.range = range
        self.health = health

        self.check = True
        self.focused_on = None

    def destroy(self, game, *, count_population: bool = True):
        super().destroy(game, count_population=count_population)

    def update(self, game, delta_time):
        # NOTE: Override
        # update anims here
        if self.health <= 0:
            self.destroy(game)
            return
        self.health += .025*delta_time
        self.on_update(game, delta_time)

    def on_update(self, game, delta_time):
        if self.check:
            game.calculate_path(self, game.Enemies)
        if not self.focused_on:
            return
        elif self.state == "Attack":
            self.state = "Idle"
        elif self.focused_on.health <= 0:
            self.focused_on = None
            game.calculate_path(self, game.Enemies)
        elif arcade.get_distance_between_sprites(self, self.focused_on) <= self.range:
            self.on_attack(game, delta_time)
        elif self.check:
            game.calculate_path(self, game.Enemies)
        elif len(self.path) < 1:
            self.check = True

    def on_attack(self, game, delta_time):
        pass

    def clicked_override(self, game):
        button = CustomUIFlatButton(game.Alphabet_Textures, text=self.state2, width=140,
                                    height=50, x=0, y=50, text_offset_x=16, text_offset_y=35, offset_x=75, offset_y=25)
        button.on_click = game.person_switch
        button.obj = self
        wrapper = UIAnchorWidget(anchor_x="left", anchor_y="bottom",
                                 child=button, align_x=150, align_y=0)
        game.extra_buttons.append(wrapper)
        game.uimanager.add(wrapper)

    def state_update(self, game, state):
        pass

    def serialize_state(self) -> dict:
        state = super().serialize_state()
        state.update({
            "state": getattr(self, "state", None),
            "state2": getattr(self, "state2", None),
        })
        return state

    def apply_state(self, game, state: dict) -> None:
        super().apply_state(game, state)
        self.state = state.get("state", getattr(self, "state", "Idle"))
        self.state2 = state.get("state2", getattr(self, "state2", None))


class BadGifter(People_that_attack):
    def __init__(self, game, x, y):
        super().__init__(game, "resources/Sprites/enemies/enemy.png", x, y, 10, 500, 100, scale=1.5)
        self.set_up(game, x, y)

    def set_up(self, game, x, y):
        self.building_bias = 1
        self.people_bias = .3

        textures = load_texture_grid(
            "resources/Sprites/Elf Sprite Sheet.png", 24, 33, 4, 16)
        self._width = 24
        self._height = 33

        self.texture = textures[0]
        self.S_Texture = textures[:4]
        self.W_Texture = textures[4:8]
        self.D_Texture = textures[8:12]
        self.A_Texture = textures[12:16]
        self.index = 0
        self.key = "S"
        self.coal = arcade.Sprite(
            "resources/Sprites/Coal.png", center_x=x, center_y=y, scale=2)

        self.timer = 0
        self.timer2 = 0

        self.gifts = arcade.SpriteList()
        self.state = "Idle"
        self.state2 = "Patrol"

        game.overParticles.append(self.coal)

    def destroy(self, game, *, count_population: bool = True):
        self.coal.remove_from_sprite_lists()
        [coal.remove_from_sprite_lists() for coal in self.gifts]
        super().destroy(game, count_population=count_population)

    def draw(self, *, filter=None, pixelated=None, blend_function=None):
        super().draw()
        self.coal.draw()

    def update(self, game, delta_time):
        if self.health <= 0:
            self.destroy(game)
            return
        self.timer += delta_time
        if self.state2 == "Patrol":
            self.on_update(game, delta_time)
            if self.timer >= 1:
                self.timer -= 1
                self.update_movement(game)
        elif self.timer > 1:
            self.timer -= 1
            if len(self.path) == 1:
                self.update_self(game)
            else:
                self.update_movement(game)
            self.harvest_resource(game)

        self.timer2 += delta_time
        if self.timer2 >= .5:
            self.timer2 -= random.randrange(3, 8)/10
            self.index += 1
            if self.index >= 4:
                self.index = 0
            match self.key:
                case "S":
                    self.texture = self.S_Texture[self.index]
                case "W":
                    self.texture = self.W_Texture[self.index]
                case "A":
                    self.texture = self.A_Texture[self.index]
                case "D":
                    self.texture = self.D_Texture[self.index]

        for gift in self.gifts:
            advance_sprite(gift, delta_time)
            gift.update()
            gift.time += delta_time
            if gift.time > 15:
                gift.remove_from_sprite_lists()
            elif self.focused_on is None:
                pass
            elif arcade_math.get_distance(gift.center_x, gift.center_y, self.focused_on.center_x, self.focused_on.center_y) < 25:
                self.focused_on.health -= self.damage * \
                    delta_time*random.random()*random.random()*4
                gift.remove_from_sprite_lists()

    def update_movement(self, game):
        super().update_movement(game)
        if self.state2 == "Work":
            return
        self.coal.remove_from_sprite_lists()
        match self.key:
            case "S":
                self.texture = self.S_Texture[self.index]
                if not self.coal in game.overParticles:
                    game.overParticles.append(self.coal)
                self.coal.center_x = self.center_x
                self.coal.center_y = self.center_y-5
            case "W":
                self.texture = self.W_Texture[self.index]
                if not self.coal in game.underParticals:
                    game.underParticals.append(self.coal)
                self.coal.center_x = self.center_x
                self.coal.center_y = self.center_y+15
            case "A":
                self.texture = self.A_Texture[self.index]
                if not self.coal in game.overParticles:
                    game.overParticles.append(self.coal)
                self.coal.center_x = self.center_x-10
                self.coal.center_y = self.center_y-5
            case "D":
                self.texture = self.D_Texture[self.index]
                if not self.coal in game.overParticles:
                    game.overParticles.append(self.coal)
                self.coal.center_x = self.center_x+10
                self.coal.center_y = self.center_y-5

    def update_self(self, game):
        super().update_self(game)
        if self.state2 == "Work":
            return
        self.coal.remove_from_sprite_lists()
        match self.key:
            case "S":
                self.texture = self.S_Texture[self.index]
                if not self.coal in game.overParticles:
                    game.overParticles.append(self.coal)
                self.coal.center_x = self.center_x
                self.coal.center_y = self.center_y-5
            case "W":
                self.texture = self.W_Texture[self.index]
                if not self.coal in game.overParticles:
                    game.overParticles.append(self.coal)
                self.coal.center_x = self.center_x-10
                self.coal.center_y = self.center_y-10
            case "A":
                self.texture = self.A_Texture[self.index]
                if not self.coal in game.underParticals:
                    game.underParticals.append(self.coal)
                self.coal.center_x = self.center_x
                self.coal.center_y = self.center_y+10
            case "D":
                self.texture = self.D_Texture[self.index]
                if not self.coal in game.overParticles:
                    game.overParticles.append(self.coal)
                self.coal.center_x = self.center_x+10
                self.coal.center_y = self.center_y-10

    def on_attack(self, game, delta_time):
        if self.state2 == "Work":
            return
        if self.timer < 1:
            return
        self.state = "Attack"

        if self.focused_on.health <= 0:
            self.focused_on = None
            self.check = True
            self.on_update(game, 0)

        heading = heading_towards(
            self.center_x,
            self.center_y,
            self.focused_on.center_x,
            self.focused_on.center_y,
        )
        heading += random.randrange(-5, 5)
        coal = arcade.Sprite(
            "resources/Sprites/Coal.png",
            scale=1,
            center_x=self.center_x,
            center_y=self.center_y,
            angle=heading - 90,
        )
        coal.time = 0
        set_sprite_motion(coal, heading, 50)
        self.gifts.append(coal)
        game.overParticles.append(coal)
        coal.update()
        self.timer = 0

    def state_update(self, game, state):

        if state == "Work":
            self.coal.remove_from_sprite_lists()
        elif state == "Patrol":
            if self.key == "S":
                game.underParticals.append(self.coal)
            else:
                game.overParticles.append(self.coal)

    def serialize_state(self) -> dict:
        state = super().serialize_state()
        state.update({
            "coal": {
                "x": self.coal.center_x,
                "y": self.coal.center_y,
                "layer": "under" if self.coal in getattr(getattr(self, "game", None), "underParticals", []) else "over",
            },
            "gifts": [
                {
                    "x": gift.center_x,
                    "y": gift.center_y,
                    "dx": getattr(gift, "_motion_dx", 0.0),
                    "dy": getattr(gift, "_motion_dy", 0.0),
                    "time": getattr(gift, "time", 0.0),
                }
                for gift in self.gifts
            ],
        })
        return state

    def apply_state(self, game, state: dict) -> None:
        super().apply_state(game, state)
        coal_state = state.get("coal", {})
        self.coal.center_x = coal_state.get("x", self.center_x)
        self.coal.center_y = coal_state.get("y", self.center_y)
        layer = coal_state.get("layer")
        self.coal.remove_from_sprite_lists()
        if self.state2 == "Work":
            pass
        elif layer == "under":
            game.underParticals.append(self.coal)
        else:
            game.overParticles.append(self.coal)
        self.gifts = arcade.SpriteList()
        for entry in state.get("gifts", []):
            gift = arcade.Sprite(
                "resources/Sprites/Coal.png",
                scale=1,
                center_x=entry.get("x", self.center_x),
                center_y=entry.get("y", self.center_y),
            )
            gift.time = entry.get("time", 0.0)
            gift._motion_dx = entry.get("dx", 0.0)
            gift._motion_dy = entry.get("dy", 0.0)
            self.gifts.append(gift)
            game.overParticles.append(gift)


class BadReporter(People_that_attack):
    def __init__(self, game, x, y):
        super().__init__(game, "resources/Sprites/enemies/enemy.png", x, y, 25, 500, 100, scale=1.5)
        self.set_up(game, x, y)

    def set_up(self, game, x, y):
        self.building_bias = 1
        self.people_bias = .3

        textures = load_texture_grid(
            "resources/Sprites/Elf Sprite Sheet.png", 24, 33, 4, 16)
        self._width = 24
        self._height = 33

        self.texture = textures[0]
        self.S_Texture = textures[:4]
        self.W_Texture = textures[4:8]
        self.D_Texture = textures[8:12]
        self.A_Texture = textures[12:16]
        self.index = 0
        self.key = "S"
        self.paper = arcade.Sprite(
            "resources/Sprites/Paper.png", center_x=x, center_y=y)

        self.timer = 0
        self.timer2 = 0

        self.gifts = arcade.SpriteList()
        self.state = "Idle"
        self.state2 = "Patrol"

        game.overParticles.append(self.paper)

    def destroy(self, game, *, count_population: bool = True):
        self.paper.remove_from_sprite_lists()
        [coal.remove_from_sprite_lists() for coal in self.gifts]
        super().destroy(game, count_population=count_population)

    def draw(self, *, filter=None, pixelated=None, blend_function=None):
        super().draw()
        self.paper.draw()

    def update(self, game, delta_time):
        if self.health <= 0:
            self.destroy(game)
            return
        self.timer += delta_time
        if self.state2 == "Patrol":
            self.on_update(game, delta_time)
            if self.timer >= 1:
                self.timer -= 1
                self.update_movement(game)
        elif self.timer > 1:
            self.timer -= 1
            if len(self.path) == 1:
                self.update_self(game)
            else:
                self.update_movement(game)
            self.harvest_resource(game)

        self.timer2 += delta_time
        if self.timer2 >= .5:
            self.timer2 -= random.randrange(3, 8)/10
            self.index += 1
            if self.index >= 4:
                self.index = 0
            match self.key:
                case "S":
                    self.texture = self.S_Texture[self.index]
                case "W":
                    self.texture = self.W_Texture[self.index]
                case "A":
                    self.texture = self.A_Texture[self.index]
                case "D":
                    self.texture = self.D_Texture[self.index]

        for gift in self.gifts:
            advance_sprite(gift, delta_time)
            gift.update()
            gift.time += delta_time
            if gift.time > 15:
                gift.remove_from_sprite_lists()
            elif self.focused_on is None:
                pass
            elif arcade_math.get_distance(gift.center_x, gift.center_y, self.focused_on.center_x, self.focused_on.center_y) < 25:
                self.focused_on.health -= self.damage * \
                    delta_time*random.random()*random.random()*4
                gift.remove_from_sprite_lists()

    def update_movement(self, game):
        super().update_movement(game)
        if self.state2 == "Work":
            return
        self.paper.remove_from_sprite_lists()
        match self.key:
            case "S":
                self.texture = self.S_Texture[self.index]
                if not self.paper in game.overParticles:
                    game.overParticles.append(self.paper)
                self.paper.center_x = self.center_x
                self.paper.center_y = self.center_y-5
            case "W":
                self.texture = self.W_Texture[self.index]
                if not self.paper in game.underParticals:
                    game.underParticals.append(self.paper)
                self.paper.center_x = self.center_x
                self.paper.center_y = self.center_y+15
            case "A":
                self.texture = self.A_Texture[self.index]
                if not self.paper in game.overParticles:
                    game.overParticles.append(self.paper)
                self.paper.center_x = self.center_x-10
                self.paper.center_y = self.center_y-5
            case "D":
                self.texture = self.D_Texture[self.index]
                if not self.paper in game.overParticles:
                    game.overParticles.append(self.paper)
                self.paper.center_x = self.center_x+10
                self.paper.center_y = self.center_y-5

    def update_self(self, game):
        super().update_self(game)
        if self.state2 == "Work":
            return
        self.paper.remove_from_sprite_lists()
        match self.key:
            case "S":
                self.texture = self.S_Texture[self.index]
                if not self.paper in game.overParticles:
                    game.overParticles.append(self.paper)
                self.paper.center_x = self.center_x
                self.paper.center_y = self.center_y-5
            case "W":
                self.texture = self.W_Texture[self.index]
                if not self.paper in game.overParticles:
                    game.overParticles.append(self.paper)
                self.paper.center_x = self.center_x-10
                self.paper.center_y = self.center_y-10
            case "A":
                self.texture = self.A_Texture[self.index]
                if not self.paper in game.underParticals:
                    game.underParticals.append(self.paper)
                self.paper.center_x = self.center_x
                self.paper.center_y = self.center_y+10
            case "D":
                self.texture = self.D_Texture[self.index]
                if not self.paper in game.overParticles:
                    game.overParticles.append(self.paper)
                self.paper.center_x = self.center_x+10
                self.paper.center_y = self.center_y-10

    def on_attack(self, game, delta_time):
        if self.state2 == "Work":
            return
        if self.timer < 1:
            return
        self.state = "Attack"

        if self.focused_on.health <= 0:
            self.focused_on = None
            self.check = True
            self.on_update(game, 0)

        heading = heading_towards(
            self.center_x,
            self.center_y,
            self.focused_on.center_x,
            self.focused_on.center_y,
        )
        heading += random.randrange(-5, 5)
        coal = arcade.Sprite(
            "resources/Sprites/Paper.png",
            scale=1,
            center_x=self.center_x,
            center_y=self.center_y,
            angle=heading - 90,
        )
        coal.time = 0
        set_sprite_motion(coal, heading, 50)
        self.gifts.append(coal)
        game.overParticles.append(coal)
        coal.update()
        self.timer = 0

    def state_update(self, game, state):

        if state == "Work":
            self.paper.remove_from_sprite_lists()
        elif state == "Patrol":
            if self.key == "S":
                game.underParticals.append(self.paper)
            else:
                game.overParticles.append(self.paper)

    def serialize_state(self) -> dict:
        state = super().serialize_state()
        game_ref = getattr(self, "game", None)
        under_particles = getattr(
            game_ref, "underParticals", []) if game_ref else []
        over_particles = getattr(
            game_ref, "overParticles", []) if game_ref else []
        layer = None
        if self.paper in under_particles:
            layer = "under"
        elif self.paper in over_particles:
            layer = "over"
        state.update({
            "paper": {
                "x": self.paper.center_x,
                "y": self.paper.center_y,
                "layer": layer,
            },
            "gifts": [
                {
                    "x": gift.center_x,
                    "y": gift.center_y,
                    "dx": getattr(gift, "_motion_dx", 0.0),
                    "dy": getattr(gift, "_motion_dy", 0.0),
                    "time": getattr(gift, "time", 0.0),
                }
                for gift in self.gifts
            ],
        })
        return state

    def apply_state(self, game, state: dict) -> None:
        super().apply_state(game, state)
        paper_state = state.get("paper", {})
        self.paper.center_x = paper_state.get("x", self.center_x)
        self.paper.center_y = paper_state.get("y", self.center_y)
        layer = paper_state.get("layer")
        self.paper.remove_from_sprite_lists()
        if self.state2 == "Work":
            pass
        elif layer == "under":
            game.underParticals.append(self.paper)
        else:
            game.overParticles.append(self.paper)

        self.gifts = arcade.SpriteList()
        for entry in state.get("gifts", []):
            gift = arcade.Sprite(
                "resources/Sprites/Paper.png",
                scale=1,
                center_x=entry.get("x", self.center_x),
                center_y=entry.get("y", self.center_y),
            )
            gift.time = entry.get("time", 0.0)
            gift._motion_dx = entry.get("dx", 0.0)
            gift._motion_dy = entry.get("dy", 0.0)
            self.gifts.append(gift)
            game.overParticles.append(gift)
