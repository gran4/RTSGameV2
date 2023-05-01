import arcade
from math import floor
import random, time
from Components import *

"""16, 15, 10, """
class Fire(arcade.Sprite):
    def __init__(self, game, x:float, y:float, strength):
        super().__init__("resources/Sprites/tree_farm.png", center_x=x, center_y=y, scale=1, hit_box_algorithm="None")
        
        self.textures = arcade.load_spritesheet("resources/Sprites/Fire Pixilart Sprite Sheet.png", 50, 50, 8, 8)
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
            game.selection_rectangle.position = (-1000000, -1000000)
            self.remove_from_sprite_lists()
        elif random.random()*self.strength > .98:
            reach = round(self.strength/2)
            if reach == 0:
                return
            x = random.randrange(-reach, reach)*50
            y = random.randrange(-reach, reach)*50
            buildings = arcade.get_sprites_at_point((x+obj.center_x, y+obj.center_y), game.Buildings)
            if len(buildings) > 0:
                try:
                    buildings[0].fire
                except:
                    game.LightOnFire(buildings[0], self.strength/5)
            boats = arcade.get_sprites_at_point((x, y), game.Boats)
            if len(boats) > 0:
                try:
                    boats[0].fire
                except:
                    game.LightOnFire(boats[0], self.strength/5)
        self.fireUpdate += delta_time
        if self.fireUpdate >= 1:
            self.fireUpdate -= 1
            if self.strength > 8:
                self.strength = 7.9
            self.texture = self.textures[floor(self.strength)]
    def destroy(self, game):
        self.remove_from_sprite_lists()
        del self.obj.fire
    def save(self, game):
        pass
    def load(self, game):
        pass

class BaseBoat(arcade.Sprite):
    def __init__(self, file_name, game, x:float, y:float, health:float, damage:float, range:int, capacity:int, scale:int=1):
        super().__init__(file_name, center_x=x, center_y=y, scale=scale, hit_box_algorithm="None")
        self.texture = arcade.load_texture(file_name)
        self.center_x = x
        self.center_y = y

        self.damage = damage
        self.health = health
        self.max_health = health
        self.health_bar = HealthBar(game, position = self.position)
        self.health_bar.fullness = self.health/self.max_health
        self.range = range

        self.capacity = capacity
        self.list = []
        self.path = []
        self.movelist = [2]

        self.timer = 0
        
    def add(self, sprite):
        if len(self.list) == self.capacity:
            return True
        sprite.remove_from_sprite_lists()
        sprite.health_bar.visible = False
        self.list.append(sprite)
        return False
    def remove(self):
        if len(self.list) == 0:
            return None
        sprite = self.list[0]
        self.list.pop(0)
        sprite.position = self.position
        sprite.health_bar.visible = True
        return sprite
    def update(self, game, delta_time):
        self.timer += delta_time
        self.health_bar.fullness = self.health/self.max_health
        if len(self.path) > 0:
            rot = rotation(self.center_x, self.center_y, self.path[0][0], self.path[0][1], angle = self.angle+0, max_turn = 360*delta_time)-0
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
        button = CustomUIFlatButton(game.Alphabet_Textures, text="Move", width=140, height=50, x=0, y=50, text_offset_x = 24, text_offset_y=35, offset_x=75, offset_y=25)
        button.on_click = game.Move
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="left", anchor_y="bottom",
            child=button, align_x=0, align_y=0)
        game.uimanager.add(wrapper)
        game.extra_buttons.append(wrapper)

        button = CustomUIFlatButton(game.Alphabet_Textures, text="Leave", width=140, height=50, x=0, y=50, text_offset_x = 16, text_offset_y=35, offset_x=75, offset_y=25)
        button.on_click = game.leave
        button.obj = self
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="left", anchor_y="bottom",
            child=button, align_x=150, align_y=0)
        game.uimanager.add(wrapper)
        game.extra_buttons.append(wrapper)
        
        button = CustomUIFlatButton(game.Alphabet_Textures, text="Destoy", width=140, height=50, scale=.3, x=0, y=50, text_offset_x = 16, text_offset_y=35, offset_x=75, offset_y=25)
        button.on_click = game.leave
        button.obj = self
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="left", anchor_y="bottom",
            child=button, align_x=300, align_y=0)
        game.uimanager.add(wrapper)
        game.extra_buttons.append(wrapper)
        
        self.clicked_override(game)
    def clicked_override(self, game):
        pass
    def destroy(self, game):
        for person in self.list:
            person.health_bar.remove_from_sprite_lists()
        self.health_bar.remove_from_sprite_lists()
        self.remove_from_sprite_lists()
        game.population -= len(self.list)
    def save(self, game):
        self.health_bar.remove_from_sprite_lists()
    def load(self, game):
        game.health_bars.append(self.health_bar._background_box)
        game.health_bars.append(self.health_bar._full_box)
class Bad_Cannoe(BaseBoat):
    def __init__(self, game, x:float, y:float):
        super().__init__("resources/Sprites/Arrow.png", game, x, y, 10, 0, 0, 2, scale=.5)
class Cannoe(BaseBoat):
    def __init__(self, game, x:float, y:float):
        super().__init__("resources/Sprites/Arrow.png", game, x, y, 10, 0, 0, 2)

class VikingLongShip(BaseBoat):
    def __init__(self, game, x:float, y:float):
        super().__init__("resources/Sprites/Arrow.png", game, x, y, 20, 0, 0, 2, scale=0.78125)
        self.textures = arcade.load_spritesheet("resources/Sprites/Viking Ship/sprPlayer_strip16.png", 64, 64, 16, 16, margin=0)
        self.texture = self.textures[0]

        self.rot = 0


    def update(self, game, delta_time):
        self.health_bar.fullness = self.health/self.max_health
        self.timer += delta_time
        if len(self.path) > 0:
            rot = rotation(self.center_x, self.center_y, self.path[0][0], self.path[0][1], angle = self.rot+90, max_turn = 360*delta_time)-90
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
    def __init__(self, game, x:float, y:float):
        super().__init__("resources/Sprites/Arrow.png", game, x, y, 10, 0, 0, 2)


class Player(arcade.Sprite):
    def __init__(self, center_x: float = 0, center_y: float = 0):
        super().__init__(None, scale=2, center_x=center_x, center_y=center_y)
        textures = arcade.load_spritesheet("resources/Sprites/Player Sprite Sheet.png", 24, 33, 4, 16)
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
            
        return super().on_update(delta_time)
#odd movement
class Person(arcade.Sprite):
    def __init__(self, game, x:float, y:float, scale = 1):
        super().__init__(center_x=x, center_y=y, scale=scale)
        textures = arcade.load_spritesheet("resources/Sprites/Elf Sprite Sheet.png", 24, 33, 4, 16)
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
        self.hit_box = self.texture.hit_box_points

        self.health = 100
        self.max_health = 100
        self.health_bar = HealthBar(game, position = self.position)
 
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

    def clicked(self, game):
        game.clear_uimanager()
        if game.last == self:
            game.last = None
            return 
        game.last = self

        button = CustomUIFlatButton(game.Alphabet_Textures, text="Move", width=140, height=50, x=0, y=50, text_offset_x = 16, text_offset_y=35, offset_x=75, offset_y=25)
        
        button.on_click = game.Move
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="left", anchor_y="bottom",
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

        self.health_bar.fullness = self.health/self.max_health
    def update_movement(self, game):
        if self.path != []:
            if self.center_x<self.path[0][0]:
                self.key = "D"
            elif self.center_x>self.path[0][0]:
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
        if not game.graph[round(self.path[0][0]/50)][round(self.path[0][1]/50)] in self.movelist and not arcade.get_sprites_at_point(self.path[0], game.Buildings):
            self.path = []
            return
        self.position = self.path.pop(0)
        self.health_bar.position = self.position


        buildings_at_point = arcade.get_sprites_at_point(self.position, game.Buildings)
        if len(buildings_at_point) > 0:
            isMaxPeople = buildings_at_point[0].add(self)
        ships_at_point = arcade.get_sprites_at_point(self.position, game.Boats)
        if len(ships_at_point) > 0:
            isMaxPeople = ships_at_point[0].add(self)


        wood_at_point = arcade.get_sprites_at_point(self.position, game.Trees)
        if len(wood_at_point) > 0:
            self.var = "wood"
            self.skill = "lumbering_skill"
            self.amount = .3
            return

        food_at_point = arcade.get_sprites_at_point(self.position, game.BerryBushes)
        if len(food_at_point) > 0:
            self.var = "food"
            self.skill = "farming_skill"
            self.amount = 1.25
            return
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

    
    def destroy(self, game):
        self.remove_from_sprite_lists()
        self.health = -100
        game.population -= 1
    def save(self, game):
        self.health_bar.remove_from_sprite_lists()
    def load(self, game):
        game.health_bars.append(self.health_bar._background_box)
        game.health_bars.append(self.health_bar._full_box)
class People_that_attack(Person):
    def __init__(self, game, filename, x, y, damage, range, health, scale=1):
        super().__init__(game, x, y, scale=scale)
        self.texture = arcade.load_texture(filename)
        self.damage = damage
        self.range = range
        self.health = health

        self.check = True
        self.focused_on = None
    def destroy(self, game):
        self.remove_from_sprite_lists()
        self.health = -100
    def update(self, game, delta_time):
        #NOTE: Override
        #update anims here
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
        button = CustomUIFlatButton(game.Alphabet_Textures, text=self.state2, width=140, height=50, x=0, y=50, text_offset_x = 16, text_offset_y=35, offset_x=75, offset_y=25)
        button.on_click = game.person_switch
        button.obj = self
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="left", anchor_y="bottom",
                    child=button, align_x=150, align_y=0)
        game.extra_buttons.append(wrapper)
        game.uimanager.add(wrapper)
    def save(self, game):
        if self.focused_on: 
            self.focused_on = game.Enemies.index(self.focused_on)
        self.health_bar.remove_from_sprite_lists()
    def load(self, game):
        if self.focused_on:
            self.focused_on = game.Enemies[self.focused_on]  
        game.health_bars.append(self.health_bar._background_box)
        game.health_bars.append(self.health_bar._full_box)
    def state_update(self, game, state):
        pass
class BadGifter(People_that_attack):
    def __init__(self, game, x, y):
        super().__init__(game, "resources/Sprites/enemy.png", x, y, 10, 500, 100, scale=1.5)
        self.set_up(game, x, y)
    def set_up(self, game, x, y):
        self.building_bias = 1
        self.people_bias = .3
        

        textures = arcade.load_spritesheet("resources/Sprites/Elf Sprite Sheet.png", 24, 33, 4, 16)
        self._width = 24
        self._height = 33

        self.texture = textures[0]
        self.S_Texture = textures[:4]
        self.W_Texture = textures[4:8]
        self.D_Texture = textures[8:12]
        self.A_Texture = textures[12:16]
        self.index = 0
        self.key = "S"
        self.coal = arcade.Sprite("resources/Sprites/Coal.png", center_x = x, center_y = y, scale=2)

        self.timer = 0
        self.timer2 = 0

        self.gifts = arcade.SpriteList()
        self.state = "Idle"
        self.state2 = "Patrol"

        game.overParticles.append(self.coal)
    def destroy(self, game):
        self.remove_from_sprite_lists()
        self.coal.remove_from_sprite_lists()
        [coal.remove_from_sprite_lists() for coal in self.gifts]
        self.health = -100
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
            gift.forward(speed=delta_time*50)
            gift.update()
            gift.time += delta_time
            if gift.time > 15:
                gift.remove_from_sprite_lists()
            elif self.focused_on is None:
                pass
            elif arcade.get_distance(gift.center_x, gift.center_y, self.focused_on.center_x, self.focused_on.center_y) < 25:
                self.focused_on.health -= self.damage*delta_time*random.random()*random.random()*4
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
            
        angle = rotation(self.center_x, self.center_y, self.focused_on.center_x, self.focused_on.center_y, max_turn=360)+random.randrange(-5, 5)
        coal = arcade.Sprite("resources/Sprites/Coal.png", scale=1, center_x = self.center_x, center_y = self.center_y, angle = angle)
        coal.time = 0
        self.gifts.append(coal)
        game.overParticles.append(coal)
        coal.forward()
        coal.update()
        self.timer = 0
    def state_update(self, game, state):
        
        if state == "Work":
            self.coal.remove_from_sprite_lists()
        elif state == "Patrol":
            if self.key == "S":
                game.underParticals.append(self.coal)
            else: game.overParticles.append(self.coal)

    def save(self, game):
        self.coal.remove_from_sprite_lists()
        
        self.gifts2 = []
        for coal in self.gifts:
            coal.remove_from_sprite_lists()
            self.gifts2.append(coal)
        self.gifts = self.gifts2
        return super().save(game)
    def load(self, game):
        self.gifts2 = arcade.SpriteList()
        for coal in self.gifts: 
            self.gifts2.append(coal)
            game.overParticles.append(coal)
        self.gifts = self.gifts2
        game.overParticles.append(self.coal)
        
        return super().load(game)
class BadReporter(People_that_attack):
    def __init__(self, game, x, y):
        super().__init__(game, "resources/Sprites/enemy.png", x, y, 25, 500, 100, scale=1.5)
        self.set_up(game, x, y)
    def set_up(self, game, x, y):
        self.building_bias = 1
        self.people_bias = .3
        

        textures = arcade.load_spritesheet("resources/Sprites/Elf Sprite Sheet.png", 24, 33, 4, 16)
        self._width = 24
        self._height = 33

        self.texture = textures[0]
        self.S_Texture = textures[:4]
        self.W_Texture = textures[4:8]
        self.D_Texture = textures[8:12]
        self.A_Texture = textures[12:16]
        self.index = 0
        self.key = "S"
        self.paper = arcade.Sprite("resources/Sprites/Paper.png", center_x = x, center_y = y)

        self.timer = 0
        self.timer2 = 0

        self.gifts = arcade.SpriteList()
        self.state = "Idle"
        self.state2 = "Patrol"

        game.overParticles.append(self.paper)
    def destroy(self, game):
        self.remove_from_sprite_lists()
        self.paper.remove_from_sprite_lists()
        [coal.remove_from_sprite_lists() for coal in self.gifts]
        self.health = -100
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
            gift.forward(speed=delta_time*50)
            gift.update()
            gift.time += delta_time
            if gift.time > 15:
                gift.remove_from_sprite_lists()
            elif self.focused_on is None:
                pass
            elif arcade.get_distance(gift.center_x, gift.center_y, self.focused_on.center_x, self.focused_on.center_y) < 25:
                self.focused_on.health -= self.damage*delta_time*random.random()*random.random()*4
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
            
        angle = rotation(self.center_x, self.center_y, self.focused_on.center_x, self.focused_on.center_y, max_turn=360)+random.randrange(-5, 5)
        coal = arcade.Sprite("resources/Sprites/Paper.png", scale=1, center_x = self.center_x, center_y = self.center_y, angle = angle)
        coal.time = 0
        self.gifts.append(coal)
        game.overParticles.append(coal)
        coal.forward()
        coal.update()
        self.timer = 0
    def state_update(self, game, state):
        
        if state == "Work":
            self.paper.remove_from_sprite_lists()
        elif state == "Patrol":
            if self.key == "S":
                game.underParticals.append(self.paper)
            else: game.overParticles.append(self.paper)


    def save(self, game):
        self.paper.remove_from_sprite_lists()
        
        self.gifts2 = []
        for paper in self.gifts:
            paper.remove_from_sprite_lists()
            self.gifts2.append(paper)
        self.gifts = self.gifts2
        return super().save(game)
    def load(self, game):
        self.gifts2 = arcade.SpriteList()
        for paper in self.gifts: 
            self.gifts2.append(paper)
            game.overParticles.append(paper)
        self.gifts = self.gifts2
        game.overParticles.append(self.paper)
        