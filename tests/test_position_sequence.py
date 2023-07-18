from itertools import product
from typing import Any, Final, Sequence

import useq
from useq import MDASequence

FITC = "FITC"
CY5 = "Cy5"
NAME = "name"
EMPTY: Final[dict] = {}
CH_FITC = useq.Channel(config=FITC, exposure=100)
CH_CY5 = useq.Channel(config=CY5, exposure=50)
Z_RANGE2 = useq.ZRangeAround(range=2, step=1)
Z_RANGE3 = useq.ZRangeAround(range=3, step=1)
Z_28_30 = useq.ZTopBottom(bottom=28, top=30, step=1)
Z_58_60 = useq.ZTopBottom(bottom=58, top=60, step=1)
GRID_2x2 = useq.GridRelative(rows=2, columns=2)
GRID_1100 = useq.GridFromEdges(top=1, bottom=-1, left=0, right=0)
GRID_2100 = useq.GridFromEdges(top=2, bottom=-1, left=0, right=0)
SEQ_1_CH = MDASequence(channels=[CH_FITC])
TLOOP2 = useq.TIntervalLoops(interval=1, loops=2)
TLOOP3 = useq.TIntervalLoops(interval=1, loops=3)
TLOOP5 = useq.TIntervalLoops(interval=1, loops=5)


def genindex(axes: dict[str, int]) -> list[dict[str, int]]:
    ranges = (range(x) for x in axes.values())
    return [dict(zip(axes, p)) for p in product(*ranges)]


def expect_mda(mda: MDASequence, **expectations: Sequence[Any]) -> None:
    results: dict[str, list[Any]] = {}
    for event in mda:
        for attr_name in expectations:
            results.setdefault(attr_name, []).append(getattr(event, attr_name))

    for attr_name, actual_value in results.items():
        expect = expectations[attr_name]
        if actual_value != expect:
            raise AssertionError(
                f"Expected {attr_name} to be {expect}, but got {actual_value}"
            )


# test channels
def test_channel_only_in_position_sub_sequence() -> None:
    # test that a sub-position with a sequence has a channel, but not the main sequence
    expect_mda(
        MDASequence(stage_positions=[EMPTY, useq.Position(sequence=SEQ_1_CH)]),
        channel=[None, FITC],
        index=[{"p": 0}, {"p": 1, "c": 0}],
        exposure=[None, 100.0],
    )


def test_channel_in_main_and_position_sub_sequence() -> None:
    # test that a sub-position that specifies channel, overrides the global channel
    expect_mda(
        MDASequence(
            stage_positions=[EMPTY, useq.Position(sequence=SEQ_1_CH)], channels=[CH_CY5]
        ),
        channel=[CY5, FITC],
        index=[{"p": 0, "c": 0}, {"p": 1, "c": 0}],
        exposure=[50, 100.0],
    )


def test_subchannel_inherits_global_channel() -> None:
    # test that a sub-positions inherit the global channel
    mda = MDASequence(
        stage_positions=[EMPTY, {"sequence": {"z_plan": Z_28_30}}],
        channels=[CH_CY5],
    )
    assert all(e.channel.config == CY5 for e in mda)


# test grid_plan
def test_grid_relative_with_multi_stage_positions() -> None:
    # test that stage positions inherit the global relative grid plan

    expect_mda(
        MDASequence(stage_positions=[(0, 0), (10, 20)], grid_plan=GRID_2x2),
        index=genindex({"p": 2, "g": 4}),
        x_pos=[-0.5, 0.5, 0.5, -0.5, 9.5, 10.5, 10.5, 9.5],
        y_pos=[0.5, 0.5, -0.5, -0.5, 20.5, 20.5, 19.5, 19.5],
    )


def test_grid_relative_only_in_position_sub_sequence() -> None:
    # test a relative grid plan in a single stage position sub-sequence
    mda = MDASequence(
        stage_positions=[
            useq.Position(x=0, y=0),
            useq.Position(x=10, y=10, sequence={"grid_plan": GRID_2x2}),
        ],
    )

    expect_mda(
        mda,
        index=[
            {"p": 0},
            {"p": 1, "g": 0},
            {"p": 1, "g": 1},
            {"p": 1, "g": 2},
            {"p": 1, "g": 3},
        ],
        x_pos=[0.0, 9.5, 10.5, 10.5, 9.5],
        y_pos=[0.0, 10.5, 10.5, 9.5, 9.5],
    )


def test_grid_absolute_only_in_position_sub_sequence() -> None:
    # test a relative grid plan in a single stage position sub-sequence
    mda = MDASequence(
        stage_positions=[
            useq.Position(x=0, y=0),
            useq.Position(x=10, y=10, sequence={"grid_plan": GRID_1100}),
        ],
    )

    expect_mda(
        mda,
        index=[{"p": 0}, {"p": 1, "g": 0}, {"p": 1, "g": 1}, {"p": 1, "g": 2}],
        x_pos=[0.0, 0.0, 0.0, 0.0],
        y_pos=[0.0, 1.0, 0.0, -1.0],
    )


def test_grid_relative_in_main_and_position_sub_sequence() -> None:
    mda = MDASequence(
        stage_positions=[
            (0, 0),
            useq.Position(name=NAME, x=10, y=10, sequence={"grid_plan": GRID_2x2}),
        ],
        grid_plan=GRID_2x2,
    )
    expect_mda(
        mda,
        index=genindex({"p": 2, "g": 4}),
        pos_name=[None] * 4 + [NAME] * 4,
        x_pos=[-0.5, 0.5, 0.5, -0.5, 9.5, 10.5, 10.5, 9.5],
        y_pos=[0.5, 0.5, -0.5, -0.5, 10.5, 10.5, 9.5, 9.5],
    )


def test_grid_absolute_in_main_and_position_sub_sequence() -> None:
    mda = MDASequence(
        stage_positions=[
            EMPTY,
            useq.Position(name=NAME, sequence={"grid_plan": GRID_2100}),
        ],
        grid_plan=GRID_1100,
    )
    expect_mda(
        mda,
        index=[
            {"p": 0, "g": 0},
            {"p": 0, "g": 1},
            {"p": 0, "g": 2},
            {"p": 1, "g": 0},
            {"p": 1, "g": 1},
            {"p": 1, "g": 2},
            {"p": 1, "g": 3},
        ],
        pos_name=[None] * 3 + [NAME] * 4,
        x_pos=[0.0] * 7,
        y_pos=[1.0, 0.0, -1.0, 2.0, 1.0, 0.0, -1.0],
    )


def test_grid_absolute_in_main_and_grid_relative_in_position_sub_sequence() -> None:
    mda = MDASequence(
        stage_positions=[
            EMPTY,
            useq.Position(name=NAME, x=10, y=10, sequence={"grid_plan": GRID_2x2}),
        ],
        grid_plan=GRID_1100,
    )

    expect_mda(
        mda,
        index=[
            {"p": 0, "g": 0},
            {"p": 0, "g": 1},
            {"p": 0, "g": 2},
            {"p": 1, "g": 0},
            {"p": 1, "g": 1},
            {"p": 1, "g": 2},
            {"p": 1, "g": 3},
        ],
        pos_name=[None] * 3 + [NAME] * 4,
        x_pos=[0.0, 0.0, 0.0, 9.5, 10.5, 10.5, 9.5],
        y_pos=[1.0, 0.0, -1.0, 10.5, 10.5, 9.5, 9.5],
    )


def test_grid_relative_in_main_and_grid_absolute_in_position_sub_sequence() -> None:
    mda = MDASequence(
        stage_positions=[
            useq.Position(x=0, y=0),
            useq.Position(name=NAME, sequence={"grid_plan": GRID_1100}),
        ],
        grid_plan=GRID_2x2,
    )
    expect_mda(
        mda,
        index=[
            {"p": 0, "g": 0},
            {"p": 0, "g": 1},
            {"p": 0, "g": 2},
            {"p": 0, "g": 3},
            {"p": 1, "g": 0},
            {"p": 1, "g": 1},
            {"p": 1, "g": 2},
        ],
        pos_name=[None] * 4 + [NAME] * 3,
        x_pos=[-0.5, 0.5, 0.5, -0.5, 0.0, 0.0, 0.0],
        y_pos=[0.5, 0.5, -0.5, -0.5, 1.0, 0.0, -1.0],
    )


def test_multi_g_in_position_sub_sequence() -> None:
    mda = MDASequence(
        stage_positions=[
            {"sequence": {"grid_plan": {"rows": 1, "columns": 2}}},
            {"sequence": {"grid_plan": GRID_2x2}},
            {"sequence": {"grid_plan": GRID_1100}},
        ]
    )
    expect_mda(
        mda,
        index=[
            {"p": 0, "g": 0},
            {"p": 0, "g": 1},
            {"p": 1, "g": 0},
            {"p": 1, "g": 1},
            {"p": 1, "g": 2},
            {"p": 1, "g": 3},
            {"p": 2, "g": 0},
            {"p": 2, "g": 1},
            {"p": 2, "g": 2},
        ],
        x_pos=[-0.5, 0.5, -0.5, 0.5, 0.5, -0.5, 0.0, 0.0, 0.0],
        y_pos=[0.0, 0.0, 0.5, 0.5, -0.5, -0.5, 1.0, 0.0, -1.0],
    )


# test_z_plan
def test_z_relative_with_multi_stage_positions() -> None:
    expect_mda(
        mda=MDASequence(stage_positions=[(0, 0, 0), (10, 20, 10)], z_plan=Z_RANGE2),
        index=genindex({"p": 2, "z": 3}),
        x_pos=[0.0, 0.0, 0.0, 10.0, 10.0, 10.0],
        y_pos=[0.0, 0.0, 0.0, 20.0, 20.0, 20.0],
        z_pos=[-1.0, 0.0, 1.0, 9.0, 10.0, 11.0],
    )


def test_z_absolute_with_multi_stage_positions() -> None:
    expect_mda(
        MDASequence(stage_positions=[(0, 0), (10, 20)], z_plan=Z_58_60),
        index=genindex({"p": 2, "z": 3}),
        x_pos=[0.0, 0.0, 0.0, 10.0, 10.0, 10.0],
        y_pos=[0.0, 0.0, 0.0, 20.0, 20.0, 20.0],
        z_pos=[58.0, 59.0, 60.0, 58.0, 59.0, 60.0],
    )


def test_z_relative_only_in_position_sub_sequence() -> None:
    mda = MDASequence(
        stage_positions=[
            useq.Position(z=0),
            useq.Position(name=NAME, z=10, sequence={"z_plan": Z_RANGE2}),
        ],
    )

    expect_mda(
        mda,
        index=[{"p": 0}, {"p": 1, "z": 0}, {"p": 1, "z": 1}, {"p": 1, "z": 2}],
        pos_name=[None, NAME, NAME, NAME],
        z_pos=[0.0, 9.0, 10.0, 11.0],
    )


def test_z_absolute_only_in_position_sub_sequence() -> None:
    mda = MDASequence(
        stage_positions=[
            useq.Position(z=0),
            useq.Position(name=NAME, sequence={"z_plan": Z_58_60}),
        ],
    )

    expect_mda(
        mda,
        index=[{"p": 0}, {"p": 1, "z": 0}, {"p": 1, "z": 1}, {"p": 1, "z": 2}],
        pos_name=[None, NAME, NAME, NAME],
        z_pos=[0.0, 58, 59, 60],
    )


def test_z_relative_in_main_and_position_sub_sequence() -> None:
    mda = MDASequence(
        stage_positions=[
            useq.Position(z=0),
            useq.Position(name=NAME, z=10, sequence={"z_plan": Z_RANGE3}),
        ],
        z_plan=Z_RANGE2,
    )

    indices = genindex({"p": 2, "z": 4})
    indices.pop(3)
    expect_mda(
        mda,
        index=indices,
        pos_name=[None] * 3 + [NAME] * 4,
        z_pos=[-1.0, 0.0, 1.0, 8.5, 9.5, 10.5, 11.5],
    )


def test_z_absolute_in_main_and_position_sub_sequence() -> None:
    mda = MDASequence(
        stage_positions=[EMPTY, useq.Position(name=NAME, sequence={"z_plan": Z_28_30})],
        z_plan=Z_58_60,
    )
    expect_mda(
        mda,
        index=genindex({"p": 2, "z": 3}),
        pos_name=[None] * 3 + [NAME] * 3,
        z_pos=[58.0, 59.0, 60.0, 28.0, 29.0, 30.0],
    )


def test_z_absolute_in_main_and_z_relative_in_position_sub_sequence() -> None:
    mda = MDASequence(
        stage_positions=[
            EMPTY,
            useq.Position(name=NAME, z=10, sequence={"z_plan": Z_RANGE3}),
        ],
        z_plan=Z_58_60,
    )
    expect_mda(
        mda,
        index=[
            {"p": 0, "z": 0},
            {"p": 0, "z": 1},
            {"p": 0, "z": 2},
            {"p": 1, "z": 0},
            {"p": 1, "z": 1},
            {"p": 1, "z": 2},
            {"p": 1, "z": 3},
        ],
        pos_name=[None] * 3 + [NAME] * 4,
        z_pos=[58.0, 59.0, 60.0, 8.5, 9.5, 10.5, 11.5],
    )


def test_z_relative_in_main_and_z_absolute_in_position_sub_sequence() -> None:
    mda = MDASequence(
        stage_positions=[
            (None, None, 0),
            {
                "name": NAME,
                "sequence": {"z_plan": Z_58_60},
            },
        ],
        z_plan=Z_RANGE3,
    )
    assert [(i.index, i.pos_name, i.z_pos) for i in mda] == [
        ({"p": 0, "z": 0}, None, -1.5),
        ({"p": 0, "z": 1}, None, -0.5),
        ({"p": 0, "z": 2}, None, 0.5),
        ({"p": 0, "z": 3}, None, 1.5),
        ({"p": 1, "z": 0}, NAME, 58.0),
        ({"p": 1, "z": 1}, NAME, 59.0),
        ({"p": 1, "z": 2}, NAME, 60.0),
    ]


def test_multi_z_in_position_sub_sequence() -> None:
    mda = MDASequence(
        stage_positions=[
            {"sequence": {"z_plan": Z_58_60}},
            {"sequence": {"z_plan": Z_RANGE3}},
            {"sequence": {"z_plan": Z_28_30}},
        ],
    )

    assert [(i.index, i.z_pos) for i in mda] == [
        ({"p": 0, "z": 0}, 58.0),
        ({"p": 0, "z": 1}, 59.0),
        ({"p": 0, "z": 2}, 60.0),
        ({"p": 1, "z": 0}, -1.5),
        ({"p": 1, "z": 1}, -0.5),
        ({"p": 1, "z": 2}, 0.5),
        ({"p": 1, "z": 3}, 1.5),
        ({"p": 2, "z": 0}, 28.0),
        ({"p": 2, "z": 1}, 29.0),
        ({"p": 2, "z": 2}, 30.0),
    ]


# test time_plan
def test_t_with_multi_stage_positions() -> None:
    mda = MDASequence(stage_positions=[EMPTY, EMPTY], time_plan=[TLOOP2])
    assert [(i.index, i.min_start_time) for i in mda] == [
        ({"t": 0, "p": 0}, 0.0),
        ({"t": 0, "p": 1}, 0.0),
        ({"t": 1, "p": 0}, 1.0),
        ({"t": 1, "p": 1}, 1.0),
    ]


def test_t_only_in_position_sub_sequence() -> None:
    mda = MDASequence(
        stage_positions=[EMPTY, {"sequence": {"time_plan": [TLOOP5]}}],
    )
    assert [(i.index, i.min_start_time) for i in mda] == [
        ({"p": 0}, None),
        ({"p": 1, "t": 0}, 0.0),
        ({"p": 1, "t": 1}, 1.0),
        ({"p": 1, "t": 2}, 2.0),
        ({"p": 1, "t": 3}, 3.0),
        ({"p": 1, "t": 4}, 4.0),
    ]


def test_t_in_main_and_in_position_sub_sequence() -> None:
    mda = MDASequence(
        stage_positions=[EMPTY, {"sequence": {"time_plan": [TLOOP5]}}],
        time_plan=[TLOOP2],
    )
    expect_mda(
        mda,
        index=[
            {"t": 0, "p": 0},
            {"t": 0, "p": 1},
            {"t": 1, "p": 1},
            {"t": 2, "p": 1},
            {"t": 3, "p": 1},
            {"t": 4, "p": 1},
            {"t": 1, "p": 0},
            {"t": 0, "p": 1},
            {"t": 1, "p": 1},
            {"t": 2, "p": 1},
            {"t": 3, "p": 1},
            {"t": 4, "p": 1},
        ],
        min_start_time=[0.0, 0.0, 1.0, 2.0, 3.0, 4.0, 1.0, 0.0, 1.0, 2.0, 3.0, 4.0],
    )


def test_mix_cgz_axes():
    mda = MDASequence(
        axis_order="tpgcz",
        stage_positions=[
            (0, 0),
            {
                "name": NAME,
                "x": 10,
                "y": 10,
                "z": 30,
                "sequence": {
                    "channels": [
                        {"config": FITC, "exposure": 200},
                        {"config": "561", "exposure": 100},
                    ],
                    "grid_plan": {"rows": 2, "columns": 1},
                    "z_plan": Z_RANGE2,
                },
            },
        ],
        channels=[CH_CY5],
        z_plan={"top": 100, "bottom": 98, "step": 1},
        grid_plan=GRID_1100,
    )
    assert [
        (
            i.index,
            i.pos_name,
            i.x_pos,
            i.y_pos,
            i.z_pos,
            i.channel.config,
            i.exposure,
        )
        for i in mda
    ] == [
        ({"p": 0, "g": 0, "c": 0, "z": 0}, None, 0.0, 1.0, 98.0, CY5, 50.0),
        ({"p": 0, "g": 0, "c": 0, "z": 1}, None, 0.0, 1.0, 99.0, CY5, 50.0),
        ({"p": 0, "g": 0, "c": 0, "z": 2}, None, 0.0, 1.0, 100.0, CY5, 50.0),
        ({"p": 0, "g": 1, "c": 0, "z": 0}, None, 0.0, 0.0, 98.0, CY5, 50.0),
        ({"p": 0, "g": 1, "c": 0, "z": 1}, None, 0.0, 0.0, 99.0, CY5, 50.0),
        ({"p": 0, "g": 1, "c": 0, "z": 2}, None, 0.0, 0.0, 100.0, CY5, 50.0),
        ({"p": 0, "g": 2, "c": 0, "z": 0}, None, 0.0, -1.0, 98.0, CY5, 50.0),
        ({"p": 0, "g": 2, "c": 0, "z": 1}, None, 0.0, -1.0, 99.0, CY5, 50.0),
        ({"p": 0, "g": 2, "c": 0, "z": 2}, None, 0.0, -1.0, 100.0, CY5, 50.0),
        ({"p": 1, "g": 0, "c": 0, "z": 0}, NAME, 10.0, 10.5, 29.0, FITC, 200.0),
        ({"p": 1, "g": 0, "c": 0, "z": 1}, NAME, 10.0, 10.5, 30.0, FITC, 200.0),
        ({"p": 1, "g": 0, "c": 0, "z": 2}, NAME, 10.0, 10.5, 31.0, FITC, 200.0),
        ({"p": 1, "g": 0, "c": 1, "z": 0}, NAME, 10.0, 10.5, 29.0, "561", 100.0),
        ({"p": 1, "g": 0, "c": 1, "z": 1}, NAME, 10.0, 10.5, 30.0, "561", 100.0),
        ({"p": 1, "g": 0, "c": 1, "z": 2}, NAME, 10.0, 10.5, 31.0, "561", 100.0),
        ({"p": 1, "g": 1, "c": 0, "z": 0}, NAME, 10.0, 9.5, 29.0, FITC, 200.0),
        ({"p": 1, "g": 1, "c": 0, "z": 1}, NAME, 10.0, 9.5, 30.0, FITC, 200.0),
        ({"p": 1, "g": 1, "c": 0, "z": 2}, NAME, 10.0, 9.5, 31.0, FITC, 200.0),
        ({"p": 1, "g": 1, "c": 1, "z": 0}, NAME, 10.0, 9.5, 29.0, "561", 100.0),
        ({"p": 1, "g": 1, "c": 1, "z": 1}, NAME, 10.0, 9.5, 30.0, "561", 100.0),
        ({"p": 1, "g": 1, "c": 1, "z": 2}, NAME, 10.0, 9.5, 31.0, "561", 100.0),
    ]


# axes order????
def test_order():
    sub_pos = useq.Position(
        z=50,
        sequence=MDASequence(
            channels=[
                useq.Channel(config=FITC, exposure=200),
                useq.Channel(config="561", exposure=200),
            ]
        ),
    )
    mda = MDASequence(
        stage_positions=[useq.Position(z=0), sub_pos],
        channels=[
            useq.Channel(config=FITC, exposure=50),
            useq.Channel(config=CY5, exposure=50),
        ],
        z_plan=useq.ZRangeAround(range=2, step=1),
    )

    # might appear confusing at first, but the sub-position had no z plan to iterate
    # so, specifying a different axis_order for the subplan does not change the
    # order of the z positions (specified globally)
    expected_indices = [
        {"p": 0, "c": 0, "z": 0},
        {"p": 0, "c": 0, "z": 1},
        {"p": 0, "c": 0, "z": 2},
        {"p": 0, "c": 1, "z": 0},
        {"p": 0, "c": 1, "z": 1},
        {"p": 0, "c": 1, "z": 2},
        {"p": 1, "c": 0, "z": 0},
        {"p": 1, "c": 1, "z": 0},
        {"p": 1, "c": 0, "z": 1},
        {"p": 1, "c": 1, "z": 1},
        {"p": 1, "c": 0, "z": 2},
        {"p": 1, "c": 1, "z": 2},
    ]
    expect_pos = [-1.0, 0.0, 1.0, -1.0, 0.0, 1.0, 49.0, 49.0, 50.0, 50.0, 51.0, 51.0]
    expect_ch = [
        FITC,
        FITC,
        FITC,
        CY5,
        CY5,
        CY5,
        FITC,
        "561",
        FITC,
        "561",
        FITC,
        "561",
    ]

    expect_mda(mda, index=expected_indices, z_pos=expect_pos, channel=expect_ch)


def test_channels_and_pos_grid_plan() -> None:
    # test that all channels are acquired for each grid position
    mda = MDASequence(
        channels=[
            useq.Channel(config=CY5, exposure=10),
            useq.Channel(config=FITC, exposure=10),
        ],
        stage_positions=[
            useq.Position(
                x=0,
                y=0,
                sequence=MDASequence(grid_plan=useq.GridRelative(rows=2, columns=1)),
            )
        ],
    )

    expect_mda(
        mda,
        index=genindex({"p": 1, "c": 2, "g": 2}),
        x_pos=[0.0, 0.0, 0.0, 0.0],
        y_pos=[0.5, -0.5, 0.5, -0.5],
        channel=[CY5, CY5, FITC, FITC],
    )


def test_channels_and_pos_z_plan() -> None:
    # test that all channels are acquired for each z position
    mda = MDASequence(
        channels=[CH_CY5, CH_FITC],
        stage_positions=[{"x": 0, "y": 0, "z": 0, "sequence": {"z_plan": Z_RANGE2}}],
    )

    assert [(i.index, i.z_pos, i.channel.config) for i in mda] == [
        ({"p": 0, "c": 0, "z": 0}, -1.0, CY5),
        ({"p": 0, "c": 0, "z": 1}, 0.0, CY5),
        ({"p": 0, "c": 0, "z": 2}, 1.0, CY5),
        ({"p": 0, "c": 1, "z": 0}, -1.0, FITC),
        ({"p": 0, "c": 1, "z": 1}, 0.0, FITC),
        ({"p": 0, "c": 1, "z": 2}, 1.0, FITC),
    ]


def test_channels_and_pos_time_plan() -> None:
    # test that all channels are acquired for each timepoint
    mda = MDASequence(
        axis_order="tpgcz",
        channels=[CH_CY5, CH_FITC],
        stage_positions=[
            {"x": 0, "y": 0, "sequence": {"time_plan": [TLOOP3]}},
        ],
    )

    assert [(i.index, i.min_start_time, i.channel.config) for i in mda] == [
        ({"p": 0, "c": 0, "t": 0}, 0.0, CY5),
        ({"p": 0, "c": 0, "t": 1}, 1.0, CY5),
        ({"p": 0, "c": 0, "t": 2}, 2.0, CY5),
        ({"p": 0, "c": 1, "t": 0}, 0.0, FITC),
        ({"p": 0, "c": 1, "t": 1}, 1.0, FITC),
        ({"p": 0, "c": 1, "t": 2}, 2.0, FITC),
    ]


def test_channels_and_pos_z_grid_and_time_plan() -> None:
    # test that all channels are acquired for each z and grid positions
    sub_seq = useq.MDASequence(grid_plan=GRID_2x2, z_plan=Z_RANGE2, time_plan=[TLOOP2])
    mda = MDASequence(
        channels=[CH_CY5, CH_FITC],
        stage_positions=[useq.Position(x=0, y=0, sequence=sub_seq)],
    )

    expect_mda(mda, channel=[CY5] * 24 + [FITC] * 24)


def test_sub_channels_and_any_plan() -> None:
    # test that only specified sub-channels are acquired for each z plan
    mda = MDASequence(
        channels=[CY5, FITC],
        stage_positions=[{"sequence": {"channels": [FITC], "z_plan": Z_RANGE2}}],
    )

    expect_mda(mda, channel=[FITC, FITC, FITC])
