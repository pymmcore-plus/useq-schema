from __future__ import annotations

import contextlib
import math
import warnings
from enum import Enum
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Iterator,
    Literal,  # noqa: F401
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import numpy as np
from pydantic_compat import Field, field_validator

from useq._base_model import FrozenModel

if TYPE_CHECKING:
    from pydantic import ConfigDict

MIN_RANDOM_POINTS = 5000


class RelativeTo(Enum):
    """Where the coordinates of the grid are relative to.

    Attributes
    ----------
    center : Literal['center']
        Grid is centered around the origin.
    top_left : Literal['top_left']
        Grid is positioned such that the top left corner is at the origin.
    """

    center: str = "center"
    top_left: str = "top_left"


class OrderMode(Enum):
    """Order in which grid positions will be iterated.

    Attributes
    ----------
    row_wise : Literal['row_wise']
        Iterate row by row.
    column_wise : Literal['column_wise']
        Iterate column by column.
    row_wise_snake : Literal['row_wise_snake']
        Iterate row by row, but alternate the direction of the columns.
    column_wise_snake : Literal['column_wise_snake']
        Iterate column by column, but alternate the direction of the rows.
    spiral : Literal['spiral']
        Iterate in a spiral pattern, starting from the center.
    """

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


class _PointsPlan(FrozenModel):
    # Overriding FrozenModel to make fov_width and fov_height mutable.
    model_config: ClassVar[ConfigDict] = {"validate_assignment": True, "frozen": False}

    fov_width: Optional[float] = Field(None)
    fov_height: Optional[float] = Field(None)

    @property
    def is_relative(self) -> bool:
        return False

    def __iter__(self) -> Iterator[GridPosition]:  # type: ignore
        raise NotImplementedError("This method must be implemented by subclasses.")

    def num_positions(self) -> int:
        raise NotImplementedError("This method must be implemented by subclasses.")


class _GridPlan(_PointsPlan):
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
    fov_width : Optional[float]
        Width of the field of view in microns.  If not provided, acquisition engines
        should use current width of the FOV based on the current objective and camera.
        Engines MAY override this even if provided.
    fov_height : Optional[float]
        Height of the field of view in microns. If not provided, acquisition engines
        should use current height of the FOV based on the current objective and camera.
        Engines MAY override this even if provided.
    """

    overlap: Tuple[float, float] = Field((0.0, 0.0), frozen=True)
    mode: OrderMode = Field(OrderMode.row_wise_snake, frozen=True)

    @field_validator("overlap", mode="before")
    def _validate_overlap(cls, v: Any) -> Tuple[float, float]:
        with contextlib.suppress(TypeError, ValueError):
            v = float(v)
        if isinstance(v, float):
            return (v,) * 2
        if isinstance(v, Sequence) and len(v) == 2:
            return float(v[0]), float(v[1])
        raise ValueError(  # pragma: no cover
            "overlap must be a float or a tuple of two floats"
        )

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

    def num_positions(self) -> int:
        """Return the number of individual positions in the grid.

        Note: For GridFromEdges and GridWidthHeight, this will depend on field of view
        size. If no field of view size is provided, the number of positions will be 1.
        """
        if isinstance(self, (GridFromEdges, GridWidthHeight)) and (
            self.fov_width is None or self.fov_height is None
        ):
            raise ValueError(
                "Retrieving the number of positions in a GridFromEdges or "
                "GridWidthHeight plan requires the field of view size to be set."
            )

        dx, dy = self._step_size(self.fov_width or 1, self.fov_height or 1)
        rows = self._nrows(dy)
        cols = self._ncolumns(dx)
        return rows * cols

    def iter_grid_positions(
        self,
        fov_width: float | None = None,
        fov_height: float | None = None,
        *,
        mode: OrderMode | None = None,
    ) -> Iterator[GridPosition]:
        """Iterate over all grid positions, given a field of view size."""
        _fov_width = fov_width or self.fov_width or 1.0
        _fov_height = fov_height or self.fov_height or 1.0
        mode = self.mode if mode is None else OrderMode(mode)

        dx, dy = self._step_size(_fov_width, _fov_height)
        rows = self._nrows(dy)
        cols = self._ncolumns(dx)
        x0 = self._offset_x(dx)
        y0 = self._offset_y(dy)

        for r, c in _INDEX_GENERATORS[mode](rows, cols):
            yield GridPosition(x0 + c * dx, y0 - r * dy, r, c, self.is_relative)

    def __iter__(self) -> Iterator[GridPosition]:  # type: ignore
        yield from self.iter_grid_positions()

    def _step_size(self, fov_width: float, fov_height: float) -> Tuple[float, float]:
        dx = fov_width - (fov_width * self.overlap[0]) / 100
        dy = fov_height - (fov_height * self.overlap[1]) / 100
        return dx, dy


class GridFromEdges(_GridPlan):
    """Yield absolute stage positions to cover a bounded area.

    The bounded area is defined by top, left, bottom and right edges in
    stage coordinates.

    Attributes
    ----------
    top : float
        Top stage position of the bounding area
    left : float
        Left stage position of the bounding area
    bottom : float
        Bottom stage position of the bounding area
    right : float
        Right stage position of the bounding area
    overlap : float | Tuple[float, float]
        Overlap between grid positions in percent. If a single value is provided, it is
        used for both x and y. If a tuple is provided, the first value is used
        for x and the second for y.
    mode : OrderMode
        Define the ways of ordering the grid positions. Options are
        row_wise, column_wise, row_wise_snake, column_wise_snake and spiral.
        By default, row_wise_snake.
    fov_width : Optional[float]
        Width of the field of view in microns.  If not provided, acquisition engines
        should use current width of the FOV based on the current objective and camera.
        Engines MAY override this even if provided.
    fov_height : Optional[float]
        Height of the field of view in microns. If not provided, acquisition engines
        should use current height of the FOV based on the current objective and camera.
        Engines MAY override this even if provided.
    """

    # everything but fov_width and fov_height is immutable
    top: float = Field(..., frozen=True)
    left: float = Field(..., frozen=True)
    bottom: float = Field(..., frozen=True)
    right: float = Field(..., frozen=True)

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


class GridRowsColumns(_GridPlan):
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
    overlap : float | Tuple[float, float]
        Overlap between grid positions in percent. If a single value is provided, it is
        used for both x and y. If a tuple is provided, the first value is used
        for x and the second for y.
    mode : OrderMode
        Define the ways of ordering the grid positions. Options are
        row_wise, column_wise, row_wise_snake, column_wise_snake and spiral.
        By default, row_wise_snake.
    fov_width : Optional[float]
        Width of the field of view in microns.  If not provided, acquisition engines
        should use current width of the FOV based on the current objective and camera.
        Engines MAY override this even if provided.
    fov_height : Optional[float]
        Height of the field of view in microns. If not provided, acquisition engines
        should use current height of the FOV based on the current objective and camera.
        Engines MAY override this even if provided.
    """

    # everything but fov_width and fov_height is immutable
    rows: int = Field(..., frozen=True, ge=1)
    columns: int = Field(..., frozen=True, ge=1)
    relative_to: RelativeTo = Field(RelativeTo.center, frozen=True)

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


GridRelative = GridRowsColumns


class GridWidthHeight(_GridPlan):
    """Yield relative delta increments to build a grid acquisition.

    Attributes
    ----------
    width: float
        Minimum total width of the grid, in microns. (may be larger based on fov_width)
    height: float
        Minimum total height of the grid, in microns. (may be larger based on
        fov_height)
    relative_to : RelativeTo
        Point in the grid to which the coordinates are relative. If "center", the grid
        is centered around the origin. If "top_left", the grid is positioned such that
        the top left corner is at the origin.
    overlap : float | Tuple[float, float]
        Overlap between grid positions in percent. If a single value is provided, it is
        used for both x and y. If a tuple is provided, the first value is used
        for x and the second for y.
    mode : OrderMode
        Define the ways of ordering the grid positions. Options are
        row_wise, column_wise, row_wise_snake, column_wise_snake and spiral.
        By default, row_wise_snake.
    fov_width : Optional[float]
        Width of the field of view in microns.  If not provided, acquisition engines
        should use current width of the FOV based on the current objective and camera.
        Engines MAY override this even if provided.
    fov_height : Optional[float]
        Height of the field of view in microns. If not provided, acquisition engines
        should use current height of the FOV based on the current objective and camera.
        Engines MAY override this even if provided.
    """

    width: float = Field(..., frozen=True, gt=0)
    height: float = Field(..., frozen=True, gt=0)
    relative_to: RelativeTo = Field(RelativeTo.center, frozen=True)

    @property
    def is_relative(self) -> bool:
        return True

    def _nrows(self, dy: float) -> int:
        return math.ceil(self.height / dy)

    def _ncolumns(self, dx: float) -> int:
        return math.ceil(self.width / dx)

    def _offset_x(self, dx: float) -> float:
        return (
            -((self._ncolumns(dx) - 1) * dx) / 2
            if self.relative_to == RelativeTo.center
            else 0.0
        )

    def _offset_y(self, dy: float) -> float:
        return (
            ((self._nrows(dy) - 1) * dy) / 2
            if self.relative_to == RelativeTo.center
            else 0.0
        )


# ------------------------ RANDOM ------------------------


class Shape(Enum):
    """Shape of the bounding box for random points.

    Attributes
    ----------
    ELLIPSE : Literal['ellipse']
        The bounding box is an ellipse.
    RECTANGLE : Literal['rectangle']
        The bounding box is a rectangle.
    """

    ELLIPSE = "ellipse"
    RECTANGLE = "rectangle"


class RandomPoints(_PointsPlan):
    """Yield random points in a specified geometric shape.

    Attributes
    ----------
    num_points : int
        Number of points to generate.
    max_width : float
        Maximum width of the bounding box.
    max_height : float
        Maximum height of the bounding box.
    shape : Shape
        Shape of the bounding box. Current options are "ellipse" and "rectangle".
    random_seed : Optional[int]
        Random numpy seed that should be used to generate the points. If None, a random
        seed will be used.
    allow_overlap : bool
        By defaut, True. If False and `fov_width` and `fov_height` are specified, points
        will not overlap and will be at least `fov_width` and `fov_height apart.
    """

    num_points: int
    max_width: float
    max_height: float
    shape: Shape
    random_seed: Optional[int] = None
    allow_overlap: bool = True

    @property
    def is_relative(self) -> bool:
        return True

    def __iter__(self) -> Iterator[GridPosition]:  # type: ignore
        seed = np.random.RandomState(self.random_seed)
        func = _POINTS_GENERATORS[self.shape]
        n_points = max(self.num_points, MIN_RANDOM_POINTS)
        points: list[Tuple[float, float]] = []
        for x, y in func(seed, n_points, self.max_width, self.max_height):
            if (
                self.allow_overlap
                or self.fov_width is None
                or self.fov_height is None
                or _is_a_valid_point(points, x, y, self.fov_width, self.fov_height)
            ):
                yield GridPosition(x, y, 0, 0, True)
                points.append((x, y))
            if len(points) >= self.num_points:
                break
        else:
            warnings.warn(
                f"Unable to generate {self.num_points} non-overlapping points. "
                f"Only {len(points)} points were found.",
                stacklevel=2,
            )

    def num_positions(self) -> int:
        return self.num_points


def _is_a_valid_point(
    points: list[Tuple[float, float]],
    x: float,
    y: float,
    min_dist_x: float,
    min_dist_y: float,
) -> bool:
    """Return True if the the point is at least min_dist away from all the others.

    note: using Manhattan distance.
    """
    return not any(
        abs(x - point_x) < min_dist_x and abs(y - point_y) < min_dist_y
        for point_x, point_y in points
    )


def _random_points_in_ellipse(
    seed: np.random.RandomState, n_points: int, max_width: float, max_height: float
) -> np.ndarray:
    """Generate a random point around a circle with center (0, 0).

    The point is within +/- radius_x and +/- radius_y at a random angle.
    """
    xy = np.sqrt(seed.uniform(0, 1, size=(n_points, 2)))
    angle = seed.uniform(0, 2 * np.pi, size=n_points)
    xy[:, 0] *= (max_width / 2) * np.cos(angle)
    xy[:, 1] *= (max_height / 2) * np.sin(angle)
    return xy


def _random_points_in_rectangle(
    seed: np.random.RandomState, n_points: int, max_width: float, max_height: float
) -> np.ndarray:
    """Generate a random point around a rectangle with center (0, 0).

    The point is within the bounding box (-width/2, -height/2, width, height).
    """
    xy = seed.uniform(0, 1, size=(n_points, 2))
    xy[:, 0] = (xy[:, 0] * max_width) - (max_width / 2)
    xy[:, 1] = (xy[:, 1] * max_height) - (max_height / 2)
    return xy


PointGenerator = Callable[[np.random.RandomState, int, float, float], np.ndarray]
_POINTS_GENERATORS: dict[Shape, PointGenerator] = {
    Shape.ELLIPSE: _random_points_in_ellipse,
    Shape.RECTANGLE: _random_points_in_rectangle,
}


AnyGridPlan = Union[GridFromEdges, GridRowsColumns, GridWidthHeight, RandomPoints]
