from __future__ import annotations

import contextlib
import math
import warnings
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, Annotated, Any, Literal, Optional, Union

import numpy as np
from annotated_types import Ge, Gt
from pydantic import Field, field_validator, model_validator
from typing_extensions import Self, deprecated

from useq._enums import Axis, RelativeTo, Shape
from useq._point_visiting import OrderMode, TraversalOrder
from useq.v2._multi_point import MultiPositionPlan
from useq.v2._position import Position

if TYPE_CHECKING:
    import numpy as np
else:
    with contextlib.suppress(ImportError):
        pass


class _GridPlan(MultiPositionPlan):
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

    axis_key: Literal[Axis.GRID] = Field(default=Axis.GRID, frozen=True, init=False)

    overlap: tuple[float, float] = Field(default=(0.0, 0.0), frozen=True)
    mode: OrderMode = Field(default=OrderMode.row_wise_snake, frozen=True)

    @field_validator("overlap", mode="before")
    def _validate_overlap(cls, v: Any) -> tuple[float, float]:
        with contextlib.suppress(TypeError, ValueError):
            v = float(v)
        if isinstance(v, float):
            return (v, v)
        if isinstance(v, Sequence) and len(v) == 2:
            return float(v[0]), float(v[1])
        raise ValueError(  # pragma: no cover
            "overlap must be a float or a tuple of two floats"
        )

    def _step_size(self, fov_width: float, fov_height: float) -> tuple[float, float]:
        """Calculate step sizes accounting for overlap."""
        dx = fov_width - (fov_width * self.overlap[0]) / 100
        dy = fov_height - (fov_height * self.overlap[1]) / 100
        return dx, dy

    @deprecated(
        "num_positions() is deprecated, use len(grid_plan) instead.",
        category=UserWarning,
        stacklevel=2,
    )
    def num_positions(self) -> int:
        """Return the number of positions in the grid."""
        return len(self)  # type: ignore[arg-type]


class GridFromEdges(_GridPlan):
    """Yield absolute stage positions to cover a bounded area.

    The bounded area is defined by top, left, bottom and right edges in
    stage coordinates.  The bounds define the *outer* edges of the images, including
    the field of view and overlap.

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

    def __iter__(self) -> Iterator[Position]:  # type: ignore [override]
        """Iterate over grid positions to cover the bounded area."""
        fov_width = self.fov_width or 1.0
        fov_height = self.fov_height or 1.0

        dx, dy = self._step_size(fov_width, fov_height)

        # Calculate grid dimensions
        width = self.right - self.left
        height = self.top - self.bottom

        cols = max(1, math.ceil(width / dx)) if dx > 0 else 1
        rows = max(1, math.ceil(height / dy)) if dy > 0 else 1

        # Calculate starting position
        # (center of first FOV should be at grid boundary + half FOV)
        x0 = self.left + fov_width / 2
        y0 = self.top - fov_height / 2

        for idx, (row, col) in enumerate(self.mode.generate_indices(rows, cols)):
            x = x0 + col * dx
            y = y0 - row * dy
            yield Position(x=x, y=y, is_relative=False, name=f"{str(idx).zfill(4)}")

    def __len__(self) -> int:
        """Return the number of positions in the grid."""
        fov_width = self.fov_width or 1.0
        fov_height = self.fov_height or 1.0

        dx, dy = self._step_size(fov_width, fov_height)

        width = self.right - self.left
        height = self.top - self.bottom

        cols = max(1, math.ceil(width / dx)) if dx > 0 else 1
        rows = max(1, math.ceil(height / dy)) if dy > 0 else 1

        return rows * cols


class GridRowsColumns(_GridPlan):
    """Grid plan based on number of rows and columns.

    Plan will iterate rows x columns positions in the specified order.  The grid is
    centered around the origin if relative_to is "center", or positioned such that
    the top left corner is at the origin if relative_to is "top_left".

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
    relative_to: RelativeTo = Field(default=RelativeTo.center, frozen=True)

    def __iter__(self) -> Iterator[Position]:  # type: ignore[override]
        """Iterate over grid positions."""
        fov_width = self.fov_width or 1.0
        fov_height = self.fov_height or 1.0

        dx, dy = self._step_size(fov_width, fov_height)

        # Calculate starting positions based on relative_to
        if self.relative_to == RelativeTo.center:
            # Center the grid around (0, 0)
            x0 = -((self.columns - 1) * dx) / 2
            y0 = ((self.rows - 1) * dy) / 2
        else:  # top_left
            # Position grid so top-left corner is at (0, 0)
            x0 = fov_width / 2
            y0 = -fov_height / 2

        for idx, (row, col) in enumerate(
            self.mode.generate_indices(self.rows, self.columns)
        ):
            x = x0 + col * dx
            y = y0 - row * dy
            yield Position(x=x, y=y, is_relative=True, name=f"{str(idx).zfill(4)}")

    def __len__(self) -> int:
        return self.rows * self.columns


class GridWidthHeight(_GridPlan):
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

    def __iter__(self) -> Iterator[Position]:  # type: ignore[override]
        """Iterate over grid positions to cover the specified width and height."""
        fov_width = self.fov_width or 1.0
        fov_height = self.fov_height or 1.0

        dx, dy = self._step_size(fov_width, fov_height)

        # Calculate number of rows and columns needed
        cols = max(1, math.ceil(self.width / dx)) if dx > 0 else 1
        rows = max(1, math.ceil(self.height / dy)) if dy > 0 else 1

        # Calculate starting positions based on relative_to
        if self.relative_to == RelativeTo.center:
            # Center the grid around (0, 0)
            x0 = -((cols - 1) * dx) / 2
            y0 = ((rows - 1) * dy) / 2
        else:  # top_left
            # Position grid so top-left corner is at (0, 0)
            x0 = fov_width / 2
            y0 = -fov_height / 2

        for idx, (row, col) in enumerate(self.mode.generate_indices(rows, cols)):
            x = x0 + col * dx
            y = y0 - row * dy
            yield Position(x=x, y=y, is_relative=True, name=f"{str(idx).zfill(4)}")

    def __len__(self) -> int:
        """Return the number of positions in the grid."""
        fov_width = self.fov_width or 1.0
        fov_height = self.fov_height or 1.0

        dx, dy = self._step_size(fov_width, fov_height)

        cols = max(1, math.ceil(self.width / dx)) if dx > 0 else 1
        rows = max(1, math.ceil(self.height / dy)) if dy > 0 else 1

        return rows * cols


# ------------------------ RANDOM ------------------------


class RandomPoints(MultiPositionPlan):
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

    axis_key: Literal[Axis.GRID] = Field(default=Axis.GRID, frozen=True, init=False)

    num_points: Annotated[int, Gt(0)]
    max_width: Annotated[float, Gt(0)] = 1
    max_height: Annotated[float, Gt(0)] = 1
    shape: Shape = Shape.ELLIPSE
    random_seed: Optional[int] = None
    allow_overlap: bool = True
    order: Optional[TraversalOrder] = TraversalOrder.TWO_OPT
    start_at: Union[Position, Annotated[int, Ge(0)]] = 0

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

    def __len__(self) -> int:
        return self.num_points

    def __iter__(self) -> Iterator[Position]:  # type: ignore[override]
        """Generate random points based on the specified parameters."""
        import numpy as np

        seed = np.random.RandomState(self.random_seed)

        points: list[tuple[float, float]] = []
        needed_points = self.num_points
        start_at = self.start_at

        # If start_at is a Position, add it to points first
        if isinstance(start_at, Position):
            if start_at.x is not None and start_at.y is not None:
                points = [(start_at.x, start_at.y)]
                needed_points -= 1
            start_at = 0

        # Generate points based on shape
        if self.shape == Shape.ELLIPSE:
            # Generate points within an ellipse
            _points = self._random_points_in_ellipse(
                seed, needed_points, self.max_width, self.max_height
            )
        else:  # RECTANGLE
            # Generate points within a rectangle
            _points = self._random_points_in_rectangle(
                seed, needed_points, self.max_width, self.max_height
            )

        # Handle overlap prevention if required
        if (
            not self.allow_overlap
            and self.fov_width is not None
            and self.fov_height is not None
        ):
            # Filter points to avoid overlap
            filtered_points: list[tuple[float, float]] = []
            for x, y in _points:
                if self._is_valid_point(
                    points + filtered_points, x, y, self.fov_width, self.fov_height
                ):
                    filtered_points.append((x, y))
                    if len(filtered_points) >= needed_points:
                        break

            if len(filtered_points) < needed_points:
                warnings.warn(
                    f"Unable to generate {self.num_points} non-overlapping points. "
                    f"Only {len(points) + len(filtered_points)} points were found.",
                    stacklevel=2,
                )
            points.extend(filtered_points)
        else:
            points.extend(_points)

        # Apply traversal ordering if specified
        if self.order is not None and len(points) > 1:
            points_array = np.array(points)
            if isinstance(self.start_at, int):
                start_at = min(self.start_at, len(points) - 1)
            else:
                start_at = 0
            order = self.order.order_points(points_array, start_at=start_at)
            points = [points[i] for i in order]

        # Yield Position objects
        for idx, (x, y) in enumerate(points):
            yield Position(x=x, y=y, is_relative=True, name=f"{str(idx).zfill(4)}")

    def _random_points_in_ellipse(
        self,
        seed: np.random.RandomState,
        n_points: int,
        max_width: float,
        max_height: float,
    ) -> list[tuple[float, float]]:
        """Generate random points within an ellipse."""
        import numpy as np

        points = seed.uniform(0, 1, size=(n_points, 3))
        xy = points[:, :2]
        angle = points[:, 2] * 2 * np.pi

        # Generate points within ellipse using polar coordinates
        r = np.sqrt(xy[:, 0])  # sqrt for uniform distribution within circle
        xy[:, 0] = r * (max_width / 2) * np.cos(angle)
        xy[:, 1] = r * (max_height / 2) * np.sin(angle)

        return [(float(x), float(y)) for x, y in xy]

    def _random_points_in_rectangle(
        self,
        seed: np.random.RandomState,
        n_points: int,
        max_width: float,
        max_height: float,
    ) -> list[tuple[float, float]]:
        """Generate random points within a rectangle."""
        xy = seed.uniform(0, 1, size=(n_points, 2))
        xy[:, 0] = (xy[:, 0] * max_width) - (max_width / 2)
        xy[:, 1] = (xy[:, 1] * max_height) - (max_height / 2)

        return [(float(x), float(y)) for x, y in xy]

    def _is_valid_point(
        self,
        existing_points: list[tuple[float, float]],
        x: float,
        y: float,
        min_dist_x: float,
        min_dist_y: float,
    ) -> bool:
        """Check if a point is valid (doesn't overlap with existing points)."""
        for px, py in existing_points:
            if abs(x - px) < min_dist_x and abs(y - py) < min_dist_y:
                return False
        return True


# all of these support __iter__() -> Iterator[Position] and len() -> int
RelativeMultiPointPlan = Union[GridRowsColumns, GridWidthHeight, RandomPoints]
AbsoluteMultiPointPlan = Union[GridFromEdges]
MultiPointPlan = Union[AbsoluteMultiPointPlan, RelativeMultiPointPlan]
