from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, get_args

import pytest
from pydantic import TypeAdapter

import useq
import useq._position
from useq._point_visiting import OrderMode, _rect_indices, _spiral_indices

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from useq._position import PositionBase


g_inputs = [
    (
        useq.GridRowsColumns(overlap=10, rows=1, columns=2, relative_to="center"),
        [
            useq.RelativePosition(x=-0.45, y=0.0, name="0000", row=0, col=0),
            useq.RelativePosition(x=0.45, y=0.0, name="0001", row=0, col=1),
        ],
    ),
    (
        useq.GridRowsColumns(overlap=0, rows=1, columns=2, relative_to="top_left"),
        [
            useq.RelativePosition(x=0.0, y=0.0, name="0000", row=0, col=0),
            useq.RelativePosition(x=1.0, y=0.0, name="0001", row=0, col=1),
        ],
    ),
    (
        useq.GridRowsColumns(overlap=(20, 40), rows=2, columns=2),
        [
            useq.RelativePosition(x=-0.4, y=0.3, name="0000", row=0, col=0),
            useq.RelativePosition(x=0.4, y=0.3, name="0001", row=0, col=1),
            useq.RelativePosition(x=0.4, y=-0.3, name="0002", row=1, col=1),
            useq.RelativePosition(x=-0.4, y=-0.3, name="0003", row=1, col=0),
        ],
    ),
    (
        useq.GridFromEdges(
            overlap=0, top=0, left=0, bottom=20, right=20, fov_height=20, fov_width=20
        ),
        [
            useq.Position(x=10.0, y=10.0, name="0000", row=0, col=0),
        ],
    ),
    (
        useq.GridFromEdges(
            overlap=20,
            top=30,
            left=-10,
            bottom=-10,
            right=30,
            fov_height=25,
            fov_width=25,
        ),
        [
            useq.Position(x=2.5, y=17.5, name="0000", row=0, col=0),
            useq.Position(x=22.5, y=17.5, name="0001", row=0, col=1),
            useq.Position(x=22.5, y=-2.5, name="0002", row=1, col=1),
            useq.Position(x=2.5, y=-2.5, name="0003", row=1, col=0),
        ],
    ),
    (
        useq.RandomPoints(
            num_points=3,
            max_width=4,
            max_height=5,
            fov_height=0.5,
            fov_width=0.5,
            shape="ellipse",
            allow_overlap=False,
            random_seed=0,
        ),
        [
            useq.RelativePosition(x=-0.9, y=-1.1, name="0000"),
            useq.RelativePosition(x=0.9, y=-0.5, name="0001"),
            useq.RelativePosition(x=-0.8, y=-0.4, name="0002"),
        ],
    ),
    (
        useq.GridFromPolygon(
            vertices=[(0, 0), (4, 0), (2, 4)],
            fov_width=2,
            fov_height=2,
            overlap=0,
        ),
        [
            useq.Position(x=1.0, y=3.0, name="0000"),
            useq.Position(x=3.0, y=3.0, name="0001"),
            useq.Position(x=3.0, y=1.0, name="0002"),
            useq.Position(x=1.0, y=1.0, name="0003"),
        ],
    ),
]


@pytest.mark.parametrize("gridplan, gridexpectation", g_inputs)
def test_g_plan(gridplan: Any, gridexpectation: Sequence[Any]) -> None:
    g_plan = TypeAdapter(useq.MultiPointPlan).validate_python(gridplan)
    assert isinstance(g_plan, get_args(useq.MultiPointPlan))
    assert isinstance(g_plan, useq._position._MultiPointPlan)
    if isinstance(gridplan, useq.RandomPoints):
        assert g_plan and [round(gp, 1) for gp in g_plan] == gridexpectation
    else:
        assert g_plan and list(g_plan) == gridexpectation
    assert g_plan.num_positions() == len(gridexpectation)


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


def test_position_equality() -> None:
    """Order of grid positions should only change the order in which they are yielded"""

    def positions_without_name(
        positions: Iterable[PositionBase],
    ) -> set[tuple[float, float, bool]]:
        """Create a set of tuples of GridPosition attributes excluding 'name'"""
        return {(pos.x, pos.y, pos.is_relative) for pos in positions}

    t1 = useq.GridRowsColumns(rows=3, columns=3, mode=OrderMode.spiral)
    spiral_pos = positions_without_name(t1.iter_grid_positions(1, 1))

    t2 = useq.GridRowsColumns(rows=3, columns=3, mode=OrderMode.row_wise)
    row_pos = positions_without_name(t2.iter_grid_positions(1, 1))

    t3 = useq.GridRowsColumns(rows=3, columns=3, mode="row_wise_snake")
    snake_row_pos = positions_without_name(t3.iter_grid_positions(1, 1))

    t4 = useq.GridRowsColumns(rows=3, columns=3, mode=OrderMode.column_wise)
    col_pos = positions_without_name(t4.iter_grid_positions(1, 1))

    t5 = useq.GridRowsColumns(rows=3, columns=3, mode=OrderMode.column_wise_snake)
    snake_col_pos = positions_without_name(t5.iter_grid_positions(1, 1))

    assert spiral_pos == row_pos == snake_row_pos == col_pos == snake_col_pos


def test_grid_type() -> None:
    g1 = useq.GridRowsColumns(rows=2, columns=3)
    assert [(g.x, g.y) for g in g1.iter_grid_positions(1, 1)] == [
        (-1.0, 0.5),
        (0.0, 0.5),
        (1.0, 0.5),
        (1.0, -0.5),
        (0.0, -0.5),
        (-1.0, -0.5),
    ]
    assert g1.is_relative
    g2 = useq.GridWidthHeight(width=3, height=2, fov_height=1, fov_width=1)
    assert [(g.x, g.y) for g in g2.iter_grid_positions()] == [
        (-1.0, 0.5),
        (0.0, 0.5),
        (1.0, 0.5),
        (1.0, -0.5),
        (0.0, -0.5),
        (-1.0, -0.5),
    ]
    assert g2.is_relative
    g3 = useq.GridFromEdges(top=1, left=-1, bottom=-1, right=2)
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
        useq.GridFromEdges(top=1, left=-1, bottom=-1, right=2).num_positions()

    with pytest.raises(ValueError, match="plan requires the field of view size"):
        useq.GridWidthHeight(width=2, height=2).num_positions()


expected_rectangle = [(0.2, 1.1), (0.4, 0.2), (-0.3, 0.7)]
expected_ellipse = [(-0.9, -1.1), (0.9, -0.5), (-0.8, -0.4)]


@pytest.mark.parametrize("n_points", [3, 100])
@pytest.mark.parametrize("shape", ["rectangle", "ellipse"])
@pytest.mark.parametrize("seed", [None, 0])
def test_random_points(n_points: int, shape: str, seed: Optional[int]) -> None:
    rp = useq.RandomPoints(
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


@pytest.mark.parametrize("order", list(useq.TraversalOrder))
def test_traversal(order: useq.TraversalOrder):
    pp = useq.RandomPoints(
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
        useq.GridRowsColumns(rows=1, columns=2, **fov),
        useq.GridWidthHeight(width=10, height=10, **fov),
        useq.RandomPoints(num_points=10, **fov),
        useq.RelativePosition(**fov),
    ],
)
def test_points_plans_plot(
    obj: useq.RelativeMultiPointPlan, monkeypatch: pytest.MonkeyPatch
) -> None:
    mpl = pytest.importorskip("matplotlib.pyplot")
    monkeypatch.setattr(mpl, "show", lambda: None)

    assert isinstance(obj, get_args(useq.RelativeMultiPointPlan))
    assert all(isinstance(x, useq.RelativePosition) for x in obj)
    assert isinstance(obj.num_positions(), int)

    obj.plot()


def test_grid_from_edges_plot(monkeypatch: pytest.MonkeyPatch) -> None:
    mpl = pytest.importorskip("matplotlib.pyplot")
    monkeypatch.setattr(mpl, "show", lambda: None)
    useq.GridFromEdges(
        overlap=10, top=0, left=0, bottom=20, right=30, fov_height=10, fov_width=20
    ).plot()


def test_grid_from_polygon_plot(monkeypatch: pytest.MonkeyPatch) -> None:
    mpl = pytest.importorskip("matplotlib.pyplot")
    monkeypatch.setattr(mpl, "show", lambda: None)
    useq.GridFromPolygon(
        vertices=[(0, 0), (10, 0), (10, 10), (0, 10)],
        fov_width=3,
        fov_height=3,
        overlap=0,
    ).plot()


def test_grid_from_polygon_with_offset() -> None:
    """Test GridFromPolygon with offset feature."""
    vertices = [(0, 0), (4, 0), (2, 4)]

    grid_no_offset = useq.GridFromPolygon(
        vertices=vertices,
        fov_width=2,
        fov_height=2,
        overlap=0,
    )
    assert grid_no_offset.num_positions() == 4

    grid_with_offset = useq.GridFromPolygon(
        vertices=vertices,
        offset=1.0,
        fov_width=2,
        fov_height=2,
        overlap=0,
    )
    assert grid_with_offset.num_positions() == 13


def test_grid_from_polygon_with_convex_hull() -> None:
    """Test GridFromPolygon with convex_hull feature."""
    # create a concave polygon (L-shape)
    vertices = [(0, 0), (3, 0), (3, 1), (1, 1), (1, 3), (0, 3)]

    # grid without convex hull
    grid_no_hull = useq.GridFromPolygon(
        vertices=vertices,
        fov_width=1,
        fov_height=1,
        overlap=0,
    )
    assert grid_no_hull.num_positions() == 8

    # grid with convex hull (should fill in the concave part)
    grid_with_hull = useq.GridFromPolygon(
        vertices=vertices,
        convex_hull=True,
        fov_width=1,
        fov_height=1,
        overlap=0,
    )
    assert grid_with_hull.num_positions() == 9


def test_invalid_poly() -> None:
    """Test that self-intersecting polygons are invalid."""
    vertices = [(0, 0), (2, 2), (0, 2), (2, 0)]
    with pytest.raises(ValueError, match="Invalid or self-intersecting polygon"):
        useq.GridFromPolygon(vertices=vertices, fov_width=1, fov_height=1)
