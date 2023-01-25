import itertools
from typing import Any, List, Sequence, Tuple

import numpy as np
import pytest
from pydantic import BaseModel

from useq import (
    Channel,
    MDAEvent,
    MDASequence,
    NoT,
    NoTile,
    NoZ,
    Position,
    TDurationLoops,
    TileFromCorners,
    TileRelative,
    TIntervalDuration,
    TIntervalLoops,
    ZAboveBelow,
    ZAbsolutePositions,
    ZRangeAround,
    ZRelativePositions,
)
from useq._tile import Coordinate, RelativeTo, TilePosition

_T = List[Tuple[Any, Sequence[float]]]

z_as_class: _T = [
    (ZAboveBelow(above=8, below=4, step=2), [-4, -2, 0, 2, 4, 6, 8]),
    (ZAbsolutePositions(absolute=[0, 0.5, 5]), [0, 0.5, 5]),
    (ZRelativePositions(relative=[0, 0.5, 5]), [0, 0.5, 5]),
    (ZRangeAround(range=8, step=1), [-4, -3, -2, -1, 0, 1, 2, 3, 4]),
    (NoZ(), []),
]
z_as_dict: _T = [
    (None, []),
    ({"above": 8, "below": 4, "step": 2}, [-4, -2, 0, 2, 4, 6, 8]),
    ({"absolute": [0, 0.5, 5]}, [0, 0.5, 5]),
    ({"relative": [0, 0.5, 5]}, [0, 0.5, 5]),
    ({"range": 8, "step": 1}, [-4, -3, -2, -1, 0, 1, 2, 3, 4]),
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
    (None, []),
    ({"interval": 0.5, "duration": 2}, [0, 0.5, 1, 1.5, 2]),
    ({"loops": 5, "duration": 8}, [0, 2, 4, 6, 8]),
    ({"loops": 5, "interval": 0.25}, [0, 0.25, 0.5, 0.75, 1]),
    (
        [{"loops": 5, "interval": 0.25}, {"interval": 1, "duration": 4}],
        [0, 0.25, 0.50, 0.75, 1, 2, 3, 4, 5],
    ),
    ({"loops": 5, "duration": {"milliseconds": 8}}, [0, 0.002, 0.004, 0.006, 0.008]),
    ({"loops": 5, "duration": {"seconds": 8}}, [0, 2, 4, 6, 8]),
    (NoT(), []),
]
t_inputs = t_as_class + t_as_dict

g_as_dict = [
    (
        {"overlap": 10.0, "rows": 1, "cols": 2, "relative_to": "center"},
        [(10.0, 10.0), True, 1, 2, RelativeTo.center],
    ),
    (
        {
            "overlap": (10.0, 8.0),
            "snake_order": False,
            "rows": 1,
            "cols": 2,
            "relative_to": "center",
        },
        [(10.0, 8.0), False, 1, 2, RelativeTo.center],
    ),
    (
        {"overlap": 10.0, "rows": 1, "cols": 2, "relative_to": "top_left"},
        [(10.0, 10.0), True, 1, 2, RelativeTo.top_left],
    ),
    (
        {
            "overlap": (10.0, 8.0),
            "snake_order": False,
            "rows": 1,
            "cols": 2,
            "relative_to": "top_left",
        },
        [(10.0, 8.0), False, 1, 2, RelativeTo.top_left],
    ),
    (
        {"overlap": 10.0, "corner1": {"x": 0, "y": 0}, "corner2": {"x": 2, "y": 2}},
        [(10.0, 10.0), True, Coordinate(x=0, y=0), Coordinate(x=2, y=2)],
    ),
    (
        {
            "overlap": (10.0, 8.0),
            "snake_order": False,
            "corner1": {"x": 0, "y": 0},
            "corner2": {"x": 2, "y": 2},
        },
        [(10.0, 8.0), False, Coordinate(x=0, y=0), Coordinate(x=2, y=2)],
    ),
    ({}, [(0.0, 0.0), True]),
]

g_as_class = [
    (
        TileRelative(overlap=10.0, rows=1, cols=2, relative_to="center"),
        [(10.0, 10.0), True, 1, 2, RelativeTo.center],
    ),
    (
        TileRelative(
            overlap=(10.0, 8.0),
            snake_order=False,
            rows=1,
            cols=2,
            relative_to="center",
        ),
        [(10.0, 8.0), False, 1, 2, RelativeTo.center],
    ),
    (
        TileFromCorners(overlap=10.0, corner1=(0, 0), corner2=(2, 2)),
        [(10.0, 10.0), True, Coordinate(x=0, y=0), Coordinate(x=2, y=2)],
    ),
    (
        TileFromCorners(
            overlap=(10.0, 8.0), snake_order=False, corner1=(0, 0), corner2=(2, 2)
        ),
        [(10.0, 8.0), False, Coordinate(x=0, y=0), Coordinate(x=2, y=2)],
    ),
    (NoTile(), [(0.0, 0.0), True]),
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
    ({"x": 0, "y": 1, "z": 2}, (0, 1, 2)),
    ({"y": 200}, (None, 200, None)),
    ((100, 200, 300), (100, 200, 300)),
    ({"z": 100, "z_plan": {"above": 8, "below": 4, "step": 2}}, (None, None, 100)),
    (np.ones(3), (1, 1, 1)),
    ((None, 200, None), (None, 200, None)),
    (np.ones(2), (1, 1, None)),
    (Position(x=100, y=200, z=300), (100, 200, 300)),
]


@pytest.mark.parametrize("zplan, zexpectation", z_inputs)
def test_z_plan(zplan: Any, zexpectation: Sequence[float]) -> None:
    assert list(MDASequence(z_plan=zplan).z_plan) == zexpectation


@pytest.mark.parametrize("tileplan, tileexpectation", g_inputs)
def test_g_plan(tileplan: Any, tileexpectation: Sequence[Any]) -> None:
    assert [
        i[1] for i in list(MDASequence(tile_plan=tileplan).tile_plan)
    ] == tileexpectation


@pytest.mark.parametrize("tplan, texpectation", t_inputs)
def test_t_plan(tplan: Any, texpectation: Sequence[float]) -> None:
    assert list(MDASequence(time_plan=tplan).time_plan) == texpectation


@pytest.mark.parametrize("channel, cexpectation", c_inputs)
def test_channel(channel: Any, cexpectation: Sequence[float]) -> None:
    channel = MDASequence(channels=[channel]).channels[0]
    assert (channel.group, channel.config) == cexpectation


@pytest.mark.parametrize("position, pexpectation", p_inputs)
def test_position(position: Any, pexpectation: Sequence[float]) -> None:
    position = MDASequence(stage_positions=[position]).stage_positions[0]
    assert (position.x, position.y, position.z) == pexpectation


@pytest.mark.parametrize("tplan, texpectation", t_as_dict[:5])
@pytest.mark.parametrize("zplan, zexpectation", z_as_dict)
@pytest.mark.parametrize("channel, cexpectation", c_inputs[:3])
@pytest.mark.parametrize("position, pexpectation", p_inputs[:4])
@pytest.mark.parametrize("tileplan, tileexpectation", g_inputs)
@pytest.mark.parametrize("order", ["tpgcz", "tpgzc", "pgtzc", "pgtcz", "pgtc", "zc"])
def test_combinations(
    tplan: Any,
    texpectation: Sequence[float],
    zplan: Any,
    zexpectation: Sequence[float],
    channel: Any,
    cexpectation: Sequence[float],
    order: str,
    position: Any,
    pexpectation: Sequence[float],
    tileplan: Any,
    tileexpectation: TilePosition,
) -> None:

    mda = MDASequence(
        z_plan=zplan,
        time_plan=tplan,
        channels=[channel],
        stage_positions=[position],
        tile_plan=tileplan,
        axis_order=order,
    )

    assert list(mda.z_plan) == zexpectation
    assert list(mda.time_plan) == texpectation
    assert (mda.channels[0].group, mda.channels[0].config) == cexpectation
    position = mda.stage_positions[0]
    assert (position.x, position.y, position.z) == pexpectation

    assert [i[1] for i in list(mda.tile_plan)] == tileexpectation

    assert list(mda)
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

    with pytest.raises(ValueError):
        mda.replace(axis_order="zptasdfs")
