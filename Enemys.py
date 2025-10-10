import arcade, random
from Components import *
"""
OBJECT x

x2 = type(x).__new__(type(x))
x2 

use unlocked to expand enemies and ui
"""


class BaseEnemy(arcade.Sprite):
    def __init__(self, file_name:str, x:float, y:float, health:float, damage:float, range:int, scale:float=1):
        super().__init__(file_name, center_x=x, center_y=y, scale=scale)
        self.texture = arcade.load_texture(file_name)
        self.center_x = x
        self.center_y = y
        self.hit_box = self.texture.hit_box_points

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
        self.next_time = 1

    def destroy(self, game):
        self.remove_from_sprite_lists()
        self.health = -100
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
    #NOTE: over ride the function
    def update(self, game, delta_time):
        if self.health <= 0:
            self.destroy(game)
            return 
        self.on_update(game, delta_time)
        self.update_movement(game, delta_time)
    #NOTE: Always call on_update in update
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
            #self.next_time = difficulty[game["map"][round(self.center_x/50)][round(self.center_y/50)]]
    def on_attack(self, game, delta_time):
        self.focused_on.health -= self.damage*delta_time*random.random()*random.random()*4
    def On_Focused_on(self):
        pass
    
    def save(self, game):
        if not self.focused_on:
            return
        if self.focused_on.__module__ == "Buildings":
            index = game.Buildings.index(self.focused_on)
            sprite_list_name = "Buildings"
        elif self.focused_on.__module__ == "Player":
            try:
                #if not boat except
                self.focused_on.capacity
                index = game.Boats.index(self.focused_on)
                sprite_list_name = "Boats"
            except:
                index = game.People.index(self.focused_on)
                sprite_list_name = "People"
        return (sprite_list_name, index)
    def load(self, game):
        if self.focused_on:
            self.focused_on = game[self.focused_on[0]][self.focused_on[1]]

class Child(BaseEnemy):
    def __init__(self, game, x, y, difficulty=1):
        super().__init__("resources/Sprites/enemy.png", x, y, 5*difficulty, 10*difficulty, 5, scale=1)

        self.building_bias = 1
        self.people_bias = .3
        self.boat_bias = 1

        self.movelist = [0, 2]
        
        self.front_texture = arcade.load_texture("resources/Sprites/Child Front.png")
        self.back_texture = arcade.load_texture("resources/Sprites/Child Back.png")
        self.left_texture = arcade.load_texture("resources/Sprites/Child Left.png")
        self.right_texture = arcade.load_texture("resources/Sprites/Child Left.png", flipped_vertically=True)

        self.texture = self.front_texture

    def update(self, game, delta_time):
        if self.health <= 0:
            self.destroy(game)
            return 
        self.on_update(game, delta_time)
    def update_movement(self, game, delta_time):
        self.path_timer += delta_time
        if self.path_timer < self.next_time:
            return
        pos = self.get_path()
        if pos is not None:
            self.position = pos
        self.path_timer -= self.next_time

        prev_pos = self.position
        super().update_movement(game, delta_time)
        if prev_pos[0] < self.position[0]:
            self.texture = self.back_texture
        elif prev_pos[0] > self.position[0]:
            self.texture = self.front_texture
        elif prev_pos[1] < self.position[1]:
            self.texture = self.right_texture
        elif prev_pos[1] > self.position[1]:
            self.texture = self.left_texture

class Enemy_Swordsman(BaseEnemy):
    def __init__(self, x: float, y: float, difficulty = 1):
        super().__init__("resources/Sprites/NightBorneWarrior/NightBorne.png", x, y, 10*difficulty, 5*difficulty, 40, scale=1)
        self.textures = load_texture_grid("resources/Sprites/NightBorneWarrior/NightBorne.png", 80, 80, 22, 111, margin = 0)
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
        super().__init__("resources/Sprites/enemy.png", x, y, 5*difficulty, 10*difficulty, 500, scale=1)
        self.texture = arcade.load_texture("resources/Sprites/enemy.png", flipped_horizontally=True)

        self.building_bias = 1
        self.people_bias = .3
        self.boat_bias = 1

        self.movelist = [0]

        self.bow = arcade.Sprite(center_x=self.center_x, center_y=self.center_y, image_width=50, image_height=50)#Entity()
        self.bow.Attack_animation = AnimationPlayer(.1)
        self.bow.Attack_textures = load_texture_grid("resources/Sprites/Long Bow Pixilart Sprite Sheet.png", 50, 50, 50, 9)
        self.bow.texture = self.bow.Attack_textures[0]
        self.bow.AttackAnimTimes = [.25, .125, .125, .125, .2, .1, .05, .025, .025]
        self.bow.WaitToAttack = .2
        self.bow.timer = 0
        self.bow.canAttack = False

        self.arrows = arcade.SpriteList()#[]
        self.state = "Idle"

        self.front_texture = arcade.load_texture("resources/Sprites/Child Front.png")
        self.back_texture = arcade.load_texture("resources/Sprites/Child Back.png")
        self.left_texture = arcade.load_texture("resources/Sprites/Child Left.png")
        self.right_texture = arcade.load_texture("resources/Sprites/Child Left.png", flipped_vertically=True)
        self.texture = self.front_texture

        self.pull_back_sound = None
        game.overParticles.append(self.bow)
    def update(self, game, delta_time):
        if self.health <= 0:
            self.destroy(game)
            return 
        self.on_update(game, delta_time)

        if self.focused_on:
            self.bow.angle = rotation(self.center_x, self.center_y, self.focused_on.center_x, self.focused_on.center_y, angle = self.bow.angle-90)+90

        self.bow.center_x = self.center_x
        self.bow.center_y = self.center_y

        self.update_movement(game, delta_time)
        for arrow in self.arrows:
            arrow.forward(speed=delta_time*50)
            arrow.update()

            arrow.time += delta_time
            if arrow.time > 15:
                arrow.remove_from_sprite_lists()
            elif not self.focused_on:
                break
            elif arcade.get_distance(arrow.center_x, arrow.center_y, self.focused_on.center_x, self.focused_on.center_y) < 25:
                self.hit = True
                arrow.hit_sound = SOUND("resources/sound_effects/arrow-impact.wav", .25, get_dist(self.position, game.player.position))
                arrow.hit_sound._timer.active = False
                arrow.visible = False
                
            if arrow.hit:
                arrow.destory_timer += delta_time
                if arrow.destroy_timer > .5:
                    self.focused_on.health -= self.damage*random.random()*random.random()*4
                    arrow.remove_from_sprite_lists()
                    continue
                arrow.hit_sound._timer.set_time(arrow.hit_sound._timer.get_time()+.5)
            #else:
            #    arrow.pull_back_sound._timer.set_time(arrow.pull_back_sound._timer.get_time()+delta_time)

        self.bow.timer += delta_time
        if self.bow.timer < self.bow.WaitToAttack:
            return
        self.bow.timer -= self.bow.WaitToAttack
        self.bow.canAttack = True
    def update_movement(self, game, delta_time):
        self.path_timer += delta_time
        if self.path_timer < self.next_time:
            return
        pos = self.get_path()
        if pos is not None:
            self.position = pos
        self.path_timer -= self.next_time

        prev_pos = self.position
        super().update_movement(game, delta_time)
        if prev_pos[0] < self.position[0]:
            self.texture = self.back_texture
        elif prev_pos[0] > self.position[0]:
            self.texture = self.front_texture
        elif prev_pos[1] < self.position[1]:
            self.texture = self.right_texture
        elif prev_pos[1] > self.position[1]:
            self.texture = self.left_texture

    def on_attack(self, game, delta_time):     
        if not self.bow.canAttack: 
            return

        if not self.pull_back_sound:
            self.pull_back_sound = SOUND("resources/sound_effects/Arrow Shoot.wav", 1, get_dist(self.position, game.player.position))
            self.pull_back_sound._timer.active = False
        self.pull_back_sound._timer.set_time(self.pull_back_sound._timer.get_time()+delta_time*.5)
        anim = self.bow.Attack_animation.updateAnim(delta_time, len(self.bow.Attack_textures))
        if anim is None:
            return
        elif anim == 0:
            self.bow.canAttack = False
        elif anim == 8:
            angle = rotation(self.center_x, self.center_y, self.focused_on.center_x, self.focused_on.center_y, max_turn=360)+random.randrange(-5, 5)
            arrow = arcade.Sprite("resources/Sprites/Arcane archer/projectile.png", scale=1, center_x = self.center_x, center_y = self.center_y, angle = angle)
            arrow.time = 0
            self.arrows.append(arrow)
            game.overParticles.append(arrow)
            arrow.forward()
            arrow.update()
            arrow.hit = False
            arrow.destory_timer = 0
            self.pull_back_sound = None

        self.bow.texture = self.bow.Attack_textures[anim]
        self.bow.Attack_animation.timetoupdate = self.bow.AttackAnimTimes[anim]
            
        self.bow.timer = 0
    def destroy(self, game):
        self.bow.remove_from_sprite_lists()
        self.bow = None

        [arrow.remove_from_sprite_lists() for arrow in self.arrows]
        return super().destroy(game)
    def save(self, game):
        super().save(game)
        
        self.bow = arcade.Sprite(center_x=self.center_x, center_y=self.center_y, image_width=50, image_height=50)#Entity()
        self.bow.Attack_animation = AnimationPlayer(.1)
        self.bow.Attack_textures = load_texture_grid("resources/Sprites/Long Bow Pixilart Sprite Sheet.png", 50, 50, 50, 9)
        self.bow.texture = self.bow.Attack_textures[0]
        self.bow.AttackAnimTimes = [.25, .125, .125, .125, .2, .1, .05, .025, .025]
        self.bow.WaitToAttack = .2
        self.bow.timer = 0
        self.bow.canAttack = False
        
        arrows2 = []
        for arrow in self.arrows:
            arrow2 = type(arrow).__new__(type(arrow))
            arrow2.position = arrow.position
            arrow2.time = arrow.time
            arrow2.angle = arrow2.angle
            arrows2.append(arrow2)
        self.arrows2 = arrows2
    def load(self, game):
        self.arrows = self.arrows2
        [game.overParticles.append(arrow) for arrow in self.arrows]
        return super().load(game)

class Arsonist(BaseEnemy):
    def __init__(self, game, x:float, y:float, difficulty=1):
        super().__init__("resources/Sprites/Player.png", x, y, 5*difficulty, 5*difficulty, 40, scale=1)

        self.front_texture = arcade.load_texture("resources/Sprites/Child Front.png")
        self.back_texture = arcade.load_texture("resources/Sprites/Child Back.png")
        self.left_texture = arcade.load_texture("resources/Sprites/Child Left.png")
        self.right_texture = arcade.load_texture("resources/Sprites/Child Left.png", flipped_vertically=True)
        self.texture = self.front_texture

        self.building_bias = 1
        self.people_bias = 100#float("inf")
        self.boat_bias = 100

        self.movelist = [0]
        self.fire_strength = 1

        self.Explosian = arcade.Sprite(center_x=x-10, center_y = y+10, scale = .25)
        self.Explosian.textures = load_texture_grid("resources/Sprites/Fire_Totem/Fire_Totem-full_Sheet.png", 64, 100, 14, 70)
        self.Explosian.texture = self.Explosian.textures[4]
        self.Explosian.AnimationPlayer = AnimationPlayer(.1)
        game.overParticles.append(self.Explosian)

    def destroy(self, game):
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
    def update_movement(self, game, delta_time):
        self.path_timer += delta_time
        if self.path_timer < 1:
            return
        pos = self.get_path()
        if pos is not None:
            self.position = pos
            self.Explosian.position = self.center_x-10, self.center_y+10
        self.path_timer -= 1

        prev_pos = self.position
        super().update_movement(game, delta_time)
        if prev_pos[0] < self.position[0]:
            self.texture = self.back_texture
        elif prev_pos[0] > self.position[0]:
            self.texture = self.front_texture
        elif prev_pos[1] < self.position[1]:
            self.texture = self.right_texture
        elif prev_pos[1] > self.position[1]:
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

            hit = arcade.check_for_collision_with_lists(self, [game.Buildings, game.People, game.Boats], method=3)
            for obj in hit:
                obj.health -= self.damage
                if obj.health <= 0:
                    obj.destroy(game)
                if obj.__module__ == "Buildings":
                    try:
                        obj.fire.strength += 1
                    except:
                        game.LightOnFire(obj, self.fire_strength)
                obj.health -= self.damage
                if obj.health <= 0:
                    obj.destroy(game)
            self.health = -100
    def save(self, game):
        x, y = self.position
        self.Explosian2 = arcade.Sprite(center_x=x-10, center_y = y+10, scale = .25)
        self.Explosian2.textures = load_texture_grid("resources/Sprites/Fire_Totem/Fire_Totem-full_Sheet.png", 64, 100, 14, 70)
        self.Explosian2.texture = self.Explosian.textures[4]
        self.Explosian2.AnimationPlayer = AnimationPlayer(.1)
        self.Explosian2.AnimationPlayer.index = self.Explosian.AnimationPlayer.index


        return super().save(game)
    def load(self, game):
        self.Explosian = self.Explosian2
        game.overParticles.append(self.Explosian)
class Golem(BaseEnemy):
    def __init__(self, game, x: float, y: float, difficulty=1):
        super().__init__("resources/Sprites/Stone Golem/Character_sheet.png", x, y, 10*difficulty, 10*difficulty, 40, scale=.8)
        textures = load_texture_grid("resources/Sprites/Stone Golem/Character_sheet.png", 100, 100, 10, 100, margin = 0)
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

        self.affect = arcade.Sprite("resources/Sprites/Selection.png", center_x=100000, center_y=100000)
        self.affect.textures = load_texture_grid("resources/Sprites/Free Pixel Effects Pack/10_weaponhit_spritesheet.png", 100, 100, 6, 31)[1:]
        self.affect.animation_player = AnimationPlayer(.03)
        game.underParticals.append(self.affect)
    def destroy(self, game):
        self.state = "Death"
        self.canAttack = False
    def update(self, game, delta_time):
        if self.health <= 0:
            self.state = "Death"
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
        anim = self.affect.animation_player.updateAnim(delta_time, len(self.affect.textures))
        if anim is not None:
            self.affect.texture = self.affect.textures[anim]


        if self.attack_time >= 1:
            hit = arcade.check_for_collision_with_lists(self.affect, [game.Buildings, game.People], method=3)
            for thing in hit:
                thing.health -= self.damage
                if thing.health <= 0: thing.destroy(game)
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
    def save(self, game):
        super().save(game)
        self.affect = arcade.Sprite("resources/Sprites/Selection.png", center_x=100000, center_y=100000)
        self.affect.textures = load_texture_grid("resources/Sprites/Free Pixel Effects Pack/10_weaponhit_spritesheet.png", 100, 100, 6, 31)[1:]
        self.affect.animation_player = AnimationPlayer(.03)
    def load(self, game):
        super().save(game)
        game.underParticals.append(self.affect)
class Wizard(BaseEnemy):
    def __init__(self, game, x: float, y: float, difficulty):
        super().__init__("resources/Sprites/Wizard/Idle.png", x, y, 5*difficulty, 2*difficulty, 200, scale=1)

        self.front_texture = arcade.load_texture("resources/Sprites/Child Front.png")
        self.back_texture = arcade.load_texture("resources/Sprites/Child Back.png")
        self.left_texture = arcade.load_texture("resources/Sprites/Child Left.png")
        self.right_texture = arcade.load_texture("resources/Sprites/Child Left.png", flipped_vertically=True)
        self.texture = self.front_texture


        self.wand = arcade.Sprite("resources/Sprites/Wand.png", scale=.35, center_x=x-10, center_y=y)
        self.wand.projectile = arcade.Sprite("resources/Sprites/Warped shooting fx files/hits-1/frames/hits-1-2.png", scale=0)
        self.wand.projectile.visible = False

        game.overParticles.append(self.wand)
        game.overParticles.append(self.wand.projectile)


        self.movelist = [0]
        self.building_bias = 10
        self.people_bias = 1
        self.boat_bias = 10

        self.state = "Idle"
        self.projectiles = arcade.SpriteList()
        self.release_projectile = 0

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
        for projectile in self.projectiles:
            if not projectile.destroy:
                projectile.forward(speed=delta_time*50)
                projectile.update()
                projectile.time += delta_time
                if projectile.time > projectile.maxtime:
                    projectile.remove_from_sprite_lists()

                if self.focused_on and arcade.get_distance(projectile.center_x, projectile.center_y, self.focused_on.center_x, self.focused_on.center_y) < 25:
                    projectile.destroy = True
            else:
                anim = projectile.destructionAnim.updateAnim(delta_time, len(projectile.destruction))
                scalevar = .15*random.random()*delta_time
                projectile.scale += scalevar
                if anim == 0:
                    hit = arcade.check_for_collision_with_lists(projectile, [game.Buildings, game.People, game.Boats], method=3)
                    for obj in hit:
                        obj.health -= self.damage
                        if obj.health > 0:
                            continue
                        obj.destroy(game)
                    projectile.remove_from_sprite_lists()
                if anim is not None:
                    projectile.texture = projectile.destruction[anim]
    def on_attack(self, game, delta_time):
        if not self.canAttack:
            return
        self.state = "Attack"
        Attack1 = arcade.get_distance_between_sprites(self, self.focused_on) > 200
        
        self.wand.projectile.visible = True
        self.wand.projectile.scale += delta_time/2

        
        if self.wand.projectile.scale < 1:
            return
        if Attack1: self.create_projectile(game)
        else: self.create_projectile(game, maxtime=3, maxrotation=22, num = 5)

        self.canAttack = False
        self.timer = 0
        self.state = "Idle"
        self.wand.projectile.scale = 0
    def create_projectile(self, game, maxtime=15, maxrotation=5, num=1):
        for i in range(num):
            angle = rotation(self.center_x, self.center_y, self.focused_on.center_x, self.focused_on.center_y, max_turn=360)
            projectile = arcade.Sprite("resources/Sprites/Warped shooting fx files/hits-1/frames/hits-1-2.png", scale = 1, angle=angle+random.randrange(-maxrotation, maxrotation))
            game.overParticles.append(projectile)
            self.projectiles.append(projectile)
            
            projectile.time = 0
            projectile.maxtime = maxtime
            projectile.destruction = []
            for i in range(1, 5):
                projectile.destruction.append(arcade.load_texture(f"resources/Sprites/Warped shooting fx files/hits-1/frames/hits-1-{i+1}.png"))
            projectile.destructionAnim = AnimationPlayer(.1)
            projectile.destroy = False
            
            projectile.position = self.position
            projectile.forward()
            projectile.update()
    def destroy(self, game):
        super().destroy(game)
        self.remove_from_sprite_lists()
        self.wand.remove_from_sprite_lists()
        self.wand.projectile.remove_from_sprite_lists()
        for projectile in self.projectiles:
            projectile.remove_from_sprite_lists()
    def save(self, game):
        x, y = self.position
        self.wand2 = arcade.Sprite("resources/Sprites/Wand.png", scale=.35, center_x=x-10, center_y=y)
        self.wand2.projectile = arcade.Sprite("resources/Sprites/Warped shooting fx files/hits-1/frames/hits-1-2.png", scale=0)
        self.wand2.projectile.visible = self.wand.projectile.visible
        self.projectiles2 = arcade.SpriteList()
        for projectile in self.projectiles:
            projectile2 = projectile
            projectile2 = type(projectile).__new__(type(projectile))
            projectile.position = projectile.position
            projectile.time = projectile.time
            projectile2.angle = projectile.angle
            projectile2.destroy = projectile.destroy
            self.projectiles2.append(projectile2)
        return super().save(game)
    def load(self, game):
        game.overParticles.append(self.wand2)
        game.overParticles.append(self.wand.projectile)

        self.projectiles = self.projectiles2
        [game.overParticles.append(projectile) for projectile in self.projectiles]
        return super().load(game)

class Privateer(BaseEnemy):
    def __init__(self, game, x:float, y:float, difficulty=1):
        super().__init__("resources/Sprites/Boat.png", x, y, 20*difficulty, 5*difficulty, 150, .5)
        self.people_bias = 1
        self.building_bias = 1
        self.boat_bias = .2
        self.movelist = [2]

        self.bow = arcade.Sprite(center_x=self.center_x, center_y=self.center_y, image_width=50, image_height=50)#Entity()
        self.bow.Attack_animation = AnimationPlayer(.1)
        self.bow.Attack_textures = load_texture_grid("resources/Sprites/Long Bow Pixilart Sprite Sheet.png", 50, 50, 50, 9)
        self.bow.texture = self.bow.Attack_textures[0]
        self.bow.AttackAnimTimes = [.25, .125, .125, .125, .2, .1, .05, .025, .025]
        self.bow.WaitToAttack = .2
        self.bow.timer = 0
        self.bow.canAttack = False
        game.overParticles.append(self.bow)

        self.arrows = arcade.SpriteList()#[]
        self.state = "Idle"
    def update(self, game, delta_time):
        if self.health <= 0:
            self.destroy(game)
            return 
        self.on_update(game, delta_time)

        if self.focused_on:
            self.bow.angle = rotation(self.center_x, self.center_y, self.focused_on.center_x, self.focused_on.center_y, angle = self.bow.angle-90)+90

        self.bow.center_x = self.center_x
        self.bow.center_y = self.center_y

        self.update_movement(game, delta_time)
        
        for arrow in self.arrows:
            arrow.forward(speed=delta_time*50)
            arrow.update()
            arrow.time += delta_time
            if arrow.time > 15:
                arrow.remove_from_sprite_lists()
            elif not self.focused_on:
                break
            elif arcade.get_distance(arrow.center_x, arrow.center_y, self.focused_on.center_x, self.focused_on.center_y) < 25:
                self.focused_on.health -= self.damage*random.random()*random.random()*4
                arrow.remove_from_sprite_lists()

        self.bow.timer += delta_time
        if self.bow.timer < self.bow.WaitToAttack:
            return
        self.bow.timer -= self.bow.WaitToAttack
        self.bow.canAttack = True

    def update_movement(self, game, delta_time):
        if self.path: 
            self.angle = rotation(self.center_x, self.center_y, self.path[0][0], self.path[0][1], angle = self.angle+90)-90   
        self.path_timer += delta_time
        if self.path_timer > self.next_time:
            pos = self.get_path()
            if pos is not None:
                self.position = pos
            self.path_timer -= self.next_time
    def on_attack(self, game, delta_time):  
        self.angle = rotation(self.center_x, self.center_y, self.focused_on.center_x, self.focused_on.center_y, angle = self.angle+90)-90   
        if not self.bow.canAttack: 
            return
        anim = self.bow.Attack_animation.updateAnim(delta_time, len(self.bow.Attack_textures))
        if anim is None:
            return
        elif anim == 0:
            self.bow.canAttack = False
        elif anim == 8:
            angle = rotation(self.center_x, self.center_y, self.focused_on.center_x, self.focused_on.center_y, max_turn=360)+random.randrange(-5, 5)
            arrow = arcade.Sprite("resources/Sprites/Arcane archer/projectile.png", scale=1, center_x = self.center_x, center_y = self.center_y, angle = angle)
            arrow.time = 0
            self.arrows.append(arrow)
            game.overParticles.append(arrow)
            arrow.forward()
            arrow.update()
        self.bow.texture = self.bow.Attack_textures[anim]
        self.bow.Attack_animation.timetoupdate = self.bow.AttackAnimTimes[anim]
            
        self.bow.timer = 0
    def destroy(self, game):
        self.bow.remove_from_sprite_lists()
        self.bow = None

        [arrow.remove_from_sprite_lists() for arrow in self.arrows]
        return super().destroy(game)
    def save(self, game):
        super().save(game)
        
        self.bow = arcade.Sprite(center_x=self.center_x, center_y=self.center_y, image_width=50, image_height=50)#Entity()
        self.bow.Attack_animation = AnimationPlayer(.1)
        self.bow.Attack_textures = load_texture_grid("resources/Sprites/Long Bow Pixilart Sprite Sheet.png", 50, 50, 50, 9)
        self.bow.texture = self.bow.Attack_textures[0]
        self.bow.AttackAnimTimes = [.25, .125, .125, .125, .2, .1, .05, .025, .025]
        self.bow.WaitToAttack = .2
        self.bow.timer = 0
        self.bow.canAttack = False
        
        arrows2 = []
        for arrow in self.arrows:
            arrow2 = type(arrow).__new__(type(arrow))
            arrow2.position = arrow.position
            arrow2.time = arrow.time
            arrow2.angle = arrow2.angle
            arrows2.append(arrow2)
        self.arrows2 = arrows2
    def load(self, game):
        self.arrows = self.arrows2
        [game.overParticles.append(arrow) for arrow in self.arrows]
        return super().load(game)
