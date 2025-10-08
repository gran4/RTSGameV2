"""
TODO: Shaders
TODO: add sound based on distince

BUG: FIX RESIZE BUG
You can see out of bounds in full screen
Doesn't load saves

Perlin noise for map generation
Buildings span more than 1 tile
Make Tiles smaller?
"""

"""
NOTE: Enemy Spawning uses a Dictionary to see how many buildings reference a spot
If the spot is referenced the spot is un reachable.
Another Dictionary is which spots are reachable.
len in dict

>0 is spawnable

NOTE: __getattr__ is obj.item
NOTE: __getitem is obj[item]
"""

#python3.10 -m PyInstaller MainTestResizable.py --noconsole --onefile --add-data "resources:resources"
#python3.10 -m PyInstaller MainTestResizable.py --windowed --noconsole --onefile --add-data "resources:resources" --icon="resources/Sprites/Icon.png"

import sys, os

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    os.chdir(sys._MEIPASS)


from math import sqrt, floor
import arcade, json, random, arcade.gui, time, pickle, atexit

from arcade.gui import UILabel, UIAnchorWidget
from BackGround import *
from Buildings import *
from Enemys import *
from CustomCellularAutomata import initialize_grid, create_grid, do_simulation_step
from Player import *
from TextInfo import *
from Components import *
from copy import copy

from MyPathfinding import LivingMap, _AStarSearch, SearchTilesAround
arcade.PymunkPhysicsEngine
#loading gets stuck somewhere
Font = "Wooden Font(1).png"
class MyGame(arcade.View):
    """
    Main application class.
    """
    def __init__(self, menu, file_num=1, world_gen="Normal", difficulty=1):

        # Call the parent class and set up the window
        super().__init__()#750, 500, "SCREEN_TITLE")

        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)

        self.time_alive = 0
        self.Christmas_timer = -300
        self.Completed_Christmas = False
        self.file_num = file_num
        self.difficulty = difficulty
        self.menu = menu
        self.science_list = None
        
        self.setup(file_num, world_gen)
        self.create_audio()
        self.updateStorage()

        self.speed = 1
        ui_slider = CustomUISlider(max_value=20, value=2, width=302, height=35, x=0, offset_x=150, offset_y=-10, button_offset_y=-6)#arcade.load_texture("resources/gui/Slider_Button.png")#self.textures[0]
        #ui_slider.move(-200, -100)
        label = UILabel(text=f"speed {ui_slider.value*.5:02.0f}x")
        self.label = label
        self.ui_slider = ui_slider

        @ui_slider.event()
        def on_change(event: UIOnChangeEvent):
            label.text = f"speed {ui_slider.value*.5:02.0f}x"
            self.speed = ui_slider.value*.5
            label.fit_content()

        slider = UIAnchorWidget(child=ui_slider, align_x=0, align_y=110, anchor_x="left", anchor_y="bottom")
        ui_slider.wrapper = slider
        self.uimanager.add(slider)
        label_wrapper = UIAnchorWidget(child=label, align_x=50, align_y=160, anchor_x="left", anchor_y="bottom")
        label.wrapper = label_wrapper
        self.uimanager.add(self.label)

        expand_button = CustomUIFlatButton({}, click_sound = self.click_sound, text=None, width=64, height=64, offset_x=16, offset_y=16, Texture="resources/gui/contract.png", Hovered_Texture="resources/gui/contract.png", Pressed_Texture="resources/gui/expand.png")
        expand_button.on_click = self.speed_bar_change
        expand_button.expand = False
        expand_button.buttons = [slider, label_wrapper]
        self.expand_button = expand_button
        self.speed_bar = expand_button
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="left", anchor_y="bottom",
                child=expand_button, align_x=0, align_y=150)
        expand_button.wrapper = wrapper
        self.uimanager.add(wrapper)

        self.create_ui()
        self.update_audio()

        self.christmas_background = arcade.Sprite("resources/gui/ChristmasOverlay.png", scale=.25, center_x=370, center_y=180)
        self.christmas_background.visible = False
        self.christmas_background.alpha = 0
        self.overParticles.append(self.christmas_background)

        window = arcade.get_window()
        self.on_resize(window.width, window.height)

    def setup(self, file_num, world_gen):
        self.extra_buttons = []
        self.camera = arcade.Camera(750, 500)
        self.not_scrolling_camera = arcade.Camera(750, 500)

        self.lacks = []

        self.science = 100
        self.overall_multiplier = 1
        self.training_speed_multiplier = 1
        self.dissent_multiplier = 1
        self.damage_multiplier = 1
        self.growth_multiplier = 1
        self.science_multiplier = 1
        self.food_multiplier = 1
        self.wood_multiplier = 1
        self.stone_multiplier = 1
        self.metal_multiplier = 1
        self.toys_multiplier = 1
        self.building_multiplier = 1

        self.food = 2000
        self.food_storage = 3000
        self.population = 2
        self.stone = 0
        self.metal = 0
        self.wood = 50
        self.toys = 0
        self.toy_amount = 100

        self.mcsStorage = 200
        self.max_pop = 5

        self.timer = 0

        self.x = 0
        self.y = 0

        #sprite lists
        #BackGround
        self.Lands = arcade.SpriteList(use_spatial_hash=True, is_static=True)
        self.Stones = arcade.SpriteList(use_spatial_hash=True, is_static=True)
        self.Seas = arcade.SpriteList(use_spatial_hash=True, is_static=True)
        self.Trees = arcade.SpriteList(use_spatial_hash=True, is_static=True)
        self.BerryBushes = arcade.SpriteList(use_spatial_hash=True, is_static=True)

        self.Fires = arcade.SpriteList(use_spatial_hash=True, is_static=True)
        self.overParticles = arcade.SpriteList()
        self.underParticals = arcade.SpriteList()

        self.Buildings = arcade.SpriteList(use_spatial_hash=True, is_static=True)
        self.Boats = arcade.SpriteList()
        self.boatUpdate = 0

        self.People = arcade.SpriteList()
        self.health_bars = arcade.SpriteList()
        self.peopleUpdate = 0
        self.move = False


        self.Enemies = arcade.SpriteList()
        self.EnemyBoats = arcade.SpriteList()
        self.spawnEnemy = -300
        self.hardness_multiplier = 1
        self.OpenToEnemies = []
        self.EnemyMap = {}

        self.boatUpdate = 0
        self.peopleUpdate = .1
        self.enemyUpdate = .2
        self.fireUpdate = .3

        self.ui_sprites = arcade.SpriteList(is_static=True)
        self.ui_sprite_background = arcade.Sprite("resources/gui/Small Text Background.png", scale = 1.1, center_x=-2000)
        self.ui_sprite_text = CustomTextSprite(None, {})#arcade.create_text_sprite("Selected None", 50, 25, arcade.color.BLACK)

        self.RiteSlots = 0

        self.left_pressed = False
        self.right_pressed = False
        self.down_pressed = False
        self.up_pressed = False


        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()
    

        self.unlocked = unlocked
        self.objects = objects

        self.object_placement = None
        self.object = None
        self.requirements = {"wood":float("inf")}


        self.last = None
        self.selection_rectangle = arcade.Sprite("resources/Sprites/Selection.png", scale=1.2, center_x=-100000, center_y=-100000)

        #self.load(file_num)
        try:
            self.load(file_num)
        except:
            self.generateWorld(100, 100, world_gen)
            self.generateEnemySpawner(100, 100)

        
        self.center_camera()   
        self.clear_uimanager()
    def create_audio(self):
        self.audios = self.menu.audios
        self.click_sound = self.menu.click_sound
        self.Background_music = self.menu.Background_music
        self.Christmas_music = self.menu.Christmas_music
        
        self.audio_type_vols = self.menu.audio_type_vols

        self.update_audio()
    def update_audio(self):
        for audio in self.audios:
            audio.volume = audio.start_vol*self.audio_type_vols[audio.type]*self.audio_type_vols["Overall"]
            audio.source.volume = audio.volume
            if audio.player:
                audio.player.volume = audio.volume
            #audio.set_volume(audio.volume, audio.player)

    def create_ui(self):
        self.PopUps = []
         
        textures = arcade.load_spritesheet("resources/gui/Wooden Font.png", 14, 24, 12, 70, margin=1)
        self.Alphabet_Textures = {" ":None}
        string = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyz.:,%/-+_"
        for i in range(len(string)):
            self.Alphabet_Textures[string[i]] = textures[i]

        self.text_timer = 0
        self.text_sprites = []
        self.lack_text = None
        self.text_visible = True
        self.under_sprite = arcade.Sprite("resources/gui/Medium Bulletin.png", scale=2.2, center_x=200, center_y=280)
        self.update_text(1)

        expand_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text=None, width=64, height=64, offset_x=16, offset_y=16, Texture="resources/gui/contract.png", Hovered_Texture="resources/gui/contract.png", Pressed_Texture="resources/gui/expand.png")
        expand_button.on_click = self.expand_button_click
        expand_button.expand = False
        self.expand_button = expand_button
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="left", anchor_y="top",
                child=expand_button, align_x=0, align_y=30)
        expand_button.wrapper = wrapper
        self.uimanager.add(wrapper)
        

        self.secondary_wrappers = []
        main_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Menus", width=140, height=50, x=0, y=50, text_offset_x = 16, text_offset_y=35, offset_x=75, offset_y=25)
        main_button.on_click = self.main_button_click
        main_button.open = False
        self.main_button = main_button
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="right", anchor_y="top",
                child=main_button, align_x=0, align_y=0)
        main_button.wrapper = wrapper
        self.uimanager.add(wrapper)


        button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Menu", width=140, height=50, x=0, y=50, text_offset_x = 24, text_offset_y=35, offset_x=75, offset_y=25)
        button.on_click = self.menus_button_click
        button.open = False
        self.menus_button = button
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="right", anchor_y="top",
                child=button, align_x=250, align_y=0)
        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.secondary_wrappers.append(wrapper)
        self.menu_buttons = []

        button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Science Menu", width=140, height=50, x=0, y=50, text_offset_x = 6, text_offset_y=35, text_margin=14, offset_x=75, offset_y=25)
        button.cost = float('inf')
        button.on_click = self.on_ScienceMenuclick
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="right", anchor_y="top",
                child=button, align_x=250, align_y=0)
        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.menu_buttons.append(wrapper)


        button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Volume Menu", width=140, height=50, x=0, y=50, text_offset_x = 16, text_offset_y=35, offset_x=75, offset_y=25)
        button.cost = float('inf')
        button.on_click = self.on_VolumeMenuclick
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="right", anchor_y="top",
                child=button, align_x=250, align_y=-100)
        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.menu_buttons.append(wrapper)


        # Creating save Button
        button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Save", width=140, height=50, x=0, y=50, text_offset_x = 24, text_offset_y=35, offset_x=75, offset_y=25)
        button.on_click = self.save
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="right", anchor_y="top",
                child=button, align_x=250, align_y=-100)
        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.secondary_wrappers.append(wrapper)


        button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Selectables", width=140, height=50, x=0, y=50, text_offset_x = -6, text_offset_y=35, text_scale=.8, text_margin=11, offset_x=75, offset_y=25)
        button.on_click = self.selectables_click
        button.open = False
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="right", anchor_y="top",
                child=button, align_x=250, align_y=-200)
        button.wrapper = wrapper

        self.selectables_button = button
        self.uimanager.add(wrapper)
        self.secondary_wrappers.append(wrapper)
        self.selectables = []


        button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Buildings", width=140, height=50, x=0, y=50, text_offset_x=0, text_offset_y=35, text_scale=1, text_margin=13, offset_x=75, offset_y=25)
        button.cost = float('inf')
        button.value = 1
        button.on_click = self.switch_val
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="right", anchor_y="top",
                child=button, align_x=250, align_y=0)
        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.selectables.append(wrapper)

        button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="People", width=140, height=50, x=0, y=50, text_offset_x=12, text_offset_y=35, offset_x=75, offset_y=25)
        button.cost = float('inf')
        button.value = 2
        button.on_click = self.switch_val
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="right", anchor_y="top",
                child=button, align_x=250, align_y=-100)
        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.selectables.append(wrapper)

        
        button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Boats", width=140, height=50, x=0, y=50, text_offset_x=12, text_offset_y=35, offset_x=75, offset_y=25)
        button.cost = float('inf')
        button.value = 3
        button.on_click = self.switch_val
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="right", anchor_y="top",
                child=button, align_x=250, align_y=-200)
        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.selectables.append(wrapper)


        button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Return", width=140, height=50, x=0, y=50, text_offset_x = 12, text_offset_y=35, offset_x=75, offset_y=25)
        button.on_click = self.return_to_menu
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="right", anchor_y="top",
                child=button, align_x=250, align_y=-300)
        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.secondary_wrappers.append(wrapper)
    def on_resize(self, width: int, height: int):
        self.camera.resize(width, height)
        self.camera.set_projection()
        self.center_camera()

        self.not_scrolling_camera.resize(width, height)
        self.not_scrolling_camera.set_projection()

        if self.ui_sprites:
            move_x = width-50
            move_y = height-0
            y = move_y
        for sprite in self.ui_sprites:
            y -= 50
            sprite.center_x = move_x
            sprite.center_y = y

        self.under_sprite.center_y = height-220
        y = height-20
        for text_sprite in self.text_sprites:
            for sprite in text_sprite.Sprite_List:
                sprite.center_y = y
                
            y -= 30
        self.christmas_background.position = self.player.center_x, self.player.center_y
        self.christmas_background.scale = .25*max(width/1240, height/900)
        return super().on_resize(width, height)

    def End(self):
        self.science_list = None
        self.uimanager.disable()

        if self.file_num:
            file = open(f"{self.file_num}", "r+")
            file.truncate() 

        num = self.time_alive-300
        if num > 0: history = 2*1.5**(num/60)
        else: history = 0
        with open("resources/game.json", "r") as read_file:
            try:
                p = json.load(read_file)
                p["Money"] += history
            except:
                p = {}
                science_unlocked = []
                with open("GameBase.json", "r") as read_file:
                    buttons = json.load(read_file)
                

                for button in buttons["ScienceMenu"]: 
                    science_unlocked.append(bool(button[8]))
                p["science_menu"] = science_unlocked
                p["Money"] = history
                
                self.graph = None

        with open("resources/game.json", "w") as write_file:
            json.dump(p, write_file)
        global prev_frame
        prev_frame = {"food":1000, "wood":0, "stone":0, "metal":0}

        if self.Christmas_music: 
            if self.Christmas_music.player: self.Christmas_music.stop(self.Christmas_music.player)
        self.Christmas_music = None

        Endmenu = EndMenu(history, self, self.menu)
        self.window.show_view(Endmenu)
    def return_to_menu(self, event):
        global prev_frame
        prev_frame = {"food":1000, "wood":0, "stone":0, "metal":0}

        if self.Christmas_music: 
            if self.Christmas_music.player: self.Christmas_music.stop(self.Christmas_music.player)
        self.Christmas_music = None

        self.uimanager.disable()
        self.menu.uimanager.enable()
        self.science_list = None
        self.window.show_view(self.menu)
    def main_button_click(self, event):
        if event.source.open:
            for wrapper in self.menu_buttons:
                wrapper.align_x = 250
            for wrapper in self.selectables:
                wrapper.align_x = 250
            for wrapper in self.secondary_wrappers:
                wrapper.align_x = 250
            event.source.wrapper.align_x = 0
            event.source.open = False
            self.ui_sprites = arcade.SpriteList()
            self.object_placement = None
            self.object = None
            self.requirements = {"wood":float("inf")}
            self.ui_sprite_text = CustomTextSprite(None, self.Alphabet_Textures, center_x=50, center_y = 20, width = 500)
            self.secondary_wrappers[0].child.open = False
            self.secondary_wrappers[2].child.open = False
            self.ui_sprite_background.center_x = -200
        else:
            for wrapper in self.secondary_wrappers:
                wrapper.align_x = 0
            event.source.wrapper.align_x = -150
            event.source.open = True
    def menus_button_click(self, event):
        if event.source.open:
            for wrapper in self.menu_buttons:
                wrapper.align_x = 250
            for wrapper in self.secondary_wrappers:
                wrapper.align_x = 0
            self.main_button.wrapper.align_x = -150
            event.source.open = False
            self.ui_sprite_background.center_x = -200
        else:
            for wrapper in self.selectables:
                wrapper.align_x = 250
            for wrapper in self.menu_buttons:
                wrapper.align_x = 0
            for wrapper in self.secondary_wrappers:
                wrapper.align_x = -150
            self.main_button.wrapper.align_x = -300
            event.source.open = True
            self.selectables_button.open = False

            self.ui_sprites = arcade.SpriteList()
            self.object_placement = None
            self.object = None
            self.requirements = {"wood":float("inf")}
            self.ui_sprite_background.center_x = -200
            self.ui_sprite_text = CustomTextSprite(None, self.Alphabet_Textures, center_x=50, center_y = 20, width = 500)
    def selectables_click(self, event):
        if event.source.open:
            for wrapper in self.menu_buttons:
                wrapper.align_x = 250
            for wrapper in self.selectables:
                wrapper.align_x = 250
            for wrapper in self.secondary_wrappers:
                wrapper.align_x = 0
            self.main_button.wrapper.align_x = -150

            self.ui_sprites = arcade.SpriteList()
            self.object_placement = None
            self.object = None
            self.requirements = {"wood":float("inf")}
            self.ui_sprite_background.center_x = -200
            self.ui_sprite_text = CustomTextSprite(None, self.Alphabet_Textures, center_x=50, center_y = 20, width = 500)
        else:
            for wrapper in self.menu_buttons:
                wrapper.align_x = 250
            for wrapper in self.selectables:
                wrapper.align_x = 0
            for wrapper in self.secondary_wrappers:
                wrapper.align_x = -150
            self.main_button.wrapper.align_x = -300
            self.menus_button.open = False
        event.source.open = not event.source.open
    def expand_button_click(self, event):
        self.text_visible = event.source.expand
        event.source.sprite, event.source.hovered_sprite, event.source.pressed_sprite = event.source.pressed_sprite, event.source.pressed_sprite, event.source.sprite
        #event.source.pressed_sprite = event.source.sprite
        event.source.expand = not event.source.expand
        self.update_text(1)
    def speed_bar_change(self, event):
        event.source.sprite, event.source.hovered_sprite, event.source.pressed_sprite = event.source.pressed_sprite, event.source.pressed_sprite, event.source.sprite
        event.source.expand = not event.source.expand
        if event.source.expand:
            for wrapper in event.source.buttons:
                wrapper.org_x = wrapper.align_x
                wrapper.align_x = -1000
        else:
            for wrapper in event.source.buttons:
                wrapper.align_x = wrapper.org_x

    def switch_val(self, event):
        self.main_button.wrapper.align_x = -400
        for wrapper in self.selectables:
            wrapper.align_x = -100
        for wrapper in self.secondary_wrappers:
            wrapper.align_x = -250

        while len(self.ui_sprites) > 0:
            self.ui_sprites.pop()
        buttons = ui_obj_info

        if event.source.value == 1:
            source = "Buildings"
        elif event.source.value == 2:
            source = "People"
        elif event.source.value == 3:
            source = "Boats"
        width = self.camera.viewport_width
        height = self.camera.viewport_height
        move_x = width-50
        y = height
        for obj in buttons[source]:
            if self.unlocked[obj]:
                y -= 50
                ui_sprite = arcade.Sprite(center_x=move_x, center_y = y)
                sprite = self.objects[obj](self, move_x, y)
                ui_sprite.texture = sprite.texture
                ui_sprite.name = obj
                ui_sprite.object_placement = source
                ui_sprite.requirements = requirements[obj]

                self.ui_sprites.append(ui_sprite)
                sprite.destroy(self)
                if isinstance(sprite, Person):
                    self.population += 1
    def on_ScienceMenuclick(self, event):
        self.ui_sprites = arcade.SpriteList()
        self.object_placement = None
        self.object = None
        self.requirements = {"wood":float("inf")}
        self.ui_sprite_background.center_x = -200
        self.ui_sprite_text = CustomTextSprite(None, self.Alphabet_Textures, center_x=50, center_y = 20, width = 500)

        self.uimanager.disable()
        self.window.show_view(ScienceMenu(self))
    def on_VolumeMenuclick(self, event):
        self.ui_sprites = arcade.SpriteList()
        self.object_placement = None
        self.object = None
        self.requirements = {"wood":float("inf")}
        self.ui_sprite_background.center_x = -200
        self.ui_sprite_text = CustomTextSprite(None, self.Alphabet_Textures, center_x=50, center_y = 20, width = 500)

        self.uimanager.disable()
        self.window.show_view(VolumeMenu(self))
    def on_SelectionMenuclick(self, event):
        self.uimanager.disable()
        self.window.show_view(BuildingMenu(self))
    def activate_Christmas(self):
        self.update_text(1)
        self.uimanager.disable()
        self.window.show_view(ChristmasMenu(self))
    def training_menu(self, event):
        self.uimanager.disable()
        self.window.show_view(TrainingMenu(self, event.source.building))
    def person_switch(self, event):
        person = event.source.obj
        if person.state2 == "Patrol":
            person.state2 = "Work"
            person.state_update(self, "Work")
        else:
            person.state2 = "Patrol"
            person.state_update(self, "Patrol")
        event.source.set_text(person.state2)
    def on_draw(self):

        t = time.time()
        """Render the screen."""
        #arcade.start_render() clears screen
        arcade.start_render()
        self.camera.use()


        #tiles
        self.Lands.draw()
        self.Seas.draw()
        self.Stones.draw()
        self.Trees.draw()
        self.BerryBushes.draw()
        self.underParticals.draw()


        if self.last:
            self.selection_rectangle.center_x = self.last.center_x-1
            self.selection_rectangle.center_y = self.last.center_y+1
            self.selection_rectangle.draw()


        self.Buildings.draw()
        self.Boats.draw()
        self.People.draw()
        self.player.draw()

        self.Enemies.draw()
        self.EnemyBoats.draw()

        self.health_bars.draw()
        self.Fires.draw()
        self.overParticles.draw()


        self.not_scrolling_camera.use()
        self.christmas_background.draw()
    
        self.uimanager.draw()
        self.ui_sprites.draw()
        
        if self.text_visible:
            self.under_sprite.draw()
            for text in self.text_sprites:
                text.draw()
            if self.lack_text: self.lack_text.draw()
        self.ui_sprite_background.draw()
        self.ui_sprite_text.draw()
        for PopUp in self.PopUps: PopUp.draw()
    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed. """

        center_x = 0
        center_y = 0
        #move camera
        if key == arcade.key.LEFT or key == arcade.key.A:
            center_x -= 50
            self.player.key = "A"
            self.player.pressed_update()
        if key == arcade.key.RIGHT or key == arcade.key.D:
            center_x += 50
            self.player.key = "D"
            self.player.pressed_update()
        if key == arcade.key.DOWN or key == arcade.key.S:
            center_y -= 50
            self.player.key = "S"
            self.player.pressed_update()
        if key == arcade.key.UP or key == arcade.key.W:
            center_y += 50
            self.player.key = "W"
            self.player.pressed_update()

        if self.can_move((self.player.center_x+center_x, self.player.center_y+center_y)):
            self.player.center_x += center_x
            self.player.center_y += center_y
        Boats_at_point = arcade.get_sprites_at_point(self.player.position, self.Boats)
        if len(Boats_at_point) >= 1:
            self.player.boat = Boats_at_point[0]
        else:
            self.player.boat = None

        self.center_camera()
    def can_move(self, pos):
        x, y = self.camera.viewport_width/2-50, self.camera.viewport_height/2
        if 750<pos[0]<self.x_line*50-750 and 750<pos[1]<self.y_line*50-750:

            pass
        else:
            info_sprite = UpdatingText("Hit the Side", self.Alphabet_Textures, .5, width = 300, center_x=x, center_y=y)
            self.PopUps.append(info_sprite)
            return False

        buildings = arcade.get_sprites_at_point(pos, self.Buildings)
        if len(buildings) != 0 and buildings[0].path:
            return True
        elif len(buildings) != 0 and not buildings[0].path:
            info_sprite = UpdatingText("Hit building", self.Alphabet_Textures, .5, width = 300, center_x=x, center_y=y)
            self.PopUps.append(info_sprite)
            return False
        elif len(arcade.get_sprites_at_point(pos, self.Stones)) != 0:
            info_sprite = UpdatingText("Hit stone", self.Alphabet_Textures, .5, width = 300, center_x=x, center_y=y)
            self.PopUps.append(info_sprite)
            return False
        elif len(arcade.get_sprites_at_point(pos, self.Boats)) == 0 and len(arcade.get_sprites_at_point(pos, self.Seas)) != 0:
            info_sprite = UpdatingText("Hit water", self.Alphabet_Textures, .5, width = 300, center_x=x, center_y=y)
            self.PopUps.append(info_sprite)
            return False
        return True
    def on_mouse_drag(self, x, y, dx, dy, _buttons, _modifiers):
        if x <= 500 or len(self.ui_sprites) == 0 or not 750 > y > 0:
            return
        elif dy > 0 and self.ui_sprites[-1].center_y+dy > 50:
            return
        elif dy < 0 and self.ui_sprites[0].center_y+dy < self.camera.viewport_height:
            return
        else:
            for button in self.ui_sprites:
                button.center_y += dy
    def on_mouse_press(self, x, y, button, modifiers):
        for press in self.uimanager.children[0]:
            try:
                if press.child.hovered:
                    return
            except:
                pass
        

        ui_clicked = self.ui_sprites_update(x, y)
        if ui_clicked:
            self.clear_uimanager()
            self.move = False
            self.last = None
            return
        elif button == arcade.MOUSE_BUTTON_RIGHT:
            self.info_on_click(x, y)
            return
        org_x, org_y = x, y
        
        x += self.player.center_x
        y += self.player.center_y
        x -=  (self.camera.viewport_width / 2)
        y -=  (self.camera.viewport_height / 2)

        x = x/50
        x = round(x)
        x2 = x
        x *= 50

        y = y/50
        y = round(y)
        y2 = y
        y *= 50

        if button == arcade.MOUSE_BUTTON_LEFT: 
            if self.move:
                source = self.last
                
                if not 750<x<self.x_line*50-750 or not 750<y<self.y_line*50-750:
                    if isinstance(source, BaseBoat):
                        info_sprite = UpdatingText("Out of Bounds", self.Alphabet_Textures, .5, width = 300, center_x=org_x, center_y=org_y)
                        self.PopUps.append(info_sprite)
                        return
                if len(arcade.get_sprites_at_point((x, y), self.Boats)) > 0:
                    self.graph[x2][y2] = 0
                elif len(arcade.get_sprites_at_point((x, y), self.Buildings)) > 0:
                    i = self.graph[x2][y2]
                    self.graph[x2][y2] = 0
                source.path = _AStarSearch(self.graph, source.position, (x, y), allow_diagonal_movement=True, movelist=source.movelist, min_dist=1)
                if len(arcade.get_sprites_at_point((x, y), self.Boats)) > 0:
                    self.graph[x2][y2] = 2
                elif len(arcade.get_sprites_at_point((x, y), self.Buildings)) > 0:
                    self.graph[x2][y2] = i

                self.move = False
                if source.path:
                    source.skill = None
                    source.amount = 0
                else:
                    info_sprite = UpdatingText("Can not move here", self.Alphabet_Textures, .5, width = 300, center_x=org_x, center_y=org_y)
                    self.PopUps.append(info_sprite)
                return
            people_at_point = arcade.get_sprites_at_point((x, y), self.People)
            if len(people_at_point) != 0:
                people_at_point[0].clicked(self)
                return
            ships_at_point = arcade.get_sprites_at_point((x, y), self.Boats)
            if len(ships_at_point) > 0:
                ships_at_point[0].clicked(self)
                return

            buildings_at_point = arcade.get_sprites_at_point((x, y), self.Buildings)
            if len(buildings_at_point) != 0:
                buildings_at_point[0].clicked(self)
                return
            
            string = ""
            if arcade.get_distance(self.player.center_x, self.player.center_y, x, y) > 400:
                string = "Too far from Santa"
            elif not _AStarSearch(self.graph, self.player.position, (x, y), movelist=[0], min_dist=50):
                string = "Santa can not pathfind here"
            elif get_closest_sprite((x, y), self.People)[1] < 100:
                pass
            elif self.SnowMap[x][y] == 0:
                string = "Must be 3 blocks from a Building or adjacent to an elf"
            elif arcade.get_sprites_at_point((x, y), self.Enemies): 
                string = "Can not place on an Enemy"
            elif self.objects[self.object] == Person and self.population >= self.max_pop:
                string = "Not enough Housing"
            if string: 
                info_sprite = UpdatingText(string, self.Alphabet_Textures, .5, width = 150, center_x=org_x, center_y=org_y)
                self.PopUps.append(info_sprite)
                return

            if self.unlocked[self.object] and 0 < x < 5000 and 0 < y < 5000:
                
                dont_continue = False
                if tiles[self.object] == Land and self.graph[x2][y2] != 0:
                    dont_continue = True
                elif tiles[self.object] == Stone and self.graph[x2][y2] != 1:
                    dont_continue = True
                elif tiles[self.object] == Sea and self.graph[x2][y2] != 2:
                    dont_continue = True
                elif tiles[self.object] == BerryBush:
                    if len(arcade.get_sprites_at_point((x, y), self.BerryBushes)) == 0:
                        dont_continue = True
                elif tiles[self.object] == Tree:
                    if len(arcade.get_sprites_at_point((x, y), self.Trees)) == 0:
                        dont_continue = True
                if dont_continue:
                    info_sprite = UpdatingText(f"You can only place this on {tiles[self.object].__name__}", self.Alphabet_Textures, .5, width = 300, center_x=org_x, center_y=org_y)
                    self.PopUps.append(info_sprite)
                    return

                missing = ""
                self.requirements = requirements[self.object]
                for _type, requirement in self.requirements.items():
                    if vars(self)[_type] < requirement:
                        if missing:
                            missing += ", "
                        missing += f"{requirement-vars(self)[_type]} {_type}"
                if missing:
                    info_sprite = UpdatingText("missing: "+missing, self.Alphabet_Textures, .5, width = 300, center_x=org_x, center_y=org_y)
                    self.PopUps.append(info_sprite)
                    return                 
              
                for _type, requirement in self.requirements.items():
                    vars(self)[_type] -= requirement
                
                
                if issubclass(self.objects[self.object], BaseBuilding):
                    self.Buildings.append(UNbuiltBuilding(self, x, y, max_len=max_length[self.object], time=times[self.object], building=self.object))
                    self.BuildingChangeEnemySpawner(x, y, placing=1, min_dist=150, max_dist=200)
                    #2 bc created lowers it
                elif issubclass(self.objects[self.object], BaseBoat):
                    created = self.objects[self.object](self, x, y)
                    self.Boats.append(created)
                elif issubclass(self.objects[self.object], Person):
                    created = self.objects[self.object](self, x, y)
                    created.path = [created.position]
                    created.update_self(self)
                    self.People.append(created)
                    self.population += 1
                else:
                    raise ValueError(f"{created}   Is not a person, building, or boat.")
                self.updateStorage()
                self.update_text(1)

            return
    def info_on_click(self, x, y):
        x2 = x
        y2 = y

        x += self.player.center_x
        y += self.player.center_y
        x -=  (self.camera.viewport_width / 2)
        y -=  (self.camera.viewport_height / 2)
        
        i = self.graph[round(x/50)][round(y/50)]
        info = ["Land", "Stone", "Sea"][i]
        if arcade.get_sprites_at_point((x, y), self.Trees):
            info += ", Tree"
        elif arcade.get_sprites_at_point((x, y), self.BerryBushes):
            info += ", Berry Bush"
        building = arcade.get_sprites_at_point((x, y), self.Buildings)
        if building:
            if type(building[0]) == UNbuiltBuilding:
                info += f", 1 not built {type(building[0])}"
            else:
                info += f", {type(building[0])}"
        enemies = arcade.get_sprites_at_point((x, y), self.Enemies)
        if len(enemies) == 1:
            info += f", 1 enemy"
        elif len(enemies) > 1:
            info += f", {len(enemies)} enemies"
        boats = arcade.get_sprites_at_point((x, y), self.Boats)
        if len(boats) == 1:
            info += f", 1 boat"
        elif len(boats) > 1:
            info += f", {len(boats)} boats"
            
        people = arcade.get_sprites_at_point((x, y), self.People)
        if len(people) == 1:
            info += f", 1 person"
        elif len(people) > 1:
            info += f", {len(people)} people"
        if arcade.get_distance(x, y, self.player.center_x, self.player.center_y) <= 30:
            info += f", PLAYER"


        info_sprite = UpdatingText(info, self.Alphabet_Textures, 1, width = 100, center_x=x2, center_y=y2)
        self.PopUps.append(info_sprite)
            
    def ui_sprites_update(self, x, y):

        ui = arcade.get_sprites_at_point((x, y), self.ui_sprites)
        if len(ui) > 0:
            self.object = ui[0].name
            self.requirements = requirements[ui[0].name]
            self.object_placement = ui[0].object_placement

            whitespaces = 15-len(ui[0].name)
            string = f"{ui[0].name} " + " "*whitespaces+ "Costs:"
            for x, y in ui[0].requirements.items():
                string += f"{y} {x}, "
            if len(ui[0].requirements.items()) == 0:
                string = string.replace("Costs:", "")

            
            string2 = ""
            try:
                obj = self.objects[ui[0].name](self, 0, 0)
                for x, y in obj.vars.items():
                    if not string2: string2 += ". Creates: "
                    else: string2 += ", "
                    string2 += f"{y} {x}"

                if len(obj.vars.items()) == 0:
                    string2 = string2.replace(". Creates:", "")
                obj.destroy(self)
            except:
                print("PROBLEM ON LINE 966", ui[0].name)
            string += string2

            string += f" Placed On {tiles[ui[0].name].__name__}"

            self.ui_sprite_background.center_x = 200
            self.ui_sprite_text = CustomTextSprite(string, self.Alphabet_Textures, center_x=50, center_y = 100, width = 250)#arcade.create_text_sprite(string, 10, 10, arcade.csscolor.WHITE)#CustomTextSprite(string, self.Alphabet_Textures, Background_Texture="resources/gui/Wood Button2.png", width=len(string)*16)
            
            return True
        else:
            return False
    def clear_uimanager(self):
        for button in self.extra_buttons:
            self.uimanager.remove(button)
        self.extra_buttons = []
            
    def check_sprite_with_enemies(self, obj):
        for enemy in self.Enemies:
            dist_to_object = arcade.get_distance_between_sprites(enemy, obj)
            if dist_to_object > 1500:
                continue
            if enemy.focused_on:
                dist_to_orig = arcade.get_distance_between_sprites(enemy, enemy.focused_on)
            else:
                dist_to_orig = 0
            if dist_to_object < dist_to_orig:
                enemy.focuse_on = obj
                self.calculate_enemy_path(enemy)
    def spawn_enemy(self):
        x, y = self.EnemySpawnPos()
        enemy_pick = "Enemy Archer"#random.choice(["Basic Enemy", "Privateer", "Enemy Archer", "Enemy Arsonist", "Enemy Wizard"])
        #while not self.unlocked[enemy_pick]:
        #    enemy_pick = random.choice(["Basic Enemy", "Privateer", "Enemy Swordsman", "Enemy Archer", "Enemy Arsonist", "Enemy Wizard"])
        enemy_class = {"Basic Enemy":Child, "Privateer":Privateer, "Enemy Archer":Enemy_Slinger, "Enemy Arsonist":Arsonist, "Enemy Wizard":Wizard}[enemy_pick]
        enemy = enemy_class(self, x, y, difficulty=self.hardness_multiplier)
        enemy.focused_on = None
        


        max_i = 100
        if len(self.OpenToEnemies) == 0:
            max_i = 1
        i = 0
        while not self.graph[x/50][y/50] in enemy.movelist:
            pos = self.EnemySpawnPos()
            if pos is not None:
                x, y = pos
            i += 1
            if i >= max_i:
                enemy.destroy(self)
                enemy_pick = "Enemy Archer"#random.choice(["Basic Enemy", "Privateer", "Enemy Archer", "Enemy Arsonist", "Enemy Wizard"])
                #while not self.unlocked[enemy_pick]:
                #    enemy_pick = random.choice(["Basic Enemy", "Privateer", "Enemy Archer", "Enemy Arsonist", "Enemy Wizard"])
                enemy_class = {"Basic Enemy":Child, "Privateer":Privateer, "Enemy Archer":Enemy_Slinger, "Enemy Arsonist":Arsonist, "Enemy Wizard":Wizard}[enemy_pick]
                enemy = enemy_class(self, x, y, difficulty=self.hardness_multiplier)
                enemy.focused_on = None
                i = 0



        enemy.center_x = x
        enemy.center_y = y
        
        self.calculate_enemy_path(enemy)
        enemy.check = True
        self.Enemies.append(enemy)
        
        for person in self.People:
            person.check = True

    def calculate_enemy_path(self, enemy):
        enemy.check = False
        enemy.path = []
        #return 
        building, distance = arcade.get_closest_sprite(enemy, self.Buildings)
        person, distance2 = arcade.get_closest_sprite(enemy, self.People)
        boat, distance3 = arcade.get_closest_sprite(enemy, self.Boats)

        
        bias1 = (distance+5)*enemy.building_bias
        bias2 = (distance2+5)*enemy.people_bias
        bias3 = (distance3+5)*enemy.boat_bias

        if distance > 1500:
            bias1 = float("inf")
        if distance2 > 1500:
            bias2 = float("inf")
        if distance3 > 1500:
            bias3 = float("inf")
        

        if bias1 == float("inf") and bias2  == float("inf") and bias3 == float("inf"):
            return

        num = min(bias1, bias2, bias3)
        if num == bias1:
            obj2 = building
        elif num == bias2:
            obj2 = person
        elif num == bias3:
            obj2 = boat


        path = _AStarSearch(self.graph, enemy.position, obj2.position, allow_diagonal_movement=True, movelist=enemy.movelist, min_dist=enemy.range)
        if not path:
            pass
        elif arcade.get_distance_between_sprites(enemy, obj2) > enemy.range:        
            pass
        if num == bias1:
            enemy.focused_on = building
        elif num == bias2:
            enemy.focused_on = person
        elif num == bias3:
            enemy.focused_on = boat
            
        if len(path) > 1:
            path.pop(0)
            enemy.path = path
            enemy.check = True
            enemy.idle = False
        elif len(path) == 1:
            enemy.path = path
            enemy.check = True
            enemy.idle = False
        else:
            enemy.check = False
    def calculate_path(self, obj, SpriteList, max_distance=1500):
        if len(SpriteList) == 0:
            return
        obj.check = False
        obj.path = []
        #return 
        
        obj2, distance = arcade.get_closest_sprite(obj, SpriteList)
        if obj2 == [] or distance > max_distance:
            return


        path = _AStarSearch(self.graph, obj.position, obj2.position, allow_diagonal_movement=True, movelist=obj.movelist, min_dist=obj.range)
        if path or arcade.get_distance_between_sprites(obj, obj2) <= obj.range: 
            obj.focused_on = obj2
            
        if len(path) > 1:
            path.pop(0)
            obj.path = path
            obj.check = True
            obj.idle = False
        elif len(path) == 1:
            obj.path = path
            obj.check = True
            obj.idle = False
        else:
            obj.check = False
    
    def Move(self, event):
        self.move = True
    def destroy(self, event):
        obj = event.source.obj
        obj.destroy(self, menu_destroy=True)

        pass
    def clean_destroy(self, event):
        obj = event.source.obj
        obj.destroy(self, menu_destroy=True)

    def LightOnFire(self, obj, strength):
        fire = Fire(self, obj.center_x, obj.center_y, strength)
        self.Fires.append(fire)
        obj.fire = fire
        fire.obj = obj
    def leave(self, event):
        person = event.source.obj.remove()
        if person != None:
            self.People.append(person)
    def print_attr(self, event):
        print(vars(event.source.obj))
    def center_camera(self):
        screen_center_x = self.player.center_x - (self.camera.viewport_width / 2)
        screen_center_y = self.player.center_y - (self.camera.viewport_height / 2)
        
        _centered = screen_center_x, screen_center_y
        self.camera.move_to(_centered)
    
    def on_update(self, delta_time):
        #print(1/delta_time)
        self.lacks = []
        if self.speed > 0:
            self.update_text(delta_time)
        [self.PopUps.remove(PopUp) for PopUp in self.PopUps if PopUp.update(delta_time)]
        delta_time *= self.speed
        

        self.Christmas_timer += delta_time
        if self.Christmas_timer >= 135:
            self.Christmas_timer -= 135
            if self.Christmas_music: 
                if self.Christmas_music.player: self.Christmas_music.stop(self.Christmas_music.player)
            self.Christmas_music.player = None

            if not self.Completed_Christmas:
                self.activate_Christmas()
            self.Completed_Christmas = False
            self.christmas_background._set_alpha(0)
        elif self.Christmas_timer >= 120:
            t = -self.Christmas_timer+135
            num = 1-t/15

            if not self.Completed_Christmas:
                self.activate_Christmas()
                self.Completed_Christmas = True


            self.Christmas_music.set_volume(self.Christmas_music.true_volume*t/15)#.1*delta_time
            self.Background_music.set_volume(self.Background_music.true_volume*num)

            num = t/15*255
            self.christmas_background._set_alpha(num)#alpha = num
            index = self.overParticles.index(self.christmas_background)
            self.overParticles.swap(index, -1)
            self.christmas_background.position = self.player.center_x, self.player.center_y

            
        elif self.Christmas_timer >= 105:
            t = self.Christmas_timer-105
            num = 1-t/15
    
            if not self.Christmas_music.player: self.Christmas_music.play()
            
            self.Christmas_music.set_volume(self.Christmas_music.true_volume*t/15)
            self.Background_music.set_volume(self.Background_music.true_volume*num)

            num = t/15*255
            self.christmas_background._set_alpha(num)#.alpha = num
            index = self.overParticles.index(self.christmas_background)
            self.overParticles.swap(index, -1)
            self.christmas_background.position = self.player.center_x, self.player.center_y

        self.player.on_update(delta_time)
        t = time.time()
        self.time_alive += delta_time

        self.timer += delta_time
        if self.timer > 1:
            self.timer -= 1
            self.food -= self.population*(sqrt(self.difficulty))
            self.science += .01/(sqrt(self.difficulty))*self.population
            self.science += .03/(sqrt(self.difficulty))
        if self.food <= 0:
            self.food = 0
            self.toy_amount += delta_time*5
            self.lacks.append("food")

        
            
        if self.population <= 1:
            self.End()
        #Update
        self.updateStorage()
        [fire.update(self, delta_time) for fire in self.Fires]
        [person.update(self, delta_time) for person in self.People]
        [building.update(delta_time, self) for building in self.Buildings]
        [boat.update(self, delta_time) for boat in self.Boats]
        [enemy.update(self, delta_time) for enemy in self.Enemies]

        if self.player.boat: self.player.position = self.player.boat.position
        self.center_camera()
    
        self.spawnEnemy += delta_time
        if self.spawnEnemy >= 0:
            self.spawnEnemy -= 25
            self.spawn_enemy()  
            self.difficulty *= 1.02
        
        if self.population <= 1:
            self.End()      
        t2 = time.time()-t

        variables = vars(self)
        weight = 0
        for resource in ["wood", "stone", "metal"]:
            weight += variables[resource]*item_weight[resource]
        if weight/self.mcsStorage > .98:
            self.lacks.append("Mcs Storage")
        
        if self.population >= self.max_pop:
            self.lacks.append("housing")
        if not self.lacks:
            self.lack_text = None
            return
        window = arcade.get_window()
        x, y = window.width/2, window.height-20
        string = ""
        for lack in self.lacks:
            if string: string += ", "
            else: string += "You lack: "
            string += lack
        self.lack_text = CustomTextSprite(string, self.Alphabet_Textures, center_x=x-200, center_y = y, width = 200, text_margin=14, Background_offset_x=100, Background_offset_y=-50, Background_Texture="resources/gui/Small Text Background.png", Background_scale=2)
    def update_text(self, delta_time):
        self.text_timer += delta_time

        if self.text_timer < 1:
            return
        self.text_timer = 0
        self.text_sprites.clear()
        y = self.camera.viewport_height-20

        output = f"Wood Count: {floor(self.wood)}"
        self.text_sprites.append(CustomTextSprite(output, self.Alphabet_Textures, center_x=55, center_y = y, width = 500, text_margin=14))
        y -= 30

        output = f"Stone Count: {floor(self.stone)}"
        self.text_sprites.append(CustomTextSprite(output, self.Alphabet_Textures, center_x=55, center_y = y, width = 500, text_margin=14))
        y -= 30

        output = f"Food Count: {floor(self.food)}"
        self.text_sprites.append(CustomTextSprite(output, self.Alphabet_Textures, center_x=55, center_y = y, width = 500, text_margin=14))
        y -= 30

        output = f"Science Count: {floor(self.science*10)/10}"
        self.text_sprites.append(CustomTextSprite(output, self.Alphabet_Textures, center_x=55, center_y = y, width = 500, text_margin=14))
        y -= 30

        output = f"Time Alive: {floor(self.time_alive*100)/100}"
        self.text_sprites.append(CustomTextSprite(output, self.Alphabet_Textures, center_x=55, center_y = y, width = 500, text_margin=14))
        y -= 30

        spawntime = -self.spawnEnemy
        output = f"Next Wave: {floor(spawntime*100)/100}"
        self.text_sprites.append(CustomTextSprite(output, self.Alphabet_Textures, center_x=55, center_y = y, width = 500, text_margin=14))
        y -= 30

        output = f"Food Storage:{floor(self.foodStoragePercent*100)}% full"
        self.text_sprites.append(CustomTextSprite(output, self.Alphabet_Textures, center_x=55, center_y = y, width = 500, text_margin=13))
        y -= 30

        output = f"Resource Storage:{floor(self.mcsStoragePercent*100)}% full"
        self.text_sprites.append(CustomTextSprite(output, self.Alphabet_Textures, center_x=55, center_y = y, width = 500, text_margin=13))
        y -= 30

        output = f"{floor(self.toys)} Toys, {floor(self.toys/self.toy_amount)}% of Toys Made"
        self.text_sprites.append(CustomTextSprite(output, self.Alphabet_Textures, center_x=55, center_y = y, width = 500, text_margin=13))
        y -= 30

        num = 75-self.Christmas_timer
        if num < 0:
            num = 90+num
        output = f"Christmas in {round(num*100)/100}"
        self.text_sprites.append(CustomTextSprite(output, self.Alphabet_Textures, center_x=55, center_y = y, width = 500, text_margin=13))
    def updateStorage(self):
        variables = vars(self)
        weight = variables["food"]*item_weight["food"]
        if weight > self.food_storage and prev_frame["food"] < weight: 
            self.lacks.append("food storage")
            variables["food"] = prev_frame["food"]
        elif weight > self.food_storage:
            self.lacks.append("food storage")
        self.foodStoragePercent = weight / self.food_storage

        weight = 0
        for resource in ["wood", "stone", "metal"]:
            weight += variables[resource]*item_weight[resource]
        if weight > self.mcsStorage:
            self.lacks.append("Mcs Storage")
            for resource in ["wood", "stone", "metal"]: 
                variables[resource] = prev_frame[resource]
                
        self.mcsStoragePercent = weight / self.mcsStorage

        variables = vars(self)
        for resource in item_weight.keys():
            prev_frame[resource] = variables[resource]
    

    def generateWorld(self, x_line, y_line, world_gen):

        self.x_line = x_line
        self.y_line = y_line
        # Create cave system using a 2D grid
        grid = create_grid(x_line, y_line)
        initialize_grid(grid)

        template_grid = create_grid(x_line, y_line)
        
        for step in range(100):
            grid, template_grid = do_simulation_step(grid, template_grid)
        
        grid2 = create_grid(x_line, y_line)
        initialize_grid(grid2)
        for step in range(4):
            grid2, template_grid = do_simulation_step(grid2, template_grid)


        # Create sprites based on 2D grid
        
        # This is the simple-to-understand method. Each grid location
        # is a sprite.
        
        if world_gen == "Normal":
            stone_factor = .7
            berry_bush_factor = .6
            tree_factor = .35
        elif world_gen == "Desert":
            stone_factor = .4
            berry_bush_factor = .85
            tree_factor = .7
        elif world_gen == "Forest":
            stone_factor = .2
            berry_bush_factor = .75
            tree_factor = .3

        self.graph = LivingMap(x_line, y_line, x_line*y_line, tilesize=50)
        self.graphlength = x_line+1

        for row in range(y_line):
            for column in range(x_line):
                if grid[row][column] == 1 and grid2[row][column] == 1:
                    random_float = random.random()
                    if random_float < stone_factor:
                        self.addStone(row*50, column*50)
                    else:
                        self.addLand(row*50, column*50)
                elif grid[row][column] == 0:
                    self.addSea(row*50, column*50)
                else:
                    self.addLand(row*50, column*50)
        for land in self.Lands:
            if not 0 < land.center_x < 4950 or not 0 < land.center_y < 4950: continue
            
            x = land.center_x/50
            y = land.center_y/50

            sand = False
            for i in ((0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                if self.graph[x+i[0]][y+i[1]] == 2:
                    sand = True
                    break
            if sand:
                land.texture = arcade.load_texture("resources/Sprites/Sand.png")
                land.typ = "Sand"
            else:
                random_float = random.random()
                if random_float > berry_bush_factor:
                    self.addBerryBush(land.center_x, land.center_y)
                elif random_float > tree_factor:
                    self.addTree(land.center_x, land.center_y)
            land.prev_texture = land.texture
                        
                
        self.place_player(x_line, y_line)
        self.test_enemies(x_line, y_line)
    def place_player(self, x_line, y_line):
        self.player = Player(center_x=0, center_y=0)
        t = time.time()
        while True:
            x = random.randrange(20, x_line-20)
            y = random.randrange(20, y_line-20)

            if self.graph[x][y] != 0:
                continue
            i = 0
            for point in ((0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                if self.graph[x+point[0]][y+point[1]] == 0: i += 1
            if i < 4:
                continue
            x *= 50
            y *= 50

            NumTilesAround = SearchTilesAround(self.graph, (x, y), allow_diagonal_movement=False, movelist=[0])
            if NumTilesAround >= 100:
                break

        
        self.player = Player(center_x=x, center_y=y)#arcade.Sprite("resources/Sprites/Player.png", scale=.5, center_x=x, center_y=y)
        
        num = 0
        for point in ((0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            x2 = x/50+point[0]
            y2 = y/50+point[1]
            if self.graph[x2][y2] != 0:
                continue
            person = Person(self, x2*50, y2*50)
            self.People.append(person)
            num += 1
            if num == 2:
                return
    def test_enemies(self, x_line, y_line):
        t = time.time()
        for row in range(y_line):
            for column in range(x_line):
                if random.random() <= 1 or self.graph[row][column] != 0 or self.graph[row+1][column+1] != 0:
                    continue
                enemy = Enemy_Slinger(self, row*50+50, column*50-50)
                self.Enemies.append(enemy)


                building = Hospital(row*50, column*50)
                #self.BuildingChangeEnemySpawner(row*50, column*50, min_dist=150, max_dist=200)
                building.enemy = None
                self.Buildings.append(building)
        for enemy in self.Enemies:
            self.calculate_enemy_path(enemy)
    
    def addLand(self, x, y):
        land = Land(self, x, y)
        land.prev_texture = land.texture
        self.Lands.append(land)
    def addTree(self, x, y):
        tree = Tree(self, x, y)
        self.Trees.append(tree)
    def addBerryBush(self, x, y):
        berry_bush = BerryBush(self, x, y)
        self.BerryBushes.append(berry_bush)
    def addSea(self, x, y):
        sea = Sea(self, x, y)
        self.Seas.append(sea)
        self.graph[x/50][y/50] = 2
    def addStone(self, x, y):
        stone = Stone(self, x, y)
        self.Stones.append(stone)
        self.graph[x/50][y/50] = 1

    def generateEnemySpawner(self, width, length):

        width *= 50
        length *= 50
        self.EnemyMap = {}
        self.SnowMap = {}
        self.OpenToEnemies = []
        x = 0
        y = 0
        while x <= width:
            self.EnemyMap[x] = {}
            self.SnowMap[x] = {}
            while y <= length:
                self.EnemyMap[x][y] = 0
                self.SnowMap[x][y] = 0
                y += 50

            y = 0
            x += 50
    def EnemySpawnPos(self):
        if len(self.OpenToEnemies) > 0:
            random_num = random.randrange(0, len(self.OpenToEnemies))
            return self.OpenToEnemies[random_num][0], self.OpenToEnemies[random_num][1]
        elif len(self.People) > 0:
            person = self.People[random.randrange(0, len(self.People))]
            return person.center_x, person.center_y
        elif self.population == 0:
            self.End()
        elif len(self.Boats) > 0:
            boat = self.Boats[random.randrange(0, len(self.Boats))]
            return boat.center_x, boat.center_y
        raise ReferenceError("BUG: Either no People in Spritelist or No place open to enemies")
    def BuildingChangeEnemySpawner(self, x, y, placing=1, min_dist=100, max_dist= 300):
        #NOTE: Placing=-1 is for destroying, keep at 1 if placing
        x = round(x/50)*50
        y = round(y/50)*50

        for x2 in range(-max_dist, max_dist, 50):
            if not 0 <= x2+x < 5000:
                continue
            for y2 in range(-max_dist, max_dist, 50):
                if not 0 <= y2+y < 5000:
                    continue

                x1 = x2+x
                y1 = y2+y
                if abs(x2)<=min_dist and abs(y2)<=min_dist:
                    self.EnemyMap[x1][y1] -= placing
                    self.SnowMap[x1][y1] += placing
                else:
                    self.EnemyMap[x1][y1] += placing
    
                #NOTE: UPDATE open to Enemies list
                if self.EnemyMap[x1][y1] > 0:
                    if not (x1, y1) in self.OpenToEnemies:

                        self.OpenToEnemies.append((x1, y1))
                elif (x1, y1) in self.OpenToEnemies:
                    self.OpenToEnemies.remove((x1, y1))
                
                Snow = self.SnowMap[x1][y1]
                land = arcade.get_sprites_at_point((x1, y1), self.Lands)
                if not land:
                    pass
                elif Snow < 1 and land[0].typ == "Snow":
                    land[0].texture = land[0].prev_texture
                    land[0].typ = land[0].prev_typ
                elif Snow >= 1 and land[0].typ != "Snow":
                    land[0].prev_texture = land[0].texture
                    land[0].prev_typ = land[0].typ
                    land[0].typ = "Snow"
                    #gul-li-ble person
                    land[0].texture = arcade.load_texture("resources/Sprites/Snow.png")

    def save(self, event): 
        variables = {}
        self.ui_sprites.clear()

        skip_keys = {
            "window", "camera", "key", "secondary_wrappers", "menu_buttons",
            "selectables", "ui_sprites", "player", "main_button", "menus_button",
            "selectables_button", "under_sprite", "extra_buttons", "text_sprites",
            "audios", "underParticals", "overParticles", "health_bars"
        }
        for key, value in vars(self).items():
            if key in skip_keys:
                continue
            if isinstance(value, arcade.SpriteList):
                variables[key] = self.copy_SpriteList(value)
                outfile = open(f"{self.file_num}",'wb')
            elif isinstance(value, (int, float, dict, list)):
                variables[key] = value
            
        variables[f"player"] = copy(self.player)
        variables["player"].sprite_lists = []
        variables["player"]._sprite_list = []

        
        variables["EnemyMap"] = self.EnemyMap
        variables["OpenToEnemies"] = self.OpenToEnemies
        variables["graph"] = self.graph.graph
        print(type(self.graph.graph))
        
        outfile = open(f"{self.file_num}",'wb')
        pickle.dump(variables, outfile)
        outfile.close()
    def copy_SpriteList(self, sprite_list: arcade.SpriteList):
        """
        Copy(and convert) the spritelist into a list

        So it won't break pickle
        
        :Parameters:
            :sprite_list: arcade.SpriteList
                SpriteList to convert

        :rtype: list
        :return: Converted SpriteList
        """
        sprite_list_copy = []
        for sprite in sprite_list:
            sprite2 = type(sprite)(self, sprite.center_x, sprite.center_y)
            variables = vars(sprite2)
            for key, val in vars(sprite).items():
                #pythonic apperently
                if val.__class__.__module__ == '__builtin__': 
                    variables[key] = val
            sprite2.save(self)
            sprite_list_copy.append(sprite2)
        return sprite_list_copy
    def load(self, file_num):
        infile = open(f"{file_num}", 'rb')
        file = pickle.load(infile)

        for key, val in file.items():
            if isinstance(val, list): 
                if key == "rites_list" or key == "science_list":
                    vars(self)[key] = val
                    continue
                elif key == "graph":
                    print("DEJNNJED")
                    print(type(vars(self)[key]))
                    print(vars(self)[key][10][12])
                    graph = LivingMap(file["x_line"], file["y_line"], file["x_line"]*file["y_line"])
                    vars(self)[key] = val
                for sprite in val:
                    vars(self)[key].append(sprite)
            elif isinstance(val, arcade.SpriteList):
                for sprite in val:
                    vars(self)[key].append(sprite)
            else:
                vars(self)[key] = val
        for key, val in vars(self).items():
            if isinstance(val, arcade.SpriteList): 
                if key == "health_bars":
                    continue
                for sprite in val:
                    sprite.load(self)
        self.player = Player(center_x=file["player"].center_x, center_y=file["player"].center_y)#arcade.Sprite("resources/Sprites/Player.png", scale=.5, center_x=file["player"].center_x, center_y=file["player"].center_y)
        """ self.graph = LivingMap(file["graphlength"], file["graphlength"], file["graphlength"]*file["graphlength"], self.Stones, self.Seas, tilesize=50)
        self.graphlength = file["graphlength"]

        #graph = create_Map(self.graphlength, self.graphlength)
        for stone in self.Stones:
            x, y = stone.center_x/50, stone.center_y/50
            self.graph[x][y] = 1
        for seas in self.Seas:
            x, y = seas.center_x/50, seas.center_y/50
            self.graph[x][y] = 2 """
class MyTutorial(MyGame):
    def __init__(self, menu, file_num=0, world_gen="Normal", difficulty=1):
        super().__init__(menu, file_num, world_gen, difficulty)
        self.sprites = arcade.SpriteList()
        self.step = 1

        self.spawnEnemy = -30
        self.unlocked["Enemy Archer"] = True
        self.unlocked["Enemy Arsonist"] = True
        self.unlocked["Enemy Wizard"] = True


        button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, width=50, height=50, scale=.1, x=50, y=50, offset_x=25, offset_y=25, Texture="resources/gui/Question Mark.png", Pressed_Texture="resources/gui/Question Mark.png", Hovered_Texture="resources/gui/Question Mark.png")
        button.on_click = self.on_question_click
        button.open = False
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center", anchor_y="center",
                child=button, align_x=0, align_y=100)
        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.question = None


        @self.ui_slider.event()
        def on_change(event: UIOnChangeEvent):
            self.label.text = f"speed {self.ui_slider.value*.5:02.0f}x"
            self.speed = self.ui_slider.value*.5
            self.label.fit_content()
            self.indicator_update(event)


        self.indicators = arcade.SpriteList()
        for button in self.uimanager.children[0]:
            if not isinstance(button, arcade.gui.UIAnchorWidget):
                continue
            indicator = arcade.Sprite("resources/gui/exclamation point.png", scale=.25)
            self.indicators.append(indicator)
            
            indicator.button = button
            button.indicator = indicator
        self.indicator_update(None)

        self.floating_question_marks = arcade.SpriteList()
        person = self.People[0]
        sprite = arcade.Sprite("resources/gui/Question Mark.png", scale=.1, center_x=person.center_x+30, center_y=person.center_y+30)
        sprite.tracking = person
        self.floating_question_marks.append(sprite)
        sprite.text_sprites = []
        sprite.text = "Move Elfs on resources to collect it.  Move on buildings and boats to build and work them.  For certian resources you need a building to collect them"
    def indicator_update(self, event):
        if event: event.source.wrapper.indicator.remove_from_sprite_lists()
        for indicator in self.indicators:
            button = indicator.button
            window = arcade.get_window()
            if button.anchor_x == "center": x = window.width/2
            if button.anchor_y == "center": y = window.height/2

            if button.anchor_x == "right": x = window.width
            if button.anchor_y == "top": y = window.height

            if button.anchor_x == "left": x = 0
            if button.anchor_y == "bottom": y = 0

            if button.anchor_x == "left" and button.anchor_y == "top": x, y = x+50, y-50
            if button.anchor_x == "left" and button.anchor_y == "bottom": x, y = x+50, y+50
            
            indicator.center_x = x+button.align_x
            indicator.center_y = y+button.align_y
    
    
    def save(self, event):
        self.indicator_update(event)
    def load(self):
        raise ValueError("")

    def on_question_click(self, event):
        window = arcade.get_window()
        if not self.question: 
            text = CustomTextSprite("Right click to anything to get info.     Press arrows or W/A/S/D to move Santa. Use Santa to move around the map.", self.Alphabet_Textures, width=-200, center_x=window.width/2+event.source.wrapper.align_x-150, center_y=window.height/2+event.source.wrapper.align_y+100, Background_offset_x=260, Background_offset_y=-35, Background_scale=1.5, Background_Texture="resources/gui/Small Text Background.png")
            self.question = text
        else:
            self.question = None
        self.indicator_update(event)
    def on_SelectionMenuclick(self, event):
        super().on_SelectionMenuclick(event)
        self.indicator_update(event)
    def main_button_click(self, event):
        super().main_button_click(event)
        self.indicator_update(event)
    def menus_button_click(self, event):
        super().menus_button_click(event)
        self.indicator_update(event)
    def selectables_click(self, event):
        super().selectables_click(event)
        self.indicator_update(event)
    def expand_button_click(self, event):
        super().expand_button_click(event)
        self.indicator_update(event)
    def speed_bar_change(self, event):
        super().speed_bar_change(event)
        self.indicator_update(event)

    def on_ScienceMenuclick(self, event):
        super().on_ScienceMenuclick(event)
        self.indicator_update(event)
    def on_VolumeMenuclick(self, event):
        super().on_VolumeMenuclick(event)
        self.indicator_update(event)
    def return_to_menu(self, event):
        if self.Christmas_music: 
            if self.Christmas_music.player: self.Christmas_music.stop(self.Christmas_music.player)
        self.Christmas_music = None
        super().return_to_menu(event)
        self.indicator_update(event)
    def switch_val(self, event):
        super().switch_val(event)
        self.indicator_update(event)

    def on_update(self, delta_time):
        super().on_update(delta_time)
        for mark in self.floating_question_marks:
            mark.center_x = mark.tracking.center_x+30
            mark.center_y = mark.tracking.center_y+30
        
    def on_mouse_press(self, x, y, button, modifiers):
        x2 = x
        y2 = y

        x += self.player.center_x
        y += self.player.center_y
        x -=  (self.camera.viewport_width / 2)
        y -=  (self.camera.viewport_height / 2)
        marks = sprites_in_range(30, (x, y), self.floating_question_marks)
        if marks:
            if marks[0].text_sprites:
                marks[0].text_sprites = []
                return
            marks[0].text_sprites.clear()

            words = marks[0].text.split("  ")
            y = 150
            for word in words: 
                if y == 150: marks[0].text_sprites.append(CustomTextSprite(word, self.Alphabet_Textures, width = -marks[0].center_x+700, center_x = marks[0].center_x-100, center_y = marks[0].center_y+y, Background_Texture="resources/gui/Small Text Background.png", Background_offset_x=marks[0].center_x/2-100, Background_offset_y=-50, Background_scale=2))
                else: marks[0].text_sprites.append(CustomTextSprite(word, self.Alphabet_Textures, width = -marks[0].center_x+650, center_x = marks[0].center_x-100, center_y = marks[0].center_y+y))
                y -= 30
            return
        super().on_mouse_press(x2, y2, button, modifiers)
    def on_draw(self):
        self.sprites.draw()
        super().on_draw()
        self.camera.use()
        for mark in self.floating_question_marks:
            mark.draw()
            if mark.text_sprites: 
                for sprite in mark.text_sprites:
                    sprite.draw()

        self.not_scrolling_camera.use()
        self.sprites.draw()
        self.indicators.draw()

        if self.question: self.question.draw()
    def spawn_enemy(self):
        #super().spawn_enemy()
        x, y = self.EnemySpawnPos()
        enemy_pick = random.choice(["Basic Enemy", "Privateer", "Enemy Archer", "Enemy Arsonist", "Enemy Wizard"])
        while not self.unlocked[enemy_pick]:
            enemy_pick = random.choice(["Basic Enemy", "Privateer", "Enemy Swordsman", "Enemy Archer", "Enemy Arsonist", "Enemy Wizard"])
        enemy_class = {"Basic Enemy":Child, "Privateer":Privateer, "Enemy Archer":Enemy_Slinger, "Enemy Arsonist":Arsonist, "Enemy Wizard":Wizard}[enemy_pick]
        enemy = enemy_class(self, x, y, difficulty=self.hardness_multiplier)
        enemy.focused_on = None
        


        max_i = 100
        if len(self.OpenToEnemies) == 0:
            max_i = 1
        i = 0
        while not self.graph[x/50][y/50] in enemy.movelist:
            pos = self.EnemySpawnPos()
            if pos is not None:
                x, y = pos
            i += 1
            if i >= max_i:
                enemy.destroy(self)
                enemy_pick = random.choice(["Basic Enemy", "Privateer", "Enemy Archer", "Enemy Arsonist", "Enemy Wizard"])
                while not self.unlocked[enemy_pick]:
                    enemy_pick = random.choice(["Basic Enemy", "Privateer", "Enemy Archer", "Enemy Arsonist", "Enemy Wizard"])
                enemy_class = {"Basic Enemy":Child, "Privateer":Privateer, "Enemy Archer":Enemy_Slinger, "Enemy Arsonist":Arsonist, "Enemy Wizard":Wizard}[enemy_pick]
                enemy = enemy_class(self, x, y, difficulty=self.hardness_multiplier)
                enemy.focused_on = None
                i = 0

        enemy.center_x = x
        enemy.center_y = y
        
        self.calculate_enemy_path(enemy)
        enemy.check = True
        self.Enemies.append(enemy)
        
        for person in self.People:
            person.check = True
        
        sprite = arcade.Sprite("resources/gui/Question Mark.png", scale=.1, center_x=enemy.center_x+30, center_y=enemy.center_y+30)
        self.floating_question_marks.append(sprite)
        sprite.tracking = enemy
        sprite.text_sprites = []
        enemy_name = {"Basic Enemy":"Child, close ranged enemy. Prefers people", 
        "Privateer":"Privateer, shoots an arrow. Prefers boats", 
        "Enemy Archer":"Enemy_Slinger, shoots an arrow. Prefers people", 
        "Enemy Arsonist":"Arsonist, starts fires. Stop the firest with Fire Stations. Prefers buildings", 
        "Enemy Wizard":"Wizard, has 2 types of attacks. Does splash damage. Prefers people"}[enemy_pick]
        sprite.text = f"{enemy_name}"

class EndMenu(arcade.View):

    def __init__(self, history, game,  menu):
        self.menu = menu
        self.game_view = game
        
        super().__init__()
        self.Christmas_timer = 30
        self.spawnEnemy = 0
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)

        # Reset the viewport, necessary if we have a scrolling game and we need
        # to reset the viewport back to the start so we can see what we draw.
        arcade.set_viewport(0, self.window.width, 0, self.window.height)

        self.click_sound = game.click_sound
        self.Background_music = game.Background_music
        self.Christmas_music = game.Christmas_music

        self.background = arcade.Sprite("resources/gui/Large Bulletin.png", scale=3.6, center_x=370, center_y=180)
        self.christmas_background = arcade.Sprite("resources/gui/ChristmasOverlay.png", scale=.25, center_x=370, center_y=180)
        self.christmas_overlay = None #arcade.Sprite("resouces/gui/Large Bulletin.png", scale = .25)

        self.texts = []

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        textures = arcade.load_spritesheet("resources/gui/Wooden Font.png", 14, 24, 12, 70, margin=1)
        self.Alphabet_Textures = {" ":None}
        string = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyz.:,%/-+_"
        for i in range(len(string)):
            self.Alphabet_Textures[string[i]] = textures[i]
  
        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Return", width=140, height=50, x=0, y=50, text_offset_x = 10, text_offset_y = 30, offset_x=75, offset_y=25)
        start_button.on_click = self.on_return
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x",anchor_y="center_y",child=start_button, align_x=0, align_y=-100)
        self.uimanager.add(wrapper)

        #self.check_game_save()
        self.texts.append(CustomTextSprite(f"You Died. ", self.Alphabet_Textures, center_x=600, center_y = 600, width = 1000, scale = 4, text_margin=50))
        if history == 0: string = "You gained no history"
        else: string = f"You gained: {round(history*10)/10} History"
        self.texts.append(CustomTextSprite(f"You were alive for {round(game.time_alive*100)/100} seconds.  {string}", self.Alphabet_Textures, center_x=300, center_y = 50, width = 5000, text_margin=16))

        main_button = CustomUIFlatButton(self.game_view.Alphabet_Textures, click_sound = self.game_view.click_sound, width=50, height=50, scale=.05, x=0, y=50, offset_x=25, offset_y=25, Texture="resources/gui/Question Mark.png", Pressed_Texture="resources/gui/Question Mark.png", Hovered_Texture="resources/gui/Question Mark.png")
        main_button.on_click = self.on_question_click
        main_button.open = False
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center", anchor_y="center",
                child=main_button, align_x=0, align_y=-200)
        main_button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.question = None


        window = arcade.get_window()
        self.on_resize(window.width, window.height)
    def on_resize(self, width: int, height: int):
        scale1, scale2 = width/218, height/140
        larger = max(scale1, scale2)
        self.background.center_x = width/2-7*larger/3.6
        self.background.center_y = height/2-75*larger/3.6
        self.background._set_scale(larger)

        self.christmas_background.position = width/2, height/2
        self.christmas_background.scale = .25*max(width/1240, height/900)

        y = height/2-35
        for text in self.texts:
            for sprite in text.Sprite_List:
                sprite.center_y = y
            y -= 30

        return super().on_resize(width, height)         

    def on_question_click(self, event):
        window = arcade.get_window()
        if not self.question: 
            text = CustomTextSprite("You lose once you have less than 2 elfs alive. You get history based on how long you lived. See Progress Tree to use it. You start getting history after 5 minutes, so you can not spam create worlds", self.game_view.Alphabet_Textures, width=-150, center_x=window.width/2+event.source.wrapper.align_x-150, center_y=window.height/2+event.source.wrapper.align_y-80, Background_offset_x=220, Background_offset_y=-25, Background_scale=1.6, Background_Texture="resources/gui/Small Text Background.png")
            self.texts.append(text)
            self.question = text
        else:
            self.texts.remove(self.question)
            self.question = None
    def on_return(self, event):
        self.uimanager.disable()
        self.menu.uimanager.enable()
        self.window.show_view(self.menu)
    def on_show(self):
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)
        arcade.set_viewport(0, self.window.width, 0, self.window.height)
    def on_draw(self):
        """ Draw this view """
        arcade.start_render()
        self.background.draw()
        self.christmas_background.draw()

        self.uimanager.draw()
        for text in self.texts: text.draw()
class ChristmasMenu(arcade.View):
    def __init__(self, game):
        self.game_view = game
        self.window = arcade.get_window()
        super().__init__(self.window)
        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()
        self.Background = arcade.Sprite("resources/gui/Christmas_menu_Background.png", center_x=self.window.width/2, center_y=self.window.height/2, scale = 10)

        self.texts = []
        if self.game_view.toys >= self.game_view.toy_amount:
            self.texts.append(CustomTextSprite(f"We exceded by {self.game_view.toy_amount-self.game_view.toys} toys.", self.game_view.Alphabet_Textures, center_x=self.window.width/3, center_y = self.window.height/1.5, width = 5000))
            self.texts.append(CustomTextSprite(f"Next Year The Children will expect at least {math.ceil(self.game_view.toy_amount*1.08)} toys", self.game_view.Alphabet_Textures, center_x=self.window.width/4, center_y = self.window.height/1.5-40, width = 5000))
            
            self.game_view.toy_amount *= 1.08
        else:
            self.texts.append(CustomTextSprite(f"We were short of {self.game_view.toy_amount-self.game_view.toys} toys.", self.game_view.Alphabet_Textures, center_x=self.window.width/3, center_y = self.window.height/1.5, width = 5000))
            self.texts.append(CustomTextSprite(f"Over Excited Children will be {round(1-self.game_view.toys/self.game_view.toy_amount, 2)*100} % more dangerous.", self.game_view.Alphabet_Textures, center_x=self.window.width/4, center_y = self.window.height/1.5-40, width = 5000))
            self.texts.append(CustomTextSprite(f"Next Year The Children will expect at least {math.ceil(self.game_view.toy_amount*1.1)} toys", self.game_view.Alphabet_Textures, center_x=self.window.width/4, center_y = self.window.height/1.5-80, width = 5000))
            self.game_view.difficulty += self.game_view.toys/self.game_view.toy_amount
            self.game_view.toy_amount *= 1.1
            if self.game_view.toy_amount > 400 and self.game_view.difficulty >= 5:
                if not self.game_view.unlocked["Enemy Wizard"]:
                    self.texts.append(CustomTextSprite(f"Some Children Got Their Hands on Wands", self.game_view.Alphabet_Textures, center_x=self.window.width/4, center_y = self.window.height/1.5-120, width = 5000))
                self.game_view.unlocked["Enemy Wizard"] = True
            elif self.game_view.toy_amount > 300 and self.game_view.difficulty >= 3:
                if not self.game_view.unlocked["Enemy Arsonist"]:
                    self.texts.append(CustomTextSprite(f"Some Children Got Their Hands on Bombs", self.game_view.Alphabet_Textures, center_x=self.window.width/4, center_y = self.window.height/1.5-120, width = 5000))
                self.game_view.unlocked["Enemy Arsonist"] = True
            elif self.game_view.toy_amount > 200 and self.game_view.difficulty >= 2:
                if not self.game_view.unlocked["Enemy Archer"]:
                    self.texts.append(CustomTextSprite(f"Some Children Got Their Hands on Bows", self.game_view.Alphabet_Textures, center_x=self.window.width/4, center_y = self.window.height/1.5-120, width = 5000))
                self.game_view.unlocked["Enemy Archer"] = True
        self.game_view.toys -= self.game_view.toy_amount
        if self.game_view.toys < 0: self.game_view.toys = 0
        main_button = CustomUIFlatButton(self.game_view.Alphabet_Textures, click_sound = self.game_view.click_sound, text="Exit", width=140, height=50, x=0, y=50, text_offset_x = 16, text_offset_y=35, offset_x=75, offset_y=25)
        main_button.on_click = self.exit
        main_button.open = False
        self.main_button = main_button
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center", anchor_y="center",
                child=main_button, align_x=0, align_y=-150)
        main_button.wrapper = wrapper
        self.uimanager.add(wrapper)


        main_button = CustomUIFlatButton(self.game_view.Alphabet_Textures, click_sound = self.game_view.click_sound, width=50, height=50, scale=.05, x=0, y=50, offset_x=25, offset_y=25, Texture="resources/gui/Question Mark.png", Pressed_Texture="resources/gui/Question Mark.png", Hovered_Texture="resources/gui/Question Mark.png")
        main_button.on_click = self.on_question_click
        main_button.open = False
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center", anchor_y="center",
                child=main_button, align_x=0, align_y=-200)
        main_button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.question = None
    def on_resize(self, width: int, height: int):
        self.game_view.on_resize(width, height)
        return super().on_resize(width, height)
    def on_question_click(self, event):
        window = arcade.get_window()
        if not self.question: 
            text = CustomTextSprite("Make enough toys for the Children for Christmas or they will become stronger.  Happens every 2 minutes. Toys to be made increases if your elfs starve", self.game_view.Alphabet_Textures, width=-150, center_x=window.width/2+event.source.wrapper.align_x-200, center_y=window.height/2+event.source.wrapper.align_y-90, Background_offset_x=250, Background_offset_y=-25, Background_scale=1.5, Background_Texture="resources/gui/Small Text Background.png")
            self.texts.append(text)
            self.question = text
        else:
            self.texts.remove(self.question)
            self.question = None
    def on_draw(self):
        arcade.start_render()
        self.game_view.on_draw()

        self.Background.draw()
        for text in self.texts: text.draw()
        self.uimanager.draw()
    def exit(self, event):
        self.uimanager.disable()
        self.game_view.uimanager.enable()

        self.window.show_view(self.game_view)
    def on_update(self, delta_time: float):
        for text in self.texts:
            if text.update(delta_time):
                self.texts.remove(text)
        return super().on_update(delta_time)

class startMenu(arcade.View):

    def __init__(self):
        
        super().__init__()
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)

        # Reset the viewport, necessary if we have a scrolling game and we need
        # to reset the viewport back to the start so we can see what we draw.
        arcade.set_viewport(0, self.window.width, 0, self.window.height)

        self.audios = []
        self.audio_type_vols = {"Overall":1, "UI":1, "Background":1}

        self.click_sound = Sound("resources/audio/click.wav")
        self.click_sound.start_vol = 5
        self.click_sound.type = "UI"
        self.click_sound.player = None
        self.audios.append(self.click_sound)

        self.Background_music = Sound("resources/audio/magical-christmas-paul-yudin-main-version-19227-01-40.wav")
        self.Background_music.start_vol = .1
        self.Background_music.type = "Background"
        self.audios.append(self.Background_music)
        self.Background_music.play(loop=True)

        self.Christmas_music = Sound("resources/audio/deck-the-halls-kevin-macleod-main-version-04-25-9985.wav")
        self.Christmas_music.start_vol = .1
        self.Christmas_music.type = "Background"
        self.Christmas_music.player = None
        self.audios.append(self.Christmas_music)
        self.update_audio()
        
        self.Background_music.true_volume = self.Background_music.volume
        self.Christmas_music.true_volume = self.Christmas_music.volume
        


        self.background = arcade.Sprite("resources/gui/Large Bulletin.png", scale=3.6, center_x=370, center_y=180)
        self.christmas_background = arcade.Sprite("resources/gui/ChristmasOverlay.png", scale=.25, center_x=370, center_y=180)

        self.texts = []

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        textures = arcade.load_spritesheet("resources/gui/Wooden Font.png", 14, 24, 12, 70, margin=1)
        self.Alphabet_Textures = {" ":None}
        string = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyz.:,%/-+_"
        for i in range(len(string)):
            self.Alphabet_Textures[string[i]] = textures[i]

        self.texts.append(CustomTextSprite("SantaFest Destiny", self.Alphabet_Textures, scale=5, width=1000, center_x=250, center_y=600, text_margin=60))

  
        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="World1", width=140, height=50, x=0, y=50, text_offset_x = 10, text_offset_y=35, offset_x=75, offset_y=25)
        start_button.on_click = self.Start
        start_button.world_num = 1
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x",anchor_y="center_y",child=start_button, align_x=0, align_y=100)
        start_button.wrapper = wrapper
        self.uimanager.add(wrapper)

        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="World2", width=140, height=50, x=0, y=50, text_offset_x = 10, text_offset_y=35, offset_x=75, offset_y=25)
        start_button.on_click = self.Start
        start_button.world_num = 2
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x",anchor_y="center_y",child=start_button, align_x=0, align_y=0)
        start_button.wrapper = wrapper
        self.uimanager.add(wrapper)

        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="World3", width=140, height=50, x=0, y=50, text_offset_x = 10, text_offset_y=35, offset_x=75, offset_y=25)
        start_button.on_click = self.Start
        start_button.world_num = 3
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x",anchor_y="center_y",child=start_button, align_x=0, align_y=-100)
        start_button.wrapper = wrapper
        self.uimanager.add(wrapper)



        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Tutorial", width=140, height=50, x=0, y=50, text_margin=14, text_offset_x =-6, text_offset_y = 35, offset_x=75, offset_y=25)
        start_button.on_click = self.start_Tutorial
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x",anchor_y="center_y",child=start_button, align_x=0, align_y=-200)
        start_button.wrapper = wrapper
        self.uimanager.add(wrapper)


        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Progress  Tree", width=140, height=50, x=0, y=50, text_margin=14, text_offset_x = -4, text_offset_y=35, offset_x=75, offset_y=25)
        start_button.on_click = self.on_scienceMenuclick
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="left",anchor_y="top",child=start_button, align_x=20, align_y=-20)
        start_button.wrapper = wrapper
        self.uimanager.add(wrapper)

        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Volume", width=140, height=50, x=0, y=50, text_margin=14, text_offset_x = 10, text_offset_y=35, offset_x=75, offset_y=25)
        start_button.on_click = self.VolumeMenu
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="left",anchor_y="top",child=start_button, align_x=20, align_y=-70)
        start_button.wrapper = wrapper
        self.uimanager.add(wrapper)

        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Credits", width=140, height=50, x=0, y=50, text_margin=14, text_offset_x = 10, text_offset_y=35, offset_x=75, offset_y=25)
        start_button.on_click = self.CreditsMenu
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="left",anchor_y="top",child=start_button, align_x=20, align_y=-120)
        start_button.wrapper = wrapper
        self.uimanager.add(wrapper)

        self.check_game_save()

        window = arcade.get_window()
        self.on_resize(window.width, window.height)
    def check_game_save(self):
        try:
            with open("resources/game.json", "r") as read_file:
                p = json.load(read_file)
            return
        except:
            pass
        
        with open("resources/game.json", "w") as write_file:
            p = {}
            p["Money"] = 0
            p["science_menu"] = self.load_sciences()
            json.dump(p, write_file)
    def load_sciences(self):
        with open("resources/GameBase copy.json", "r") as read_file:
            ScienceMenuInfo = json.load(read_file)["ScienceMenu"]
        
        return [bool(button[8]) for button in ScienceMenuInfo]
    def on_resize(self, width: int, height: int):
        scale1, scale2 = width/218, height/140
        larger = max(scale1, scale2)
        self.background.center_x = width/2-7*larger/3.6
        self.background.center_y = height/2-75*larger/3.6
        self.background._set_scale(larger)

        self.christmas_background.position = width/2, height/2
        self.christmas_background.scale = .25*max(width/1240, height/900)
        return super().on_resize(width, height)         
        
    def VolumeMenu(self, event):
        self.uimanager.disable()
        Menu = VolumeMenu(self)
        self.window.show_view(Menu)
    def CreditsMenu(self, event):
        self.uimanager.disable()
        Menu = CreditsMenu(self)
        self.window.show_view(Menu)
    def update_audio(self):
        for audio in self.audios:
            audio.volume = audio.start_vol*self.audio_type_vols[audio.type]*self.audio_type_vols["Overall"]
            audio.source.volume = audio.volume
            if audio.player:
                audio.player.volume = audio.volume

    def Start(self, event):
        if self.button == 4:
            window = arcade.get_window()
            width, height = window.width, window.height
            x = width/2+event.source.wrapper.align_x
            y = height/2+event.source.wrapper.align_y
            text = UpdatingText(f"Starts the Game.", self.Alphabet_Textures, 10, center_x=x, center_y = y, width = 200, Background_Texture="resources/gui/Small Text Background.png")
            self.texts.append(text)
            return
        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)
        self.uimanager.disable()
        Game = CreateWorld(self, event.source.world_num)
        self.window.show_view(Game)
    def start_Tutorial(self, event):
        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)
        self.uimanager.disable()
        Game = MyTutorial(self, file_num=None, world_gen="Normal", difficulty=1)#CreateWorld(self, event.source.world_num)
        self.window.show_view(Game)
    def on_scienceMenuclick(self, event):
        if self.button == 4:
            window = arcade.get_window()
            width, height = window.width, window.height
            x = event.source.wrapper.align_x
            y = height+event.source.wrapper.align_y
            text = UpdatingText(f"This Menu Upgrades the Science Tree in Game.", self.Alphabet_Textures, 10, center_x=x, center_y = y, width = 300, Background_Texture="resources/gui/Small Text Background.png")
            self.texts.append(text)
            return

        scienceMenu = UpgradeScienceMenu(self)
        self.uimanager.disable()
        self.window.show_view(scienceMenu)
    def on_show(self):
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)
        arcade.set_viewport(0, self.window.width, 0, self.window.height)
    def on_draw(self):
        """ Draw this view """
        arcade.start_render()
        self.background.draw()
        self.christmas_background.draw()

        self.uimanager.draw()
        for text in self.texts: text.draw()

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        self.button = button
        return super().on_mouse_press(x, y, button, modifiers)
    def on_update(self, delta_time: float):
        for text in self.texts:
            if text.update(delta_time):
                self.texts.remove(text)
        return super().on_update(delta_time)
class CreateWorld(arcade.View):

    def __init__(self, menu, file_num):
        super().__init__()
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)
        arcade.set_viewport(0, self.window.width, 0, self.window.height)
        self.click_sound = menu.click_sound
        self.Background_music = menu.Background_music
        self.Christmas_music = menu.Christmas_music

        self.audios = menu.audios
        self.audio_type_vols = menu.audio_type_vols

        self.background = arcade.Sprite("resources/gui/Large Bulletin.png", scale=3.6, center_x=370, center_y=180)
        self.christmas_background = arcade.Sprite("resources/gui/ChristmasOverlay.png", scale=.25, center_x=370, center_y=180)

        self.texts = []#arcade.SpriteList(use_spatial_hash=True, is_static=True)
        
        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        self.menu = menu
        self.file_num = file_num

        
        textures = arcade.load_spritesheet("resources/gui/Wooden Font.png", 14, 24, 12, 70, margin=1)

        self.Alphabet_Textures = {" ":None}
        string = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyz.:,%/-+_"
        for i in range(len(string)):
            self.Alphabet_Textures[string[i]] = textures[i]


        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Start", width=140, height=50, x=0, y=50, text_offset_y = 35, text_offset_x = 16, offset_x=75, offset_y=25)
        start_button.on_click = self.Start
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x",anchor_y="center_y",child=start_button, align_x=0, align_y=-100)
        self.uimanager.add(wrapper)

        text = CustomTextSprite("World Type:", self.Alphabet_Textures, center_x=300, center_y = 430, width = 500)
        text.org_x = -75
        text.org_y = 180
        self.texts.append(text)


        self.gen_list = ["Normal", "Desert", "Forest"]
        self.gen_list_index = 0
        button = CustomUIFlatButton(self.Alphabet_Textures, text="Normal", width=140, height=50, x=0, y=0, text_offset_x = 15, text_offset_y = 35, text_scale=1, offset_x=75, offset_y=24, Pressed_Texture = "resources/gui/Wood Button.png")
        #start_button.on_click = self.Generation_change 
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x",anchor_y="center_y",child=button, align_x=0, align_y=150)
        self.uimanager.add(wrapper)
        button.set_text(self.gen_list[self.gen_list_index], self.Alphabet_Textures)

        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, width=40, height=50, scale=1, x=30, y=50, text_offset_x = 0, offset_x=30, offset_y=8, Texture="resources/gui/Right Pointer.png", Hovered_Texture="resources/gui/Right Pointer.png", Pressed_Texture="resources/gui/Right Pointer.png")
        start_button.direction = 1#right
        start_button.button = button
        start_button.on_click = self.Generation_change 
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x",anchor_y="center_y",child=start_button, align_x=80, align_y=150)
        self.uimanager.add(wrapper)

        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, width=40, height=50, scale=1, x=20, y=50, text_offset_x = 0, offset_x=20, offset_y=0, Texture="resources/gui/Left Pointer.png", Hovered_Texture="resources/gui/Left Pointer.png", Pressed_Texture="resources/gui/Left Pointer.png")
        start_button.direction = -1#left
        start_button.button = button
        start_button.on_click = self.Generation_change 
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x",anchor_y="center_y",child=start_button, align_x=-80, align_y=150)
        self.uimanager.add(wrapper)


        text = CustomTextSprite("Difficulty:", self.Alphabet_Textures, center_x=300, center_y = 330, width = 500)
        text.org_x = -75
        text.org_y = 80
        self.texts.append(text)


        self.difficulty_list = [" Easy ", "Normal", " Hard "]
        self.difficulty_list_index = 0
        button = CustomUIFlatButton(self.Alphabet_Textures, text="Easy", width=140, height=50, x=0, y=50, text_offset_x = 10, text_offset_y = 35, offset_x=75, offset_y=24, Pressed_Texture = "resources/gui/Wood Button.png")
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x",anchor_y="center_y",child=button, align_x=0, align_y=50)
        self.uimanager.add(wrapper)
        button.set_text(self.difficulty_list[self.difficulty_list_index], self.Alphabet_Textures)

        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, width=40, height=50, scale=1, x=30, y=50, text_offset_x = 0, offset_x=30, offset_y=8, Texture="resources/gui/Right Pointer.png", Hovered_Texture="resources/gui/Right Pointer.png", Pressed_Texture="resources/gui/Right Pointer.png")
        start_button.direction = 1#right
        start_button.button = button
        start_button.on_click = self.Difficulty_change
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x",anchor_y="center_y",child=start_button, align_x=80, align_y=50)
        self.uimanager.add(wrapper)

        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, width=40, height=50, scale=1, x=20, y=50, text_offset_x = 0, offset_x=20, offset_y=0, Texture="resources/gui/Left Pointer.png", Hovered_Texture="resources/gui/Left Pointer.png", Pressed_Texture="resources/gui/Left Pointer.png")
        start_button.direction = -1#left
        start_button.button = button
        start_button.on_click = self.Difficulty_change
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x",anchor_y="center_y",child=start_button, align_x=-80, align_y=50)
        self.uimanager.add(wrapper)


        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Clear Data", width=140, height=50, text_offset_y = 35, text_offset_x = 16, offset_x=75, offset_y=25)
        start_button.on_click = self.Delete_data
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x",anchor_y="center_y",child=start_button, align_x=0, align_y=-50)
        start_button.wrapper = wrapper
        self.uimanager.add(wrapper)

        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Return", width=140, height=50, x=0, y=50, text_margin=14, text_offset_y = 35, text_offset_x = 10, offset_x=75, offset_y=25)
        start_button.on_click = self.Return
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="left",anchor_y="top",child=start_button, align_x=20, align_y=-20)
        self.uimanager.add(wrapper)
        
        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Volume", width=140, height=50, x=0, y=50, text_margin=14, text_offset_y = 35, text_offset_x = 10, offset_x=75, offset_y=25)
        start_button.on_click = self.VolumeMenu
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="left",anchor_y="top",child=start_button, align_x=20, align_y=-70)
        self.uimanager.add(wrapper)

        window = arcade.get_window()
        width, height = window.width, window.height
        for text in self.texts:
            text.center_x = width/2+text.org_x
            text.center_y = height/2+text.org_y
            text.update_text(text.text, self.Alphabet_Textures, center_x = text.center_x, center_y = text.center_y)
        
        self.christmas_background = arcade.Sprite("resources/gui/ChristmasOverlay.png", scale=.25, center_x=370, center_y=180)
        
        self.on_resize(window.width, window.height)
    def on_resize(self, width: int, height: int):
        scale1, scale2 = width/218, height/140
        larger = max(scale1, scale2)
        self.background.center_x = width/2-7*larger/3.6
        self.background.center_y = height/2-75*larger/3.6
        self.background._set_scale(larger)

        self.christmas_background.position = width/2, height/2
        self.christmas_background.scale = .25*max(width/1240, height/900)

        for text in self.texts:
            text.center_x = width/2+text.org_x
            text.center_y = height/2+text.org_y
            text.update_text(text.text, self.Alphabet_Textures, center_x = text.center_x, center_y = text.center_y)        
        return super().on_resize(width, height)

    def Delete_data(self, event):
        window = arcade.get_window()
        width, height = window.width, window.height
        x = event.source.wrapper.align_x
        y = height+event.source.wrapper.align_y
        text = UpdatingText(f"Deletes Save File if there is one.", self.Alphabet_Textures, 20, center_x=x, center_y = y, width = 300, Background_Texture="resources/gui/Small Text Background.png")
        self.texts.append(text)
        
        file = open(f"{self.file_num}", "r+")
        file.truncate() 
    def Generation_change(self, event):
        self.gen_list_index += event.source.direction
        if self.gen_list_index >= len(self.gen_list):
            self.gen_list_index = 0
        elif self.gen_list_index < 0:
            self.gen_list_index = len(self.gen_list) - 1
        event.source.button.set_text(self.gen_list[self.gen_list_index], self.Alphabet_Textures)
    def Difficulty_change(self, event):
        self.difficulty_list_index += event.source.direction
        if self.difficulty_list_index >= len(self.difficulty_list):
            self.difficulty_list_index = 0
        elif self.difficulty_list_index < 0:
            self.difficulty_list_index = len(self.difficulty_list) - 1
        event.source.button.set_text(self.difficulty_list[self.difficulty_list_index], self.Alphabet_Textures)


    def Start(self, event):
        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)
        self.uimanager.disable()
        Game = MyGame(self.menu, file_num=self.file_num, world_gen=self.gen_list[self.gen_list_index], difficulty=self.difficulty_list_index+1)
        self.window.show_view(Game)
    def Return(self, event):
        self.uimanager.disable()
        self.menu.uimanager.enable()
        self.window.show_view(self.menu)
    def VolumeMenu(self, event):
        self.uimanager.disable()
        Game = VolumeMenu(self)
        self.window.show_view(Game)
    def update_audio(self):
        for audio in self.audios:
            audio.volume = audio.start_vol*self.audio_type_vols[audio.type]*self.audio_type_vols["Overall"]
            audio.source.volume = audio.volume
            if audio.player:
                audio.player.volume = audio.volume


    def on_show(self):
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)

        # Reset the viewport, necessary if we have a scrolling game and we need
        # to reset the viewport back to the start so we can see what we draw.
        arcade.set_viewport(0, self.window.width, 0, self.window.height)
    def on_draw(self):
        """ Draw this view """
        arcade.start_render()
        self.background.draw()
        self.christmas_background.draw()

        self.uimanager.draw()
        for text in self.texts: text.draw()
    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        self.button = button
        return super().on_mouse_press(x, y, button, modifiers)
    def on_update(self, delta_time: float):
        for text in self.texts:
            if text.update(delta_time):
                self.texts.remove(text)
        return super().on_update(delta_time)

class CreditsMenu(arcade.View):
    def __init__(self, menu):
        self.texts = []
        self.menu = menu
        self.window = arcade.get_window()
        super().__init__(self.window)

        self.background = arcade.Sprite("resources/gui/Large Bulletin.png", scale=3.6, center_x=370, center_y=180)
        self.christmas_background = arcade.Sprite("resources/gui/ChristmasOverlay.png", scale=.25, center_x=370, center_y=180)

    
        x = 150
        y = self.window.height/1.5+40
        self.texts.append(CustomTextSprite(f"Credits", self.menu.Alphabet_Textures, center_x=x, center_y = y, scale=4, text_margin = 60, width = 500))
        y -= 40
        self.texts.append(CustomTextSprite(f"The Arcade Library by Paul Vincent Craven", self.menu.Alphabet_Textures, center_x=x, center_y = y, width = 500))
        y -= 40
        self.texts.append(CustomTextSprite(f"Christmas Over Lay From https://www.freepik.com/free-vector/watercolor-christmas  -background_19963694.htm", self.menu.Alphabet_Textures, center_x=x, center_y = y, text_scale=2, text_margin = 13, width = 500))
        y -= 60
        self.texts.append(CustomTextSprite(f"Wooden Buttons are From https://www.freepik.com/free-vector/wooden-buttons  -user-interface-design-game-video-player-website-vector-cartoon-set-brown  _18056387.htm", self.menu.Alphabet_Textures, center_x=x, center_y = y, scale=1, text_margin = 16, width = 500))
        y -= 60
        self.texts.append(CustomTextSprite(f"Silver Buttons are From https://www.freepik.com/free-vector/game-buttons-wood-stone-gamer-  interface_23068339.htm", self.menu.Alphabet_Textures, center_x=x, center_y = y, scale=.9, text_margin = 12, width = 500))
        y -= 60
        self.texts.append(CustomTextSprite(f"Gold Buttons are From https://www.freepik.com/free-vector/wooden-gold-buttons-ui-game  _12760665.htm", self.menu.Alphabet_Textures, center_x=x, center_y = y, text_scale=2, text_margin = 13, width = 500))
        y -= 60
        self.texts.append(CustomTextSprite(f"Woodeen Backgrounds are From https://www.freepik.com/free-vector/wooden-gold-buttons-ui  -game_12760665.htm", self.menu.Alphabet_Textures, center_x=x, center_y = y, text_scale=2, text_margin = 13, width = 500))
        y -= 60
        

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        main_button = CustomUIFlatButton(self.menu.Alphabet_Textures, click_sound = self.menu.click_sound, text="Exit", width=140, height=50, x=0, y=50, text_offset_x = 16, text_offset_y=35, offset_x=75, offset_y=25)
        main_button.on_click = self.exit
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center", anchor_y="center",
                child=main_button, align_x=0, align_y=-200)
        self.uimanager.add(wrapper)

        window = arcade.get_window()
        self.on_resize(window.width, window.height)
    def on_draw(self):
        arcade.start_render()
        self.background.draw()
        self.christmas_background.draw()

        for text in self.texts: text.draw()
        self.uimanager.draw()
        return super().on_draw()
    def on_resize(self, width: int, height: int):
        scale1, scale2 = width/218, height/140
        larger = max(scale1, scale2)
        self.background.center_x = width/2-7*larger/3.6
        self.background.center_y = height/2-75*larger/3.6
        self.background._set_scale(larger)

        self.christmas_background.position = width/2, height/2
        self.christmas_background.scale = .25*max(width/1240, height/900)
        return super().on_resize(width, height)

    def exit(self, event):
        self.uimanager.disable()
        self.menu.uimanager.enable()

        self.window.show_view(self.menu)
class UpgradeScienceMenu(arcade.View):
    def __init__(self, menu):
        
        super().__init__()
        self.click_sound = menu.click_sound
        self.menu_view = menu
        self.background = arcade.Sprite("resources/gui/Large Bulletin.png", scale=3.6, center_x=370, center_y=180)
        self.christmas_background = arcade.Sprite("resources/gui/ChristmasOverlay.png", scale=.25, center_x=370, center_y=180)

        self.gold_button_texture = arcade.load_texture("resources/gui/Gold Button.png")
        self.silver_button_texture = arcade.load_texture("resources/gui/Silver Button.png")

        textures = arcade.load_spritesheet("resources/gui/Wooden Font.png", 14, 24, 12, 70, margin=1)
        self.Alphabet_Textures = {" ":None}
        string = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyz.:,%/-+_"
        for i in range(len(string)):
            self.Alphabet_Textures[string[i]] = textures[i]
  
        self.set_up()


        bg_tex = arcade.load_texture(":resources:gui_basic_assets/window/grey_panel.png")
        text_area = arcade.gui.UITextArea(x=0, y=0,width=200,height=50, scroll_speed=10,
                                    text="", text_color=(0, 0, 0, 255))
        texturePane = arcade.gui.UITexturePane(text_area.with_space_around(right=20), 
                                tex=bg_tex, padding=(10, 10, 10, 10))
        
        text_area.move(dy=-200)
        texturePane.locked = True
        texturePane.true_x = 0
        self.uimanager.add(texturePane)
        self.text_area = text_area

        window = arcade.get_window()
        self.on_resize(window.width, window.height)
    def set_up(self):
        self.last = None

        self.pressed_a = False
        self.pressed_d = False

        self.mouse_x = 0
        self.mouse_y = 0
        self.x = 0
        

        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)
        arcade.set_viewport(0, self.window.width, 0, self.window.height)


        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()
        self.lineList = arcade.ShapeElementList()  
        self.load()


        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Menu", width=140, height=50, x=0, y=50, text_offset_x = 16, text_offset_y = 35, offset_x=75, offset_y=25)
        start_button.on_click = self.exit
        start_button.unlocked = True
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="right", anchor_y="top",
            child=start_button, align_x=-50, align_y=-50)
        self.uimanager.add(wrapper)
        wrapper.identity = float('inf')
        wrapper.true_x = 300
        wrapper.description = "None"


        button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, width=50, height=50, scale=.1, x=50, y=50, offset_x=25, offset_y=25, Texture="resources/gui/Question Mark.png", Pressed_Texture="resources/gui/Question Mark.png", Hovered_Texture="resources/gui/Question Mark.png")
        button.on_click = self.on_question_click
        button.open = False
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center", anchor_y="center",
                child=button, align_x=0, align_y=-200)
        wrapper.identity = float('inf')
        wrapper.true_x = 300
        wrapper.description = "None"

        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.question = None
    def load(self):
        self.science_buttons = []

        saved = True
        try:
            with open("resources/game.json", "r") as read_file:
                p = json.load(read_file)
                self.Money = p["Money"]
        except:
            saved = False

            self.Money = 0

        window = arcade.get_window()
        self.texts = []
        self.text = UpdatingText(f"{floor(self.Money)} History", self.Alphabet_Textures, float("inf"), scale=4, text_margin = 50, center_x = -400+window.width/2, center_y = 200+window.height/2)

        
        with open("resources/GameBase copy.json", "r") as read_file:
            ScienceMenuInfo = json.load(read_file)["ScienceMenu"]
                

        id = 0
        for button in ScienceMenuInfo:
            
            start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text=button[0], width=140, height=50, x=0, y=50, text_margin=13, text_offset_x = 0, text_offset_y = 35, offset_x=75, offset_y=25)
            start_button.on_click = self.on_buttonclick
            wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
                child=start_button, align_x=button[1], align_y=button[2])
            wrapper.true_x = button[1]
            self.science_buttons.append(wrapper)
            
            wrapper.description = button[4]+f"              Cost:{button[7]}"
            wrapper.identity = id
            wrapper.unlocked = False

            start_button.affect = button[5]
            start_button.connections = button[3]
            start_button.cost = button[7]
            start_button.wrapper = wrapper
            button_names = button[3]

            start_button.connections = [ScienceMenuInfo.index(button2) for button2 in ScienceMenuInfo if button2[0] in button_names]

            self.uimanager.add(wrapper)

            if button[8] == 1:
                start_button.unlocked = True
            elif saved:
                start_button.unlocked = p["science_menu"][id]
            else:
                start_button.unlocked = False
                convert_button(start_button, self.silver_button_texture)
                start_button.cost = button[7]
            if start_button.unlocked:
                start_button.cost = float("inf")
                wrapper.identity = float("inf")

                convert_button(start_button, self.gold_button_texture)
                
            for i in start_button.connections:
                endx = ScienceMenuInfo[i][1]+370#cameraView
                endy = ScienceMenuInfo[i][2]+250
                line = arcade.create_line(button[1]+370, button[2]+250, endx, endy, (0, 0, 0, 255), line_width=5)
                line.identity = id
                self.lineList.append(line)

            id += 1
    def on_resize(self, width: int, height: int):
        scale1, scale2 = width/218, height/140
        larger = max(scale1, scale2)
        self.background.center_x = width/2-7*larger/3.6
        self.background.center_y = height/2-75*larger/3.6
        self.background._set_scale(larger)

        self.christmas_background.position = width/2, height/2
        self.christmas_background.scale = .25*max(width/1240, height/900)

        self.lineList._set_center_x(width/2-400+self.x)
        self.lineList._set_center_y(height/2-250)
        


    def on_key_press(self, key, modifiers):
        if key == arcade.key.A or key == arcade.key.LEFT:
            self.pressed_a = True
        if key == arcade.key.D or key == arcade.key.RIGHT:
            self.pressed_d = True
    def on_key_release(self, key, _modifiers):
        if key == arcade.key.A or key == arcade.key.LEFT:
            self.pressed_a = False
        if key == arcade.key.D or key == arcade.key.RIGHT:
            self.pressed_d = False
    def exit(self, event):
        try:
            with open("resources/game.json", "r") as read_file:
                p = json.load(read_file)
        except:
            p = {"science_menu":[]}
        
        with open("resources/game.json", "w") as write_file:
            p["Money"] = self.Money
            p["science_menu"] = []
            for button in self.science_buttons:
                p["science_menu"].append(button.child.unlocked)

            json.dump(p, write_file)
        
        
        self.uimanager.disable()
        self.menu_view.uimanager.enable()
        self.window.show_view(self.menu_view)
    def on_question_click(self, event):
        window = arcade.get_window()
        if not self.question: 
            text = CustomTextSprite("Use this menu to unlock more of the science tree in game.", self.Alphabet_Textures, width=-200, center_x=window.width/2+event.source.wrapper.align_x-150, center_y=window.height/2+event.source.wrapper.align_y+100, Background_offset_x=260, Background_offset_y=-35, Background_scale=1.5, Background_Texture="resources/gui/Small Text Background.png")
            self.question = text
        else:
            self.question = None

    def on_buttonclick(self, event):
        if self.button == 4:
            window = arcade.get_window()
            string = "Not Unlocked. "
            if event.source.wrapper.unlocked:
                string = "Unlocked.  "
            text = UpdatingText(string+event.source.cost, self.Alphabet_Textures, .5, scale=1, center_x = event.source.wrapper.align_x+window.width/2, center_y = event.source.rapper.align_y+window.height/2)
            self.texts.append(text)
            return
        self.handle_cost(event.source)
    def handle_cost(self, source):
        window = arcade.get_window()
        wrapper = source.wrapper
        #Does the player have enough science
        if source.unlocked:
            text = UpdatingText(f"Already unlocked", self.Alphabet_Textures, .5, scale=1, center_x = wrapper.align_x+window.width/2, center_y = wrapper.align_y+window.height/2)
            self.texts.append(text)
            return

        cost = self.check_backwards(source)
        if cost <= self.Money:
            self.Money -= cost
            self.unlock_backwards(source)
            self.text.update_text(f"{floor(self.Money)} History", self.Alphabet_Textures, scale=4, text_margin = 50, center_x = -400+window.width/2, center_y = 200+window.height/2)
        else:
            text = UpdatingText(f"You need {cost-self.Money} History", self.Alphabet_Textures, .5, scale=1, center_x = wrapper.align_x+window.width/2, center_y = wrapper.align_y+window.height/2)
            self.texts.append(text)
            return


        wrapper.identity = float("inf")
        self.handle_affect(source)        
    def handle_affect(self, source):
        convert_button(source, self.gold_button_texture)


        source.cost = float("inf")
        source.unlocked = True
    def check_backwards(self, source):
        if not source or source.unlocked:
            return 0

        cost = source.cost
        for i in source.connections:
            cost += self.check_backwards(self.science_buttons[i].child)
        return cost
    def unlock_backwards(self, source):
        if not source or source.unlocked:
            return 
        for i in source.connections:
            self.unlock_backwards(self.science_buttons[i].child)
        self.handle_affect(source)
        #self.uimanager.children[0].pop(-1)    
    def on_show(self):
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)

        arcade.set_viewport(0, self.window.width, 0, self.window.height)

    def on_draw(self):
        """ Draw this view """
        arcade.start_render()

        self.background.draw()
        self.christmas_background.draw()

        self.lineList.draw()
        self.uimanager.draw()
        for text in self.texts:
            text.draw() 
        self.text.draw()
        if self.question: self.question.draw()
    def on_mouse_motion(self, x, y, dx, dy):
        """
        Called whenever the mouse moves.
        """
        self.mouse_x = x
        self.mouse_y = y
        
        self.text_area.rect = self.text_area.rect.align_center(x, y)

        collided = False
        for button in self.science_buttons:
            if not button.rect.collide_with_point(*(x, y)):
                continue
            self.text_area.doc.text = button.description
            self.text_area.trigger_full_render()
            collided = True
            break
        if not collided:
            self.text_area.rect = self.text_area.rect.align_center(0, -1000)
    def on_update(self, delta_time):

        if self.pressed_a and self.x + 50 < -self.science_buttons[0].true_x:
            self.x += 1000*delta_time
            self.lineList.move(1000*delta_time, 0)
            #self.lineList.move(0, 0)
        if self.pressed_d and self.x - 50 > -self.science_buttons[-1].true_x:
            self.x -= 1000*delta_time
            self.lineList.move(-1000*delta_time, 0)

        if self.pressed_a or self.pressed_d:
            for button2 in self.science_buttons:
                button2.align_x = button2.true_x+self.x
        for text in self.texts:
            if text.update(delta_time):
                self.texts.remove(text)
    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        self.button = button
        if sprites_in_range(15, (x, y), self.text.Sprite_List):
            text = UpdatingText(f"Get at end of a Game. Use to upgrade science tree", self.Alphabet_Textures, .5, scale=1, center_x = x, center_y = y-20, Background_offset_x=50, Background_Texture="resources/gui/Small Text Background.png")
            self.texts.append(text)
        return super().on_mouse_press(x, y, button, modifiers)

class ScienceMenu(arcade.View):
    def __init__(self, game_view):
        
        super().__init__()
        self.click_sound = game_view.click_sound
        self.click_sound.volume = game_view.click_sound.volume
        self.set_up(game_view)

        self.background = arcade.Sprite("resources/gui/Large Bulletin.png", scale=3.6, center_x=370, center_y=180)
        self.christmas_background = arcade.Sprite("resources/gui/ChristmasOverlay.png", scale=.25, center_x=370, center_y=180)

        textures = arcade.load_spritesheet("resources/gui/Wooden Font.png", 14, 24, 12, 70, margin=1)
        self.Alphabet_Textures = {" ":None}
        string = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyz.:,%/-+_"
        for i in range(len(string)):
            self.Alphabet_Textures[string[i]] = textures[i]
        self.gold_button_texture = arcade.load_texture("resources/gui/Gold Button.png")
        self.silver_button_texture = arcade.load_texture("resources/gui/Silver Button.png")
        

        self.pre_load()

        window = arcade.get_window()
        self.texts = []
        self.text = UpdatingText(f"{round(self.game_view.science*10)/10} Science", self.Alphabet_Textures, float("inf"), center_x = -400+window.width/2, center_y = 200+window.height/2)
        self.texts.append(self.text)


        bg_tex = arcade.load_texture(":resources:gui_basic_assets/window/grey_panel.png")
        text_area = arcade.gui.UITextArea(x=0, y=0,width=200,height=50, scroll_speed=10,
                                    text="", text_color=(0, 0, 0, 255))
        texturePane = arcade.gui.UITexturePane(text_area.with_space_around(right=20), 
                                tex=bg_tex, padding=(10, 10, 10, 10))
        text_area.move(dy=-200)
        texturePane.unlocked = True
        texturePane.true_x = 0
        self.uimanager.add(texturePane)
        self.text_area = text_area


        window = arcade.get_window()
        self.on_resize(window.width, window.height)
    def set_up(self, game_view):
        self.game_view = game_view
        self.last = None

        self.pressed_a = False
        self.pressed_d = False

        self.mouse_x = 0
        self.mouse_y = 0
        self.x = 0

        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)
        arcade.set_viewport(0, self.window.width, 0, self.window.height)


        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        self.lineList = arcade.ShapeElementList()
        self.science_buttons = []
    def on_resize(self, width: int, height: int):
        scale1, scale2 = width/218, height/140
        larger = max(scale1, scale2)
        self.background.center_x = width/2-7*larger/3.6
        self.background.center_y = height/2-75*larger/3.6
        self.background._set_scale(larger)

        self.christmas_background.position = width/2, height/2
        self.christmas_background.scale = .25*max(width/1240, height/900)
        
        self.lineList._set_center_x(width/2-400+self.x)
        self.lineList._set_center_y(height/2-250)

    def pre_load(self):
        #NOTE: Determens if saved
        self.load()
        
        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Menu", width=140, height=50, x=0, y=50, text_offset_x = 24, text_offset_y = 35, offset_x=75, offset_y=25)
        #start_button = arcade.gui.UIFlatButton(text="Menu",width=100, x=50, y=50)
        start_button.on_click = self.exit
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="right", anchor_y="top",
            child=start_button, align_x=-50, align_y=-50)
        self.uimanager.add(wrapper)
        start_button.unlocked = True

        wrapper.true_x = 300
        wrapper.description = "None"

        self.menu_button = wrapper
    def load(self):
        saved = self.game_view.science_list != None

        with open("resources/game.json", "r") as read_file:
            game = json.load(read_file)['science_menu']
        
        with open("resources/GameBase copy.json", "r") as read_file:
            buttons = json.load(read_file)
            
        ScienceMenuInfo = buttons["ScienceMenu"]

        id = 0
        for button in ScienceMenuInfo:
            #start_button = arcade.gui.UIFlatButton(text=button[0],width=150, x=0, y=0)
            start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text=button[0], width=140, height=50, x=0, y=50, text_margin=13, text_offset_x = 0, text_offset_y = 35, offset_x=75, offset_y=25)
            start_button.on_click = self.on_buttonclick
            wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
                child=start_button, align_x=button[1], align_y=button[2])
            wrapper.true_x = button[1]


            wrapper.description = button[4]+f"              Cost:{button[6]}"
            wrapper.identity = id
            if saved and self.game_view.science_list[id]: 
                start_button.unlocked = self.game_view.science_list[id]

                convert_button(start_button, self.gold_button_texture)
            else:
                start_button.unlocked = False
            
            start_button.affect = button[5]
            start_button.cost = button[6]

            button_names = button[3]

            start_button.connections = [ScienceMenuInfo.index(button2) for button2 in ScienceMenuInfo if button2[0] in button_names]
            
            start_button.wrapper = wrapper
            self.uimanager.add(wrapper)
            self.science_buttons.append(wrapper)
            
            start_button.locked = False
            if not game[id]:
                start_button._style = {"bg_color":arcade.color.DIM_GRAY, "font_color":arcade.color.BLACK}
                convert_button(start_button, self.silver_button_texture)
                start_button.locked = True


            for i in start_button.connections:
                endx = ScienceMenuInfo[i][1]+370#cameraView
                endy = ScienceMenuInfo[i][2]+250#cameraView

                line = arcade.create_line(button[1]+370, button[2]+250, endx, endy, (120,100,100, 200), line_width=5)
                line.identity = id
                self.lineList.append(line)

            id += 1
            
    def on_key_press(self, key, modifiers):
        if key == arcade.key.A or key == arcade.key.LEFT:
            self.pressed_a = True
        if key == arcade.key.D or key == arcade.key.RIGHT:
            self.pressed_d = True
    def on_key_release(self, key, _modifiers):
        if key == arcade.key.A or key == arcade.key.LEFT:
            self.pressed_a = False
        if key == arcade.key.D or key == arcade.key.RIGHT:
            self.pressed_d = False
    def exit(self, event):
        self.game_view.science_list = [button.child.unlocked for button in self.science_buttons]

        self.game_view.uimanager.enable()
        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)
        self.uimanager.disable()
        self.window.show_view(self.game_view)
    def on_buttonclick(self, event):
        if self.button == 4:
            window = arcade.get_window()
            string = "Not Unlocked. "
            if event.source.locked:
                string = "Locked.   Unlock in Progress Tree. "
            elif event.source.unlocked:
                string = "Unlocked. "
            
            text = UpdatingText(string, self.Alphabet_Textures, 1, scale=1, center_x = event.source.wrapper.align_x+window.width/2, center_y = event.source.wrapper.align_y+window.height/2)
            self.texts.append(text)
            return

        self.handle_cost(event.source)
        
    def handle_cost(self, source):
        window = arcade.get_window()
        x, y = source.wrapper.align_x+window.width/2, source.wrapper.align_y+window.height/2
        
        if source.locked:
            text = UpdatingText(f"Locked", self.Alphabet_Textures, .5, scale=1, center_x = x, center_y = y)
            self.texts.append(text)
            return
        elif source.unlocked:
            text = UpdatingText(f"Alerady Unlocked", self.Alphabet_Textures, .5, scale=1, center_x = x, center_y = y)
            self.texts.append(text)
            return
                

        cost = self.check_backwards(source)
        if cost > self.game_view.science:
            science_missing = cost-self.game_view.science
            text = UpdatingText(f"missing {floor(science_missing*100)/100} science", self.Alphabet_Textures, .5, scale=1, center_x = x, center_y = y)
            self.texts.append(text)
            return 
        self.game_view.science -= cost
        self.unlock_backwards(source)
        self.text.update_text(f"{round(self.game_view.science*10)/10} science", self.Alphabet_Textures, scale=1, center_x = -400+window.width/2, center_y = 200+window.height/2)


    
        #passed conditions
        self.handle_affect(source)
    def handle_affect(self, source):
        
        for _type, amount in source.affect.items():
            try:
                vars(self.game_view)[_type] += amount/100
            except:
                self.game_view.unlocked[_type] = True
                    

        convert_button(source, self.gold_button_texture)
        source.unlocked = True
    def check_backwards(self, source):
        if not source or source.unlocked:
            return 0
        cost = source.cost
        for i in source.connections:
            cost += self.check_backwards(self.science_buttons[i].child)
        return cost
    def unlock_backwards(self, source):
        if not source or source.unlocked:
            return 
        for i in source.connections:
            self.unlock_backwards(self.science_buttons[i].child)
        self.handle_affect(source)
    
    def on_show(self):
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)

        arcade.set_viewport(0, self.window.width, 0, self.window.height)
    def on_draw(self):
        """ Draw this view """
        arcade.start_render()

        self.background.draw()
        self.christmas_background.draw()
        self.lineList.draw()
        self.uimanager.draw()
        for text in self.texts: text.draw()
    def on_mouse_motion(self, x, y, dx, dy):
        """
        Called whenever the mouse moves.
        """
        self.mouse_x = x
        self.mouse_y = y
        
        #self.text_area.move(dx, dy)
        self.text_area.rect = self.text_area.rect.align_center(x, y)

        collided = False
        for button in self.science_buttons:
            if not button.rect.collide_with_point(*(x, y)):
                continue
            self.text_area.doc.text = button.description
            self.text_area.trigger_full_render()
            collided = True
            break
        if not collided:
            self.text_area.rect = self.text_area.rect.align_center(0, -1000)
    def on_update(self, delta_time):

        if self.pressed_a and self.x + 50 < -self.science_buttons[0].true_x:
            self.x += 1000*delta_time
            self.lineList.move(1000*delta_time, 0)
            #self.lineList.move(0, 0)
        if self.pressed_d and self.x - 50 > -self.science_buttons[-1].true_x:
            self.x -= 1000*delta_time
            self.lineList.move(-1000*delta_time, 0)

        if self.pressed_a or self.pressed_d:
            for button2 in self.science_buttons:
                button2.align_x = button2.true_x+self.x
        
        for text in self.texts: 
            if text.update(delta_time):
                self.texts.remove(text)
    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        self.button = button
        return super().on_mouse_press(x, y, button, modifiers)
class VolumeMenu(arcade.View):
    def __init__(self, game_view):
        super().__init__()
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)
        arcade.set_viewport(0, self.window.width, 0, self.window.height)
        game_view.uimanager.disable()
        self.game_view = game_view
        self.set_up()

        window = arcade.get_window()
        self.on_resize(window.width, window.height)
    def set_up(self):

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        self.click_sound = self.game_view.click_sound

        self.background = arcade.Sprite("resources/gui/Large Bulletin.png", scale=3.6, center_x=370, center_y=180)
        self.christmas_background = arcade.Sprite("resources/gui/ChristmasOverlay.png", scale=.25, center_x=370, center_y=180)


        textures = arcade.load_spritesheet("resources/gui/Wooden Font.png", 14, 24, 12, 70, margin=1)
        self.Alphabet_Textures = {" ":None}
        string = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyz.:,%/-+_"
        for i in range(len(string)):
            self.Alphabet_Textures[string[i]] = textures[i]
        window = arcade.get_window()

        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound = self.click_sound, text="Menu", width=140, height=50, x=0, y=50, text_offset_x = 24, text_offset_y = 35, offset_x=75, offset_y=25)
        start_button.on_click = self.exit
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="right", anchor_y="top",
            child=start_button, align_x=0, align_y=0)
        self.uimanager.add(wrapper)

        self.texts = []
        self.speed = 1
        ui_slider = CustomUISlider(max_value=200, value=self.game_view.audio_type_vols["Overall"]*100, width=302, height=35, x=0, offset_x=150, offset_y=-10, button_offset_y=-6)#arcade.load_texture("resources/gui/Slider_Button.png")#self.textures[0]
        #ui_slider.move(-200, -100)
        label = CustomTextSprite(f"Master Volume: {ui_slider.value:02.0f}%", self.Alphabet_Textures, center_x=window.width/2-145, center_y=window.height/2+150)#UILabel(text=f"Master Volume: {ui_slider.value:02.0f}%")

        @ui_slider.event()
        def on_change(event: UIOnChangeEvent):
            label.update_text(f"Master Volume: {ui_slider.value:02.0f}%", self.Alphabet_Textures, center_x=window.width/2-145, center_y=window.height/2+150)
            #label.text = f"Master Volume: {ui_slider.value:02.0f}%"
            self.speed = ui_slider.value
            #label.fit_content()
            self.game_view.audio_type_vols["Overall"] = ui_slider.value/100
            self.game_view.update_audio()

        slider = UIAnchorWidget(child=ui_slider, align_x=0, align_y=110, anchor_x="center", anchor_y="center")
        self.uimanager.add(slider)
        #self.label = UIAnchorWidget(child=label, align_x=0, align_y=160, anchor_x="center", anchor_y="center")
        self.texts.append(label)



        ui_slider1 = CustomUISlider(max_value=200, value=self.game_view.audio_type_vols["UI"]*100, width=302, height=35, x=0, offset_x=150, offset_y=-10, button_offset_y=-6)#arcade.load_texture("resources/gui/Slider_Button.png")#self.textures[0]
        #ui_slider.move(-200, -100)
        label1 = CustomTextSprite(f"UI Volume: {ui_slider1.value:02.0f}%", self.Alphabet_Textures, center_x=window.width/2-145, center_y=window.height/2+50)

        @ui_slider1.event()
        def on_change(event: UIOnChangeEvent):
            label1.update_text(f"UI Volume: {ui_slider1.value:02.0f}%", self.Alphabet_Textures, center_x=window.width/2-145, center_y=window.height/2+50)
            self.speed = ui_slider1.value

            self.game_view.audio_type_vols["UI"] = ui_slider1.value/100
            self.game_view.update_audio()

        slider = UIAnchorWidget(child=ui_slider1, align_x=0, align_y=10, anchor_x="center", anchor_y="center")
        self.uimanager.add(slider)
        self.texts.append(label1)




        ui_slider2 = CustomUISlider(max_value=200, value=self.game_view.audio_type_vols["Background"]*100, width=302, height=35, x=0, offset_x=150, offset_y=-10, button_offset_y=-6)#arcade.load_texture("resources/gui/Slider_Button.png")#self.textures[0]
        #ui_slider.move(-200, -100)
        label2 = CustomTextSprite(f"Background Volume: {ui_slider2.value:02.0f}%", self.Alphabet_Textures, center_x=window.width/2-145, center_y=window.height/2-50, text_margin=14)

        @ui_slider2.event()
        def on_change(event: UIOnChangeEvent):
            label2.update_text(f"Background Volume: {ui_slider2.value:02.0f}%", self.Alphabet_Textures, center_x=window.width/2-145, center_y=window.height/2-50, text_margin=14)
            self.speed = ui_slider2.value

            self.game_view.audio_type_vols["Background"] = ui_slider2.value/100
            self.game_view.update_audio()

        slider = UIAnchorWidget(child=ui_slider2, align_x=0, align_y=-90, anchor_x="center", anchor_y="center")
        self.uimanager.add(slider)
        self.texts.append(label2)
    def on_resize(self, width: int, height: int):
        scale1, scale2 = width/218, height/140
        larger = max(scale1, scale2)
        self.background.center_x = width/2-7*larger/3.6
        self.background.center_y = height/2-75*larger/3.6
        self.background._set_scale(larger)

        self.christmas_background.position = width/2, height/2
        self.christmas_background.scale = .25*max(width/1240, height/900)
        
        y = center_y=height/2+150
        for label in self.texts:
            label.update_text(label.text, self.Alphabet_Textures, center_x=width/2-145, center_y=y)
            y -= 100
        return super().on_resize(width, height)

    def on_draw(self):
        arcade.start_render()
        self.background.draw()
        self.christmas_background.draw()
        for text in self.texts: text.draw()
        
        self.uimanager.draw()
    def on_mouse_drag(self, x: float, y: float, dx: float, dy: float, _buttons: int, _modifiers: int):
        return super().on_mouse_drag(x, y, dx, dy, _buttons, _modifiers)
    def exit(self, event):
        self.game_view.Christmas_music.true_volume = self.game_view.Christmas_music.volume
        self.game_view.Background_music.true_volume = self.game_view.Background_music.volume

        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)
        self.uimanager.disable()
        self.game_view.uimanager.enable()
        self.window.show_view(self.game_view)
class ShowMenu(arcade.View):
    def __init__(self, game_view):
        super().__init__()
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)
        arcade.set_viewport(0, self.window.width, 0, self.window.height)
        game_view.uimanager.disable()
        self.game_view = game_view
        self.set_up()
    def set_up(self):

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()


        start_button = arcade.gui.UIFlatButton(text="Menu",width=100, x=50, y=50)
        start_button.on_click = self.exit
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
            child=start_button, align_x=300, align_y=200)
        self.uimanager.add(wrapper)


        game = vars(self.game_view)
        y = 450
        self.texts = arcade.SpriteList(use_spatial_hash=True, is_static=True)
        for item in items_to_show:
            self.texts.append(arcade.create_text_sprite(f"{game[item]} {item}", 0, y, arcade.color.WHITE, font_size=36))
            y -= 50

    def on_draw(self):
        arcade.start_render()
        for text in self.texts:
            text.draw()
        self.uimanager.draw()
        
    def on_mouse_drag(self, x: float, y: float, dx: float, dy: float, _buttons: int, _modifiers: int):
        return super().on_mouse_drag(x, y, dx, dy, _buttons, _modifiers)
    
    def exit(self, event):
        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)
        self.uimanager.disable()
        self.game_view.uimanager.enable()
        self.window.show_view(self.game_view)

class Selection(arcade.Sprite):
    def __init__(self, texture, x, y):
        super().__init__(texture, center_x=x, center_y=y, scale=1)
class BuildingMenu(arcade.View):
    def __init__(self, game_view):
        
        super().__init__()
        self.set_up(game_view)
        self.load()

    def set_up(self, game_view):
        self.game_view = game_view
        self.last = None

        self.pressed_a = False
        self.pressed_d = False

        self.mouse_x = 0
        self.mouse_y = 0

        self.x = 0
        

        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)
        arcade.set_viewport(0, self.window.width, 0, self.window.height)


        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        self.lineList = arcade.ShapeElementList()
        
    def load(self):
        with open("textInfo.json", "r") as read_file:
            buttons = json.load(read_file)
            
        start_button = arcade.gui.UIFlatButton(text="Menu",width=100, x=50, y=50)
        start_button.on_click = self.exit
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
            child=start_button, align_x=300, align_y=200)
        self.uimanager.add(wrapper)
        wrapper.description = "None"
                
        for button in buttons["Selectables"]:
            length = len(button[3])*11
            start_button = arcade.gui.UIFlatButton(text=button[3],width=length, x=0, y=0)
            start_button.on_click = self.on_buttonclick
            wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
                child=start_button, align_x=button[1], align_y=button[2])

            start_button.type = button[3]
            wrapper.description = button[4]
            start_button.requirements = button[5]
            start_button.placement = button[6]
            start_button.wrapper = wrapper

            self.uimanager.add(wrapper)

            
    def on_key_press(self, key: int, modifiers: int):
        if key == arcade.key.A:
            self.pressed_a = True
        if key == arcade.key.D:
            self.pressed_d = True
    def on_key_release(self, key: int, _modifiers: int):
        if key == arcade.key.A:
            self.pressed_a = False
        if key == arcade.key.D:
            self.pressed_d = False


    def exit(self, event):
        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)
        self.game_view.uimanager.enable()
        self.uimanager.disable()
        self.window.show_view(self.game_view)

    def on_buttonclick(self, event):
        source = event.source
        if not isinstance(source, arcade.gui.UIFlatButton):
            return

        if self.game_view.unlocked[source.type]:
            #passed conditions
            self.handle_affect(source)


        
    def handle_affect(self, source:arcade.gui.UIFlatButton):
        self.game_view.object = source.type
        self.game_view.requirements = source.requirements
        self.game_view.object_placement = source.placement
       
        
    def on_show(self):
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)

        arcade.set_viewport(0, self.window.width, 0, self.window.height)


    def on_draw(self):
        """ Draw this view """
        arcade.start_render()

        self.uimanager.draw()

    def on_mouse_motion(self, x, y, dx, dy):
        """
        Called whenever the mouse moves.
        """
        self.mouse_x = x
        self.mouse_y = y

    def on_update(self, delta_time):
        pass
class TrainingMenu(arcade.View):
    def __init__(self, game_view, building):
        
        super().__init__()
        self.building = building
        self.set_up(game_view)
        self.load()
    def set_up(self, game_view):
        self.game_view = game_view
        self.last = None
        self.title = None

        self.pressed_a = False
        self.pressed_d = False

        self.mouse_x = 0
        self.mouse_y = 0

        self.x = 0
        

        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)
        arcade.set_viewport(0, self.window.width, 0, self.window.height)


        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        self.lineList = arcade.ShapeElementList()
        self.image = arcade.Sprite()

        self.updating_texts = []

        window = arcade.get_window()
        self.on_resize(window.width, window.height)

        self.image = None
    def load(self):
        buttons = self.building.trainable
        self.ui_texts = arcade.SpriteList()
            
        start_button = CustomUIFlatButton(self.game_view.Alphabet_Textures, click_sound = self.game_view.click_sound, text="Menu", width=140, height=50, x=0, y=50, text_offset_x = 24, text_offset_y = 35, offset_x=75, offset_y=25)
        start_button.on_click = self.exit
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
            child=start_button, align_x=300, align_y=200)
        self.uimanager.add(wrapper)
        wrapper.description = "None"
        
        x, y = 50, 0
        for button in buttons:
            start_button = CustomUIFlatButton(self.game_view.Alphabet_Textures, click_sound = self.game_view.click_sound, text=button, width=140, height=50, x=0, y=50, margin=13, text_offset_x = -6, text_offset_y = 35, offset_x=75, offset_y=25)
            start_button.on_click = self.on_selectionclick
            wrapper = arcade.gui.UIAnchorWidget(anchor_x="left", anchor_y="top",
                child=start_button, align_x=x, align_y=y)
            start_button.wrapper = wrapper
            start_button.string = button
            self.uimanager.add(wrapper)
            y -= 75
    def on_resize(self, width: int, height: int):
        return super().on_resize(width, height) 
        
    def on_key_press(self, key: int, modifiers: int):
        if key == arcade.key.A:
            self.pressed_a = True
        if key == arcade.key.D:
            self.pressed_d = True
    def on_key_release(self, key: int, _modifiers: int):
        if key == arcade.key.A:
            self.pressed_a = False
        if key == arcade.key.D:
            self.pressed_d = False
    def exit(self, event):
        if self.image:
            if isinstance(self.image, Person):
                self.game_view.population += 1
            self.image.destroy(self.game_view)
            self.image = None
        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)
        self.game_view.uimanager.enable()
        self.uimanager.disable()
        del self.image
        del self.lineList
        self.window.show_view(self.game_view)

    def on_selectionclick(self, event):
        
        self.ui_texts.clear()
        self.string = event.source.string
        if self.title is not None:
            self.uimanager.remove(self.title)
            self.uimanager.remove(self.description)

        self.title = arcade.gui.UITextArea(x=250, y=420,width=300,height=75, scroll_speed=10,
                                    text=self.string, font_size=48, text_color=(0, 0, 0, 255))#append(arcade.create_text_sprite(self.string, 200, 400, arcade.color.BLACK, font_size=48))
        self.title.fit_content()
        self.uimanager.add(self.title)

        string = "Costs:"
        for key, val in requirements[self.string].items():
            string += f" {val} {key},"
        #self.ui_texts.append(arcade.create_text_sprite(descriptions[self.string]+f"       Time: {trainingtimes[self.string]}       "+string, 200, 100, arcade.color.BLACK, font_size=24))
        self.description = arcade.gui.UITextArea(x=250, y=180, width=400, height=60, scroll_speed=10, font_size=24,
                            text=descriptions[self.string]+f"Time: {trainingtimes[self.string]}           "+string, 
                            text_color=(0, 0, 0, 255))
        self.uimanager.add(self.description)
        self.description.fit_content()
        
        self.button = arcade.gui.UIFlatButton(text="Train",width=100, x=50, y=50)
        self.button.on_click = self.on_buttonclick
        self.button.string = self.string
        self.button.cost = requirements[self.string]
        wrapper = arcade.gui.UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
            child=self.button, align_x=0, align_y=-200)
        self.button.wrapper = wrapper
        self.uimanager.add(wrapper)

        if self.image:
            if isinstance(self.image, Person):
                self.game_view.population += 1
            self.image.destroy(self.game_view)
            self.image = None
        


        self.image = objects[self.string](self.game_view, 400, 320)
        self.image._set_scale(4)

    def on_buttonclick(self, event):
        source = event.source
        if self.game_view.unlocked[source.string]:
            #passed conditions
            self.handle_affect(source)
        else:
            window = arcade.get_window()
            text = UpdatingText("Not Unlocked", self.game_view.Alphabet_Textures, 1, width = 100, center_x=window.width/2, center_y=window.height/2-200)
            self.updating_texts.append(text)
    def handle_affect(self, source:arcade.gui.UIFlatButton):
        if len(self.building.list_of_people) == 0:
            text = UpdatingText("No People to train", self.game_view.Alphabet_Textures, 1, width = 100, center_x=source.x, center_y=source.y)
            self.updating_texts.append(text)
            return
        variables = vars(self.game_view)
        missing = ""
        for key, val in source.cost.items(): 
            if variables[key] < val: 
                if missing: missing += ", "
                else: missing = "Missing: "
                missing += f"{val-variables[key]} {key}"
        if missing:
            text = UpdatingText(missing, self.game_view.Alphabet_Textures, 1, width = 100, center_x=source.x, center_y=source.y)
            self.updating_texts.append(text)
            return

        for person in self.building.list_of_people:
            if person.advancement != None: continue
            person.advancement = source.string
            person.trainingtime = 0

            for key, val in source.cost.items(): variables[key] -= val
            break


    def on_update(self, delta_time: float):
        for text in self.updating_texts:
            text.update(delta_time)
        return super().on_update(delta_time)    
    def on_show(self):
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)

        arcade.set_viewport(0, self.window.width, 0, self.window.height)
    def on_draw(self):
        """ Draw this view """
        arcade.start_render()

        self.uimanager.draw()
        self.ui_texts.draw()
        if self.image: self.image.draw()
        for text in self.updating_texts:
            text.draw()
    def on_mouse_motion(self, x, y, dx, dy):
        """
        Called whenever the mouse moves.
        """
        self.mouse_x = x
        self.mouse_y = y

def retrieve_from_Science(world):
    try:
        infile = open(f"{world}", 'rb')
        return pickle.load(infile)['science_list']
    except:
        with open("resources/GameBase copy.json", "r") as read_file:
            buttons = json.load(read_file)
        
        return [bool(button[8]) for button in buttons["ScienceMenu"]]
def main():
    """Main method"""
    window = arcade.Window(1440, 900, "SantaFest Destiny", resizable=True)
    StartMenu = startMenu()#MyGame()#StartMenu()
    window.show_view(StartMenu)
    arcade.run()
def foo():
    print("NJJNJNDEEDDE")

if __name__ == "__main__":
    atexit.register(foo)
    main()
