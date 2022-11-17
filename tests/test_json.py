from pathlib import Path

from useq import MDASequence

JSON = '{"metadata": {"some info": "something"}, "axis_order": "tpcz", "stage_positions": [{"x": 10.0, "y": 20.0, "z": null, "name": null, "z_plan": {"go_up": true}}, {"x": 10.0, "y": 20.0, "z": 50.0, "name": "test_name", "z_plan": {"go_up": true, "above": 10.0, "below": 0.0, "step": 1.0}}], "channels": [{"config": "Cy5", "group": "Channel", "exposure": 50.0, "do_stack": true, "z_offset": 0.0, "acquire_every": 1, "camera": null}, {"config": "FITC", "group": "Channel", "exposure": 100.0, "do_stack": true, "z_offset": 0.0, "acquire_every": 1, "camera": null}, {"config": "DAPI", "group": "Channel", "exposure": null, "do_stack": false, "z_offset": 0.0, "acquire_every": 3, "camera": null}], "time_plan": {"prioritize_duration": false, "phases": [{"prioritize_duration": false, "interval": 3.0, "loops": 3}, {"prioritize_duration": true, "interval": 10.0, "duration": 2400.0}]}, "z_plan": {"go_up": true, "range": 1.0, "step": 0.5}}'  # noqa


MDA = MDASequence(
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
)


def test_json(tmp_path: Path) -> None:
    json_file = tmp_path / "test.json"
    json_file.write_text(JSON)
    mda = MDASequence.parse_file(json_file)
    assert mda == MDA
    # round trip
    assert mda.json(exclude={"uid"}) == JSON
