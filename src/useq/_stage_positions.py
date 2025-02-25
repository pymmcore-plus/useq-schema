from typing import ClassVar

from pydantic import RootModel

from useq import Position
from useq._axis_iterable import AxisIterableBase


class StagePositions(RootModel, AxisIterableBase):
    root: tuple[Position, ...]
    axis_key: ClassVar[str] = "p"

    def __iter__(self):
        return iter(self.root)

    def __getitem__(self, item):
        return self.root[item]

    def create_event_kwargs(cls, val: Position) -> dict:
        """Convert a value from the iterator to kwargs for an MDAEvent."""
        return {"x_pos": val.x, "y_pos": val.y}

    def length(self) -> int:
        """Return the number of axis values.

        If the axis is infinite, return -1.
        """
        return len(self.root)
