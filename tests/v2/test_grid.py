from __future__ import annotations

import importlib
import importlib.util
import math
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

import numpy as np
import pytest

from useq._enums import RelativeTo, Shape
from useq.v2 import (
    GridFromEdges,
    GridRowsColumns,
    GridWidthHeight,
    MultiPointPlan,
    OrderMode,
    RandomPoints,
    TraversalOrder,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from useq.v2 import Position


def _in_ellipse(x: float, y: float, w: float, h: float, tol: float = 1.01) -> bool:
    return (x / (w / 2)) ** 2 + (y / (h / 2)) ** 2 <= tol


SLOTS = {"slots": True}


@dataclass(**SLOTS)
class GridTestCase:
    grid: MultiPointPlan
    expected_coords: list[tuple[float, float]]


GRID_CASES: list[GridTestCase] = [
    # -------------------------------------------------------------------
    GridTestCase(
        GridFromEdges(
            top=10,
            left=0,
            bottom=0,
            right=10,
            fov_width=5,
            fov_height=5,
        ),
        [(2.5, 7.5), (7.5, 7.5), (7.5, 2.5), (2.5, 2.5)],
    ),
    GridTestCase(
        GridFromEdges(
            top=5,
            left=0,
            bottom=0,
            right=5,
            fov_width=5,
            fov_height=5,
        ),
        [(2.5, 2.5)],
    ),
    # -------------------------------------------------------------------
    GridTestCase(
        GridRowsColumns(
            rows=2,
            columns=3,
            relative_to=RelativeTo.center,
            fov_width=1,
            fov_height=1,
        ),
        [(-1.0, 0.5), (0.0, 0.5), (1.0, 0.5), (1.0, -0.5), (0.0, -0.5), (-1.0, -0.5)],
    ),
    GridTestCase(
        GridRowsColumns(
            rows=2,
            columns=2,
            relative_to=RelativeTo.top_left,
            fov_width=1,
            fov_height=1,
        ),
        [(0.0, 0.0), (1.0, 0.0), (1.0, -1.0), (0.0, -1.0)],
    ),
    # -------------------------------------------------------------------
    GridTestCase(
        GridWidthHeight(
            width=3,
            height=2,
            relative_to=RelativeTo.center,
            fov_width=1,
            fov_height=1,
        ),
        [(-1.0, 0.5), (0.0, 0.5), (1.0, 0.5), (1.0, -0.5), (0.0, -0.5), (-1.0, -0.5)],
    ),
    GridTestCase(
        GridWidthHeight(
            width=2,
            height=2,
            relative_to=RelativeTo.top_left,
            fov_width=1,
            fov_height=1,
        ),
        [(0.0, 0.0), (1.0, 0.0), (1.0, -1.0), (0.0, -1.0)],
    ),
    # fractional coverage (2.5 x 1.5) ⇒ same coords as 3 x 2 case
    GridTestCase(
        GridWidthHeight(
            width=2.5,
            height=1.5,
            relative_to=RelativeTo.center,
            fov_width=1,
            fov_height=1,
        ),
        [(-1.0, 0.5), (0.0, 0.5), (1.0, 0.5), (1.0, -0.5), (0.0, -0.5), (-1.0, -0.5)],
    ),
    # -------------------------------------------------------------------
    GridTestCase(
        RandomPoints(
            shape=Shape.ELLIPSE,
            num_points=5,
            max_width=10,
            max_height=6,
            random_seed=42,
        ),
        [
            (-0.2114, -2.8339),
            (-0.2337, -1.5420),
            (1.6669, 0.3887),
            (1.7288, 0.5794),
            (3.4772, -0.0116),
        ],
    ),
    GridTestCase(
        RandomPoints(
            shape=Shape.RECTANGLE,
            num_points=4,
            max_width=8,
            max_height=4,
            random_seed=123,
        ),
        [(1.5717, -0.8554), (-2.1851, 0.2052), (1.7557, -0.3075), (3.8461, 0.7393)],
    ),
]


def _coords(grid: Iterable[Position]) -> list[tuple[float, float]]:
    return [(p.x, p.y) for p in grid]  # type: ignore


@pytest.mark.parametrize("tc", GRID_CASES, ids=lambda tc: type(tc.grid).__name__)
def test_grid_cases(tc: GridTestCase) -> None:
    pos = list(tc.grid)
    coords = _coords(pos)
    np.testing.assert_allclose(coords, tc.expected_coords, atol=1e-4)
    assert len(pos) == len(tc.expected_coords)

    if isinstance(tc.grid, RandomPoints):
        w, h = tc.grid.max_width, tc.grid.max_height
        if tc.grid.shape is Shape.ELLIPSE:
            for x, y in coords:
                assert _in_ellipse(x, y, w, h)
        else:
            for x, y in coords:
                assert -w / 2 <= x <= w / 2
                assert -h / 2 <= y <= h / 2


def test_grid_from_edges_with_overlap() -> None:
    g = GridFromEdges(
        top=10,
        left=0,
        bottom=0,
        right=10,
        fov_width=5,
        fov_height=5,
        overlap=50,
    )
    coords = cast("list[tuple[float, float]]", [(p.x, p.y) for p in g])

    # 50 % overlap ⇒ step = 2.5 µm
    assert len(g) > 4
    assert coords[0] == (2.5, 7.5)
    assert math.isclose(coords[1][0] - coords[0][0], 2.5, abs_tol=1e-6)


def test_grid_rows_columns_overlap_spacing() -> None:
    g = GridRowsColumns(
        rows=2,
        columns=2,
        relative_to=RelativeTo.center,
        fov_width=2,
        fov_height=2,
        overlap=(25, 50),
    )
    coords = _coords(g)

    dx, dy = 2 * (1 - 0.25), 2 * (1 - 0.5)
    assert math.isclose(abs(coords[1][0] - coords[0][0]), dx, abs_tol=0.01)
    assert math.isclose(abs(coords[2][1] - coords[0][1]), dy, abs_tol=0.01)


def test_random_points_no_overlap() -> None:
    g = RandomPoints(
        num_points=3,
        max_width=10,
        max_height=10,
        shape=Shape.RECTANGLE,
        fov_width=2,
        fov_height=2,
        allow_overlap=False,
        random_seed=456,
    )
    coords = _coords(g)
    for i, (x1, y1) in enumerate(coords):
        for j, (x2, y2) in enumerate(coords):
            if i != j:
                assert abs(x1 - x2) >= 2 or abs(y1 - y2) >= 2

    if importlib.util.find_spec("matplotlib") is not None and os.name != "nt":
        g.plot(show=False)


def test_random_points_traversal_ordering() -> None:
    g1 = RandomPoints(num_points=5, random_seed=789, order=None)
    g2 = RandomPoints(num_points=5, random_seed=789, order=TraversalOrder.TWO_OPT)

    coords1 = [(p.x, p.y) for p in g1]
    coords2 = [(p.x, p.y) for p in g2]

    assert set(coords1) == set(coords2) and coords1 != coords2


# ---------------------------------------------------------------------------
# traversal modes & naming
# ---------------------------------------------------------------------------


def test_row_vs_column_snake() -> None:
    row = GridRowsColumns(
        rows=2, columns=3, mode=OrderMode.row_wise_snake, fov_width=1, fov_height=1
    )
    col = GridRowsColumns(
        rows=2, columns=3, mode=OrderMode.column_wise_snake, fov_width=1, fov_height=1
    )

    row_coords = [(p.x, p.y) for p in row]
    col_coords = [(p.x, p.y) for p in col]

    assert row_coords[0] == col_coords[0]  # both start top-left
    assert row_coords[1] != col_coords[1]  # diverge after that


def test_position_naming() -> None:
    names = [
        p.name for p in GridRowsColumns(rows=2, columns=2, fov_width=1, fov_height=1)
    ]
    assert names == ["0000", "0001", "0002", "0003"]
