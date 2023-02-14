import pytest

from useq import (
    GridRelative,
    MDASequence,
)


@pytest.fixture
def mda() -> MDASequence:
    return MDASequence(
        axis_order="tpgcz",
        stage_positions=[(10, 20), {"x": 10, "y": 20, "z": 50}],
        channels=[{"config": "Cy5", "exposure": 50}],
    )


def _update_pos_sequence(mda: MDASequence, axis: str):
    p_seq = MDASequence()
    if "c" in axis:
        p_seq = p_seq.replace(channels=[{"config": "DAPI"}])
    if "z" in axis:
        p_seq = p_seq.replace(z_plan={"range": 2, "step": 0.5})
    if "g" in axis:
        p_seq = p_seq.replace(grid_plan=GridRelative(rows=2, columns=2))
    new_pos = [(10, 20), {"x": 10, "y": 20, "z": 50, "sequence": p_seq}]
    return mda.replace(stage_positions=new_pos)


def test_position_sequence_channels(mda: MDASequence) -> None:
    mda1 = mda.replace(
        channels=[
            {"config": "Cy5", "exposure": 50},
            {"config": "FITC", "exposure": 100.0},
        ]
    )
    mda2 = _update_pos_sequence(mda1, "c")

    assert [(i.index, i.channel.config) for i in list(mda1.iter_events())] == [
        ({"p": 0, "c": 0}, "Cy5"),
        ({"p": 0, "c": 1}, "FITC"),
        ({"p": 1, "c": 0}, "Cy5"),
        ({"p": 1, "c": 1}, "FITC"),
    ]
    assert [(i.index, i.channel.config) for i in list(mda2.iter_events())] == [
        ({"p": 0, "c": 0}, "Cy5"),
        ({"p": 0, "c": 1}, "FITC"),
        ({"p": 1, "c": 0}, "DAPI"),
    ]


def test_position_sequence_zplan(mda: MDASequence) -> None:
    mda1 = mda.replace(z_plan={"range": 1.0, "step": 0.5})
    mda2 = _update_pos_sequence(mda1, "z")

    assert [i.index for i in list(mda1.iter_events())] == [
        {"p": 0, "c": 0, "z": 0},
        {"p": 0, "c": 0, "z": 1},
        {"p": 0, "c": 0, "z": 2},
        {"p": 1, "c": 0, "z": 0},
        {"p": 1, "c": 0, "z": 1},
        {"p": 1, "c": 0, "z": 2},
    ]

    assert [i.index for i in list(mda2.iter_events())] == [
        {"p": 0, "c": 0, "z": 0},
        {"p": 0, "c": 0, "z": 1},
        {"p": 0, "c": 0, "z": 2},
        {"p": 1, "c": 0, "z": 0},
        {"p": 1, "c": 0, "z": 1},
        {"p": 1, "c": 0, "z": 2},
        {"p": 1, "c": 0, "z": 3},
        {"p": 1, "c": 0, "z": 4},
    ]


def test_position_sequence_gridplan(mda: MDASequence) -> None:
    mda1 = mda.replace(grid_plan=GridRelative(rows=1, columns=2))
    mda2 = _update_pos_sequence(mda1, "g")

    assert [i.index for i in list(mda1.iter_events())] == [
        {"p": 0, "g": 0, "c": 0},
        {"p": 0, "g": 1, "c": 0},
        {"p": 1, "g": 0, "c": 0},
        {"p": 1, "g": 1, "c": 0},
    ]

    assert [i.index for i in list(mda2.iter_events())] == [
        {"p": 0, "g": 0, "c": 0},
        {"p": 0, "g": 1, "c": 0},
        {"p": 1, "g": 0, "c": 0},
        {"p": 1, "g": 1, "c": 0},
        {"p": 1, "g": 2, "c": 0},
        {"p": 1, "g": 3, "c": 0},
    ]
