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


def test_position_warns_on_absolute_sub_sequence_grid() -> None:
    """Position clears x/y and warns at construction when sub-sequence uses an absolute grid."""
    # GridFromEdges
    with pytest.warns(UserWarning, match="is ignored when a position sequence uses"):
        pos = useq.Position(
            x=1,
            y=2,
            sequence={"grid_plan": {"top": 1, "bottom": -1, "left": 0, "right": 0}},
        )
    assert pos.x is None
    assert pos.y is None

    # GridFromPolygon
    with pytest.warns(UserWarning, match="is ignored when a position sequence uses"):
        pos2 = useq.Position(
            x=1,
            y=2,
            sequence={
                "grid_plan": {
                    "vertices": [(0, 0), (4, 0), (2, 4)],
                    "fov_width": 2,
                    "fov_height": 2,
                }
            },
        )
    assert pos2.x is None
    assert pos2.y is None

    # relative sub-sequence grid — no warning
    pos3 = useq.Position(x=1, y=2, sequence={"grid_plan": {"rows": 2, "columns": 2}})
    assert pos3.x == 1
    assert pos3.y == 2
