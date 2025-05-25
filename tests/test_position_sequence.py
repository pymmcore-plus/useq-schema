# pyright: reportArgumentType=false
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import TYPE_CHECKING, Any

import pytest

import useq

if TYPE_CHECKING:
    from useq._mda_event import MDAEvent

##############################################################################
# helpers
##############################################################################


def genindex(axes: dict[str, int]) -> list[dict[str, int]]:
    """Produce the cartesian product of `range(n)` for the given axes."""
    return [
        dict(zip(axes, prod)) for prod in product(*(range(v) for v in axes.values()))
    ]


@dataclass(slots=True, frozen=True)
class MDATestCase:
    """A test case combining an MDASequence and expected attribute values.

    Parameters
    ----------
    name:
        A short identifier used for the parametrised test id.
    seq:
        The :class:`useq.MDASequence` under test.
    expected:
        A mapping whose keys are `useq.MDAEvent` attribute names,
        and whose values are the *ordered* list of expected attribute
        values when ``seq`` is iterated.  Only the attributes present in this
        mapping are checked.
    """

    name: str
    seq: useq.MDASequence
    expected: dict[str, list[Any]] | list[MDAEvent]


##############################################################################
# test cases
##############################################################################

CASES: list[MDATestCase] = [
    MDATestCase(
        name="channel_only_in_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                {},
                useq.AbsolutePosition(
                    sequence=useq.MDASequence(
                        channels=[useq.Channel(config="FITC", exposure=100)]
                    )
                ),
            ]
        ),
        expected={
            "channel": [None, "FITC"],
            "index": [{"p": 0}, {"p": 1, "c": 0}],
            "exposure": [None, 100.0],
        },
    ),
    MDATestCase(
        name="channel_in_main_and_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                {},
                useq.AbsolutePosition(
                    sequence=useq.MDASequence(
                        channels=[useq.Channel(config="FITC", exposure=100)]
                    )
                ),
            ],
            channels=[useq.Channel(config="Cy5", exposure=50)],
        ),
        expected={
            "channel": ["Cy5", "FITC"],
            "index": [{"p": 0, "c": 0}, {"p": 1, "c": 0}],
            "exposure": [50.0, 100.0],
        },
    ),
    MDATestCase(
        name="subchannel_inherits_global_channel",
        seq=useq.MDASequence(
            stage_positions=[
                {},
                {"sequence": {"z_plan": useq.ZTopBottom(bottom=28, top=30, step=1)}},
            ],
            channels=[useq.Channel(config="Cy5", exposure=50)],
        ),
        expected={
            "channel": ["Cy5"] * 4,
            "index": [
                {"p": 0, "c": 0},
                {"p": 1, "z": 0, "c": 0},
                {"p": 1, "z": 1, "c": 0},
                {"p": 1, "z": 2, "c": 0},
            ],
        },
    ),
    MDATestCase(
        name="grid_relative_with_multi_stage_positions",
        seq=useq.MDASequence(
            stage_positions=[useq.AbsolutePosition(x=0, y=0), (10, 20)],
            grid_plan=useq.GridRelative(rows=2, columns=2),
        ),
        expected={
            "index": genindex({"p": 2, "g": 4}),
            "x_pos": [-0.5, 0.5, 0.5, -0.5, 9.5, 10.5, 10.5, 9.5],
            "y_pos": [0.5, 0.5, -0.5, -0.5, 20.5, 20.5, 19.5, 19.5],
        },
    ),
    MDATestCase(
        name="grid_relative_only_in_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                useq.AbsolutePosition(x=0, y=0),
                useq.AbsolutePosition(
                    x=10,
                    y=10,
                    sequence={
                        "grid_plan": useq.GridRelative(rows=2, columns=2),
                    },
                ),
            ]
        ),
        expected={
            "index": [
                {"p": 0},
                {"p": 1, "g": 0},
                {"p": 1, "g": 1},
                {"p": 1, "g": 2},
                {"p": 1, "g": 3},
            ],
            "x_pos": [0.0, 9.5, 10.5, 10.5, 9.5],
            "y_pos": [0.0, 10.5, 10.5, 9.5, 9.5],
        },
    ),
    MDATestCase(
        name="grid_absolute_only_in_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                useq.AbsolutePosition(x=0, y=0),
                useq.AbsolutePosition(
                    x=10,
                    y=10,
                    sequence={
                        "grid_plan": useq.GridFromEdges(
                            top=1, bottom=-1, left=0, right=0
                        )
                    },
                ),
            ]
        ),
        expected={
            "index": [
                {"p": 0},
                {"p": 1, "g": 0},
                {"p": 1, "g": 1},
                {"p": 1, "g": 2},
            ],
            "x_pos": [0.0, 0.0, 0.0, 0.0],
            "y_pos": [0.0, 1.0, 0.0, -1.0],
        },
    ),
    MDATestCase(
        name="grid_relative_in_main_and_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                useq.AbsolutePosition(x=0, y=0),
                useq.AbsolutePosition(
                    name="name",
                    x=10,
                    y=10,
                    sequence={"grid_plan": useq.GridRelative(rows=2, columns=2)},
                ),
            ],
            grid_plan=useq.GridRelative(rows=2, columns=2),
        ),
        expected={
            "index": genindex({"p": 2, "g": 4}),
            "pos_name": [None] * 4 + ["name"] * 4,
            "x_pos": [-0.5, 0.5, 0.5, -0.5, 9.5, 10.5, 10.5, 9.5],
            "y_pos": [0.5, 0.5, -0.5, -0.5, 10.5, 10.5, 9.5, 9.5],
        },
    ),
    MDATestCase(
        name="grid_absolute_in_main_and_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                {},
                useq.AbsolutePosition(
                    name="name",
                    sequence={
                        "grid_plan": useq.GridFromEdges(
                            top=2, bottom=-1, left=0, right=0
                        )
                    },
                ),
            ],
            grid_plan=useq.GridFromEdges(top=1, bottom=-1, left=0, right=0),
        ),
        expected={
            "index": [
                {"p": 0, "g": 0},
                {"p": 0, "g": 1},
                {"p": 0, "g": 2},
                {"p": 1, "g": 0},
                {"p": 1, "g": 1},
                {"p": 1, "g": 2},
                {"p": 1, "g": 3},
            ],
            "pos_name": [None] * 3 + ["name"] * 4,
            "x_pos": [0.0] * 7,
            "y_pos": [1.0, 0.0, -1.0, 2.0, 1.0, 0.0, -1.0],
        },
    ),
    MDATestCase(
        name="grid_absolute_in_main_and_grid_relative_in_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                {},
                useq.AbsolutePosition(
                    name="name",
                    x=10,
                    y=10,
                    sequence={"grid_plan": useq.GridRelative(rows=2, columns=2)},
                ),
            ],
            grid_plan=useq.GridFromEdges(top=1, bottom=-1, left=0, right=0),
        ),
        expected={
            "index": [
                {"p": 0, "g": 0},
                {"p": 0, "g": 1},
                {"p": 0, "g": 2},
                {"p": 1, "g": 0},
                {"p": 1, "g": 1},
                {"p": 1, "g": 2},
                {"p": 1, "g": 3},
            ],
            "pos_name": [None] * 3 + ["name"] * 4,
            "x_pos": [0.0, 0.0, 0.0, 9.5, 10.5, 10.5, 9.5],
            "y_pos": [1.0, 0.0, -1.0, 10.5, 10.5, 9.5, 9.5],
        },
    ),
    MDATestCase(
        name="grid_relative_in_main_and_grid_absolute_in_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                useq.AbsolutePosition(x=0, y=0),
                useq.AbsolutePosition(
                    name="name",
                    sequence={
                        "grid_plan": useq.GridFromEdges(
                            top=1, bottom=-1, left=0, right=0
                        )
                    },
                ),
            ],
            grid_plan=useq.GridRelative(rows=2, columns=2),
        ),
        expected={
            "index": [
                {"p": 0, "g": 0},
                {"p": 0, "g": 1},
                {"p": 0, "g": 2},
                {"p": 0, "g": 3},
                {"p": 1, "g": 0},
                {"p": 1, "g": 1},
                {"p": 1, "g": 2},
            ],
            "pos_name": [None] * 4 + ["name"] * 3,
            "x_pos": [-0.5, 0.5, 0.5, -0.5, 0.0, 0.0, 0.0],
            "y_pos": [0.5, 0.5, -0.5, -0.5, 1.0, 0.0, -1.0],
        },
    ),
    MDATestCase(
        name="multi_g_in_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                {"sequence": {"grid_plan": {"rows": 1, "columns": 2}}},
                {"sequence": {"grid_plan": useq.GridRelative(rows=2, columns=2)}},
                {
                    "sequence": {
                        "grid_plan": useq.GridFromEdges(
                            top=1, bottom=-1, left=0, right=0
                        )
                    }
                },
            ]
        ),
        expected={
            "index": [
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
            "x_pos": [-0.5, 0.5, -0.5, 0.5, 0.5, -0.5, 0.0, 0.0, 0.0],
            "y_pos": [0.0, 0.0, 0.5, 0.5, -0.5, -0.5, 1.0, 0.0, -1.0],
        },
    ),
    MDATestCase(
        name="z_relative_with_multi_stage_positions",
        seq=useq.MDASequence(
            stage_positions=[(0, 0, 0), (10, 20, 10)],
            z_plan=useq.ZRangeAround(range=2, step=1),
        ),
        expected={
            "index": genindex({"p": 2, "z": 3}),
            "x_pos": [0.0, 0.0, 0.0, 10.0, 10.0, 10.0],
            "y_pos": [0.0, 0.0, 0.0, 20.0, 20.0, 20.0],
            "z_pos": [-1.0, 0.0, 1.0, 9.0, 10.0, 11.0],
        },
    ),
    MDATestCase(
        name="z_absolute_with_multi_stage_positions",
        seq=useq.MDASequence(
            stage_positions=[useq.AbsolutePosition(x=0, y=0), (10, 20)],
            z_plan=useq.ZTopBottom(bottom=58, top=60, step=1),
        ),
        expected={
            "index": genindex({"p": 2, "z": 3}),
            "x_pos": [0.0, 0.0, 0.0, 10.0, 10.0, 10.0],
            "y_pos": [0.0, 0.0, 0.0, 20.0, 20.0, 20.0],
            "z_pos": [58.0, 59.0, 60.0, 58.0, 59.0, 60.0],
        },
    ),
    MDATestCase(
        name="z_relative_only_in_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                useq.AbsolutePosition(z=0),
                useq.AbsolutePosition(
                    name="name",
                    z=10,
                    sequence={"z_plan": useq.ZRangeAround(range=2, step=1)},
                ),
            ]
        ),
        expected={
            "index": [
                {"p": 0},
                {"p": 1, "z": 0},
                {"p": 1, "z": 1},
                {"p": 1, "z": 2},
            ],
            "pos_name": [None, "name", "name", "name"],
            "z_pos": [0.0, 9.0, 10.0, 11.0],
        },
    ),
    MDATestCase(
        name="z_absolute_only_in_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                useq.AbsolutePosition(z=0),
                useq.AbsolutePosition(
                    name="name",
                    sequence={"z_plan": useq.ZTopBottom(bottom=58, top=60, step=1)},
                ),
            ]
        ),
        expected={
            "index": [
                {"p": 0},
                {"p": 1, "z": 0},
                {"p": 1, "z": 1},
                {"p": 1, "z": 2},
            ],
            "pos_name": [None, "name", "name", "name"],
            "z_pos": [0.0, 58.0, 59.0, 60.0],
        },
    ),
    MDATestCase(
        name="z_relative_in_main_and_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                useq.AbsolutePosition(z=0),
                useq.AbsolutePosition(
                    name="name",
                    z=10,
                    sequence={"z_plan": useq.ZRangeAround(range=3, step=1)},
                ),
            ],
            z_plan=useq.ZRangeAround(range=2, step=1),
        ),
        expected={
            # pop the 3rd index
            "index": (idx := genindex({"p": 2, "z": 4}))[:3] + idx[4:],
            "pos_name": [None] * 3 + ["name"] * 4,
            "z_pos": [-1.0, 0.0, 1.0, 8.5, 9.5, 10.5, 11.5],
        },
    ),
    MDATestCase(
        name="z_absolute_in_main_and_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                {},
                useq.AbsolutePosition(
                    name="name",
                    sequence={"z_plan": useq.ZTopBottom(bottom=28, top=30, step=1)},
                ),
            ],
            z_plan=useq.ZTopBottom(bottom=58, top=60, step=1),
        ),
        expected={
            "index": genindex({"p": 2, "z": 3}),
            "pos_name": [None] * 3 + ["name"] * 3,
            "z_pos": [58.0, 59.0, 60.0, 28.0, 29.0, 30.0],
        },
    ),
    MDATestCase(
        name="z_absolute_in_main_and_z_relative_in_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                {},
                useq.AbsolutePosition(
                    name="name",
                    z=10,
                    sequence={"z_plan": useq.ZRangeAround(range=3, step=1)},
                ),
            ],
            z_plan=useq.ZTopBottom(bottom=58, top=60, step=1),
        ),
        expected={
            "index": [
                {"p": 0, "z": 0},
                {"p": 0, "z": 1},
                {"p": 0, "z": 2},
                {"p": 1, "z": 0},
                {"p": 1, "z": 1},
                {"p": 1, "z": 2},
                {"p": 1, "z": 3},
            ],
            "pos_name": [None] * 3 + ["name"] * 4,
            "z_pos": [58.0, 59.0, 60.0, 8.5, 9.5, 10.5, 11.5],
        },
    ),
    MDATestCase(
        name="z_relative_in_main_and_z_absolute_in_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                useq.AbsolutePosition(z=0),
                useq.AbsolutePosition(
                    name="name",
                    sequence={"z_plan": useq.ZTopBottom(bottom=58, top=60, step=1)},
                ),
            ],
            z_plan=useq.ZRangeAround(range=3, step=1),
        ),
        expected={
            "index": [
                {"p": 0, "z": 0},
                {"p": 0, "z": 1},
                {"p": 0, "z": 2},
                {"p": 0, "z": 3},
                {"p": 1, "z": 0},
                {"p": 1, "z": 1},
                {"p": 1, "z": 2},
            ],
            "pos_name": [None] * 4 + ["name"] * 3,
            "z_pos": [-1.5, -0.5, 0.5, 1.5, 58.0, 59.0, 60.0],
        },
    ),
    MDATestCase(
        name="multi_z_in_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                {"sequence": {"z_plan": useq.ZTopBottom(bottom=58, top=60, step=1)}},
                {"sequence": {"z_plan": useq.ZRangeAround(range=3, step=1)}},
                {"sequence": {"z_plan": useq.ZTopBottom(bottom=28, top=30, step=1)}},
            ]
        ),
        expected={
            "index": [
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
            "z_pos": [
                58.0,
                59.0,
                60.0,
                -1.5,
                -0.5,
                0.5,
                1.5,
                28.0,
                29.0,
                30.0,
            ],
        },
    ),
    MDATestCase(
        name="t_with_multi_stage_positions",
        seq=useq.MDASequence(
            stage_positions=[{}, {}],
            time_plan=[useq.TIntervalLoops(interval=1, loops=2)],
        ),
        expected={
            "index": genindex({"t": 2, "p": 2}),
            "min_start_time": [0.0, 0.0, 1.0, 1.0],
        },
    ),
    MDATestCase(
        name="t_only_in_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                {},
                {"sequence": {"time_plan": [useq.TIntervalLoops(interval=1, loops=5)]}},
            ]
        ),
        expected={
            "index": [
                {"p": 0},
                {"p": 1, "t": 0},
                {"p": 1, "t": 1},
                {"p": 1, "t": 2},
                {"p": 1, "t": 3},
                {"p": 1, "t": 4},
            ],
            "min_start_time": [None, 0.0, 1.0, 2.0, 3.0, 4.0],
        },
    ),
    MDATestCase(
        name="t_in_main_and_in_position_sub_sequence",
        seq=useq.MDASequence(
            stage_positions=[
                {},
                {"sequence": {"time_plan": [useq.TIntervalLoops(interval=1, loops=5)]}},
            ],
            time_plan=[useq.TIntervalLoops(interval=1, loops=2)],
        ),
        expected={
            "index": [
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
            "min_start_time": [
                0.0,
                0.0,
                1.0,
                2.0,
                3.0,
                4.0,
                1.0,
                0.0,
                1.0,
                2.0,
                3.0,
                4.0,
            ],
        },
    ),
    MDATestCase(
        name="mix_cgz_axes",
        seq=useq.MDASequence(
            axis_order="tpgcz",
            stage_positions=[
                useq.AbsolutePosition(x=0, y=0),
                useq.AbsolutePosition(
                    name="name",
                    x=10,
                    y=10,
                    z=30,
                    sequence=useq.MDASequence(
                        channels=[
                            {"config": "FITC", "exposure": 200},
                            {"config": "Cy3", "exposure": 100},
                        ],
                        grid_plan=useq.GridRelative(rows=2, columns=1),
                        z_plan=useq.ZRangeAround(range=2, step=1),
                    ),
                ),
            ],
            channels=[useq.Channel(config="Cy5", exposure=50)],
            z_plan={"top": 100, "bottom": 98, "step": 1},
            grid_plan=useq.GridFromEdges(top=1, bottom=-1, left=0, right=0),
        ),
        expected={
            "index": [
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
            "pos_name": [None] * 9 + ["name"] * 12,
            "x_pos": [0.0] * 9 + [10.0] * 12,
            "y_pos": [1, 1, 1, 0, 0, 0, -1, -1, -1] + [10.5] * 6 + [9.5] * 6,
            "z_pos": [98.0, 99.0, 100.0] * 3 + [29.0, 30.0, 31.0] * 4,
            "channel": ["Cy5"] * 9 + (["FITC"] * 3 + ["Cy3"] * 3) * 2,
            "exposure": [50.0] * 9 + [200.0, 200.0, 200.0, 100.0, 100.0, 100.0] * 2,
        },
    ),
    MDATestCase(
        name="order",
        seq=useq.MDASequence(
            stage_positions=[
                useq.AbsolutePosition(z=0),
                useq.AbsolutePosition(
                    z=50,
                    sequence=useq.MDASequence(
                        channels=[
                            useq.Channel(config="FITC", exposure=100),
                            useq.Channel(config="Cy3", exposure=200),
                        ]
                    ),
                ),
            ],
            channels=[
                useq.Channel(config="FITC", exposure=100),
                useq.Channel(config="Cy5", exposure=50),
            ],
            z_plan=useq.ZRangeAround(range=2, step=1),
        ),
        expected={
            "index": [
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
            ],
            "z_pos": [
                -1.0,
                0.0,
                1.0,
                -1.0,
                0.0,
                1.0,
                49.0,
                49.0,
                50.0,
                50.0,
                51.0,
                51.0,
            ],
            "channel": ["FITC"] * 3 + ["Cy5"] * 3 + ["FITC", "Cy3"] * 3,
        },
    ),
    MDATestCase(
        name="channels_and_pos_grid_plan",
        seq=useq.MDASequence(
            channels=[
                useq.Channel(config="Cy5", exposure=50),
                useq.Channel(config="FITC", exposure=100),
            ],
            stage_positions=[
                useq.AbsolutePosition(
                    x=0,
                    y=0,
                    sequence=useq.MDASequence(
                        grid_plan=useq.GridRelative(rows=2, columns=1)
                    ),
                )
            ],
        ),
        expected={
            "index": genindex({"p": 1, "c": 2, "g": 2}),
            "x_pos": [0.0, 0.0, 0.0, 0.0],
            "y_pos": [0.5, -0.5, 0.5, -0.5],
            "channel": ["Cy5", "Cy5", "FITC", "FITC"],
        },
    ),
    MDATestCase(
        name="channels_and_pos_z_plan",
        seq=useq.MDASequence(
            channels=[
                useq.Channel(config="Cy5", exposure=50),
                useq.Channel(config="FITC", exposure=100),
            ],
            stage_positions=[
                useq.AbsolutePosition(
                    x=0,
                    y=0,
                    z=0,
                    sequence={"z_plan": useq.ZRangeAround(range=2, step=1)},
                )
            ],
        ),
        expected={
            "index": genindex({"p": 1, "c": 2, "z": 3}),
            "z_pos": [-1.0, 0.0, 1.0, -1.0, 0.0, 1.0],
            "channel": ["Cy5", "Cy5", "Cy5", "FITC", "FITC", "FITC"],
        },
    ),
    MDATestCase(
        name="channels_and_pos_time_plan",
        seq=useq.MDASequence(
            axis_order="tpgcz",
            channels=[
                useq.Channel(config="Cy5", exposure=50),
                useq.Channel(config="FITC", exposure=100),
            ],
            stage_positions=[
                useq.AbsolutePosition(
                    x=0,
                    y=0,
                    sequence={"time_plan": [useq.TIntervalLoops(interval=1, loops=3)]},
                )
            ],
        ),
        expected={
            "index": genindex({"p": 1, "c": 2, "t": 3}),
            "min_start_time": [0.0, 1.0, 2.0, 0.0, 1.0, 2.0],
            "channel": ["Cy5", "Cy5", "Cy5", "FITC", "FITC", "FITC"],
        },
    ),
    MDATestCase(
        name="channels_and_pos_z_grid_and_time_plan",
        seq=useq.MDASequence(
            channels=[
                useq.Channel(config="Cy5", exposure=50),
                useq.Channel(config="FITC", exposure=100),
            ],
            stage_positions=[
                useq.AbsolutePosition(
                    x=0,
                    y=0,
                    sequence=useq.MDASequence(
                        grid_plan=useq.GridRelative(rows=2, columns=2),
                        z_plan=useq.ZRangeAround(range=2, step=1),
                        time_plan=[useq.TIntervalLoops(interval=1, loops=2)],
                    ),
                )
            ],
        ),
        expected={"channel": ["Cy5"] * 24 + ["FITC"] * 24},
    ),
    MDATestCase(
        name="sub_channels_and_any_plan",
        seq=useq.MDASequence(
            channels=["Cy5", "FITC"],
            stage_positions=[
                useq.AbsolutePosition(
                    sequence=useq.MDASequence(
                        channels=["FITC"],
                        z_plan=useq.ZRangeAround(range=2, step=1),
                    )
                )
            ],
        ),
        expected={"channel": ["FITC", "FITC", "FITC"]},
    ),
]


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_mda_sequence(case: MDATestCase) -> None:
    if isinstance(case.expected, list):
        # test case expressed the expectation as a list of MDAEvent
        actual_events = list(case.seq)
        if len(actual_events) != len(case.expected):
            raise AssertionError(
                f"\nMismatch in case '{case.name}':\n"
                f"  expected: {len(case.expected)} events\n"
                f"    actual: {len(actual_events)} events\n"
            )
        for i, event in enumerate(actual_events):
            if event != case.expected[i]:
                raise AssertionError(
                    f"\nMismatch in case '{case.name}':\n"
                    f"  expected: {case.expected[i]}\n"
                    f"    actual: {event}\n"
                )

    if isinstance(case.expected, dict):
        # test case expressed the expectation as a dict of {Event attr -> values list}
        actual: dict[str, list[Any]] = {k: [] for k in case.expected}
        for event in case.seq:
            for attr in case.expected:
                actual[attr].append(getattr(event, attr))

        if mismatched_fields := {
            attr for attr in actual if actual[attr] != case.expected[attr]
        }:
            msg = f"\nMismatch in case '{case.name}':\n"
            for attr in mismatched_fields:
                msg += f"  {attr}:\n"
                msg += f"    expected: {case.expected[attr]}\n"
                msg += f"      actual: {actual[attr]}\n"
            raise AssertionError(msg)
