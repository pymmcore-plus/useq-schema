import itertools
from typing import Any, List, Sequence, Tuple

import numpy as np
import pytest
from pydantic import BaseModel

from useq import (
    Channel,
    GridFromEdges,
    GridRelative,
    MDAEvent,
    MDASequence,
    Position,
    TDurationLoops,
    TIntervalDuration,
    TIntervalLoops,
    ZAboveBelow,
    ZAbsolutePositions,
    ZRangeAround,
    ZRelativePositions,
)
from useq._grid import OrderMode, RelativeTo

_T = List[Tuple[Any, Sequence[float]]]

z_as_class: _T = [
    (ZAboveBelow(above=8, below=4, step=2), [-4, -2, 0, 2, 4, 6, 8]),
    (ZAbsolutePositions(absolute=[0, 0.5, 5]), [0, 0.5, 5]),
    (ZRelativePositions(relative=[0, 0.5, 5]), [0, 0.5, 5]),
    (ZRangeAround(range=8, step=1), [-4, -3, -2, -1, 0, 1, 2, 3, 4]),
]
z_as_dict: _T = [
    ({"above": 8, "below": 4, "step": 2}, [-4, -2, 0, 2, 4, 6, 8]),
    ({"range": 8, "step": 1}, [-4, -3, -2, -1, 0, 1, 2, 3, 4]),
    ({"absolute": [0, 0.5, 5]}, [0, 0.5, 5]),
    ({"relative": [0, 0.5, 5]}, [0, 0.5, 5]),
]
z_inputs = z_as_class + z_as_dict

t_as_class: _T = [
    # frame every second for 4 seconds
    (TIntervalDuration(interval=1, duration=4), [0, 1, 2, 3, 4]),
    # 5 frames spanning 8 seconds
    (TDurationLoops(loops=5, duration=8), [0, 2, 4, 6, 8]),
    # 5 frames, taken every 250 ms
    (TIntervalLoops(loops=5, interval=0.25), [0, 0.25, 0.5, 0.75, 1]),
    (
        [
            TIntervalLoops(loops=5, interval=0.25),
            TIntervalDuration(interval=1, duration=4),
        ],
        [0, 0.25, 0.5, 0.75, 1, 2, 3, 4, 5],
    ),
]

t_as_dict: _T = [
    ({"interval": 0.5, "duration": 2}, [0, 0.5, 1, 1.5, 2]),
    ({"loops": 5, "duration": 8}, [0, 2, 4, 6, 8]),
    ({"loops": 5, "interval": 0.25}, [0, 0.25, 0.5, 0.75, 1]),
    (
        [{"loops": 5, "interval": 0.25}, {"interval": 1, "duration": 4}],
        [0, 0.25, 0.50, 0.75, 1, 2, 3, 4, 5],
    ),
    ({"loops": 5, "duration": {"milliseconds": 8}}, [0, 0.002, 0.004, 0.006, 0.008]),
    ({"loops": 5, "duration": {"seconds": 8}}, [0, 2, 4, 6, 8]),
]
t_inputs = t_as_class + t_as_dict

g_as_dict = [
    (
        {"overlap": 10.0, "rows": 1, "columns": 2, "relative_to": "center"},
        [(10.0, 10.0), OrderMode.row_wise_snake, 1, 2, RelativeTo.center],
    ),
    (
        {"overlap": 10.0, "rows": 1, "columns": 2, "relative_to": "top_left"},
        [(10.0, 10.0), OrderMode.row_wise_snake, 1, 2, RelativeTo.top_left],
    ),
    (
        {"overlap": 10.0, "top": 0.0, "left": 0.0, "bottom": 2.0, "right": 2.0},
        [(10.0, 10.0), OrderMode.row_wise_snake, 0.0, 0.0, 2.0, 2.0],
    ),
]

g_as_class = [
    (
        GridRelative(overlap=10.0, rows=1, columns=2, relative_to="center"),
        [(10.0, 10.0), OrderMode.row_wise_snake, 1, 2, RelativeTo.center],
    ),
    (
        GridFromEdges(overlap=10.0, top=0.0, left=0, bottom=2, right=2),
        [(10.0, 10.0), OrderMode.row_wise_snake, 0.0, 0.0, 2.0, 2.0],
    ),
]
g_inputs = g_as_class + g_as_dict


all_orders = ["".join(i) for i in itertools.permutations("tpgcz")]

c_inputs = [
    ("DAPI", ("Channel", "DAPI")),
    ({"config": "DAPI"}, ("Channel", "DAPI")),
    ({"config": "DAPI", "group": "Group", "acquire_every": 3}, ("Group", "DAPI")),
    (Channel(config="DAPI"), ("Channel", "DAPI")),
    (Channel(config="DAPI", group="Group"), ("Group", "DAPI")),
]

p_inputs = [
    ([{"x": 0, "y": 1, "z": 2}], (0, 1, 2)),
    ([{"y": 200}], (None, 200, None)),
    ([(100, 200, 300)], (100, 200, 300)),
    (
        [
            {
                "z": 100,
                "sequence": {"z_plan": {"above": 8, "below": 4, "step": 2}},
            }
        ],
        (None, None, 100),
    ),
    ([np.ones(3)], (1, 1, 1)),
    ([(None, 200, None)], (None, 200, None)),
    ([np.ones(2)], (1, 1, None)),
    (np.array([[0, 0, 0], [1, 1, 1]]), (0, 0, 0)),
    (np.array([0, 0]), (0, 0, None)),
    ([Position(x=100, y=200, z=300)], (100, 200, 300)),
]


@pytest.mark.parametrize("zplan, zexpectation", z_inputs)
def test_z_plan(zplan: Any, zexpectation: Sequence[float]) -> None:
    assert list(MDASequence(z_plan=zplan).z_plan) == zexpectation


@pytest.mark.parametrize("gridplan, gridexpectation", g_inputs)
def test_g_plan(gridplan: Any, gridexpectation: Sequence[Any]) -> None:
    assert [
        i[1] for i in list(MDASequence(grid_plan=gridplan).grid_plan)
    ] == gridexpectation


@pytest.mark.parametrize("tplan, texpectation", t_inputs)
def test_time_plan(tplan: Any, texpectation: Sequence[float]) -> None:
    assert list(MDASequence(time_plan=tplan).time_plan) == texpectation


@pytest.mark.parametrize("channel, cexpectation", c_inputs)
def test_channel(channel: Any, cexpectation: Sequence[float]) -> None:
    channel = MDASequence(channels=[channel]).channels[0]
    assert (channel.group, channel.config) == cexpectation


@pytest.mark.parametrize("position, pexpectation", p_inputs)
def test_stage_positions(position: Any, pexpectation: Sequence[float]) -> None:
    position = MDASequence(stage_positions=position).stage_positions[0]
    assert (position.x, position.y, position.z) == pexpectation


def test_axis_order_errors() -> None:
    with pytest.raises(ValueError, match="acquisition order must be a"):
        MDASequence(axis_order=1)
    with pytest.raises(ValueError, match="Duplicate entries found"):
        MDASequence(axis_order="tpgcztpgcz")

    # p after z not ok when z_plan in stage_positions
    with pytest.raises(ValueError, match="'z' cannot precede 'p' in acquisition"):
        MDASequence(
            axis_order="zpc",
            z_plan={"top": 6, "bottom": 0, "step": 1},
            channels=["DAPI"],
            stage_positions=[
                {
                    "x": 0,
                    "y": 0,
                    "z": 0,
                    "sequence": {"z_plan": {"range": 2, "step": 1}},
                }
            ],
        )
    # p before z ok
    MDASequence(
        axis_order="pzc",
        z_plan={"top": 6, "bottom": 0, "step": 1},
        channels=["DAPI"],
        stage_positions=[
            {
                "x": 0,
                "y": 0,
                "z": 0,
                "sequence": {"z_plan": {"range": 2, "step": 1}},
            }
        ],
    )

    # c precedes t not ok if acquire_every > 1 in channels
    with pytest.warns(UserWarning, match="Channels with skipped frames detected"):
        MDASequence(
            axis_order="ct",
            time_plan={"interval": 1, "duration": 10},
            channels=[{"config": "DAPI", "acquire_every": 3}],
        )

    # absolute grid_plan with multiple stage positions

    with pytest.warns(UserWarning, match="Global grid plan will override"):
        MDASequence(
            stage_positions=[(0, 0, 0), (10, 10, 10)],
            grid_plan={"top": 1, "bottom": -1, "left": 0, "right": 0},
        )

    # if grid plan is relative, is ok
    MDASequence(
        stage_positions=[(0, 0, 0), (10, 10, 10)],
        grid_plan={"rows": 2, "columns": 2},
    )

    # if all but one sub-position has a grid plan , is ok
    MDASequence(
        stage_positions=[
            (0, 0, 0),
            {"sequence": {"grid_plan": {"rows": 2, "columns": 2}}},
            {
                "sequence": {
                    "grid_plan": {"top": 1, "bottom": -1, "left": 0, "right": 0}
                }
            },
        ],
        grid_plan={"top": 1, "bottom": -1, "left": 0, "right": 0},
    )

    # multi positions in position sub-sequence
    with pytest.raises(ValueError, match="Currently, a Position sequence cannot"):
        MDASequence(
            stage_positions=[
                {"sequence": {"stage_positions": [(10, 10, 10), (20, 20, 20)]}}
            ]
        )


@pytest.mark.parametrize("tplan, texpectation", t_as_dict[1:3])
@pytest.mark.parametrize("zplan, zexpectation", z_as_dict[:2])
@pytest.mark.parametrize("channel, cexpectation", c_inputs[:3])
@pytest.mark.parametrize("positions, pexpectation", p_inputs[:3])
def test_combinations(
    tplan: Any,
    texpectation: Sequence[float],
    zplan: Any,
    zexpectation: Sequence[float],
    channel: Any,
    cexpectation: Sequence[str],
    positions: Any,
    pexpectation: Sequence[float],
) -> None:
    mda = MDASequence(
        time_plan=tplan, z_plan=zplan, channels=[channel], stage_positions=positions
    )

    assert list(mda.z_plan) == zexpectation
    assert list(mda.time_plan) == texpectation
    assert (mda.channels[0].group, mda.channels[0].config) == cexpectation
    position = mda.stage_positions[0]
    assert (position.x, position.y, position.z) == pexpectation

    assert mda.to_pycromanager()


@pytest.mark.parametrize("cls", [MDASequence, MDAEvent])
def test_schema(cls: BaseModel) -> None:
    assert cls.schema()
    assert cls.schema_json()


def test_z_position() -> None:
    mda = MDASequence(axis_order="tpcz", stage_positions=[(222, 1, 10), (111, 1, 20)])
    assert not mda.z_plan
    for event in mda:
        assert event.z_pos


def test_shape_and_axes() -> None:
    mda = MDASequence(
        z_plan=z_as_class[0][0], time_plan=t_as_class[0][0], axis_order="tzp"
    )
    assert mda.shape == (5, 7)
    assert mda.axis_order == "tzp"
    assert mda.used_axes == "tz"
    assert mda.sizes == {"t": 5, "z": 7, "p": 0}

    mda2 = mda.replace(axis_order="zptc")
    assert mda2.shape == (7, 5)
    assert mda2.axis_order == "zptc"
    assert mda2.used_axes == "zt"
    assert mda2.sizes == {"z": 7, "p": 0, "t": 5, "c": 0}

    assert mda2.uid != mda.uid

    with pytest.raises(ValueError):
        mda.replace(axis_order="zptasdfs")


def test_hashable(mda1: MDASequence) -> None:
    assert hash(mda1)
    assert mda1 == mda1
    assert mda1 != 23


def test_mda_str_repr(mda1: MDASequence) -> None:
    assert str(mda1)
    assert repr(mda1)


def test_mda_warns_extra() -> None:
    with pytest.warns(UserWarning, match="got unknown keyword arguments"):
        seq = MDASequence(random_key="random_value")
    assert not hasattr(seq, "random_key")

    with pytest.warns(UserWarning, match="got unknown keyword arguments"):
        Position(random_key="random_value")


def test_skip_channel_do_stack_no_zplan():
    mda = MDASequence(channels=[{"config": "DAPI", "do_stack": False}])
    assert len(list(mda)) == 1
