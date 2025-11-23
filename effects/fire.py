import math
import random
from math import floor

import arcade

from Components import load_texture_grid


class Fire(arcade.Sprite):
    def __init__(self, game, x: float, y: float, strength):
        super().__init__("resources/Sprites/buildings/tree_farm.png", center_x=x,
                         center_y=y, scale=1, hit_box_algorithm="None")

        self.textures = load_texture_grid(
            "resources/Sprites/Fire Pixilart Sprite Sheet.png", 50, 50, 8, 8)
        idx = min(len(self.textures) - 1, floor(strength))
        self.texture = self.textures[idx]

        self.center_x = x
        self.center_y = y
        self.strength = strength
        self.fireUpdate = 0
        self._haze_time = 0.0
        self._haze_sprite = None
        self._add_heat_haze(game)

    def update(self, game, delta_time):
        obj = self.obj
        # Stronger, faster-burning fires
        obj.health -= self.strength*(1-obj.fire_resistence)*delta_time*.2
        self.strength += delta_time*.7*(1-obj.fire_resistence)

        self._update_heat_haze(game, delta_time)

        if obj.health <= 0:
            obj.destroy(game)
            game.clear_uimanager()
            from Player import Bad_Cannoe  # Local import to avoid circular deps
            game.last = Bad_Cannoe(game, 10000000, 1000000)
            self.remove_from_sprite_lists()
        elif random.random()*self.strength > .9:
            reach = max(1, round(self.strength))
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
            idx = min(len(self.textures) - 1, floor(self.strength))
            self.texture = self.textures[idx]

    def destroy(self, game):
        self._remove_heat_haze()
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
            "frame": min(len(self.textures) - 1, floor(self.strength)),
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

    # Heat haze helpers
    def _add_heat_haze(self, game):
        if getattr(self, "_haze_sprite", None):
            return
        haze_texture = arcade.make_soft_circle_texture(
            36, (255, 190, 120, 180), center_alpha=160, outer_alpha=0)
        haze = arcade.Sprite()
        haze.texture = haze_texture
        haze.center_x = self.center_x
        haze.center_y = self.center_y
        haze.scale = 1.1
        haze.alpha = 110
        haze._haze_phase = random.uniform(0, math.pi * 2)
        haze._haze_spin = random.uniform(-20, 20)
        haze._haze_wobble = random.uniform(0.04, 0.08)
        self._haze_sprite = haze
        if game and haze not in getattr(game, "overParticles", []):
            game.overParticles.append(haze)

    def _update_heat_haze(self, game, delta_time):
        haze = getattr(self, "_haze_sprite", None)
        target = getattr(self, "obj", None)
        if not haze or not target:
            return
        haze.center_x = target.center_x
        haze.center_y = target.center_y
        self._haze_time += delta_time
        phase = getattr(haze, "_haze_phase", 0.0) + delta_time * 1.5
        haze._haze_phase = phase
        wobble = getattr(haze, "_haze_wobble", 0.05)
        haze.scale = 1.05 + math.sin(phase) * wobble
        haze.angle += getattr(haze, "_haze_spin", 10) * delta_time
        haze.alpha = max(50, min(160, int(120 + 45 * math.sin(self._haze_time * 2.2))))
        if game and haze not in getattr(game, "overParticles", []):
            game.overParticles.append(haze)

    def _remove_heat_haze(self):
        haze = getattr(self, "_haze_sprite", None)
        if haze:
            haze.remove_from_sprite_lists()
            self._haze_sprite = None
