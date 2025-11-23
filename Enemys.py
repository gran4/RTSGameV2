import random

import arcade
from arcade import math as arcade_math

from Components import *
from effects import ProjectileEffect

"""
OBJECT x

x2 = type(x).__new__(type(x))
x2 

use unlocked to expand enemies and ui
"""


class BaseEnemy(arcade.Sprite):
    def __init__(self, file_name: str, x: float, y: float, health: float, damage: float, range: int, scale: float = 1):
        super().__init__(file_name, center_x=x, center_y=y, scale=scale)
        self.texture = arcade.load_texture(file_name)
        self.texture_path = file_name
        self.center_x = x
        self.center_y = y

        self.damage = damage
        self.health = health
        self.range = range
        self.state = "Idle"

        self.barriers = []
        self.path = []
        self.path_timer = 0

        self.check = True
        self.create_statemachene()
        self.rotation = 0
        # Slow down movement pacing so enemies step less frequently.
        self.next_time = 1.6
        self.focused_on = None
        self.spawn_kwargs: dict = {}

    def destroy(self, game):
        self.remove_from_sprite_lists()
        self.health = -100
        # Remove any floating question mark that was tracking this enemy.
        marks = getattr(game, "floating_question_marks", None)
        if marks:
            for mark in list(marks):
                if getattr(mark, "tracking", None) is self:
                    try:
                        mark.remove_from_sprite_lists()
                        marks.remove(mark)
                    except Exception:
                        pass
                    for text_sprite in getattr(mark, "text_sprites", []) or []:
                        try:
                            text_sprite.remove_from_sprite_lists()
                        except Exception:
                            pass

    def get_path(self):
        if type(self.path) != list:
            return None
        elif len(self.path) == 0:
            return None

        path = self.path[0]
        self.path.pop(0)
        return path

    def create_statemachene(self):
        self.idle = False
        self.tracking = False
        self.attacking = False
    # NOTE: over ride the function

    def update(self, game, delta_time):
        if self.health <= 0:
            self.destroy(game)
            return
        self.on_update(game, delta_time)
        if self.focused_on is None and not self.path:
            game.calculate_enemy_path(self)
        # Child was never stepping along its path after the update override.
        self.update_movement(game, delta_time)
        self.update_movement(game, delta_time)
    # NOTE: Always call on_update in update

    def on_update(self, game, delta_time):

        if self.state == "Attack":
            self.state = "Idle"
        if self.focused_on:
            if arcade.get_distance_between_sprites(self, self.focused_on) <= self.range:
                self.on_attack(game, delta_time)
            elif len(self.path) < 1:
                self.check = True
            elif self.check:
                game.calculate_enemy_path(self)
                self.check = False
            if self.focused_on.health <= 0:
                self.focused_on.destroy(game)
                self.focused_on = None
                self.check = True
        if self.check:
            game.calculate_enemy_path(self)
        return True

    def update_movement(self, game, delta_time):
        self.path_timer += delta_time
        if self.path_timer > self.next_time:
            pos = self.get_path()
            if pos is not None:
                self.position = pos
            self.path_timer -= self.next_time
            # self.next_time = difficulty[game["map"][round(self.center_x/50)][round(self.center_y/50)]]

    def on_attack(self, game, delta_time):
        self.focused_on.health -= self.damage * \
            delta_time*random.random()*random.random()*4

    def On_Focused_on(self):
        pass

    def load(self, game):
        texture_path = getattr(self, "_saved_texture_path", None) or getattr(
            self, "texture_path", None)
        if texture_path:
            try:
                texture = arcade.load_texture(texture_path)
                self.texture = texture
            except Exception:
                pass
        if getattr(self, "texture", None):
            set_sprite_hit_box(self, self.texture.hit_box_points)

    def serialize_state(self) -> dict:
        state = {
            "type": type(self).__name__,
            "x": self.center_x,
            "y": self.center_y,
            "health": self.health,
            "max_health": getattr(self, "max_health", self.health),
            "damage": self.damage,
            "range": self.range,
            "state": getattr(self, "state", "Idle"),
            "path": [list(pos) for pos in self.path],
            "path_timer": self.path_timer,
            "next_time": self.next_time,
            "spawn": getattr(self, "spawn_kwargs", {}),
        }
        extra = self._serialize_extra_state()
        if extra:
            state["extra"] = extra
        return state

    def apply_state(self, game, state: dict) -> None:
        self.center_x = state.get("x", self.center_x)
        self.center_y = state.get("y", self.center_y)
        self.position = (self.center_x, self.center_y)
        self.health = state.get("health", self.health)
        self.max_health = state.get(
            "max_health", getattr(self, "max_health", self.health))
        self.damage = state.get("damage", self.damage)
        self.range = state.get("range", self.range)
        self.state = state.get("state", getattr(self, "state", "Idle"))
        self.spawn_kwargs = state.get(
            "spawn", getattr(self, "spawn_kwargs", {}))
        self.path = [tuple(pos) for pos in state.get("path", list(self.path))]
        self.path_timer = state.get("path_timer", self.path_timer)
        self.next_time = state.get("next_time", self.next_time)
        self._apply_extra_state(game, state.get("extra"))

    def _serialize_extra_state(self) -> dict:
        return {}

    def _apply_extra_state(self, game, extra_state: dict | None) -> None:
        return


class Child(BaseEnemy):
    def __init__(self, game, x, y, difficulty=1):
        super().__init__("resources/Sprites/enemies/enemy.png", x,
                         y, 5*difficulty, 10*difficulty, 5, scale=1)
        self.spawn_kwargs = {"difficulty": difficulty}

        self.building_bias = 1
        self.people_bias = .3
        self.boat_bias = 1

        self.movelist = [0, 2]

        self.front_texture = arcade.load_texture(
            "resources/Sprites/enemies/child_front.png")
        self.back_texture = arcade.load_texture(
            "resources/Sprites/enemies/child_back.png")
        self.left_texture = arcade.load_texture(
            "resources/Sprites/enemies/child_left.png")
        self.right_texture = self.left_texture.flip_left_right()

        self.texture = self.front_texture
        # Track cleanup to avoid leaving any stray sprites if extended later.
        self._cleaned_up = False

    def update(self, game, delta_time):
        if self.health <= 0:
            self.destroy(game)
            return
        self.on_update(game, delta_time)
        if self.focused_on is None and not self.path:
            game.calculate_enemy_path(self)
        # Step along the calculated path.
        self.update_movement(game, delta_time)
        if self.health <= 0:
            self._cleanup()

    def update_movement(self, game, delta_time):
        prev_x, prev_y = self.position
        super().update_movement(game, delta_time)
        if prev_x == self.center_x and prev_y == self.center_y:
            return
        if prev_x < self.center_x:
            self.texture = self.back_texture
        elif prev_x > self.center_x:
            self.texture = self.front_texture
        elif prev_y < self.center_y:
            self.texture = self.right_texture
        elif prev_y > self.center_y:
            self.texture = self.left_texture

    def destroy(self, game):
        super().destroy(game)
        self._cleanup()

    def _cleanup(self):
        if getattr(self, "_cleaned_up", False):
            return
        self._cleaned_up = True


class Enemy_Swordsman(BaseEnemy):
    def __init__(self, x: float, y: float, difficulty=1):
        super().__init__("resources/Sprites/enemies/NightBorneWarrior/NightBorne.png",
                         x, y, 10*difficulty, 5*difficulty, 40, scale=1)
        self.spawn_kwargs = {"difficulty": difficulty}
        self.textures = load_texture_grid(
            "resources/Sprites/enemies/NightBorneWarrior/NightBorne.png", 80, 80, 22, 111, margin=0)
        self.texture = self.textures[0]

        self.Idle = self.textures[:7]
        self.IdleAnim = AnimationPlayer(.1)

        self.Attack = self.textures[44:55]
        self.AttackAnim = AnimationPlayer(.1)

        self.Death = self.textures[88:111]
        self.DeathAnim = AnimationPlayer(.1)

        self.state = "Idle"
        self.attack_time = 0
        self.attack_timer = 0
        self.WaitToAttack = 1
        self.can_attack = False

        self.building_bias = 10
        self.people_bias = .1
        self.movelist = [0]

    def destroy(self, game):
        self.state = "Death"
        self.can_attack = False

    def update(self, game, delta_time):
        if self.health <= 0:
            self.state = "Death"
        self.on_update(game, delta_time)

        if self.state == "Idle":
            anim = self.IdleAnim.updateAnim(delta_time, len(self.Idle))
            if anim is not None:
                self.texture = self.Idle[anim]
            self.attack_timer += delta_time
            if self.attack_timer >= self.WaitToAttack:
                self.can_attack = True
            self.update_movement(game, delta_time)
        elif self.state == "Death":
            anim = self.IdleAnim.updateAnim(delta_time, len(self.Death))
            if anim == 0:
                self.remove_from_sprite_lists()
            if anim is not None:
                self.texture = self.Death[anim]

    def on_attack(self, game, delta_time):
        if not self.can_attack:
            return
        self.state = "Attack"
        self.attack_time += delta_time
        anim = self.AttackAnim.updateAnim(delta_time, len(self.Attack))
        if anim is not None:
            self.texture = self.Attack[anim]
        if anim == 0:
            self.state = "Idle"
            self.attack_time = 0
            self.attack_timer = 0
            self.can_attack = False


class Enemy_Slinger(BaseEnemy):
    def __init__(self, game, x, y, difficulty=1):
        super().__init__("resources/Sprites/enemies/enemy.png", x,
                         y, 5*difficulty, 10*difficulty, 325, scale=1)
        self.spawn_kwargs = {"difficulty": difficulty}
        self.texture = arcade.load_texture("resources/Sprites/enemies/enemy.png")

        self.building_bias = 1
        self.people_bias = .3
        self.boat_bias = 1

        self.movelist = [0]

        self.bow = arcade.Sprite(
            center_x=self.center_x, center_y=self.center_y, image_width=50, image_height=50)  # Entity()
        self.bow.Attack_animation = AnimationPlayer(.1)
        self.bow.Attack_textures = load_texture_grid(
            "resources/Sprites/enemies/Long Bow Pixilart Sprite Sheet.png", 50, 50, 50, 9)
        self.bow.texture = self.bow.Attack_textures[0]
        self.bow.AttackAnimTimes = [.25, .125,
                                    .125, .125, .2, .1, .05, .025, .025]
        self.bow.WaitToAttack = .2
        self.bow.timer = 0
        self.bow.canAttack = False

        self.arrows = arcade.SpriteList()
        self.state = "Idle"
        self._sfx_cooldown = 0.0
        self._sfx_cooldown = 0.0

        self.front_texture = arcade.load_texture(
            "resources/Sprites/enemies/child_front.png")
        self.back_texture = arcade.load_texture(
            "resources/Sprites/enemies/child_back.png")
        self.left_texture = arcade.load_texture(
            "resources/Sprites/enemies/child_left.png")
        self.right_texture = self.left_texture.flip_left_right()
        self.texture = self.front_texture

        self.pull_back_sound = None
        game.overParticles.append(self.bow)

    def update(self, game, delta_time):
        if self.health <= 0:
            self.destroy(game)
            return
        self.on_update(game, delta_time)

        if self.focused_on:
            heading = heading_towards(
                self.center_x,
                self.center_y,
                self.focused_on.center_x,
                self.focused_on.center_y,
            )
            self.bow.angle = -heading - 90

        self.bow.center_x = self.center_x
        self.bow.center_y = self.center_y

        self.update_movement(game, delta_time)
        for arrow in list(self.arrows):
            advance_sprite(arrow, delta_time)
            arrow.update()

            arrow.time += delta_time
            if arrow.time > 15 or not self.focused_on:
                arrow.remove_from_sprite_lists()
                try:
                    self.arrows.remove(arrow)
                except ValueError:
                    pass
                continue
            elif arcade_math.get_distance(arrow.center_x, arrow.center_y, self.focused_on.center_x, self.focused_on.center_y) < 25:
                arrow.hit = True
                if getattr(game, "speed", 1) > 0:
                    arrow.hit_sound = SOUND(
                        "resources/sound_effects/arrow-impact.wav",
                        .25,
                        get_dist(self.position, game.player.position),
                        volume_map=getattr(game, "audio_type_vols", None),
                        sound_type="UI",
                    )
                if getattr(arrow, "hit_sound", None) and getattr(arrow.hit_sound, "_timer", None):
                    arrow.hit_sound._timer.active = False
                arrow.visible = False

            if arrow.hit:
                arrow.destroy_timer += delta_time
                if arrow.destroy_timer > .5:
                    self.focused_on.health -= self.damage*random.random()*random.random()*4
                    arrow.remove_from_sprite_lists()
                    try:
                        self.arrows.remove(arrow)
                    except ValueError:
                        pass
                    continue
                if getattr(arrow, "hit_sound", None) and getattr(arrow.hit_sound, "_timer", None):
                    arrow.hit_sound._timer.set_time(
                        arrow.hit_sound._timer.get_time()+.5)
            # else:
            #    arrow.pull_back_sound._timer.set_time(arrow.pull_back_sound._timer.get_time()+delta_time)

        self.bow.timer += delta_time
        if self.bow.timer < self.bow.WaitToAttack:
            return
        self.bow.timer -= self.bow.WaitToAttack
        self.bow.canAttack = True

    def update_movement(self, game, delta_time):
        prev_x, prev_y = self.position
        super().update_movement(game, delta_time)
        if prev_x == self.center_x and prev_y == self.center_y:
            return
        if prev_x < self.center_x:
            self.texture = self.back_texture
        elif prev_x > self.center_x:
            self.texture = self.front_texture
        elif prev_y < self.center_y:
            self.texture = self.right_texture
        elif prev_y > self.center_y:
            self.texture = self.left_texture

    def on_attack(self, game, delta_time):
        if not self.bow.canAttack:
            return
        self._sfx_cooldown -= getattr(game, "real_delta_time", delta_time)

        self._sfx_cooldown -= getattr(game, "real_delta_time", delta_time)
        if getattr(game, "speed", 1) <= 0:
            if self.pull_back_sound:
                try:
                    self.pull_back_sound.pause()
                except Exception:
                    pass
                self.pull_back_sound = None
            return
        if not self.pull_back_sound and self._sfx_cooldown <= 0:
            self.pull_back_sound = SOUND(
                "resources/sound_effects/Arrow Shoot.wav",
                1,
                get_dist(self.position, game.player.position),
                volume_map=getattr(game, "audio_type_vols", None),
                sound_type="UI",
                cooldown=0,
            )
            if getattr(self.pull_back_sound, "_timer", None):
                self.pull_back_sound._timer.active = False
            self._sfx_cooldown = 0.15
        if getattr(self.pull_back_sound, "_timer", None):
            self.pull_back_sound._timer.set_time(
                self.pull_back_sound._timer.get_time()+delta_time*.5)
        anim = self.bow.Attack_animation.updateAnim(
            delta_time, len(self.bow.Attack_textures))
        if anim is None:
            return
        elif anim == 0:
            self.bow.canAttack = False
        elif anim == 8:
            heading = heading_towards(
                self.center_x,
                self.center_y,
                self.focused_on.center_x,
                self.focused_on.center_y,
            )
            heading += random.randrange(-5, 5)
            arrow = arcade.Sprite(
                "resources/Sprites/enemies/projectile.png",
                scale=1,
                center_x=self.center_x,
                center_y=self.center_y,
                angle=-heading,
            )
            arrow.time = 0
            set_sprite_motion(arrow, heading, 50)
            self.arrows.append(arrow)
            game.overParticles.append(arrow)
            arrow.update()
            arrow.hit = False
            arrow.destroy_timer = 0
            self.pull_back_sound = None

        self.bow.texture = self.bow.Attack_textures[anim]
        self.bow.Attack_animation.timetoupdate = self.bow.AttackAnimTimes[anim]

        self.bow.timer = 0

    def destroy(self, game):
        if self.bow in game.overParticles:
            game.overParticles.remove(self.bow)
        self.bow.remove_from_sprite_lists()
        self.bow = None

        for arrow in list(self.arrows):
            if arrow in game.overParticles:
                game.overParticles.remove(arrow)
            arrow.remove_from_sprite_lists()
        self.arrows = arcade.SpriteList()
        return super().destroy(game)

    def _serialize_extra_state(self) -> dict:
        bow_state = {
            "timer": getattr(self.bow, "timer", 0.0),
            "can_attack": getattr(self.bow, "canAttack", False),
            "angle": self.bow.angle,
            "anim_index": getattr(self.bow.Attack_animation, "index", 0),
            "anim_time": getattr(self.bow.Attack_animation, "time", 0.0),
        }
        arrows_state = []
        for arrow in self.arrows:
            arrows_state.append(
                {
                    "x": arrow.center_x,
                    "y": arrow.center_y,
                    "dx": getattr(arrow, "_motion_dx", 0.0),
                    "dy": getattr(arrow, "_motion_dy", 0.0),
                    "time": getattr(arrow, "time", 0.0),
                    "angle": arrow.angle,
                    "hit": getattr(arrow, "hit", False),
                    "destroy_timer": getattr(arrow, "destroy_timer", 0.0),
                    "visible": arrow.visible,
                }
            )
        return {
            "bow": bow_state,
            "arrows": arrows_state,
        }

    def _apply_extra_state(self, game, extra_state: dict | None) -> None:
        if not extra_state:
            return
        bow_state = extra_state.get("bow", {})
        self.bow.timer = bow_state.get(
            "timer", getattr(self.bow, "timer", 0.0))
        self.bow.canAttack = bow_state.get(
            "can_attack", getattr(self.bow, "canAttack", False))
        self.bow.angle = bow_state.get("angle", self.bow.angle)
        self.bow.Attack_animation.index = bow_state.get(
            "anim_index", self.bow.Attack_animation.index)
        self.bow.Attack_animation.time = bow_state.get(
            "anim_time", self.bow.Attack_animation.time)

        self.arrows = arcade.SpriteList()
        arrow_texture = "resources/Sprites/enemies/projectile.png"
        for entry in extra_state.get("arrows", []):
            arrow = arcade.Sprite(
                arrow_texture,
                scale=1,
                center_x=entry.get("x", self.center_x),
                center_y=entry.get("y", self.center_y),
                angle=entry.get("angle", 0.0),
            )
            arrow._motion_dx = entry.get("dx", 0.0)
            arrow._motion_dy = entry.get("dy", 0.0)
            arrow.time = entry.get("time", 0.0)
            arrow.hit = entry.get("hit", False)
            arrow.destroy_timer = entry.get("destroy_timer", 0.0)
            arrow.visible = entry.get("visible", True)
            self.arrows.append(arrow)
            game.overParticles.append(arrow)


class Arsonist(BaseEnemy):
    def __init__(self, game, x: float, y: float, difficulty=1):
        super().__init__("resources/Sprites/enemies/child_front.png", x,
                         y, 5*difficulty, 5*difficulty, 40, scale=1)
        self.spawn_kwargs = {"difficulty": difficulty}

        self.front_texture = arcade.load_texture(
            "resources/Sprites/enemies/child_front.png")
        self.back_texture = arcade.load_texture(
            "resources/Sprites/enemies/child_back.png")
        self.left_texture = arcade.load_texture(
            "resources/Sprites/enemies/child_left.png")
        self.right_texture = self.left_texture.flip_left_right()

        self.building_bias = 1
        self.people_bias = 100  # float("inf")
        self.boat_bias = 100

        self.movelist = [0]
        self.fire_strength = 1

        self.Explosian = arcade.Sprite(center_x=x-10, center_y=y+10, scale=.25)
        self.Explosian.textures = load_texture_grid(
            "resources/Sprites/enemies/Fire_Totem/Fire_Totem-full_Sheet.png", 64, 100, 14, 70)
        self.Explosian.texture = self.Explosian.textures[4]
        self.Explosian.AnimationPlayer = AnimationPlayer(.1)
        game.overParticles.append(self.Explosian)
        self._explosion_cleaned_up = False

    def destroy(self, game):
        self._cleanup_explosion(game)
        super().destroy(game)
        self.Explosian.remove_from_sprite_lists()

    def update(self, game, delta_time):
        if self.health <= 0:
            self.destroy(game)
            return
        self.on_update(game, delta_time)
        self.update_movement(game, delta_time)

        if self.state == "Attack":
            self.Explosian.position = self.position
            self.attack(game, delta_time)
        # If the arsonist dies mid-attack, clean up the lingering explosion sprite.
        if self.health <= 0:
            self._cleanup_explosion(game)

    def update_movement(self, game, delta_time):
        prev_x, prev_y = self.position
        super().update_movement(game, delta_time)
        self.Explosian.position = self.center_x-10, self.center_y+10
        if prev_x == self.center_x and prev_y == self.center_y:
            return
        if prev_x < self.center_x:
            self.texture = self.back_texture
        elif prev_x > self.center_x:
            self.texture = self.front_texture
        elif prev_y < self.center_y:
            self.texture = self.right_texture
        elif prev_y > self.center_y:
            self.texture = self.left_texture

    def on_attack(self, game, delta_time):
        self.Explosian.scale = 1
        self.state = "Attack"

    def attack(self, game, delta_time):
        anim = self.Explosian.AnimationPlayer.updateAnim(delta_time, 10)
        if anim is not None:
            self.Explosian.texture = self.Explosian.textures[60:70][anim]

        if anim == 0:
            self.destroy(game)
            self.remove_from_sprite_lists()

            hit = arcade.check_for_collision_with_lists(
                self, [game.Buildings, game.People, game.Boats], method=3)
            for obj in hit:
                obj.health -= self.damage
                if obj.health <= 0:
                    obj.destroy(game)
                    continue
                if obj.__module__ == "Buildings":
                    try:
                        obj.fire.strength += 1
                    except:
                        game.LightOnFire(obj, self.fire_strength)
            self.health = -100

    def _cleanup_explosion(self, game):
        if getattr(self, "_explosion_cleaned_up", False):
            return
        explosion = getattr(self, "Explosian", None)
        if not explosion:
            self._explosion_cleaned_up = True
            return
        try:
            explosion.remove_from_sprite_lists()
            if game and explosion in getattr(game, "overParticles", []):
                game.overParticles.remove(explosion)
        except Exception:
            pass
        explosion.center_x = 100000
        explosion.center_y = 100000
        anim = getattr(explosion, "AnimationPlayer", None)
        if anim:
            anim.index = 0
            anim.time = 0
        self._explosion_cleaned_up = True

    def _serialize_extra_state(self) -> dict:
        anim = getattr(self.Explosian, "AnimationPlayer", None)
        return {
            "explosion": {
                "x": self.Explosian.center_x,
                "y": self.Explosian.center_y,
                "scale": self.Explosian.scale,
                "anim_index": getattr(anim, "index", 0),
                "anim_time": getattr(anim, "time", 0.0),
            },
            "fire_strength": self.fire_strength,
        }

    def _apply_extra_state(self, game, extra_state: dict | None) -> None:
        if not extra_state:
            return
        self.fire_strength = extra_state.get(
            "fire_strength", self.fire_strength)
        explosion_state = extra_state.get("explosion", {})
        self.Explosian.center_x = explosion_state.get(
            "x", self.Explosian.center_x)
        self.Explosian.center_y = explosion_state.get(
            "y", self.Explosian.center_y)
        self.Explosian.scale = explosion_state.get(
            "scale", self.Explosian.scale)
        anim = getattr(self.Explosian, "AnimationPlayer", None)
        if anim:
            anim.index = explosion_state.get("anim_index", anim.index)
            anim.time = explosion_state.get("anim_time", anim.time)
        if self.Explosian not in game.overParticles:
            game.overParticles.append(self.Explosian)


class Golem(BaseEnemy):
    def __init__(self, game, x: float, y: float, difficulty=1):
        super().__init__("resources/Sprites/enemies/Stone Golem/Character_sheet.png",
                         x, y, 10*difficulty, 10*difficulty, 40, scale=.8)
        self.spawn_kwargs = {"difficulty": difficulty}
        textures = load_texture_grid(
            "resources/Sprites/enemies/Stone Golem/Character_sheet.png", 100, 100, 10, 100, margin=0)
        self.texture = textures[0]
        self.Idle = textures[:4]
        self.Idle_animation = AnimationPlayer(.1)

        self.ShutDown = textures[31:39]
        self.ShutDown_animation = AnimationPlayer(.1)

        self.Death = textures[73:84]
        self.Death_animation = AnimationPlayer(.1)

        self.attacking = textures[13]

        self.attack_timer = 0
        self.WaitToAttack = 2
        self.canAttack = True

        self.attack_time = 0

        self.building_bias = .1
        self.people_bias = 1
        self.boat_bias = 1

        self.movelist = [0]

        affect_textures = load_texture_grid(
            "resources/Sprites/enemies/Free Pixel Effects Pack/10_weaponhit_spritesheet.png", 100, 100, 6, 31)[1:]
        self.affect = arcade.Sprite(center_x=100000, center_y=100000,
                                    texture=affect_textures[0])
        self.affect.textures = affect_textures
        self.affect.animation_player = AnimationPlayer(.03)
        game.underParticals.append(self.affect)
        self._affect_cleaned_up = False

    def destroy(self, game):
        self._cleanup_affect(game)
        self.state = "Death"
        self.canAttack = False

    def update(self, game, delta_time):
        if self.health <= 0:
            self.state = "Death"
        if self.state == "Death":
            self._cleanup_affect(game)
        self.on_update(game, delta_time)

        if self.state == "Idle":
            anim = self.Idle_animation.updateAnim(delta_time, len(self.Idle))
            if anim is not None:
                self.texture = self.Idle[anim]
            self.attack_timer += delta_time
            if self.attack_timer >= self.WaitToAttack:
                self.canAttack = True
            self.update_movement(game, delta_time)
        elif self.state == "Death":
            anim = self.Death_animation.updateAnim(delta_time, len(self.Death))
            if anim == 0:
                self.remove_from_sprite_lists()
            if anim is not None:
                self.texture = self.Death[anim]

    def on_attack(self, game, delta_time):
        if not self.canAttack:
            return

        self.texture = self.attacking
        self.attack_time += delta_time

        self.affect.center_x = self.center_x
        self.affect.center_y = self.center_y

        self.affect.scale += 0.15 * random.random()
        anim = self.affect.animation_player.updateAnim(
            delta_time, len(self.affect.textures))
        if anim is not None:
            self.affect.texture = self.affect.textures[anim]

        if self.attack_time >= 1:
            hit = arcade.check_for_collision_with_lists(
                self.affect, [game.Buildings, game.People], method=3)
            for thing in hit:
                thing.health -= self.damage
                if thing.health <= 0:
                    thing.destroy(game)
            self.affect.width = 64
            self.affect.height = 64
            self.affect.scale = 1
            self.affect.center_x = 100000
            self.affect.center_y = 100000
            self.affect.animation_player.index = 0
            self.affect.animation_player.time = 0
            self.affect.texture = self.affect.textures[0]

            self.texture = self.Idle[0]
            self.canAttack = False
            self.attack_time = 0
            self.attack_timer = 0
        # If the golem is gone (killed during an attack), make sure the lingering
        # hit effect is cleaned up instead of sticking around the map.
        if self.health <= 0:
            self._cleanup_affect(game)

    def _serialize_extra_state(self) -> dict:
        anim = getattr(self.affect, "animation_player", None)
        return {
            "affect": {
                "x": self.affect.center_x,
                "y": self.affect.center_y,
                "scale": self.affect.scale,
                "width": self.affect.width,
                "height": self.affect.height,
                "anim_index": getattr(anim, "index", 0),
                "anim_time": getattr(anim, "time", 0.0),
            },
            "attack_timer": self.attack_timer,
            "attack_time": self.attack_time,
            "can_attack": self.canAttack,
        }

    def _apply_extra_state(self, game, extra_state: dict | None) -> None:
        super()._apply_extra_state(game, extra_state)
        if not extra_state:
            return
        affect_state = extra_state.get("affect", {})
        self.affect.center_x = affect_state.get("x", self.affect.center_x)
        self.affect.center_y = affect_state.get("y", self.affect.center_y)
        self.affect.scale = affect_state.get("scale", self.affect.scale)
        self.affect.width = affect_state.get("width", self.affect.width)
        self.affect.height = affect_state.get("height", self.affect.height)
        anim = getattr(self.affect, "animation_player", None)
        if anim:
            anim.index = affect_state.get("anim_index", anim.index)
            anim.time = affect_state.get("anim_time", anim.time)
        if self.affect not in game.underParticals:
            game.underParticals.append(self.affect)
        self.attack_timer = extra_state.get("attack_timer", self.attack_timer)
        self.attack_time = extra_state.get("attack_time", self.attack_time)
        self.canAttack = extra_state.get("can_attack", self.canAttack)

    def _cleanup_affect(self, game):
        if getattr(self, "_affect_cleaned_up", False):
            return
        affect = getattr(self, "affect", None)
        if not affect:
            self._affect_cleaned_up = True
            return
        # Remove from any sprite lists so it stops drawing once the golem dies.
        try:
            affect.remove_from_sprite_lists()
            if game and affect in getattr(game, "underParticals", []):
                game.underParticals.remove(affect)
        except Exception:
            pass
        affect.center_x = 100000
        affect.center_y = 100000
        anim = getattr(affect, "animation_player", None)
        if anim:
            anim.index = 0
            anim.time = 0
        self._affect_cleaned_up = True


class Wizard(BaseEnemy):
    def __init__(self, game, x: float, y: float, difficulty):
        super().__init__("resources/Sprites/enemies/Wizard/Idle.png",
                         x, y, 5*difficulty, 2*difficulty, 200, scale=1)
        self.spawn_kwargs = {"difficulty": difficulty}

        self.front_texture = arcade.load_texture(
            "resources/Sprites/enemies/child_front.png")
        self.back_texture = arcade.load_texture(
            "resources/Sprites/enemies/child_back.png")
        self.left_texture = arcade.load_texture(
            "resources/Sprites/enemies/child_left.png")
        self.right_texture = self.left_texture.flip_horizontally()
        self.texture = self.front_texture

        self.wand = arcade.Sprite(
            "resources/Sprites/enemies/Wand.png", scale=.35, center_x=x-10, center_y=y)
        projectile_texture = "resources/Sprites/enemies/Warped shooting fx files/hits-1/frames/hits-1-2.png"
        destruction_paths = [
            f"resources/Sprites/enemies/Warped shooting fx files/hits-1/frames/hits-1-{i+1}.png"
            for i in range(1, 5)
        ]
        self.projectile_effect = ProjectileEffect(
            projectile_texture,
            destruction_paths,
            scale=1,
            speed=50,
            animation_speed=0.1,
        )
        self.wand.projectile = arcade.Sprite(projectile_texture, scale=0)
        self.wand.projectile.visible = False

        game.overParticles.append(self.wand)
        game.overParticles.append(self.wand.projectile)

        self.movelist = [0]
        self.building_bias = 10
        self.people_bias = 1
        self.boat_bias = 10

        self.state = "Idle"

        self.WaitToAttack = 1
        self.timer = 0
        self.canAttack = False

    def update(self, game, delta_time):
        if self.health <= 0:
            self.state = "Death"
        self.on_update(game, delta_time)

        if self.state == "Idle":
            self.timer += delta_time
            if self.timer > self.WaitToAttack:
                self.canAttack = True
            self.update_movement(game, delta_time)
            self.wand.position = self.center_x-10, self.center_y
            self.wand.projectile.position = self.wand.center_x, self.wand.center_y+15
        elif self.state == "Death":
            self.destroy(game)

        def _should_detonate(projectile):
            if not self.focused_on:
                return False
            return arcade_math.get_distance(
                projectile.center_x,
                projectile.center_y,
                self.focused_on.center_x,
                self.focused_on.center_y,
            ) < 25

        def _on_explode(projectile):
            hit = arcade.check_for_collision_with_lists(
                projectile, [game.Buildings, game.People, game.Boats], method=3)
            for obj in hit:
                obj.health -= self.damage
                if obj.health > 0:
                    continue
                obj.destroy(game)

        self.projectile_effect.update(
            game,
            delta_time,
            should_detonate=_should_detonate,
            on_explode=_on_explode,
        )

    def on_attack(self, game, delta_time):
        if not self.canAttack:
            return
        self.state = "Attack"
        Attack1 = arcade.get_distance_between_sprites(
            self, self.focused_on) > 200

        self.wand.projectile.visible = True
        scale_x, scale_y = self.wand.projectile.scale
        new_scale = scale_y + float(delta_time)/2
        self.wand.projectile.scale = (new_scale, new_scale)

        current_scale = self.wand.projectile.scale
        if isinstance(current_scale, tuple):
            current_scale = current_scale[1]
        if current_scale < 1:
            return
        heading = heading_towards(
            self.center_x,
            self.center_y,
            self.focused_on.center_x,
            self.focused_on.center_y,
        )
        if Attack1:
            self.projectile_effect.spawn(
                game,
                self.position,
                heading,
            )
        else:
            self.projectile_effect.spawn(
                game,
                self.position,
                heading,
                maxtime=3,
                max_rotation=22,
                count=5,
            )

        self.canAttack = False
        self.timer = 0
        self.state = "Idle"
        self.wand.projectile.scale = (0, 0)

    def destroy(self, game):
        super().destroy(game)
        self.remove_from_sprite_lists()
        self.wand.remove_from_sprite_lists()
        self.wand.projectile.remove_from_sprite_lists()
        self.projectile_effect.cleanup()

    def _serialize_extra_state(self) -> dict:
        wand_state = {
            "wand_x": self.wand.center_x,
            "wand_y": self.wand.center_y,
            "projectile_scale": self.wand.projectile.scale,
            "projectile_visible": self.wand.projectile.visible,
        }
        return {
            "wand": wand_state,
            "projectiles": self.projectile_effect.serialize(),
            "timer": self.timer,
            "can_attack": self.canAttack,
        }

    def _apply_extra_state(self, game, extra_state: dict | None) -> None:
        if not extra_state:
            return
        wand_state = extra_state.get("wand", {})
        self.wand.center_x = wand_state.get("wand_x", self.wand.center_x)
        self.wand.center_y = wand_state.get("wand_y", self.wand.center_y)
        self.wand.projectile.scale = wand_state.get(
            "projectile_scale", self.wand.projectile.scale)
        self.wand.projectile.visible = wand_state.get(
            "projectile_visible", self.wand.projectile.visible)
        if self.wand not in game.overParticles:
            game.overParticles.append(self.wand)
        if self.wand.projectile not in game.overParticles:
            game.overParticles.append(self.wand.projectile)

        self.timer = extra_state.get("timer", self.timer)
        self.canAttack = extra_state.get("can_attack", self.canAttack)

        self.projectile_effect.restore(game, extra_state.get("projectiles", []))


class Privateer(BaseEnemy):
    def __init__(self, game, x: float, y: float, difficulty=1):
        super().__init__("resources/Sprites/boat.png",
                         x, y, 20*difficulty, 5*difficulty, 150, .5)
        self.spawn_kwargs = {"difficulty": difficulty}
        self.people_bias = 1
        self.building_bias = 1
        self.boat_bias = .2
        self.movelist = [2]

        self.bow = arcade.Sprite(
            center_x=self.center_x, center_y=self.center_y, image_width=50, image_height=50)  # Entity()
        self.bow.Attack_animation = AnimationPlayer(.1)
        self.bow.Attack_textures = load_texture_grid(
            "resources/Sprites/enemies/Long Bow Pixilart Sprite Sheet.png", 50, 50, 50, 9)
        self.bow.texture = self.bow.Attack_textures[0]
        self.bow.AttackAnimTimes = [.25, .125,
                                    .125, .125, .2, .1, .05, .025, .025]
        self.bow.WaitToAttack = .2
        self.bow.timer = 0
        self.bow.canAttack = False
        game.overParticles.append(self.bow)

        self.arrows = arcade.SpriteList()
        self.state = "Idle"

    def update(self, game, delta_time):
        if self.health <= 0:
            self.destroy(game)
            return
        self.on_update(game, delta_time)

        if self.focused_on:
            heading = heading_towards(
                self.center_x,
                self.center_y,
                self.focused_on.center_x,
                self.focused_on.center_y,
            )
            self.bow.angle = -heading - 90

        self.bow.center_x = self.center_x
        self.bow.center_y = self.center_y

        self.update_movement(game, delta_time)

        for arrow in list(self.arrows):
            advance_sprite(arrow, delta_time)
            arrow.update()
            arrow.time += delta_time
            if arrow.time > 15 or not self.focused_on:
                arrow.remove_from_sprite_lists()
                try:
                    self.arrows.remove(arrow)
                except ValueError:
                    pass
                continue
            elif arcade_math.get_distance(arrow.center_x, arrow.center_y, self.focused_on.center_x, self.focused_on.center_y) < 25:
                self.focused_on.health -= self.damage*random.random()*random.random()*4
                arrow.remove_from_sprite_lists()
                try:
                    self.arrows.remove(arrow)
                except ValueError:
                    pass

        self.bow.timer += delta_time
        if self.bow.timer < self.bow.WaitToAttack:
            return
        self.bow.timer -= self.bow.WaitToAttack
        self.bow.canAttack = True

    def update_movement(self, game, delta_time):
        if self.path:
            heading = heading_towards(
                self.center_x,
                self.center_y,
                self.path[0][0],
                self.path[0][1],
            )
            self.angle = heading - 90
        self.path_timer += delta_time
        if self.path_timer > self.next_time:
            pos = self.get_path()
            if pos is not None:
                self.position = pos
            self.path_timer -= self.next_time

    def on_attack(self, game, delta_time):
        self.angle = heading_towards(
            self.center_x,
            self.center_y,
            self.focused_on.center_x,
            self.focused_on.center_y,
        ) - 90
        if not self.bow.canAttack:
            return
        anim = self.bow.Attack_animation.updateAnim(
            delta_time, len(self.bow.Attack_textures))
        if anim is None:
            return
        elif anim == 0:
            self.bow.canAttack = False
        elif anim == 8:
            heading = heading_towards(
                self.center_x,
                self.center_y,
                self.focused_on.center_x,
                self.focused_on.center_y,
            )
            heading += random.randrange(-5, 5)
            arrow = arcade.Sprite(
                "resources/Sprites/enemies/projectile.png",
                scale=1,
                center_x=self.center_x,
                center_y=self.center_y,
                angle=-heading,
            )
            arrow.time = 0
            set_sprite_motion(arrow, heading, 50)
            self.arrows.append(arrow)
            game.overParticles.append(arrow)
            arrow.update()
        self.bow.texture = self.bow.Attack_textures[anim]
        self.bow.Attack_animation.timetoupdate = self.bow.AttackAnimTimes[anim]

        self.bow.timer = 0

    def destroy(self, game):
        self.bow.remove_from_sprite_lists()
        self.bow = None

        for arrow in self.arrows:
            arrow.remove_from_sprite_lists()
        return super().destroy(game)

    def _serialize_extra_state(self) -> dict:
        bow_state = {
            "timer": getattr(self.bow, "timer", 0.0),
            "can_attack": getattr(self.bow, "canAttack", False),
            "angle": self.bow.angle,
            "anim_index": getattr(self.bow.Attack_animation, "index", 0),
            "anim_time": getattr(self.bow.Attack_animation, "time", 0.0),
        }
        arrows_state = []
        for arrow in self.arrows:
            arrows_state.append(
                {
                    "x": arrow.center_x,
                    "y": arrow.center_y,
                    "dx": getattr(arrow, "_motion_dx", 0.0),
                    "dy": getattr(arrow, "_motion_dy", 0.0),
                    "time": getattr(arrow, "time", 0.0),
                    "angle": arrow.angle,
                }
            )
        return {
            "bow": bow_state,
            "arrows": arrows_state,
        }

    def _apply_extra_state(self, game, extra_state: dict | None) -> None:
        if not extra_state:
            return
        bow_state = extra_state.get("bow", {})
        self.bow.timer = bow_state.get(
            "timer", getattr(self.bow, "timer", 0.0))
        self.bow.canAttack = bow_state.get(
            "can_attack", getattr(self.bow, "canAttack", False))
        self.bow.angle = bow_state.get("angle", self.bow.angle)
        self.bow.Attack_animation.index = bow_state.get(
            "anim_index", self.bow.Attack_animation.index)
        self.bow.Attack_animation.time = bow_state.get(
            "anim_time", self.bow.Attack_animation.time)
        if self.bow not in game.overParticles:
            game.overParticles.append(self.bow)

        self.arrows = arcade.SpriteList()
        arrow_texture = "resources/Sprites/enemies/projectile.png"
        for entry in extra_state.get("arrows", []):
            arrow = arcade.Sprite(
                arrow_texture,
                scale=1,
                center_x=entry.get("x", self.center_x),
                center_y=entry.get("y", self.center_y),
                angle=entry.get("angle", 0.0),
            )
            arrow._motion_dx = entry.get("dx", 0.0)
            arrow._motion_dy = entry.get("dy", 0.0)
            arrow.time = entry.get("time", 0.0)
            self.arrows.append(arrow)
            game.overParticles.append(arrow)
