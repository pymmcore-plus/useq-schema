from typing import List, Tuple, Union

import pytest

from useq import GridFromCorners, GridRelative

# assuming fov = (1, 1)
tiles = [
    (
        GridRelative(rows=2, cols=2, order_mode="row_wise"),
        [(-0.5, 0.5, 0, 0), (0.5, 0.5, 0, 1), (-0.5, -0.5, 1, 0), (0.5, -0.5, 1, 1)],
    ),
    (
        GridRelative(rows=2, cols=2),
        [(-0.5, 0.5, 0, 0), (0.5, 0.5, 0, 1), (0.5, -0.5, 1, 1), (-0.5, -0.5, 1, 0)],
    ),
    (
        GridRelative(rows=2, cols=2, order_mode="column_wise"),
        [(-0.5, 0.5, 0, 0), (-0.5, -0.5, 1, 0), (0.5, 0.5, 0, 1), (0.5, -0.5, 1, 1)],
    ),
    (
        GridRelative(rows=2, cols=2, order_mode="snake_column_wise"),
        [(-0.5, 0.5, 0, 0), (-0.5, -0.5, 1, 0), (0.5, -0.5, 1, 1), (0.5, 0.5, 0, 1)],
    ),
    (
        GridRelative(rows=2, cols=2, order_mode="spiral"),
        [(0.0, 0.0, 0, 0), (0.0, 1.0, 1, 0), (1.0, 1.0, 1, 1), (1.0, 0.0, 0, 1)],
    ),
    (
        GridRelative(rows=2, cols=2, relative_to="top_left", order_mode="row_wise"),
        [(0.0, 0.0, 0, 0), (1.0, 0.0, 0, 1), (0.0, -1.0, 1, 0), (1.0, -1.0, 1, 1)],
    ),
    (
        GridRelative(rows=2, cols=2, relative_to="top_left"),
        [(0.0, 0.0, 0, 0), (1.0, 0.0, 0, 1), (1.0, -1.0, 1, 1), (0.0, -1.0, 1, 0)],
    ),
    (
        GridRelative(rows=2, cols=2, relative_to="top_left", order_mode="column_wise"),
        [(0.0, 0.0, 0, 0), (0.0, -1.0, 1, 0), (1.0, 0.0, 0, 1), (1.0, -1.0, 1, 1)],
    ),
    (
        GridRelative(
            rows=2, cols=2, relative_to="top_left", order_mode="snake_column_wise"
        ),
        [(0.0, 0.0, 0, 0), (0.0, -1.0, 1, 0), (1.0, -1.0, 1, 1), (1.0, 0.0, 0, 1)],
    ),
    (
        GridRelative(rows=2, cols=2, relative_to="top_left", order_mode="spiral"),
        [(0.0, 0.0, 0, 0), (0.0, 1.0, 1, 0), (1.0, 1.0, 1, 1), (1.0, 0.0, 0, 1)],
    ),
    (
        GridFromCorners(corner1=(0, 0), corner2=(2, 2), order_mode="row_wise"),
        [
            (0.0, 0.0, 0, 0),
            (1.0, 0.0, 0, 1),
            (2.0, 0.0, 0, 2),
            (0.0, -1.0, 1, 0),
            (1.0, -1.0, 1, 1),
            (2.0, -1.0, 1, 2),
            (0.0, -2.0, 2, 0),
            (1.0, -2.0, 2, 1),
            (2.0, -2.0, 2, 2),
        ],
    ),
    (
        GridFromCorners(corner1=(0, 0), corner2=(2, 2)),
        [
            (0.0, 0.0, 0, 0),
            (1.0, 0.0, 0, 1),
            (2.0, 0.0, 0, 2),
            (2.0, -1.0, 1, 2),
            (1.0, -1.0, 1, 1),
            (0.0, -1.0, 1, 0),
            (0.0, -2.0, 2, 0),
            (1.0, -2.0, 2, 1),
            (2.0, -2.0, 2, 2),
        ],
    ),
    (
        GridFromCorners(corner1=(0, 0), corner2=(2, 2), order_mode="column_wise"),
        [
            (0.0, 0.0, 0, 0),
            (0.0, -1.0, 1, 0),
            (0.0, -2.0, 2, 0),
            (1.0, 0.0, 0, 1),
            (1.0, -1.0, 1, 1),
            (1.0, -2.0, 2, 1),
            (2.0, 0.0, 0, 2),
            (2.0, -1.0, 1, 2),
            (2.0, -2.0, 2, 2),
        ],
    ),
    (
        GridFromCorners(corner1=(0, 0), corner2=(2, 2), order_mode="snake_column_wise"),
        [
            (0.0, 0.0, 0, 0),
            (0.0, -1.0, 1, 0),
            (0.0, -2.0, 2, 0),
            (1.0, -2.0, 2, 1),
            (1.0, -1.0, 1, 1),
            (1.0, 0.0, 0, 1),
            (2.0, 0.0, 0, 2),
            (2.0, -1.0, 1, 2),
            (2.0, -2.0, 2, 2),
        ],
    ),
    (
        GridFromCorners(corner1=(0, 0), corner2=(2, 2), order_mode="spiral"),
        [
            (1.0, 1.0, 0, 0),
            (1.0, 2.0, 1, 0),
            (2.0, 2.0, 1, 1),
            (2.0, 1.0, 0, 1),
            (2.0, 0.0, -1, 1),
            (1.0, 0.0, -1, 0),
            (0.0, 0.0, -1, -1),
            (0.0, 1.0, 0, -1),
            (0.0, 2.0, 1, -1),
        ],
    ),
]


@pytest.mark.parametrize("tilemode, expectedpos", tiles)
def test_grids(
    tilemode: Union[GridRelative, GridFromCorners], expectedpos: List[Tuple]
):
    assert [
        (i.x, i.y, i.row, i.col) for i in list(tilemode.iter_grid_pos(1, 1))
    ] == expectedpos
