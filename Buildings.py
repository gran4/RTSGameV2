import arcade
from arcade import math as arcade_math
from Components import *
from Player import *
from gui_compat import UIAnchorWidget
    
things = {"Bad Gifter":BadGifter, "Bad Reporter":BadReporter}

class BaseBuilding(arcade.Sprite):
    produces: dict[str, float] = {}
    def __init__(self, game, x:float, y:float, health:float, dmg:float, range:int, max_len:int, texture:str, scale=1):
        super().__init__(texture, center_x=x, center_y=y, scale=scale)

        self.game = game
        self.texture = arcade.load_texture(texture)
        self.center_x = x
        self.center_y = y
        self.path = False

        self.dmg = dmg
        self.health = health
        self.max_health = self.health
        self.health_bar = HealthBar(game, position = self.position)
        self.health_bar.fullness = self.health/self.max_health
        self.range = range
        
        self.list_of_people = []
        self.max_length = max_len

        self.check_timer = 0
        self.enemy = None
        self.fire = None
        self.fire_resistence = .9
        self.vars = dict(self.produces)
    def add(self, sprite):
        if len(self.list_of_people) == self.max_length:
            return True
        if sprite in self.game.People:
            self.game.People.remove(sprite)
        self.list_of_people.append(sprite)
        sprite.health_bar.visible = False
        sprite.remove_from_sprite_lists()
        sprite.in_building = True
        return False
    def remove(self):
        if len(self.list_of_people) == 0:
            return
        sprite = self.list_of_people[0]
        sprite.health_bar.visible = True
        sprite.in_building = False
        self.list_of_people.pop(0)
        return sprite
    def destroy(self, game, menu_destroy = False):
        if menu_destroy:
            while len(self.list_of_people) > 0:
                person = self.remove()
                game.People.append(person)
        else:
            game.population -= len(self.list_of_people)
            for person in self.list_of_people:
                person.health_bar.remove_from_sprite_lists
                person.remove_from_sprite_lists()
        if self is game.last:
            game.clear_uimanager()
            game.last = Bad_Cannoe(game, 10000000, 1000000)
            game.selection_rectangle.position = (-1000000, -1000000)
        game.BuildingChangeEnemySpawner(self.center_x, self.center_y, placing=-1, min_dist=150, max_dist=200)
        self.remove_from_sprite_lists()
        self.health_bar.remove_from_sprite_lists()

        if self.fire: self.fire.destroy(game)
        
        self.health = -100
    def on_destroy(self, source):
        self.destroy(source.game, source.menu_destroy)

    def clicked(self, game):
        game.clear_uimanager()
        if game.last == self:
            game.last = None
            return 
        game.last = self

        button = CustomUIFlatButton(game.Alphabet_Textures, text="Leave", width=140, height=50, x=0, y=50, text_offset_x = 16, text_offset_y=35, offset_x=75, offset_y=25)
        button.on_click = game.leave
        button.obj = self
        wrapper = UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
            child=button, align_x=-300, align_y=-200)
        game.uimanager.add(wrapper)
        game.extra_buttons.append(wrapper)

        button = CustomUIFlatButton(game.Alphabet_Textures, text="Print  Attrs", width=140, height=50, x=0, y=50, text_offset_x = 16, text_offset_y=35, offset_x=75, offset_y=25)
        button.on_click = game.print_attr
        button.obj = self
        wrapper = UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
            child=button, align_x=-100, align_y=-200)
        game.uimanager.add(wrapper)
        game.extra_buttons.append(wrapper)

        button = CustomUIFlatButton(game.Alphabet_Textures, text="Destroy", width=140, height=50, x=0, y=50, text_offset_x = 10, text_offset_y=35, offset_x=65, offset_y=25)
        button.on_click = game.destroy
        button.obj = self
        wrapper = UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
            child=button, align_x=100, align_y=-200)
        game.uimanager.add(wrapper)
        game.extra_buttons.append(wrapper)

        self.clicked_override(game)
    def clicked_override(self, game):
        pass
    def update(self, delta_time, game):
        for resource, amount in self.vars.items():
            vars(game)[resource] += amount*delta_time*vars(game)[resource+"_multiplier"]/self.max_length*len(self.list_of_people)*game.overall_multiplier
        self.on_update(delta_time, game)
    def on_update(self, delta_time, game):
        if self.health <= 0:
            self.destroy(game)
        self.health_bar.fullness = self.health/self.max_health

        if self.enemy:
            if arcade.get_distance_between_sprites(self, self.enemy) < self.range:
                self.on_attack(delta_time, game)
            else:
                self.enemy = None
        else:
            self.check_timer += delta_time
            if self.check_timer < 1:
                return
            self.check_timer -= 1
            enemy, distance = get_closest_sprite(self.position, game.Enemies)
            if enemy and distance <= self.range:
                self.enemy = enemy
    def on_attack(self, delta_time, game):
        if not self.enemy:
            return
        self.enemy.health -= self.dmg
        if self.enemy.health <= 0:
            enemy = self.enemy
            self.enemy = None
            if enemy in game.Enemies:
                game.Enemies.remove(enemy)
            enemy.destroy(game)
    def save(self, game):
        if self.enemy:
            self.enemy = game.Enemies.index(self.enemy)
        self.health_bar.remove_from_sprite_lists()
    def load(self, game):
        if self.enemy:
            self.enemy = game.Enemies[self.enemy]
        game.health_bars.append(self.health_bar._background_box)
        game.health_bars.append(self.health_bar._full_box)
class UNbuiltBuilding(BaseBuilding):
    def __init__(self, game, x: float, y: float, max_len: int=0, time: float=0, building: str="", scale=1):
        super().__init__(game, x, y, 10, 0, 0, max_len, "resources/Sprites/IN Progress.png", scale)
        self.time = time
        if self.max_length < 1:
            self.max_length
        self.building = building
    def on_build(self, game):
        while len(self.list_of_people) > 0:
            person = self.remove()
            game.People.append(person)
        if self is game.last:
            game.clear_uimanager()
            game.last = Bad_Cannoe(game, 10000000, 1000000)
            game.selection_rectangle.position = (-1000000, -1000000)
        self.remove_from_sprite_lists()
        self.health_bar.remove_from_sprite_lists()

        if self.fire:
            self.fire.destroy(game)

        build = game.objects[self.building](game, self.center_x, self.center_y)
        build.fire = self.fire
        if self.fire: self.fire.obj = build
        self.fire = None
        game.Buildings.append(build)
    def update(self, delta_time, game):
        self.time -= delta_time*len(self.list_of_people)
        self.health_bar.fullness = self.health/self.max_health
        if self.time <= 0:
            self.on_build(game)
    def clicked_override(self, game):
        game.uimanager.remove(game.extra_buttons[-1])
        game.extra_buttons.pop(-1)
        button = CustomUIFlatButton(game.Alphabet_Textures, text="Destroy", width=140, height=50, x=0, y=50, text_offset_x = 16, text_offset_y=35, offset_x=75, offset_y=25)
        button.on_click = game.clean_destroy
        button.obj = self
        wrapper = UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
            child=button, align_x=100, align_y=-200)
        game.extra_buttons.append(wrapper)

        game.uimanager.add(wrapper)

class ResearchShop(BaseBuilding):
    produces = {"science": .04}
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 10, 0, 0, 1, "resources/Sprites/conjurerater.png")
        self.Updates = False
class Lab(BaseBuilding):
    produces = {"science": .1}
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 10, 0, 0, 1, "resources/Sprites/Lab.png")
        self.Updates = False

class WorkShop(BaseBuilding):
    produces = {"toys": 1}
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 10, 0, 0, 1, "resources/Sprites/WorkShop.png")
class Factory(BaseBuilding):
    produces = {"toys": 2}
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 10, 0, 0, 1, "resources/Sprites/Factory.png", scale=.5)


class Hospital(BaseBuilding):
    produces = {}
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 10, 0, 0, 1, "resources/Sprites/Hospital.png")
    def update(self, delta_time, game):
        for person in self.list_of_people:
            if person.health >= 1:
                continue
            person.health += .01*delta_time     
        self.on_update(delta_time, game)

class PebbleSite(BaseBuilding):
    produces = {"stone": .1}
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 20, 0, 0, 1, "resources/Sprites/Pebble Site.png")
        self.Updates = False
class Quary(BaseBuilding):
    produces = {"stone": .25}
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 20, 0, 0, 1, "resources/Sprites/Quary.png")
        self.Updates = False
class Lumbermill(BaseBuilding):
    produces = {"wood": .25}
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 10, 0, 0, 1, "resources/Sprites/tree_farm.png")
        self.Updates = False
class BlackSmith(BaseBuilding):
    produces = {}
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 10, 0, 0, 1, "resources/Sprites/BlackSmith.png")
        self.Updates = True

        self.required = {"wood":.01, "stone":.002}
        self.reward = {"metal":.025}
    def update(self, delta_time, game):
        if len(self.list_of_people) < 1:
            return
        game_vars = vars(game)
        lacks = []
        for key, val in self.required.items():
            if game_vars[key] < val:
                lacks.append(key)
        if lacks: 
            game.lacks = lacks
            return

        for key, val in self.required.items():
            game_vars[key] -= val
        for key, val in self.reward.items():
            game_vars[key] += val
        

class SnowTower(BaseBuilding):
    produces = {}
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 20, .5, 400, 1, "resources/Sprites/SnowTower.png")
        self.Updates = False
        self.canAttack = True
        self.timer = 0
        self.WaitToAttack = 1

        self.snowballs = arcade.SpriteList()
        self.focused_on = None
    def update(self, delta_time, game):
        if self.health <= 0:
            self.destroy(game)
            return 

        self.health_bar.fullness = self.health/self.max_health

        target, distance = get_closest_sprite(self.position, game.Enemies)
        if target and distance <= self.range:
            self.focused_on = target
        else:
            self.focused_on = None

        
        for snowball in list(self.snowballs):
            advance_sprite(snowball, delta_time)
            snowball.update()
            snowball.time += delta_time
            if snowball.time > 15:
                snowball.remove_from_sprite_lists()
                continue
            if not self.focused_on:
                snowball.remove_from_sprite_lists()
                continue
            if arcade_math.get_distance(snowball.center_x, snowball.center_y, self.focused_on.center_x, self.focused_on.center_y) < 25:
                self.focused_on.health -= self.dmg * random.random() * random.random() * 4
                snowball.remove_from_sprite_lists()
                if self.focused_on.health <= 0:
                    self.focused_on = None

        self.timer += delta_time
        if self.timer < self.WaitToAttack or not self.focused_on:
            return
        self.timer -= self.WaitToAttack
        self.canAttack = True
        self.on_attack(delta_time, game)
    def on_attack(self, delta_time, game):     
        if not self.canAttack: 
            return
        heading = heading_towards(
            self.center_x,
            self.center_y,
            self.focused_on.center_x,
            self.focused_on.center_y,
        )
        heading += random.uniform(-5, 5)
        snowball = arcade.Sprite(
            "resources/Sprites/Snowball.png",
            scale=1,
            center_x=self.center_x,
            center_y=self.center_y,
            angle=-heading,
        )
        snowball.time = 0
        set_sprite_motion(snowball, heading, 50)
        self.snowballs.append(snowball)
        game.overParticles.append(snowball)
        snowball.update()
        self.canAttack = False
        if self.focused_on and self.focused_on.health <= 0:
            self.focused_on = None


class RaindeerFarm(BaseBuilding):
    produces = {"food": 1.4}
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 10, 0, 0, 1, "resources/Sprites/Pasture.png")
        self.Updates = False
class Farm(BaseBuilding):
    produces = {"food": 1.6}
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 10, 0, 0, 1, "resources/Sprites/Observatory.jpeg")
        self.set_hit_box(((-25.0, -25.0), (25.0, -25.0), (25.0, 25.0), (-25.0, 25.0)))

        self.AnimationPlayer = AnimationPlayer(1)
        self.textures = load_texture_grid("resources/Sprites/Farm Pixilart Sprite Sheet.png", 50, 50, 50, 2)
        self.texture = self.textures[0]
    def update(self, delta_time, game):
        super().update()
        if len(self.list_of_people) > 0:
            anim = self.AnimationPlayer.updateAnim(delta_time, len(self.textures))
            if anim is not None:
                self.texture = self.textures[anim]
        self.on_update(delta_time, game)
    def remove(self):
        if len(self.list_of_people) == 0:
            return
        elif len(self.list_of_people) == 1:
            self.texture = self.textures[0]
            self.AnimationPlayer = AnimationPlayer(1)
        sprite = self.list_of_people[0]
        self.list_of_people.pop(0)
        return sprite
class FireStation(BaseBuilding):
    produces = {}
    def __init__(self, game, x: float, y: float):
        super().__init__(game, x, y, .4, 50, 400, 1, "resources/Sprites/Fire Station.png", scale=1)
        self.timer = 0
    def update(self, delta_time, game):
        if self.health <= 0:
            self.destroy(game)
        self.timer += delta_time
        if self.timer > 1:
            self.on_attack(delta_time, game)
            self.timer -= 1
    def on_attack(self, delta_time, game):
        for sprite in sprites_in_range(self.range, self.position, game.Buildings):
            if not sprite.fire:
                continue
            sprite.fire.strength -= self.dmg*delta_time
            if sprite.fire.strength > 0:
                continue
            sprite.fire.destroy(game)
            sprite.fire = None


class Path(BaseBuilding):
    produces = {}
    def __init__(self, game, x:float, y:float, health, max_len, crossing_time, image):
        super().__init__(game, x, y, health, 0, 0, max_len, image)
        self.Updates = False
        self.crossing_time = crossing_time


        x = int(self.center_x/50)
        y = int(self.center_y/50)
        self.before = game.graph[x][y]
        game.graph[x][y] = 0

        self.max_length = 0
        self.path = True
    def destroy(self, game, menu_destroy=False):
        x = int(self.center_x/50)
        y = int(self.center_y/50)
        game.graph[x][y] = self.before
        super().destroy(game, menu_destroy)
class Pass(Path):
    produces = {}
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 10, 10, 2, "resources/Sprites/Road.png")
        self.Updates = False
        self.prev = game.graph[round(self.center_x/50)][round(self.center_y/50)]
        game.graph[round(self.center_x/50)][round(self.center_y/50)] = 0
    def destroy(self, game, menu_destroy=False):
        game.graph[round(self.center_x/50)][round(self.center_y/50)] = self.prev
        return super().destroy(game, menu_destroy)


class Housing(BaseBuilding):
    produces = {}
    def __init__(self, game, x:float, y:float, health, sprite, people_amount):
        super().__init__(game, x, y, health, 0, 0, people_amount, sprite)
        self.people_amount = people_amount

        self.max_length = people_amount
        game.max_pop += self.people_amount
#Igloo?
class Igloo(Housing):
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 10, "resources/Sprites/Igloo.png", 1)
class Dormatory(Housing):
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 10, "resources/Sprites/Hut.png", 4)


class FoodDepot(BaseBuilding):
    produces = {}
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 10, 0, 0, 1, "resources/Sprites/FoodDepot.png")
        self.food_storage = 75

        game.food_storage += self.food_storage
    def destroy(self, game, menu_destroy=False):
        game.food_storage -= self.food_storage
        super().destroy(game, menu_destroy)

class StoneWall(BaseBuilding):
    produces = {}
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 100, 0, 0, 1, "resources/Sprites/StoneWall.png")
class MetalWall(BaseBuilding):
    produces = {}
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 1000, 0, 0, 1, "resources/Sprites/MetalWall.png")


class MaterialDepot(BaseBuilding):
    produces = {}
    def __init__(self, game, x:float, y:float):
        self.storage = 10
        super().__init__(game, x, y, 10, 0, 0, 1, "resources/Sprites/MaterialDepot.png")

        game.mcsStorage += self.storage
    def destroy(self, game, menu_destroy=False):
        game.mcsStorage -= self.storage
        super().destroy(game, menu_destroy)
class BetterMaterialDepot(BaseBuilding):
    produces = {}
    def __init__(self, game, x:float, y:float):
        self.storage = 20
        super().__init__(game, x, y, 10, 0, 0, 1, "resources/Sprites/MaterialDepot.png")

        game.mcsStorage += self.storage
    def destroy(self, game, menu_destroy=False):
        game.mcsStorage -= self.storage
        super().destroy(game, menu_destroy)

class Encampment(BaseBuilding):
    produces = {}
    def __init__(self, game, x:float, y:float):
        super().__init__(game, x, y, 10, 0, 0, 1, "resources/Sprites/Training Ground.png")
        self.trainable = ["Bad Gifter", "Bad Reporter"]
    def add(self, sprite):
        if len(self.list_of_people) == self.max_length:
            return True
        advancement = getattr(sprite, "advancement", None)
        if advancement and advancement not in self.trainable:
            return True

        if not hasattr(sprite, "advancement"):
            sprite.advancement = None
        if not hasattr(sprite, "trainingtime"):
            sprite.trainingtime = 0

        if sprite in self.game.People:
            self.game.People.remove(sprite)
        self.list_of_people.append(sprite)
        sprite.health_bar.visible = False
        sprite.remove_from_sprite_lists()
        sprite.in_building = True
        return False
    def remove(self):
        if len(self.list_of_people) == 0:
            return
        person = None
        for p in self.list_of_people:
            if p.advancement is not None:
                person = p
                break
        if person is None:
            person = self.list_of_people[0]
        self.list_of_people.remove(person)
        person.health_bar.visible = True
        person.in_building = False
        person.position = self.position
        return person
    def clicked_override(self, game):
        button = CustomUIFlatButton(game.Alphabet_Textures, text="Train", width=140, height=50, x=0, y=50, text_offset_x = 16, text_offset_y=35, offset_x=75, offset_y=25)
        button.on_click = game.training_menu
        button.obj = self
        wrapper = UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
                    child=button, align_x=300, align_y=-200)
        button.building = self
        game.uimanager.add(wrapper)
        game.extra_buttons.append(wrapper)
    def update(self, delta_time, game):
        for person in self.list_of_people:
            if person.advancement is None:
                continue
            person.trainingtime += delta_time*game.training_speed_multiplier
            if person.trainingtime < trainingtimes[person.advancement]:
                continue
            self.list_of_people.remove(person)

            personv2 = things[person.advancement](game, self.center_x, self.center_y)
            personv2.trained = True
            game.People.append(personv2)

            person.destroy(game)
            game.population += 1
        
