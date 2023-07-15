import pytest

from useq import MDASequence


@pytest.fixture
def mda1() -> MDASequence:
    return MDASequence(
        axis_order="tpgcz",
        metadata={"some info": "something"},
        stage_positions=[
            (10, 20),
            {
                "x": 10,
                "y": 20,
                "z": 50,
                "name": "test_name",
                "sequence": MDASequence(
                    z_plan={"above": 10, "below": 0, "step": 1},
                    grid_plan={"rows": 2, "columns": 3},
                ),
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
        grid_plan={"rows": 2, "columns": 1},
        autofocus_plan={
            "autofocus_device_name": "Z",
            "autofocus_motor_offset": 50,
            "axes": ("c",),
        },
    )
