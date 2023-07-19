from __future__ import annotations

import math
from enum import Enum
from functools import partial
from typing import Any, Callable, Iterator, NamedTuple, Sequence, Tuple, Union

import numpy as np
from pydantic import validator

from useq._base_model import FrozenModel


class RelativeTo(Enum):
    center = "center"
    top_left = "top_left"


class OrderMode(Enum):
    """Different ways of ordering the grid positions."""

    row_wise = "row_wise"
    column_wise = "column_wise"
    row_wise_snake = "row_wise_snake"
    column_wise_snake = "column_wise_snake"
    spiral = "spiral"


def _spiral_indices(
    rows: int, columns: int, center_origin: bool = False
) -> Iterator[Tuple[int, int]]:
    """Return a spiral iterator over a 2D grid.

    Parameters
    ----------
    rows : int
        Number of rows.
    columns : int
        Number of columns.
    center_origin : bool
        If center_origin is True, all indices are centered around (0, 0), and some will
        be negative. Otherwise, the indices are centered around (rows//2, columns//2)

    Yields
    ------
    (x, y) : tuple[int, int]
        Indices of the next element in the spiral.
    """
    # direction: first down and then clockwise (assuming positive Y is down)

    x = y = 0
    if center_origin:  # see docstring
        xshift = yshift = 0
    else:
        xshift = (columns - 1) // 2
        yshift = (rows - 1) // 2
    dx = 0
    dy = -1
    for _ in range(max(columns, rows) ** 2):
        if (-columns / 2 < x <= columns / 2) and (-rows / 2 < y <= rows / 2):
            yield y + yshift, x + xshift
        if x == y or (x < 0 and x == -y) or (x > 0 and x == 1 - y):
            dx, dy = -dy, dx
        x, y = x + dx, y + dy


# function that iterates indices (row, col) in a grid where (0, 0) is the top left
def _rect_indices(
    rows: int, columns: int, snake: bool = False, row_wise: bool = True
) -> Iterator[Tuple[int, int]]:
    """Return a row or column-wise iterator over a 2D grid."""
    c, r = np.meshgrid(np.arange(columns), np.arange(rows))
    if snake:
        if row_wise:
            c[1::2, :] = c[1::2, :][:, ::-1]
        else:
            r[:, 1::2] = r[:, 1::2][::-1, :]
    return zip(r.ravel(), c.ravel()) if row_wise else zip(r.T.ravel(), c.T.ravel())


# used in iter_indices below, to determine the order in which indices are yielded
IndexGenerator = Callable[[int, int], Iterator[Tuple[int, int]]]
_INDEX_GENERATORS: dict[OrderMode, IndexGenerator] = {
    OrderMode.row_wise: partial(_rect_indices, snake=False, row_wise=True),
    OrderMode.column_wise: partial(_rect_indices, snake=False, row_wise=False),
    OrderMode.row_wise_snake: partial(_rect_indices, snake=True, row_wise=True),
    OrderMode.column_wise_snake: partial(_rect_indices, snake=True, row_wise=False),
    OrderMode.spiral: _spiral_indices,
}


class GridPosition(NamedTuple):
    x: float
    y: float
    row: int
    col: int
    is_relative: bool


class _GridPlan(FrozenModel):
    """Base class for all grid plans.

    Attributes
    ----------
    overlap : float | Tuple[float, float]
        Overlap between grid positions in percent. If a single value is provided, it is
        used for both x and y. If a tuple is provided, the first value is used
        for x and the second for y.
    mode : OrderMode
        Define the ways of ordering the grid positions. Options are
        row_wise, column_wise, row_wise_snake, column_wise_snake and spiral.
        By default, row_wise_snake.
    """

    overlap: Tuple[float, float] = (0.0, 0.0)
    mode: OrderMode = OrderMode.row_wise_snake

    @validator("overlap", pre=True)
    def _validate_overlap(cls, v: Any) -> Tuple[float, float]:
        if isinstance(v, float):
            return (v,) * 2
        if isinstance(v, Sequence) and len(v) == 2:
            return float(v[0]), float(v[1])
        raise ValueError(  # pragma: no cover
            "overlap must be a float or a tuple of two floats"
        )

    @property
    def is_relative(self) -> bool:
        return False

    def _offset_x(self, dx: float) -> float:
        raise NotImplementedError

    def _offset_y(self, dy: float) -> float:
        raise NotImplementedError

    def _nrows(self, dy: float) -> int:
        """Return the number of rows, given a grid step size."""
        raise NotImplementedError

    def _ncolumns(self, dx: float) -> int:
        """Return the number of columns, given a grid step size."""
        raise NotImplementedError

    def iter_grid_positions(
        self, fov_width: float, fov_height: float
    ) -> Iterator[GridPosition]:
        """Iterate over all grid positions, given a field of view size."""
        dx, dy = self._step_size(fov_width, fov_height)
        rows = self._nrows(dy)
        cols = self._ncolumns(dx)
        x0 = self._offset_x(dx)
        y0 = self._offset_y(dy)
        for r, c in _INDEX_GENERATORS[self.mode](rows, cols):
            yield GridPosition(x0 + c * dx, y0 - r * dy, r, c, self.is_relative)

    def __len__(self) -> int:
        return len(list(self.iter_grid_positions(1, 1)))

    def _step_size(self, fov_width: float, fov_height: float) -> Tuple[float, float]:
        dx = fov_width - (fov_width * self.overlap[0]) / 100
        dy = fov_height - (fov_height * self.overlap[1]) / 100
        return dx, dy


class GridFromEdges(_GridPlan):
    """Yield absolute stage positions to cover a bounded area...

    ...defined by setting the stage coordinates of the top, left,
    bottom and right edges.

    Attributes
    ----------
    top : float
        top stage position of the bounding area
    left : float
        left stage position of the bounding area
    bottom : float
        bottom stage position of the bounding area
    right : float
        right stage position of the bounding area
    """

    top: float
    left: float
    bottom: float
    right: float

    def _nrows(self, dy: float) -> int:
        total_height = abs(self.top - self.bottom) + dy
        return math.ceil(total_height / dy)

    def _ncolumns(self, dx: float) -> int:
        total_width = abs(self.right - self.left) + dx
        return math.ceil(total_width / dx)

    def _offset_x(self, dx: float) -> float:
        return min(self.left, self.right)

    def _offset_y(self, dy: float) -> float:
        return max(self.top, self.bottom)


class GridRelative(_GridPlan):
    """Yield relative delta increments to build a grid acquisition.

    Attributes
    ----------
    rows: int
        Number of rows.
    columns: int
        Number of columns.
    relative_to : RelativeTo
        Point in the grid to which the coordinates are relative. If "center", the grid
        is centered around the origin. If "top_left", the grid is positioned such that
        the top left corner is at the origin.
    """

    rows: int
    columns: int
    relative_to: RelativeTo = RelativeTo.center

    @property
    def is_relative(self) -> bool:
        return True

    def _nrows(self, dy: float) -> int:
        return self.rows

    def _ncolumns(self, dx: float) -> int:
        return self.columns

    def _offset_x(self, dx: float) -> float:
        return (
            -((self.columns - 1) * dx) / 2
            if self.relative_to == RelativeTo.center
            else 0.0
        )

    def _offset_y(self, dy: float) -> float:
        return (
            ((self.rows - 1) * dy) / 2 if self.relative_to == RelativeTo.center else 0.0
        )


AnyGridPlan = Union[GridFromEdges, GridRelative]
