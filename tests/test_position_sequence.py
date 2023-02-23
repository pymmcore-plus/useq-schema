import pytest

from useq import GridRelative, MDASequence


@pytest.fixture
def mda() -> MDASequence:
    return MDASequence(
        axis_order="tpgcz",
        stage_positions=[(10, 20, 0), {"name": "test", "x": 10, "y": 20, "z": 50}],
        channels=[{"config": "Cy5", "exposure": 50}],
    )


def _update_pos_sequence(mda: MDASequence, axis: str):
    p_seq = MDASequence()
    if "c" in axis:
        p_seq = p_seq.replace(channels=[{"config": "DAPI", "exposure": 100}])
    if "z" in axis:
        p_seq = p_seq.replace(z_plan={"top": 60, "bottom": 55, "step": 1})
    if "g" in axis:
        p_seq = p_seq.replace(grid_plan={"rows": 2, "columns": 2})
    if "t" in axis:
        p_seq = p_seq.replace(time_plan=[{"interval": 1, "loops": 2}])
    new_pos = [
        (10, 20, 0),
        {"name": "test", "x": 10, "y": 20, "z": 50, "sequence": p_seq},
    ]
    return mda.replace(stage_positions=new_pos)


def event_list(sequence: MDASequence) -> list:
    return [
        (
            i.global_index,
            i.index,
            i.pos_name,
            i.x_pos,
            i.y_pos,
            i.z_pos,
            i.min_start_time,
            i.exposure,
            # i.channel,
        )
        for i in sequence.iter_events()
    ]


def test_position_sequence_channels(mda: MDASequence) -> None:
    mda1 = mda.replace(
        channels=[
            {"config": "Cy5", "exposure": 50},
            {"config": "FITC", "exposure": 100.0},
        ]
    )
    mda2 = _update_pos_sequence(mda1, "c")

    assert event_list(mda1) == [
        (0, {"p": 0, "c": 0}, None, 10.0, 20.0, 0.0, None, 50.0),
        (1, {"p": 0, "c": 1}, None, 10.0, 20.0, 0.0, None, 100.0),
        (2, {"p": 1, "c": 0}, "test", 10.0, 20.0, 50.0, None, 50.0),
        (3, {"p": 1, "c": 1}, "test", 10.0, 20.0, 50.0, None, 100.0),
    ]

    assert event_list(mda2) == [
        (0, {"p": 0, "c": 0}, None, 10.0, 20.0, 0.0, None, 50.0),
        (1, {"p": 0, "c": 1}, None, 10.0, 20.0, 0.0, None, 100.0),
        (2, {"p": 1, "c": 0}, "test", 10.0, 20.0, 50.0, None, 100.0),
    ]


def test_position_sequence_zplan(mda: MDASequence) -> None:
    mda1 = mda.replace(z_plan={"range": 1.0, "step": 0.5})
    mda2 = _update_pos_sequence(mda1, "z")

    assert event_list(mda1) == [
        (0, {"p": 0, "c": 0, "z": 0}, None, 10.0, 20.0, -0.5, None, 50.0),
        (1, {"p": 0, "c": 0, "z": 1}, None, 10.0, 20.0, 0.0, None, 50.0),
        (2, {"p": 0, "c": 0, "z": 2}, None, 10.0, 20.0, 0.5, None, 50.0),
        (3, {"p": 1, "c": 0, "z": 0}, "test", 10.0, 20.0, 49.5, None, 50.0),
        (4, {"p": 1, "c": 0, "z": 1}, "test", 10.0, 20.0, 50.0, None, 50.0),
        (5, {"p": 1, "c": 0, "z": 2}, "test", 10.0, 20.0, 50.5, None, 50.0),
    ]

    assert event_list(mda2) == [
        (0, {"p": 0, "c": 0, "z": 0}, None, 10.0, 20.0, -0.5, None, 50.0),
        (1, {"p": 0, "c": 0, "z": 1}, None, 10.0, 20.0, 0.0, None, 50.0),
        (2, {"p": 0, "c": 0, "z": 2}, None, 10.0, 20.0, 0.5, None, 50.0),
        (3, {"p": 1, "c": 0, "z": 0}, "test", 10.0, 20.0, 55.0, None, 50.0),
        (4, {"p": 1, "c": 0, "z": 1}, "test", 10.0, 20.0, 56.0, None, 50.0),
        (5, {"p": 1, "c": 0, "z": 2}, "test", 10.0, 20.0, 57.0, None, 50.0),
        (6, {"p": 1, "c": 0, "z": 3}, "test", 10.0, 20.0, 58.0, None, 50.0),
        (7, {"p": 1, "c": 0, "z": 4}, "test", 10.0, 20.0, 59.0, None, 50.0),
        (8, {"p": 1, "c": 0, "z": 5}, "test", 10.0, 20.0, 60.0, None, 50.0),
    ]


def test_position_sequence_gridplan(mda: MDASequence) -> None:
    mda1 = mda.replace(grid_plan=GridRelative(rows=1, columns=2))
    mda2 = _update_pos_sequence(mda1, "g")

    assert event_list(mda1) == [
        (0, {"p": 0, "g": 0, "c": 0}, None, 9.5, 20.0, 0.0, None, 50.0),
        (1, {"p": 0, "g": 1, "c": 0}, None, 10.5, 20.0, 0.0, None, 50.0),
        (2, {"p": 1, "g": 0, "c": 0}, "test", 9.5, 20.0, 50.0, None, 50.0),
        (3, {"p": 1, "g": 1, "c": 0}, "test", 10.5, 20.0, 50.0, None, 50.0),
    ]

    assert event_list(mda2) == [
        (0, {"p": 0, "g": 0, "c": 0}, None, 9.5, 20.0, 0.0, None, 50.0),
        (1, {"p": 0, "g": 1, "c": 0}, None, 10.5, 20.0, 0.0, None, 50.0),
        (2, {"p": 1, "g": 0, "c": 0}, "test", 9.0, 20.5, 50.0, None, 50.0),
        (3, {"p": 1, "g": 1, "c": 0}, "test", 10.0, 20.5, 50.0, None, 50.0),
        (4, {"p": 1, "g": 2, "c": 0}, "test", 10.0, 19.5, 50.0, None, 50.0),
        (5, {"p": 1, "g": 3, "c": 0}, "test", 9.0, 19.5, 50.0, None, 50.0),
    ]


def test_position_sequence_time(mda: MDASequence) -> None:
    mda1 = mda.replace(time_plan=[{"interval": 1, "loops": 4}])
    mda2 = _update_pos_sequence(mda1, "t")

    assert event_list(mda1) == [
        (0, {"t": 0, "p": 0, "c": 0}, None, 10.0, 20.0, 0.0, 0.0, 50.0),
        (1, {"t": 0, "p": 1, "c": 0}, "test", 10.0, 20.0, 50.0, 0.0, 50.0),
        (2, {"t": 1, "p": 0, "c": 0}, None, 10.0, 20.0, 0.0, 1.0, 50.0),
        (3, {"t": 1, "p": 1, "c": 0}, "test", 10.0, 20.0, 50.0, 1.0, 50.0),
        (4, {"t": 2, "p": 0, "c": 0}, None, 10.0, 20.0, 0.0, 2.0, 50.0),
        (5, {"t": 2, "p": 1, "c": 0}, "test", 10.0, 20.0, 50.0, 2.0, 50.0),
        (6, {"t": 3, "p": 0, "c": 0}, None, 10.0, 20.0, 0.0, 3.0, 50.0),
        (7, {"t": 3, "p": 1, "c": 0}, "test", 10.0, 20.0, 50.0, 3.0, 50.0),
    ]

    assert event_list(mda2) == [
        (0, {"t": 0, "p": 0, "c": 0}, None, 10.0, 20.0, 0.0, 0.0, 50.0),
        (1, {"t": 0, "p": 1, "c": 0}, "test", 10.0, 20.0, 50.0, 0.0, 50.0),
        (2, {"t": 1, "p": 1, "c": 0}, "test", 10.0, 20.0, 50.0, 1.0, 50.0),
        (3, {"t": 1, "p": 0, "c": 0}, None, 10.0, 20.0, 0.0, 1.0, 50.0),
        (4, {"t": 0, "p": 1, "c": 0}, "test", 10.0, 20.0, 50.0, 0.0, 50.0),
        (5, {"t": 1, "p": 1, "c": 0}, "test", 10.0, 20.0, 50.0, 1.0, 50.0),
        (6, {"t": 2, "p": 0, "c": 0}, None, 10.0, 20.0, 0.0, 2.0, 50.0),
        (7, {"t": 0, "p": 1, "c": 0}, "test", 10.0, 20.0, 50.0, 0.0, 50.0),
        (8, {"t": 1, "p": 1, "c": 0}, "test", 10.0, 20.0, 50.0, 1.0, 50.0),
        (9, {"t": 3, "p": 0, "c": 0}, None, 10.0, 20.0, 0.0, 3.0, 50.0),
        (10, {"t": 0, "p": 1, "c": 0}, "test", 10.0, 20.0, 50.0, 0.0, 50.0),
        (11, {"t": 1, "p": 1, "c": 0}, "test", 10.0, 20.0, 50.0, 1.0, 50.0),
    ]
