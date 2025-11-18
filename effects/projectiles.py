from __future__ import annotations

import random
from typing import Callable, Iterable, Sequence

import arcade

from Components import AnimationPlayer, advance_sprite, set_sprite_motion


ShouldDetonate = Callable[[arcade.Sprite], bool]
ExplosionCallback = Callable[[arcade.Sprite], None]


class ProjectileEffect:
    """Manage a collection of animated projectile sprites."""

    def __init__(
        self,
        texture_path: str,
        destruction_paths: Sequence[str] | None = None,
        *,
        scale: float = 1.0,
        speed: float = 50.0,
        animation_speed: float = 0.1,
    ) -> None:
        self.texture_path = texture_path
        self.scale = scale
        self.speed = speed
        self.animation_speed = animation_speed
        if destruction_paths:
            self._destruction_frames = [arcade.load_texture(path)
                                        for path in destruction_paths]
        else:
            self._destruction_frames = []
        self.projectiles = arcade.SpriteList()

    def spawn(
        self,
        game,
        origin: tuple[float, float],
        heading: float,
        *,
        maxtime: float = 15.0,
        count: int = 1,
        max_rotation: float = 5.0,
    ) -> None:
        """Create projectiles at ``origin`` aimed roughly at ``heading``."""
        for _ in range(count):
            offset = random.uniform(-max_rotation, max_rotation)
            projectile_heading = heading + offset
            projectile = arcade.Sprite(
                self.texture_path,
                scale=self.scale,
                angle=projectile_heading - 90,
                center_x=origin[0],
                center_y=origin[1],
            )
            projectile.time = 0.0
            projectile.maxtime = maxtime
            projectile.destroy = False
            projectile.destruction = self._destruction_frames
            projectile.destructionAnim = AnimationPlayer(self.animation_speed)
            set_sprite_motion(projectile, projectile_heading, self.speed)
            projectile.update()
            self.projectiles.append(projectile)
            if game and projectile not in getattr(game, "overParticles", []):
                game.overParticles.append(projectile)

    def update(
        self,
        game,
        delta_time: float,
        *,
        should_detonate: ShouldDetonate | None = None,
        on_explode: ExplosionCallback | None = None,
    ) -> None:
        """Advance projectile movement and trigger explosions."""
        for projectile in list(self.projectiles):
            if not getattr(projectile, "destroy", False):
                advance_sprite(projectile, delta_time)
                projectile.update()
                projectile.time += delta_time
                if projectile.time > getattr(projectile, "maxtime", 0):
                    self._remove(projectile)
                    continue
                if should_detonate and should_detonate(projectile):
                    projectile.destroy = True
            else:
                self._update_explosion(projectile, delta_time, game, on_explode)

    def serialize(self) -> list[dict]:
        data: list[dict] = []
        for projectile in self.projectiles:
            data.append(
                {
                    "x": projectile.center_x,
                    "y": projectile.center_y,
                    "dx": getattr(projectile, "_motion_dx", 0.0),
                    "dy": getattr(projectile, "_motion_dy", 0.0),
                    "time": getattr(projectile, "time", 0.0),
                    "maxtime": getattr(projectile, "maxtime", 0.0),
                    "destroy": getattr(projectile, "destroy", False),
                    "scale": projectile.scale,
                    "angle": projectile.angle,
                    "anim_index": getattr(getattr(projectile, "destructionAnim", None), "index", 0),
                    "anim_time": getattr(getattr(projectile, "destructionAnim", None), "time", 0.0),
                }
            )
        return data

    def restore(self, game, entries: Iterable[dict]) -> None:
        self.projectiles = arcade.SpriteList()
        for entry in entries:
            projectile = arcade.Sprite(
                self.texture_path,
                scale=entry.get("scale", self.scale),
                angle=entry.get("angle", 0.0),
                center_x=entry.get("x", 0.0),
                center_y=entry.get("y", 0.0),
            )
            projectile._motion_dx = entry.get("dx", 0.0)
            projectile._motion_dy = entry.get("dy", 0.0)
            projectile.time = entry.get("time", 0.0)
            projectile.maxtime = entry.get("maxtime", 0.0)
            projectile.destroy = entry.get("destroy", False)
            projectile.destruction = self._destruction_frames
            projectile.destructionAnim = AnimationPlayer(self.animation_speed)
            projectile.destructionAnim.index = entry.get("anim_index", 0)
            projectile.destructionAnim.time = entry.get("anim_time", 0.0)
            self.projectiles.append(projectile)
            if game and projectile not in getattr(game, "overParticles", []):
                game.overParticles.append(projectile)

    def cleanup(self) -> None:
        for projectile in list(self.projectiles):
            self._remove(projectile)
        self.projectiles = arcade.SpriteList()

    def _remove(self, projectile: arcade.Sprite) -> None:
        projectile.remove_from_sprite_lists()
        if projectile in self.projectiles:
            self.projectiles.remove(projectile)

    def _update_explosion(
        self,
        projectile: arcade.Sprite,
        delta_time: float,
        game,
        on_explode: ExplosionCallback | None,
    ) -> None:
        if not self._destruction_frames:
            self._remove(projectile)
            return
        anim = projectile.destructionAnim.updateAnim(
            delta_time, len(self._destruction_frames))
        scalevar = 0.15 * random.random() * delta_time
        current_scale = projectile.scale
        if isinstance(current_scale, tuple):
            new_scale = current_scale[1] + scalevar
            projectile.scale = (new_scale, new_scale)
        else:
            projectile.scale = current_scale + scalevar
        if anim == 0:
            if on_explode:
                on_explode(projectile)
            self._remove(projectile)
        else:
            projectile.texture = self._destruction_frames[min(anim, len(self._destruction_frames)-1)]
