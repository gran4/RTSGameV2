from pathlib import Path
from typing import Any, Optional, Tuple, Union

import pyglet

import arcade
from mytypes import Color, Point, RGBA255

FontNameOrNames = Union[str, Tuple[str, ...]]

def _draw_pyglet_label(label: pyglet.text.Label) -> None:
    """

    Helper for drawing pyglet labels with rotation within arcade.

    Originally part of draw_text in this module, now abstracted and improved
    so that both arcade.Text and arcade.draw_text can make use of it.

    :param pyglet.text.Label label: a pyglet label to wrap and draw
    """
    assert isinstance(label, pyglet.text.Label)
    window = arcade.get_window()

    # window.ctx.reset()
    with window.ctx.pyglet_rendering():
        label.draw()



def create_text_texture(text: str,
    color: RGBA255 = arcade.color.WHITE,
    font_size: float = 12,
    width: int = 0,
    align: str = "left",
    font_name: FontNameOrNames = ("calibri", "arial"),
    bold: bool = False,
    italic: bool = False,
    anchor_x: str = "left",
    multiline: bool = False,
    texture_atlas: Optional[arcade.TextureAtlas] = None):

    if align != "center" and align != "left" and align != "right":
        raise ValueError("The 'align' parameter must be equal to 'left', 'right', or 'center'.")

    adjusted_font = _attempt_font_name_resolution(font_name)
    _label = pyglet.text.Label(
        text=text,
        font_name=adjusted_font,
        font_size=font_size,
        anchor_x=anchor_x,
        color=Color.from_iterable(color),
        width=width,
        align=align,
        bold=bold,
        italic=italic,
        multiline=multiline,
        )

    size = (
        int(_label.width),
        int(_label.height),
    )
    
    texture = arcade.Texture.create_empty(text, size)

    if not texture_atlas:
        texture_atlas = arcade.get_window().ctx.default_atlas
    texture_atlas.add(texture)
    with texture_atlas.render_into(texture) as fbo:
        fbo.clear((0, 0, 0, 255))
        _draw_pyglet_label(_label)
    return texture


texture = arcade.create_text_texture("BRRRRRRR")
print(type(texture))
print(texture.width)
print(texture.height)