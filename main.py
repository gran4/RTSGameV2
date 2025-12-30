from array import array
from collections import defaultdict, deque
from copy import copy
import heapq
import json
import logging
import os
import pickle
import random
import sys
import time
from math import ceil, floor, sqrt
import math
from pathlib import Path
from typing import Any, Optional

import arcade
from arcade import XYWH
from arcade import math as arcade_math
from arcade.draw import draw_rect_filled, draw_rect_outline
from arcade.shape_list import ShapeElementList, create_line, create_rectangle_filled
from arcade.gl import geometry
from arcade.gui import UIFlatButton, UILabel, UITextureButton

from BackGround import *
from Buildings import *
from Components import *
from CustomCellularAutomata import create_grid, do_simulation_step, initialize_grid
from Enemys import *
from MyPathfinding import LivingMap, SearchTilesAround, _AStarSearch
from Player import *
from effects import Fire
from TextInfo import *
from gui_compat import UIAnchorWidget

if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    os.chdir(sys._MEIPASS)


def _collect_subclasses(cls):
    subs = set()
    for sub in cls.__subclasses__():
        subs.add(sub)
        subs.update(_collect_subclasses(sub))
    return subs


ENEMY_CLASS_MAP = {c.__name__: c for c in _collect_subclasses(BaseEnemy) | {
    BaseEnemy}}
BUILDING_CLASS_MAP = {c.__name__: c for c in _collect_subclasses(BaseBuilding) | {
    BaseBuilding}}

WATER_DEPTH_SCALE = 3.0

BASE_DIR = Path(__file__).resolve().parent
SAVE_DIR = BASE_DIR / "save_files"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR = BASE_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_DIR / "ui.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

CHRISTMAS_TRIGGER_TIME = 120.0
WATER_TIME_SCALE = 0.4
WATER_OVERLAY_PATH = (BASE_DIR / "resources/Sprites/terrain/water.jpg")
WATER_OVERLAY_REPEAT = 1.0
WATER_DEPTH_SCALE = 3.0
WATER_TILE_SIZE = 50

WATER_VERTEX_SHADER = """
#version 330
in vec2 in_vert;
in vec2 in_uv;
out vec2 v_uv;

void main() {
    v_uv = in_uv;
    gl_Position = vec4(in_vert, 0.0, 1.0);
}
"""

WATER_FRAGMENT_SHADER = """
#version 330
uniform sampler2D base_texture;
uniform sampler2D overlay_texture;
uniform sampler2D depth_texture;
uniform float u_time;
uniform vec2 u_resolution;
uniform vec2 u_overlay_scale;
uniform vec2 u_overlay_offset;
uniform vec2 u_world_origin;
uniform vec2 u_world_size;
uniform vec2 u_depth_scale;

in vec2 v_uv;
out vec4 fragColor;

void main() {
    vec2 uv = v_uv;

    float wave1 = sin(uv.y * 24.0 + u_time * 1.2) * 0.006;
    float wave2 = cos(uv.x * 18.0 + u_time * 0.95) * 0.006;
    vec2 distorted_uv = uv + vec2(wave1, wave2);
    vec2 world_pos = u_world_origin + uv * u_world_size;

    vec4 base_mask_sample = texture(base_texture, uv);
    vec4 base_color = texture(base_texture, distorted_uv);
    vec2 overlay_uv = distorted_uv * u_overlay_scale + u_overlay_offset + vec2(u_time * 0.02, -u_time * 0.018);
    vec4 overlay_sample = texture(overlay_texture, overlay_uv);

    float gradient = gl_FragCoord.y / u_resolution.y;
    vec3 bright_blue = mix(vec3(0.04, 0.32, 0.65), vec3(0.12, 0.52, 0.9), gradient * 0.7);
    vec3 base_mix = mix(base_color.rgb, bright_blue, 0.65);

    float edge = smoothstep(0.0, 0.25, base_mask_sample.a);
    vec3 overlay_target = mix(bright_blue, overlay_sample.rgb, overlay_sample.a * 0.12);
    vec3 overlay_mix = mix(base_mix, overlay_target, edge);

    vec2 depth_uv = clamp(
        (world_pos + vec2(25.0, 25.0)) * u_depth_scale,
        vec2(0.0),
        vec2(1.0)
    );
    float depth = texture(depth_texture, depth_uv).r;
    float depth_shade = mix(0.55, 0.94, 1.0 - depth);
    vec3 color = overlay_mix * depth_shade;

    float alpha = base_mask_sample.a * 0.82;

    fragColor = vec4(color, alpha);
}
"""


def get_save_path(file_id):
    if file_id is None:
        return None
    return SAVE_DIR / f"{file_id}"


def apply_audio_volume(audio, volume_map):
    start = getattr(audio, "start_vol", 1)
    type_key = getattr(audio, "type", "Overall")
    overall = volume_map.get("Overall", 1)
    type_vol = volume_map.get(type_key, 1)
    volume = start * type_vol * overall
    if hasattr(audio, "set_volume"):
        audio.set_volume(volume)
    else:
        audio.volume = volume
        if getattr(audio, "player", None):
            audio.player.volume = volume
    source = getattr(audio, "source", None)
    if source is not None:
        source.volume = volume


def stretch_background(sprite: arcade.Sprite | None,
                       width: float,
                       height: float,
                       *,
                       padding: float = 0.15,
                       min_scale: float = 16.5) -> None:
    """Ensure a parchment-style background fills the current window."""
    if sprite is None:
        return
    texture = getattr(sprite, "texture", None)
    tex_w = getattr(texture, "width", 0) or 1
    tex_h = getattr(texture, "height", 0) or 1
    base_scale = getattr(sprite, "_base_scale", None)
    if base_scale is None:
        raw_scale = getattr(sprite, "scale", 1.0)
        if isinstance(raw_scale, (tuple, list)):
            raw_scale = max(raw_scale) if raw_scale else 1.0
        base_scale = float(raw_scale or 1.0)
        sprite._base_scale = base_scale
    try:
        numeric_min_scale = float(min_scale)
    except (TypeError, ValueError):
        if isinstance(min_scale, (tuple, list)):
            numeric_min_scale = max(min_scale) if min_scale else base_scale
        else:
            numeric_min_scale = base_scale
    min_scale = max(numeric_min_scale, base_scale)
    sprite.center_x = width / 2
    sprite.center_y = height / 2
    width_scale = ((width * (1 + padding)) / tex_w)
    height_scale = ((height * (1 + padding)) / tex_h)
    target_scale = max(min_scale, width_scale, height_scale)
    sprite.scale = target_scale


def resize_ui_manager(owner: Any, width: int, height: int) -> None:
    """Resize the active UIManager if the current view owns one."""
    manager = getattr(owner, "uimanager", None)
    if not manager or not hasattr(manager, "on_resize"):
        return
    try:
        manager.on_resize(width, height)
        surfaces = getattr(manager, "_surfaces", None)
        if isinstance(surfaces, dict):
            surfaces.clear()
    except Exception:
        logging.exception("Failed to resize UI manager for %s", type(owner).__name__)


def show_view_resized(window: arcade.Window, view: arcade.View) -> None:
    """Switch to a view and immediately apply the current window size."""
    window.show_view(view)
    width = getattr(window, "width", 0) or getattr(window, "size", (0, 0))[0]
    height = getattr(window, "height", 0) or getattr(window, "size", (0, 0))[1]
    if not width or not height:
        return
    if hasattr(view, "on_resize"):
        try:
            view.on_resize(width, height)
        except TypeError:
            # Some views might not follow the (width, height) signature; ignore them.
            pass
    resize_ui_manager(view, width, height)


Font = "Wooden Font(1).png"
PARCHMENT_COLOR = (244, 229, 207)


class SnowAmbience:
    """Lightweight ambient snow particles over snowy terrain."""

    def __init__(self) -> None:
        self.particles = arcade.SpriteList()
        self.texture = arcade.make_soft_circle_texture(
            14, (235, 245, 255, 230), center_alpha=230, outer_alpha=10)
        self._player_on_snow = False
        self._check_timer = 0.0

    def update(self, game, delta_time: float) -> None:
        self._check_timer -= delta_time
        if self._check_timer <= 0:
            self._check_timer = 0.5
            self._player_on_snow = self._player_on_snow_tile(game)

        if self._player_on_snow:
            self._spawn(game, delta_time)
        self._update_particles(delta_time)

    def _player_on_snow_tile(self, game) -> bool:
        player = getattr(game, "player", None)
        if not player:
            return False
        px = getattr(player, "center_x", None)
        py = getattr(player, "center_y", None)
        if px is None or py is None:
            return False
        lands = arcade.get_sprites_at_point((px, py), getattr(game, "Lands", []))
        return bool(lands and getattr(lands[0], "typ", None) == "Snow")

    def _spawn(self, game, delta_time: float) -> None:
        camera = getattr(game, "camera", None)
        if not camera:
            return
        width = getattr(camera, "viewport_width", None)
        height = getattr(camera, "viewport_height", None)
        if not width or not height:
            return

        cam_pos = getattr(camera, "position", (0.0, 0.0))
        if isinstance(cam_pos, tuple) or isinstance(cam_pos, list):
            center_x, center_y = cam_pos
        else:
            center_x = getattr(cam_pos, "x", 0.0)
            center_y = getattr(cam_pos, "y", 0.0)

        spawn_rate = 90  # particles per second
        to_spawn = int(spawn_rate * delta_time)
        if random.random() < (spawn_rate * delta_time - to_spawn):
            to_spawn += 1

        if to_spawn <= 0:
            return

        view_min_x = center_x - width / 2
        view_max_x = center_x + width / 2
        spawn_y = center_y + height / 2 + 120

        for _ in range(to_spawn):
            particle = arcade.Sprite(
                center_x=random.uniform(view_min_x, view_max_x),
                center_y=spawn_y + random.uniform(-40, 40),
            )
            particle.texture = self.texture
            particle.alpha = random.randint(220, 255)
            particle.time = 0.0
            particle.lifetime = random.uniform(30.0, 50.0)
            base_heading = 270 + random.uniform(-14, 16)
            base_speed = random.uniform(90, 130)
            set_sprite_motion(particle, base_heading, base_speed)
            sway = random.uniform(-13, 13)
            particle._motion_dx += sway
            particle.scale = random.uniform(0.80, 1.2)
            particle.update()
            self.particles.append(particle)
            if particle not in getattr(game, "overParticles", []):
                game.overParticles.append(particle)

    def _update_particles(self, delta_time: float) -> None:
        for particle in list(self.particles):
            advance_sprite(particle, delta_time)
            particle.time += delta_time
            life_ratio = particle.time / getattr(particle, "lifetime", 0.5)
            if life_ratio >= 1:
                particle.remove_from_sprite_lists()
                if particle in self.particles:
                    self.particles.remove(particle)
                continue
            particle.alpha = max(0, int(particle.alpha * (1 - 0.01 * delta_time)))
            current_scale = particle.scale
            if isinstance(current_scale, tuple):
                new_scale = tuple(val * 0.99 for val in current_scale)
            else:
                new_scale = current_scale * 0.99
            particle.scale = new_scale

class MyGame(arcade.View):
    """
    Main application class.
    """

    def __init__(self, menu, file_num=1, world_gen="Normal", difficulty=1):
        super().__init__()
        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)

        self.time_alive = 0
        self.Christmas_timer = -300
        self.Completed_Christmas = False
        self._returning_to_menu = False
        self.file_num = file_num
        self.difficulty = difficulty
        self.menu = menu
        self.science_list = None

        self._water_ctx = None
        self._water_program = None
        self._water_quad = None
        self._water_texture = None
        self._water_fbo = None
        self._water_overlay_texture = None
        self._water_depth_texture = None
        self._water_depth_data = None
        self._water_shader_failed = False
        self._shore_program = None

        self.setup(file_num, world_gen)
        self._init_water_shader()
        self.create_audio()
        self.updateStorage()

        self.speed = 1
        ui_slider = CustomUISlider(max_value=20, value=2, width=302,
                                   height=35, x=0, offset_x=150, offset_y=-10, button_offset_y=-6)
        label = UILabel(text=f"speed {ui_slider.value*.5:.0f}x")
        self.label = label
        self.ui_slider = ui_slider

        @ui_slider.event()
        def on_change(event: UIOnChangeEvent):
            label.text = f"speed {ui_slider.value*.5:.0f}x"
            self.speed = ui_slider.value*.5
            label.fit_content()

        slider = UIAnchorWidget(
            child=ui_slider, align_x=100, align_y=25, anchor_x="left", anchor_y="bottom")
        ui_slider.wrapper = slider
        self.uimanager.add(slider)
        label_wrapper = UIAnchorWidget(
            child=label, align_x=50, align_y=160, anchor_x="left", anchor_y="bottom")
        label.wrapper = label_wrapper
        self.uimanager.add(self.label)

        expand_button = CustomUIFlatButton({}, click_sound=self.click_sound, text=None, width=64, height=64, offset_x=16, offset_y=16,
                                           Texture="resources/gui/contract.png", Hovered_Texture="resources/gui/contract.png", Pressed_Texture="resources/gui/expand.png")
        expand_button.on_click = self.speed_bar_change
        expand_button.expand = False
        expand_button.buttons = [slider, label_wrapper]
        self.expand_button = expand_button
        self.speed_bar = expand_button
        self._configure_toggle_button_icon(
            expand_button, collapsed_texture="resources/gui/contract.png", expanded_texture="resources/gui/expand.png")
        wrapper = UIAnchorWidget(anchor_x="left", anchor_y="bottom",
                                 child=expand_button, align_x=0, align_y=0)
        expand_button.wrapper = wrapper
        self.uimanager.add(wrapper)

        self.create_ui()
        self.update_audio()

        self.christmas_background = arcade.Sprite(
            "resources/gui/ChristmasOverlay.png", scale=.25, center_x=370, center_y=180)
        self.christmas_background.visible = False
        self.christmas_background.alpha = 0
        self.overParticles.append(self.christmas_background)

        window = arcade.get_window()
        self.on_resize(window.width, window.height)

    def setup(self, file_num, world_gen):
        self.extra_buttons = []
        self.camera = arcade.Camera2D()
        self.not_scrolling_camera = arcade.Camera2D()

        self.lacks = []
        self._storage_frame_valid = False
        self._selection_glow_texture = arcade.make_soft_square_texture(
            180, (255, 225, 120, 70), outer_alpha=0
        )

        self.science = 0
        self.overall_multiplier = 1
        self.training_speed_multiplier = 1
        self.dissent_multiplier = 1
        self.damage_multiplier = 1
        self.growth_multiplier = 1
        self.science_multiplier = 1
        self.presents_multiplier = 1
        self.history_gain_multiplier = 1
        self.wood_multiplier = 1
        self.stone_multiplier = 1
        self.metal_multiplier = 1
        self.building_multiplier = 1

        self.presents = 2000
        self.population = 2
        self.stone = 10
        self.metal = 0
        self.wood = 50
        self.present_quota = 100
        self.failed_presents = 0
        self.max_present_failures = 3

        self.mcsStorage = 500
        self.max_pop = 5
        self.apply_repeatable_upgrades()

        self.timer = 0

        self.x = 0
        self.y = 0

        self.Lands = arcade.SpriteList(use_spatial_hash=True)
        self.Stones = arcade.SpriteList(use_spatial_hash=True)
        self.Seas = arcade.SpriteList(use_spatial_hash=True)
        self.Trees = arcade.SpriteList(use_spatial_hash=True)
        self.BerryBushes = arcade.SpriteList(use_spatial_hash=True)
        self.shoreline_overlay = ShapeElementList()

        self.Fires = arcade.SpriteList(use_spatial_hash=True)
        self.overParticles = arcade.SpriteList()
        self.underParticals = arcade.SpriteList()
        self.fog_layers = arcade.SpriteList(use_spatial_hash=False)
        self.snow_ambience = SnowAmbience()

        self.Buildings = arcade.SpriteList(use_spatial_hash=True)
        self.Boats = arcade.SpriteList()
        self.boatUpdate = 0

        self.People = arcade.SpriteList()
        self.health_bars = arcade.SpriteList()
        self.peopleUpdate = 0
        self.move = False

        self.Enemies = arcade.SpriteList()
        self.EnemyBoats = arcade.SpriteList()
        self.spawnEnemy = -500
        self.hardness_multiplier = 1
        self.min_enemy_spawn_distance = 200
        self.EnemyMap = {}
        self.OpenToEnemies = []
        self._enemy_spawn_counts: dict[tuple[int, int], int] = defaultdict(int)
        self._enemy_spawn_history: deque[tuple[int, int]] = deque()
        self._max_spawn_history = 200

        self.boatUpdate = 0
        self.peopleUpdate = .1
        self.enemyUpdate = .2
        self.fireUpdate = .3

        self.ui_sprites = arcade.SpriteList()
        self.selection_panel = None
        self.selection_panel_visible = False

        self.RiteSlots = 0

        self.left_pressed = False
        self.right_pressed = False
        self.down_pressed = False
        self.up_pressed = False

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        self.unlocked = copy(unlocked)
        self.objects = objects

        self.object_placement = None
        self.object = None
        self.requirements = {"wood": float("inf")}

        self._mouse_position: tuple[float, float] | None = None
        self._preview_position: tuple[float, float] | None = None
        self._preview_valid = False
        self._preview_player_anchor: tuple[float, float] | None = None
        self._preview_viewport: tuple[float, float] | None = None
        self._preview_grid: tuple[int, int] | None = None
        self._preview_object_name: str | None = None
        self._preview_last_check = 0.0
        self._preview_texture_cache: dict[tuple, arcade.Texture] = {}
        self._preview_blocked_by_ui = False
        self._preview_too_far = False

        self.last = None

        try:
            self.load(file_num)
        except FileNotFoundError:
            logging.info(
                "Save slot %s not found; generating new world", file_num)
            self.generateWorld(100, 100, world_gen)
            self.generateEnemySpawner(100, 100)
        except (EOFError, pickle.UnpicklingError) as exc:
            logging.warning(
                "Save slot %s is corrupt or empty (%s); regenerating world", file_num, exc)
            self.generateWorld(100, 100, world_gen)
            self.generateEnemySpawner(100, 100)
        except Exception:
            logging.exception("Failed to load save slot %s", file_num)
            raise

        self._rebuild_water_depth_map()
        self.center_camera()
        self.clear_uimanager()
        self._rebuild_shoreline_overlay()
        self._init_fog_layers()

    def create_audio(self):
        self.audios = self.menu.audios
        self.click_sound = self.menu.click_sound
        self.Background_music = self.menu.Background_music
        self.Christmas_music = self.menu.Christmas_music

        self.audio_type_vols = self.menu.audio_type_vols

        self.update_audio()

    def update_audio(self):
        for audio in self.audios:
            apply_audio_volume(audio, self.audio_type_vols)

    def create_ui(self):
        self.PopUps = []

        textures = load_texture_grid(
            "resources/gui/Wooden Font.png", 14, 24, 12, 71, margin=1)
        self.Alphabet_Textures = {" ": None}
        string = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyz.:,%/-+_'"
        for i in range(len(string)):
            self.Alphabet_Textures[string[i]] = textures[i]

        self.text_timer = 0
        self.text_sprites = []
        self.lack_text = None
        self.lack_popup = None
        self.lack_popup_timer = 0.0
        self.text_visible = True
        self.hud_panel_modes: tuple[str, ...] = ("summary", "detail")
        self.active_hud_mode_index: int = 0
        self.summary_under_sprite = arcade.Sprite(
            "resources/gui/Large Bulletin.png", scale=1.55, center_x=275, center_y=260)
        self.detail_under_sprite = arcade.Sprite(
            "resources/gui/Long Bulletin.png", scale=0.58, center_x=275, center_y=520)
        self.hud_background_offsets = {
            "summary": {"x": 0, "y": 50},
            "detail": {"x": 0, "y": 0},
        }
        self._active_hud_mode: str = self.hud_panel_modes[0]
        self._hud_background_draw_offset: dict[str, float] = {"x": 0.0, "y": 0.0}
        self.under_sprite = self.summary_under_sprite
        window = arcade.get_window()
        window_height = getattr(window, "height", 0) or getattr(
            window, "size", (0, 0))[1]
        if not window_height:
            window_height = getattr(getattr(self, "camera", None),
                                    "viewport_height", 0) or 0
        if window_height <= 0:
            window_height = 900
        self._hud_panel_top_offset = 220.0
        self._hud_detail_extra_offset = 70.0
        panel_center_y = window_height - self._hud_panel_top_offset
        self.summary_under_sprite.center_y = panel_center_y
        self.detail_under_sprite.center_y = panel_center_y - self._hud_detail_extra_offset
        self._hud_anchor_center: Optional[tuple[float, float]] = (
            float(self.under_sprite.center_x),
            float(self.under_sprite.center_y),
        )
        self.update_text(1)

        self.selection_panel_position = (200, 110)
        self.selection_panel_width = 260
        self.selection_panel = CustomTextSprite(
            None,
            self.Alphabet_Textures,
            center_x=self.selection_panel_position[0],
            center_y=self.selection_panel_position[1],
            width=self.selection_panel_width,
            Background_Texture="resources/gui/Small Text Background.png",
            Background_scale=1.1,
            vertical_align='top',
        )
        self.selection_panel_visible = False

        self._active_lack_popup_type: Optional[str] = None

        summary_contract_texture = arcade.load_texture(
            "resources/gui/contract.png")
        summary_toggle = UITextureButton(
            texture=summary_contract_texture,
            texture_hovered=summary_contract_texture,
            texture_pressed=summary_contract_texture,
            scale=2,
        )
        summary_toggle.on_click = self.expand_button_click
        summary_toggle.expand = False
        self.expand_button = summary_toggle
        self._configure_toggle_button_icon(
            summary_toggle, collapsed_texture="resources/gui/contract.png", expanded_texture="resources/gui/expand.png")
        wrapper = UIAnchorWidget(anchor_x="left", anchor_y="top",
                                 child=summary_toggle, align_x=0, align_y=-30)
        summary_toggle.wrapper = wrapper
        self.uimanager.add(wrapper)

        self.secondary_wrappers = []
        main_button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Panels", width=140, height=50)
        main_button.on_click = self.main_button_click
        main_button.open = False
        self.main_button = main_button
        wrapper = UIAnchorWidget(anchor_x="right", anchor_y="top",
                                 child=main_button, align_x=-50, align_y=-50)
        main_button.wrapper = wrapper
        self.uimanager.add(wrapper)

        button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Menus", width=140, height=50)
        button.on_click = self.menus_button_click
        button.open = False
        self.menus_button = button
        wrapper = UIAnchorWidget(anchor_x="right", anchor_y="top",
                                 child=button, align_x=150, align_y=-50)
        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.secondary_wrappers.append(wrapper)
        self.menu_buttons = []

        button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Science Menu", width=140, height=50)
        button.cost = float('inf')
        button.on_click = self.on_ScienceMenuclick
        wrapper = UIAnchorWidget(anchor_x="right", anchor_y="top",
                                 child=button, align_x=150, align_y=-50)
        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.menu_buttons.append(wrapper)

        button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Volume Menu", width=140, height=50)
        button.cost = float('inf')
        button.on_click = self.on_VolumeMenuclick
        wrapper = UIAnchorWidget(anchor_x="right", anchor_y="top",
                                 child=button, align_x=150, align_y=-150)
        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.menu_buttons.append(wrapper)

        button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Save", width=140, height=50)
        button.on_click = self.save
        wrapper = UIAnchorWidget(anchor_x="right", anchor_y="top",
                                 child=button, align_x=150, align_y=-150)
        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.secondary_wrappers.append(wrapper)

        button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Deploy", width=140, height=50)
        button.on_click = self.selectables_click
        button.open = False
        wrapper = UIAnchorWidget(anchor_x="right", anchor_y="top",
                                 child=button, align_x=150, align_y=-250)
        button.wrapper = wrapper

        self.selectables_button = button
        self.uimanager.add(wrapper)
        self.secondary_wrappers.append(wrapper)
        self.selectables = []

        button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Return", width=140, height=50)
        button.on_click = self.return_to_menu
        wrapper = UIAnchorWidget(anchor_x="right", anchor_y="top",
                                 child=button, align_x=250, align_y=-350)
        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.secondary_wrappers.append(wrapper)

        button = CustomUIFlatButton(self.Alphabet_Textures, click_sound=self.click_sound,
                                    text="Buildings", width=140, height=50, text_margin=14)
        button.cost = float('inf')
        button.value = 1
        button.on_click = self.switch_val
        wrapper = UIAnchorWidget(anchor_x="right", anchor_y="top",
                                 child=button, align_x=150, align_y=-50)
        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.selectables.append(wrapper)

        button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="People", width=140, height=50)
        button.cost = float('inf')
        button.value = 2
        button.on_click = self.switch_val
        wrapper = UIAnchorWidget(anchor_x="right", anchor_y="top",
                                 child=button, align_x=150, align_y=-150)
        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.selectables.append(wrapper)

        button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Boats", width=140, height=50)
        button.cost = float('inf')
        button.value = 3
        button.on_click = self.switch_val
        wrapper = UIAnchorWidget(anchor_x="right", anchor_y="top",
                                 child=button, align_x=150, align_y=-250)
        button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.selectables.append(wrapper)

    def on_resize(self, width: int, height: int):
        self.camera.match_window()
        self.center_camera()

        self.not_scrolling_camera.match_window(position=True)

        if self.ui_sprites:
            move_x = width-50
            move_y = height-0
            y = move_y
        for sprite in self.ui_sprites:
            y -= 50
            sprite.center_x = move_x
            sprite.center_y = y

        panel_offset = getattr(self, "_hud_panel_top_offset", 220.0)
        detail_extra = getattr(self, "_hud_detail_extra_offset", 50.0)
        summary_sprite = getattr(self, "summary_under_sprite", None)
        detail_sprite = getattr(self, "detail_under_sprite", None)
        panels = [
            (summary_sprite, 0.0),
            (detail_sprite, detail_extra),
        ]
        anchor_sprite = getattr(self, "under_sprite", None)
        prev_anchor = getattr(self, "_hud_anchor_center", None)
        new_anchor = None
        for sprite, extra in panels:
            if not sprite:
                continue
            sprite.center_y = height - (panel_offset + extra)
            if sprite is anchor_sprite:
                new_anchor = (float(sprite.center_x), float(sprite.center_y))
        if new_anchor and prev_anchor is not None:
            dx = new_anchor[0] - prev_anchor[0]
            dy = new_anchor[1] - prev_anchor[1]
            if dx or dy:
                for text_sprite in self.text_sprites:
                    text_sprite.translate(dx, dy)
        if new_anchor:
            self._hud_anchor_center = new_anchor
        if getattr(self, "text_sprites", None):
            self.update_text(0, force=True)
        self.christmas_background.position = self.player.center_x, self.player.center_y
        self.christmas_background.scale = .25*max(width/1240, height/900)

        resize_ui_manager(self, width, height)
        self._update_water_framebuffer(width, height)
        return super().on_resize(width, height)

    def End(self, reason: str | None = None, force_menu: bool = False, extra_lines: list[str] | None = None):
        self.science_list = None
        self.uimanager.disable()

        if self.file_num:
            file_path = get_save_path(self.file_num)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch(exist_ok=True)
            with file_path.open("r+") as file:
                file.truncate()

        num = self.time_alive-300
        if num > 0:
            history = 2*1.5**(num/60)
        else:
            history = 0
        history *= getattr(self, "history_gain_multiplier", 1)
        with open("resources/game.json", "r") as read_file:
            try:
                p = json.load(read_file)
                p["History"] += history
            except:
                p = {}
                science_unlocked = {}
                with open("resources/GameBase.json", "r") as read_file:
                    menu_config = json.load(read_file)

                for idx, node in enumerate(menu_config["ScienceMenu"]):
                    name = node[0] or f"science_{idx}"
                    science_unlocked[name] = bool(node[8])
                p["science_menu"] = science_unlocked
                p["History"] = history

                self.graph = None

        with open("resources/game.json", "w") as write_file:
            json.dump(p, write_file)
        global prev_frame
        prev_frame = {"presents": 1000, "wood": 0, "stone": 0, "metal": 0}

        if self.Christmas_music:
            if self.Christmas_music.player:
                self.Christmas_music.stop(self.Christmas_music.player)
        self.Christmas_music = None

        if force_menu:
            message = reason or "The workshop could not meet the children's demands."
            game_over = GameOverView(self.menu, message)
            show_view_resized(self.window, game_over)
        else:
            Endmenu = EndMenu(history, self, self.menu,
                              reason, extra_lines=extra_lines)
            show_view_resized(self.window, Endmenu)

    def return_to_menu(self, event):
        self._returning_to_menu = True
        global prev_frame
        prev_frame = {"presents": 1000, "wood": 0, "stone": 0, "metal": 0}

        if self.Christmas_music:
            if self.Christmas_music.player:
                self.Christmas_music.stop(self.Christmas_music.player)
        self.Christmas_music = None

        self.uimanager.disable()
        self.menu.uimanager.enable()
        self.science_list = None
        window = arcade.get_window()
        width = getattr(window, "width", 0) or getattr(window, "size", (0, 0))[0]
        height = getattr(window, "height", 0) or getattr(window, "size", (0, 0))[1]
        show_view_resized(self.window, self.menu)
        if hasattr(self.menu, "on_resize") and width and height:
            self.menu.on_resize(width, height)

    def main_button_click(self, event):
        if event.source.open:
            for wrapper in self.menu_buttons:
                wrapper.align_x = 250
            for wrapper in self.selectables:
                wrapper.align_x = 250
            for wrapper in self.secondary_wrappers:
                wrapper.align_x = 250
            event.source.wrapper.align_x = -50
            event.source.open = False
            self.ui_sprites = arcade.SpriteList()
            self.object_placement = None
            self.object = None
            self.requirements = {"wood": float("inf")}
            self.secondary_wrappers[0].child.open = False
            self.secondary_wrappers[2].child.open = False
            self.hide_selection_panel()
        else:
            for wrapper in self.secondary_wrappers:
                wrapper.align_x = -50
            event.source.wrapper.align_x = -200
            event.source.open = True

    def menus_button_click(self, event):
        if event.source.open:
            for wrapper in self.menu_buttons:
                wrapper.align_x = 250
            for wrapper in self.secondary_wrappers:
                wrapper.align_x = -50
            self.main_button.wrapper.align_x = -200
            event.source.open = False
            self.hide_selection_panel()
        else:
            for wrapper in self.selectables:
                wrapper.align_x = 250
            for wrapper in self.menu_buttons:
                wrapper.align_x = -50
            for wrapper in self.secondary_wrappers:
                wrapper.align_x = -200
            self.main_button.wrapper.align_x = -350
            event.source.open = True
            self.selectables_button.open = False

            self.ui_sprites = arcade.SpriteList()
            self.object_placement = None
            self.object = None
            self.requirements = {"wood": float("inf")}
            self.hide_selection_panel()

    def selectables_click(self, event):
        if event.source.open:
            for wrapper in self.menu_buttons:
                wrapper.align_x = 250
            for wrapper in self.selectables:
                wrapper.align_x = 250
            for wrapper in self.secondary_wrappers:
                wrapper.align_x = -50
            self.main_button.wrapper.align_x = -200

            self.ui_sprites = arcade.SpriteList()
            self.object_placement = None
            self.object = None
            self.requirements = {"wood": float("inf")}
            self.hide_selection_panel()
        else:
            for wrapper in self.menu_buttons:
                wrapper.align_x = 250
            for wrapper in self.selectables:
                wrapper.align_x = -50
            for wrapper in self.secondary_wrappers:
                wrapper.align_x = -200
            self.main_button.wrapper.align_x = -350
            self.menus_button.open = False
        event.source.open = not event.source.open

    def expand_button_click(self, event):
        click_sound = getattr(self, "click_sound", None)
        if click_sound:
            try:
                click_sound.play()
            except Exception:
                pass
        event.source.expand = not getattr(event.source, "expand", False)
        self._apply_toggle_button_icon(event.source, event.source.expand)
        self.text_visible = not event.source.expand
        self.update_text(1)

    def speed_bar_change(self, event):
        event.source.expand = not getattr(event.source, "expand", False)
        self._apply_toggle_button_icon(event.source, event.source.expand)
        if event.source.expand:
            for wrapper in event.source.buttons:
                wrapper.org_x = wrapper.align_x
                wrapper.align_x = -1000
        else:
            for wrapper in event.source.buttons:
                wrapper.align_x = wrapper.org_x

    def _configure_toggle_button_icon(self, button, collapsed_texture: str, expanded_texture: str) -> None:
        textures = {
            False: arcade.load_texture(collapsed_texture),
            True: arcade.load_texture(expanded_texture),
        }
        button._toggle_icon_textures = textures
        self._apply_toggle_button_icon(button, getattr(button, "expand", False))

    @staticmethod
    def _apply_toggle_button_icon(button, expanded: bool) -> None:
        textures = getattr(button, "_toggle_icon_textures", None)
        if not textures:
            return
        texture = textures.get(expanded)
        if texture is None:
            return
        if hasattr(button, "sprite"):
            for sprite in (getattr(button, "sprite", None), getattr(button, "hovered_sprite", None), getattr(button, "pressed_sprite", None)):
                if sprite:
                    sprite.texture = texture
        else:
            if hasattr(button, "texture"):
                button.texture = texture
            if hasattr(button, "texture_hovered"):
                button.texture_hovered = texture
            if hasattr(button, "texture_pressed"):
                button.texture_pressed = texture

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
                ui_sprite = arcade.Sprite(center_x=move_x, center_y=y)
                sprite = self.objects[obj](self, move_x, y)
                ui_sprite.texture = sprite.texture
                ui_sprite.name = obj
                ui_sprite.object_placement = source
                ui_sprite.requirements = requirements[obj]

                self.ui_sprites.append(ui_sprite)
                if isinstance(sprite, Person):
                    sprite.destroy(self, count_population=False)
                else:
                    sprite.destroy(self)

    def hide_selection_panel(self):
        self.selection_panel_visible = False

    def show_selection_panel(self, text):
        if not self.selection_panel:
            return
        self.selection_panel.update_text(
            text,
            self.Alphabet_Textures,
            center_x=self.selection_panel_position[0],
            center_y=self.selection_panel_position[1],
            width=self.selection_panel_width,
            vertical_align='top',
        )
        self.selection_panel_visible = True

    def _world_to_screen(self, world_x: float, world_y: float) -> tuple[float, float]:
        camera = getattr(self, "camera", None)
        player = getattr(self, "player", None)
        if not camera or not player:
            return world_x, world_y
        screen_x = world_x - player.center_x + (camera.viewport_width / 2)
        screen_y = world_y - player.center_y + (camera.viewport_height / 2)
        margin = 30
        if screen_x < margin:
            screen_x = margin
        elif screen_x > camera.viewport_width - margin:
            screen_x = camera.viewport_width - margin
        if screen_y < margin:
            screen_y = margin
        elif screen_y > camera.viewport_height - margin:
            screen_y = camera.viewport_height - margin
        return screen_x, screen_y

    def _clear_object_selection(self) -> None:
        self.object = None
        self.object_placement = None
        self.requirements = {"wood": float("inf")}
        self._clear_preview_state()
        self.hide_selection_panel()

    def show_move_feedback(self, message: str, world_x: float | None = None, world_y: float | None = None, duration: float = 0.8) -> None:
        if world_x is None or world_y is None:
            world_x, world_y = getattr(self.player, "position", (0, 0))
        screen_x, screen_y = self._world_to_screen(world_x, world_y)
        info_sprite = UpdatingText(message, self.Alphabet_Textures,
                                   duration, width=260, center_x=screen_x, center_y=screen_y)
        self.PopUps.append(info_sprite)

    def show_lack_popup(self, text, screen_x, screen_y, duration=3):
        self.lack_popup_timer = time.time() + duration
        self.lack_popup = CustomTextSprite(
            text,
            self.Alphabet_Textures,
            center_x=screen_x,
            center_y=screen_y,
            width=200,
            text_margin=14,
        )
        self._active_lack_popup_type = text

    def refresh_population(self) -> int:
        """Recompute population based on active sprites and return it."""
        alive_people = len(self.People)
        people_in_buildings = sum(
            len(getattr(building, "list_of_people", [])) for building in self.Buildings)
        people_on_boats = sum(len(getattr(boat, "list", []))
                              for boat in self.Boats)
        self.population = alive_people + people_in_buildings + people_on_boats
        return self.population

    def _add_lack(self, lack_name: str):
        if lack_name not in self.lacks:
            self.lacks.append(lack_name)

    def on_ScienceMenuclick(self, event):
        self.ui_sprites = arcade.SpriteList()
        self.object_placement = None
        self.object = None
        self.requirements = {"wood": float("inf")}
        self.hide_selection_panel()

        self.uimanager.disable()
        show_view_resized(self.window, ScienceMenu(self))

    def on_VolumeMenuclick(self, event):
        self.ui_sprites = arcade.SpriteList()
        self.object_placement = None
        self.object = None
        self.requirements = {"wood": float("inf")}
        self.hide_selection_panel()

        self.uimanager.disable()
        show_view_resized(self.window, VolumeMenu(self))

    def on_SelectionMenuclick(self, event):
        self.uimanager.disable()
        show_view_resized(self.window, BuildingMenu(self))

    def activate_Christmas(self):
        if self._returning_to_menu:
            return
        if self.presents < self.present_quota:
            self.End("The workshop could not meet the children's demands.")
            return

        self.update_text(1)
        self.uimanager.disable()
        show_view_resized(self.window, ChristmasMenu(self))

    def training_menu(self, event):
        self.uimanager.disable()
        show_view_resized(self.window, TrainingMenu(self, event.source.building))

    def apply_christmas_success(self):
        self.presents -= self.present_quota
        if self.presents < 0:
            self.presents = 0
        self.present_quota = ceil(self.present_quota * 1.08)
        self.Completed_Christmas = False
        self.Christmas_timer = 0

    def resume_after_christmas(self):
        self.apply_christmas_success()
        self.uimanager.enable()
        self.center_camera()
        show_view_resized(self.window, self)

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
        self.clear()
        self.camera.use()

        self.Lands.draw()
        self._draw_water_layer()
        self.Stones.draw()
        self.Trees.draw()
        self.BerryBushes.draw()
        self.underParticals.draw()

        selected = getattr(self, "last", None)

        self.Buildings.draw()
        self._draw_empty_building_overlay()

        self.Boats.draw()

        self.People.draw()
        self.player.draw()

        self.Enemies.draw()
        self.EnemyBoats.draw()

        self.health_bars.draw()
        self.Fires.draw()
        self.overParticles.draw()
        self.fog_layers.draw(pixelated=True)

        self._draw_placement_preview()

        self._draw_out_of_bounds_overlay()

        if selected:
            self._draw_selection_glow(selected)
            self._draw_selection_overlay(selected)
            self._redraw_selection_stack(selected)
            self._redraw_selected_health_bar(selected)
            self._draw_selection_border(selected)

        self.not_scrolling_camera.use()
        self.christmas_background.draw()

        self.uimanager.draw()
        self.ui_sprites.draw()

        if self.text_visible:
            offset = getattr(self, "_hud_background_draw_offset", {"x": 0.0, "y": 0.0})
            sprite = getattr(self, "under_sprite", None)
            if sprite:
                original_x, original_y = sprite.center_x, sprite.center_y
                sprite.center_x = original_x + offset.get("x", 0.0)
                sprite.center_y = original_y + offset.get("y", 0.0)
                sprite.draw()
                sprite.center_x = original_x
                sprite.center_y = original_y
            for text in self.text_sprites:
                text.draw()
            if self.lack_text:
                self.lack_text.draw()
        if self.lack_popup:
            if time.time() > self.lack_popup_timer:
                self.lack_popup = None
            else:
                self.lack_popup.draw()
        if self.selection_panel_visible and self.selection_panel:
            self.selection_panel.draw()
        for PopUp in self.PopUps:
            PopUp.draw()

    def _draw_placement_preview(self) -> None:
        if (
            not self.object
            or not self._preview_position
            or self._preview_blocked_by_ui
            or self._preview_too_far
        ):
            return

        world_x, world_y = self._preview_position
        tile_size = 50
        if self._preview_valid:
            fill_color = (60, 180, 110, 120)
            border_color = (150, 255, 170, 180)
        else:
            fill_color = (200, 80, 80, 120)
            border_color = (255, 150, 150, 190)

        draw_rect_filled(XYWH(world_x, world_y, tile_size, tile_size), fill_color)
        draw_rect_outline(XYWH(world_x, world_y, tile_size, tile_size), border_color, 2)
        preview_texture = self._resolve_preview_texture()
        if preview_texture:
            texture, scale = preview_texture
            alpha = 210 if self._preview_valid else 160
            width = max(1.0, texture.width * scale)
            height = max(1.0, texture.height * scale)
            self._draw_preview_texture(texture, world_x, world_y, width, height, alpha)

    def _draw_out_of_bounds_overlay(self) -> None:
        """Darken regions outside the generated world when the camera sees them."""
        camera = getattr(self, "camera", None)
        player = getattr(self, "player", None)
        if not camera or not getattr(self, "x_line", None) or not getattr(self, "y_line", None):
            return

        width = getattr(camera, "viewport_width", None)
        height = getattr(camera, "viewport_height", None)
        if not width or not height:
            return

        if player:
            center_x = getattr(player, "center_x", 0.0)
            center_y = getattr(player, "center_y", 0.0)
        else:
            cam_pos = getattr(camera, "position", (0.0, 0.0))
            if isinstance(cam_pos, tuple) or isinstance(cam_pos, list):
                center_x, center_y = cam_pos
            else:
                center_x = getattr(cam_pos, "x", 0.0)
                center_y = getattr(cam_pos, "y", 0.0)

        half_width = width / 2
        half_height = height / 2
        view_min_x = center_x - half_width
        view_max_x = center_x + half_width
        view_min_y = center_y - half_height
        view_max_y = center_y + half_height

        tile_size = 50
        world_min_x = 0
        world_min_y = 0
        world_max_x = self.x_line * tile_size
        world_max_y = self.y_line * tile_size

        edge_padding = 900
        pad_tiles = max(0, int(edge_padding // tile_size))
        allowed_min_x = max(world_min_x, pad_tiles * tile_size)
        allowed_min_y = max(world_min_y, pad_tiles * tile_size)
        allowed_max_x = min(world_max_x, world_max_x - pad_tiles * tile_size)
        allowed_max_y = min(world_max_y, world_max_y - pad_tiles * tile_size)
        if allowed_max_x < allowed_min_x:
            allowed_max_x = allowed_min_x
        if allowed_max_y < allowed_min_y:
            allowed_max_y = allowed_min_y

        inner_color = (5, 5, 15, 180)
        outer_color = (5, 5, 15, 215)
        boundary_color = (130, 90, 50, 220)
        inner_mask_needed = False

        def _draw_rect(x_min: float, x_max: float, y_min: float, y_max: float, color) -> None:
            width = max(0.0, x_max - x_min)
            height = max(0.0, y_max - y_min)
            if width <= 0 or height <= 0:
                return
            center_x = x_min + (width / 2)
            center_y = y_min + (height / 2)
            draw_rect_filled(XYWH(center_x, center_y, width, height), color)

        if view_min_x < allowed_min_x:
            inner_mask_needed = True
            _draw_rect(view_min_x, allowed_min_x, view_min_y,
                       view_max_y, inner_color)
        if view_max_x > allowed_max_x:
            inner_mask_needed = True
            _draw_rect(allowed_max_x, view_max_x, view_min_y,
                       view_max_y, inner_color)
        if view_min_y < allowed_min_y:
            inner_mask_needed = True
            lower_x_min = max(view_min_x, allowed_min_x)
            lower_x_max = min(view_max_x, allowed_max_x)
            _draw_rect(lower_x_min, lower_x_max, view_min_y,
                       allowed_min_y, inner_color)
        if view_max_y > allowed_max_y:
            inner_mask_needed = True
            upper_x_min = max(view_min_x, allowed_min_x)
            upper_x_max = min(view_max_x, allowed_max_x)
            _draw_rect(upper_x_min, upper_x_max, allowed_max_y,
                       view_max_y, inner_color)

        if view_min_x < world_min_x:
            _draw_rect(view_min_x, world_min_x, view_min_y,
                       view_max_y, outer_color)
        if view_max_x > world_max_x:
            _draw_rect(world_max_x, view_max_x, view_min_y,
                       view_max_y, outer_color)
        if view_min_y < world_min_y:
            lower_x_min = max(view_min_x, world_min_x)
            lower_x_max = min(view_max_x, world_max_x)
            _draw_rect(lower_x_min, lower_x_max, view_min_y,
                       world_min_y, outer_color)
        if view_max_y > world_max_y:
            upper_x_min = max(view_min_x, world_min_x)
            upper_x_max = min(view_max_x, world_max_x)
            _draw_rect(upper_x_min, upper_x_max, world_max_y,
                       view_max_y, outer_color)

        if inner_mask_needed:
            allowed_width = max(0.0, allowed_max_x - allowed_min_x)
            allowed_height = max(0.0, allowed_max_y - allowed_min_y)
            if allowed_width > 0 and allowed_height > 0:
                draw_rect_outline(
                    XYWH(
                        allowed_min_x + allowed_width / 2,
                        allowed_min_y + allowed_height / 2,
                        allowed_width,
                        allowed_height,
                    ),
                    boundary_color,
                    4,
                )

    def _rebuild_shoreline_overlay(self) -> None:
        self.shoreline_overlay = ShapeElementList()

    def _init_fog_layers(self) -> None:
        self.fog_layers = arcade.SpriteList(use_spatial_hash=False)
        world_width = getattr(self, "x_line", 0) * 50
        world_height = getattr(self, "y_line", 0) * 50
        if world_width <= 0 or world_height <= 0:
            return
        texture_size = 192
        fog_color = (150, 155, 165, 30)
        texture = arcade.make_soft_square_texture(texture_size, fog_color, outer_alpha=0)
        world_area = max(1.0, world_width * world_height)
        density_factor = min(16, max(6, int(world_area / 2_000_000)))
        for _ in range(density_factor):
            sprite = arcade.Sprite(center_x=random.uniform(0, world_width), center_y=random.uniform(0, world_height))
            sprite.texture = texture
            sprite.scale = random.uniform(2.7, 3.4)
            base_alpha = random.randint(50, 90)
            sprite.alpha = min(255, int(base_alpha * 1.1))
            sprite.change_x = random.uniform(2.2, 6.5)
            sprite.change_y = random.uniform(-1.8, 1.8)
            sprite._drift_speed = random.uniform(0.45, 1.0)
            self.fog_layers.append(sprite)

    def _update_fog_layers(self, delta_time: float) -> None:
        if not self.fog_layers:
            return
        world_width = getattr(self, "x_line", 0) * 50
        world_height = getattr(self, "y_line", 0) * 50
        if world_width <= 0 or world_height <= 0:
            return
        margin = 200.0
        for sprite in self.fog_layers:
            drift_scale = getattr(sprite, "_drift_speed", 1.0)
            sprite.center_x += sprite.change_x * delta_time * drift_scale
            sprite.center_y += sprite.change_y * delta_time * drift_scale
            if sprite.center_x < -margin:
                sprite.center_x = world_width + margin
            elif sprite.center_x > world_width + margin:
                sprite.center_x = -margin
            if sprite.center_y < -margin:
                sprite.center_y = world_height + margin
            elif sprite.center_y > world_height + margin:
                sprite.center_y = -margin

    def _init_water_shader(self) -> None:
        if self._water_shader_failed:
            return
        window = arcade.get_window()
        if not window:
            return
        ctx = window.ctx
        self._water_ctx = ctx
        try:
            self._water_program = ctx.program(
                vertex_shader=WATER_VERTEX_SHADER,
                fragment_shader=WATER_FRAGMENT_SHADER,
            )
        except Exception:
            logging.exception("Failed to compile water shader")
            self._water_program = None
            self._water_shader_failed = True
            return

        self._water_quad = geometry.quad_2d_fs()
        self._update_water_framebuffer(window.width, window.height)
        if self._water_overlay_texture is None:
            self._load_water_overlay_texture()
        if self._water_depth_texture is None and self._water_depth_data:
            self._upload_water_depth_texture()

    def _update_water_framebuffer(self, width: int, height: int) -> None:
        if not self._water_ctx or not width or not height:
            return
        width = max(1, int(width))
        height = max(1, int(height))
        texture = getattr(self, "_water_texture", None)
        if texture and texture.width == width and texture.height == height:
            return
        self._release_water_framebuffer()

        texture = self._water_ctx.texture((width, height))
        texture.filter = self._water_ctx.LINEAR, self._water_ctx.LINEAR
        self._water_texture = texture
        self._water_fbo = self._water_ctx.framebuffer(color_attachments=[texture])

    def _release_water_framebuffer(self) -> None:
        if getattr(self, "_water_fbo", None):
            try:
                self._water_fbo.release()
            except Exception:
                pass
        if getattr(self, "_water_texture", None):
            try:
                self._water_texture.release()
            except Exception:
                pass
        self._water_fbo = None
        self._water_texture = None

    def _load_water_overlay_texture(self) -> None:
        if not self._water_ctx:
            return
        if not WATER_OVERLAY_PATH.exists():
            self._water_overlay_texture = None
            return
        try:
            texture = self._water_ctx.load_texture(str(WATER_OVERLAY_PATH))
        except Exception:
            logging.exception("Failed to load water overlay texture")
            self._water_overlay_texture = None
            return
        texture.wrap_x = self._water_ctx.REPEAT
        texture.wrap_y = self._water_ctx.REPEAT
        texture.filter = self._water_ctx.LINEAR, self._water_ctx.LINEAR
        self._water_overlay_texture = texture

    def _upload_water_depth_texture(self) -> None:
        if not self._water_ctx or not self._water_depth_data:
            self._release_water_depth_texture()
            return
        data, width, height = self._water_depth_data
        try:
            texture = self._water_ctx.texture(
                (width, height),
                components=1,
                data=data.tobytes(),
                dtype='f4',
            )
        except Exception:
            logging.exception("Failed to upload water depth texture")
            return
        texture.wrap_x = self._water_ctx.CLAMP_TO_EDGE
        texture.wrap_y = self._water_ctx.CLAMP_TO_EDGE
        texture.filter = self._water_ctx.LINEAR, self._water_ctx.LINEAR
        self._water_depth_texture = texture

    def _release_water_depth_texture(self) -> None:
        if getattr(self, "_water_depth_texture", None):
            try:
                self._water_depth_texture.release()
            except Exception:
                pass
        self._water_depth_texture = None

    def _rebuild_water_depth_map(self) -> None:
        x_line = getattr(self, "x_line", 0)
        y_line = getattr(self, "y_line", 0)
        graph = getattr(self, "graph", None)
        if not x_line or not y_line or graph is None:
            self._water_depth_data = None
            self._release_water_depth_texture()
            return

        depth_map: list[list[float]] = [
            [math.inf for _ in range(y_line)] for _ in range(x_line)
        ]
        visited = [[False for _ in range(y_line)] for _ in range(x_line)]

        def is_water(ix: int, iy: int) -> bool:
            if ix < 0 or iy < 0 or ix >= x_line or iy >= y_line:
                return False
            return graph[ix][iy] == 2

        neighbor_offsets = [
            (1, 0, 1.0),
            (-1, 0, 1.0),
            (0, 1, 1.0),
            (0, -1, 1.0),
            (1, 1, math.sqrt(2.0)),
            (1, -1, math.sqrt(2.0)),
            (-1, 1, math.sqrt(2.0)),
            (-1, -1, math.sqrt(2.0)),
        ]

        for ix in range(x_line):
            for iy in range(y_line):
                if not is_water(ix, iy) or visited[ix][iy]:
                    continue

                stack = [(ix, iy)]
                visited[ix][iy] = True
                component: list[tuple[int, int]] = []
                while stack:
                    cx, cy = stack.pop()
                    component.append((cx, cy))
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = cx + dx, cy + dy
                        if not is_water(nx, ny) or visited[nx][ny]:
                            continue
                        visited[nx][ny] = True
                        stack.append((nx, ny))

                comp_set = set(component)
                seeds = []
                for cx, cy in component:
                    touches_land = False
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        if not is_water(cx + dx, cy + dy):
                            touches_land = True
                            break
                    if touches_land:
                        seeds.append((cx, cy))

                if not seeds:
                    seeds = component.copy()

                pq: list[tuple[float, int, int]] = []
                for cx, cy in component:
                    depth_map[cx][cy] = math.inf
                for sx, sy in seeds:
                    depth_map[sx][sy] = 0.0
                    heapq.heappush(pq, (0.0, sx, sy))

                comp_max = 0.0
                while pq:
                    current_dist, cx, cy = heapq.heappop(pq)
                    if current_dist > depth_map[cx][cy]:
                        continue
                    comp_max = max(comp_max, current_dist)
                    for dx, dy, cost in neighbor_offsets:
                        nx, ny = cx + dx, cy + dy
                        if (nx, ny) not in comp_set:
                            continue
                        candidate = current_dist + cost
                        if candidate + 1e-5 < depth_map[nx][ny]:
                            depth_map[nx][ny] = candidate
                            heapq.heappush(pq, (candidate, nx, ny))

                if comp_max <= 0.0:
                    comp_max = 1.0

                for cx, cy in component:
                    value = depth_map[cx][cy]
                    if math.isinf(value):
                        value = comp_max
                    normalized = min((value / comp_max) * WATER_DEPTH_SCALE, 1.0)
                    depth_map[cx][cy] = normalized

        data = array('f')
        for iy in range(y_line):
            for ix in range(x_line):
                value = depth_map[ix][iy]
                if math.isinf(value):
                    value = 0.0
                data.append(float(value))

        self._water_depth_data = (data, x_line, y_line)
        if self._water_ctx:
            self._upload_water_depth_texture()

    def _draw_water_layer(self) -> None:
        if not self.Seas:
            return
        if (not self._water_program or not self._water_fbo or
                not self._water_quad or not self._water_texture):
            if not self._water_shader_failed:
                self._init_water_shader()
        if (not self._water_program or not self._water_fbo or not self._water_quad or
                not self._water_texture):
            self.Seas.draw()
            return
        window = arcade.get_window()
        if not window:
            self.Seas.draw()
            return

        render_width = int(window.width or 1)
        render_height = int(window.height or 1)
        self._update_water_framebuffer(render_width, render_height)
        ctx = self._water_ctx
        ctx_vp = getattr(ctx, "viewport", None)

        try:
            self._water_fbo.use()
        except Exception:
            logging.exception("Failed to bind water framebuffer")
            self.Seas.draw()
            return

        if not ctx:
            self.Seas.draw()
            return

        orig_viewport = getattr(ctx, "viewport", None)
        try:
            ctx.viewport = (0, 0, render_width, render_height)
        except Exception:
            pass
        orig_cam_vw = getattr(self.camera, "viewport_width", None)
        orig_cam_vh = getattr(self.camera, "viewport_height", None)
        if orig_cam_vw is not None:
            try:
                self.camera.viewport_width = render_width
                self.camera.viewport_height = render_height
            except Exception:
                pass

        self.camera.use()
        self._water_fbo.clear(color=(0, 0, 0, 0))
        self.Seas.draw()

        window.use()
        try:
            if orig_viewport is not None:
                ctx.viewport = orig_viewport
            else:
                ctx.viewport = (0, 0, window.width, window.height)
        except Exception:
            pass

        if orig_cam_vw is not None:
            try:
                self.camera.viewport_width = orig_cam_vw
                self.camera.viewport_height = orig_cam_vh
            except Exception:
                pass

        previous_camera = getattr(window, "current_camera", None)
        try:
            ctx.viewport = (0, 0, window.width, window.height)
        except Exception:
            pass
        window.use()

        self._water_texture.use(0)
        ctx.enable(ctx.BLEND)
        self._water_program["base_texture"] = 0

        viewport_width = getattr(self.camera, "viewport_width", window.width)
        viewport_height = getattr(self.camera, "viewport_height", window.height)
        cam_pos = getattr(self.camera, "position", (viewport_width / 2, viewport_height / 2))
        if not isinstance(cam_pos, (tuple, list)):
            cam_pos = getattr(cam_pos, "x", 0.0), getattr(cam_pos, "y", 0.0)
        cam_x, cam_y = float(cam_pos[0]), float(cam_pos[1])
        world_origin = (
            cam_x - viewport_width / 2,
            cam_y - viewport_height / 2,
        )
        self._water_program["u_world_origin"] = (
            float(world_origin[0]),
            float(world_origin[1]),
        )
        self._water_program["u_world_size"] = (
            float(viewport_width),
            float(viewport_height),
        )

        world_width = max(self.x_line * WATER_TILE_SIZE, 1)
        world_height = max(self.y_line * WATER_TILE_SIZE, 1)

        overlay_unit = 1
        if self._water_overlay_texture:
            self._water_overlay_texture.use(overlay_unit)
            self._water_program["overlay_texture"] = overlay_unit
            overlay_repeat = WATER_OVERLAY_REPEAT
            self._water_program["u_overlay_scale"] = (
                float(overlay_repeat),
                float(overlay_repeat),
            )
            self._water_program["u_overlay_offset"] = (
                float(world_origin[0] / max(world_width, 1) * overlay_repeat),
                float(world_origin[1] / max(world_height, 1) * overlay_repeat),
            )
        else:
            self._water_program["overlay_texture"] = 0
            self._water_program["u_overlay_scale"] = (1.0, 1.0)
            self._water_program["u_overlay_offset"] = (0.0, 0.0)

        depth_unit = 2
        self._water_program["u_depth_scale"] = (
            1.0 / float(world_width),
            1.0 / float(world_height),
        )
        if self._water_depth_texture:
            self._water_depth_texture.use(depth_unit)
            self._water_program["depth_texture"] = depth_unit
        else:
            self._water_program["depth_texture"] = 0

        time_alive = float(getattr(self, "time_alive", 0.0))
        self._water_program["u_time"] = time_alive * WATER_TIME_SCALE
        display_width = window.width
        display_height = window.height
        ctx_screen = getattr(getattr(window, "ctx", None), "screen", None)
        if ctx_screen:
            display_width = getattr(ctx_screen, "width", display_width)
            display_height = getattr(ctx_screen, "height", display_height)
        self._water_program["u_resolution"] = (
            float(max(display_width, 1)),
            float(max(display_height, 1)),
        )
        self._water_quad.render(self._water_program)
        ctx.disable(ctx.BLEND)

        ctx_vp_after = getattr(ctx, "viewport", None)

        if previous_camera:
            previous_camera.use()
        else:
            self.camera.use()

        if getattr(self, "shoreline_overlay", None):
            self.shoreline_overlay.draw()

    def _draw_selection_overlay(self, target=None):
        target = target or getattr(self, "last", None)
        rect = self._selection_rect(target)
        if rect is None:
            return

        center_x, center_y, width, height = rect
        color = self._selection_color(target)

        draw_rect_filled(
            XYWH(center_x, center_y, width, height),
            color,
        )

    def _selection_rect(self, target):
        if not target or getattr(target, "center_x", None) is None:
            return None
        tile_size = 50
        center_x = round(target.center_x / tile_size) * tile_size
        center_y = round(target.center_y / tile_size) * tile_size
        if abs(center_x) > 10000 or abs(center_y) > 10000:
            return None
        padding = self._selection_padding(target)
        width = tile_size + padding
        height = tile_size + padding
        return center_x, center_y, width, height

    def _selection_color(self, target):
        if isinstance(target, BaseBuilding):
            return (255, 221, 70, 205)
        if isinstance(target, BaseBoat):
            return (255, 228, 90, 190)
        return (255, 240, 140, 175)

    def _selection_padding(self, target):
        if isinstance(target, BaseBuilding):
            return 12
        if isinstance(target, BaseBoat):
            return 12
        return 12

    def _redraw_selection_stack(self, target, include_target=True):
        rect = self._selection_rect(target)
        if rect is None:
            return
        center_x, center_y, width, height = rect
        sprites = []
        if include_target and isinstance(target, arcade.Sprite):
            sprites.append(target)
        sprites.extend(self._sprites_in_rect(
            self.People, center_x, center_y, width, height))
        player = getattr(self, "player", None)
        if player and self._sprite_overlaps_rect(player, center_x, center_y, width, height):
            sprites.append(player)

        seen_ids: set[int] = set()
        for sprite in sprites:
            if not sprite:
                continue
            sprite_id = id(sprite)
            if sprite_id in seen_ids:
                continue
            seen_ids.add(sprite_id)
            sprite.draw()

    def _redraw_selected_health_bar(self, target) -> None:
        if not target:
            return
        health_bar = getattr(target, "health_bar", None)
        if not health_bar or not getattr(health_bar, "visible", True):
            return
        background = getattr(health_bar, "background_box", None)
        full = getattr(health_bar, "full_box", None)
        if background:
            background.draw()
        if full:
            full.draw()

    def _draw_selection_border(self, target):
        if not target or getattr(target, "center_x", None) is None:
            return
        rect = self._selection_rect(target)
        if rect is None:
            return
        center_x, center_y, width, height = rect
        color = self._selection_border_color(target)
        draw_rect_outline(
            XYWH(center_x, center_y, width, height),
            color,
            border_width=3,
        )

    def _draw_empty_building_overlay(self) -> None:
        """Dim buildings that have no occupants so they stand out."""
        if not getattr(self, "Buildings", None):
            return
        color = (200, 200, 200, 90)
        for building in self.Buildings:
            if not isinstance(building, BaseBuilding):
                continue
            if getattr(building, "max_length", 0) <= 0:
                continue
            if not getattr(building, "allows_people", True):
                continue
            occupants = getattr(building, "list_of_people", [])
            if occupants:
                continue
            draw_rect_filled(
                XYWH(
                    building.center_x,
                    building.center_y,
                    getattr(building, "width", 50),
                    getattr(building, "height", 50),
                ),
                color,
            )

    def _draw_selection_glow(self, target=None):
        target = target or getattr(self, "last", None)
        rect = self._selection_rect(target)
        if rect is None:
            return
        center_x, center_y, width, height = rect
        pad = 18
        glow_w = width + pad
        glow_h = height + pad
        texture = getattr(self, "_selection_glow_texture", None)
        if not texture:
            return
        try:
            texture.draw_sized(center_x, center_y, glow_w, glow_h, alpha=200)
        except Exception:
            scale_x = glow_w / max(texture.width, 1)
            scale_y = glow_h / max(texture.height, 1)
            sprite = arcade.Sprite(texture, scale=(scale_x + scale_y) / 2)
            sprite.center_x = center_x
            sprite.center_y = center_y
            sprite.alpha = 200
            sprite.draw()

    def _selection_border_color(self, target):
        if isinstance(target, BaseBuilding):
            return (255, 230, 100, 255)
        if isinstance(target, BaseBoat):
            return (255, 240, 120, 255)
        return (255, 250, 160, 255)

    def _sprites_in_rect(self, sprite_list, center_x, center_y, width, height):
        if not sprite_list:
            return []
        matches = []
        for sprite in sprite_list:
            if self._sprite_overlaps_rect(sprite, center_x, center_y, width, height):
                matches.append(sprite)
        return matches

    @staticmethod
    def _sprite_overlaps_rect(sprite, center_x, center_y, width, height):
        half_w = width / 2
        half_h = height / 2
        dx = abs(sprite.center_x - center_x)
        dy = abs(sprite.center_y - center_y)
        return dx < (half_w + sprite.width / 2) and dy < (half_h + sprite.height / 2)

    def on_key_press(self, key, modifiers):
        """Called whenever a key is pressed. """

        if key == arcade.key.H:
            modes = getattr(self, "hud_panel_modes", ("summary", "detail"))
            current_index = getattr(self, "active_hud_mode_index", 0)
            if not modes:
                return
            self.active_hud_mode_index = (current_index + 1) % len(modes)
            self.update_text(1)
            return

        center_x = 0
        center_y = 0
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
        Boats_at_point = arcade.get_sprites_at_point(
            self.player.position, self.Boats)
        if len(Boats_at_point) >= 1:
            self.player.boat = Boats_at_point[0]
        else:
            self.player.boat = None

        self.center_camera()

    def can_move(self, pos):
        x, y = self.camera.viewport_width/2-50, self.camera.viewport_height/2
        boundary = 900
        if boundary < pos[0] < self.x_line*50-boundary and boundary < pos[1] < self.y_line*50-boundary:

            pass
        else:
            info_sprite = UpdatingText(
                "Hit the Side", self.Alphabet_Textures, .5, width=300, center_x=x, center_y=y)
            self.PopUps.append(info_sprite)
            return False

        buildings = arcade.get_sprites_at_point(pos, self.Buildings)
        if len(buildings) != 0 and buildings[0].path:
            return True
        elif len(buildings) != 0 and not buildings[0].path:
            info_sprite = UpdatingText(
                "Hit building", self.Alphabet_Textures, .5, width=300, center_x=x, center_y=y)
            self.PopUps.append(info_sprite)
            return False
        elif len(arcade.get_sprites_at_point(pos, self.Stones)) != 0:
            info_sprite = UpdatingText(
                "Hit stone", self.Alphabet_Textures, .5, width=300, center_x=x, center_y=y)
            self.PopUps.append(info_sprite)
            return False
        elif len(arcade.get_sprites_at_point(pos, self.Boats)) == 0 and len(arcade.get_sprites_at_point(pos, self.Seas)) != 0:
            info_sprite = UpdatingText(
                "Hit water", self.Alphabet_Textures, .5, width=300, center_x=x, center_y=y)
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
        if self._ui_consumed_click(x, y):
            return
        if button == arcade.MOUSE_BUTTON_RIGHT:
            self.info_on_click(x, y)
            return
        if button != arcade.MOUSE_BUTTON_LEFT:
            return

        org_x, org_y = x, y
        world_x_raw, world_y_raw = self._screen_to_world(x, y)
        world_x, world_y, grid_x, grid_y = self._screen_to_world_and_grid(x, y)

        if self._handle_active_move(world_x, world_y, grid_x, grid_y, org_x, org_y):
            return

        if self._handle_direct_selection(world_x_raw, world_y_raw):
            return

        if self.object is None:
            self._show_info_popup(
                "Select an item to deploy first", org_x, org_y, width=200)
            return

        self._attempt_place_selected_object(
            world_x, world_y, grid_x, grid_y, org_x, org_y)

    def on_mouse_motion(self, x, y, dx, dy):
        self._update_preview_state(x, y)

    def _ui_consumed_click(self, x, y):
        if self._cursor_over_ui(x, y, include_selection=False):
            return True

        if self.ui_sprites_update(x, y):
            self.clear_uimanager()
            self.move = False
            self.last = None
            return True
        return False

    def _cursor_over_ui(self, x, y, include_selection: bool = True) -> bool:
        children = getattr(self.uimanager, "children", [])
        if children:
            for press in children[0]:
                child = getattr(press, "child", None)
                if child and getattr(child, "hovered", False):
                    return True

        if include_selection and len(arcade.get_sprites_at_point((x, y), self.ui_sprites)) > 0:
            return True
        return False

    def _screen_to_world(self, x, y) -> tuple[float, float]:
        camera = getattr(self, "camera", None)
        player = getattr(self, "player", None)
        if not camera or not player:
            return x, y
        world_x = x + self.player.center_x - (self.camera.viewport_width / 2)
        world_y = y + self.player.center_y - (self.camera.viewport_height / 2)
        return world_x, world_y

    def _screen_to_world_and_grid(self, x, y):
        world_x, world_y = self._screen_to_world(x, y)

        grid_x = round(world_x / 50)
        grid_y = round(world_y / 50)
        world_x = grid_x * 50
        world_y = grid_y * 50
        return world_x, world_y, grid_x, grid_y

    def _update_preview_state(self, screen_x: float, screen_y: float) -> None:
        self._mouse_position = (screen_x, screen_y)
        if not self.object:
            self._clear_preview_state()
            return

        if self._cursor_over_ui(screen_x, screen_y):
            self._preview_blocked_by_ui = True
            self._clear_preview_state()
            return
        self._preview_blocked_by_ui = False
        self._preview_too_far = False

        player = getattr(self, "player", None)
        camera = getattr(self, "camera", None)
        if not player or not camera:
            self._clear_preview_state()
            return

        world_x, world_y, grid_x, grid_y = self._screen_to_world_and_grid(
            screen_x, screen_y)
        self._preview_position = (world_x, world_y)
        now = time.time()
        need_refresh = (
            self._preview_grid != (grid_x, grid_y)
            or self._preview_object_name != self.object
            or (now - self._preview_last_check) > 0.15
        )
        if need_refresh:
            reach_reason = self._placement_precheck(
                world_x,
                world_y,
                grid_x,
                grid_y,
                getattr(self, "population", 0),
                override_population_check=True,
            )
            if reach_reason in ("Too far from Santa", "Santa can not pathfind here"):
                self._preview_too_far = True
                self._preview_position = None
                self._preview_valid = False
                return
            self._preview_valid = self._can_place_selection(
                world_x, world_y, grid_x, grid_y)
            self._preview_grid = (grid_x, grid_y)
            self._preview_object_name = self.object
            self._preview_last_check = now
        self._preview_player_anchor = (player.center_x, player.center_y)
        self._preview_viewport = (
            camera.viewport_width, camera.viewport_height)

    def _force_preview_refresh(self) -> None:
        if self._mouse_position and self.object:
            # Force the next update to recompute validity even if the cursor hasn't moved.
            self._preview_grid = None
            self._preview_last_check = 0.0
            self._update_preview_state(*self._mouse_position)

    def _clear_preview_state(self) -> None:
        self._preview_position = None
        self._preview_valid = False
        self._preview_player_anchor = None
        self._preview_viewport = None
        self._preview_grid = None
        self._preview_object_name = None
        self._preview_last_check = 0.0
        self._preview_blocked_by_ui = False
        self._preview_too_far = False

    def _refresh_preview_on_camera_change(self) -> None:
        if not self.object or not self._mouse_position:
            return
        player = getattr(self, "player", None)
        camera = getattr(self, "camera", None)
        if not player or not camera:
            return
        current_anchor = (player.center_x, player.center_y)
        current_viewport = (camera.viewport_width, camera.viewport_height)
        if (
            current_anchor != self._preview_player_anchor
            or current_viewport != self._preview_viewport
        ):
            self._update_preview_state(*self._mouse_position)

    def _can_place_selection(self, world_x, world_y, grid_x, grid_y) -> bool:
        if not self.object or self.object not in self.objects:
            return False
        if not (self.unlocked.get(self.object, False) and 0 < world_x < 5000 and 0 < world_y < 5000):
            return False

        current_population = getattr(self, "population", 0)
        lack_reason = self._placement_precheck(
            world_x, world_y, grid_x, grid_y, current_population)
        if lack_reason:
            return False
        if self._placement_occupancy_issue(world_x, world_y):
            return False
        tile_error = self._validate_tile_target(
            world_x, world_y, grid_x, grid_y)
        if tile_error:
            return False
        if self._missing_requirements():
            return False

        obj_cls = self.objects.get(self.object)
        if obj_cls and issubclass(obj_cls, Person) and current_population >= self.max_pop:
            return False
        return True

    def _placement_occupancy_issue(self, world_x: float, world_y: float) -> str | None:
        if not self.object:
            return None
        obj_cls = self.objects.get(self.object)
        if not obj_cls:
            return None

        point = (world_x, world_y)

        def _has_sprite(sprite_list: arcade.SpriteList) -> bool:
            return bool(arcade.get_sprites_at_point(point, sprite_list))

        blocking_boat = _has_sprite(self.Boats)
        blocking_building = _has_sprite(self.Buildings)

        if issubclass(obj_cls, BaseBoat):
            if blocking_boat:
                return "A boat is already here"
            if blocking_building:
                return "Blocked by a building"
            return None

        if issubclass(obj_cls, BaseBuilding):
            if blocking_building:
                return "There's already a building here"
            if blocking_boat:
                return "Move the boat first"
            return None

        # Default for units/other placeables: prevent spawning inside solid objects.
        if blocking_building or blocking_boat:
            return "Blocked by another object"
        return None

    def _draw_preview_texture(self, texture: arcade.Texture, center_x: float, center_y: float, width: float, height: float, alpha: int) -> None:
        draw_lrwh = getattr(arcade, "draw_lrwh_rectangle_textured", None)
        if draw_lrwh is None:
            draw_commands = getattr(arcade, "draw_commands", None)
            if draw_commands:
                draw_lrwh = getattr(draw_commands, "draw_lrwh_rectangle_textured", None)
        if draw_lrwh:
            draw_lrwh(
                center_x - width / 2,
                center_y - height / 2,
                width,
                height,
                texture,
                alpha=alpha,
            )
            return

        draw_scaled = getattr(arcade, "draw_scaled_texture_rectangle", None)
        if draw_scaled:
            draw_scaled(center_x, center_y, width, height, texture, alpha=alpha)
            return

        draw_basic = getattr(arcade, "draw_texture_rectangle", None)
        if draw_basic:
            draw_basic(center_x, center_y, width, height, texture, alpha=alpha)

    def _resolve_preview_texture(self) -> tuple[arcade.Texture, float] | None:
        if not self.object:
            return None
        spec = preview_textures.get(self.object)
        if not spec:
            return None
        key = (
            spec.get("path"),
            spec.get("x", 0),
            spec.get("y", 0),
            spec.get("width"),
            spec.get("height"),
        )
        if key[0] is None:
            return None
        texture = self._preview_texture_cache.get(key)
        if texture is None:
            load_kwargs = {}
            for param in ("x", "y", "width", "height"):
                if param in spec:
                    load_kwargs[param] = spec[param]
            try:
                texture = arcade.load_texture(spec["path"], **load_kwargs)
            except Exception:
                logging.exception("Failed to load preview texture for %s", self.object)
                return None
            self._preview_texture_cache[key] = texture
        return texture, float(spec.get("scale", 1.0))

    def _handle_active_move(self, world_x, world_y, grid_x, grid_y, screen_x, screen_y):
        if not self.move:
            return False

        source = self.last
        if source is None or source.health <= 0:
            self.move = False
            return True
        boundary = 900
        if not boundary < world_x < self.x_line * 50 - boundary or not boundary < world_y < self.y_line * 50 - boundary:
            if isinstance(source, BaseBoat):
                self._show_info_popup("Out of Bounds", screen_x, screen_y)
            self.move = False
            return True

        boat_at_target = arcade.get_sprites_at_point(
            (world_x, world_y), self.Boats)
        building_at_target = arcade.get_sprites_at_point(
            (world_x, world_y), self.Buildings)
        blocking_building = None
        if building_at_target:
            blocking_building = next(
                (b for b in building_at_target if not getattr(
                    b, "allows_people", True)),
                None,
            )
        if blocking_building:
            self.move = False
            self.show_move_feedback("Can't move there", world_x, world_y)
            return True
        original_value = None
        if boat_at_target:
            self.graph[grid_x][grid_y] = 0
        elif building_at_target:
            original_value = self.graph[grid_x][grid_y]
            self.graph[grid_x][grid_y] = 0

        source.path = _AStarSearch(
            self.graph,
            source.position,
            (world_x, world_y),
            allow_diagonal_movement=True,
            movelist=source.movelist,
            min_dist=1,
        )

        if boat_at_target:
            self.graph[grid_x][grid_y] = 2
        elif building_at_target and original_value is not None:
            self.graph[grid_x][grid_y] = original_value

        self.move = False
        if source.path:
            source.skill = None
            source.amount = 0
        else:
            self._show_info_popup("Can not move here", screen_x, screen_y)
        return True

    def _handle_direct_selection(self, world_x, world_y):
        people_at_point = arcade.get_sprites_at_point(
            (world_x, world_y), self.People)
        if people_at_point:
            self._clear_object_selection()
            people_at_point[0].clicked(self)
            return True
        ships_at_point = arcade.get_sprites_at_point(
            (world_x, world_y), self.Boats)
        if ships_at_point:
            self._clear_object_selection()
            ships_at_point[0].clicked(self)
            return True
        buildings_at_point = arcade.get_sprites_at_point(
            (world_x, world_y), self.Buildings)
        if buildings_at_point:
            self._clear_object_selection()
            buildings_at_point[0].clicked(self)
            return True
        return False

    def _attempt_place_selected_object(self, world_x, world_y, grid_x, grid_y, screen_x, screen_y):
        if not (self.unlocked.get(self.object) and 0 < world_x < 5000 and 0 < world_y < 5000):
            return

        occupancy_issue = self._placement_occupancy_issue(world_x, world_y)
        if occupancy_issue:
            self._show_info_popup(occupancy_issue, screen_x, screen_y)
            self._force_preview_refresh()
            return

        current_population = self.refresh_population()
        lack_reason = self._placement_precheck(
            world_x, world_y, grid_x, grid_y, current_population)
        if lack_reason:
            self.show_lack_popup(lack_reason, screen_x, screen_y, duration=1.5)
            self._force_preview_refresh()
            return

        tile_error = self._validate_tile_target(
            world_x, world_y, grid_x, grid_y)
        if tile_error:
            self._show_info_popup(tile_error, screen_x, screen_y)
            self._force_preview_refresh()
            return

        missing_resources = self._missing_requirements()
        if missing_resources:
            self._show_info_popup(
                f"missing: {missing_resources}", screen_x, screen_y)
            self._force_preview_refresh()
            return

        current_population = self.refresh_population()
        obj_cls = self.objects.get(self.object)
        if obj_cls and issubclass(obj_cls, Person) and current_population >= self.max_pop:
            self._add_lack("housing")
            self.show_lack_popup("Not enough Housing",
                                 screen_x, screen_y, duration=1.5)
            self._force_preview_refresh()
            return

        self._deduct_requirements()
        self._spawn_selected_object(world_x, world_y)
        self.updateStorage()
        self.update_text(1)
        self._force_preview_refresh()

    def _placement_precheck(self, world_x, world_y, grid_x, grid_y, current_population, override_population_check: bool = False):
        if arcade_math.get_distance(self.player.center_x, self.player.center_y, world_x, world_y) > 400:
            return "Too far from Santa"
        if not _AStarSearch(self.graph, self.player.position, (world_x, world_y), movelist=[0], min_dist=50):
            return "Santa can not pathfind here"
        if get_closest_sprite((world_x, world_y), self.People)[1] < 100:
            return None
        if self.SnowMap[world_x][world_y] == 0:
            return "Must be 3 blocks from a Building or adjacent to an elf"
        if arcade.get_sprites_at_point((world_x, world_y), self.Enemies):
            return "Can not place on an Enemy"
        if get_closest_sprite((world_x, world_y), self.Enemies)[1] < 150:
            return "Too close to an enemy"
        if not override_population_check and current_population >= self.max_pop and (
            self.object_placement == "People" or issubclass(
                self.objects[self.object], Person)
        ):
            return "Not enough Housing"
        return None

    def _validate_tile_target(self, world_x, world_y, grid_x, grid_y):
        target_tile = tiles[self.object]
        error_message = f"You can only place this on {target_tile.__name__}"
        if target_tile == Land and self.graph[grid_x][grid_y] != 0:
            return error_message
        if target_tile == Stone and self.graph[grid_x][grid_y] != 1:
            return error_message
        if target_tile == Sea and self.graph[grid_x][grid_y] != 2:
            return error_message
        if target_tile == BerryBush and not arcade.get_sprites_at_point((world_x, world_y), self.BerryBushes):
            return error_message
        if target_tile == Tree and not arcade.get_sprites_at_point((world_x, world_y), self.Trees):
            return error_message
        return None

    def _missing_requirements(self):
        self.requirements = requirements[self.object]
        missing_parts = []
        for _type, requirement in self.requirements.items():
            deficit = requirement - vars(self)[_type]
            if deficit > 0:
                missing_parts.append(f"{deficit} {_type}")
        return ", ".join(missing_parts) if missing_parts else None

    def _deduct_requirements(self):
        for _type, requirement in self.requirements.items():
            vars(self)[_type] -= requirement

    def _spawn_selected_object(self, world_x, world_y):
        obj_cls = self.objects[self.object]
        if issubclass(obj_cls, BaseBuilding):
            building = UNbuiltBuilding(
                self,
                world_x,
                world_y,
                max_len=max_length[self.object],
                time=times[self.object],
                building=self.object,
            )
            self.Buildings.append(building)
        elif issubclass(obj_cls, BaseBoat):
            created = obj_cls(self, world_x, world_y)
            self.Boats.append(created)
        elif issubclass(obj_cls, Person):
            created = obj_cls(self, world_x, world_y)
            created.path = [created.position]
            created.update_self(self)
            self.People.append(created)
            self.population += 1
        else:
            raise ValueError(f"{obj_cls} is not a person, building, or boat.")

    def _show_info_popup(self, message, screen_x, screen_y, width=300):
        info_sprite = UpdatingText(
            message, self.Alphabet_Textures, 0.5, width=width, center_x=screen_x, center_y=screen_y)
        self.PopUps.append(info_sprite)

    def info_on_click(self, x, y):
        x2 = x
        y2 = y

        x += self.player.center_x
        y += self.player.center_y
        x -= (self.camera.viewport_width / 2)
        y -= (self.camera.viewport_height / 2)

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
        if arcade_math.get_distance(x, y, self.player.center_x, self.player.center_y) <= 30:
            info += f", PLAYER"

        info_sprite = UpdatingText(
            info, self.Alphabet_Textures, 1, width=100, center_x=x2, center_y=y2)
        self.PopUps.append(info_sprite)

    def ui_sprites_update(self, x, y):

        ui = arcade.get_sprites_at_point((x, y), self.ui_sprites)
        if len(ui) > 0:
            self.object = ui[0].name
            self.requirements = requirements[ui[0].name]
            self.object_placement = ui[0].object_placement

            whitespaces = 15-len(ui[0].name)
            string = f"{ui[0].name} " + " "*whitespaces + "Costs:"
            for x, y in ui[0].requirements.items():
                string += f"{y} {x}, "
            if len(ui[0].requirements.items()) == 0:
                string = string.replace("Costs:", "")

            produced = {}
            obj_cls = self.objects.get(ui[0].name)
            if obj_cls and issubclass(obj_cls, BaseBuilding):
                produced = getattr(obj_cls, "produces", {}) or {}

            if produced:
                parts = []
                for resource, amount in produced.items():
                    parts.append(f"{amount} {resource}")
                if parts:
                    string += ". Creates: " + ", ".join(parts)

            string += f" Placed On {tiles[ui[0].name].__name__}"

            self.show_selection_panel(string)
            self._force_preview_refresh()

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
                dist_to_orig = arcade.get_distance_between_sprites(
                    enemy, enemy.focused_on)
            else:
                dist_to_orig = 0
            if dist_to_object < dist_to_orig:
                enemy.focuse_on = obj
                self.calculate_enemy_path(enemy)

    def spawn_enemy(self):
        enemies = ["Child", "Privateer", "Archer", "Arsonist", "Wizard"]
        enemy_pick = random.choice(enemies)
        enemy_class = {"Child": Child, "Privateer": Privateer, "Archer": Enemy_Slinger,
                       "Arsonist": Arsonist, "Wizard": Wizard}[enemy_pick]
        enemy = enemy_class(self, 0, 0, difficulty=self.hardness_multiplier)
        spawn_pos = self.EnemySpawnPos(enemy.movelist)
        if spawn_pos is None:
            enemy.destroy(self)
            return
        x, y = spawn_pos
        enemy.center_x = x
        enemy.center_y = y
        enemy.focused_on = None

        max_i = 100
        if len(self.OpenToEnemies) == 0:
            max_i = 1
        i = 0
        while self.graph[int(x/50)][int(y/50)] not in enemy.movelist:
            pos = self.EnemySpawnPos(enemy.movelist)
            if pos is None:
                enemy.destroy(self)
                return
            x, y = pos
            i += 1
            if i >= max_i:
                enemy.destroy(self)
                enemy_pick = "Enemy Archer"
                enemy_class = {"Basic Enemy": Child, "Privateer": Privateer, "Enemy Archer": Enemy_Slinger,
                               "Enemy Arsonist": Arsonist, "Enemy Wizard": Wizard}[enemy_pick]
                enemy = enemy_class(
                    self, 0, 0, difficulty=self.hardness_multiplier)
                enemy.focused_on = None
                i = 0
                spawn_pos = self.EnemySpawnPos(enemy.movelist)
                if spawn_pos is None:
                    return
                x, y = spawn_pos

        base_x, base_y = x, y
        jittered_x, jittered_y = self._apply_spawn_jitter(
            base_x, base_y, enemy.movelist)
        enemy.center_x = jittered_x
        enemy.center_y = jittered_y

        self.calculate_enemy_path(enemy)
        enemy.check = True
        self.Enemies.append(enemy)
        self._register_enemy_spawn_point(base_x, base_y)

        for person in self.People:
            person.check = True

    def calculate_enemy_path(self, enemy):
        enemy.check = False
        enemy.path = []
        building, distance = get_closest_sprite(enemy.position, self.Buildings)
        if building is None:
            distance = float("inf")

        person, distance2 = get_closest_sprite(enemy.position, self.People)
        if person is None:
            distance2 = float("inf")

        boat, distance3 = get_closest_sprite(enemy.position, self.Boats)
        if boat is None:
            distance3 = float("inf")

        bias1 = (distance+5)*enemy.building_bias
        bias2 = (distance2+5)*enemy.people_bias
        bias3 = (distance3+5)*enemy.boat_bias

        if distance > 1500:
            bias1 = float("inf")
        if distance2 > 1500:
            bias2 = float("inf")
        if distance3 > 1500:
            bias3 = float("inf")

        attempts = [
            ("building", building, bias1),
            ("person", person, bias2),
            ("boat", boat, bias3),
        ]
        path = None
        target = None
        while attempts:
            attempts.sort(key=lambda item: item[2])
            name, obj2, bias = attempts.pop(0)
            if bias == float("inf") or obj2 is None:
                continue
            path = _AStarSearch(
                self.graph,
                enemy.position,
                obj2.position,
                allow_diagonal_movement=True,
                movelist=enemy.movelist,
                min_dist=enemy.range,
            )
            if path:
                target = (name, obj2)
                break
        if not path or not target:
            enemy.check = True
            enemy.path = []
            return
        name, obj2 = target
        if arcade.get_distance_between_sprites(enemy, obj2) > enemy.range:
            enemy.check = True
        if name == "building":
            enemy.focused_on = building
        elif name == "person":
            enemy.focused_on = person
        elif name == "boat":
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

        obj2, distance = get_closest_sprite(obj.position, SpriteList)
        if obj2 == [] or distance > max_distance:
            return

        path = _AStarSearch(self.graph, obj.position, obj2.position,
                            allow_diagonal_movement=True, movelist=obj.movelist, min_dist=obj.range)
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
        if person is None:
            return
        if person not in self.People:
            try:
                self.People.append(person)
            except ValueError:
                pass
        person.in_building = False
        person.host_building = None
        person.health_bar.visible = True
        person.health_bar.position = person.position
        self.refresh_population()

    def print_attr(self, event):
        print(vars(event.source.obj))

    def center_camera(self):
        target_x = self.player.center_x
        target_y = self.player.center_y

        self.camera.position = (target_x, target_y)

    def on_update(self, delta_time):
        self.lacks = []
        if self.speed > 0:
            self.update_text(delta_time)
        [self.PopUps.remove(PopUp)
         for PopUp in self.PopUps if PopUp.update(delta_time)]
        self.real_delta_time = delta_time
        delta_time *= self.speed
        if self._returning_to_menu:
            return

        self.refresh_population()

        self.Christmas_timer += delta_time
        if (
            self.Christmas_timer >= CHRISTMAS_TRIGGER_TIME
            and not self.Completed_Christmas
        ):
            if self.Christmas_music and self.Christmas_music.player:
                self.Christmas_music.stop(self.Christmas_music.player)
            self.christmas_background.alpha = 0
            self.activate_Christmas()
            self.Completed_Christmas = True
            return

        self.player.on_update(delta_time)
        t = time.time()
        self.time_alive += delta_time

        self.timer += delta_time
        if self.timer > 1:
            self.timer -= 1
            self.science += .01/(sqrt(self.difficulty))*self.population
            self.science += .03/(sqrt(self.difficulty))

        if self.population <= 1:
            self.End("All your elves have fallen. The workshop stands empty.")
        self.updateStorage()
        [fire.update(self, delta_time) for fire in self.Fires]
        [person.update(self, delta_time) for person in self.People]
        [building.update(delta_time, self) for building in self.Buildings]
        [boat.update(self, delta_time) for boat in self.Boats]
        [enemy.update(self, delta_time) for enemy in self.Enemies]
        self._update_fog_layers(delta_time)
        base_dt = getattr(self, "real_delta_time", delta_time)
        self.snow_ambience.update(self, base_dt)

        if self.player.boat:
            self.player.position = self.player.boat.position
        self.center_camera()
        self._refresh_preview_on_camera_change()

        self.spawnEnemy += delta_time * getattr(self, "speed", 1)
        spawned = False
        while self.spawnEnemy >= 0:
            self.spawnEnemy -= 25
            self.spawn_enemy()
            self.difficulty *= 1.02
            spawned = True
        if spawned and not self.Enemies:
            for building in self.Buildings:
                if isinstance(building, SnowTower):
                    building.focused_on = None

        if self.population <= 1:
            self.End("All your elves have fallen. The workshop stands empty.")
        t2 = time.time()-t

        variables = vars(self)
        weight = 0
        for resource in ["wood", "stone", "metal"]:
            weight += variables[resource]*item_weight[resource]
        if weight/self.mcsStorage > .98:
            self._add_lack("Mcs Storage")

        if self.population >= self.max_pop:
            self._add_lack("housing")
        if not self.lacks:
            self.lack_text = None
            return
        if self.lack_popup and time.time() > self.lack_popup_timer:
            self.lack_popup = None
            self._active_lack_popup_type = None
        window = arcade.get_window()
        x, y = window.width/2, window.height-20
        string = ""
        for lack in self.lacks:
            if string:
                string += ", "
            else:
                string += "You lack: "
            string += lack
            if self.object and lack.lower().startswith(self.object.lower()[:3]) and self.lack_popup is None:
                self.show_lack_popup(f"{lack}", x, y)
        self.lack_text = CustomTextSprite(
            string, self.Alphabet_Textures, center_x=x-200, center_y=y, width=200, text_margin=14)

    def update_text(self, delta_time: float, *, force: bool = False):
        if not force:
            self.text_timer += delta_time
            if self.text_timer < 1:
                return
        self.text_timer = 0
        self.text_sprites.clear()
        y = self.camera.viewport_height-20

        modes = getattr(self, "hud_panel_modes", ("summary", "detail"))
        mode_index = getattr(self, "active_hud_mode_index", 0)
        if not modes:
            modes = ("summary",)
            self.hud_panel_modes = modes
            self.active_hud_mode_index = 0
        active_mode = modes[min(mode_index, len(modes) - 1)]
        target_sprite = None
        if active_mode == "summary":
            panel_width = 360
            target_sprite = getattr(self, "summary_under_sprite", None)
        else:
            panel_width = 440
            target_sprite = getattr(self, "detail_under_sprite", None)
        if target_sprite is not None:
            self.under_sprite = target_sprite

        self._active_hud_mode = active_mode
        offsets = getattr(self, "hud_background_offsets", {})
        offset = offsets.get(active_mode, {"x": 0, "y": 0})
        if isinstance(offset, tuple):
            offset = {"x": offset[0], "y": offset[1]}
        self._hud_background_draw_offset = {
            "x": float(offset.get("x", 0)),
            "y": float(offset.get("y", 0)),
        }

        panel_center_x = getattr(getattr(self, "under_sprite", None),
                                 "center_x", 180)
        if self.under_sprite:
            panel_center_x = self.under_sprite.center_x
            if active_mode == "detail":
                y = self.under_sprite.center_y + 255
            else:
                y = self.under_sprite.center_y + 190

        header_gap = 34 if active_mode == "detail" else 39
        line_gap = 26 if active_mode == "detail" else 31

        def add_header(text: str) -> None:
            nonlocal y
            self.text_sprites.append(CustomTextSprite(
                text, self.Alphabet_Textures, center_x=panel_center_x, center_y=y, width=panel_width, text_margin=12))
            y -= header_gap

        def add_line(text: str) -> None:
            nonlocal y
            self.text_sprites.append(CustomTextSprite(
                text, self.Alphabet_Textures, center_x=panel_center_x, center_y=y, width=panel_width, text_margin=12))
            y -= line_gap

        def add_gap(amount: int = 12) -> None:
            nonlocal y
            y -= amount

        wood = floor(self.wood)
        stone = floor(self.stone)
        presents = floor(self.presents)
        science = round(self.science, 1)
        storage_ratio = getattr(self, "mcsStoragePercent", 0.0)
        storage_percent = floor(storage_ratio * 100)
        presents_percent = 0
        if self.present_quota:
            presents_percent = floor((self.presents / self.present_quota) * 100)
        alive_time = floor(self.time_alive*100)/100
        spawntime = -self.spawnEnemy
        next_wave = floor(spawntime*100)/100
        remaining = max(0.0, CHRISTMAS_TRIGGER_TIME - self.Christmas_timer)
        christmas_time = round(remaining*100)/100
        housing = f"{self.population}/{self.max_pop}"
        housing_full = self.population >= self.max_pop

        if active_mode == "summary":
            add_header("SUMMARY (H)")
            add_line(f"W:{wood}  S:{stone}")
            add_line(f"P:{presents}  Sci:{science}")
            add_line(f"Storage:{storage_percent}%  Quota:{presents_percent}%")
            add_line(f"Wave:{next_wave:.1f}s  Xmas:{christmas_time:.1f}s")
            add_line(f"Housing: {housing}{' FULL' if housing_full else ''}")
            add_line("Press H for details")
            self._store_hud_anchor_center()
            return

        add_header("RESOURCES")
        add_line(f"Wood: {wood}")
        add_line(f"Stone: {stone}")
        add_line(f"Presents: {presents}")
        add_line(f"Science: {science}")

        add_gap()
        add_header("PRODUCTION")
        add_line(f"Storage: {storage_percent}% full")
        add_line(f"Gift Quota: {presents_percent}%")

        add_gap()
        add_header("TIMERS")
        add_line(f"Alive: {alive_time:.2f}s")
        add_line(f"Next Wave: {next_wave:.2f}s")
        add_line(f"Christmas: {christmas_time:.2f}s")

        add_gap()
        add_header("POPULATION")
        if housing_full:
            add_line(f"Housing: {housing} FULL")
        else:
            add_line(f"Housing: {housing}")
        add_line("Press H for summary")
        self._store_hud_anchor_center()

    def _store_hud_anchor_center(self) -> None:
        sprite = getattr(self, "under_sprite", None)
        if sprite is None:
            self._hud_anchor_center = None
            return
        self._hud_anchor_center = (
            float(sprite.center_x),
            float(sprite.center_y),
        )

    def updateStorage(self):
        variables = vars(self)
        weight = sum(
            variables[resource] * item_weight[resource]
            for resource in ["wood", "stone", "metal"]
        )
        if weight > self.mcsStorage:
            self._add_lack("Mcs Storage")
            if self._storage_frame_valid:
                for resource in ["wood", "stone", "metal"]:
                    variables[resource] = prev_frame[resource]
            else:
                self._cap_resources_to_storage(variables)
                self._storage_frame_valid = True
        else:
            self._storage_frame_valid = True

        weight = sum(
            variables[resource] * item_weight[resource]
            for resource in ["wood", "stone", "metal"]
        )
        self.mcsStoragePercent = weight / self.mcsStorage

        variables = vars(self)
        for resource in item_weight.keys():
            prev_frame[resource] = variables[resource]

    def apply_repeatable_upgrades(self):
        try:
            with open("resources/game.json", "r") as read_file:
                data = json.load(read_file)
        except:
            data = {}
        stored_levels = data.get("repeatable_upgrades", {})
        self.meta_upgrade_levels = {
            name: int(level) for name, level in stored_levels.items()}
        for definition in load_repeatable_upgrade_defs():
            name = definition.get("name", "")
            level = int(self.meta_upgrade_levels.get(name, 0))
            if level <= 0:
                continue
            for attr, amount in definition.get("effect", {}).items():
                self._apply_repeatable_upgrade_effect(attr, amount, level)
    def _apply_repeatable_upgrade_effect(self, attr: str, amount: float, level: int):
        if attr.endswith("_multiplier") or attr == "history_gain_multiplier":
            current = getattr(self, attr, 1)
            factor = (1 + amount/100.0) ** level
            setattr(self, attr, current * factor)
        elif attr.endswith("_storage"):
            current = getattr(self, attr, 0)
            current += amount * level
            setattr(self, attr, current)
        else:
            current = getattr(self, attr, 0)
            current += amount * level
            setattr(self, attr, current)

    def _cap_resources_to_storage(self, variables):
        """Scale resources down to fit inside the current storage capacity."""
        weight = sum(
            variables[resource] * item_weight[resource]
            for resource in ["wood", "stone", "metal"]
        )
        if weight <= 0:
            for resource in ["wood", "stone", "metal"]:
                variables[resource] = 0
            return

        scale = self.mcsStorage / weight
        if scale >= 1:
            return

        for resource in ["wood", "stone", "metal"]:
            variables[resource] *= scale

    def _run_cellular_phases(self, grid, phases):
        """Apply multiple CA passes with varying rules to shape the grid."""
        if not grid or not grid[0]:
            return grid
        width = len(grid[0])
        height = len(grid)
        template = create_grid(width, height)
        for steps, death_limit, birth_limit in phases:
            steps = max(0, int(steps))
            for _ in range(steps):
                grid, template = do_simulation_step(
                    grid,
                    template,
                    death_limit=death_limit,
                    birth_limit=birth_limit,
                )
        return grid

    def _reset_world_generation_lists(self) -> None:
        """Prepare sprite lists for a fresh world generation attempt."""
        self.Lands = arcade.SpriteList(use_spatial_hash=True)
        self.Stones = arcade.SpriteList(use_spatial_hash=True)
        self.Seas = arcade.SpriteList(use_spatial_hash=True)
        self.Trees = arcade.SpriteList(use_spatial_hash=True)
        self.BerryBushes = arcade.SpriteList(use_spatial_hash=True)
        self.Buildings = arcade.SpriteList(use_spatial_hash=True)
        self.People = arcade.SpriteList()
        self.health_bars = arcade.SpriteList()
        self.Fires = arcade.SpriteList(use_spatial_hash=True)
        self.overParticles = arcade.SpriteList()
        self.underParticals = arcade.SpriteList()
        self.Enemies = arcade.SpriteList()
        self.EnemyBoats = arcade.SpriteList()
        self.shoreline_overlay = ShapeElementList()
        self.graph = None

    def generateWorld(self, x_line, y_line, world_gen):
        max_attempts = getattr(self, "max_worldgen_attempts", 3)
        for attempt in range(1, max_attempts + 1):
            self._reset_world_generation_lists()
            if self._generate_world_attempt(x_line, y_line, world_gen):
                if attempt > 1:
                    logging.info(
                        "World generation succeeded after %s attempts", attempt)
                return
            logging.warning(
                "World generation attempt %s/%s failed to place the player. Retrying...",
                attempt,
                max_attempts,
            )
        raise RuntimeError(
            "Unable to generate a playable world after multiple attempts.")

    def _generate_world_attempt(self, x_line, y_line, world_gen):

        self.x_line = x_line
        self.y_line = y_line
        grid = create_grid(x_line, y_line)
        initialize_grid(grid, chance=0.5)
        grid = self._run_cellular_phases(
            grid,
            [
                (6, 4, 5),
                (4, 3, 4),
                (3, 3, 3),
            ],
        )

        grid2 = create_grid(x_line, y_line)
        initialize_grid(grid2, chance=0.52)
        grid2 = self._run_cellular_phases(
            grid2,
            [
                (5, 4, 5),
                (4, 3, 4),
            ],
        )

        mountain_mask = create_grid(x_line, y_line)
        initialize_grid(mountain_mask, chance=0.7)
        mountain_mask = self._run_cellular_phases(
            mountain_mask,
            [
                (4, 3, 4),
                (3, 3, 3),
            ],
        )

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

        self.graph = LivingMap(x_line, y_line, x_line * y_line, tilesize=50)
        self.graphlength = x_line + 1
        self.Lands = arcade.SpriteList(use_spatial_hash=True)
        self.Stones = arcade.SpriteList(use_spatial_hash=True)
        self.Seas = arcade.SpriteList(use_spatial_hash=True)

        transition_stone_factor = min(0.25, max(0.03, stone_factor * 0.15))

        graph_data = self.graph.graph
        for row in range(y_line):
            for column in range(x_line):
                world_x = row * 50
                world_y = column * 50
                mountain_seed = mountain_mask[row][column] == 1
                is_core = (
                    grid[row][column] == 1
                    and grid2[row][column] == 1
                    and mountain_seed
                )
                if is_core:
                    graph_data[row][column] = 1
                elif grid[row][column] == 0:
                    graph_data[row][column] = 2
                else:
                    if mountain_seed and random.random() < transition_stone_factor:
                        graph_data[row][column] = 1
                    else:
                        graph_data[row][column] = 0

        width = len(graph_data)
        height = len(graph_data[0]) if width else 0
        if width > 2 and height > 2:
            stones_to_land: list[tuple[int, int]] = []
            land_to_stone: list[tuple[int, int]] = []
            for gx in range(1, width - 1):
                    for gy in range(1, height - 1):
                        value = graph_data[gx][gy]
                        stone_neighbors = 0
                        for dx in (-1, 0, 1):
                            for dy in (-1, 0, 1):
                                if dx == 0 and dy == 0:
                                    continue
                                nx = gx + dx
                                ny = gy + dy
                                if nx < 0 or ny < 0 or nx >= width or ny >= height:
                                    continue
                                if graph_data[nx][ny] == 1:
                                    stone_neighbors += 1
                        if value == 1 and stone_neighbors <= 3:
                            stones_to_land.append((gx, gy))
                        elif value == 0 and stone_neighbors >= 8:
                            land_to_stone.append((gx, gy))

            def _replace_tile(gx: int, gy: int, value: int) -> None:
                graph_data[gx][gy] = value

            for gx, gy in stones_to_land:
                _replace_tile(gx, gy, 0)

            for gx, gy in land_to_stone:
                _replace_tile(gx, gy, 1)

            # Remove tiny isolated stone clusters entirely.
            min_cluster_size = 4
            visited: set[tuple[int, int]] = set()
            for gx in range(width):
                for gy in range(height):
                    if graph_data[gx][gy] != 1 or (gx, gy) in visited:
                        continue
                    stack = [(gx, gy)]
                    component: list[tuple[int, int]] = []
                    while stack:
                        cx, cy = stack.pop()
                        if (cx, cy) in visited:
                            continue
                        visited.add((cx, cy))
                        component.append((cx, cy))
                        for dx in (-1, 0, 1):
                            for dy in (-1, 0, 1):
                                if dx == 0 and dy == 0:
                                    continue
                                nx = cx + dx
                                ny = cy + dy
                                if nx < 0 or ny < 0 or nx >= width or ny >= height:
                                    continue
                                if graph_data[nx][ny] == 1:
                                    stack.append((nx, ny))
                    if len(component) < min_cluster_size:
                        for cx, cy in component:
                            _replace_tile(cx, cy, 0)

            # Soft-round remaining mountains by iteratively filling concave corners.
            for _ in range(3):
                rounded_to_land: list[tuple[int, int]] = []
                rounded_to_stone: list[tuple[int, int]] = []
                for gx in range(1, width - 1):
                    for gy in range(1, height - 1):
                        stone_neighbors = 0
                        for dx in (-1, 0, 1):
                            for dy in (-1, 0, 1):
                                if dx == 0 and dy == 0:
                                    continue
                                nx = gx + dx
                                ny = gy + dy
                                if graph_data[nx][ny] == 1:
                                    stone_neighbors += 1
                        if graph_data[gx][gy] == 1 and stone_neighbors <= 2:
                            rounded_to_land.append((gx, gy))
                        elif graph_data[gx][gy] == 0 and stone_neighbors >= 6:
                            rounded_to_stone.append((gx, gy))
                if not rounded_to_land and not rounded_to_stone:
                    break
                for cx, cy in rounded_to_land:
                    _replace_tile(cx, cy, 0)
                for cx, cy in rounded_to_stone:
                    _replace_tile(cx, cy, 1)

            # Round coastlines by trimming sharp land spikes while preserving coves,
            # but gently fill tiny slivers of water almost entirely surrounded by land.
            for _ in range(4):
                land_to_sea: list[tuple[int, int]] = []
                sea_to_land: list[tuple[int, int]] = []
                for gx in range(1, width - 1):
                    for gy in range(1, height - 1):
                        land_neighbors = 0
                        sea_neighbors = 0
                        for dx in (-1, 0, 1):
                            for dy in (-1, 0, 1):
                                if dx == 0 and dy == 0:
                                    continue
                                nx = gx + dx
                                ny = gy + dy
                                val = graph_data[nx][ny]
                                if val == 0:
                                    land_neighbors += 1
                                elif val == 2:
                                    sea_neighbors += 1
                        if graph_data[gx][gy] == 0:
                            if sea_neighbors >= 4 and land_neighbors <= 2:
                                land_to_sea.append((gx, gy))
                        elif graph_data[gx][gy] == 2:
                            if land_neighbors >= 7 and sea_neighbors == 0:
                                sea_to_land.append((gx, gy))
                if not land_to_sea and not sea_to_land:
                    break
                for cx, cy in land_to_sea:
                    _replace_tile(cx, cy, 2)
                for cx, cy in sea_to_land:
                    _replace_tile(cx, cy, 0)

            # Expand continents outward so land masses don't collapse into thin strips.
            for _ in range(3):
                sea_to_land: list[tuple[int, int]] = []
                for gx in range(1, width - 1):
                    for gy in range(1, height - 1):
                        if graph_data[gx][gy] != 2:
                            continue
                        land_neighbors = 0
                        sea_neighbors = 0
                        for dx in (-1, 0, 1):
                            for dy in (-1, 0, 1):
                                if dx == 0 and dy == 0:
                                    continue
                                nx = gx + dx
                                ny = gy + dy
                                val = graph_data[nx][ny]
                                if val == 0 or val == 1:
                                    land_neighbors += 1
                                elif val == 2:
                                    sea_neighbors += 1
                        if land_neighbors >= 5 and sea_neighbors <= 2:
                            sea_to_land.append((gx, gy))
                if not sea_to_land:
                    break
                for cx, cy in sea_to_land:
                    _replace_tile(cx, cy, 0)

        for gx in range(x_line):
            for gy in range(y_line):
                world_x = gx * 50
                world_y = gy * 50
                tile_value = graph_data[gx][gy]
                if tile_value == 0:
                    self.addLand(world_x, world_y)
                elif tile_value == 1:
                    self.addStone(world_x, world_y)
                elif tile_value == 2:
                    self.addSea(world_x, world_y)

        for land in self.Lands:
            if not 0 < land.center_x < 4950 or not 0 < land.center_y < 4950:
                continue

            x = land.center_x/50
            y = land.center_y/50

            sand = False
            for i in ((0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                if self.graph[x+i[0]][y+i[1]] == 2:
                    sand = True
                    break
            if sand:
                land.texture = arcade.load_texture(
                    "resources/Sprites/terrain/Sand.png")
                land.typ = "Sand"
            else:
                random_float = random.random()
                if random_float > berry_bush_factor:
                    self.addBerryBush(land.center_x, land.center_y)
                elif random_float > tree_factor:
                    self.addTree(land.center_x, land.center_y)
            land.prev_texture = land.texture

        if not self.place_player(x_line, y_line):
            return False
        self.test_enemies(x_line, y_line)
        return True

    def place_player(self, x_line, y_line):
        """Choose a spawn spot with enough open land; regenerate map if it fails."""
        self.player = Player(center_x=0, center_y=0)
        center_x = x_line / 2
        center_y = y_line / 2
        bias_ratio = getattr(self, "spawn_bias_radius_ratio", 0.35)
        bias_radius = min(x_line, y_line) * bias_ratio
        max_attempts = getattr(self, "max_spawn_search_attempts", 8000)
        attempts = 0
        required_area = getattr(self, "min_spawn_area_tiles", 80)
        relaxed_area = getattr(
            self, "min_spawn_area_tiles_relaxed", required_area + 40)
        require_stone = getattr(self, "spawn_requires_nearby_stone", True)

        def _has_nearby_stone(tile_x: int, tile_y: int, radius: int = 8) -> bool:
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    nx = tile_x + dx
                    ny = tile_y + dy
                    if nx < 0 or ny < 0 or nx >= x_line or ny >= y_line:
                        continue
                    if self.graph[nx][ny] == 1:
                        return True
            return False

        def _tile_is_open(tile_x: int, tile_y: int) -> bool:
            if self.graph[tile_x][tile_y] != 0:
                return False
            open_neighbors = 0
            for point in ((0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                nx = tile_x + point[0]
                ny = tile_y + point[1]
                if 0 <= nx < x_line and 0 <= ny < y_line and self.graph[nx][ny] == 0:
                    open_neighbors += 1
            return open_neighbors >= 4

        def _is_viable(tile_x: int, tile_y: int) -> bool:
            if not _tile_is_open(tile_x, tile_y):
                return False
            has_stone = _has_nearby_stone(tile_x, tile_y) if require_stone else True
            if not has_stone:
                return False
            world_x = tile_x * 50
            world_y = tile_y * 50
            try:
                contiguous = SearchTilesAround(
                    self.graph, (world_x, world_y), allow_diagonal_movement=False, movelist=[0])
            except Exception:
                contiguous = 0
            if contiguous >= required_area:
                return True
            try:
                diagonal = SearchTilesAround(
                    self.graph, (world_x, world_y), allow_diagonal_movement=True, movelist=[0])
            except Exception:
                diagonal = 0
            return diagonal >= relaxed_area

        spawn_tile: tuple[int, int] | None = None
        while attempts < max_attempts and spawn_tile is None:
            attempts += 1
            if attempts % 4 != 0:
                angle = random.random() * 2 * math.pi
                radius = bias_radius * math.sqrt(random.random())
                tile_x = int(center_x + math.cos(angle) * radius)
                tile_y = int(center_y + math.sin(angle) * radius)
            else:
                tile_x = random.randrange(24, x_line - 24)
                tile_y = random.randrange(24, y_line - 24)
            tile_x = max(24, min(x_line - 24, tile_x))
            tile_y = max(24, min(y_line - 24, tile_y))
            if _is_viable(tile_x, tile_y):
                spawn_tile = (tile_x, tile_y)
                break

        fallback_attempts = 0
        fallback_limit = max_attempts * 2
        while spawn_tile is None and fallback_attempts < fallback_limit:
            fallback_attempts += 1
            tile_x = random.randrange(24, x_line - 24)
            tile_y = random.randrange(24, y_line - 24)
            if _is_viable(tile_x, tile_y):
                spawn_tile = (tile_x, tile_y)
                break
            if fallback_attempts % 2000 == 0 and relaxed_area > 60:
                # Gradually relax the requirement so we eventually succeed.
                relaxed_area = max(60, relaxed_area - 10)
                required_area = max(50, required_area - 10)

        if spawn_tile is None:
            logging.warning("Unable to find a suitable spawn tile.")
            return False

        tile_x, tile_y = spawn_tile
        x = tile_x * 50
        y = tile_y * 50
        self.player = Player(center_x=x, center_y=y)

        num = 0
        for point in ((0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)):
            x2 = tile_x+point[0]
            y2 = tile_y+point[1]
            if self.graph[x2][y2] != 0:
                continue
            person = Person(self, x2*50, y2*50)
            self.People.append(person)
            num += 1
            if num == 2:
                break
        return True

    def test_enemies(self, x_line, y_line):
        t = time.time()
        for row in range(y_line):
            for column in range(x_line):
                if random.random() <= 1 or self.graph[row][column] != 0 or self.graph[row+1][column+1] != 0:
                    continue
                enemy = Enemy_Slinger(self, row*50+50, column*50-50)
                self.Enemies.append(enemy)

                building = Hospital(row*50, column*50)
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
        self._rebuild_open_enemy_tiles()

    def _rebuild_open_enemy_tiles(self) -> None:
        self.OpenToEnemies = []
        enemy_map = getattr(self, "EnemyMap", None)
        if not enemy_map:
            return
        for x, column in enemy_map.items():
            for y, count in column.items():
                if count > 0 and self.graph[int(x/50)][int(y/50)] == 0:
                    self.OpenToEnemies.append((x, y))

    def _find_valid_spawn_near(self, anchor_x, anchor_y, allowed_tiles: list[int]) -> tuple[int, int] | None:
        if not allowed_tiles:
            return None
        base_x = round(anchor_x / 50) * 50
        base_y = round(anchor_y / 50) * 50
        max_radius = 600
        for radius in range(0, max_radius + 50, 50):
            ring_candidates: list[tuple[int, int]] = []
            for dx in range(-radius, radius + 1, 50):
                for dy in range(-radius, radius + 1, 50):
                    if abs(dx) != radius and abs(dy) != radius and radius != 0:
                        continue
                    x = base_x + dx
                    y = base_y + dy
                    if not (0 <= x < len(self.graph.graph) * 50 and 0 <= y < len(self.graph.graph[0]) * 50):
                        continue
                    tile = self.graph[int(x / 50)][int(y / 50)]
                    if tile in allowed_tiles:
                        ring_candidates.append((x, y))
            if ring_candidates:
                return self._choose_low_usage_spawn(ring_candidates)
        return None

    def EnemySpawnPos(self, allowed_tiles: list[int]):
        if self.OpenToEnemies:
            valid_tiles: list[tuple[int, int]] = []
            invalid_tiles: list[tuple[int, int]] = []
            for x, y in self.OpenToEnemies:
                if self.graph[int(x/50)][int(y/50)] in allowed_tiles:
                    valid_tiles.append((x, y))
                else:
                    invalid_tiles.append((x, y))
            if invalid_tiles:
                invalid_set = set(invalid_tiles)
                self.OpenToEnemies = [
                    tile for tile in self.OpenToEnemies if tile not in invalid_set]
            if valid_tiles:
                return self._choose_low_usage_spawn(valid_tiles)

        anchors: list[tuple[float, float]] = []
        if len(self.People) > 0:
            person = self.People[random.randrange(0, len(self.People))]
            anchors.append((person.center_x, person.center_y))

        building_occupants: list[arcade.Sprite] = []
        for building in getattr(self, "Buildings", []):
            building_occupants.extend(getattr(building, "list_of_people", []))
        if building_occupants:
            person = random.choice(building_occupants)
            anchors.append((person.center_x, person.center_y))

        boat_passengers: list[arcade.Sprite] = []
        for boat in getattr(self, "Boats", []):
            boat_passengers.extend(getattr(boat, "list", []))
        if boat_passengers:
            passenger = random.choice(boat_passengers)
            anchors.append((passenger.center_x, passenger.center_y))

        if self.Boats:
            boat = random.choice(self.Boats)
            if getattr(boat, "list", []):
                anchors.append((boat.center_x, boat.center_y))

        random.shuffle(anchors)
        for anchor_x, anchor_y in anchors:
            candidate = self._find_valid_spawn_near(
                anchor_x, anchor_y, allowed_tiles)
            if candidate:
                return candidate

        for _ in range(200):
            rand_x = random.randrange(20, self.x_line - 20) * 50
            rand_y = random.randrange(20, self.y_line - 20) * 50
            if self.graph[int(rand_x / 50)][int(rand_y / 50)] in allowed_tiles:
                return rand_x, rand_y

        if self.population == 0:
            self.End()
            return None
        return None

    def _choose_low_usage_spawn(self, candidates: list[tuple[int, int]]) -> tuple[int, int] | None:
        if not candidates:
            return None

        safe_candidates = [
            pos for pos in candidates if not self._is_near_protected_structures(pos)]
        pool = safe_candidates or candidates

        weights = []
        for x, y in pool:
            tile = (round(x / 50) * 50, round(y / 50) * 50)
            count = self._enemy_spawn_counts.get(tile, 0)
            weights.append(1 / (count + 1))
        total = sum(weights)
        pick = random.random() * total
        for candidate, weight in zip(pool, weights):
            pick -= weight
            if pick <= 0:
                return candidate
        return pool[-1]

    def _is_near_protected_structures(self, pos: tuple[int, int]) -> bool:
        threshold = getattr(self, "min_enemy_spawn_distance", 0) or 0
        if threshold <= 0:
            return False
        x, y = pos
        for building in getattr(self, "Buildings", []):
            if arcade_math.get_distance(building.center_x, building.center_y, x, y) < threshold:
                return True
        player = getattr(self, "player", None)
        if player and arcade_math.get_distance(player.center_x, player.center_y, x, y) < threshold:
            return True
        return False

    def _register_enemy_spawn_point(self, x: float, y: float) -> None:
        tile = (round(x / 50) * 50, round(y / 50) * 50)
        self._enemy_spawn_counts[tile] += 1
        self._enemy_spawn_history.append(tile)
        while len(self._enemy_spawn_history) > self._max_spawn_history:
            old = self._enemy_spawn_history.popleft()
            self._enemy_spawn_counts[old] -= 1
            if self._enemy_spawn_counts[old] <= 0:
                self._enemy_spawn_counts.pop(old, None)

    def _apply_spawn_jitter(self, x: float, y: float, allowed_tiles: list[int], max_offset: int = 18) -> tuple[float, float]:
        tile_size = getattr(self.graph, "tilesize", 50)
        max_x = len(self.graph.graph) * tile_size if self.graph.graph else 0
        max_y = len(self.graph.graph[0]) * tile_size if self.graph.graph else 0
        for _ in range(8):
            offset_x = x + random.randint(-max_offset, max_offset)
            offset_y = y + random.randint(-max_offset, max_offset)
            if not (0 <= offset_x < max_x and 0 <= offset_y < max_y):
                continue
            tile_x = int(offset_x / tile_size)
            tile_y = int(offset_y / tile_size)
            if self.graph[tile_x][tile_y] not in allowed_tiles:
                continue
            if self._spawn_position_is_free(offset_x, offset_y):
                return offset_x, offset_y
        return x, y

    def _spawn_position_is_free(self, x: float, y: float, min_distance: float = 18.0) -> bool:
        for enemy in self.Enemies:
            if arcade_math.get_distance(x, y, enemy.center_x, enemy.center_y) < min_distance:
                return False
        return True

    def BuildingChangeEnemySpawner(self, x, y, placing=1, min_dist=100, max_dist=300):
        x = round(x/50)*50
        y = round(y/50)*50

        graph_lookup = self.graph
        for x2 in range(-max_dist, max_dist, 50):
            if not 0 <= x2+x < 5000:
                continue
            for y2 in range(-max_dist, max_dist, 50):
                if not 0 <= y2+y < 5000:
                    continue

                x1 = x2+x
                y1 = y2+y
                tile_type = graph_lookup[int(x1/50)][int(y1/50)]
                if abs(x2) <= min_dist and abs(y2) <= min_dist:
                    self.EnemyMap[x1][y1] -= placing
                    self.SnowMap[x1][y1] += placing
                else:
                    self.EnemyMap[x1][y1] += placing

                if tile_type != 0:
                    continue
                if self.EnemyMap[x1][y1] > 0:
                    if (x1, y1) not in self.OpenToEnemies:
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
                    land[0].texture = arcade.load_texture(
                        "resources/Sprites/terrain/Snow.png")

    def save(self, event):
        if getattr(self, "is_tutorial", False):
            toast = UpdatingText(
                "Saving is disabled in the tutorial.",
                self.Alphabet_Textures,
                2.0,
                center_x=self.camera.viewport_width / 2,
                center_y=self.camera.viewport_height - 80,
                Background_Texture="resources/gui/Small Text Background.png",
                width=320,
            )
            self.texts.append(toast)
            return
        variables = {}
        self.ui_sprites.clear()

        skip_keys = {
            "window", "camera", "key", "secondary_wrappers", "menu_buttons",
            "selectables", "ui_sprites", "player", "main_button", "menus_button",
            "selectables_button", "under_sprite", "extra_buttons", "text_sprites",
            "audios", "underParticals", "overParticles", "health_bars",
            "Buildings", "People", "Boats", "Enemies", "Fires",
            "Lands", "Stones", "Seas", "Trees", "BerryBushes",
        }
        for key, value in vars(self).items():
            if key in skip_keys:
                continue
            if isinstance(value, (int, float, dict, list)):
                variables[key] = value

        player_state = {
            "center_x": self.player.center_x,
            "center_y": self.player.center_y,
            "health": getattr(self.player, "health", 0),
            "max_health": getattr(self.player, "max_health", 0),
        }
        variables["player_state"] = player_state

        person_states, person_ids = self._serialize_people()
        variables["people_state"] = person_states
        variables["EnemyMap"] = self.EnemyMap
        graph_rows: list[list[int]] = []
        for column in getattr(self.graph, "graph", []):
            graph_rows.append([int(cell) for cell in column])
        variables["graph"] = graph_rows
        variables["terrain_state"] = self._serialize_terrain()
        boats_state, boat_lookup = self._serialize_boats(person_ids)
        variables["boats_state"] = boats_state
        buildings_state, building_lookup = self._serialize_buildings(
            person_ids)
        variables["buildings_state"] = buildings_state
        variables["fires_state"] = self._serialize_fires(
            building_lookup, boat_lookup)
        variables["enemies_state"] = self._serialize_enemies()

        for enemy in variables.get("Enemies", []):
            self._strip_sprite_render_data(enemy)
        variables["x_line"] = getattr(self, "x_line", 0)
        variables["y_line"] = getattr(self, "y_line", 0)

        if not self.file_num:
            return

        file_path = get_save_path(self.file_num)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open('wb') as outfile:
            try:
                pickle.dump(variables, outfile)
            except Exception:
                for key, val in variables.items():
                    try:
                        pickle.dumps(val)
                    except Exception as err:
                        print(f"Pickle failure: {key} -> {type(val)}: {err}")
                raise

    def _strip_sprite_render_data(self, sprite: arcade.Sprite) -> None:
        """Remove Arcade-specific rendering data so the sprite can be pickled."""
        texture = getattr(sprite, "_texture", None)
        texture_path = getattr(sprite, "texture_path", None)
        if texture and not texture_path:
            texture_path = getattr(texture, "file_path", None)
            if texture_path:
                sprite.texture_path = str(texture_path)
        if texture_path:
            sprite._saved_texture_path = texture_path

        for attr in ("_texture", "_hit_box", "_vertex_list", "_geometry", "_sprite_list", "_sprite", "_buffer", "_ctx"):
            if hasattr(sprite, attr):
                try:
                    setattr(sprite, attr, None)
                except Exception:
                    pass

    def _serialize_buildings(self, person_ids: dict) -> tuple[list[dict], dict[arcade.Sprite, int]]:
        obj_to_id: dict[arcade.Sprite, int] = {}
        states: list[dict] = []
        for idx, building in enumerate(getattr(self, "Buildings", [])):
            building._state_id = idx
            states.append(building.serialize_state(person_ids))
            obj_to_id[building] = idx
        return states, obj_to_id

    def _load_buildings_from_state(self, states: list[dict], person_map: dict) -> dict:
        id_map: dict[int, arcade.Sprite] = {}
        self.Buildings = arcade.SpriteList(use_spatial_hash=True)
        open_tiles: list[tuple[int, int]] = []
        for state in states:
            cls_name = state.get("type")
            if not cls_name:
                continue
            cls = BUILDING_CLASS_MAP.get(
                cls_name) or self.objects.get(cls_name)
            if not cls:
                continue
            x = state.get("x", 0)
            y = state.get("y", 0)
            try:
                if cls_name == "UNbuiltBuilding":
                    building = cls(
                        self,
                        x,
                        y,
                        max_len=state.get("max_length", 0),
                        time=state.get("time", 0),
                        building=state.get("build_target", ""),
                    )
                else:
                    building = cls(self, x, y)
            except TypeError:
                building = cls.__new__(cls)
                arcade.Sprite.__init__(building, None, center_x=x, center_y=y)
                building.game = self
            if hasattr(building, "apply_state"):
                building.apply_state(self, state)
            self.Buildings.append(building)
            if isinstance(building, UNbuiltBuilding):
                building._spawn_registered = False
            else:
                building._spawn_registered = getattr(
                    building, "affects_enemy_spawns", True)
            bid = state.get("id")
            if bid is not None:
                id_map[bid] = building
        self._assign_people_to_buildings(person_map)
        return id_map

    def _assign_people_to_buildings(self, person_map: dict) -> None:
        for building in getattr(self, "Buildings", []):
            occupant_ids = getattr(building, "_pending_occupants", [])
            for pid in occupant_ids:
                person = person_map.get(pid)
                if person:
                    try:
                        building.add(person)
                    except Exception:
                        continue
            building._pending_occupants = []

    def _serialize_people(self) -> tuple[list[dict], dict]:
        people_states: list[dict] = []
        id_map: dict[arcade.Sprite, int] = {}
        seen: set[arcade.Sprite] = set()
        ordered_people: list[arcade.Sprite] = []
        for person in getattr(self, "People", []):
            if person not in seen:
                seen.add(person)
                ordered_people.append(person)
        for building in getattr(self, "Buildings", []):
            for occupant in getattr(building, "list_of_people", []):
                if occupant not in seen:
                    seen.add(occupant)
                    ordered_people.append(occupant)
        for boat in getattr(self, "Boats", []):
            for passenger in getattr(boat, "list", []):
                if passenger not in seen:
                    seen.add(passenger)
                    ordered_people.append(passenger)

        for idx, person in enumerate(ordered_people):
            state = person.serialize_state()
            state["id"] = idx
            people_states.append(state)
            id_map[person] = idx
        return people_states, id_map

    def _load_people_from_state(self, states: list[dict] | None) -> dict:
        id_map: dict[int, arcade.Sprite] = {}
        self.People = arcade.SpriteList()
        if not states:
            return id_map
        for state in states:
            cls_name = state.get("type", "Person")
            cls = self.objects.get(cls_name)
            if cls is None:
                cls = globals().get(cls_name)
            if cls is None:
                cls = Person
            x = state.get("x", 0)
            y = state.get("y", 0)
            try:
                person = cls(self, x, y)
            except TypeError:
                person = cls.__new__(cls)
                Person.__init__(person, self, x, y)
            if hasattr(person, "apply_state"):
                person.apply_state(self, state)
            self.People.append(person)
            pid = state.get("id")
            if pid is not None:
                id_map[pid] = person
        return id_map

    def _serialize_boats(self, person_ids: dict) -> tuple[list[dict], dict[arcade.Sprite, int]]:
        obj_to_id: dict[arcade.Sprite, int] = {}
        states: list[dict] = []
        for idx, boat in enumerate(getattr(self, "Boats", [])):
            boat._state_id = idx
            states.append(boat.serialize_state(person_ids))
            obj_to_id[boat] = idx
        return states, obj_to_id

    def _load_boats_from_state(self, states: list[dict] | None, person_map: dict) -> None:
        id_map: dict[int, arcade.Sprite] = {}
        if not states:
            self.Boats = arcade.SpriteList()
            return id_map
        self.Boats = arcade.SpriteList()
        for state in states:
            cls_name = state.get("type")
            if not cls_name:
                continue
            cls = self.objects.get(cls_name)
            if not cls:
                continue
            x = state.get("x", 0)
            y = state.get("y", 0)
            try:
                boat = cls(self, x, y)
            except TypeError:
                boat = cls.__new__(cls)
                arcade.Sprite.__init__(boat, None, center_x=x, center_y=y)
                boat.game = self
            if hasattr(boat, "apply_state"):
                boat.apply_state(self, state)
            self.Boats.append(boat)
            bid = state.get("id")
            if bid is not None:
                id_map[bid] = boat
        self._assign_people_to_boats(person_map)
        return id_map

    def _assign_people_to_boats(self, person_map: dict) -> None:
        for boat in getattr(self, "Boats", []):
            passenger_ids = getattr(boat, "_pending_passengers", [])
            for pid in passenger_ids:
                person = person_map.get(pid)
                if person:
                    try:
                        boat.add(person)
                    except Exception:
                        continue
            boat._pending_passengers = []

    def _serialize_fires(self, building_lookup: dict, boat_lookup: dict) -> list[dict]:
        states: list[dict] = []
        for fire in getattr(self, "Fires", []):
            state = fire.save_state(building_lookup, boat_lookup)
            if state.get("owner_type") is None:
                continue
            states.append(state)
        return states

    def _load_fires_from_state(self, states: list[dict] | None, building_id_map: dict, boat_id_map: dict) -> None:
        self.Fires = arcade.SpriteList(use_spatial_hash=True)
        if not states:
            return
        for state in states:
            fire = Fire.from_state(self, state, building_id_map, boat_id_map)
            if not fire:
                continue
            self.Fires.append(fire)

    def _serialize_enemies(self) -> list[dict]:
        return [enemy.serialize_state() for enemy in getattr(self, "Enemies", [])]

    def _load_enemies_from_state(self, states: list[dict] | None) -> None:
        self.Enemies = arcade.SpriteList()
        if not states:
            return
        for state in states:
            cls_name = state.get("type")
            if not cls_name:
                continue
            cls = ENEMY_CLASS_MAP.get(cls_name)
            if not cls:
                continue
            x = state.get("x", 0)
            y = state.get("y", 0)
            spawn = state.get("spawn", {})
            enemy = None
            try:
                enemy = cls(self, x, y, **spawn)
            except TypeError:
                try:
                    enemy = cls(x, y, **spawn)
                except TypeError:
                    pass
            if enemy is None:
                enemy = cls.__new__(cls)
                arcade.Sprite.__init__(enemy, None, center_x=x, center_y=y)
                enemy.game = self
            if hasattr(enemy, "apply_state"):
                enemy.apply_state(self, state)
            self.Enemies.append(enemy)

    def _serialize_terrain(self) -> dict:
        terrain = {
            "land": [tile.serialize_state() for tile in getattr(self, "Lands", [])],
            "stone": [tile.serialize_state() for tile in getattr(self, "Stones", [])],
            "sea": [tile.serialize_state() for tile in getattr(self, "Seas", [])],
            "trees": [tile.serialize_state() for tile in getattr(self, "Trees", [])],
            "berries": [tile.serialize_state() for tile in getattr(self, "BerryBushes", [])],
        }
        return terrain

    def _load_terrain_from_state(self, state: dict) -> None:
        self.Lands = arcade.SpriteList(use_spatial_hash=True)
        self.Stones = arcade.SpriteList(use_spatial_hash=True)
        self.Seas = arcade.SpriteList(use_spatial_hash=True)
        self.Trees = arcade.SpriteList(use_spatial_hash=True)
        self.BerryBushes = arcade.SpriteList(use_spatial_hash=True)

        tile_factories = {
            "Land": Land,
            "Sand": Sand,
            "Stone": Stone,
            "Sea": Sea,
            "Tree": Tree,
            "BerryBush": BerryBush,
        }

        def _build_tiles(entries, target_list):
            for data in entries:
                tile_type = data.get("type")
                factory = tile_factories.get(tile_type)
                if not factory:
                    continue
                tile = factory(self, data.get("x", 0), data.get("y", 0))
                if hasattr(tile, "apply_state"):
                    tile.apply_state(data)
                target_list.append(tile)

        _build_tiles(state.get("land", []), self.Lands)
        _build_tiles(state.get("stone", []), self.Stones)
        _build_tiles(state.get("sea", []), self.Seas)
        _build_tiles(state.get("trees", []), self.Trees)
        _build_tiles(state.get("berries", []), self.BerryBushes)

    def load(self, file_num):
        if not file_num:
            raise FileNotFoundError("Save slot empty")
        file_path = get_save_path(file_num)
        if not file_path.exists() or file_path.stat().st_size == 0:
            raise FileNotFoundError("Save slot empty")
        with file_path.open('rb') as infile:
            file = pickle.load(infile)

        x_line = file.get("x_line", getattr(self, "x_line", 0))
        y_line = file.get("y_line", getattr(self, "y_line", 0))

        graph_rows = file.get("graph")
        if graph_rows and x_line and y_line:
            graph = LivingMap(x_line, y_line, x_line * y_line, tilesize=50)
            for x, column in enumerate(graph_rows):
                for y, cell in enumerate(column):
                    if x < len(graph.graph) and y < len(graph.graph[x]):
                        graph.graph[x][y] = cell
            self.graph = graph
            self.x_line = x_line
            self.y_line = y_line

        person_map = self._load_people_from_state(file.get("people_state"))
        boat_states = file.get("boats_state")
        if boat_states:
            boat_id_map = self._load_boats_from_state(boat_states, person_map)
        else:
            boat_id_map = {}
        building_states = file.get("buildings_state")
        if building_states:
            building_id_map = self._load_buildings_from_state(
                building_states, person_map)
        else:
            building_id_map = {}
        terrain_state = file.get("terrain_state")
        if terrain_state:
            self._load_terrain_from_state(terrain_state)
        fires_state = file.get("fires_state")
        if fires_state:
            self._load_fires_from_state(
                fires_state, building_id_map, boat_id_map)
        enemies_state = file.get("enemies_state")
        if enemies_state:
            self._load_enemies_from_state(enemies_state)

        sprite_list_skip = {"Lands", "Stones", "Seas", "Trees", "BerryBushes"}

        for key, val in file.items():
            if isinstance(val, list):
                if key == "rites_list" or key == "science_list":
                    vars(self)[key] = val
                    continue
                elif key == "graph":
                    # Processed earlier so buildings had a valid map during load
                    continue
                elif key in {"buildings_state", "people_state", "boats_state", "terrain_state",
                             "enemies_state", *sprite_list_skip}:
                    continue
                for sprite in val:
                    vars(self)[key].append(sprite)
            elif isinstance(val, arcade.SpriteList):
                if key in sprite_list_skip:
                    continue
                for sprite in val:
                    vars(self)[key].append(sprite)
            else:
                if key in {"x_line", "y_line"}:
                    vars(self)[key] = val
                    continue
                vars(self)[key] = val

        if "EnemyMap" in file:
            self.EnemyMap = file["EnemyMap"]
            self._rebuild_open_enemy_tiles()
        player_state = file.get("player_state") or {}
        self.player = Player(center_x=player_state.get(
            "center_x", 0), center_y=player_state.get("center_y", 0))
        if "health" in player_state:
            self.player.health = player_state["health"]
        if "max_health" in player_state:
            self.player.max_health = player_state["max_health"]

class MyTutorial(MyGame):
    def __init__(self, menu, file_num=0, world_gen="Normal", difficulty=1):
        super().__init__(menu, file_num, world_gen, difficulty)
        self.sprites = arcade.SpriteList()
        self.step = 1

        self.spawnEnemy = -630
        self.presents += 500
        self.wood += 200
        self.stone += 150
        self.metal += 50
        self.unlocked["Enemy Archer"] = True
        self.unlocked["Enemy Arsonist"] = True
        self.unlocked["Enemy Wizard"] = True

        button = CustomUIFlatButton(self.Alphabet_Textures, click_sound=self.click_sound, width=50, height=50, scale=.1, x=50, y=50, offset_x=25, offset_y=25,
                                    Texture="resources/gui/Question Mark.png", Pressed_Texture="resources/gui/Question Mark.png", Hovered_Texture="resources/gui/Question Mark.png")
        button.on_click = self.on_question_click
        button.open = False
        wrapper = UIAnchorWidget(anchor_x="center", anchor_y="center",
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
            if not isinstance(button, UIAnchorWidget):
                continue
            indicator = arcade.Sprite(
                "resources/gui/exclamation point.png", scale=.25)
            self.indicators.append(indicator)

            indicator.button = button
            button.indicator = indicator
        self.indicator_update(None)

        self.floating_question_marks = arcade.SpriteList()
        person = self.People[0]
        sprite = arcade.Sprite("resources/gui/Question Mark.png", scale=.1,
                               center_x=person.center_x+30, center_y=person.center_y+30)
        sprite.tracking = person
        self.floating_question_marks.append(sprite)
        sprite.text_sprites = []
        sprite.text = "Move Elfs on resources to collect it.  Move on buildings and boats to build and work them.  For certian resources you need a building to collect them"

    def indicator_update(self, event):
        if event:
            event.source.wrapper.indicator.remove_from_sprite_lists()
        for indicator in self.indicators:
            button = indicator.button
            window = arcade.get_window()
            if button.anchor_x == "center":
                x = window.width/2
            if button.anchor_y == "center":
                y = window.height/2

            if button.anchor_x == "right":
                x = window.width
            if button.anchor_y == "top":
                y = window.height

            if button.anchor_x == "left":
                x = 0
            if button.anchor_y == "bottom":
                y = 0

            if button.anchor_x == "left" and button.anchor_y == "top":
                x, y = x+50, y-50
            if button.anchor_x == "left" and button.anchor_y == "bottom":
                x, y = x+50, y+50

            indicator.center_x = x+button.align_x
            indicator.center_y = y+button.align_y

    def on_question_click(self, event):
        window = arcade.get_window()
        if not self.question:
            text = CustomTextSprite("Right click to anything to get info.     Press arrows or W/A/S/D to move Santa. Use Santa to move around the map.", self.Alphabet_Textures, width=-200, center_x=window.width/2+event.source.wrapper.align_x -
                                    150, center_y=window.height/2+event.source.wrapper.align_y+100, Background_offset_x=260, Background_offset_y=-35, Background_scale=1.5, Background_Texture="resources/gui/Small Text Background.png")
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
            if self.Christmas_music.player:
                self.Christmas_music.stop(self.Christmas_music.player)
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
        x -= (self.camera.viewport_width / 2)
        y -= (self.camera.viewport_height / 2)
        marks = sprites_in_range(30, (x, y), self.floating_question_marks)
        if marks:
            if marks[0].text_sprites:
                marks[0].text_sprites = []
                return
            marks[0].text_sprites.clear()

            words = marks[0].text.split("  ")
            y = 150
            for word in words:
                if y == 150:
                    marks[0].text_sprites.append(CustomTextSprite(word, self.Alphabet_Textures, width=-marks[0].center_x+700, center_x=marks[0].center_x-100, center_y=marks[0].center_y+y,
                                                 Background_Texture="resources/gui/Small Text Background.png", Background_offset_x=marks[0].center_x/2-100, Background_offset_y=-50, Background_scale=2))
                else:
                    marks[0].text_sprites.append(CustomTextSprite(
                        word, self.Alphabet_Textures, width=-marks[0].center_x+650, center_x=marks[0].center_x-100, center_y=marks[0].center_y+y))
                y -= 30
            return
        super().on_mouse_press(x2, y2, button, modifiers)

    def on_draw(self):
        super().on_draw()

        self.camera.use()
        self.sprites.draw()
        for mark in self.floating_question_marks:
            mark.draw()
            if mark.text_sprites:
                for sprite in mark.text_sprites:
                    sprite.draw()

        self.not_scrolling_camera.use()
        self.sprites.draw()
        self.indicators.draw()

        if self.question:
            self.question.draw()

    def spawn_enemy(self):
        enemy_pick = random.choice(
            ["Basic Enemy", "Privateer", "Enemy Archer", "Enemy Arsonist", "Enemy Wizard"])
        while not self.unlocked[enemy_pick]:
            enemy_pick = random.choice(
                ["Basic Enemy", "Privateer", "Enemy Swordsman", "Enemy Archer", "Enemy Arsonist", "Enemy Wizard"])
        enemy_class = {"Basic Enemy": Child, "Privateer": Privateer, "Enemy Archer": Enemy_Slinger,
                       "Enemy Arsonist": Arsonist, "Enemy Wizard": Wizard}[enemy_pick]
        enemy = enemy_class(self, 0, 0, difficulty=self.hardness_multiplier)
        spawn_pos = self.EnemySpawnPos(enemy.movelist)
        if spawn_pos is None:
            enemy.destroy(self)
            return
        x, y = spawn_pos
        enemy.center_x = x
        enemy.center_y = y
        enemy.focused_on = None

        max_i = 100
        if len(self.OpenToEnemies) == 0:
            max_i = 1
        i = 0
        while self.graph[int(x/50)][int(y/50)] not in enemy.movelist:
            pos = self.EnemySpawnPos(enemy.movelist)
            if pos is None:
                enemy.destroy(self)
                return
            x, y = pos
            i += 1
            if i >= max_i:
                enemy.destroy(self)
                enemy_pick = random.choice(
                    ["Basic Enemy", "Privateer", "Enemy Archer", "Enemy Arsonist", "Enemy Wizard"])
                while not self.unlocked[enemy_pick]:
                    enemy_pick = random.choice(
                        ["Basic Enemy", "Privateer", "Enemy Archer", "Enemy Arsonist", "Enemy Wizard"])
                enemy_class = {"Basic Enemy": Child, "Privateer": Privateer, "Enemy Archer": Enemy_Slinger,
                               "Enemy Arsonist": Arsonist, "Enemy Wizard": Wizard}[enemy_pick]
                enemy = enemy_class(
                    self, 0, 0, difficulty=self.hardness_multiplier)
                enemy.focused_on = None
                i = 0
                spawn_pos = self.EnemySpawnPos(enemy.movelist)
                if spawn_pos is None:
                    return
                x, y = spawn_pos

        base_x, base_y = x, y
        jittered_x, jittered_y = self._apply_spawn_jitter(
            base_x, base_y, enemy.movelist)
        enemy.center_x = jittered_x
        enemy.center_y = jittered_y

        self.calculate_enemy_path(enemy)
        enemy.check = True
        self.Enemies.append(enemy)
        self._register_enemy_spawn_point(base_x, base_y)

        for person in self.People:
            person.check = True

        sprite = arcade.Sprite("resources/gui/Question Mark.png", scale=.1,
                               center_x=enemy.center_x+30, center_y=enemy.center_y+30)
        self.floating_question_marks.append(sprite)
        sprite.tracking = enemy
        sprite.text_sprites = []
        enemy_name = {"Basic Enemy": "Child, close ranged enemy. Prefers people",
                      "Privateer": "Privateer, shoots an arrow. Prefers boats",
                      "Enemy Archer": "Enemy_Slinger, shoots an arrow. Prefers people",
                      "Enemy Arsonist": "Arsonist, starts fires. Stop the firest with Fire Stations. Prefers buildings",
                      "Enemy Wizard": "Wizard, has 2 types of attacks. Does splash damage. Prefers people"}[enemy_pick]
        sprite.text = f"{enemy_name}"


class GameOverView(arcade.View):

    def __init__(self, menu, message: str):
        super().__init__()
        self.menu = menu
        self.message = message
        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        button = UIFlatButton(text="Return to Menu", width=220)
        button.on_click = self.on_return
        wrapper = UIAnchorWidget(
            anchor_x="center",
            anchor_y="center",
            child=button,
            align_x=0,
            align_y=-80,
        )
        self.uimanager.add(wrapper)

        exit_button = UIFlatButton(text="Exit", width=220)
        exit_button.on_click = self.on_exit
        wrapper = UIAnchorWidget(
            anchor_x="center",
            anchor_y="center",
            child=exit_button,
            align_x=0,
            align_y=-150,
        )
        self.uimanager.add(wrapper)

    def on_draw(self):
        self.clear(arcade.color.DARK_SLATE_GRAY)
        width, height = self.window.width, self.window.height
        arcade.draw_text(
            "Game Over",
            width / 2,
            height / 2 + 80,
            arcade.color.WHITE,
            36,
            anchor_x="center",
        )
        arcade.draw_text(
            self.message,
            width / 2,
            height / 2 + 20,
            arcade.color.ANTIQUE_WHITE,
            18,
            anchor_x="center",
            width=width * 0.8,
            align="center",
        )

    def on_return(self, _event):
        self.uimanager.disable()
        if hasattr(self.menu, "uimanager"):
            self.menu.uimanager.enable()
        if hasattr(self.menu, "update_audio"):
            self.menu.update_audio()
        show_view_resized(self.window, self.menu)

    def on_exit(self, _event):
        self.uimanager.disable()
        show_view_resized(self.window, startMenu())


class EndMenu(arcade.View):

    def __init__(self, history, game, menu, reason: str | None = None, extra_lines: list[str] | None = None):
        self.menu = menu
        self.game_view = game
        self.reason = reason
        self.extra_lines = extra_lines or []

        super().__init__()
        self.Christmas_timer = 30
        self.spawnEnemy = 0
        """ This is run once when we switch to this view """
        self._background_color = arcade.color.BEIGE

        reset_window_viewport(self.window)

        self.click_sound = game.click_sound
        self.Background_music = game.Background_music
        self.Christmas_music = game.Christmas_music

        window = arcade.get_window()
        self.window = window

        base_width, base_height = 1440, 900
        initial_scale = 3.6 * \
            min(self.window.width / base_width,
                self.window.height / base_height)
        self.background = arcade.Sprite(
            "resources/gui/Large Bulletin.png",
            center_x=self.window.width / 2,
            center_y=self.window.height / 2,
            scale=initial_scale
        )
        self.christmas_background = arcade.Sprite(
            "resources/gui/ChristmasOverlay.png",
            center_x=self.window.width / 2,
            center_y=self.window.height / 2,
            scale=max(self.window.width / 5001, self.window.height / 3334)
        )
        self.christmas_overlay = None

        self.texts = []

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        textures = load_texture_grid(
            "resources/gui/Wooden Font.png", 14, 24, 12, 71, margin=1)
        self.Alphabet_Textures = {" ": None}
        string = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyz.:,%/-+_'"
        for i in range(len(string)):
            self.Alphabet_Textures[string[i]] = textures[i]

        start_button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Return", width=140, height=50)
        start_button.on_click = self.on_return
        wrapper = UIAnchorWidget(
            anchor_x="center_x", anchor_y="center_y", child=start_button, align_x=0, align_y=-100)
        self.uimanager.add(wrapper)

        self.texts.append(CustomTextSprite(f"You Died. ", self.Alphabet_Textures, center_x=self.window.width /
                          2, center_y=self.window.height+200, width=1000, scale=4, text_margin=50))
        if self.reason:
            self.texts.append(CustomTextSprite(self.reason, self.Alphabet_Textures,
                              center_x=self.window.width/2, center_y=540, width=1200, text_margin=18, scale=1.5))
        if self.extra_lines:
            extra_y = 500
            for line in self.extra_lines:
                self.texts.append(
                    CustomTextSprite(
                        line,
                        self.Alphabet_Textures,
                        center_x=self.window.width/2,
                        center_y=extra_y,
                        width=1200,
                        text_margin=18,
                        scale=1.2,
                    )
                )
                extra_y -= 35
        if history == 0:
            string = "You gained no history"
        else:
            string = f"You gained: {round(history*10)/10} History"
        self.texts.append(CustomTextSprite(f"You were alive for {round(game.time_alive*100)/100} seconds.  {string}",
                          self.Alphabet_Textures, center_x=300, center_y=50, width=5000, text_margin=16))

        main_button = CustomUIFlatButton(self.game_view.Alphabet_Textures, click_sound=self.game_view.click_sound, width=50, height=50, scale=1,
                                         Texture="resources/gui/Question Mark.png", Pressed_Texture="resources/gui/Question Mark.png", Hovered_Texture="resources/gui/Question Mark.png")
        main_button.on_click = self.on_question_click
        main_button.open = False
        wrapper = UIAnchorWidget(anchor_x="center", anchor_y="center",
                                 child=main_button, align_x=0, align_y=-200)
        main_button.wrapper = wrapper
        self.uimanager.add(wrapper)
        self.question = None

        window = arcade.get_window()
        self.on_resize(window.width, window.height)

    def on_resize(self, width: int, height: int):
        scale1, scale2 = width/218, height/140
        scale = min(scale1, scale2)
        scale = max(scale, 0.1)
        self.background.center_x = width/2-7*scale/3.6
        self.background.center_y = height/2-75*scale/3.6
        self.background.scale = scale

        self.christmas_background.position = width/2, height/2
        self.christmas_background.scale = .25*max(width/1240, height/900)

        resize_ui_manager(self, width, height)

        y = height/2-35
        for text in self.texts:
            for sprite in text.Sprite_List:
                sprite.center_y = y
            y -= 30

        return super().on_resize(width, height)

    def on_question_click(self, event):
        window = arcade.get_window()
        if not self.question:
            text = CustomTextSprite(
                "You lose once you have less than 2 elfs alive. You get history based on how long you lived. See Progress Tree to use it. You start getting history after 5 minutes, so you can not spam create worlds",
                self.game_view.Alphabet_Textures, width=3000,
                center_x=window.width/2+event.source.wrapper.align_x-150, center_y=window.height/2+event.source.wrapper.align_y-80,
                Background_Texture="resources/gui/Small Text Background.png")
            self.texts.append(text)
            self.question = text
        else:
            self.texts.remove(self.question)
            self.question = None

    def on_return(self, event):
        self.uimanager.disable()
        self.menu.uimanager.enable()
        window = arcade.get_window()
        width = getattr(window, "width", 0) or getattr(window, "size", (0, 0))[0]
        height = getattr(window, "height", 0) or getattr(window, "size", (0, 0))[1]
        show_view_resized(self.window, self.menu)
        if hasattr(self.menu, "on_resize") and width and height:
            self.menu.on_resize(width, height)

    def on_exit(self, _event):
        self.uimanager.disable()
        show_view_resized(self.window, startMenu())

    def on_show_view(self):
        """Called when this view becomes active."""
        super().on_show_view()
        arcade.set_background_color(arcade.color.BEIGE)
        reset_window_viewport(self.window)

    def on_draw(self):
        """ Draw this view """
        self.clear()
        self.background.draw()
        self.christmas_background.draw()

        self.uimanager.draw()
        for text in self.texts:
            text.draw()


class ChristmasMenu(arcade.View):

    def __init__(self, game):
        super().__init__()
        self.game_view = game
        self.window = arcade.get_window()

        self.background = arcade.Sprite(
            "resources/gui/Christmas_menu_Background.png",
            center_x=self.window.width / 2,
            center_y=self.window.height / 2,
            scale=10,
        )

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        self.texts: list[CustomTextSprite] = []
        self._text_offsets: list[tuple[float, float]] = []

        quota = self.game_view.present_quota
        presents_made = floor(self.game_view.presents)
        diff = presents_made - quota
        next_quota = ceil(quota * 1.08)

        summary = f"We crafted {presents_made} presents. Quota was {quota}."
        details = "We met the children's expectations exactly."
        if diff > 0:
            details = f"We exceeded the quota by {diff} present(s)!"

        future = f"Next year's quota will be {next_quota}."

        entries = [summary, details, future,
                   "Press Return to resume festivities."]
        base_y = self.window.height / 2 + 80
        for idx, text in enumerate(entries):
            sprite = CustomTextSprite(
                text,
                self.game_view.Alphabet_Textures,
                center_x=self.window.width / 2,
                center_y=base_y - idx * 40,
                width=800,
                text_margin=18,
            )
            self.texts.append(sprite)
            self._text_offsets.append(
                (0, base_y - idx * 40 - self.window.height / 2))

        return_button = CustomUIFlatButton(
            self.game_view.Alphabet_Textures,
            click_sound=self.game_view.click_sound,
            text="Return",
            width=160,
            height=54,
        )
        return_button.on_click = self.on_return
        wrapper = UIAnchorWidget(
            anchor_x="center",
            anchor_y="center",
            child=return_button,
            align_x=0,
            align_y=-120,
        )
        self.uimanager.add(wrapper)

        self.game_view.Completed_Christmas = True

    def on_return(self, _event):
        self.uimanager.disable()
        self.game_view.resume_after_christmas()

    def on_draw(self):
        self.clear()
        self.background.draw()
        for text in self.texts:
            text.draw()
        self.uimanager.draw()

    def on_update(self, delta_time: float):
        for text in self.texts:
            text.update(delta_time)

    def on_resize(self, width: int, height: int):
        self.background.center_x = width / 2
        self.background.center_y = height / 2
        for sprite, (_, offset_y) in zip(self.texts, self._text_offsets):
            sprite.set_position(width / 2, height / 2 + offset_y)
        resize_ui_manager(self, width, height)
        return super().on_resize(width, height)


def state_list_from_save(saved_state, names, defaults, coerce=bool):
    values = []
    is_dict = isinstance(saved_state, dict)
    is_list = isinstance(saved_state, list)
    for idx, name in enumerate(names):
        default = defaults[idx]
        if is_dict:
            values.append(coerce(saved_state.get(name, default)))
        elif is_list and idx < len(saved_state):
            values.append(coerce(saved_state[idx]))
        else:
            values.append(default)
    return values


def state_dict_from_list(names, values, coerce=bool):
    return {name: coerce(values[idx]) for idx, name in enumerate(names)}


def load_repeatable_upgrade_defs():
    with open("resources/GameBase.json", "r") as read_file:
        menu_config = json.load(read_file)
    return menu_config.get("RepeatableUpgrades", [])


class startMenu(arcade.View):

    def __init__(self):

        super().__init__()
        """ This is run once when we switch to this view """
        self._background_color = arcade.color.BEIGE
        arcade.set_background_color(self._background_color)

        reset_window_viewport(self.window)

        self.audios = []
        # Ensure the game starts with audible output; players can still dial it down in the Volume menu.
        self.audio_type_vols = {"Overall": 0.7, "UI": 1, "Background": 1}

        self.click_sound = Sound("resources/audio/click.wav")
        self.click_sound.start_vol = 5
        self.click_sound.type = "UI"
        self.click_sound.player = None
        apply_audio_volume(self.click_sound, self.audio_type_vols)
        self.audios.append(self.click_sound)

        self.Background_music = Sound(
            "resources/audio/magical-christmas-paul-yudin-main-version-19227-01-40.wav")
        self.Background_music.start_vol = .1
        self.Background_music.type = "Background"
        apply_audio_volume(self.Background_music, self.audio_type_vols)
        self.audios.append(self.Background_music)
        self.Background_music.play(loop=True)

        self.Christmas_music = Sound(
            "resources/audio/deck-the-halls-kevin-macleod-main-version-04-25-9985.wav")
        self.Christmas_music.start_vol = .1
        self.Christmas_music.type = "Background"
        self.Christmas_music.player = None
        apply_audio_volume(self.Christmas_music, self.audio_type_vols)
        self.audios.append(self.Christmas_music)
        self.update_audio()

        self.Background_music.true_volume = self.Background_music.volume
        self.Christmas_music.true_volume = self.Christmas_music.volume

        self.background = arcade.Sprite(
            "resources/gui/Large Bulletin.png", scale=12.0, center_x=370, center_y=180)
        self.christmas_background = arcade.Sprite(
            "resources/gui/ChristmasOverlay.png", scale=.25, center_x=370, center_y=180)

        self.texts = []

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        textures = load_texture_grid(
            "resources/gui/Wooden Font.png", 14, 24, 12, 71, margin=1)
        self.Alphabet_Textures = {" ": None}
        string = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyz.:,%/-+_'"
        for i in range(len(string)):
            self.Alphabet_Textures[string[i]] = textures[i]

        title_width = max(self.window.width - 200, 400)
        self.title_text = CustomTextSprite(
            "SantaFest Destiny",
            self.Alphabet_Textures,
            scale=3.0,
            width=title_width,
            center_x=self.window.width / 2,
            center_y=self.window.height - 140,
            text_margin=18,
        )
        self.texts.append(self.title_text)

        self.world_buttons: list[CustomUIFlatButton] = []
        self.world_clear_buttons: list[CustomUIFlatButton] = []
        for idx, align_y in enumerate((150, 70, -10), start=1):
            play_button = CustomUIFlatButton(
                self.Alphabet_Textures, click_sound=self.click_sound, text="", width=220, height=54)
            play_button.on_click = self.Start
            play_button.world_num = idx
            wrapper = UIAnchorWidget(
                anchor_x="center_x", anchor_y="center_y", child=play_button, align_x=-40, align_y=align_y)
            play_button.wrapper = wrapper
            self.uimanager.add(wrapper)
            self.world_buttons.append(play_button)

            clear_button = CustomUIFlatButton(
                self.Alphabet_Textures, click_sound=self.click_sound, text="Clear", width=100, height=40)
            clear_button.on_click = self.ClearSlot
            clear_button.world_num = idx
            wrapper = UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
                                     child=clear_button, align_x=150, align_y=align_y+5)
            clear_button.wrapper = wrapper
            self.uimanager.add(wrapper)
            self.world_clear_buttons.append(clear_button)

        self._refresh_world_buttons()

        start_button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Tutorial", width=220, height=54)
        start_button.on_click = self.start_Tutorial
        wrapper = UIAnchorWidget(
            anchor_x="center_x", anchor_y="center_y", child=start_button, align_x=0, align_y=-90)
        start_button.wrapper = wrapper
        self.uimanager.add(wrapper)

        start_button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Progress Tree", width=220, height=54)
        start_button.on_click = self.on_scienceMenuclick
        wrapper = UIAnchorWidget(
            anchor_x="left", anchor_y="top", child=start_button, align_x=20, align_y=-20)
        start_button.wrapper = wrapper
        self.uimanager.add(wrapper)

        start_button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Upgrades", width=220, height=54)
        start_button.on_click = self.on_repeatable_upgrade_click
        wrapper = UIAnchorWidget(
            anchor_x="left", anchor_y="top", child=start_button, align_x=20, align_y=-80)
        start_button.wrapper = wrapper
        self.uimanager.add(wrapper)

        start_button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Volume", width=220, height=54)
        start_button.on_click = self.VolumeMenu
        wrapper = UIAnchorWidget(
            anchor_x="left", anchor_y="top", child=start_button, align_x=20, align_y=-140)
        start_button.wrapper = wrapper
        self.uimanager.add(wrapper)

        start_button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Credits", width=220, height=54)
        start_button.on_click = self.CreditsMenu
        wrapper = UIAnchorWidget(
            anchor_x="left", anchor_y="top", child=start_button, align_x=20, align_y=-200)
        start_button.wrapper = wrapper
        self.uimanager.add(wrapper)

        self.check_game_save()

        window = arcade.get_window()
        self.on_resize(window.width, window.height)

    def check_game_save(self):
        try:
            with open("resources/game.json", "r") as read_file:
                p = json.load(read_file)
        except:
            p = {"History": 0}

        changed = False

        science_names, science_defaults = self.load_sciences()
        science_state = state_list_from_save(
            p.get("science_menu"), science_names, science_defaults)
        science_map = state_dict_from_list(science_names, science_state)
        if p.get("science_menu") != science_map:
            changed = True
        p["science_menu"] = science_map

        progress_names, progress_defaults = self.load_progress_upgrades()
        progress_state = state_list_from_save(
            p.get("progress_menu"), progress_names, progress_defaults)
        progress_map = state_dict_from_list(progress_names, progress_state)
        if p.get("progress_menu") != progress_map:
            changed = True
        p["progress_menu"] = progress_map

        repeatable_defs = load_repeatable_upgrade_defs()
        repeatable_names = [entry.get("name", f"upgrade_{idx}")
                            for idx, entry in enumerate(repeatable_defs)]
        repeatable_defaults = [0] * len(repeatable_names)
        repeatable_state = state_list_from_save(
            p.get("repeatable_upgrades"), repeatable_names, repeatable_defaults, int)
        repeatable_map = state_dict_from_list(
            repeatable_names, repeatable_state, int)
        if p.get("repeatable_upgrades") != repeatable_map:
            changed = True
        p["repeatable_upgrades"] = repeatable_map

        if changed:
            with open("resources/game.json", "w") as write_file:
                json.dump(p, write_file)

    def load_sciences(self):
        with open("resources/GameBase.json", "r") as read_file:
            science_nodes = json.load(read_file)["ScienceMenu"]

        names = []
        defaults = []
        for idx, node in enumerate(science_nodes):
            name = node[0] or f"science_{idx}"
            names.append(name)
            defaults.append(bool(node[8]))
        return names, defaults

    def load_progress_upgrades(self):
        with open("resources/GameBase.json", "r") as read_file:
            menu_config = json.load(read_file)
        upgrade_menu = menu_config.get("ProgressUpgradeMenu", [])
        names = []
        defaults = []
        for idx, entry in enumerate(upgrade_menu):
            if not isinstance(entry, list) or not entry:
                continue
            if entry[0] != "progress":
                continue
            name = entry[1] or f"progress_{idx}"
            names.append(name)
            default_value = entry[9] if len(entry) > 9 else 0
            defaults.append(bool(default_value))
        return names, defaults

    def on_resize(self, width: int, height: int):
        base_width, base_height = 1440, 900
        scale_factor = min(width / base_width, height / base_height)
        self.background.scale = 3.6 * scale_factor
        self.background.center_x = width / 2
        self.background.center_y = height / 2

        self.christmas_background.scale = max(width / 5001, height / 3334)
        self.christmas_background.position = width / 2, height / 2

        title_width = max(width - 200, 400)
        self.title_text.update_text(
            self.title_text.text,
            self.Alphabet_Textures,
            center_x=width / 2,
            center_y=height - 140,
            width=title_width,
        )
        return super().on_resize(width, height)

    def VolumeMenu(self, event):
        self.uimanager.disable()
        Menu = VolumeMenu(self)
        show_view_resized(self.window, Menu)

    def CreditsMenu(self, event):
        self.uimanager.disable()
        Menu = CreditsMenu(self)
        show_view_resized(self.window, Menu)

    def update_audio(self):
        for audio in self.audios:
            apply_audio_volume(audio, self.audio_type_vols)

    def Start(self, event):
        if self.button == 4:
            window = arcade.get_window()
            width, height = window.width, window.height
            x = width/2+event.source.wrapper.align_x
            y = height/2+event.source.wrapper.align_y
            text = UpdatingText(f"Starts the Game.", self.Alphabet_Textures, 10, center_x=x,
                                center_y=y, width=200, Background_Texture="resources/gui/Small Text Background.png")
            self.texts.append(text)
            return
        slot = getattr(event.source, "world_num", 1)
        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)
        self.uimanager.disable()
        if self._slot_has_save(slot):
            Game = MyGame(self, file_num=slot,
                          world_gen="Normal", difficulty=1)
        else:
            Game = CreateWorld(self, slot)
        show_view_resized(self.window, Game)

    def ClearSlot(self, event):
        slot = getattr(event.source, "world_num", 1)
        path = get_save_path(slot)
        try:
            if path.exists():
                path.unlink()
        except Exception:
            logging.exception("Unable to clear save slot %s", slot)
        self._refresh_world_buttons()

    def start_Tutorial(self, event):
        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)
        self.uimanager.disable()
        Game = MyTutorial(self, file_num=None,
                          world_gen="Normal", difficulty=1)
        show_view_resized(self.window, Game)

    def on_scienceMenuclick(self, event):
        if self.button == 4:
            window = arcade.get_window()
            width, height = window.width, window.height
            x = event.source.wrapper.align_x
            y = height+event.source.wrapper.align_y
            text = UpdatingText(f"This Menu Upgrades the Science Tree in Game.", self.Alphabet_Textures, 10,
                                center_x=x, center_y=y, width=300, Background_Texture="resources/gui/Small Text Background.png")
            self.texts.append(text)
            return

        scienceMenu = UpgradeScienceMenu(self)
        self.uimanager.disable()
        show_view_resized(self.window, scienceMenu)

    def on_repeatable_upgrade_click(self, event):
        if self.button == 4:
            window = arcade.get_window()
            width, height = window.width, window.height
            x = event.source.wrapper.align_x
            y = height+event.source.wrapper.align_y
            text = UpdatingText("Invest History into repeatable bonuses.", self.Alphabet_Textures, 10,
                                center_x=x, center_y=y, width=320, Background_Texture="resources/gui/Small Text Background.png")
            self.texts.append(text)
            return

        upgrades = RepeatableUpgradeMenu(self)
        self.uimanager.disable()
        show_view_resized(self.window, upgrades)

    def on_show_view(self):
        super().on_show_view()
        arcade.set_background_color(PARCHMENT_COLOR)
        reset_window_viewport(self.window)
        self._refresh_world_buttons()

    def on_draw(self):
        """ Draw this view """
        self.clear(self._background_color)
        self.background.draw()
        self.christmas_background.draw()

        self.uimanager.draw()
        for text in self.texts:
            text.draw()

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        self.button = button
        return super().on_mouse_press(x, y, button, modifiers)

    def on_update(self, delta_time: float):
        for text in self.texts:
            if text.update(delta_time):
                self.texts.remove(text)
        return super().on_update(delta_time)

    def _slot_has_save(self, slot: int) -> bool:
        path = get_save_path(slot)
        return path.exists() and path.stat().st_size > 0

    def _refresh_world_buttons(self) -> None:
        for button in getattr(self, "world_buttons", []):
            slot = getattr(button, "world_num", 1)
            label = f"World {slot}"
            if not self._slot_has_save(slot):
                label += " (Empty)"
            button.set_text(label, self.Alphabet_Textures)
        for button in getattr(self, "world_clear_buttons", []):
            slot = getattr(button, "world_num", 1)
            has_save = self._slot_has_save(slot)
            button.enabled = has_save
            button.visible = True


class CreateWorld(arcade.View):

    def __init__(self, menu, file_num):
        super().__init__()
        """ This is run once when we switch to this view """
        arcade.set_background_color(PARCHMENT_COLOR)
        self.window.background_color = PARCHMENT_COLOR
        reset_window_viewport(self.window)
        self.click_sound = menu.click_sound
        self.Background_music = menu.Background_music
        self.Christmas_music = menu.Christmas_music

        self.audios = menu.audios
        self.audio_type_vols = menu.audio_type_vols

        self.background = arcade.Sprite(
            "resources/gui/Large Bulletin.png", scale=16.5, center_x=370, center_y=180)
        self.christmas_background = arcade.Sprite(
            "resources/gui/ChristmasOverlay.png", scale=.25, center_x=370, center_y=180)

        self.texts = []

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        self.menu = menu
        self.file_num = file_num

        textures = load_texture_grid(
            "resources/gui/Wooden Font.png", 14, 24, 12, 71, margin=1)

        self.Alphabet_Textures = {" ": None}
        string = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyz.:,%/-+_'"
        for i in range(len(string)):
            self.Alphabet_Textures[string[i]] = textures[i]

        text = CustomTextSprite(
            "World Type:", self.Alphabet_Textures, width=500)
        text.org_x = 5
        text.org_y = 180
        self.texts.append(text)

        self.gen_list = ["Normal", "Desert", "Forest"]
        self.gen_list_index = 0
        button = CustomUIFlatButton(self.Alphabet_Textures, text="Normal",
                                    width=140, height=50, Pressed_Texture="resources/gui/Wood Button.png")
        button.on_click = self.Generation_change
        wrapper = UIAnchorWidget(
            anchor_x="center_x", anchor_y="center_y", child=button, align_x=0, align_y=145)
        self.uimanager.add(wrapper)
        button.set_text(
            self.gen_list[self.gen_list_index], self.Alphabet_Textures)

        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound=self.click_sound,
                                          width=40, height=40, Texture="resources/gui/Right Pointer resized.png")
        start_button.direction = 1
        start_button.button = button
        start_button.on_click = self.Generation_change
        wrapper = UIAnchorWidget(
            anchor_x="center_x", anchor_y="center_y", child=start_button, align_x=80, align_y=145)
        self.uimanager.add(wrapper)

        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound=self.click_sound,
                                          width=40, height=40, Texture="resources/gui/Left Pointer resized.png")
        start_button.direction = -1
        start_button.button = button
        start_button.on_click = self.Generation_change
        wrapper = UIAnchorWidget(
            anchor_x="center_x", anchor_y="center_y", child=start_button, align_x=-80, align_y=145)
        self.uimanager.add(wrapper)

        text = CustomTextSprite(
            "Difficulty:", self.Alphabet_Textures, width=500)
        text.org_x = 5
        text.org_y = 80
        self.texts.append(text)

        self.difficulty_list = [" Easy ", "Normal", " Hard "]
        self.difficulty_list_index = 0
        button = CustomUIFlatButton(self.Alphabet_Textures, text="Easy", width=140,
                                    height=50, text_offset_x=10, Pressed_Texture="resources/gui/Wood Button.png")
        button.on_click = self.Difficulty_change
        wrapper = UIAnchorWidget(
            anchor_x="center_x", anchor_y="center_y", child=button, align_x=0, align_y=50)
        self.uimanager.add(wrapper)
        button.set_text(
            self.difficulty_list[self.difficulty_list_index], self.Alphabet_Textures)

        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound=self.click_sound,
                                          width=40, height=40, Texture="resources/gui/Right Pointer resized.png")
        start_button.direction = 1  # right
        start_button.button = button
        start_button.on_click = self.Difficulty_change
        wrapper = UIAnchorWidget(
            anchor_x="center_x", anchor_y="center_y", child=start_button, align_x=80, align_y=50)
        self.uimanager.add(wrapper)

        start_button = CustomUIFlatButton(self.Alphabet_Textures, click_sound=self.click_sound,
                                          width=40, height=40, Texture="resources/gui/Left Pointer resized.png")
        start_button.direction = -1  # left
        start_button.button = button
        start_button.on_click = self.Difficulty_change
        wrapper = UIAnchorWidget(
            anchor_x="center_x", anchor_y="center_y", child=start_button, align_x=-80, align_y=50)
        self.uimanager.add(wrapper)

        start_button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Start", width=140, height=50)
        start_button.on_click = self.Start
        wrapper = UIAnchorWidget(
            anchor_x="center_x", anchor_y="center_y", child=start_button, align_x=0, align_y=-100)
        self.uimanager.add(wrapper)

        start_button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Return", width=220, height=54)
        start_button.on_click = self.Return
        wrapper = UIAnchorWidget(
            anchor_x="left", anchor_y="top", child=start_button, align_x=20, align_y=-20)
        self.uimanager.add(wrapper)

        start_button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Volume", width=220, height=54)
        start_button.on_click = self.VolumeMenu
        wrapper = UIAnchorWidget(
            anchor_x="left", anchor_y="top", child=start_button, align_x=20, align_y=-80)
        self.uimanager.add(wrapper)

        window = arcade.get_window()
        width, height = window.width, window.height
        for text in self.texts:
            text.center_x = width/2+text.org_x
            text.center_y = height/2+text.org_y
            text.update_text(text.text, self.Alphabet_Textures,
                             center_x=text.center_x, center_y=text.center_y)

        self.christmas_background = arcade.Sprite(
            "resources/gui/ChristmasOverlay.png", scale=.25, center_x=370, center_y=180)
        self.on_resize(window.width, window.height)

    def on_resize(self, width: int, height: int):
        stretch_background(self.background, width, height, padding=0.2)

        self.christmas_background.position = width/2, height/2
        self.christmas_background.scale = .25*max(width/1240, height/900)

        for text in self.texts:
            text.center_x = width/2+text.org_x
            text.center_y = height/2+text.org_y
            text.update_text(text.text, self.Alphabet_Textures,
                             center_x=text.center_x, center_y=text.center_y)
        resize_ui_manager(self, width, height)
        return super().on_resize(width, height)

    def Generation_change(self, event):
        step = getattr(event.source, "direction", 1)
        self.gen_list_index = (self.gen_list_index + step) % len(self.gen_list)
        target_button = getattr(event.source, "button", event.source)
        target_button.set_text(
            self.gen_list[self.gen_list_index], self.Alphabet_Textures)

    def Difficulty_change(self, event):
        step = getattr(event.source, "direction", 1)
        self.difficulty_list_index = (
            self.difficulty_list_index + step) % len(self.difficulty_list)
        target_button = getattr(event.source, "button", event.source)
        target_button.set_text(
            self.difficulty_list[self.difficulty_list_index], self.Alphabet_Textures)

    def Start(self, event):
        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)
        self.uimanager.disable()
        Game = MyGame(self.menu, file_num=self.file_num,
                      world_gen=self.gen_list[self.gen_list_index], difficulty=self.difficulty_list_index+1)
        show_view_resized(self.window, Game)

    def Return(self, event):
        self.uimanager.disable()
        self.menu.uimanager.enable()
        show_view_resized(self.window, self.menu)

    def VolumeMenu(self, event):
        self.uimanager.disable()
        Game = VolumeMenu(self)
        show_view_resized(self.window, Game)

    def update_audio(self):
        for audio in self.audios:
            apply_audio_volume(audio, self.audio_type_vols)

    def on_show_view(self):
        super().on_show_view()
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)

        reset_window_viewport(self.window)

    def on_draw(self):
        """ Draw this view """
        self.clear()
        self.background.draw()
        self.christmas_background.draw()

        self.uimanager.draw()
        for text in self.texts:
            text.draw()

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

        self.background = arcade.Sprite(
            "resources/gui/Large Bulletin.png", scale=16.5, center_x=370, center_y=180)
        self.christmas_background = arcade.Sprite(
            "resources/gui/ChristmasOverlay.png", scale=.25, center_x=370, center_y=180)

        x = self.window.width/2
        y = self.window.height/2+150
        self.texts.append(CustomTextSprite(f"Credits", self.menu.Alphabet_Textures,
                          center_x=x, center_y=y, scale=4, text_margin=60, width=500))
        y -= 40
        self.texts.append(CustomTextSprite(f"The Arcade Library by Paul Vincent Craven",
                          self.menu.Alphabet_Textures, center_x=x, center_y=y, width=500))
        y -= 50
        self.texts.append(CustomTextSprite(f"Christmas Over Lay from: https://www.freepik.com/free-vector/watercolor-christmas  -background_19963694.htm",
                          self.menu.Alphabet_Textures, center_x=x, center_y=y, text_scale=2, text_margin=13, width=1000))
        y -= 60
        self.texts.append(CustomTextSprite(f"Wooden Buttons are from: https://www.freepik.com/free-vector/wooden-buttons  -user-interface-design-game-video-player-website-vector-cartoon-set-brown  _18056387.htm",
                          self.menu.Alphabet_Textures, center_x=x, center_y=y, width=1000))
        y -= 60
        self.texts.append(CustomTextSprite(f"Silver Buttons are from: https://www.freepik.com/free-vector/game-buttons-wood-stone-gamer-  interface_23068339.htm",
                          self.menu.Alphabet_Textures, center_x=x, center_y=y, scale=.9, text_margin=12, width=1000))
        y -= 60
        self.texts.append(CustomTextSprite(f"Gold Buttons are from: https://www.freepik.com/free-vector/wooden-gold-buttons-ui-game  _12760665.htm",
                          self.menu.Alphabet_Textures, center_x=x, center_y=y, text_scale=2, text_margin=13, width=1000))
        y -= 60
        self.texts.append(CustomTextSprite(f"Wooden Backgrounds are from: https://www.freepik.com/free-vector/wooden-gold-buttons-ui  -game_12760665.htm",
                          self.menu.Alphabet_Textures, center_x=x, center_y=y, text_scale=2, text_margin=13, width=1000))
        y -= 60

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        menu_button = CustomUIFlatButton(
            self.menu.Alphabet_Textures, click_sound=self.menu.click_sound, text="Back", width=220, height=54)
        menu_button.on_click = self.exit
        wrapper = UIAnchorWidget(
            anchor_x="left", anchor_y="top", child=menu_button, align_x=20, align_y=-20)
        self.uimanager.add(wrapper)

        window = arcade.get_window()
        self.on_resize(window.width, window.height)

    def on_draw(self):
        self.clear(PARCHMENT_COLOR)
        width = getattr(arcade.get_window(), "width", 0) or self.window.width
        height = getattr(arcade.get_window(), "height", 0) or self.window.height
        draw_rect_filled(XYWH(width / 2, height / 2, width, height), PARCHMENT_COLOR)
        self.background.draw()
        self.christmas_background.draw()

        for text in self.texts:
            text.draw()
        self.uimanager.draw()
        return super().on_draw()

    def on_resize(self, width: int, height: int):
        stretch_background(self.background, width, height, padding=0.18)

        self.christmas_background.scale = max(width / 5001, height / 3334)
        self.christmas_background.position = width / 2, height / 2
        resize_ui_manager(self, width, height)
        return super().on_resize(width, height)

    def exit(self, event):
        self.uimanager.disable()
        self.menu.uimanager.enable()

        show_view_resized(self.window, self.menu)


class UpgradeScienceMenu(arcade.View):
    def __init__(self, menu):

        super().__init__()
        self.click_sound = menu.click_sound
        self.menu_view = menu
        self.background = arcade.Sprite(
            "resources/gui/Large Bulletin.png", scale=16.5, center_x=370, center_y=180)
        self.christmas_background = arcade.Sprite(
            "resources/gui/ChristmasOverlay.png", scale=.25, center_x=370, center_y=180)

        self.gold_button_texture = arcade.load_texture(
            "resources/gui/Gold Button.png")
        self.silver_button_texture = arcade.load_texture(
            "resources/gui/Silver Button.png")

        textures = load_texture_grid(
            "resources/gui/Wooden Font.png", 14, 24, 12, 71, margin=1)
        self.Alphabet_Textures = {" ": None}
        string = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyz.:,%/-+_'"
        for i in range(len(string)):
            self.Alphabet_Textures[string[i]] = textures[i]
        self.set_up()

        self.tooltip = CustomTextSprite(
            "",
            self.Alphabet_Textures,
            center_x=-1000,
            center_y=-1000,
            width=260,
            height=0,
            text_margin=12,
            text_scale=0.9,
            Background_Texture="resources/gui/Small Text Background.png",
            Background_offset_x=0,
            Background_offset_y=-50,
            vertical_align='top',
        )
        self.tooltip_visible = False

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
        arcade.set_background_color(PARCHMENT_COLOR)
        self.window.background_color = PARCHMENT_COLOR
        reset_window_viewport(self.window)

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()
        self.lineList = ShapeElementList()
        self.load()

        menu_button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Back", width=220, height=54)
        menu_button.on_click = self.exit
        wrapper = UIAnchorWidget(
            anchor_x="left", anchor_y="top", child=menu_button, align_x=20, align_y=-20)
        self.uimanager.add(wrapper)

        button = CustomUIFlatButton(self.Alphabet_Textures, click_sound=self.click_sound, width=50, height=50, scale=.6, x=50, y=50, offset_x=25, offset_y=25,
                                    Texture="resources/gui/Question Mark.png", Pressed_Texture="resources/gui/Question Mark.png", Hovered_Texture="resources/gui/Question Mark.png")
        button.on_click = self.on_question_click
        button.open = False
        wrapper = UIAnchorWidget(anchor_x="left", anchor_y="top",
                                 child=button, align_x=200, align_y=-50)
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
                self.history_points = p.get("History", 0)
        except:
            saved = False
            self.history_points = 0
            p = {}

        window = arcade.get_window()
        self.texts = []
        self.text = UpdatingText(f"{floor(self.history_points)} History", self.Alphabet_Textures, float(
            "inf"), scale=4, text_margin=50, center_x=-400+window.width/2, center_y=200+window.height/2)

        with open("resources/GameBase.json", "r") as read_file:
            menu_config = json.load(read_file)
        science_nodes = menu_config.get("ScienceMenu", [])
        upgrade_layout = menu_config.get("ProgressUpgradeMenu", [])
        if not upgrade_layout:
            upgrade_layout = [["science", node[0], node[1], node[2]]
                              for node in science_nodes]

        self._science_defaults = []
        self._science_names = []
        self._progress_defaults = []
        self._progress_names = []

        science_lookup = {}
        for idx, node in enumerate(science_nodes):
            node_name = node[0] or f"science_{idx}"
            science_lookup[node_name] = (node, idx)
            self._science_names.append(node_name)
            self._science_defaults.append(bool(node[8]))

        if saved:
            science_state = state_list_from_save(
                p.get("science_menu"), self._science_names, self._science_defaults)
        else:
            science_state = list(self._science_defaults)

        combined_nodes = []

        for entry in upgrade_layout:
            if not isinstance(entry, list) or not entry:
                continue
            entry_type = entry[0]
            if entry_type == "science":
                if len(entry) < 4:
                    continue
                name = entry[1]
                layout_x = entry[2]
                layout_y = entry[3]
                node_info = science_lookup.get(name)
                if not node_info:
                    continue
                node, idx = node_info
                combined_nodes.append({
                    "node": node,
                    "type": "science",
                    "save_index": idx,
                    "display_x": layout_x,
                    "display_y": layout_y,
                })
            elif entry_type == "progress":
                if len(entry) < 4:
                    continue
                name = entry[1]
                layout_x = entry[2]
                layout_y = entry[3]
                connections = entry[4] if len(entry) > 4 else []
                description = entry[5] if len(entry) > 5 else ""
                affect = entry[6] if len(entry) > 6 else {}
                base_cost = entry[7] if len(entry) > 7 else 0
                history_cost = entry[8] if len(entry) > 8 else 0
                default_unlocked = entry[9] if len(entry) > 9 else 0

                progress_index = len(self._progress_defaults)
                self._progress_names.append(name)
                self._progress_defaults.append(bool(default_unlocked))

                node = [
                    name,
                    layout_x,
                    layout_y,
                    connections,
                    description,
                    affect,
                    base_cost,
                    history_cost,
                    default_unlocked,
                ]
                combined_nodes.append({
                    "node": node,
                    "type": "progress",
                    "save_index": progress_index,
                    "display_x": layout_x,
                    "display_y": layout_y,
                })

        if saved:
            progress_state = state_list_from_save(
                p.get("progress_menu"), self._progress_names, self._progress_defaults)
        else:
            progress_state = list(self._progress_defaults)

        name_to_index = {}
        for combined_idx, entry in enumerate(combined_nodes):
            node = entry["node"]
            name = node[0] or f"upgrade_{entry['type']}_{entry['save_index']}"
            name_to_index[name] = combined_idx

        for global_id, entry in enumerate(combined_nodes):
            node = entry["node"]
            node_label = node[0] or "Unnamed Research"
            display_x = entry["display_x"]
            display_y = entry["display_y"]
            badge_cfg = BadgeConfig(
                text=str(node[7]),
                texture="resources/gui/wood_circle.png",
                anchor_x="right",
                anchor_y="bottom",
                padding_x=10,
                padding_y=6,
                offset_x=30,
                offset_y=40,
                text_scale=0.6,
                text_margin=8,
            )
            start_button = CustomUIFlatButton(
                self.Alphabet_Textures,
                click_sound=self.click_sound,
                text=node_label,
                width=160,
                height=54,
                text_margin=12,
                badge=badge_cfg,
            )
            start_button.on_click = self.on_buttonclick
            wrapper = UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
                                     child=start_button, align_x=display_x, align_y=display_y)
            wrapper.true_x = display_x
            self.science_buttons.append(wrapper)

            wrapper.description = node[4]
            wrapper.identity = global_id

            start_button.affect = node[5]
            start_button.cost = node[7]
            start_button.wrapper = wrapper
            start_button.save_type = entry["type"]
            start_button.save_index = entry["save_index"]

            connections = []
            for connection_name in node[3]:
                idx = name_to_index.get(connection_name)
                if idx is not None:
                    connections.append(idx)
            start_button.connections = connections

            self.uimanager.add(wrapper)

            if entry["type"] == "science":
                state_list = science_state
            else:
                state_list = progress_state
            start_button.unlocked = bool(
                state_list[start_button.save_index] if start_button.save_index < len(state_list) else False)

            if start_button.unlocked:
                start_button.cost = float("inf")
                wrapper.identity = float("inf")
                convert_button(start_button, self.gold_button_texture)
                start_button.set_badge_text(None)
            else:
                convert_button(start_button, self.silver_button_texture)
                start_button.set_badge_text(str(node[7]))

            wrapper.unlocked = start_button.unlocked

            for i in start_button.connections:
                target_entry = combined_nodes[i]
                endx = target_entry.get("display_x", target_entry["node"][1]) + 370
                endy = target_entry.get("display_y", target_entry["node"][2]) + 250
                line = create_line(
                    display_x+370, display_y+250, endx, endy, (0, 0, 0, 255), line_width=5)
                line.identity = global_id
                self.lineList.append(line)

    def on_resize(self, width: int, height: int):
        stretch_background(self.background, width, height, padding=0.18)

        self.christmas_background.position = width/2, height/2
        self.christmas_background.scale = .25*max(width/1240, height/900)

        self.lineList.center_x = width/2 - 400 + self.x
        self.lineList.center_y = height/2 - 250
        resize_ui_manager(self, width, height)
        reset_window_viewport(self.window)

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
            p = {}

        science_defaults = getattr(self, "_science_defaults", [])
        progress_defaults = getattr(self, "_progress_defaults", [])
        science_unlocks = [False] * len(science_defaults)
        progress_unlocks = [False] * len(progress_defaults)

        for wrapper in self.science_buttons:
            child = getattr(wrapper, "child", None)
            if not child:
                continue
            save_index = getattr(child, "save_index", None)
            save_type = getattr(child, "save_type", None)
            if save_index is None or save_type not in ("science", "progress"):
                continue
            if save_type == "science" and save_index < len(science_unlocks):
                science_unlocks[save_index] = bool(child.unlocked)
            elif save_type == "progress" and save_index < len(progress_unlocks):
                progress_unlocks[save_index] = bool(child.unlocked)

        with open("resources/game.json", "w") as write_file:
            p["History"] = self.history_points
            p["science_menu"] = state_dict_from_list(
                getattr(self, "_science_names", []), science_unlocks)
            p["progress_menu"] = state_dict_from_list(
                getattr(self, "_progress_names", []), progress_unlocks)
            json.dump(p, write_file)

        self.uimanager.disable()
        self.menu_view.uimanager.enable()
        show_view_resized(self.window, self.menu_view)

    def on_question_click(self, event):
        window = arcade.get_window()
        if not self.question:
            text = CustomTextSprite(
                "Use this menu to unlock more of the science tree in game.",
                self.Alphabet_Textures, width=270,
                center_x=event.source.wrapper.align_x+250, center_y=event.source.wrapper.align_y+750,
                Background_offset_x=0, Background_offset_y=-55, Background_scale=1.05, Background_Texture="resources/gui/Small Text Background.png"
            )
            self.question = text
        else:
            self.question = None

    def on_buttonclick(self, event):
        if self.button == 4:
            window = arcade.get_window()
            string = "Not Unlocked. "
            if event.source.wrapper.unlocked:
                string = "Unlocked.  "
            text = UpdatingText(f"{string}{event.source.cost}", self.Alphabet_Textures, .5, scale=1,
                                center_x=event.source.wrapper.align_x+window.width/2, center_y=event.source.rapper.align_y+window.height/2)
            self.texts.append(text)
            return
        self.handle_cost(event.source)

    def handle_cost(self, source):
        window = arcade.get_window()
        wrapper = source.wrapper
        if source.unlocked:
            text = UpdatingText(f"Already unlocked", self.Alphabet_Textures, .5, scale=1,
                                center_x=wrapper.align_x+window.width/2, center_y=wrapper.align_y+window.height/2)
            self.texts.append(text)
            return

        cost = self.check_backwards(source)
        if cost <= self.history_points:
            self.history_points -= cost
            self.unlock_backwards(source)
            self.text.update_text(f"{floor(self.history_points)} History", self.Alphabet_Textures, scale=4,
                                  text_margin=50, center_x=-400+window.width/2, center_y=200+window.height/2)
        else:
            text = UpdatingText(f"You need {cost-self.history_points} History", self.Alphabet_Textures, .5, scale=1,
                                center_x=wrapper.align_x+window.width/2, center_y=wrapper.align_y+window.height/2)
            self.texts.append(text)
            return

        wrapper.identity = float("inf")
        self.handle_affect(source)

    def handle_affect(self, source):
        convert_button(source, self.gold_button_texture)
        source.cost = float("inf")
        source.unlocked = True
        source.set_badge_text(None)
        if hasattr(source, "wrapper") and source.wrapper:
            source.wrapper.unlocked = True

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

    def on_show_view(self):
        super().on_show_view()
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)

        reset_window_viewport(self.window)

    def on_draw(self):
        """ Draw this view """
        width = getattr(arcade.get_window(), "width", 0) or self.window.width
        height = getattr(arcade.get_window(), "height", 0) or self.window.height
        self.clear(PARCHMENT_COLOR)
        draw_rect_filled(XYWH(width / 2, height / 2, width, height), PARCHMENT_COLOR)
        self.background.draw()
        self.christmas_background.draw()

        self.lineList.draw()
        self.uimanager.draw()
        for wrapper in self.science_buttons:
            child = getattr(wrapper, "child", None)
            if child and hasattr(child, "draw_badge_overlay"):
                child.draw_badge_overlay()
        for text in self.texts:
            text.draw()
        self.text.draw()
        if self.tooltip_visible:
            self.tooltip.draw()
        if self.question:
            self.question.draw()

    def on_mouse_motion(self, x, y, dx, dy):
        """
        Called whenever the mouse moves.
        """
        self.mouse_x = x
        self.mouse_y = y
        self.update_science_tooltip(x, y)

    def update_science_tooltip(self, x, y):
        collided = False
        for button in self.science_buttons:
            child = getattr(button, "child", None)
            rect = child.rect if child else button.rect
            if not (rect.left <= x <= rect.right and rect.bottom <= y <= rect.top):
                continue
            center_x = (rect.left + rect.right) / 2
            provisional_center_y = rect.top + 20
            self.tooltip.update_text(
                button.description,
                self.Alphabet_Textures,
                center_x=center_x,
                center_y=provisional_center_y,
                width=260,
                vertical_align='top',
            )
            text_height = getattr(self.tooltip, '_content_height', 0)
            desired_top = rect.top + 12
            desired_center_y = desired_top - text_height / 2
            self.tooltip.set_position(center_x, desired_center_y)
            self.tooltip_visible = True
            collided = True
            break
        if not collided:
            self.tooltip_visible = False

    def on_update(self, delta_time):

        if self.pressed_a and self.x + 50 < -self.science_buttons[0].true_x:
            self.x += 1000*delta_time
            self.lineList.move(1000*delta_time, 0)

            self.update_science_tooltip(self.mouse_x, self.mouse_y)
        if self.pressed_d and self.x - 50 > -self.science_buttons[-1].true_x:
            self.x -= 1000*delta_time
            self.lineList.move(-1000*delta_time, 0)

            self.update_science_tooltip(self.mouse_x, self.mouse_y)

        if self.pressed_a or self.pressed_d:
            for button2 in self.science_buttons:
                button2.align_x = button2.true_x+self.x
        for text in self.texts:
            if text.update(delta_time):
                self.texts.remove(text)

    def on_mouse_press(self, x: float, y: float, button: int, modifiers: int):
        self.button = button
        if sprites_in_range(15, (x, y), self.text.Sprite_List):
            text = UpdatingText(f"Get at end of a Game. Use to upgrade science tree", self.Alphabet_Textures, .5, scale=1,
                                center_x=x, center_y=y-20, Background_offset_x=50, Background_Texture="resources/gui/Small Text Background.png")
            self.texts.append(text)
        return super().on_mouse_press(x, y, button, modifiers)


class RepeatableUpgradeMenu(arcade.View):
    def __init__(self, menu):
        super().__init__()
        self.menu = menu
        self.click_sound = menu.click_sound
        self.background = arcade.Sprite(
            "resources/gui/Large Bulletin.png", scale=16.5, center_x=370, center_y=180)
        self.christmas_background = arcade.Sprite(
            "resources/gui/ChristmasOverlay.png", scale=.25, center_x=370, center_y=180)

        self.Alphabet_Textures = menu.Alphabet_Textures

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        self.upgrade_defs = load_repeatable_upgrade_defs()
        try:
            with open("resources/game.json", "r") as read_file:
                save_state = json.load(read_file)
        except:
            save_state = {"History": 0, "repeatable_upgrades": {}}

        stored_levels = save_state.get("repeatable_upgrades", {})
        self.history = save_state.get("History", 0)
        self.upgrade_levels: dict[str, int] = {}
        for definition in self.upgrade_defs:
            name = definition.get("name", "Upgrade")
            self.upgrade_levels[name] = int(stored_levels.get(name, 0))
        for definition in self.upgrade_defs:
            name = definition.get("name", "Upgrade")
            self.upgrade_levels.setdefault(name, 0)

        self.texts: list[CustomTextSprite] = []
        self._build_texts()
        self._build_buttons()
        if not self.upgrade_defs:
            self._set_status("No repeatable upgrades available yet.")

        menu_button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Back", width=220, height=54)
        menu_button.on_click = self._exit
        wrapper = UIAnchorWidget(anchor_x="left", anchor_y="top",
                                 child=menu_button, align_x=20, align_y=-20)
        self.uimanager.add(wrapper)

        window = arcade.get_window()
        self.on_resize(window.width, window.height)

    def _build_texts(self):
        window = arcade.get_window()
        self.history_text = CustomTextSprite(
            "",
            self.Alphabet_Textures,
            center_x=window.width/2,
            center_y=window.height/2+220,
            width=800,
            text_margin=18,
        )
        self.history_text.org_x = 0
        self.history_text.org_y = 220
        self.texts.append(self.history_text)

        self.status_text = CustomTextSprite(
            "",
            self.Alphabet_Textures,
            center_x=window.width/2,
            center_y=window.height/2-260,
            width=800,
            text_margin=18,
        )
        self.status_text.org_x = 0
        self.status_text.org_y = -260
        self.texts.append(self.status_text)
        self._set_status("")

        self.upgrade_texts: dict[str, CustomTextSprite] = {}
        base_offset = 140
        for idx, definition in enumerate(self.upgrade_defs):
            y_offset = base_offset - idx * 90
            text = CustomTextSprite(
                "",
                self.Alphabet_Textures,
                center_x=window.width/2-100,
                center_y=window.height/2+y_offset,
                width=600,
                text_margin=16,
            )
            text.org_x = -100
            text.org_y = y_offset
            self.texts.append(text)
            self.upgrade_texts[definition.get("name", f"Upgrade {idx}")] = text

        self._refresh_history_text()

    def _build_buttons(self):
        self.upgrade_buttons: dict[str, CustomUIFlatButton] = {}
        base_offset = 140
        for idx, definition in enumerate(self.upgrade_defs):
            y_offset = base_offset - idx * 90
            button = CustomUIFlatButton(
                self.Alphabet_Textures,
                click_sound=self.click_sound,
                text="Upgrade",
                width=200,
                height=70,
                scale=1.05
            )
            button.upgrade_name = definition.get("name", f"Upgrade {idx}")
            button.definition = definition
            button.on_click = self._on_upgrade_click
            wrapper = UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
                                     child=button, align_x=380, align_y=y_offset)
            button.wrapper = wrapper
            self.uimanager.add(wrapper)
            self.upgrade_buttons[button.upgrade_name] = button

        self._refresh_upgrade_rows()

    def _calculate_cost(self, definition, level):
        base_cost = definition.get("base_cost", 10)
        growth = definition.get("cost_growth", 1.2)
        return ceil(base_cost * (growth ** level))

    def _format_effect_summary(self, effect: dict[str, float]):
        parts = []
        for key, value in effect.items():
            label = key.replace("_", " ")
            if key.endswith("_multiplier"):
                label = label.replace(" multiplier", "")
                parts.append(f"+{value}% {label} / level")
            elif key.endswith("_storage"):
                label = label.replace(" storage", "")
                parts.append(f"+{value} {label} storage / level")
            else:
                parts.append(f"+{value} {label} / level")
        return "; ".join(parts)

    def _refresh_upgrade_rows(self):
        for definition in self.upgrade_defs:
            name = definition.get("name", "Upgrade")
            level = self.upgrade_levels.get(name, 0)
            cost = self._calculate_cost(definition, level)
            description = definition.get("description", "")
            effect_text = self._format_effect_summary(
                definition.get("effect", {}))
            effect_line = f"Effect: {effect_text}" if effect_text and not description else None
            label = self.upgrade_texts.get(name)
            if label:
                text_lines = [f"{name} - Level {level}"]
                detail_line = description if description else effect_line
                if detail_line and detail_line not in text_lines:
                    text_lines.append(detail_line)
                label.update_text(
                    "\n".join(text_lines),
                    self.Alphabet_Textures,
                    center_x=label.center_x,
                    center_y=label.center_y,
                    width=600,
                )
            button = self.upgrade_buttons.get(name)
            if button:
                button.set_text(f"Upgrade ({cost} History)",
                                self.Alphabet_Textures)
                button.enabled = self.history >= cost

    def _refresh_history_text(self):
        self.history_text.update_text(
            f"History: {floor(self.history)}",
            self.Alphabet_Textures,
            center_x=self.history_text.center_x,
            center_y=self.history_text.center_y,
        )

    def _set_status(self, text: str):
        self.status_text.update_text(
            text,
            self.Alphabet_Textures,
            center_x=self.status_text.center_x,
            center_y=self.status_text.center_y,
        )

    def _on_upgrade_click(self, event):
        name = getattr(event.source, "upgrade_name", None)
        definition = getattr(event.source, "definition", None)
        if not name or not definition:
            return
        level = self.upgrade_levels.get(name, 0)
        cost = self._calculate_cost(definition, level)
        if self.history < cost:
            missing = ceil(cost - self.history)
            self._set_status(f"Need {missing} more History.")
            return
        self.history -= cost
        self.upgrade_levels[name] = level + 1
        self._set_status(f"{name} upgraded to level {level+1}!")
        self._refresh_history_text()
        self._refresh_upgrade_rows()

    def _exit(self, event):
        self._save_upgrades()
        self.uimanager.disable()
        self.menu.uimanager.enable()
        show_view_resized(self.window, self.menu)

    def _save_upgrades(self):
        try:
            with open("resources/game.json", "r") as read_file:
                data = json.load(read_file)
        except:
            data = {}
        data["History"] = self.history
        data["repeatable_upgrades"] = self.upgrade_levels
        with open("resources/game.json", "w") as write_file:
            json.dump(data, write_file)

    def on_resize(self, width: int, height: int):
        stretch_background(self.background, width, height, padding=0.18)

        self.christmas_background.position = width/2, height/2
        self.christmas_background.scale = .25*max(width/1240, height/900)

        for text in self.texts:
            text.center_x = width/2 + getattr(text, "org_x", 0)
            text.center_y = height/2 + getattr(text, "org_y", 0)
        self._refresh_history_text()
        self._refresh_upgrade_rows()
        resize_ui_manager(self, width, height)
        return super().on_resize(width, height)

    def on_draw(self):
        self.clear()
        self.background.draw()
        self.christmas_background.draw()
        for text in self.texts:
            text.draw()
        self.uimanager.draw()

    def on_show_view(self):
        super().on_show_view()
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)
        reset_window_viewport(self.window)

class ScienceMenu(arcade.View):
    def __init__(self, game_view):

        super().__init__()
        self.click_sound = game_view.click_sound
        self.click_sound.volume = game_view.click_sound.volume
        self.set_up(game_view)

        self.background = arcade.Sprite(
            "resources/gui/Large Bulletin.png", scale=16.5, center_x=370, center_y=180)
        self.christmas_background = arcade.Sprite(
            "resources/gui/ChristmasOverlay.png", scale=.25, center_x=370, center_y=180)

        textures = load_texture_grid(
            "resources/gui/Wooden Font.png", 14, 24, 12, 71, margin=1)
        self.Alphabet_Textures = {" ": None}
        string = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyz.:,%/-+_'"
        for i in range(len(string)):
            self.Alphabet_Textures[string[i]] = textures[i]
        self.gold_button_texture = arcade.load_texture(
            "resources/gui/Gold Button.png")
        self.silver_button_texture = arcade.load_texture(
            "resources/gui/Silver Button.png")

        self.pre_load()

        window = arcade.get_window()
        self.texts = []
        self.text = UpdatingText(f"{round(self.game_view.science*10)/10} Science", self.Alphabet_Textures,
                                 float("inf"), center_x=-400+window.width/2, center_y=200+window.height/2)
        self.texts.append(self.text)

        self.tooltip = CustomTextSprite(
            "",
            self.Alphabet_Textures,
            center_x=-1000,
            center_y=-1000,
            width=260,
            height=0,
            text_margin=12,
            text_scale=0.9,
            Background_Texture="resources/gui/Small Text Background.png",
            Background_offset_x=0,
            Background_offset_y=-50,
            vertical_align='top',
        )
        self.tooltip_visible = False

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
        arcade.set_background_color(PARCHMENT_COLOR)
        self.window.background_color = PARCHMENT_COLOR
        reset_window_viewport(self.window)

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        self.lineList = ShapeElementList()
        self.science_buttons = []

    def on_resize(self, width: int, height: int):
        stretch_background(self.background, width, height, padding=0.18)

        self.christmas_background.position = width/2, height/2
        self.christmas_background.scale = .25*max(width/1240, height/900)

        self.lineList.center_x = width/2 - 400 + self.x
        self.lineList.center_y = height/2 - 250
        resize_ui_manager(self, width, height)

    def pre_load(self):
        self.load()

        start_button = CustomUIFlatButton(
            self.Alphabet_Textures, click_sound=self.click_sound, text="Back", width=140, height=50)
        start_button.on_click = self.exit
        wrapper = UIAnchorWidget(anchor_x="left", anchor_y="top",
                                 child=start_button, align_x=20, align_y=-20)
        self.uimanager.add(wrapper)
        start_button.unlocked = True

        wrapper.true_x = 300
        wrapper.description = "None"
        self.menu_button = wrapper

    def load(self):
        saved = self.game_view.science_list != None

        with open("resources/game.json", "r") as read_file:
            saved_science = json.load(read_file)['science_menu']

        with open("resources/GameBase.json", "r") as read_file:
            buttons = json.load(read_file)
        ScienceMenuInfo = buttons["ScienceMenu"]

        science_names = []
        science_defaults = []
        for idx, button in enumerate(ScienceMenuInfo):
            science_names.append(button[0] or f"science_{idx}")
            science_defaults.append(bool(button[8]))

        persistent_unlocks = state_list_from_save(
            saved_science, science_names, science_defaults)

        id = 0
        for button in ScienceMenuInfo:
            label = button[0] or "Unnamed Research"
            badge_cfg = BadgeConfig(
                text=str(button[6]),
                texture="resources/gui/wood_circle.png",
                anchor_x="right",
                anchor_y="bottom",
                padding_x=10,
                padding_y=6,
                offset_x=30,
                offset_y=40,
                text_scale=0.6,
                text_margin=8,
            )
            start_button = CustomUIFlatButton(
                self.Alphabet_Textures,
                click_sound=self.click_sound,
                text=label,
                width=160,
                height=54,
                x=0,
                y=50,
                text_margin=12,
                text_offset_x=0,
                text_offset_y=0,
                offset_x=0,
                offset_y=0,
                badge=badge_cfg,
            )
            start_button.on_click = self.on_buttonclick
            wrapper = UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
                                     child=start_button, align_x=button[1], align_y=button[2])
            wrapper.true_x = button[1]

            wrapper.description = button[4]
            wrapper.identity = id
            if saved and self.game_view.science_list[id]:
                start_button.unlocked = self.game_view.science_list[id]
                convert_button(start_button, self.gold_button_texture)
            else:
                start_button.unlocked = False

            start_button.affect = button[5]
            start_button.cost = button[6]
            if start_button.unlocked:
                start_button.set_badge_text(None)
            else:
                start_button.set_badge_text(str(button[6]))

            button_names = button[3]

            start_button.connections = [ScienceMenuInfo.index(
                button2) for button2 in ScienceMenuInfo if button2[0] in button_names]

            start_button.wrapper = wrapper
            self.uimanager.add(wrapper)
            self.science_buttons.append(wrapper)

            start_button.locked = False
            if not persistent_unlocks[id]:
                start_button._style = {
                    "bg_color": arcade.color.DIM_GRAY, "font_color": arcade.color.BLACK}
                convert_button(start_button, self.silver_button_texture)
                start_button.locked = True
                start_button.set_badge_text(None)

            for i in start_button.connections:
                endx = ScienceMenuInfo[i][1]+370
                endy = ScienceMenuInfo[i][2]+250

                line = create_line(
                    button[1]+370, button[2]+250, endx, endy, (120, 100, 100, 200), line_width=5)
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
        self.game_view.science_list = [
            button.child.unlocked for button in self.science_buttons]

        self.game_view.uimanager.enable()
        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)
        self.uimanager.disable()
        show_view_resized(self.window, self.game_view)

    def on_buttonclick(self, event):
        if self.button == 4:
            window = arcade.get_window()
            string = "Not Unlocked. "
            if event.source.locked:
                string = "Locked.   Unlock in Progress Tree. "
            elif event.source.unlocked:
                string = "Unlocked. "

            text = UpdatingText(string, self.Alphabet_Textures, 1, scale=1, center_x=event.source.wrapper.align_x +
                                window.width/2, center_y=event.source.wrapper.align_y+window.height/2)
            self.texts.append(text)
            return

        self.handle_cost(event.source)

    def handle_cost(self, source):
        window = arcade.get_window()
        x, y = source.wrapper.align_x+window.width / \
            2, source.wrapper.align_y+window.height/2

        if source.locked:
            text = UpdatingText(
                f"Locked", self.Alphabet_Textures, .5, scale=1, center_x=x, center_y=y)
            self.texts.append(text)
            return
        elif source.unlocked:
            text = UpdatingText(
                f"Alerady Unlocked", self.Alphabet_Textures, .5, scale=1, center_x=x, center_y=y)
            self.texts.append(text)
            return

        cost = self.check_backwards(source)
        if cost > self.game_view.science:
            science_missing = cost-self.game_view.science
            text = UpdatingText(f"missing {floor(science_missing*100)/100} science",
                                self.Alphabet_Textures, .5, scale=1, center_x=x, center_y=y)
            self.texts.append(text)
            return
        self.game_view.science -= cost
        self.unlock_backwards(source)
        self.text.update_text(f"{round(self.game_view.science*10)/10} science", self.Alphabet_Textures,
                              scale=1, center_x=-400+window.width/2, center_y=200+window.height/2)

        self.handle_affect(source)

    def handle_affect(self, source):

        for _type, amount in source.affect.items():
            try:
                vars(self.game_view)[_type] += amount/100
            except:
                self.game_view.unlocked[_type] = True

        convert_button(source, self.gold_button_texture)
        source.unlocked = True
        source.set_badge_text(None)

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

    def on_show_view(self):
        super().on_show_view()
        arcade.set_background_color(PARCHMENT_COLOR)

        reset_window_viewport(self.window)

    def on_draw(self):
        """ Draw this view """
        width = getattr(arcade.get_window(), "width", 0) or self.window.width
        height = getattr(arcade.get_window(), "height", 0) or self.window.height
        self.clear(PARCHMENT_COLOR)
        draw_rect_filled(XYWH(width / 2, height / 2, width, height), PARCHMENT_COLOR)
        self.background.draw()
        self.christmas_background.draw()
        self.lineList.draw()
        self.uimanager.draw()
        for wrapper in self.science_buttons:
            child = getattr(wrapper, "child", None)
            if child and hasattr(child, "draw_badge_overlay"):
                child.draw_badge_overlay()
        for text in self.texts:
            text.draw()
        if self.tooltip_visible:
            self.tooltip.draw()

    def on_mouse_motion(self, x, y, dx, dy):
        """
        Called whenever the mouse moves.
        """
        self.mouse_x = x
        self.mouse_y = y
        self.update_science_tooltip(x, y)

    def update_science_tooltip(self, x, y):
        collided = False
        for button in self.science_buttons:
            child = getattr(button, "child", None)
            rect = child.rect if child else button.rect
            if not (rect.left <= x <= rect.right and rect.bottom <= y <= rect.top):
                continue
            center_x = (rect.left + rect.right) / 2
            text = button.description
            provisional_center_y = rect.top + 20
            self.tooltip.update_text(
                text,
                self.Alphabet_Textures,
                center_x=center_x,
                center_y=provisional_center_y,
                width=260,
                vertical_align='top',
            )
            text_height = getattr(self.tooltip, '_content_height', 0)
            desired_top = rect.top + 12
            desired_center_y = desired_top - text_height / 2
            self.tooltip.set_position(center_x, desired_center_y)
            self.tooltip_visible = True
            collided = True
            break
        if not collided:
            self.tooltip_visible = False

    def on_update(self, delta_time):

        if self.pressed_a and self.x + 50 < -self.science_buttons[0].true_x:
            self.x += 1000*delta_time
            self.lineList.move(1000*delta_time, 0)
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
        self._previous_background_color = getattr(
            arcade.get_window(), "background_color", arcade.color.BLACK)
        self._set_background(arcade.color.BEIGE)
        reset_window_viewport(self.window)
        game_view.uimanager.disable()
        self.game_view = game_view
        self.set_up()

        window = arcade.get_window()
        self.on_resize(window.width, window.height)

    def _set_background(self, color):
        arcade.set_background_color(color)
        self.window.background_color = color

    def set_up(self):

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        self.click_sound = self.game_view.click_sound

        base_width, base_height = 1440, 900
        scale_factor = min(self.window.width / base_width,
                           self.window.height / base_height)
        self.background = arcade.Sprite(
            "resources/gui/Large Bulletin.png",
            center_x=self.window.width / 2,
            center_y=self.window.height / 2,
            scale=3.6 * scale_factor,
        )
        self.christmas_background = arcade.Sprite(
            "resources/gui/ChristmasOverlay.png",
            center_x=self.window.width / 2,
            center_y=self.window.height / 2,
            scale=max(self.window.width / 5001, self.window.height / 3334),
        )

        textures = load_texture_grid(
            "resources/gui/Wooden Font.png", 14, 24, 12, 71, margin=1)
        self.Alphabet_Textures = {" ": None}
        string = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyz.:,%/-+_'"
        for i in range(len(string)):
            self.Alphabet_Textures[string[i]] = textures[i]
        window = arcade.get_window()

        menu_button = CustomUIFlatButton(
            self.Alphabet_Textures,
            click_sound=self.click_sound,
            text="Back",
            width=220, height=54
        )
        menu_button.on_click = self.exit
        back_wrapper = UIAnchorWidget(
            anchor_x="left", anchor_y="top", child=menu_button, align_x=20, align_y=-20)
        self.uimanager.add(back_wrapper)

        self.texts = []
        self.speed = 1
        self._pending_slider_refresh = False
        self._slider_wrappers: list[UIAnchorWidget] = []
        ui_slider = CustomUISlider(
            max_value=200, value=self.game_view.audio_type_vols["Overall"]*100, width=360, height=35)
        label = CustomTextSprite(
            f"Master Volume: {ui_slider.value:.0f}%",
            self.Alphabet_Textures,
            center_x=window.width/2-170,
            center_y=window.height/2+130,
            width=450,
            text_margin=18,
        )

        @ui_slider.event()
        def on_change(event: UIOnChangeEvent):
            label.update_text(
                f"Master Volume: {ui_slider.value:.0f}%",
                self.Alphabet_Textures,
                center_x=window.width/2-170,
                center_y=window.height/2+130,
            )
            self.speed = ui_slider.value
            self.game_view.audio_type_vols["Overall"] = ui_slider.value/100
            self.game_view.update_audio()

        slider = UIAnchorWidget(
            child=ui_slider, align_x=140, align_y=130, anchor_x="center", anchor_y="center")
        self.uimanager.add(slider)
        self.texts.append(label)
        self._slider_wrappers.append(slider)

        ui_slider1 = CustomUISlider(max_value=200, value=max(
            1, self.game_view.audio_type_vols["UI"]*100) if self.game_view.audio_type_vols["UI"] else 100, width=360, height=35)
        label1 = CustomTextSprite(
            f"UI Volume: {ui_slider1.value:.0f}%",
            self.Alphabet_Textures,
            center_x=window.width/2-170,
            center_y=window.height/2+30,
            width=450,
            text_margin=18,
        )

        @ui_slider1.event()
        def on_change(event: UIOnChangeEvent):
            label1.update_text(
                f"UI Volume: {ui_slider1.value:.0f}%",
                self.Alphabet_Textures,
                center_x=window.width/2-170,
                center_y=window.height/2+30,
            )
            self.speed = ui_slider1.value

            self.game_view.audio_type_vols["UI"] = ui_slider1.value/100
            self.game_view.update_audio()

        slider = UIAnchorWidget(
            child=ui_slider1, align_x=140, align_y=30, anchor_x="center", anchor_y="center")
        self.uimanager.add(slider)
        self.texts.append(label1)
        self._slider_wrappers.append(slider)

        ui_slider2 = CustomUISlider(max_value=200, value=max(
            1, self.game_view.audio_type_vols["Background"]*100) if self.game_view.audio_type_vols["Background"] else 100, width=360, height=35)
        label2 = CustomTextSprite(
            f"Background Volume: {ui_slider2.value:.0f}%",
            self.Alphabet_Textures,
            center_x=window.width/2-170,
            center_y=window.height/2-70,
            width=450,
            text_margin=18,
        )

        @ui_slider2.event()
        def on_change(event: UIOnChangeEvent):
            label2.update_text(
                f"Background Volume: {ui_slider2.value:.0f}%",
                self.Alphabet_Textures,
                center_x=window.width/2-170,
                center_y=window.height/2-70,
            )
            self.speed = ui_slider2.value

            self.game_view.audio_type_vols["Background"] = ui_slider2.value/100
            self.game_view.update_audio()

        slider = UIAnchorWidget(child=ui_slider2, align_x=140,
                                align_y=-70, anchor_x="center", anchor_y="center")
        self.uimanager.add(slider)
        self.texts.append(label2)
        self._slider_wrappers.append(slider)

        # Defer surface refresh to the next frame so layout has finalized
        self._pending_slider_refresh = True
        arcade.schedule_once(self._refresh_slider_surfaces, 0)

    def on_resize(self, width: int, height: int):
        base_width, base_height = 1440, 900
        scale_factor = min(width / base_width, height / base_height)
        self.background.scale = 3.6 * scale_factor
        self.background.center_x = width / 2
        self.background.center_y = height / 2

        self.christmas_background.scale = max(width/5001, height/3334)
        self.christmas_background.position = width/2, height/2

        y = height/2 + 130
        for label in self.texts:
            label.update_text(label.text, self.Alphabet_Textures,
                              center_x=width/2-170, center_y=y)
            y -= 100
        return super().on_resize(width, height)

    def on_draw(self):
        self.clear(self._background_color)
        self.background.draw()
        self.christmas_background.draw()
        for text in self.texts:
            text.draw()

        self.uimanager.draw()

    def on_mouse_drag(self, x: float, y: float, dx: float, dy: float, _buttons: int, _modifiers: int):
        return super().on_mouse_drag(x, y, dx, dy, _buttons, _modifiers)

    def _refresh_slider_surfaces(self, dt):
        for wrapper in getattr(self, "_slider_wrappers", []):
            wrapper.trigger_full_render()
        self._pending_slider_refresh = False

    def exit(self, event):
        if getattr(self, "_pending_slider_refresh", False):
            arcade.unschedule(self._refresh_slider_surfaces)
            self._pending_slider_refresh = False
        self.game_view.Christmas_music.true_volume = self.game_view.Christmas_music.volume
        self.game_view.Background_music.true_volume = self.game_view.Background_music.volume

        self.uimanager.disable()
        self.game_view.uimanager.enable()
        if hasattr(self, "_previous_background_color"):
            self._set_background(self._previous_background_color)
        show_view_resized(self.window, self.game_view)


class ShowMenu(arcade.View):
    def __init__(self, game_view):
        super().__init__()
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)
        reset_window_viewport(self.window)
        game_view.uimanager.disable()
        self.game_view = game_view
        self.set_up()

    def set_up(self):

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        start_button = arcade.gui.UIFlatButton(
            text="Menu", width=100, x=50, y=50)
        start_button.on_click = self.exit
        wrapper = UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
                                 child=start_button, align_x=300, align_y=200)
        self.uimanager.add(wrapper)

        game = vars(self.game_view)
        y = 450
        self.texts = arcade.SpriteList(use_spatial_hash=True)
        for item in items_to_show:
            self.texts.append(arcade.create_text_sprite(
                f"{game[item]} {item}", 0, y, arcade.color.WHITE, font_size=36))
            y -= 50

    def on_draw(self):
        self.clear()
        for text in self.texts:
            text.draw()
        self.uimanager.draw()

    def on_mouse_drag(self, x: float, y: float, dx: float, dy: float, _buttons: int, _modifiers: int):
        return super().on_mouse_drag(x, y, dx, dy, _buttons, _modifiers)

    def exit(self, event):
        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)
        self.uimanager.disable()
        self.game_view.uimanager.enable()
        show_view_resized(self.window, self.game_view)


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
        reset_window_viewport(self.window)

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        self.lineList = ShapeElementList()

    def load(self):
        start_button = arcade.gui.UIFlatButton(
            text="Menu", width=100, x=50, y=50)
        start_button.on_click = self.exit
        wrapper = UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
                                 child=start_button, align_x=300, align_y=200)
        self.uimanager.add(wrapper)
        wrapper.description = "None"

        with open("textInfo.json", "r") as read_file:
            menu_config = json.load(read_file)
        for node in menu_config["Selectables"]:
            align_x, align_y, label, description, requirements, placement = node
            length = len(label) * 11
            start_button = arcade.gui.UIFlatButton(
                text=label, width=length, x=0, y=0)
            start_button.on_click = self.on_buttonclick
            wrapper = UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
                                     child=start_button, align_x=align_x, align_y=align_y)

            start_button.type = label
            wrapper.description = description
            start_button.requirements = requirements
            start_button.placement = placement
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
        show_view_resized(self.window, self.game_view)

    def on_buttonclick(self, event):
        source = event.source
        if not isinstance(source, arcade.gui.UIFlatButton):
            return

        if self.game_view.unlocked[source.type]:
            self.handle_affect(source)

    def handle_affect(self, source: arcade.gui.UIFlatButton):
        self.game_view.object = source.type
        self.game_view.requirements = source.requirements
        self.game_view.object_placement = source.placement
        self.game_view._force_preview_refresh()

    def on_show_view(self):
        super().on_show_view()
        arcade.set_background_color(PARCHMENT_COLOR)

        reset_window_viewport(self.window)

    def on_draw(self):
        """ Draw this view """
        self.clear()

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
        reset_window_viewport(self.window)

        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        self.lineList = ShapeElementList()
        self.image = arcade.Sprite()

        self.updating_texts = []

        window = arcade.get_window()
        self.on_resize(window.width, window.height)

        self.image = None

    def load(self):
        buttons = self.building.trainable
        self.ui_texts = arcade.SpriteList()

        start_button = CustomUIFlatButton(
            self.game_view.Alphabet_Textures, click_sound=self.game_view.click_sound, text="Menu", width=140, height=50)
        start_button.on_click = self.exit
        wrapper = UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
                                 child=start_button, align_x=0, align_y=0)
        self.uimanager.add(wrapper)
        wrapper.description = "None"

        x, y = 50, 0
        for button in buttons:
            start_button = CustomUIFlatButton(
                self.game_view.Alphabet_Textures, click_sound=self.game_view.click_sound, text=button, width=140, height=50)
            start_button.on_click = self.on_selectionclick
            wrapper = UIAnchorWidget(anchor_x="left", anchor_y="top",
                                     child=start_button, align_x=x, align_y=y)
            start_button.wrapper = wrapper
            start_button.string = button
            self.uimanager.add(wrapper)
            y -= 75

    def on_resize(self, width: int, height: int):
        resize_ui_manager(self, width, height)
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
                self.image.destroy(self.game_view, count_population=False)
            else:
                self.image.destroy(self.game_view)
            self.image = None
        arcade.set_background_color(arcade.csscolor.CORNFLOWER_BLUE)
        self.game_view.uimanager.enable()
        self.uimanager.disable()
        del self.image
        del self.lineList
        show_view_resized(self.window, self.game_view)

    def on_selectionclick(self, event):

        self.ui_texts.clear()
        self.string = event.source.string
        if self.title is not None:
            self.uimanager.remove(self.title)
            self.uimanager.remove(self.description)

        self.title = arcade.gui.UITextArea(x=250, y=420, width=300, height=75, scroll_speed=10,
                                           text=self.string, font_size=48, text_color=(0, 0, 0, 255))  # append(arcade.create_text_sprite(self.string, 200, 400, arcade.color.BLACK, font_size=48))
        self.title.fit_content()
        self.uimanager.add(self.title)

        string = "Costs:"
        for key, val in requirements[self.string].items():
            string += f" {val} {key},"
        self.description = arcade.gui.UITextArea(x=250, y=180, width=400, height=60, scroll_speed=10, font_size=24,
                                                 text=descriptions[self.string] +
                                                 f"Time: {trainingtimes[self.string]}           "+string,
                                                 text_color=(0, 0, 0, 255))
        self.uimanager.add(self.description)
        self.description.fit_content()

        self.button = arcade.gui.UIFlatButton(
            text="Train", width=100, x=50, y=50)
        self.button.on_click = self.on_buttonclick
        self.button.string = self.string
        self.button.cost = requirements[self.string]
        wrapper = UIAnchorWidget(anchor_x="center_x", anchor_y="center_y",
                                 child=self.button, align_x=0, align_y=-200)
        self.button.wrapper = wrapper
        self.uimanager.add(wrapper)

        if self.image:
            if isinstance(self.image, Person):
                self.image.destroy(self.game_view, count_population=False)
            else:
                self.image.destroy(self.game_view)
            self.image = None

        self.image = objects[self.string](self.game_view, 400, 320)
        self.image.scale = 4

    def on_buttonclick(self, event):
        source = event.source
        if self.game_view.unlocked[source.string]:
            self.handle_affect(source)
        else:
            window = arcade.get_window()
            text = UpdatingText("Not Unlocked", self.game_view.Alphabet_Textures,
                                1, width=100, center_x=window.width/2, center_y=window.height/2-200)
            self.updating_texts.append(text)

    def handle_affect(self, source: arcade.gui.UIFlatButton):
        if len(self.building.list_of_people) == 0:
            text = UpdatingText(
                "No People to train",
                self.game_view.Alphabet_Textures,
                1,
                width=100,
                center_x=source.wrapper.child.center_x,
                center_y=source.wrapper.child.center_y,
            )
            self.updating_texts.append(text)
            return
        variables = vars(self.game_view)
        missing = ""
        for key, val in source.cost.items():
            if variables[key] < val:
                if missing:
                    missing += ", "
                else:
                    missing = "Missing: "
                missing += f"{val-variables[key]} {key}"
        if missing:
            text = UpdatingText(
                missing,
                self.game_view.Alphabet_Textures,
                1,
                width=100,
                center_x=source.wrapper.child.center_x,
                center_y=source.wrapper.child.center_y,
            )
            self.updating_texts.append(text)
            return

        for person in self.building.list_of_people:
            if person.advancement != None:
                continue
            person.advancement = source.string
            person.trainingtime = 0

            for key, val in source.cost.items():
                variables[key] -= val
            break

    def on_update(self, delta_time: float):
        for text in self.updating_texts:
            text.update(delta_time)
        return super().on_update(delta_time)

    def on_show_view(self):
        super().on_show_view()
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)

        reset_window_viewport(self.window)

    def on_draw(self):
        """ Draw this view """
        self.clear()

        self.uimanager.draw()
        self.ui_texts.draw()
        if self.image:
            self.image.draw()
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
        with open("resources/GameBase.json", "r") as read_file:
            menu_config = json.load(read_file)

        return [bool(node[8]) for node in menu_config["ScienceMenu"]]


def main():
    """Main method"""
    window = arcade.Window(1440, 900, "SantaFest Destiny", resizable=True)
    StartMenu = startMenu()
    show_view_resized(window, StartMenu)
    arcade.run()


if __name__ == "__main__":
    main()
