from __future__ import annotations

from itertools import product
from typing import Any, Sequence

import useq
from useq import MDASequence

FITC = "FITC"
CY5 = "Cy5"
CY3 = "Cy3"
NAME = "name"
EMPTY: dict = {}
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
        assert actual_value == expectations[attr_name]


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
            stage_positions=[EMPTY, useq.Position(sequence=SEQ_1_CH)],
            channels=[CH_CY5],
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
        MDASequence(
            stage_positions=[useq.Position(x=0, y=0), (10, 20)],
            grid_plan=GRID_2x2,
        ),
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
            useq.Position(x=0, y=0),
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
        MDASequence(
            stage_positions=[useq.Position(x=0, y=0), (10, 20)], z_plan=Z_58_60
        ),
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
        stage_positions=[
            EMPTY,
            useq.Position(name=NAME, sequence={"z_plan": Z_28_30}),
        ],
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
            useq.Position(z=0),
            useq.Position(name=NAME, sequence={"z_plan": Z_58_60}),
        ],
        z_plan=Z_RANGE3,
    )
    expect_mda(
        mda,
        index=[
            {"p": 0, "z": 0},
            {"p": 0, "z": 1},
            {"p": 0, "z": 2},
            {"p": 0, "z": 3},
            {"p": 1, "z": 0},
            {"p": 1, "z": 1},
            {"p": 1, "z": 2},
        ],
        pos_name=[None] * 4 + [NAME] * 3,
        z_pos=[-1.5, -0.5, 0.5, 1.5, 58.0, 59.0, 60.0],
    )


def test_multi_z_in_position_sub_sequence() -> None:
    mda = MDASequence(
        stage_positions=[
            {"sequence": {"z_plan": Z_58_60}},
            {"sequence": {"z_plan": Z_RANGE3}},
            {"sequence": {"z_plan": Z_28_30}},
        ],
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
            {"p": 2, "z": 0},
            {"p": 2, "z": 1},
            {"p": 2, "z": 2},
        ],
        z_pos=[58.0, 59.0, 60.0, -1.5, -0.5, 0.5, 1.5, 28.0, 29.0, 30.0],
    )


# test time_plan
def test_t_with_multi_stage_positions() -> None:
    expect_mda(
        MDASequence(stage_positions=[EMPTY, EMPTY], time_plan=[TLOOP2]),
        index=genindex({"t": 2, "p": 2}),
        min_start_time=[0.0, 0.0, 1.0, 1.0],
    )


def test_t_only_in_position_sub_sequence() -> None:
    expect_mda(
        MDASequence(stage_positions=[EMPTY, {"sequence": {"time_plan": [TLOOP5]}}]),
        index=[
            {"p": 0},
            {"p": 1, "t": 0},
            {"p": 1, "t": 1},
            {"p": 1, "t": 2},
            {"p": 1, "t": 3},
            {"p": 1, "t": 4},
        ],
        min_start_time=[None, 0.0, 1.0, 2.0, 3.0, 4.0],
    )


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


def test_mix_cgz_axes() -> None:
    mda = MDASequence(
        axis_order="tpgcz",
        stage_positions=[
            useq.Position(x=0, y=0),
            useq.Position(
                name=NAME,
                x=10,
                y=10,
                z=30,
                sequence=MDASequence(
                    channels=[
                        {"config": FITC, "exposure": 200},
                        {"config": CY3, "exposure": 100},
                    ],
                    grid_plan=useq.GridRelative(rows=2, columns=1),
                    z_plan=Z_RANGE2,
                ),
            ),
        ],
        channels=[CH_CY5],
        z_plan={"top": 100, "bottom": 98, "step": 1},
        grid_plan=GRID_1100,
    )
    expect_mda(
        mda,
        index=[
            *genindex({"p": 1, "g": 3, "c": 1, "z": 3}),
            {"p": 1, "g": 0, "c": 0, "z": 0},
            {"p": 1, "g": 0, "c": 0, "z": 1},
            {"p": 1, "g": 0, "c": 0, "z": 2},
            {"p": 1, "g": 0, "c": 1, "z": 0},
            {"p": 1, "g": 0, "c": 1, "z": 1},
            {"p": 1, "g": 0, "c": 1, "z": 2},
            {"p": 1, "g": 1, "c": 0, "z": 0},
            {"p": 1, "g": 1, "c": 0, "z": 1},
            {"p": 1, "g": 1, "c": 0, "z": 2},
            {"p": 1, "g": 1, "c": 1, "z": 0},
            {"p": 1, "g": 1, "c": 1, "z": 1},
            {"p": 1, "g": 1, "c": 1, "z": 2},
        ],
        pos_name=[None] * 9 + [NAME] * 12,
        x_pos=[0.0] * 9 + [10.0] * 12,
        y_pos=[1, 1, 1, 0, 0, 0, -1, -1, -1] + [10.5] * 6 + [9.5] * 6,
        z_pos=[98.0, 99.0, 100.0] * 3 + [29.0, 30.0, 31.0] * 4,
        channel=[CY5] * 9 + ([FITC] * 3 + [CY3] * 3) * 2,
        exposure=[50.0] * 9 + [200.0] * 3 + [100.0] * 3 + [200.0] * 3 + [100.0] * 3,
    )


# axes order????
def test_order() -> None:
    sub_pos = useq.Position(
        z=50,
        sequence=MDASequence(
            channels=[CH_FITC, useq.Channel(config=CY3, exposure=200)]
        ),
    )
    mda = MDASequence(
        stage_positions=[useq.Position(z=0), sub_pos],
        channels=[CH_FITC, CH_CY5],
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
    expect_ch = [FITC] * 3 + [CY5] * 3 + [FITC, CY3] * 3
    expect_mda(mda, index=expected_indices, z_pos=expect_pos, channel=expect_ch)


def test_channels_and_pos_grid_plan() -> None:
    # test that all channels are acquired for each grid position
    sub_seq = MDASequence(grid_plan=useq.GridRelative(rows=2, columns=1))
    mda = MDASequence(
        channels=[CH_CY5, CH_FITC],
        stage_positions=[useq.Position(x=0, y=0, sequence=sub_seq)],
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
        stage_positions=[useq.Position(x=0, y=0, z=0, sequence={"z_plan": Z_RANGE2})],
    )
    expect_mda(
        mda,
        index=genindex({"p": 1, "c": 2, "z": 3}),
        z_pos=[-1.0, 0.0, 1.0, -1.0, 0.0, 1.0],
        channel=[CY5, CY5, CY5, FITC, FITC, FITC],
    )


def test_channels_and_pos_time_plan() -> None:
    # test that all channels are acquired for each timepoint
    mda = MDASequence(
        axis_order="tpgcz",
        channels=[CH_CY5, CH_FITC],
        stage_positions=[useq.Position(x=0, y=0, sequence={"time_plan": [TLOOP3]})],
    )
    expect_mda(
        mda,
        index=genindex({"p": 1, "c": 2, "t": 3}),
        min_start_time=[0.0, 1.0, 2.0, 0.0, 1.0, 2.0],
        channel=[CY5, CY5, CY5, FITC, FITC, FITC],
    )


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
