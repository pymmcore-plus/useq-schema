"""Tests for plate_row/plate_col, name_pattern, and composite pos_name."""

from __future__ import annotations

import json

import pytest
import yaml

import useq


# --- plate_row / plate_col name generation -----------------------------------

_NAME_FROM_PLATE_CASES = [
    pytest.param({"plate_row": 0, "plate_col": 0}, "A1", id="int_0_0"),
    pytest.param({"plate_row": 0, "plate_col": 1}, "A2", id="int_0_1"),
    pytest.param({"plate_row": 1, "plate_col": 0}, "B1", id="int_1_0"),
    pytest.param({"plate_row": 25, "plate_col": 0}, "Z1", id="int_25_0"),
    pytest.param({"plate_row": 26, "plate_col": 0}, "AA1", id="int_26_0"),
    pytest.param({"plate_row": "A", "plate_col": "1"}, "A1", id="str_A_1"),
    pytest.param({"plate_row": "B", "plate_col": 2}, "B3", id="mixed_B_2"),
]


@pytest.mark.parametrize("kwargs, expected_name", _NAME_FROM_PLATE_CASES)
def test_name_from_plate(kwargs: dict, expected_name: str) -> None:
    pos = useq.Position(**kwargs)
    assert pos.name == expected_name


def test_matching_explicit_name_accepted() -> None:
    pos = useq.Position(name="A1", plate_row=0, plate_col=0)
    assert pos.name == "A1"


def test_mismatched_name_raises() -> None:
    with pytest.raises(ValueError, match="does not match"):
        useq.Position(name="B9", plate_row=0, plate_col=0)


def test_no_plate_coords_preserves_name() -> None:
    assert useq.Position(name="my_pos").name == "my_pos"
    assert useq.Position(x=100).name is None


# --- plate_row / plate_col serialization -------------------------------------


def test_plate_json_round_trip() -> None:
    pos = useq.Position(x=1000, y=2000, plate_row=0, plate_col=1)
    data = json.loads(pos.model_dump_json())
    assert data["plate_row"] == 0
    assert data["plate_col"] == 1
    pos2 = useq.Position.model_validate(data)
    assert pos2.plate_row == 0
    assert pos2.plate_col == 1
    assert pos2.name == "A2"


def test_plate_json_round_trip_str() -> None:
    pos = useq.Position(plate_row="B", plate_col="3")
    data = json.loads(pos.model_dump_json())
    assert data["plate_row"] == "B"
    assert data["plate_col"] == "3"
    assert useq.Position.model_validate(data).name == "B3"


def test_plate_yaml_round_trip() -> None:
    seq = useq.MDASequence(
        stage_positions=[useq.Position(x=1000, y=1000, plate_row=0, plate_col=0)]
    )
    data = yaml.safe_load(seq.yaml())
    seq2 = useq.MDASequence(**data)
    assert seq2.stage_positions[0].plate_row == 0
    assert seq2.stage_positions[0].plate_col == 0
    assert seq2.stage_positions[0].name == "A1"


# --- plate_row / plate_col propagation through __add__ -----------------------


def test_plate_coords_propagate_through_add() -> None:
    well = useq.Position(x=1000, y=1000, plate_row=0, plate_col=0)
    offset = useq.RelativePosition(x=50, y=50, name="0000")
    result = well + offset
    assert result.plate_row == 0
    assert result.plate_col == 0
    assert result.name == "A1_0000"


# --- WellPlatePlan sets plate_row / plate_col --------------------------------


def test_well_plate_plan_sets_plate_coords() -> None:
    pp = useq.WellPlatePlan(
        plate="24-well",
        a1_center_xy=(0, 0),
        selected_wells=([0, 1], [0, 1]),
    )
    for pos in pp.selected_well_positions:
        assert pos.plate_row is not None
        assert pos.plate_col is not None


def test_well_plate_plan_image_positions_carry_plate_coords() -> None:
    pp = useq.WellPlatePlan(
        plate="24-well",
        a1_center_xy=(0, 0),
        selected_wells=([0], [0]),
        well_points_plan=useq.GridRowsColumns(
            rows=1, columns=2, fov_width=1, fov_height=1
        ),
    )
    for pos in pp.image_positions:
        assert pos.plate_row is not None
        assert pos.plate_col is not None


# --- name_pattern on grid plans ----------------------------------------------


def test_grid_default_name_pattern() -> None:
    names = [p.name for p in useq.GridRowsColumns(rows=2, columns=2)]
    assert names == ["0000", "0001", "0002", "0003"]


_CUSTOM_PATTERN_CASES = [
    pytest.param(
        "row_{row:03d}_col_{col:04d}",
        {"row_000_col_0000", "row_000_col_0001", "row_001_col_0001", "row_001_col_0000"},
        id="row_col",
    ),
    pytest.param(
        "fov{idx}",
        {"fov0", "fov1", "fov2", "fov3"},
        id="fov_idx",
    ),
    pytest.param(
        "r{row}c{col}",
        {"r0c0", "r0c1", "r1c0", "r1c1"},
        id="compact",
    ),
]


@pytest.mark.parametrize("pattern, expected_names", _CUSTOM_PATTERN_CASES)
def test_grid_custom_name_pattern(pattern: str, expected_names: set[str]) -> None:
    grid = useq.GridRowsColumns(rows=2, columns=2, name_pattern=pattern)
    names = {p.name for p in grid}
    assert names == expected_names


def test_grid_name_pattern_serialization() -> None:
    grid = useq.GridRowsColumns(rows=2, columns=2, name_pattern="site_{idx:04d}")
    data = json.loads(grid.model_dump_json())
    assert data["name_pattern"] == "site_{idx:04d}"
    grid2 = useq.GridRowsColumns.model_validate(data)
    assert grid2.name_pattern == "site_{idx:04d}"


def test_grid_name_pattern_from_yaml() -> None:
    data = yaml.safe_load('rows: 2\ncolumns: 2\nname_pattern: "r{row}c{col}"')
    grid = useq.GridRowsColumns(**data)
    assert {p.name for p in grid} == {"r0c0", "r0c1", "r1c0", "r1c1"}


# --- composite pos_name in MDAEvent ------------------------------------------


def test_plate_position_with_grid_composite_pos_name() -> None:
    """Plate positions with grid get composite pos_name: 'A1_0000'."""
    seq = useq.MDASequence(
        stage_positions=[useq.Position(plate_row=0, plate_col=0)],
        grid_plan=useq.GridRowsColumns(rows=1, columns=2, fov_width=180, fov_height=180),
    )
    events = list(seq)
    assert events[0].pos_name == "A1_0000"
    assert events[1].pos_name == "A1_0001"


def test_regular_position_with_grid_no_composite() -> None:
    """Non-plate positions should NOT get grid name appended."""
    seq = useq.MDASequence(
        stage_positions=[useq.Position(x=1000, y=1000, name="MyPos")],
        grid_plan=useq.GridRowsColumns(rows=1, columns=2, fov_width=180, fov_height=180),
    )
    events = list(seq)
    assert all(e.pos_name == "MyPos" for e in events)


def test_plate_position_without_grid_pos_name() -> None:
    seq = useq.MDASequence(
        stage_positions=[useq.Position(plate_row=0, plate_col=0)]
    )
    assert list(seq)[0].pos_name == "A1"


def test_multiple_wells_with_grid_pos_names() -> None:
    seq = useq.MDASequence(
        stage_positions=[
            useq.Position(x=1000, y=1000, plate_row=0, plate_col=0),
            useq.Position(x=2000, y=2000, plate_row=1, plate_col=1),
        ],
        grid_plan=useq.GridRowsColumns(rows=1, columns=2, fov_width=180, fov_height=180),
    )
    pos_names = {e.pos_name for e in seq}
    assert pos_names == {"A1_0000", "A1_0001", "B2_0000", "B2_0001"}
