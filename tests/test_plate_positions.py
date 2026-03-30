"""Tests for plate_row/plate_col on Position."""

from __future__ import annotations

import json

import yaml

import useq


def test_position_plate_row_col() -> None:
    pos = useq.Position(x=1000, y=2000, plate_row=0, plate_col=1)
    assert pos.plate_row == 0
    assert pos.plate_col == 1


def test_position_no_plate_coords() -> None:
    pos = useq.Position(x=100)
    assert pos.plate_row is None
    assert pos.plate_col is None


def test_plate_json_round_trip() -> None:
    pos = useq.Position(x=1000, y=2000, plate_row=0, plate_col=1)
    data = json.loads(pos.model_dump_json())
    assert data["plate_row"] == 0
    assert data["plate_col"] == 1
    pos2 = useq.Position.model_validate(data)
    assert pos2.plate_row == 0
    assert pos2.plate_col == 1


def test_plate_yaml_round_trip() -> None:
    seq = useq.MDASequence(
        stage_positions=[useq.Position(x=1000, y=1000, plate_row=0, plate_col=0)]
    )
    data = yaml.safe_load(seq.yaml())
    seq2 = useq.MDASequence(**data)
    assert seq2.stage_positions[0].plate_row == 0
    assert seq2.stage_positions[0].plate_col == 0


def test_plate_coords_propagate_through_add() -> None:
    well = useq.Position(x=1000, y=1000, plate_row=0, plate_col=0, name="A1")
    offset = useq.RelativePosition(x=50, y=50, name="0000")
    result = well + offset
    assert result.plate_row == 0
    assert result.plate_col == 0


def test_well_plate_plan_sets_plate_coords() -> None:
    pp = useq.WellPlatePlan(
        plate="24-well",
        a1_center_xy=(0, 0),
        selected_wells=([0, 1], [0, 1]),
    )
    for pos in pp.selected_well_positions:
        assert pos.plate_row is not None
        assert pos.plate_col is not None
        assert isinstance(pos.plate_row, int)
        assert isinstance(pos.plate_col, int)


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
