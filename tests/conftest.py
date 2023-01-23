import pytest

from useq import MDASequence


@pytest.fixture
def mda1() -> MDASequence:
    return MDASequence(
        axis_order="tpcz",
        metadata={"some info": "something"},
        stage_positions=[
            (10, 20),
            {
                "x": 10,
                "y": 20,
                "z": 50,
                "name": "test_name",
                "z_plan": {"above": 10, "below": 0, "step": 1},
            },
        ],
        channels=[
            {"config": "Cy5", "exposure": 50},
            {"config": "FITC", "exposure": 100.0},
            {"config": "DAPI", "do_stack": False, "acquire_every": 3},
        ],
        time_plan=[
            {"interval": 3, "loops": 3},
            {"duration": {"minutes": 40}, "interval": 10},
        ],
        z_plan={"range": 1.0, "step": 0.5},
        tile_plan={"is_relative": True, "rows": 2, "cols": 1},
    )
