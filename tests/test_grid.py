from typing import Optional

import pytest

from useq import GridFromEdges, GridRowsColumns, GridWidthHeight, RandomPoints
from useq._grid import OrderMode, _rect_indices, _spiral_indices

EXPECT = {
    (True, False): [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0), (2, 1)],
    (True, True): [(0, 0), (0, 1), (1, 1), (1, 0), (2, 0), (2, 1)],
    (False, False): [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1)],
    (False, True): [(0, 0), (1, 0), (2, 0), (2, 1), (1, 1), (0, 1)],
}


@pytest.mark.parametrize("row_wise", [True, False], ids=["row_wise", "col_wise"])
@pytest.mark.parametrize("snake", [True, False], ids=["snake", "normal"])
def test_grid_indices(row_wise: bool, snake: bool) -> None:
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
    """Order of grid positions should only change the order in which they are yielded"""
    t1 = GridRowsColumns(rows=3, columns=3, mode=OrderMode.spiral)
    spiral_pos = set(t1.iter_grid_positions(1, 1))

    t2 = GridRowsColumns(rows=3, columns=3, mode=OrderMode.row_wise)
    row_pos = set(t2.iter_grid_positions(1, 1))

    t3 = GridRowsColumns(rows=3, columns=3, mode="row_wise_snake")
    snake_row_pos = set(t3.iter_grid_positions(1, 1))

    t4 = GridRowsColumns(rows=3, columns=3, mode=OrderMode.column_wise)
    col_pos = set(t4.iter_grid_positions(1, 1))

    t5 = GridRowsColumns(rows=3, columns=3, mode=OrderMode.column_wise_snake)
    snake_col_pos = set(t5.iter_grid_positions(1, 1))

    assert spiral_pos == row_pos == snake_row_pos == col_pos == snake_col_pos


def test_grid_type():
    g1 = GridRowsColumns(rows=2, columns=3)
    assert [(g.x, g.y) for g in g1.iter_grid_positions(1, 1)] == [
        (-1.0, 0.5),
        (0.0, 0.5),
        (1.0, 0.5),
        (1.0, -0.5),
        (0.0, -0.5),
        (-1.0, -0.5),
    ]
    assert g1.is_relative
    g2 = GridWidthHeight(width=3, height=2, fov_height=1, fov_width=1)
    assert [(g.x, g.y) for g in g2.iter_grid_positions()] == [
        (-1.0, 0.5),
        (0.0, 0.5),
        (1.0, 0.5),
        (1.0, -0.5),
        (0.0, -0.5),
        (-1.0, -0.5),
    ]
    assert g2.is_relative
    g3 = GridFromEdges(top=1, left=-1, bottom=-1, right=2)
    assert [(g.x, g.y) for g in g3.iter_grid_positions(1, 1)] == [
        (-1.0, 1.0),
        (0.0, 1.0),
        (1.0, 1.0),
        (2.0, 1.0),
        (2.0, 0.0),
        (1.0, 0.0),
        (0.0, 0.0),
        (-1.0, 0.0),
        (-1.0, -1.0),
        (0.0, -1.0),
        (1.0, -1.0),
        (2.0, -1.0),
    ]
    assert not g3.is_relative


def test_num_position_error() -> None:
    with pytest.raises(ValueError, match="the field of view size be set"):
        GridFromEdges(top=1, left=-1, bottom=-1, right=2).num_positions()


expected_rectangle = [
    (0.195254015709299, 1.0759468318620975),
    (0.4110535042865755, 0.2244159149844842),
    (-0.30538080264438117, 0.7294705653332807),
]
expected_ellipse = [
    (-1.1833701700089627, -1.272217607180939),
    (1.2886747534938614, -0.5343419915023853),
    (-1.2180986624660364, -0.4016429267523442),
]


@pytest.mark.parametrize("n_points", [3, 100])
@pytest.mark.parametrize("shape", ["rectangle", "ellipse"])
@pytest.mark.parametrize("seed", [None, 0])
def test_random_points(n_points: int, shape: str, seed: Optional[int]) -> None:
    rp = RandomPoints(
        num_points=n_points,
        max_width=4,
        max_height=5,
        shape=shape,
        random_seed=seed,
        allow_overlap=False,
        fov_width=0.5,
        fov_height=0.5,
    )

    if n_points == 3:
        expected = expected_rectangle if shape == "rectangle" else expected_ellipse
        if seed is None:
            assert [(g.x, g.y) for g in rp] != expected
        else:
            assert [(g.x, g.y) for g in rp] == expected
    else:
        with pytest.raises(UserWarning, match="Max number of iterations reached"):
            list(rp)
