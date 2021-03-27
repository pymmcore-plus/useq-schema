from pathlib import Path

from useq import MDASequence

YAML = """
axis_order: tpcz
channels:
- config: Cy5
  exposure: 50.0
- config: FITC
  exposure: 100.0
- acquire_every: 3
  config: DAPI
  do_stack: false
stage_positions:
- x: 10.0
  y: 20.0
- x: 10.0
  y: 20.0
  z: 50.0
  z_plan:
    above: 10.0
    below: 0.0
    step: 1.0
time_plan:
  phases:
  - interval: 0:00:03
    loops: 3
  - duration: 0:40:00
    interval: 0:00:10
z_plan:
  range: 1.0
  step: 0.5
"""


MDA = MDASequence(
    axis_order="tpcz",
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


def test_yaml(tmp_path: Path) -> None:
    yaml_file = tmp_path / "test.yaml"
    yaml_file.write_text(YAML)
    mda = MDASequence.parse_file(yaml_file)
    assert mda == MDA
    # round trip
    assert f"\n{mda.yaml()}" == YAML
