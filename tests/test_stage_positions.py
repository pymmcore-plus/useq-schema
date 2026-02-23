from collections.abc import Sequence
from typing import Any

import numpy as np
import pytest

import useq

p_inputs = [
    ({"x": 0, "y": 1, "z": 2}, (0, 1, 2)),
    ({"y": 200}, (None, 200, None)),
    ((100, 200, 300), (100, 200, 300)),
    (
        {
            "z": 100,
            "sequence": {"z_plan": {"above": 8, "below": 4, "step": 2}},
        },
        (None, None, 100),
    ),
    (np.ones(3), (1, 1, 1)),
    ((None, 200, None), (None, 200, None)),
    (np.ones(2), (1, 1, None)),
    (np.array([0, 0, 0]), (0, 0, 0)),
    (np.array([0, 0]), (0, 0, None)),
    (useq.Position(x=100, y=200, z=300), (100, 200, 300)),
]


@pytest.mark.parametrize("position, pexpectation", p_inputs)
def test_stage_positions(position: Any, pexpectation: Sequence[float]) -> None:
    position = useq.Position.model_validate(position)
    assert (position.x, position.y, position.z) == pexpectation


_ABSOLUTE_GRID_PLANS = [
    pytest.param(
        {"top": 1, "bottom": -1, "left": 0, "right": 0},
        id="GridFromEdges",
    ),
    pytest.param(
        {"vertices": [(0, 0), (4, 0), (2, 4)], "fov_width": 2, "fov_height": 2},
        id="GridFromPolygon",
    ),
]


@pytest.mark.parametrize("grid_plan", _ABSOLUTE_GRID_PLANS)
def test_position_warns_on_absolute_sub_sequence_grid(
    grid_plan: dict,
) -> None:
    """Position clears x/y and warns at construction when sub-sequence uses an absolute grid."""
    with pytest.warns(UserWarning, match="is ignored when a position sequence uses"):
        pos = useq.Position(x=1, y=2, sequence={"grid_plan": grid_plan})
    assert pos.x is None
    assert pos.y is None


def test_position_no_warn_on_relative_sub_sequence_grid() -> None:
    """Position keeps x/y when sub-sequence uses a relative grid."""
    pos = useq.Position(x=1, y=2, sequence={"grid_plan": {"rows": 2, "columns": 2}})
    assert pos.x == 1
    assert pos.y == 2
