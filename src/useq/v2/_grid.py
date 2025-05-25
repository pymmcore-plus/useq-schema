from __future__ import annotations

import contextlib
import warnings
from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, Annotated, Any, Optional, Union

from annotated_types import Ge, Gt
from pydantic import Field, field_validator, model_validator
from typing_extensions import Self

from useq._enums import RelativeTo, Shape
from useq._point_visiting import OrderMode, TraversalOrder
from useq.v2._multi_point import MultiPositionPlan

if TYPE_CHECKING:
    from useq.v1._position import Position


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

    overlap: tuple[float, float] = Field((0.0, 0.0), frozen=True)
    mode: OrderMode = Field(OrderMode.row_wise_snake, frozen=True)

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

    def __iter__(self) -> Iterator[Position]: ...

    def __len__(self) -> int: ...


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
    relative_to: RelativeTo = Field(RelativeTo.center, frozen=True)

    def __iter__(self) -> Iterator[Position]: ...

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

    def __iter__(self) -> Iterator[Position]: ...

    def __len__(self) -> int: ...


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

    def __iter__(self) -> Iterator[Position]: ...


# all of these support __iter__() -> Iterator[Position] and len() -> int
RelativeMultiPointPlan = Union[GridRowsColumns, GridWidthHeight, RandomPoints]
AbsoluteMultiPointPlan = Union[GridFromEdges]
MultiPointPlan = Union[AbsoluteMultiPointPlan, RelativeMultiPointPlan]
