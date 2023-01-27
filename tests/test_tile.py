from typing import List, Tuple, Union

import pytest

from useq import TileFromCorners, TileRelative

# assuming fov = (1, 1)
tiles = [
    (
        TileRelative(rows=2, cols=2, order_mode="row_wise"),
        [(-0.5, 0.5, 0, 0), (0.5, 0.5, 0, 1), (-0.5, -0.5, 1, 0), (0.5, -0.5, 1, 1)],
    ),
    (
        TileRelative(rows=2, cols=2, order_mode="snake_row_wise"),
        [(-0.5, 0.5, 0, 0), (0.5, 0.5, 0, 1), (0.5, -0.5, 1, 1), (-0.5, -0.5, 1, 0)],
    ),
    (
        TileRelative(rows=2, cols=2, order_mode="column_wise"),
        [(-0.5, 0.5, 0, 0), (-0.5, -0.5, 1, 0), (0.5, 0.5, 0, 1), (0.5, -0.5, 1, 1)],
    ),
    (
        TileRelative(rows=2, cols=2, order_mode="snake_column_wise"),
        [(-0.5, 0.5, 0, 0), (-0.5, -0.5, 1, 0), (0.5, -0.5, 1, 1), (0.5, 0.5, 0, 1)],
    ),
    (
        TileRelative(rows=2, cols=2, order_mode="spiral"),
        [(0.0, 0.0, 0, 0), (0.0, 1.0, 1, 0), (1.0, 1.0, 1, 1), (1.0, 0.0, 0, 1)],
    ),
    (
        TileRelative(rows=2, cols=2, relative_to="top_left", order_mode="row_wise"),
        [(0.0, 0.0, 0, 0), (1.0, 0.0, 0, 1), (0.0, -1.0, 1, 0), (1.0, -1.0, 1, 1)],
    ),
    (
        TileRelative(
            rows=2, cols=2, relative_to="top_left", order_mode="snake_row_wise"
        ),
        [(0.0, 0.0, 0, 0), (1.0, 0.0, 0, 1), (1.0, -1.0, 1, 1), (0.0, -1.0, 1, 0)],
    ),
    (
        TileRelative(rows=2, cols=2, relative_to="top_left", order_mode="column_wise"),
        [(0.0, 0.0, 0, 0), (0.0, -1.0, 1, 0), (1.0, 0.0, 0, 1), (1.0, -1.0, 1, 1)],
    ),
    (
        TileRelative(
            rows=2, cols=2, relative_to="top_left", order_mode="snake_column_wise"
        ),
        [(0.0, 0.0, 0, 0), (0.0, -1.0, 1, 0), (1.0, -1.0, 1, 1), (1.0, 0.0, 0, 1)],
    ),
    (
        TileRelative(rows=2, cols=2, relative_to="top_left", order_mode="spiral"),
        [(0.0, 0.0, 0, 0), (0.0, 1.0, 1, 0), (1.0, 1.0, 1, 1), (1.0, 0.0, 0, 1)],
    ),
    (
        TileFromCorners(corner1=(0, 0), corner2=(2, 2), order_mode="row_wise"),
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
        TileFromCorners(corner1=(0, 0), corner2=(2, 2), order_mode="snake_row_wise"),
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
        TileFromCorners(corner1=(0, 0), corner2=(2, 2), order_mode="column_wise"),
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
        TileFromCorners(corner1=(0, 0), corner2=(2, 2), order_mode="snake_column_wise"),
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
        TileFromCorners(corner1=(0, 0), corner2=(2, 2), order_mode="spiral"),
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
def test_tiles(
    tilemode: Union[TileRelative, TileFromCorners], expectedpos: List[Tuple]
):
    assert [
        (i.x, i.y, i.row, i.col) for i in list(tilemode.iter_tiles(1, 1))
    ] == expectedpos
