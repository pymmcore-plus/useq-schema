from enum import Enum
from functools import partial
from typing import Callable, Iterator, Tuple

import numpy as np

# ----------------------------- Random Points -----------------------------------


class GridOrder(Enum):
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
_INDEX_GENERATORS: dict[GridOrder, IndexGenerator] = {
    GridOrder.row_wise: partial(_rect_indices, snake=False, row_wise=True),
    GridOrder.column_wise: partial(_rect_indices, snake=False, row_wise=False),
    GridOrder.row_wise_snake: partial(_rect_indices, snake=True, row_wise=True),
    GridOrder.column_wise_snake: partial(_rect_indices, snake=True, row_wise=False),
    GridOrder.spiral: _spiral_indices,
}

# ----------------------------- Random Points -----------------------------------


class TraversalOrder(Enum):
    NEAREST_NEIGHBOR = "Nearest Neighbor"
    SHORTEST_TOUR = "Shortest Tour (TSP)"
    RANDOM_WALK = "Random Walk"
    SPIRAL = "Spiral Traversal"

    def sort_points(self, points: np.ndarray) -> np.ndarray:
        """Sort the points based on the traversal order."""
        if self == TraversalOrder.NEAREST_NEIGHBOR:
            return _nearest_neighbor_order(points)
        if self == TraversalOrder.SHORTEST_TOUR:
            return _shortest_tour_order(points)
        if self == TraversalOrder.RANDOM_WALK:
            return _random_walk_sort(points)
        if self == TraversalOrder.SPIRAL:
            return _spiral_sort(points)
        raise ValueError(f"Unknown traversal order: {self}")


LARGE_NUMBER = 1e9


def _nearest_neighbor_order(points: np.ndarray, start_at: int = 0) -> np.ndarray:
    """Return the order of points based on the nearest neighbor algorithm.

    Parameters.
    ----------
    points : np.ndarray
        Array of 2D (Y, X) points in the format (n, 2).
    start_at : int, optional
        Index of the point to start at. If None, the first point is used.

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

    # NOTE: > ~500 of points, scipy.spatial.cKDTree would begin to be faster
    # but it's a new dependency and may not be a common use case
    for i in range(1, n):
        # get the last point
        last = points[order[i - 1]]
        # calculate the distance to all other points
        dist = np.linalg.norm(points - last, axis=1)
        # find the nearest point that has not been visited
        next_point = np.argmin(dist + visited * LARGE_NUMBER)
        # store the index of the next point
        order[i] = next_point
        # mark the point as visited
        visited[next_point] = True

    return order  # type: ignore [no-any-return]


def _shortest_tour_order(points: np.ndarray, start_at: int = 0) -> np.ndarray:
    """Return the order of points based on the shortest tour (TSP).

    Parameters.
    ----------
    points : np.ndarray
        Array of 2D (Y, X) points in the format (n, 2).
    start_at : int, optional
        Index of the point to start at. If None, the first point is used.
    """
    raise NotImplementedError("Shortest tour is not implemented yet.")





def _path_distance(r: np.ndarray, c: np.ndarray) -> float:
    # Calculate the euclidian distance in n-space of the route r traversing cities c,
    # ending at the path start.
    return np.sum([np.linalg.norm(c[r[p]] - c[r[p - 1]]) for p in range(len(r))])


def _two_opt_swap(r: np.ndarray, i: int, k: int) -> np.ndarray:
    # Reverse the order of all elements from element i to element k in array r.
    return np.concatenate((r[0:i], r[k : -len(r) + i - 1 : -1], r[k + 1 : len(r)]))


def two_opt(points: np.ndarray, improvement_threshold: float = 0.01) -> np.ndarray:
    # 2-opt Algorithm adapted from https://en.wikipedia.org/wiki/2-opt
    # https://stackoverflow.com/questions/25585401/travelling-salesman-in-scipy
    # Make an array of row numbers corresponding to cities.
    route = np.arange(points.shape[0])
    # Initialize the improvement factor.
    improvement_factor = 1.0
    # Calculate the distance of the initial path.
    best_distance = _path_distance(route, points)
    # If the route is still improving, keep going!
    while improvement_factor > improvement_threshold:
        # Record the distance at the beginning of the loop.
        distance_to_beat = best_distance
        # From each city except the first and last,
        for swap_first in range(1, len(route) - 2):
            # to each of the points following,
            for swap_last in range(swap_first + 1, len(route)):
                # try reversing the order of these points
                new_route = _two_opt_swap(route, swap_first, swap_last)
                # and check the total distance with this modification.
                new_distance = _path_distance(new_route, points)
                # If the path distance is an improvement,
                if new_distance < best_distance:
                    # make this the accepted best route
                    route = new_route
                    # and update the distance corresponding to this route.
                    best_distance = new_distance
        # Calculate how much the route has improved.
        improvement_factor = 1 - best_distance / distance_to_beat
    return route  # When the route is no longer improving substan
