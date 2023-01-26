import itertools
import math
from enum import Enum
from typing import Any, Iterator, NamedTuple, Sequence, Tuple, Union

from pydantic import validator

from useq._base_model import FrozenModel


class RelativeTo(Enum):
    center = "center"
    top_left = "top_left"


class Coordinate(FrozenModel):
    """Defines a position in 2D space.

    Attributes
    ----------
    x : float
        X position in microns.
    y : float
        Y position in microns.
    """

    x: float
    y: float

    @classmethod
    def validate(cls, v: Any) -> "Coordinate":
        if isinstance(v, Coordinate):
            return v
        if isinstance(v, dict):
            return Coordinate(**v)
        if isinstance(v, (list, tuple)):
            return Coordinate(x=v[0], y=v[1])
        raise ValueError(f"Cannot convert to Coordinate: {v}")


class TilePosition(NamedTuple):
    x: float
    y: float
    row: int
    col: int
    is_relative: bool


class _TilePlan(FrozenModel):
    """Base class for all tile plans.

    Attributes
    ----------
    overlap : float | Tuple[float, float]
        Overlap between tiles in percent. If a single value is provided, it is
        used for both x and y. If a tuple is provided, the first value is used
        for x and the second for y.
    snake_order : bool
        If `True`, tiles are arranged in a snake order (i.e. back and forth).
        If `False`, tiles are arranged in a row-wise order.
    """

    overlap: Tuple[float, float] = (0.0, 0.0)
    snake_order: bool = True

    @validator("overlap", pre=True)
    def _validate_overlap(cls, v: Any) -> Tuple[float, float]:
        if isinstance(v, float):
            return (v,) * 2
        if isinstance(v, Sequence) and len(v) == 2:
            return float(v[0]), float(v[1])
        raise ValueError("overlap must be a float or a tuple of two floats")

    @property
    def is_relative(self) -> bool:
        return False

    def _offset_x(self, dx: float) -> float:
        return 0

    def _offset_y(self, dy: float) -> float:
        return 0

    def _nrows(self, dx: float) -> int:
        """Return the number of rows, given a grid step size."""
        raise NotImplementedError

    def _ncols(self, dy: float) -> int:
        """Return the number of cols, given a grid step size."""
        raise NotImplementedError

    def iter_tiles(self, fov_width: float, fov_height: float) -> Iterator[TilePosition]:
        """Iterate over all tiles, given a field of view size."""
        dx, dy = self._step_size(fov_width, fov_height)
        rows = self._nrows(dx)
        cols = self._ncols(dy)
        x0 = self._offset_x(dx)
        y0 = self._offset_y(dy)
        for r, c in itertools.product(range(rows), range(cols)):
            if self.snake_order and r % 2 == 1:
                c = cols - c - 1
            yield TilePosition(x0 + c * dx, y0 - r * dy, r, c, self.is_relative)

    def __len__(self) -> int:
        return len(list(self.iter_tiles(1, 1)))

    def _step_size(self, fov_width: float, fov_height: float) -> Tuple[float, float]:
        dx = fov_width - (fov_width * self.overlap[0]) / 100
        dy = fov_height - (fov_height * self.overlap[1]) / 100
        return dx, dy


class TileFromCorners(_TilePlan):
    """Define tile positions from two corners.

    Attributes
    ----------
    corner1 : Coordinate
        First bounding coordinate (e.g. "top left").
    corner2 : Coordinate
        Second bounding coordinate (e.g. "bottom right").
    """

    corner1: Coordinate
    corner2: Coordinate

    def _nrows(self, dx: float) -> int:
        total_width = abs(self.corner1.x - self.corner2.x)
        return math.ceil(total_width / dx)

    def _ncols(self, dy: float) -> int:
        total_height = abs(self.corner1.y - self.corner2.y)
        return math.ceil(total_height / dy)

    def _offset_x(self, dx: float) -> float:
        return min(self.corner1.x, self.corner2.x)

    def _offset_y(self, dy: float) -> float:
        return min(self.corner1.y, self.corner2.y)


class TileRelative(_TilePlan):
    """Yield relative delta increments to build a tile acquisition.

    Attributes
    ----------
    rows: int
        Number of rows.
    cols: int
        Number of columns.
    relative_to: Literal["center", "top_left"]:
        Point in the grid to which the coordinates are relative. If "center", the grid
        is centered around the origin. If "top_left", the grid is positioned such that
        the top left corner is at the origin.
    """

    rows: int
    cols: int
    relative_to: RelativeTo = RelativeTo.center

    @property
    def is_relative(self) -> bool:
        return True

    def _nrows(self, dx: float) -> int:
        return self.rows

    def _ncols(self, dy: float) -> int:
        return self.cols

    def _offset_x(self, dx: float) -> float:
        return (
            -((self.cols - 1) * dx) / 2
            if self.relative_to == RelativeTo.center
            else 0.0
        )

    def _offset_y(self, dy: float) -> float:
        return (
            ((self.rows - 1) * dy) / 2 if self.relative_to == RelativeTo.center else 0.0
        )


class NoTile(_TilePlan):
    def iter_tiles(self, fov_width: float, fov_height: float) -> Iterator[TilePosition]:
        return iter([])


AnyTilePlan = Union[TileFromCorners, TileRelative, NoTile]
