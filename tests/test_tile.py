import pytest

from useq import TileRelative
from useq._tile import OrderMode, _rect_indices, _spiral_indices

EXPECT = {
    (True, False): [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)],
    (True, True): [(0, 0), (0, 1), (1, 1), (1, 0), (2, 0), (2, 1)],
    (False, False): [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)],
    (False, True): [(0, 0), (1, 0), (2, 0), (2, 1), (1, 1), (0, 1)],
}


@pytest.mark.parametrize("row_wise", [True, False], ids=["row_wise", "col_wise"])
@pytest.mark.parametrize("snake", [True, False], ids=["snake", "normal"])
def test_tile_indices(row_wise: bool, snake: bool) -> None:
    indices = _rect_indices(3, 2, snake=snake, row_wise=row_wise)
    assert list(indices) == EXPECT[(row_wise, snake)]


def test_spiral_indices() -> None:
    assert list(_spiral_indices(2, 3)) == [
        (0, 1),
        (0, 2),
        (1, 2),
        (1, 1),
        (1, 0),
        (0, 0),
    ]
    assert list(_spiral_indices(2, 3, center_origin=True)) == [
        (0, 0),
        (0, 1),
        (1, 1),
        (1, 0),
        (1, -1),
        (0, -1),
    ]


def test_position_equality():
    """Order of tiles should only change the order in which they are yielded"""
    t1 = TileRelative(rows=3, columns=3, mode=OrderMode.spiral)
    spiral_pos = set(t1.iter_tiles(1, 1))

    t2 = TileRelative(rows=3, columns=3, mode=OrderMode.row_wise)
    row_pos = set(t2.iter_tiles(1, 1))

    t3 = TileRelative(rows=3, columns=3, mode="row_wise_snake")
    snake_row_pos = set(t3.iter_tiles(1, 1))

    t4 = TileRelative(rows=3, columns=3, mode=OrderMode.column_wise)
    col_pos = set(t4.iter_tiles(1, 1))

    t5 = TileRelative(rows=3, columns=3, mode=OrderMode.column_wise_snake)
    snake_col_pos = set(t5.iter_tiles(1, 1))

    assert spiral_pos == row_pos == snake_row_pos == col_pos == snake_col_pos
