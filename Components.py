import arcade, math, itertools

from dataclasses import dataclass
from typing import Optional, Tuple, Union, Literal

from pyglet.event import EVENT_HANDLED, EVENT_UNHANDLED

from arcade import load_spritesheet as _arcade_load_spritesheet, Rect
from arcade.texture import Texture
from arcade.gui import (
    UIWidget,
    Surface,
    UIEvent,
    UIMouseMovementEvent,
    UIMouseDragEvent,
    UIMousePressEvent,
    UIMouseReleaseEvent,
)
from arcade.gui.events import UIOnChangeEvent, UIOnClickEvent
from arcade.gui import Property, bind
from arcade.types import Color, LBWH

from pathlib import Path
import time
import pyglet.media as media


trainingtimes = {"Bad Gifter":5, "Bad Reporter":10}
movement = {0:1, 1:2, 2:1}

if not hasattr(arcade.Sprite, "draw"):
    def _compat_sprite_draw(self):
        draw_list = getattr(self, "_compat_draw_list", None)
        if draw_list is None:
            draw_list = arcade.SpriteList()
            draw_list.append(self)
            self._compat_draw_list = draw_list
        draw_list.draw()

    arcade.Sprite.draw = _compat_sprite_draw  # type: ignore[attr-defined]

def reset_window_viewport(
    window: Optional[arcade.Window] = None,
    *,
    left: float = 0.0,
    bottom: float = 0.0,
    width: Optional[float] = None,
    height: Optional[float] = None,
) -> None:
    win = window or arcade.get_window()
    default_width = getattr(win, "width", 0) or getattr(win, "size", (0, 0))[0] or 1
    default_height = getattr(win, "height", 0) or getattr(win, "size", (0, 0))[1] or 1

    viewport_width = width if width is not None else default_width
    viewport_height = height if height is not None else default_height

    if viewport_width <= 0:
        viewport_width = default_width or 1
    if viewport_height <= 0:
        viewport_height = default_height or 1

    win.viewport = (left, bottom, viewport_width, viewport_height)


def set_scroll_viewport(
    left: float,
    bottom: float,
    width: float,
    height: float,
    window: Optional[arcade.Window] = None,
) -> None:
    reset_window_viewport(
        window,
        left=left,
        bottom=bottom,
        width=width,
        height=height,
    )

def load_texture_grid(
    path: str,
    width: int,
    height: int,
    columns: int,
    count: int,
    margin: Union[int, Tuple[int, int, int, int]] = 0,
    *,
    hit_box_algorithm=None,
):
    sheet = _arcade_load_spritesheet(path)
    image = sheet.image

    if isinstance(margin, tuple):
        if len(margin) != 4:
            raise ValueError("margin tuple must contain four values: (left, right, bottom, top)")
        margin_left, margin_right, margin_bottom, margin_top = margin
    else:
        margin_left = margin_right = margin_bottom = margin_top = margin

    spacing_x = margin_right
    spacing_y = margin_bottom

    textures = []
    rows = max(1, (count + columns - 1) // columns)

    texture_index = 0
    for row in range(rows):
        for column in range(columns):
            if texture_index >= count:
                break

            x = margin_left + column * (width + spacing_x)
            y = margin_top + row * (height + spacing_y)

            cropped = image.crop((x, y, x + width, y + height))
            texture = Texture(cropped, hit_box_algorithm=hit_box_algorithm)
            texture.file_path = Path(path)
            textures.append(texture)
            texture_index += 1

    return textures

def get_closest_sprite(pos, sprite_list):
    lowest_dist = float("inf")
    save = None
    for sprite in sprite_list:
        dist = get_dist(pos, sprite.position)
        if dist < lowest_dist:
            lowest_dist = dist
            save = sprite
    return save, lowest_dist
def rotation(x, y, x2, y2, angle=0, max_turn=5):
    x_diff = x2 - x
    y_diff = y2 - y
    target_angle_radians = math.atan2(y_diff, x_diff)
    if target_angle_radians < 0:
        target_angle_radians += 2 * math.pi
    actual_angle_radians = math.radians(angle)
    rot_speed_radians = math.radians(max_turn)
        # What is the difference between what we want, and where we are?
    angle_diff_radians = target_angle_radians - actual_angle_radians
        # Figure out if we rotate clockwise or counter-clockwise
    if abs(angle_diff_radians) <= rot_speed_radians:
        actual_angle_radians = target_angle_radians
        clockwise = None
    elif angle_diff_radians > 0 and abs(angle_diff_radians) < math.pi:
        clockwise = False
    elif angle_diff_radians > 0 and abs(angle_diff_radians) >= math.pi:
        clockwise = True
    elif angle_diff_radians < 0 and abs(angle_diff_radians) < math.pi:
        clockwise = True
    else:
        clockwise = False

    # Rotate the proper direction if needed
    if actual_angle_radians != target_angle_radians and clockwise:
        actual_angle_radians -= rot_speed_radians
    elif actual_angle_radians != target_angle_radians:
        actual_angle_radians += rot_speed_radians

        # Keep in a range of 0 to 2pi
    if actual_angle_radians > 2 * math.pi:
        actual_angle_radians -= 2 * math.pi
    elif actual_angle_radians < 0:
        actual_angle_radians += 2 * math.pi

    return math.degrees(actual_angle_radians)


def heading_towards(x: float, y: float, x2: float, y2: float) -> float:
    """Return instant heading in degrees from (x, y) to (x2, y2)."""
    return math.degrees(math.atan2(y2 - y, x2 - x))


def set_sprite_motion(sprite: arcade.Sprite, heading_degrees: float, speed: float) -> None:
    radians = math.radians(heading_degrees)
    sprite._motion_dx = math.cos(radians) * speed
    sprite._motion_dy = math.sin(radians) * speed


def advance_sprite(sprite: arcade.Sprite, delta_time: float) -> None:
    dx = getattr(sprite, '_motion_dx', 0.0)
    dy = getattr(sprite, '_motion_dy', 0.0)
    if dx or dy:
        sprite.center_x += dx * delta_time
        sprite.center_y += dy * delta_time


def get_dist(pos, pos2):
    return math.hypot(pos[0] - pos2[0], pos[1] - pos2[1])
def sprites_in_range(range, pos, sprite_list):
    return [sprite for sprite in sprite_list if get_dist(pos, sprite.position) < range and sprite.position != pos]
def convert_button(
    button: "CustomUIFlatButton",
    button_texture: Union[str, arcade.Texture],
    hovered_texture: Optional[Union[str, arcade.Texture]] = None,
    pressed_texture: Optional[Union[str, arcade.Texture]] = None,
) -> None:
    def _ensure_texture(tex: Union[str, arcade.Texture]) -> arcade.Texture:
        if isinstance(tex, arcade.Texture):
            return tex
        return arcade.load_texture(tex)

    base_texture = _ensure_texture(button_texture)
    hovered = _ensure_texture(hovered_texture or button_texture)
    pressed = _ensure_texture(pressed_texture or hovered_texture or button_texture)

    desired_width = button.width
    desired_height = button.height

    texture_width = base_texture.width or 1
    texture_height = base_texture.height or 1

    scale_x = desired_width / texture_width
    scale_y = desired_height / texture_height
    sprite_scale = min(scale_x, scale_y)

    for sprite, texture in (
        (button.sprite, base_texture),
        (button.hovered_sprite, hovered),
        (button.pressed_sprite, pressed),
    ):
        sprite.texture = texture
        sprite.scale = sprite_scale


@dataclass
class BadgeConfig:
    text: str = ""
    texture: str = "resources/gui/wood_circle.png"
    scale: float = 0.12
    anchor_x: Literal["left", "center", "right"] = "right"
    anchor_y: Literal["top", "center", "bottom"] = "bottom"
    offset_x: float = 0.0
    offset_y: float = 0.0
    padding_x: float = 6.0
    padding_y: float = 6.0
    text_scale: float = 0.7
    text_margin: float = 10.0


_ANCHOR_X = {"left": -1, "center": 0, "right": 1}
_ANCHOR_Y = {"bottom": -1, "center": 0, "top": 1}

class AnimationPlayer(object):
    def __init__(self, timetoupdate, index=0) -> None:
        self.time = 0
        self.index = index
        self.timetoupdate = timetoupdate
    def updateAnim(self, deltatime, maxLen):
        self.time += deltatime
        if self.time >= self.timetoupdate:
            self.index += 1
            if self.index >= maxLen:
                self.index = 0
            self.time -= self.timetoupdate
            return self.index
        return None
class Sound(arcade.Sound):
    """Arcade ``Sound`` wrapper that tolerates load/play failures and tracks volume."""

    def __init__(self, file_name: Union[str, Path], streaming: bool = False):
        try:
            super().__init__(file_name, streaming)
        except Exception:
            # Keep a stub so higher-level code doesn't crash; playback will just no-op
            self.source = None
        self.player = None
        self.volume = 1.0

    def set_volume(self, volume: float) -> None:
        volume = max(0.0, volume)
        self.volume = volume
        if self.player:
            try:
                self.player.volume = volume
            except Exception:
                self.player = None

    def play(self, pan: float = 0, loop: bool = False) -> None:  # type: ignore[override]
        try:
            self.player = super().play(self.volume, pan, loop)
        except Exception:
            self.player = None

_sound_cooldowns: dict[tuple[str, str], float] = {}
_sound_cache: dict[str, Optional[arcade.Sound]] = {}
_active_sound_players: dict[str, list] = {}
_ACTIVE_SOUND_LIMIT = 8


def _get_sound(file: str) -> Optional[arcade.Sound]:
    if file in _sound_cache:
        return _sound_cache[file]
    try:
        sound = arcade.load_sound(file)
    except Exception as exc:
        logging.getLogger(__name__).warning("Failed to load sound %s: %s", file, exc)
        _sound_cache[file] = None
        return None
    _sound_cache[file] = sound
    return sound


def SOUND(file, volume, dist, volume_map=None, sound_type="UI", cooldown=0.1):
    """Play a one-shot sound with simple distance attenuation and global volume support."""
    now = time.time()
    key = (file, sound_type)
    last = _sound_cooldowns.get(key, 0.0)
    if cooldown and now - last < cooldown:
        return None

    sound = _get_sound(file)
    if sound is None:
        return None

    if dist > 1000:
        attenuated = 0.0
    elif dist != 0:
        attenuated = volume * (50 / dist)
    else:
        attenuated = volume

    if volume_map:
        overall = volume_map.get("Overall", 1.0)
        type_scale = volume_map.get(sound_type, 1.0)
        attenuated *= overall * type_scale

    attenuated = max(0.0, min(attenuated, 1.0))

    if attenuated <= 0.0:
        return None

    players = _active_sound_players.setdefault(file, [])
    players = [p for p in players if getattr(p, 'playing', False)]
    if len(players) >= _ACTIVE_SOUND_LIMIT:
        _active_sound_players[file] = players
        return None

    try:
        player = arcade.play_sound(sound, volume=attenuated)
    except Exception as exc:
        logging.getLogger(__name__).warning("Error playing sound '%s': %s", file, exc)
        return None

    players.append(player)
    _active_sound_players[file] = players
    _sound_cooldowns[key] = now
    return player

class Handle_Christmas(object):
    def update(self):
        delta_time = 0
        if self.timer >= 75:
            self.timer -= 75
        if self.timer >= 60:
            t = self.timer - 45
            num = max(0.0, 15 - t / 15)
            self.Christmas_music.set_volume(self.Christmas_music.true_volume * num)
            self.Background_music.set_volume(self.Background_music.true_volume * max(0.0, t / 15))
        elif self.timer >= 45:
            t = self.timer - 45
            num = max(0.0, 15 - t / 15)
            self.Christmas_music.set_volume(self.Christmas_music.true_volume * max(0.0, t / 15))
            self.Background_music.set_volume(self.Background_music.true_volume * num)

class StateMachieneState(object):
    def __init__(self, state, accessable) -> None:
        self.state = state
        self.can_go_to = accessable
class StateMachiene(object):
    def __init__(self, state, states) -> None:
        
        self.states = []
        for i in states:
            Node = StateMachieneState(i)
            self.states.append(Node)
        self.state = state
class Entity(object):
    def __init__(self) -> None:
        pass

class HealthBar:
    """
    Represents a bar which can display information about a sprite.

    :param MyGame Game: Game
    :param Tuple[float, float] position: The initial position of the bar.
    :param arcade.Color full_color: The color of the bar.
    :param arcade.Color background_color: The background color of the bar.
    :param int width: The width of the bar.
    :param int height: The height of the bar.
    :param int border_size: The size of the bar's border.
    """

    def __init__(
        self,
        game,
        position: Tuple[float, float] = (0, 0),
        full_color: Color = arcade.color.GREEN,
        background_color: Color = arcade.color.BLACK,
        width: int = 40,
        height: int = 4,
        border_size: int = 4,
    ) -> None:
        # Store the reference to the owner and the sprite list


        # Set the needed size variables
        self._box_width: int = width
        self._box_height: int = height
        self._half_box_width: int = self._box_width // 2
        self._center_x: float = 0.0
        self._center_y: float = 0.0
        self._fullness: float = 0.0

        # Create the boxes needed to represent the indicator bar
        self._background_box: arcade.SpriteSolidColor = arcade.SpriteSolidColor(
            self._box_width + border_size,
            self._box_height + border_size,
            color=background_color,
        )
        self._full_box: arcade.SpriteSolidColor = arcade.SpriteSolidColor(
            self._box_width,
            self._box_height,
            color=full_color,
        )
        game.health_bars.append(self._background_box)
        game.health_bars.append(self._full_box)

        # Set the fullness and position of the bar
        self.fullness: float = 1.0
        self.visible: bool = True
        self.position: Tuple[float, float] = position
    def remove_from_sprite_lists(self):
        self._background_box.remove_from_sprite_lists()
        self._full_box.remove_from_sprite_lists()

    @property
    def background_box(self) -> arcade.SpriteSolidColor:
        """Returns the background box of the indicator bar."""
        return self._background_box

    @property
    def full_box(self) -> arcade.SpriteSolidColor:
        """Returns the full box of the indicator bar."""
        return self._full_box

    @property
    def fullness(self) -> float:
        """Returns the fullness of the bar."""
        return self._fullness

    @fullness.setter
    def fullness(self, new_fullness: float) -> None:
        """Sets the fullness of the bar."""
        # Check if new_fullness if valid
        if 0.0 > new_fullness:
            new_fullness = 0
        elif 1.0 < new_fullness:
            new_fullness = 1

        # Set the size of the bar
        self._fullness = new_fullness

        self.full_box.width = self._box_width * new_fullness
        self.full_box.left = self._center_x - (self._box_width // 2)
    
    @property
    def visible(self) -> float:
        """Returns the visibility"""
        return getattr(self, "_visible", True)
    @visible.setter
    def visible(self, visible) -> None:
        self._visible = bool(visible)
        self._full_box.visible = self._visible
        self._background_box.visible = self._visible

    @property
    def position(self) -> Tuple[float, float]:
        """Returns the current position of the bar."""
        return self._center_x, self._center_y

    @position.setter
    def position(self, new_position: Tuple[float, float]) -> None:
        """Sets the new position of the bar."""
        # Check if the position has changed. If so, change the bar's position
        if new_position != self.position:
            new_position = new_position[0], new_position[1]-20
            self._center_x, self._center_y = new_position
            self.background_box.position = new_position
            self.full_box.position = new_position

            # Make sure full_box is to the left of the bar instead of the middle
            self.full_box.left = self._center_x - (self._box_width // 2)
class CustomTextSprite(object):
    def __init__(self, string, Alphabet_Textures, scale=1, 
                 center_x=0, center_y = 0, 
                 text_scale=1, text_margin=16, width=100, height = 40,  Background_offset_x=0, Background_offset_y=0, Background_scale=1, Background_Texture=None, vertical_align:"Literal['center','top','bottom']"='center') -> None:
        super().__init__()
        self.Sprite_List = arcade.SpriteList()
        self.background_texture = Background_Texture
        self.background_offset_x = Background_offset_x
        self.background_offset_y = Background_offset_y
        self.background_scale = Background_scale
        self._background_base_width: float = 0
        self._background_base_height: float = 0

        self.text_scale = text_scale
        self.text_margin = text_margin
        self.width = width
        self.height = height
        self.scale = scale
        self.center_x = center_x
        self.center_y = center_y
        self.vertical_align = vertical_align
        self._content_height: float = 0.0
        self._background_height: float = 0.0
        self._content_height: float = 0.0
        self._background_height: float = 0.0

        self._background_height: float = 0.0
        self.Background_Sprite: Optional[arcade.Sprite]
        if Background_Texture:
            self.Background_Sprite = arcade.Sprite(
                Background_Texture,
                center_x=center_x + Background_offset_x,
                center_y=center_y + Background_offset_y,
                scale=Background_scale,
            )
            self._background_base_width = self.Background_Sprite.width
            self._background_base_height = self.Background_Sprite.height
        else:
            self.Background_Sprite = None

        self.update_text(string, Alphabet_Textures)
        
    def update_text(self, text, Alphabet_Textures, scale=None, 
                 center_x=None, center_y=None, 
                 text_margin=None, width=None, height=None, vertical_align=None):
        self.text = text
        self.Sprite_List.clear()
        if not text:
            return
        words = text.split(' ')
        if scale is not None:
            self.scale = scale
        if center_x is not None:
            self.center_x = center_x
        if center_y is not None:
            self.center_y = center_y
        if text_margin is not None:
            self.text_margin = text_margin
        if width is not None:
            self.width = width
        if height is not None:
            self.height = height
        if vertical_align is not None:
            self.vertical_align = vertical_align

        available_width = self.width if self.width > 0 else float("inf")
        glyph_advance = max(14 * self.scale * 0.8, 1)
        line_height = glyph_advance * 2.2
        space_width = glyph_advance

        lines: list[tuple[list[str], float]] = []
        current_words: list[str] = []
        current_width = 0.0

        for index, word in enumerate(words):
            word_width = len(word) * glyph_advance
            additional_space = space_width if current_words else 0

            if current_words and (current_width + additional_space + word_width) > available_width:
                lines.append((current_words, current_width))
                current_words = []
                current_width = 0.0
                additional_space = 0

            if additional_space:
                current_width += additional_space

            current_words.append(word)
            current_width += word_width

        if current_words:
            lines.append((current_words, current_width))

        glyph_height = glyph_advance * 1.4
        content_height = len(lines) * line_height
        total_height = max(glyph_height, content_height)
        effective_height = self.height if self.height > 0 else total_height
        padding = glyph_advance * 0.3

        if self.vertical_align == 'top':
            top_y = self.center_y + effective_height / 2 - padding
            start_y = top_y - line_height / 2
        elif self.vertical_align == 'bottom':
            bottom_y = self.center_y - effective_height / 2 + padding
            start_y = bottom_y + (len(lines) - 1) * line_height + line_height / 2
        else:
            start_y = self.center_y + total_height / 2 - line_height / 2

        current_y = start_y
        for words_in_line, line_width in lines:
            start_x = self.center_x - line_width / 2 + glyph_advance / 2
            current_x = start_x
            for word_index, word in enumerate(words_in_line):
                for character in word:
                    texture = Alphabet_Textures.get(character)
                    if texture is None:
                        current_x += glyph_advance
                        continue
                    sprite = arcade.Sprite(
                        center_x=current_x,
                        center_y=current_y,
                        scale=self.scale,
                    )
                    sprite.texture = texture
                    self.Sprite_List.append(sprite)
                    current_x += glyph_advance

                if word_index != len(words_in_line) - 1:
                    current_x += space_width

            current_y -= line_height

        if self.Background_Sprite:
            max_line_width = max((width for _, width in lines), default=0)
            padding_x = glyph_advance * 2.5
            padding_y = glyph_advance * 2.5
            bg_width = max(max_line_width + padding_x, 1)
            bg_height = max(total_height + padding_y, 1)

            self.Background_Sprite.center_x = self.center_x + self.background_offset_x
            if self.vertical_align == 'top':
                self.Background_Sprite.center_y = self.center_y + effective_height / 2 - bg_height / 2 + self.background_offset_y
            elif self.vertical_align == 'bottom':
                self.Background_Sprite.center_y = self.center_y - effective_height / 2 + bg_height / 2 + self.background_offset_y
            else:
                self.Background_Sprite.center_y = self.center_y + self.background_offset_y

            if self._background_base_width and self._background_base_height:
                self.Background_Sprite.width = max(bg_width, self._background_base_width * self.background_scale)
                self.Background_Sprite.height = max(bg_height, self._background_base_height * self.background_scale)
            else:
                self.Background_Sprite.width = bg_width
                self.Background_Sprite.height = bg_height

            self._background_height = self.Background_Sprite.height

        else:
            self._background_height = total_height
    def update_textv2(self, text, Alphabet_Textures, scale=1, 
                 center_x=0, center_y = 0, 
                 text_margin=16, width=100, height = 40):
        self.Sprite_List.clear()
        if text:
            pos_x = -45+center_x
            pos_y = 5+center_y
            if len(text)*scale*text_margin > width:
                pos_y += 10
            for string in text:
                sprite = arcade.Sprite(center_x=center_x+pos_x, center_y=center_y+pos_y, scale=scale)
                sprite.texture = Alphabet_Textures[string]
                self.Sprite_List.append(sprite)
                pos_x += text_margin
                if pos_x*scale > width-90+center_x:
                    pos_x = -45+center_x
                    pos_y -= 24
    def draw(self):
        if self.Background_Sprite:
            self.Background_Sprite.draw()
        self.Sprite_List.draw()
    def update(self, delta_time):
        return None

    def set_position(self, center_x, center_y):
        dx = center_x - self.center_x
        dy = center_y - self.center_y
        self.center_x = center_x
        self.center_y = center_y
        for sprite in self.Sprite_List:
            sprite.center_x += dx
            sprite.center_y += dy
        if self.Background_Sprite:
            self.Background_Sprite.center_x += dx
            self.Background_Sprite.center_y += dy

class CustomUIFlatButton(arcade.gui.UIInteractiveWidget):
    """
    A text button, with support for background color and a border.

    :param float x: x coordinate of bottom left
    :param float y: y coordinate of bottom left
    :param float width: width of widget. Defaults to texture width if not specified.
    :param float height: height of widget. Defaults to texture height if not specified.
    :param str text: text to add to the button.
    :param style: Used to style the button

    """

    def __init__(self, 
                 Alphabet_Textures,
                 center_x: float = 0,
                 center_y: float = 0,
                 width: float = 100,
                 height: float = 60,
                 scale=1,
                 text="",
                 size_hint=None,
                 size_hint_min=None,
                 size_hint_max=None,
                 style=None, 
                 text_offset_x=0, text_offset_y = 0, 
                 text_scale=1, text_margin=16,  
                 offset_x=0, offset_y=0, 
                 line_spacing = 20,
                 Texture="resources/gui/Wood Button resized.png", Hovered_Texture=None, Pressed_Texture=None, 
                 click_sound = None,
                 badge: Optional[BadgeConfig] = None,
                 **kwargs):
        if Hovered_Texture is None:
            Hovered_Texture = Texture
        if Pressed_Texture is None and Texture == "resources/gui/Wood Button resized.png":
            Pressed_Texture = "resources/gui/Wood Button Pressed resized.png"
        elif Pressed_Texture is None:
            Pressed_Texture = Texture

        widget_x = kwargs.pop("x", None)
        widget_y = kwargs.pop("y", None)

        if widget_x is None:
            widget_x = center_x - width / 2
        else:
            center_x = widget_x + width / 2

        if widget_y is None:
            widget_y = center_y - height / 2
        else:
            center_y = widget_y + height / 2

        super().__init__(
            x=widget_x,
            y=widget_y,
            width=width,
            height=height,
            size_hint=size_hint,
            size_hint_min=size_hint_min,
            size_hint_max=size_hint_max,
            style=style,
            **kwargs,
        )
        self._center_x = center_x
        self._center_y = center_y
        self.click_sound = click_sound
        self.clicked = False

        self._text = text
        self._style = style or {}
        self._alphabet_textures = Alphabet_Textures
        self._text_dirty = True

        self.offset_x = offset_x
        self.offset_y = offset_y
        self._visual_bounds: Tuple[float, float, float, float] = (0.0, 0.0, width, height)

#image_width=width+50, image_height=height+50       image_width=width+607, image_height=height+303, 
        sprite_center_x = center_x + offset_x
        sprite_center_y = center_y + offset_y
        base_texture = arcade.load_texture(Texture)
        hovered_texture = arcade.load_texture(Hovered_Texture)
        pressed_texture = arcade.load_texture(Pressed_Texture)

        desired_width = width
        desired_height = height
        texture_width = base_texture.width or 1
        texture_height = base_texture.height or 1

        scale_x = desired_width / texture_width
        scale_y = desired_height / texture_height
        sprite_scale = min(scale_x, scale_y) * scale

        self.sprite = arcade.Sprite(center_x=sprite_center_x, center_y=sprite_center_y)
        self.sprite.texture = base_texture
        self.sprite.scale = sprite_scale

        self.hovered_sprite = arcade.Sprite(center_x=sprite_center_x, center_y=sprite_center_y)
        self.hovered_sprite.texture = hovered_texture
        self.hovered_sprite.scale = sprite_scale

        self.pressed_sprite = arcade.Sprite(center_x=sprite_center_x, center_y=sprite_center_y)
        self.pressed_sprite.texture = pressed_texture
        self.pressed_sprite.scale = sprite_scale
        self.text_sprites = arcade.SpriteList()
        self.badge_text_sprites = arcade.SpriteList()

        self.line_spacing = line_spacing
        self.text_offset_x=text_offset_x
        self.text_offset_y = text_offset_y 
        self.text_scale=text_scale
        self.text_margin=text_margin
        self.offset_x=offset_x
        self.offset_y=offset_y

        self._badge_text = ""
        self._badge_text_dirty = False
        self.badge_sprite: Optional[arcade.Sprite] = None
        self._badge_anchor_x = "right"
        self._badge_anchor_y = "bottom"
        self._badge_padding_x = 6.0
        self._badge_padding_y = 6.0
        self._badge_offset_x = 0.0
        self._badge_offset_y = 0.0
        self.badge_text_scale = 0.7
        self.badge_text_margin = 10.0

        if badge is not None:
            texture = arcade.load_texture(badge.texture)
            self.badge_sprite = arcade.Sprite(center_x=center_x, center_y=center_y)
            self.badge_sprite.texture = texture
            self.badge_sprite.scale = badge.scale
            self._badge_anchor_x = badge.anchor_x
            self._badge_anchor_y = badge.anchor_y
            self._badge_padding_x = badge.padding_x
            self._badge_padding_y = badge.padding_y
            self._badge_offset_x = badge.offset_x
            self._badge_offset_y = badge.offset_y
            self.badge_text_scale = badge.text_scale
            self.badge_text_margin = badge.text_margin
            self.set_badge_text(badge.text)

        
        self.set_text(text, Alphabet_Textures)
        self._text_dirty = True

    def _compute_visual_bounds(self) -> Tuple[float, float, float, float]:
        min_x = float("inf")
        min_y = float("inf")
        max_x = float("-inf")
        max_y = float("-inf")

        for sprite in itertools.chain(
            (self.sprite, self.hovered_sprite, self.pressed_sprite),
            self.text_sprites,
        ):
            if not sprite:
                continue
            half_width = getattr(sprite, "width", 0) / 2
            half_height = getattr(sprite, "height", 0) / 2
            center_x = getattr(sprite, "center_x", 0)
            center_y = getattr(sprite, "center_y", 0)

            min_x = min(min_x, center_x - half_width)
            max_x = max(max_x, center_x + half_width)
            min_y = min(min_y, center_y - half_height)
            max_y = max(max_y, center_y + half_height)

        if math.isinf(min_x) or math.isinf(min_y):
            min_x = 0.0
            min_y = 0.0
            max_x = self.width
            max_y = self.height

        self._visual_bounds = (min_x, min_y, max_x, max_y)
        return self._visual_bounds

    def _limit_render_area(self, surface: arcade.gui.Surface) -> None:
        """Expand the render surface so button sprites aren't clipped by offsets."""
        min_x, min_y, max_x, max_y = self._compute_visual_bounds()
        rect = self.content_rect

        extra_left = max(0.0, -min_x)
        extra_bottom = max(0.0, -min_y)
        extra_right = max(0.0, max_x - self.width)
        extra_top = max(0.0, max_y - self.height)

        if not any((extra_left, extra_right, extra_bottom, extra_top)):
            surface.limit(rect)
            return

        expanded = LBWH(
            rect.left - extra_left,
            rect.bottom - extra_bottom,
            rect.width + extra_left + extra_right,
            rect.height + extra_bottom + extra_top,
        )
        surface.limit(expanded)

    def do_render(self, surface: arcade.gui.Surface):
        self._update_visual_state()
        self._limit_render_area(surface)
        if self.pressed:
            self.pressed_sprite.draw()
            if self.click_sound and not self.clicked: 
                self.click_sound.play()
                self.clicked = True
        elif self.hovered:
            self.clicked = False
            self.hovered_sprite.draw()
        else:
            self.clicked = False
            self.sprite.draw()
        if self.text:
            self.text_sprites.draw()

        if self.text:
            return
            font_name = self._style.get("font_name", ("calibri", "arial"))
            font_size = self._style.get("font_size", 15)
            font_color = self._style.get("font_color", arcade.color.WHITE)
            border_width = self._style.get("border_width", 2)

            start_x = self.width // 2
            start_y = self.height // 2

            text_margin = 2
            arcade.draw_text(
                text=self.text,
                start_x=start_x,
                start_y=start_y,
                font_name=font_name,
                font_size=font_size,
                color=font_color,
                align="center",
                anchor_x='center', anchor_y='center',
                width=self.width - 2 * border_width - 2 * text_margin
            )
    def do_render2(self, surface: arcade.gui.Surface):
        self.prepare_render(surface)

        # Render button
        font_name = self._style.get("font_name", ("calibri", "arial"))
        font_size = self._style.get("font_size", 15)
        font_color = self._style.get("font_color", arcade.color.WHITE)
        border_width = self._style.get("border_width", 2)
        border_color = self._style.get("border_color", None)
        bg_color = self._style.get("bg_color", (21, 19, 21))

        if self.pressed:
            bg_color = self._style.get("bg_color_pressed", arcade.color.WHITE)
            border_color = self._style.get("border_color_pressed", arcade.color.WHITE)
            font_color = self._style.get("font_color_pressed", arcade.color.BLACK)
        elif self.hovered:
            border_color = self._style.get("border_color_pressed", arcade.color.WHITE)

        # render BG
        if bg_color:
            arcade.draw_xywh_rectangle_filled(0, 0, self.width, self.height, color=bg_color)

        # render border
        if border_color and border_width:
            arcade.draw_xywh_rectangle_outline(
                border_width,
                border_width,
                self.width - 2 * border_width,
                self.height - 2 * border_width,
                color=border_color,
                border_width=border_width)

        # render text
        if self.text:
            start_x = self.width // 2
            start_y = self.height // 2

            text_margin = 2
            arcade.draw_text(
                text=self.text,
                start_x=start_x,
                start_y=start_y,
                font_name=font_name,
                font_size=font_size,
                color=font_color,
                align="center",
                anchor_x='center', anchor_y='center',
                width=self.width - 2 * border_width - 2 * text_margin
            )
    @property
    def text(self):
        return self._text
    @text.setter
    def text(self, value):
        self.set_text(value, self._alphabet_textures)
    def set_text(self, text, Alphabet_Textures=None):
        if Alphabet_Textures is not None:
            self._alphabet_textures = Alphabet_Textures
        self._text = text or ""
        self._text_dirty = True
        self._rebuild_text_sprites()
        self.trigger_full_render()
    def set_badge_text(self, text: Optional[str]):
        if self.badge_sprite is None:
            return
        if not text:
            self.badge_sprite.visible = False
            self._badge_text = ""
            self.badge_text_sprites.clear()
            self._badge_text_dirty = False
            self.trigger_full_render()
            return
        self.badge_sprite.visible = True
        self._badge_text = text
        self._badge_text_dirty = True
        self.trigger_full_render()
    def _rebuild_text_sprites(self):
        self.text_sprites.clear()
        if not self._text or not self._alphabet_textures:
            self._text_dirty = False
            return
        glyph_width = max(self.text_margin * self.text_scale, 1)
        line_height = max(self.line_spacing * self.text_scale, glyph_width)

        max_line_width = max(self.width - 20, glyph_width)
        words = self._text.split(" ")

        lines: list[list[str]] = []
        current_line: list[str] = []
        current_width = 0.0

        for word in words:
            word_width = len(word) * glyph_width
            space_width = glyph_width if current_line else 0
            if current_line and current_width + space_width + word_width > max_line_width:
                lines.append(current_line)
                current_line = []
                current_width = 0.0
                space_width = 0

            if space_width:
                current_line.append(" ")
                current_width += space_width

            for ch in word:
                current_line.append(ch)
            current_width += word_width

        if current_line:
            lines.append(current_line)

        base_center_x = self.width / 2 + self.offset_x
        base_center_y = self.height / 2 + self.offset_y

        total_height = (len(lines) - 1) * line_height
        start_y = base_center_y + total_height / 2 + self.text_offset_y

        current_y = start_y
        for line_chars in lines:
            line_width = len(line_chars) * glyph_width
            current_x = base_center_x - line_width / 2 + self.text_offset_x
            for ch in line_chars:
                if ch == " ":
                    current_x += glyph_width
                    continue
                texture = self._alphabet_textures.get(ch)
                if texture is None:
                    current_x += glyph_width
                    continue
                center_x = current_x + glyph_width / 2
                sprite = arcade.Sprite(
                    center_x=center_x,
                    center_y=current_y,
                    scale=self.text_scale,
                )
                sprite.texture = texture
                sprite._relative_x = center_x - base_center_x
                sprite._relative_y = current_y - base_center_y
                self.text_sprites.append(sprite)
                current_x += glyph_width
            current_y -= line_height

        self._text_dirty = False

    def _rebuild_badge_text_sprites(self):
        self.badge_text_sprites.clear()
        if (
            not self.badge_sprite
            or not getattr(self.badge_sprite, "visible", True)
            or not self._badge_text
            or not self._alphabet_textures
        ):
            self._badge_text_dirty = False
            return

        glyph_width = max(self.badge_text_margin * self.badge_text_scale, 1)
        total_width = len(self._badge_text) * glyph_width
        current_x = -total_width / 2 + glyph_width / 2

        for ch in self._badge_text:
            texture = self._alphabet_textures.get(ch)
            if texture is None:
                current_x += glyph_width
                continue
            sprite = arcade.Sprite(center_x=0, center_y=0, scale=self.badge_text_scale)
            sprite.texture = texture
            sprite._relative_x = current_x
            sprite._relative_y = 0
            self.badge_text_sprites.append(sprite)
            current_x += glyph_width

        self._badge_text_dirty = False

    def _calculate_badge_center(self, base_center_x: float, base_center_y: float) -> Tuple[float, float]:
        if not self.badge_sprite:
            return base_center_x, base_center_y

        half_w = self.width / 2
        half_h = self.height / 2
        badge_half_w = getattr(self.badge_sprite, "width", 0) / 2
        badge_half_h = getattr(self.badge_sprite, "height", 0) / 2

        anchor_x = _ANCHOR_X.get(self._badge_anchor_x, 1)
        anchor_y = _ANCHOR_Y.get(self._badge_anchor_y, -1)

        rel_x = anchor_x * (half_w - badge_half_w - self._badge_padding_x) + self._badge_offset_x
        rel_y = anchor_y * (half_h - badge_half_h - self._badge_padding_y) - self._badge_offset_y

        return base_center_x + rel_x, base_center_y + rel_y

    def _update_visual_state(self):
        local_center_x = self.width / 2 + self.offset_x
        local_center_y = self.height / 2 + self.offset_y

        for sprite in (self.sprite, self.hovered_sprite, self.pressed_sprite):
            sprite.center_x = local_center_x
            sprite.center_y = local_center_y

        if self._text_dirty:
            self._rebuild_text_sprites()
        if self._badge_text_dirty:
            self._rebuild_badge_text_sprites()

        base_center_x = self.width / 2 + self.offset_x
        base_center_y = self.height / 2 + self.offset_y
        for sprite in self.text_sprites:
            rel_x = getattr(sprite, "_relative_x", 0)
            rel_y = getattr(sprite, "_relative_y", 0)
            sprite.center_x = base_center_x + rel_x
            sprite.center_y = base_center_y + rel_y

        self._compute_visual_bounds()

    def draw_badge_overlay(self):
        if not self.badge_sprite or not getattr(self.badge_sprite, "visible", True):
            return
        # Ensure text sprites are up to date before drawing
        if self._text_dirty:
            self._rebuild_text_sprites()
        if self._badge_text_dirty:
            self._rebuild_badge_text_sprites()

        base_center_x = self.width / 2 + self.offset_x
        base_center_y = self.height / 2 + self.offset_y
        badge_center_x, badge_center_y = self._calculate_badge_center(base_center_x, base_center_y)
        world_left = self.rect.left
        world_bottom = self.rect.bottom

        def _draw_sprite_at_world(sprite, dx=0.0, dy=0.0):
            original = (sprite.center_x, sprite.center_y)
            sprite.center_x = world_left + badge_center_x + dx
            sprite.center_y = world_bottom + badge_center_y + dy
            sprite.draw()
            sprite.center_x, sprite.center_y = original

        _draw_sprite_at_world(self.badge_sprite)
        for sprite in self.badge_text_sprites:
            rel_x = getattr(sprite, "_relative_x", 0)
            rel_y = getattr(sprite, "_relative_y", 0)
            _draw_sprite_at_world(sprite, rel_x, rel_y)

    def _hit_test(self, pos: Tuple[float, float]) -> bool:
        bounds = getattr(self, "_visual_bounds", None)
        if not bounds:
            bounds = self._compute_visual_bounds()

        min_x, min_y, max_x, max_y = bounds
        left = self.rect.left + min_x
        right = self.rect.left + max_x
        bottom = self.rect.bottom + min_y
        top = self.rect.bottom + max_y
        x, y = pos
        return left <= x <= right and bottom <= y <= top

    def on_event(self, event: UIEvent) -> bool | None:
        if UIWidget.on_event(self, event):
            return EVENT_HANDLED

        if isinstance(event, UIMouseMovementEvent):
            self.hovered = self._hit_test(event.pos)

        if (
            isinstance(event, UIMousePressEvent)
            and self._hit_test(event.pos)
            and event.button in self.interaction_buttons
        ):
            self.pressed = True
            self._grap_active()
            return EVENT_HANDLED

        if (
            self.pressed
            and isinstance(event, UIMouseReleaseEvent)
            and event.button in self.interaction_buttons
        ):
            self.pressed = False
            if self._hit_test(event.pos) and not self.disabled:
                self._grap_active()
                click_event = UIOnClickEvent(
                    source=self,
                    x=event.x,
                    y=event.y,
                    button=event.button,
                    modifiers=event.modifiers,
                )
                self.dispatch_event("on_click", click_event)
            return EVENT_HANDLED

        return EVENT_UNHANDLED

class CustomUISlider(UIWidget):
    """Minimal slider implementation drawing directly on the widget surface."""

    value = Property(0.0)
    hovered = Property(False)
    pressed = Property(False)

    def __init__(
        self,
        *,
        value: float = 0,
        min_value: float = 0,
        max_value: float = 100,
        x: float = 0,
        y: float = 0,
        width: float = 300,
        height: float = 24,
        size_hint=None,
        size_hint_min=None,
        size_hint_max=None,
        offset_x: Optional[float] = 0,
        offset_y: float = 0,
        button_offset_x: float = 0,
        button_offset_y: float = 0,
        track_color: Color = (70, 40, 20, 255),
        fill_color: Color = (196, 120, 48, 255),
        knob_color: Color = (240, 200, 64, 255),
        **kwargs,
    ) -> None:
        super().__init__(
            x=x,
            y=y,
            width=width,
            height=height,
            size_hint=size_hint,
            size_hint_min=size_hint_min,
            size_hint_max=size_hint_max,
            **kwargs,
        )

        self.vmin = min_value
        self.vmax = max_value
        self.value = max(min(value, self.vmax), self.vmin)

        self._offset_x = offset_x or 0
        self._offset_y = offset_y
        self.button_offset_x = button_offset_x
        self.button_offset_y = button_offset_y

        self.track_color = track_color
        self.fill_color = fill_color
        self.knob_color = knob_color

        self._padding = max(int(self.height * 0.18), 6)
        self._knob_radius = max(int(self.height * 0.35), 8)

        bind(self, "value", self.trigger_full_render)
        bind(self, "hovered", self.trigger_render)
        bind(self, "pressed", self.trigger_full_render)

        self.register_event_type("on_change")

    # Geometry helpers -----------------------------------------------------
    def _usable_width(self) -> float:
        return max(self.width - 2 * self._padding, 1)

    def _x_for_value(self, value: float) -> float:
        span = self.vmax - self.vmin
        if span == 0:
            return self._padding
        clamped = max(min(value, self.vmax), self.vmin)
        nval = (clamped - self.vmin) / span
        return self._padding + nval * self._usable_width()

    @property
    def norm_value(self) -> float:
        span = self.vmax - self.vmin
        if span == 0:
            return 0.0
        return (self.value - self.vmin) / span

    @norm_value.setter
    def norm_value(self, norm: float) -> None:
        span = self.vmax - self.vmin
        if span == 0:
            self.value = self.vmin
            return
        norm = max(0.0, min(1.0, norm))
        self.value = self.vmin + norm * span

    @property
    def value_x(self) -> float:
        return self._x_for_value(self.value)

    @value_x.setter
    def value_x(self, nx: float) -> None:
        usable = self._usable_width()
        left = self._padding
        right = left + usable
        nx = max(left, min(right, nx))
        self.norm_value = (nx - left) / usable

    # Rendering ------------------------------------------------------------
    def do_render(self, surface: Surface) -> None:
        self.prepare_render(surface)

        track_height = max(int(self.height * 0.22), 4)
        track_bottom = (self.height - track_height) / 2 + self._offset_y
        track_left = self._padding
        track_width = self._usable_width()

        arcade.draw_lbwh_rectangle_filled(
            track_left,
            track_bottom,
            track_width,
            track_height,
            self.track_color,
        )

        fill_width = track_width * self.norm_value
        if fill_width > 0:
            arcade.draw_lbwh_rectangle_filled(
                track_left,
                track_bottom,
                fill_width,
                track_height,
                self.fill_color,
            )

        knob_center_x = self.value_x + self.button_offset_x
        knob_center_y = self.height / 2 + self.button_offset_y + self._offset_y
        arcade.draw_circle_filled(
            knob_center_x,
            knob_center_y,
            self._knob_radius,
            self.knob_color,
        )

    # Interaction ----------------------------------------------------------
    def _cursor_pos(self) -> Tuple[float, float]:
        return (
            self.left + self.value_x + self.button_offset_x,
            self.bottom + self.height / 2 + self.button_offset_y,
        )

    def _is_on_cursor(self, x: float, y: float) -> bool:
        cx, cy = self._cursor_pos()
        return math.dist((x, y), (cx, cy)) <= self._knob_radius

    def on_event(self, event: UIEvent) -> Optional[bool]:
        if isinstance(event, UIMouseMovementEvent):
            self.hovered = self._is_on_cursor(event.x, event.y)

        if isinstance(event, UIMousePressEvent) and self._is_on_cursor(event.x, event.y):
            self.pressed = True

        if isinstance(event, UIMouseDragEvent) and self.pressed:
            old_value = self.value
            self.value_x = event.x - self.left
            self.dispatch_event("on_change", UIOnChangeEvent(self, old_value, self.value))  # type: ignore

        if isinstance(event, UIMouseReleaseEvent):
            self.pressed = False

        return EVENT_UNHANDLED

    def on_change(self, event: UIOnChangeEvent) -> None:
        pass


class CustomTextSprite2(object):
    def __init__(self, string, Alphabet_Textures, scale=1, 
                 center_x=0, center_y = 0, 
                 text_scale=1, text_margin=16, width=100, height = 40,  Background_offset_x=0, Background_offset_y=0, Background_scale=1, Background_Texture=None) -> None:
        super().__init__()
        self.Sprite_List = arcade.SpriteList()
        self.background_texture = Background_Texture
        self.background_offset_x = Background_offset_x
        self.background_offset_y = Background_offset_y
        self.background_scale = Background_scale
        self.text_scale = text_scale
        self.width = width
        self.height = height
        self.center_x = center_x
        self.center_y = center_y
        self.scale = scale
        self.text_margin = text_margin

        if Background_Texture:
            self.Background_Sprite = arcade.Sprite(
                Background_Texture,
                center_x=center_x+width/2+Background_offset_x,
                center_y=center_y-height*2+Background_offset_y,
                scale=Background_scale,
            )
        else:
            self.Background_Sprite = None

        self.update_text(string, Alphabet_Textures, scale=scale, text_scale=text_scale,
                 center_x=center_x, center_y=center_y, 
                 text_margin=text_margin, width=width, height = height)
        
    def update_text(self, text, Alphabet_Textures, scale=1, text_scale=1,
                 center_x=None, center_y = None, 
                 text_margin=None, width=None, height = None):
        self.text = text
        self.Sprite_List.clear()
        if not text:
            return
        if center_x is not None:
            self.center_x = center_x
        if center_y is not None:
            self.center_y = center_y
        if text_margin is not None:
            self.text_margin = text_margin
        if width is not None:
            self.width = width
        if height is not None:
            self.height = height

        words = text.split(' ')

        glyph_advance = max(14 * scale * text_scale * 0.8, 1)
        space_width = glyph_advance
        available_width = self.width if self.width > 0 else float("inf")

        lines: list[tuple[list[str], float]] = []
        current_words: list[str] = []
        current_width = 0.0

        for word in words:
            word_width = len(word) * glyph_advance
            additional_space = space_width if current_words else 0

            if current_words and current_width + additional_space + word_width > available_width:
                lines.append((current_words, current_width))
                current_words = []
                current_width = 0.0
                additional_space = 0

            if additional_space:
                current_width += additional_space

            current_words.append(word)
            current_width += word_width

        if current_words:
            lines.append((current_words, current_width))

        total_height = (len(lines) - 1) * (glyph_advance * 1.2)
        start_y = self.center_y + total_height / 2

        current_y = start_y
        for words_in_line, line_width in lines:
            start_x = self.center_x - line_width / 2 + glyph_advance / 2
            current_x = start_x
            for word_index, word in enumerate(words_in_line):
                for string in word:
                    texture = Alphabet_Textures.get(string)
                    if texture is None:
                        current_x += glyph_advance
                        continue
                    sprite = arcade.Sprite(center_x=current_x, center_y=current_y, scale=scale*text_scale)
                    sprite.texture = texture
                    self.Sprite_List.append(sprite)
                    current_x += glyph_advance
                if word_index != len(words_in_line) - 1:
                    current_x += space_width
            current_y -= glyph_advance * 1.2

        if self.Background_Sprite:
            self.Background_Sprite.center_x = self.center_x + self.background_offset_x
            self.Background_Sprite.center_y = self.center_y + self.background_offset_y

    def draw(self):
        if self.Background_Sprite:
            self.Background_Sprite.draw()
        self.Sprite_List.draw()

    def set_position(self, center_x, center_y):
        dx = center_x - self.center_x
        dy = center_y - self.center_y
        self.center_x = center_x
        self.center_y = center_y
        for sprite in self.Sprite_List:
            sprite.center_x += dx
            sprite.center_y += dy
        if self.Background_Sprite:
            self.Background_Sprite.center_x += dx
            self.Background_Sprite.center_y += dy


textures = load_texture_grid("resources/gui/Wooden Font.png", 14, 24, 12, 71, margin=1)
Alphabet_Textures = {" ":None}
string = "ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890abcdefghijklmnopqrstuvwxyz.:,%/-+_'"
for i in range(len(string)):
    Alphabet_Textures[string[i]] = textures[i]
    """
    Main application class.
    """

    def __init__(self):
        super().__init__(800, 600, "WINDOW_TITLE", resizable=True)

        # Set the working directory (where we expect to find files) to the same
        # directory this .py file is in. You can leave this out of your own
        # code, but it is needed to easily run the examples using "python -m"
        # as mentioned at the top of this program.
        arcade.set_background_color(arcade.color.BLACK)
    def setup(self):
        self.bttn = CustomTextSprite2("BRRRRRRR", Alphabet_Textures, center_x=400, center_y=300, scale=2)

    def on_draw(self):
        self.bttn.draw()
        return super().on_draw()


def main():
    game = MyGame()
    game.setup()
    arcade.run()


if __name__ == "__main__":
    main()

class UpdatingText(CustomTextSprite):
    def __init__(self, string, Alphabet_Textures, max_time, scale=1, center_x=0, center_y=0, text_scale=1, text_margin=16, width=100, height=40, Background_offset_x=0, Background_offset_y=0, Background_scale=1, Background_Texture=None) -> None:
        super().__init__(string, Alphabet_Textures, scale, center_x=center_x, center_y=center_y, text_scale=text_scale, text_margin=text_margin, width=width, height=height,  Background_offset_x=Background_offset_x, Background_offset_y=Background_offset_y, Background_scale=Background_scale, Background_Texture=Background_Texture)
        self.max_time = max_time
        self.timer = 0
    def update(self, delta_time):
        self.timer += delta_time
        if self.timer >= self.max_time:
            return True
