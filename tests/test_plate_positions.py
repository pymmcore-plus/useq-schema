"""Tests for plate_row/plate_col on Position."""

from __future__ import annotations

import json

import pytest
import yaml

import useq


def test_plate_row_col() -> None:
    pos = useq.Position(x=1000, y=2000, plate_row=0, plate_col=1)
    assert (pos.plate_row, pos.plate_col) == (0, 1)
    assert useq.Position(x=100).plate_row is None


@pytest.mark.parametrize("fmt", ["json", "yaml"])
def test_plate_round_trip(fmt: str) -> None:
    seq = useq.MDASequence(
        stage_positions=[useq.Position(x=1000, y=1000, plate_row=0, plate_col=1)]
    )
    if fmt == "json":
        data = json.loads(seq.model_dump_json())
    else:
        data = yaml.safe_load(seq.yaml())
    seq2 = useq.MDASequence.model_validate(data)
    assert seq2.stage_positions[0].plate_row == 0
    assert seq2.stage_positions[0].plate_col == 1


def test_plate_coords_propagate_through_add() -> None:
    p1 = useq.Position(x=1000, plate_row=0, plate_col=0, name="A1")
    p2 = useq.RelativePosition(x=50, name="0000")
    result = p1 + p2
    assert (result.plate_row, result.plate_col) == (0, 0)


@pytest.mark.parametrize("attr", ["selected_well_positions", "image_positions"])
def test_well_plate_plan_sets_plate_coords(attr: str) -> None:
    pp = useq.WellPlatePlan(
        plate="24-well",
        a1_center_xy=(0, 0),
        selected_wells=([0], [0]),
        well_points_plan=useq.GridRowsColumns(
            rows=1, columns=2, fov_width=1, fov_height=1
        ),
    )
    for pos in getattr(pp, attr):
        assert isinstance(pos.plate_row, int)
        assert isinstance(pos.plate_col, int)
