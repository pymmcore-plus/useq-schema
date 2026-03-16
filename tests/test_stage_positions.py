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


# ---------- Position with xy_stage, z_stage, other_stages ----------


def test_position_with_stage_names() -> None:
    pos = useq.Position(x=10, y=20, z=30, xy_stage="XYStage", z_stage="PiezoZ")
    assert pos.xy_stage == "XYStage"
    assert pos.z_stage == "PiezoZ"
    assert pos.other_stages == {}


def test_position_with_other_stages() -> None:
    pos = useq.Position(
        x=10, y=20, z=30, other_stages={"FilterWheel": 3.0, "Turret": 1.0}
    )
    assert pos.other_stages == {"FilterWheel": 3.0, "Turret": 1.0}


# ---------- MDAEvent backward-compat construction ----------


def test_mda_event_legacy_construction() -> None:
    event = useq.MDAEvent(x_pos=100, y_pos=200, z_pos=50)
    assert event.x_pos == 100.0
    assert event.y_pos == 200.0
    assert event.z_pos == 50.0
    assert "x" in event.positions
    assert "y" in event.positions
    assert "z" in event.positions
    assert event.positions["x"].pos == 100.0


def test_mda_event_positions_dict_construction() -> None:
    event = useq.MDAEvent(
        positions={
            "x": {"pos": 100},
            "z": {"pos": 50, "stage": "PiezoZ"},
        }
    )
    assert event.x_pos == 100.0
    assert event.y_pos is None
    assert event.z_pos == 50.0
    assert event.positions["z"].stage == "PiezoZ"


def test_mda_event_positions_none_values() -> None:
    """x_pos=None should not create an entry in positions."""
    event = useq.MDAEvent(x_pos=None, y_pos=200)
    assert "x" not in event.positions
    assert event.x_pos is None
    assert event.y_pos == 200.0


def test_mda_event_serialization_legacy_format() -> None:
    """When only spatial axes with no stage names, serialize to legacy format."""
    event = useq.MDAEvent(x_pos=100, y_pos=200, z_pos=50)
    data = event.model_dump(exclude_unset=True)
    assert "x_pos" in data
    assert "y_pos" in data
    assert "z_pos" in data
    assert data["x_pos"] == 100.0
    assert data["y_pos"] == 200.0
    assert data["z_pos"] == 50.0
    assert "positions" not in data


def test_mda_event_serialization_with_stage_names() -> None:
    """When stage names are present, serialize to positions format."""
    event = useq.MDAEvent(
        positions={"x": {"pos": 100}, "z": {"pos": 50, "stage": "PiezoZ"}}
    )
    data = event.model_dump(exclude_unset=True)
    assert "positions" in data
    assert "x_pos" not in data


def test_mda_event_serialization_with_non_spatial_axes() -> None:
    """Non-spatial axes should use positions format."""
    event = useq.MDAEvent(
        positions={
            "x": {"pos": 100},
            "FilterWheel": {"pos": 3.0, "stage": "FilterWheel"},
        }
    )
    data = event.model_dump(exclude_unset=True)
    assert "positions" in data
    assert "x_pos" not in data


def test_mda_event_xy_stage_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="x and y positions must use the same"):
        useq.MDAEvent(
            positions={
                "x": {"pos": 100, "stage": "StageA"},
                "y": {"pos": 200, "stage": "StageB"},
            }
        )


def test_mda_event_model_validate_legacy() -> None:
    """model_validate with legacy format should work."""
    event = useq.MDAEvent.model_validate(
        {"x_pos": 100, "y_pos": 200, "z_pos": 50}
    )
    assert event.x_pos == 100.0
    assert event.y_pos == 200.0
    assert event.z_pos == 50.0


def test_mda_event_round_trip() -> None:
    """Serialization and deserialization round-trip."""
    event = useq.MDAEvent(x_pos=100, y_pos=200, z_pos=50)
    data = event.model_dump()
    event2 = useq.MDAEvent.model_validate(data)
    assert event2.x_pos == event.x_pos
    assert event2.y_pos == event.y_pos
    assert event2.z_pos == event.z_pos


def test_mda_event_round_trip_with_stages() -> None:
    """Round-trip with stage names."""
    event = useq.MDAEvent(
        positions={
            "x": {"pos": 100, "stage": "XYStage"},
            "y": {"pos": 200, "stage": "XYStage"},
            "z": {"pos": 50, "stage": "PiezoZ"},
        }
    )
    data = event.model_dump()
    event2 = useq.MDAEvent.model_validate(data)
    assert event2.positions["x"].pos == 100.0
    assert event2.positions["x"].stage == "XYStage"
    assert event2.positions["z"].stage == "PiezoZ"


# ---------- MDASequence propagation ----------


def test_mda_sequence_propagates_stage_names() -> None:
    """Stage positions with xy_stage/z_stage/other_stages propagate to events."""
    seq = useq.MDASequence(
        stage_positions=[
            useq.Position(
                x=10, y=20, z=30,
                xy_stage="XYStage",
                z_stage="PiezoZ",
                other_stages={"FilterWheel": 3.0},
            )
        ],
    )
    events = list(seq)
    assert len(events) == 1
    event = events[0]
    assert event.x_pos == 10.0
    assert event.y_pos == 20.0
    assert event.z_pos == 30.0
    assert event.positions["x"].stage == "XYStage"
    assert event.positions["y"].stage == "XYStage"
    assert event.positions["z"].stage == "PiezoZ"
    assert event.positions["FilterWheel"].pos == 3.0
    assert event.positions["FilterWheel"].stage == "FilterWheel"
