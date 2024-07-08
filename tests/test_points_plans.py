from __future__ import annotations

from typing import TYPE_CHECKING, Iterable, Optional, get_args

import pytest

from useq import (
    GridFromEdges,
    GridRowsColumns,
    GridWidthHeight,
    RandomPoints,
    RelativeMultiPointPlan,
    RelativePosition,
    TraversalOrder,
)
from useq._point_visiting import OrderMode, _rect_indices, _spiral_indices

if TYPE_CHECKING:
    from useq._position import PositionBase

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

    def positions_without_name(
        positions: Iterable[PositionBase],
    ) -> set[tuple[float, float, bool]]:
        """Create a set of tuples of GridPosition attributes excluding 'name'"""
        return {(pos.x, pos.y, pos.is_relative) for pos in positions}

    t1 = GridRowsColumns(rows=3, columns=3, mode=OrderMode.spiral)
    spiral_pos = positions_without_name(t1.iter_grid_positions(1, 1))

    t2 = GridRowsColumns(rows=3, columns=3, mode=OrderMode.row_wise)
    row_pos = positions_without_name(t2.iter_grid_positions(1, 1))

    t3 = GridRowsColumns(rows=3, columns=3, mode="row_wise_snake")
    snake_row_pos = positions_without_name(t3.iter_grid_positions(1, 1))

    t4 = GridRowsColumns(rows=3, columns=3, mode=OrderMode.column_wise)
    col_pos = positions_without_name(t4.iter_grid_positions(1, 1))

    t5 = GridRowsColumns(rows=3, columns=3, mode=OrderMode.column_wise_snake)
    snake_col_pos = positions_without_name(t5.iter_grid_positions(1, 1))

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
    with pytest.raises(ValueError, match="plan requires the field of view size"):
        GridFromEdges(top=1, left=-1, bottom=-1, right=2).num_positions()

    with pytest.raises(ValueError, match="plan requires the field of view size"):
        GridWidthHeight(width=2, height=2).num_positions()


expected_rectangle = [(0.2, 1.1), (0.4, 0.2), (-0.3, 0.7)]
expected_ellipse = [(-0.9, -1.1), (0.9, -0.5), (-0.8, -0.4)]


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
        values = [(round(g.x, 1), round(g.y, 1)) for g in rp]
        if seed is None:
            assert values != expected
        else:
            assert values == expected
    else:
        with pytest.raises(UserWarning, match="Unable to generate"):
            list(rp)


@pytest.mark.parametrize("order", list(TraversalOrder))
def test_traversal(order: TraversalOrder):
    pp = RandomPoints(
        num_points=30,
        max_height=3000,
        max_width=3000,
        order=order,
        random_seed=1,
        start_at=10,
        fov_height=300,
        fov_width=300,
        allow_overlap=False,
    )
    list(pp)


fov = {"fov_height": 200, "fov_width": 200}


@pytest.mark.parametrize(
    "obj",
    [
        GridRowsColumns(rows=1, columns=2, **fov),
        GridWidthHeight(width=10, height=10, **fov),
        RandomPoints(num_points=10, **fov),
        RelativePosition(**fov),
    ],
)
def test_points_plans(obj: RelativeMultiPointPlan, monkeypatch: pytest.MonkeyPatch):
    mpl = pytest.importorskip("matplotlib.pyplot")
    monkeypatch.setattr(mpl, "show", lambda: None)

    assert isinstance(obj, get_args(RelativeMultiPointPlan))
    assert all(isinstance(x, RelativePosition) for x in obj)
    assert isinstance(obj.num_positions(), int)

    obj.plot()
