from __future__ import annotations

import contextlib
import math
import warnings
from collections.abc import Iterable, Iterator, Sequence
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Callable,
    Optional,
    Union,
)

import numpy as np
from annotated_types import Ge, Gt
from pydantic import Field, field_validator, model_validator
from typing_extensions import Self, TypeAlias

from useq._point_visiting import OrderMode, TraversalOrder
from useq._position import (
    AbsolutePosition,
    PositionT,
    RelativePosition,
    _MultiPointPlan,
)

try:
    import shapely

    shapely_installed = True
except:
    print("shapely can't be imported, polygon offsetting is not supported")
    shapely_installed = False
if TYPE_CHECKING:
    from matplotlib.axes import Axes

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

    center = "center"
    top_left = "top_left"


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

    overlap: tuple[float, float] = Field((0.0, 0.0), frozen=True)
    mode: OrderMode = Field(OrderMode.row_wise_snake, frozen=True)

    @field_validator("overlap", mode="before")
    def _validate_overlap(cls, v: Any) -> tuple[float, float]:
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
            yield pos_cls(  # type: ignore [misc]
                x=x0 + c * dx,
                y=y0 - r * dy,
                row=r,
                col=c,
                name=f"{str(idx).zfill(4)}",
            )

    def __iter__(self) -> Iterator[PositionT]:  # type: ignore [override]
        yield from self.iter_grid_positions()

    def _step_size(self, fov_width: float, fov_height: float) -> tuple[float, float]:
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

    def plot(self, *, show: bool = True) -> Axes:
        """Plot the positions in the plan."""
        from useq._plot import plot_points

        if self.fov_width is not None and self.fov_height is not None:
            rect = (self.fov_width, self.fov_height)
        else:
            rect = None

        return plot_points(
            self,
            rect_size=rect,
            bounding_box=(self.left, self.top, self.right, self.bottom),
            show=show,
        )


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


class GridFromPolygon(_GridPlan[AbsolutePosition]):
    """Yield absolute stage positions to cover a polygon.

    Input:A polygon with(out) hole(s), extra argument to fill holes or not within the polygon,
        whether to apply a convex hull, and option to offset the polygon with a certain size.

    Attributes
    ----------
    polygon : list[tuple[float,float]]
        list of minimum 3 points/vertices of a polygon in yx.
        '[[y,x],[y,x],[y,x].....]
    convex hull Optional[boolean]:
        True to create a convex hull from the polygon
    overlap : float | tuple[float, float]
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

    # TODO add buffer argument to vary offset: float = Field((fov_width*fov_height)/2,frozen=False)
    # TODO remove shapely code in _offset_polygon()
    # TODO instead of offsetting the polygon, maybe shrink the grid towards the centroid of the polygon?
    ##Alternative for shapely import:
    # https://github.com/karimbahgat/Shapy/blob/master/shapy/geometry.py
    # https://medium.com/@gurbuzkaanakkaya/polygon-buffering-algorithm-generating-buffer-points-228ed062fdf9
    # python only:
    # https://github.com/karimbahgat/Shapy #specifically:line 543 https://github.com/karimbahgat/Shapy/blob/master/shapy/geometry.py
    # https://github.com/chalk-diagrams/planar

    polygon: Annotated[
        list[tuple[float, float]],
        Field(
            ...,
            min_length=3,
            description="List of points that define the polygon, must be at least 3 points",
            frozen=False,
        ),
    ]
    convex_hull: bool = Field(
        False,
        description="If True, the convex hull will be used.",
    )
    top_all: Annotated[Optional[float], Field(None, init=True)]
    left_all: Annotated[Optional[float], Field(None, init=True)]
    bottom_all: Annotated[Optional[float], Field(None, init=True)]
    right_all: Annotated[Optional[float], Field(None, init=True)]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.top_all, self.left_all, self.bottom_all, self.right_all = (
            self._bounding_box_of_polygon()
        )

    def _max_value(self, edges_list: Optional[list] = None) -> list[float]:
        if edges_list is None:
            edges_list = []
        max_values = [0, 0, 0, 0]
        ##In case of yx points, instead of top,left,bottom,right, duplicate the values.
        edges_list = list(edges_list)
        if len(edges_list[0]) == 2:
            for idx, value in enumerate(edges_list):
                edges_list[idx] = value + value
        for idx in range(len(max_values)):
            for grid in edges_list:
                if grid[idx] >= max_values[idx]:
                    max_values[idx] = grid[idx]
        print(f"max_values: bounding box: {max_values}")
        return max_values

    def _min_value(self, edges_list: Optional[list] = None) -> list[float]:
        if edges_list is None:
            edges_list = []
        min_values = list(self._max_value(edges_list))
        self.right_all, self.bottom_all, *_ = min_values[::-1]
        edges_list = list(edges_list)
        if len(edges_list[0]) == 2:
            for idx, value in enumerate(edges_list):
                edges_list[idx] = value + value
        for idx in range(len(min_values)):
            for grid in edges_list:
                if grid[idx] <= min_values[idx]:
                    min_values[idx] = grid[idx]
        return min_values  # , list(self._max_value())

    def _bounding_box_of_polygon(self) -> list[float, float, float, float]:
        self.top_all, self.left_all, *_ = self._min_value(self.polygon)
        # print(f"bounding box of polygon; top: {self.top_all}, left: {self.left_all}, bottom: {self.bottom_all}, right: {self.right_all}")
        return self.top_all, self.left_all, self.bottom_all, self.right_all

    def _convert_bounding_boxes_to_polygon_vertices(
        self, list_of_bounding_boxes
    ) -> list:
        """Generates a list of YX points top_left_bottom_right, rewriting to XY may make more sense."""
        if len(list_of_bounding_boxes[0]) == 4:
            vertices = []
            for box in list_of_bounding_boxes:
                top, left, bottom, right = box  # bottom, right
                vertices.extend(
                    [(top, left), (top, right), (bottom, left), (bottom, right)]
                )
            return vertices
        else:
            vertices = list_of_bounding_boxes
            return vertices

    def _offset_polygon(self, vertices) -> list:
        vertices = tuple(vertices)
        geom = shapely.Polygon(vertices)
        vertices = geom.buffer(
            distance=(self.fov_height + self.fov_width) / 3,
            cap_style="round",
            join_style="round",
        )
        vertices = list(vertices.exterior.coords)
        return vertices

    def _convex_hull(self, vertices) -> list:
        """Computes the convex hull of a set of 2D points.
        Input: an iterable sequence of (x, y) pairs representing the points.
        Output: a list of vertices of the convex hull in counter-clockwise order,
        starting from the vertex with the lexicographically smallest coordinates.
        Implements Andrew's monotone chain algorithm. O(n log n) complexity.
        source:
        https://en.wikibooks.org/wiki/Algorithm_Implementation/Geometry/Convex_hull/Monotone_chain#Python.
        """
        # Sort the points lexicographically (tuples are compared lexicographically).
        # Remove duplicates to detect the case we have just one unique point.
        vertices = sorted(set(vertices))
        # Boring case: no points or a single point, possibly repeated multiple times.\
        if len(vertices) <= 1:
            return vertices

        # 2D cross product of OA and OB vectors, i.e. z-component of their 3D cross product.
        # Returns a positive value, if OAB makes a counter-clockwise turn,
        # negative for clockwise turn, and zero if the points are collinear.
        def cross(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

        # Build lower hull
        lower = []
        for p in vertices:
            while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)
        # Build upper hull
        upper = []
        for p in reversed(vertices):
            while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)
        # Concatenation of the lower and upper hulls gives the convex hull.
        # Last point of each list is omitted because it is repeated at the beginning of the other list.
        return lower[:-1] + upper[:-1]

    def _point_inside_polygon(
        self, point: PositionT, polygon_vertices: list[float, float]
    ) -> bool:
        # TODO raycasting or windingnumber
        """Ray casting algorithm to check for each position if it is inside polygon."""
        shift_to_center = True
        if shift_to_center:
            x, y = (
                point.x + (self.fov_width * (1 - self.overlap[0] / 100) / 2),
                point.y + (self.fov_height * (1 - self.overlap[1] / 100) / 2),
            )
        else:
            x, y = point.x, point.y
        inside = False
        for p1, p2 in zip(
            polygon_vertices, polygon_vertices[1:] + [polygon_vertices[0]]
        ):
            p1y, p1x = p1  # edge 1
            p2y, p2x = p2  # edge 2
            if (p1y <= y and y < p2y) or (p2y <= y and y < p1y):
                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                if x <= xinters:
                    inside = not inside
        return inside

    def _intersect_raster_with_polygon(self) -> Iterator[PositionT]:
        """
        #TODO determine whether centroid and sort order is to be asserted.
        #TODO Keeping the refinement step may be cleaner outside the method.
        Refine the polygon by offsetting and/or.
        """
        polygon_vertices = self.polygon
        if shapely_installed:
            ##Dilates the polygon
            polygon_vertices = self._offset_polygon(polygon_vertices)
        if self.convex_hull:
            polygon_vertices = self._convex_hull(polygon_vertices)

        grid_from_bounding_box = self.iter_grid_positions()

        for position in list(grid_from_bounding_box):
            if self._point_inside_polygon(
                point=position, polygon_vertices=polygon_vertices
            ):
                yield position

    @property
    def is_relative(self) -> bool:
        return False

    def _nrows(self, dy: float) -> int:
        total_height = abs(self.top_all - self.bottom_all) + dy
        return math.ceil(total_height / dy)

    def _ncolumns(self, dx: float) -> int:
        total_width = abs(self.right_all - self.left_all) + dx
        return math.ceil(total_width / dx)

    def _offset_x(self, dx: float) -> float:
        return min(self.left_all, self.right_all)

    def _offset_y(self, dy: float) -> float:
        return max(self.top_all, self.bottom_all)

    def num_positions(self):
        # TODO write _num_positions() to not reflect rows * columns, but the actual positions.
        # return len(list(self.intersect_raster_with_polygon()))
        return "To get the number of tiles within the polygon: len(list(mda_sequence.grid_plan.__iter__()))"

    def __iter__(self) -> Iterator[PositionT]:
        yield from self._intersect_raster_with_polygon()


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

        points: list[tuple[float, float]] = []
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
    points: list[tuple[float, float]],
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
AbsoluteMultiPointPlan = Union[GridFromEdges, GridFromPolygon]
MultiPointPlan = Union[AbsoluteMultiPointPlan, RelativeMultiPointPlan]
