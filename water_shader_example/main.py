"""Minimal Arcade demo showing how to drive a simple GLSL water shader."""
from __future__ import annotations

from array import array
from pathlib import Path

import arcade

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
SCREEN_TITLE = "2D Water Shader"
TEXTURE_PATH = Path(__file__).with_name("water.jpg")


class WaterWindow(arcade.Window):
    """Window that renders a fullscreen quad with a fragment shader."""

    def __init__(self) -> None:
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, resizable=True)
        self.center_window()

        if not TEXTURE_PATH.exists():
            raise FileNotFoundError(
                "Missing water texture. Place a texture next to main.py named water.png"
            )

        # Keep time for animation
        self.elapsed_time: float = 0.0

        # Load the base texture the shader will distort
        self.water_texture = self.ctx.load_texture(str(TEXTURE_PATH))

        # Vertex/fragment shader pair.
        shader_dir = Path(__file__).parent
        self.program = self.ctx.load_program(
            vertex_shader=str(shader_dir / "water.vert"),
            fragment_shader=str(shader_dir / "water.frag"),
        )

        # A full-screen quad declared in NDC coordinates (-1 .. 1)
        vertex_data = array(
            "f",
            [
                -1.0,
                -1.0,
                0.0,
                0.0,
                1.0,
                -1.0,
                1.0,
                0.0,
                1.0,
                1.0,
                1.0,
                1.0,
                -1.0,
                1.0,
                0.0,
                1.0,
            ],
        )
        index_data = array("I", [0, 1, 2, 0, 2, 3])

        buffer = self.ctx.buffer(data=vertex_data)
        index_buffer = self.ctx.buffer(data=index_data)

        self.quad = self.ctx.geometry(
            [
                arcade.gl.BufferDescription(buffer, "2f 2f", ["in_pos", "in_uv"]),
            ],
            index_buffer=index_buffer,
        )

        # Static uniforms: resolution + sampler binding.
        width, height = self.get_size()
        self.program["u_resolution"] = (float(width), float(height))
        self.program["u_texture"] = 0

    def on_resize(self, width: int, height: int) -> None:
        super().on_resize(width, height)
        self.program["u_resolution"] = (float(width), float(height))

    def on_update(self, delta_time: float) -> None:
        self.elapsed_time += delta_time
        self.program["u_time"] = self.elapsed_time * 0.5

    def on_draw(self) -> None:
        self.clear()
        self.water_texture.use(0)
        self.quad.render(self.program)


def main() -> None:
    window = WaterWindow()
    arcade.run()


if __name__ == "__main__":
    main()
