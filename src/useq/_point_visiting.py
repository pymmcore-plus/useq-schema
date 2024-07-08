from __future__ import annotations

from enum import Enum
from functools import partial
from typing import Callable, Iterable, Iterator, Tuple

import numpy as np

# ----------------------------- Random Points -----------------------------------


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

    def generate_indices(self, rows: int, columns: int) -> Iterator[Tuple[int, int]]:
        """Generate indices for the given grid size."""
        return _INDEX_GENERATORS[self](rows, columns)


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


IndexGenerator = Callable[[int, int], Iterator[Tuple[int, int]]]
_INDEX_GENERATORS: dict[OrderMode, IndexGenerator] = {
    OrderMode.row_wise: partial(_rect_indices, snake=False, row_wise=True),
    OrderMode.column_wise: partial(_rect_indices, snake=False, row_wise=False),
    OrderMode.row_wise_snake: partial(_rect_indices, snake=True, row_wise=True),
    OrderMode.column_wise_snake: partial(_rect_indices, snake=True, row_wise=False),
    OrderMode.spiral: _spiral_indices,
}

# ----------------------------- Random Points -----------------------------------


class TraversalOrder(Enum):
    NEAREST_NEIGHBOR = "nearest_neighbor"
    TWO_OPT = "two_opt"
    RANDOM = "random"

    def order_points(self, points: np.ndarray, start_at: int = 0) -> np.ndarray:
        """Return the order of points based on the traversal order."""
        if len(points) <= 2:  # no sense in optimizing
            return np.arange(len(points))
        start_at = min(start_at, len(points) - 1)
        if self == TraversalOrder.NEAREST_NEIGHBOR:
            return _nearest_neighbor_order(points, start_at)
        if self == TraversalOrder.TWO_OPT:
            return _two_opt_order(points, start_at)
        if self == TraversalOrder.RANDOM:
            return np.random.permutation(len(points))
        raise ValueError(f"Unknown traversal order: {self}")  # pragma: no cover

    def __call__(
        self, points: Iterable[tuple[float, float]], start_at: int = 0
    ) -> np.ndarray:
        """Sort the points based on the traversal order."""
        points = np.asarray(points)
        order = self.order_points(points, start_at=start_at)
        return points[order]  # type: ignore [no-any-return]


def _nearest_neighbor_order(points: np.ndarray, start_at: int = 0) -> np.ndarray:
    """Return the order of points based on the nearest neighbor algorithm.

    Parameters.
    ----------
    points : np.ndarray
        Array of 2D (Y, X) points in the format (n, 2).
    start_at : int, optional
        Index of the point to start at.  By default, the first point is used.

    Examples
    --------
    >>> points = np.array([[0, 0], [1, 0], [1, 1], [0, 1]])
    >>> order = _nearest_neighbor_order(points)
    >>> sorted = points[order]
    """
    n = len(points)
    visited = np.zeros(n, dtype=bool)
    order = np.zeros(n, dtype=int)
    order[0] = start_at
    visited[start_at] = True

    LARGE_NUMBER = 1e9
    # NOTE: at ~500+ points, scipy.spatial.cKDTree would begin to be faster
    # but it's a new dependency and may not be a common use case
    for i in range(1, n):
        # calculate the distance from the last visited point to all other points
        dist = np.linalg.norm(points - points[order[i - 1]], axis=1)
        # find the nearest point that has not been visited
        next_point = np.argmin(dist + visited * LARGE_NUMBER)
        # store it and mark it as visited
        order[i] = next_point
        visited[next_point] = True

    return order


def _two_opt_order(
    points: np.ndarray, start_at: int = 0, improvement_threshold: float = 0.05
) -> np.ndarray:
    """Return the order of points based on the 2-opt algorithm.

    https://en.wikipedia.org/wiki/2-opt

    Parameters
    ----------
    points : np.ndarray
        Array of 2D (Y, X) points in the format (n, 2).
    start_at : int, optional
        Index of the point to start at. By default, the first point is used.
    improvement_threshold : float, optional
        The minimum improvement factor required to continue the optimization.
        By default, 0.05.

    Examples
    --------
    >>> points = np.random.rand(100, 2)
    >>> order = _two_opt_order(points)
    >>> sorted = points[order]
    """
    n = points.shape[0]
    route = np.arange(n)

    if start_at != 0:
        route = np.roll(route, -start_at)

    dist_matrix = _distance_matrix(points)

    # this will track the best distance found so far
    best_distance = _total_distance(points[route])
    improvement_factor = 1.0
    while improvement_factor > improvement_threshold:
        distance_to_beat = best_distance
        for i in range(1, n - 2):
            for k in range(i + 1, n):
                # Calculate the distances involved in the potential swap
                ri = route[i]
                ri1 = route[i - 1]
                rk = route[k]
                y = route[(k + 1) % n]

                dist_before = dist_matrix[ri1, ri] + dist_matrix[rk, y]
                dist_after = dist_matrix[ri1, rk] + dist_matrix[ri, y]

                # If the new distance is better, perform the swap
                if dist_after < dist_before:
                    # Reverse the order of all elements from element i to element k.
                    route[i : k + 1] = route[i : k + 1][::-1]
                    best_distance = best_distance - dist_before + dist_after

        improvement_factor = 1 - best_distance / distance_to_beat

    return route


def _total_distance(points: np.ndarray) -> float:
    # Calculate the total Euclidean distance of the route traversing the given points
    # in the order provided
    diffs = points - np.roll(points, shift=1, axis=0)
    return np.sum(np.linalg.norm(diffs, axis=1))  # type: ignore [no-any-return]


def _distance_matrix(points: np.ndarray) -> np.ndarray:
    # Calculate the distance matrix (euclidean distance between each pair of points)
    return np.sqrt(np.sum((points[:, None] - points) ** 2, axis=2))  # type: ignore [no-any-return]
