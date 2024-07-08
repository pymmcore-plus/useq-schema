from __future__ import annotations

import contextlib
import math
import warnings
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Iterator,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import numpy as np
from annotated_types import Ge, Gt  # noqa: TCH002
from pydantic import Field, field_validator, model_validator

from useq._point_visiting import OrderMode, TraversalOrder
from useq._position import (
    AbsolutePosition,
    PositionT,
    RelativePosition,
    _MultiPointPlan,
)

if TYPE_CHECKING:
    from typing_extensions import Annotated, Self, TypeAlias

    PointGenerator: TypeAlias = Callable[
        [np.random.RandomState, int, float, float], Iterable[tuple[float, float]]
    ]

MIN_RANDOM_POINTS = 10000


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


# used in iter_indices below, to determine the order in which indices are yielded
class _GridPlan(_MultiPointPlan[PositionT]):
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
            # type ignore is because mypy thinks self is Never here...
            self.fov_width is None or self.fov_height is None  # type: ignore [attr-defined]
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
        order: OrderMode | None = None,
    ) -> Iterator[PositionT]:
        """Iterate over all grid positions, given a field of view size."""
        _fov_width = fov_width or self.fov_width or 1.0
        _fov_height = fov_height or self.fov_height or 1.0
        order = self.mode if order is None else OrderMode(order)

        dx, dy = self._step_size(_fov_width, _fov_height)
        rows = self._nrows(dy)
        cols = self._ncolumns(dx)
        x0 = self._offset_x(dx)
        y0 = self._offset_y(dy)

        pos_cls = RelativePosition if self.is_relative else AbsolutePosition
        for idx, (r, c) in enumerate(order.generate_indices(rows, cols)):
            yield pos_cls(
                x=x0 + c * dx,
                y=y0 - r * dy,
                row=r,
                col=c,
                name=f"{str(idx).zfill(4)}",
            )

    def __iter__(self) -> Iterator[PositionT]:  # type: ignore [override]
        yield from self.iter_grid_positions()

    def _step_size(self, fov_width: float, fov_height: float) -> Tuple[float, float]:
        dx = fov_width - (fov_width * self.overlap[0]) / 100
        dy = fov_height - (fov_height * self.overlap[1]) / 100
        return dx, dy


class GridFromEdges(_GridPlan[AbsolutePosition]):
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

    @property
    def is_relative(self) -> bool:
        return False

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


class GridRowsColumns(_GridPlan[RelativePosition]):
    """Grid plan based on number of rows and columns.

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


class GridWidthHeight(_GridPlan[RelativePosition]):
    """Grid plan based on total width and height.

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


class RandomPoints(_MultiPointPlan[RelativePosition]):
    """Yield random points in a specified geometric shape.

    Attributes
    ----------
    num_points : int
        Number of points to generate.
    max_width : float
        Maximum width of the bounding box in microns.
    max_height : float
        Maximum height of the bounding box in microns.
    shape : Shape
        Shape of the bounding box. Current options are "ellipse" and "rectangle".
    random_seed : Optional[int]
        Random numpy seed that should be used to generate the points. If None, a random
        seed will be used.
    allow_overlap : bool
        By defaut, True. If False and `fov_width` and `fov_height` are specified, points
        will not overlap and will be at least `fov_width` and `fov_height apart.
    order : TraversalOrder
        Order in which the points will be visited. If None, order is simply the order
        in which the points are generated (random).  Use 'nearest_neighbor' or
        'two_opt' to order the points in a more structured way.
    start_at : int | RelativePosition
        Position or index of the point to start at. This is only used if `order` is
        'nearest_neighbor' or 'two_opt'.  If a position is provided, it will *always*
        be included in the list of points. If an index is provided, it must be less than
        the number of points, and corresponds to the index of the (randomly generated)
        points; this likely only makes sense when `random_seed` is provided.
    """

    num_points: Annotated[int, Gt(0)]
    max_width: Annotated[float, Gt(0)] = 1
    max_height: Annotated[float, Gt(0)] = 1
    shape: Shape = Shape.ELLIPSE
    random_seed: Optional[int] = None
    allow_overlap: bool = True
    order: Optional[TraversalOrder] = TraversalOrder.TWO_OPT
    start_at: Union[RelativePosition, Annotated[int, Ge(0)]] = 0

    @model_validator(mode="after")
    def _validate_startat(self) -> Self:
        if isinstance(self.start_at, int) and self.start_at > (self.num_points - 1):
            warnings.warn(
                "start_at is greater than the number of points. "
                "Setting start_at to last point.",
                stacklevel=2,
            )
            self.start_at = self.num_points - 1
        return self

    def __iter__(self) -> Iterator[RelativePosition]:  # type: ignore [override]
        seed = np.random.RandomState(self.random_seed)
        func = _POINTS_GENERATORS[self.shape]

        points: list[Tuple[float, float]] = []
        needed_points = self.num_points
        start_at = self.start_at
        if isinstance(start_at, RelativePosition):
            points = [(start_at.x, start_at.y)]
            needed_points -= 1
            start_at = 0

        # in the easy case, just generate the requested number of points
        if self.allow_overlap or self.fov_width is None or self.fov_height is None:
            _points = func(seed, needed_points, self.max_width, self.max_height)
            points.extend(_points)

        else:
            # if we need to avoid overlap, generate points, check if they are valid, and
            # repeat until we have enough
            per_iter = needed_points
            tries = 0
            while tries < MIN_RANDOM_POINTS and len(points) < self.num_points:
                candidates = func(seed, per_iter, self.max_width, self.max_height)
                tries += per_iter
                for p in candidates:
                    if _is_a_valid_point(points, *p, self.fov_width, self.fov_height):
                        points.append(p)
                        if len(points) >= self.num_points:
                            break

            if len(points) < self.num_points:
                warnings.warn(
                    f"Unable to generate {self.num_points} non-overlapping points. "
                    f"Only {len(points)} points were found.",
                    stacklevel=2,
                )

        if self.order is not None:
            points = self.order(points, start_at=start_at)  # type: ignore [assignment]

        for idx, (x, y) in enumerate(points):
            yield RelativePosition(x=x, y=y, name=f"{str(idx).zfill(4)}")

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
    points = seed.uniform(0, 1, size=(n_points, 3))
    xy = points[:, :2]
    angle = points[:, 2] * 2 * np.pi
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


_POINTS_GENERATORS: dict[Shape, PointGenerator] = {
    Shape.ELLIPSE: _random_points_in_ellipse,
    Shape.RECTANGLE: _random_points_in_rectangle,
}


# all of these support __iter__() -> Iterator[PositionBase] and num_positions() -> int
RelativeMultiPointPlan = Union[
    GridRowsColumns, GridWidthHeight, RandomPoints, RelativePosition
]
AbsoluteMultiPointPlan = Union[GridFromEdges]
MultiPointPlan = Union[AbsoluteMultiPointPlan, RelativeMultiPointPlan]
