"""Performance benchmarks for useq-schema, run with pytest-codspeed.

Run locally with:

    uv run --group bench pytest benchmarks --codspeed
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pytest

import useq
from useq import v2

if TYPE_CHECKING:
    from pytest_codspeed import BenchmarkFixture


# A realistic multi-dimensional acquisition: time, positions (one with a
# sub-sequence), grid, channels, z-stack and autofocus.
MDA_KWARGS: dict[str, Any] = {
    "axis_order": "tpgcz",
    "metadata": {"some info": "something"},
    "stage_positions": [
        (10, 20),
        {
            "x": 10,
            "y": 20,
            "z": 50,
            "name": "test_name",
            "sequence": {
                "z_plan": {"above": 10, "below": 0, "step": 1},
                "grid_plan": {"rows": 2, "columns": 3},
            },
        },
    ],
    "channels": [
        {"config": "Cy5", "exposure": 50},
        {"config": "FITC", "exposure": 100.0},
        {"config": "DAPI", "do_stack": False, "acquire_every": 3},
    ],
    "time_plan": [
        {"interval": 3, "loops": 3},
        {"interval": 10, "loops": 2},
    ],
    "z_plan": {"range": 1.0, "step": 0.5},
    "grid_plan": {"rows": 2, "columns": 1},
    "autofocus_plan": {
        "autofocus_device_name": "Z",
        "autofocus_motor_offset": 50,
        "axes": ("c",),
    },
}

# v2 positions cannot carry a sub-sequence, so drop it for the v2 benchmarks.
V2_MDA_KWARGS: dict[str, Any] = {
    **MDA_KWARGS,
    "stage_positions": [(10, 20), {"x": 10, "y": 20, "z": 50, "name": "test_name"}],
}

# A simpler, larger sequence: 2 timepoints x 4 positions x 3x3 grid x 2 channels
# x 11 z-steps = 1584 events.
LARGE_KWARGS: dict[str, Any] = {
    "axis_order": "tpgcz",
    "time_plan": {"interval": 1, "loops": 2},
    "stage_positions": [(0, 0, 0), (100, 0, 0), (0, 100, 0), (100, 100, 0)],
    "grid_plan": {"rows": 3, "columns": 3, "fov_width": 10, "fov_height": 10},
    "channels": ["DAPI", "FITC"],
    "z_plan": {"range": 10, "step": 1},
}


@pytest.fixture
def mda() -> useq.MDASequence:
    return useq.MDASequence(**MDA_KWARGS)


@pytest.fixture
def large_mda() -> useq.MDASequence:
    return useq.MDASequence(**LARGE_KWARGS)


# ---------------------------------------------------------------------------
# MDASequence construction, validation and serialization
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_mda_sequence_create() -> None:
    useq.MDASequence(**MDA_KWARGS)


def test_mda_sequence_iter_events(
    benchmark: BenchmarkFixture, mda: useq.MDASequence
) -> None:
    events = benchmark(lambda: list(mda.iter_events()))
    assert events


def test_mda_sequence_iter_events_large(
    benchmark: BenchmarkFixture, large_mda: useq.MDASequence
) -> None:
    events = benchmark(lambda: list(large_mda.iter_events()))
    assert len(events) == 1584


def test_mda_sequence_estimate_duration(
    benchmark: BenchmarkFixture, mda: useq.MDASequence
) -> None:
    estimate = benchmark(mda.estimate_duration)
    assert estimate.total_duration > 0


def test_mda_sequence_to_json(
    benchmark: BenchmarkFixture, mda: useq.MDASequence
) -> None:
    assert benchmark(mda.model_dump_json)


def test_mda_sequence_from_json(
    benchmark: BenchmarkFixture, mda: useq.MDASequence
) -> None:
    text = mda.model_dump_json()
    seq = benchmark(useq.MDASequence.model_validate_json, text)
    assert seq == mda


def test_mda_events_to_json(benchmark: BenchmarkFixture, mda: useq.MDASequence) -> None:
    events = list(mda.iter_events())

    def dump() -> list[str]:
        return [e.model_dump_json() for e in events]

    assert benchmark(dump)


# ---------------------------------------------------------------------------
# v2 MDASequence
# ---------------------------------------------------------------------------


@pytest.mark.benchmark
def test_v2_mda_sequence_create() -> None:
    v2.MDASequence(**V2_MDA_KWARGS)


def test_v2_mda_sequence_iter_events(benchmark: BenchmarkFixture) -> None:
    seq = v2.MDASequence(**V2_MDA_KWARGS)
    events = benchmark(lambda: list(seq.iter_events()))
    assert events


def test_v2_mda_sequence_iter_events_large(benchmark: BenchmarkFixture) -> None:
    seq = v2.MDASequence(**LARGE_KWARGS)
    events = benchmark(lambda: list(seq.iter_events()))
    assert len(events) == 1584


# ---------------------------------------------------------------------------
# Grid and point plans
# ---------------------------------------------------------------------------


def test_grid_rows_columns_iter(benchmark: BenchmarkFixture) -> None:
    plan = useq.GridRowsColumns(rows=20, columns=20, fov_width=10, fov_height=10)
    positions = benchmark(lambda: list(plan))
    assert len(positions) == 400


def test_grid_from_edges_iter(benchmark: BenchmarkFixture) -> None:
    plan = useq.GridFromEdges(
        top=0, left=0, bottom=500, right=500, fov_width=25, fov_height=25
    )
    positions = benchmark(lambda: list(plan))
    assert positions


def test_grid_from_polygon_iter(benchmark: BenchmarkFixture) -> None:
    plan = useq.GridFromPolygon(
        vertices=[(0, 0), (400, 50), (500, 300), (250, 500), (20, 350)],
        fov_width=20,
        fov_height=20,
        overlap=10,
    )
    positions = benchmark(lambda: list(plan))
    assert positions


def test_random_points_iter(benchmark: BenchmarkFixture) -> None:
    plan = useq.RandomPoints(
        num_points=100,
        max_width=1000,
        max_height=1000,
        fov_width=10,
        fov_height=10,
        random_seed=0,
        order="two_opt",
    )
    positions = benchmark(lambda: list(plan))
    assert len(positions) == 100


# ---------------------------------------------------------------------------
# Well plates
# ---------------------------------------------------------------------------


def test_well_plate_plan_image_positions(benchmark: BenchmarkFixture) -> None:
    def build() -> list[useq.Position]:
        plan = useq.WellPlatePlan(
            plate=384,
            a1_center_xy=(500, 200),
            rotation=2,
            selected_wells=np.s_[:, :],
            well_points_plan=useq.GridRowsColumns(rows=2, columns=2),
        )
        return list(plan.image_positions)

    positions = benchmark(build)
    assert len(positions) == 384 * 4


def test_well_plate_plan_iter_sequence(benchmark: BenchmarkFixture) -> None:
    seq = useq.MDASequence(
        stage_positions=useq.WellPlatePlan(
            plate=96,
            a1_center_xy=(0, 0),
            selected_wells=np.s_[:4, :6],
            well_points_plan=useq.RandomPoints(num_points=4, random_seed=0),
        ),
        channels=["DAPI", "FITC"],
    )
    events = benchmark(lambda: list(seq.iter_events()))
    assert len(events) == 24 * 4 * 2
