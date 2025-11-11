"""Compatibility helpers for arcade GUI components changed in arcade 3.x."""
from __future__ import annotations

from typing import Optional, Tuple

try:
    from arcade.gui import UIAnchorWidget  # type: ignore
except ImportError:  # pragma: no cover - executed on new arcade versions only
    from arcade.gui.widgets.layout import UIAnchorLayout

    class UIAnchorWidget(UIAnchorLayout):
        """Compat wrapper matching the arcade 2.x UIAnchorWidget API."""

        def __init__(
            self,
            *,
            child=None,
            anchor_x: str = "center",
            anchor_y: str = "center",
            align_x: float = 0,
            align_y: float = 0,
            size_hint: Optional[Tuple[float, float]] = (1, 1),
            size_hint_min=None,
            size_hint_max=None,
            **kwargs,
        ) -> None:
            super().__init__(
                size_hint=size_hint,
                size_hint_min=size_hint_min,
                size_hint_max=size_hint_max,
                **kwargs,
            )
            self._anchor_x = anchor_x
            self._anchor_y = anchor_y
            self._align_x = align_x
            self._align_y = align_y
            self.child = None

            if child is not None:
                self.set_child(child)

        def set_child(self, child):
            if self.child is child:
                return child

            if self.child is not None:
                super().remove(self.child)

            self.child = child
            super().add(
                child,
                anchor_x=self._anchor_x,
                anchor_y=self._anchor_y,
                align_x=self._align_x,
                align_y=self._align_y,
            )
            return child

        def add(self, child, **kwargs):  # type: ignore[override]
            return self.set_child(child)

        def remove_child(self):
            if self.child is not None:
                super().remove(self.child)
                self.child = None

        def _reapply(self):
            if self.child is not None:
                super().remove(self.child)
                super().add(
                    self.child,
                    anchor_x=self._anchor_x,
                    anchor_y=self._anchor_y,
                    align_x=self._align_x,
                    align_y=self._align_y,
                )

        @property
        def anchor_x(self):
            return self._anchor_x

        @anchor_x.setter
        def anchor_x(self, value):
            self._anchor_x = value
            self._reapply()

        @property
        def anchor_y(self):
            return self._anchor_y

        @anchor_y.setter
        def anchor_y(self, value):
            self._anchor_y = value
            self._reapply()

        @property
        def align_x(self):
            return self._align_x

        @align_x.setter
        def align_x(self, value):
            self._align_x = value
            self._reapply()

        @property
        def align_y(self):
            return self._align_y

        @align_y.setter
        def align_y(self, value):
            self._align_y = value
            self._reapply()


__all__ = ["UIAnchorWidget"]
