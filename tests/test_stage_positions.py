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

_RELATIVE_GRID_PLANS = [
    pytest.param({"rows": 2, "columns": 2}, id="GridRowsColumns"),
    pytest.param(
        useq.RandomPoints(num_points=3, max_width=100, max_height=100),
        id="RandomPoints",
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


@pytest.mark.parametrize("grid_plan", _RELATIVE_GRID_PLANS)
def test_position_no_warn_on_relative_sub_sequence_grid(grid_plan: Any) -> None:
    """Position keeps x/y when sub-sequence uses a relative grid."""
    pos = useq.Position(x=1, y=2, sequence={"grid_plan": grid_plan})
    assert pos.x == 1
    assert pos.y == 2


# --- __add__ / __radd__ -----------------------------------------------------------

_ADD_CASES = [
    pytest.param(
        useq.Position(x=1, y=2, z=3),
        useq.RelativePosition(x=5, y=10, z=1),
        (6, 12, 4),
        id="both_have_values",
    ),
    pytest.param(
        useq.Position(x=None, y=None, z=3),
        useq.RelativePosition(x=5, y=10, z=0),
        (5, 10, 3),
        id="none_falls_back_to_other",
    ),
]


@pytest.mark.parametrize("pos, rel, expected", _ADD_CASES)
def test_position_add(
    pos: useq.Position, rel: useq.RelativePosition, expected: tuple
) -> None:
    result = pos + rel
    assert (result.x, result.y, result.z) == expected


def test_position_radd() -> None:
    """__radd__ supports reversed addition (RelativePosition + AbsolutePosition)."""
    pos = useq.Position(x=1, y=2, z=3)
    rel = useq.RelativePosition(x=5, y=10, z=0)
    result = rel + pos
    assert (result.x, result.y, result.z) == (6, 12, 3)


# --- RelativePosition rejected in stage_positions --------------------------------


def test_relative_position_rejected_in_stage_positions() -> None:
    """RelativePosition is always rejected in stage_positions."""
    with pytest.raises(Exception, match="RelativePosition cannot be used"):
        useq.MDASequence(stage_positions=[useq.RelativePosition(x=1, y=2, z=3)])


# --- Global grid + position interactions -----------------------------------------


def test_warns_global_abs_grid_does_not_mutate_original_position() -> None:
    """Clearing x/y for a global absolute grid must not mutate the original Position."""
    pos = useq.Position(x=1, y=2, z=3)
    with pytest.warns(UserWarning, match="is ignored when using"):
        seq = useq.MDASequence(
            stage_positions=[pos],
            grid_plan={"top": 1, "bottom": -1, "left": 0, "right": 0},
        )
    assert pos.x == 1  # original must be untouched
    assert pos.y == 2
    assert seq.stage_positions[0].x is None  # sequence copy is updated
    assert seq.stage_positions[0].y is None


@pytest.mark.parametrize("grid_plan", _ABSOLUTE_GRID_PLANS)
def test_z_only_position_iterates_with_absolute_grid(grid_plan: dict) -> None:
    """Position(x=None, y=None, z=3) iterates correctly: grid provides x/y, pos z."""
    seq = useq.MDASequence(
        stage_positions=[useq.Position(x=None, y=None, z=3)],
        grid_plan=grid_plan,
    )
    events = list(seq)
    assert len(events) > 0
    for event in events:
        assert event.x_pos is not None
        assert event.y_pos is not None
        assert event.z_pos == 3.0
