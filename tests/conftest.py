from useq import MDASequence
import pytest


@pytest.fixture
def mda1() -> MDASequence:
    return MDASequence(
        axis_order="tpcz",
        metadata={"some info": "something"},
        stage_positions=[
            (10, 20),
            dict(x=10, y=20, z=50, z_plan=dict(above=10, below=0, step=1)),
        ],
        channels=[
            dict(config="Cy5", exposure=50),
            dict(config="FITC", exposure=100.0),
            dict(config="DAPI", do_stack=False, acquire_every=3),
        ],
        time_plan=[
            dict(interval=3, loops=3),
            dict(duration={"minutes": 40}, interval=10),
        ],
        z_plan=dict(range=1.0, step=0.5),
    )
