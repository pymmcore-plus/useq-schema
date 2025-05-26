# pyright: reportArgumentType=false
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import TYPE_CHECKING, Any, Callable

import pytest

from useq import (
    AxesBasedAF,
    Channel,
    GridFromEdges,
    GridRowsColumns,
    HardwareAutofocus,
    MDAEvent,
    MDASequence,
    Position,
    TIntervalLoops,
    ZRangeAround,
    ZTopBottom,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True)
class MDATestCase:
    """A test case combining an MDASequence and expected attribute values.

    Parameters
    ----------
    name : str
        A short identifier used for the parametrised test id.
    seq : MDASequence
        The :class:`useq.MDASequence` under test.
    expected : dict[str, list[Any]] | list[MDAEvent] | None
        one of:
        - a dictionary mapping attribute names to a list of expected values, where
          the list length is equal to the number of events in the sequence.
        - a list of expected `useq.MDAEvent` objects, compared directly to the expanded
          sequence.
    predicate : Callable[[MDASequence], str] | None
        A callable that takes a `useq.MDASequence`.  If a non-empty string is returned,
        it is raised as an assertion error with the string as the message.
    """

    name: str
    seq: MDASequence
    expected: dict[str, list[Any]] | list[MDAEvent] | None = None
    predicate: Callable[[MDASequence], str | None] | None = None

    def __post_init__(self) -> None:
        if self.expected is None and self.predicate is None:
            raise ValueError("Either expected or predicate must be provided. ")


##############################################################################
# helpers
##############################################################################


def genindex(axes: dict[str, int]) -> list[dict[str, int]]:
    """Produce the cartesian product of `range(n)` for the given axes."""
    return [
        dict(zip(axes, prod)) for prod in product(*(range(v) for v in axes.values()))
    ]


##############################################################################
# test cases
##############################################################################

GRID_SUBSEQ_CASES: list[MDATestCase] = [
    MDATestCase(
        name="channel_only_in_position_sub_sequence",
        seq=MDASequence(
            stage_positions=[
                {},
                Position(
                    sequence=MDASequence(
                        channels=[Channel(config="FITC", exposure=100)]
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
        seq=MDASequence(
            stage_positions=[
                {},
                Position(
                    sequence=MDASequence(
                        channels=[Channel(config="FITC", exposure=100)]
                    )
                ),
            ],
            channels=[Channel(config="Cy5", exposure=50)],
        ),
        expected={
            "channel": ["Cy5", "FITC"],
            "index": [{"p": 0, "c": 0}, {"p": 1, "c": 0}],
            "exposure": [50.0, 100.0],
        },
    ),
    MDATestCase(
        name="subchannel_inherits_global_channel",
        seq=MDASequence(
            stage_positions=[
                {},
                {"sequence": {"z_plan": ZTopBottom(bottom=28, top=30, step=1)}},
            ],
            channels=[Channel(config="Cy5", exposure=50)],
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
        seq=MDASequence(
            stage_positions=[Position(x=0, y=0), (10, 20)],
            grid_plan=GridRowsColumns(rows=2, columns=2),
        ),
        expected={
            "index": genindex({"p": 2, "g": 4}),
            "x_pos": [-0.5, 0.5, 0.5, -0.5, 9.5, 10.5, 10.5, 9.5],
            "y_pos": [0.5, 0.5, -0.5, -0.5, 20.5, 20.5, 19.5, 19.5],
        },
    ),
    MDATestCase(
        name="grid_relative_only_in_position_sub_sequence",
        seq=MDASequence(
            stage_positions=[
                Position(x=0, y=0),
                Position(
                    x=10,
                    y=10,
                    sequence={
                        "grid_plan": GridRowsColumns(rows=2, columns=2),
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
        seq=MDASequence(
            stage_positions=[
                Position(x=0, y=0),
                Position(
                    x=10,
                    y=10,
                    sequence={
                        "grid_plan": GridFromEdges(top=1, bottom=-1, left=0, right=0)
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
        seq=MDASequence(
            stage_positions=[
                Position(x=0, y=0),
                Position(
                    name="name",
                    x=10,
                    y=10,
                    sequence={"grid_plan": GridRowsColumns(rows=2, columns=2)},
                ),
            ],
            grid_plan=GridRowsColumns(rows=2, columns=2),
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
        seq=MDASequence(
            stage_positions=[
                {},
                Position(
                    name="name",
                    sequence={
                        "grid_plan": GridFromEdges(top=2, bottom=-1, left=0, right=0)
                    },
                ),
            ],
            grid_plan=GridFromEdges(top=1, bottom=-1, left=0, right=0),
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
        seq=MDASequence(
            stage_positions=[
                {},
                Position(
                    name="name",
                    x=10,
                    y=10,
                    sequence={"grid_plan": GridRowsColumns(rows=2, columns=2)},
                ),
            ],
            grid_plan=GridFromEdges(top=1, bottom=-1, left=0, right=0),
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
        seq=MDASequence(
            stage_positions=[
                Position(x=0, y=0),
                Position(
                    name="name",
                    sequence={
                        "grid_plan": GridFromEdges(top=1, bottom=-1, left=0, right=0)
                    },
                ),
            ],
            grid_plan=GridRowsColumns(rows=2, columns=2),
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
        seq=MDASequence(
            stage_positions=[
                {"sequence": {"grid_plan": {"rows": 1, "columns": 2}}},
                {"sequence": {"grid_plan": GridRowsColumns(rows=2, columns=2)}},
                {
                    "sequence": {
                        "grid_plan": GridFromEdges(top=1, bottom=-1, left=0, right=0)
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
        seq=MDASequence(
            stage_positions=[(0, 0, 0), (10, 20, 10)],
            z_plan=ZRangeAround(range=2, step=1),
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
        seq=MDASequence(
            stage_positions=[Position(x=0, y=0), (10, 20)],
            z_plan=ZTopBottom(bottom=58, top=60, step=1),
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
        seq=MDASequence(
            stage_positions=[
                Position(z=0),
                Position(
                    name="name",
                    z=10,
                    sequence={"z_plan": ZRangeAround(range=2, step=1)},
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
        seq=MDASequence(
            stage_positions=[
                Position(z=0),
                Position(
                    name="name",
                    sequence={"z_plan": ZTopBottom(bottom=58, top=60, step=1)},
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
        seq=MDASequence(
            stage_positions=[
                Position(z=0),
                Position(
                    name="name",
                    z=10,
                    sequence={"z_plan": ZRangeAround(range=3, step=1)},
                ),
            ],
            z_plan=ZRangeAround(range=2, step=1),
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
        seq=MDASequence(
            stage_positions=[
                {},
                Position(
                    name="name",
                    sequence={"z_plan": ZTopBottom(bottom=28, top=30, step=1)},
                ),
            ],
            z_plan=ZTopBottom(bottom=58, top=60, step=1),
        ),
        expected={
            "index": genindex({"p": 2, "z": 3}),
            "pos_name": [None] * 3 + ["name"] * 3,
            "z_pos": [58.0, 59.0, 60.0, 28.0, 29.0, 30.0],
        },
    ),
    MDATestCase(
        name="z_absolute_in_main_and_z_relative_in_position_sub_sequence",
        seq=MDASequence(
            stage_positions=[
                {},
                Position(
                    name="name",
                    z=10,
                    sequence={"z_plan": ZRangeAround(range=3, step=1)},
                ),
            ],
            z_plan=ZTopBottom(bottom=58, top=60, step=1),
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
        seq=MDASequence(
            stage_positions=[
                Position(z=0),
                Position(
                    name="name",
                    sequence={"z_plan": ZTopBottom(bottom=58, top=60, step=1)},
                ),
            ],
            z_plan=ZRangeAround(range=3, step=1),
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
        seq=MDASequence(
            stage_positions=[
                {"sequence": {"z_plan": ZTopBottom(bottom=58, top=60, step=1)}},
                {"sequence": {"z_plan": ZRangeAround(range=3, step=1)}},
                {"sequence": {"z_plan": ZTopBottom(bottom=28, top=30, step=1)}},
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
        seq=MDASequence(
            stage_positions=[{}, {}],
            time_plan=[TIntervalLoops(interval=1, loops=2)],
        ),
        expected={
            "index": genindex({"t": 2, "p": 2}),
            "min_start_time": [0.0, 0.0, 1.0, 1.0],
        },
    ),
    MDATestCase(
        name="t_only_in_position_sub_sequence",
        seq=MDASequence(
            stage_positions=[
                {},
                {"sequence": {"time_plan": [TIntervalLoops(interval=1, loops=5)]}},
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
        seq=MDASequence(
            stage_positions=[
                {},
                {"sequence": {"time_plan": [TIntervalLoops(interval=1, loops=5)]}},
            ],
            time_plan=[TIntervalLoops(interval=1, loops=2)],
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
        seq=MDASequence(
            axis_order="tpgcz",
            stage_positions=[
                Position(x=0, y=0),
                Position(
                    name="name",
                    x=10,
                    y=10,
                    z=30,
                    sequence=MDASequence(
                        channels=[
                            {"config": "FITC", "exposure": 200},
                            {"config": "Cy3", "exposure": 100},
                        ],
                        grid_plan=GridRowsColumns(rows=2, columns=1),
                        z_plan=ZRangeAround(range=2, step=1),
                    ),
                ),
            ],
            channels=[Channel(config="Cy5", exposure=50)],
            z_plan={"top": 100, "bottom": 98, "step": 1},
            grid_plan=GridFromEdges(top=1, bottom=-1, left=0, right=0),
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
        seq=MDASequence(
            stage_positions=[
                Position(z=0),
                Position(
                    z=50,
                    sequence=MDASequence(
                        channels=[
                            Channel(config="FITC", exposure=100),
                            Channel(config="Cy3", exposure=200),
                        ]
                    ),
                ),
            ],
            channels=[
                Channel(config="FITC", exposure=100),
                Channel(config="Cy5", exposure=50),
            ],
            z_plan=ZRangeAround(range=2, step=1),
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
        seq=MDASequence(
            channels=[
                Channel(config="Cy5", exposure=50),
                Channel(config="FITC", exposure=100),
            ],
            stage_positions=[
                Position(
                    x=0,
                    y=0,
                    sequence=MDASequence(grid_plan=GridRowsColumns(rows=2, columns=1)),
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
        seq=MDASequence(
            channels=[
                Channel(config="Cy5", exposure=50),
                Channel(config="FITC", exposure=100),
            ],
            stage_positions=[
                Position(
                    x=0,
                    y=0,
                    z=0,
                    sequence={"z_plan": ZRangeAround(range=2, step=1)},
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
        seq=MDASequence(
            axis_order="tpgcz",
            channels=[
                Channel(config="Cy5", exposure=50),
                Channel(config="FITC", exposure=100),
            ],
            stage_positions=[
                Position(
                    x=0,
                    y=0,
                    sequence={"time_plan": [TIntervalLoops(interval=1, loops=3)]},
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
        seq=MDASequence(
            channels=[
                Channel(config="Cy5", exposure=50),
                Channel(config="FITC", exposure=100),
            ],
            stage_positions=[
                Position(
                    x=0,
                    y=0,
                    sequence=MDASequence(
                        grid_plan=GridRowsColumns(rows=2, columns=2),
                        z_plan=ZRangeAround(range=2, step=1),
                        time_plan=[TIntervalLoops(interval=1, loops=2)],
                    ),
                )
            ],
        ),
        expected={"channel": ["Cy5"] * 24 + ["FITC"] * 24},
    ),
    MDATestCase(
        name="sub_channels_and_any_plan",
        seq=MDASequence(
            channels=["Cy5", "FITC"],
            stage_positions=[
                Position(
                    sequence=MDASequence(
                        channels=["FITC"],
                        z_plan=ZRangeAround(range=2, step=1),
                    )
                )
            ],
        ),
        expected={"channel": ["FITC", "FITC", "FITC"]},
    ),
]

##############################################################################
# Autofocus Tests
##############################################################################


def ensure_af(
    expected_indices: Sequence[int] | None = None, expected_z: float | None = None
) -> Callable[[MDASequence], str | None]:
    """Test things about autofocus events.

    Parameters
    ----------
    expected_indices : Sequence[int] | None
        Ensure that the autofocus events are at these indices.
    expected_z : float | None
        Ensure that all autofocus events have this z position.
    """
    exp = list(expected_indices) if expected_indices else []

    def _pred(seq: MDASequence) -> str | None:
        errors: list[str] = []
        if exp:
            actual_indices = [
                i
                for i, ev in enumerate(seq)
                if isinstance(ev.action, HardwareAutofocus)
            ]
            if actual_indices != exp:
                errors.append(f"expected AF indices {exp}, got {actual_indices}")

        if expected_z is not None:
            z_vals = [
                ev.z_pos for ev in seq if isinstance(ev.action, HardwareAutofocus)
            ]
            if not all(z == expected_z for z in z_vals):
                errors.append(f"expected all AF events at z={expected_z}, got {z_vals}")
        if errors:
            return ", ".join(errors)
        return None

    return _pred


AF_CASES: list[MDATestCase] = [
    # 1. NO AXES - Should never trigger
    MDATestCase(
        name="af_no_axes_no_autofocus",
        seq=MDASequence(
            stage_positions=[Position(z=30)],
            z_plan=ZRangeAround(range=2, step=1),
            channels=["DAPI", "FITC"],
            autofocus_plan=AxesBasedAF(
                autofocus_device_name="Z", autofocus_motor_offset=40, axes=()
            ),
        ),
        predicate=ensure_af(expected_indices=[]),
    ),
    # 2. CHANNEL AXIS (c) - Triggers on channel changes
    MDATestCase(
        name="af_axes_c_basic",
        seq=MDASequence(
            stage_positions=[Position(z=30)],
            z_plan=ZRangeAround(range=2, step=1),
            channels=["DAPI", "FITC"],
            autofocus_plan=AxesBasedAF(autofocus_device_name="Z", axes=("c",)),
        ),
        predicate=ensure_af(expected_indices=[0, 4]),
    ),
    # 3. Z AXIS (z) - Triggers on z changes
    MDATestCase(
        name="af_axes_z_basic",
        seq=MDASequence(
            stage_positions=[Position(z=30)],
            z_plan=ZRangeAround(range=2, step=1),
            channels=["DAPI", "FITC"],
            autofocus_plan=AxesBasedAF(autofocus_device_name="Z", axes=("z",)),
        ),
        predicate=ensure_af(expected_indices=range(0, 11, 2)),
    ),
    # 4. GRID AXIS (g) - Triggers on grid position changes
    MDATestCase(
        name="af_axes_g_basic",
        seq=MDASequence(
            stage_positions=[Position(z=30)],
            channels=["DAPI", "FITC"],
            grid_plan=GridRowsColumns(rows=2, columns=1),
            autofocus_plan=AxesBasedAF(autofocus_device_name="Z", axes=("g",)),
        ),
        predicate=ensure_af(expected_indices=[0, 3]),
    ),
    # 5. POSITION AXIS (p) - Triggers on position changes
    MDATestCase(
        name="af_axes_p_basic",
        seq=MDASequence(
            stage_positions=[Position(z=30), Position(z=200)],
            channels=["DAPI", "FITC"],
            autofocus_plan=AxesBasedAF(autofocus_device_name="Z", axes=("p",)),
        ),
        predicate=ensure_af(expected_indices=[0, 3]),
    ),
    # 6. TIME AXIS (t) - Triggers on time changes
    MDATestCase(
        name="af_axes_t_basic",
        seq=MDASequence(
            stage_positions=[Position(z=30), Position(z=200)],
            channels=["DAPI", "FITC"],
            time_plan=[TIntervalLoops(interval=1, loops=2)],
            autofocus_plan=AxesBasedAF(autofocus_device_name="Z", axes=("t",)),
        ),
        predicate=ensure_af(expected_indices=[0, 5]),
    ),
    # 7. AXIS ORDER EFFECTS - Different axis order changes when axes trigger
    MDATestCase(
        name="af_axis_order_effect",
        seq=MDASequence(
            stage_positions=[Position(z=30)],
            z_plan=ZRangeAround(range=2, step=1),
            channels=["DAPI", "FITC"],
            axis_order="tpgzc",  # Different from default "tpczg"
            autofocus_plan=AxesBasedAF(autofocus_device_name="Z", axes=("z",)),
        ),
        predicate=ensure_af(expected_indices=[0, 3, 6]),
    ),
    # 8. SUBSEQUENCE AUTOFOCUS - AF plan within position subsequence
    MDATestCase(
        name="af_subsequence_af",
        seq=MDASequence(
            stage_positions=[
                Position(z=30),
                Position(
                    z=10,
                    sequence=MDASequence(
                        autofocus_plan=AxesBasedAF(
                            autofocus_device_name="Z",
                            axes=("c",),
                        )
                    ),
                ),
            ],
            channels=["DAPI", "FITC"],
        ),
        predicate=ensure_af(expected_indices=[2, 4]),
    ),
    # 9. MIXED MAIN + SUBSEQUENCE AF
    MDATestCase(
        name="af_mixed_main_and_sub",
        seq=MDASequence(
            stage_positions=[
                Position(z=30),
                Position(
                    z=10,
                    sequence=MDASequence(
                        autofocus_plan=AxesBasedAF(
                            autofocus_device_name="Z",
                            autofocus_motor_offset=40,
                            axes=("z",),
                        ),
                    ),
                ),
            ],
            channels=["DAPI", "FITC"],
            z_plan=ZRangeAround(range=2, step=1),
            autofocus_plan=AxesBasedAF(
                autofocus_device_name="Z", autofocus_motor_offset=40, axes=("p",)
            ),
        ),
        predicate=ensure_af(expected_indices=[0, *range(7, 18, 2)]),
    ),
    # 10. Z POSITION CORRECTION - AF events get correct z position with relative z plans
    MDATestCase(
        name="af_z_position_correction",
        seq=MDASequence(
            stage_positions=[Position(z=200)],
            channels=["DAPI", "FITC"],
            z_plan=ZRangeAround(range=2, step=1),
            autofocus_plan=AxesBasedAF(
                autofocus_device_name="Z", autofocus_motor_offset=40, axes=("c",)
            ),
        ),
        predicate=ensure_af(expected_z=200),
    ),
    # 11. SUBSEQUENCE Z POSITION CORRECTION
    MDATestCase(
        name="af_subsequence_z_position",
        seq=MDASequence(
            stage_positions=[
                Position(
                    z=10,
                    sequence=MDASequence(
                        autofocus_plan=AxesBasedAF(
                            autofocus_device_name="Z",
                            autofocus_motor_offset=40,
                            axes=("c",),
                        )
                    ),
                )
            ],
            channels=["DAPI", "FITC"],
            z_plan=ZRangeAround(range=2, step=1),
        ),
        predicate=ensure_af(expected_z=10),
    ),
    # 12. NO DEVICE NAME - Edge case for testing without device name
    MDATestCase(
        name="af_no_device_name",
        seq=MDASequence(
            time_plan=[TIntervalLoops(interval=1, loops=2)],
            autofocus_plan=AxesBasedAF(axes=("t",)),
        ),
        predicate=lambda _: "",  # Just check it doesn't crash
    ),
]

##############################################################################
# Keep Shutter Open Tests
###############################################################################


def ensure_shutter_behavior(
    expected_indices: Sequence[int] | bool | None = None,
) -> Callable[[MDASequence], str | None]:
    """Test keep_shutter_open behavior."""

    def _pred(seq: MDASequence) -> str | None:
        events = list(seq)
        errors: list[str] = []

        if expected_indices is not None:
            if expected_indices is True:
                if closed_events := [
                    i for i, e in enumerate(events) if not e.keep_shutter_open
                ]:
                    errors.append(
                        f"expected all shutters open, but events "
                        f"{closed_events} have keep_shutter_open=False"
                    )
            elif expected_indices is False:
                if open_events := [
                    i for i, e in enumerate(events) if e.keep_shutter_open
                ]:
                    errors.append(
                        f"expected all shutters closed, but events "
                        f"{open_events} have keep_shutter_open=True"
                    )
            else:
                actual_indices = [
                    i for i, e in enumerate(events) if e.keep_shutter_open
                ]
                if actual_indices != list(expected_indices):
                    errors.append(
                        f"expected shutter open at indices {expected_indices}, "
                        f"got {actual_indices}"
                    )

        if errors:
            return "; ".join(errors)
        return None

    return _pred


KEEP_SHUTTER_CASES: list[MDATestCase] = [
    # with z as the last axis, the shutter will be left open
    # whenever z is the first index (since there are only 2 z planes)
    MDATestCase(
        name="keep_shutter_open_across_z_order_tcz",
        seq=MDASequence(
            axis_order=tuple("tcz"),
            channels=["DAPI", "FITC"],
            time_plan=TIntervalLoops(loops=2, interval=0),
            z_plan=ZRangeAround(range=1, step=1),
            keep_shutter_open_across="z",
        ),
        predicate=ensure_shutter_behavior(expected_indices=[0, 2, 4, 6]),
    ),
    # with c as the last axis, the shutter will never be left open
    MDATestCase(
        name="keep_shutter_open_across_z_order_tzc",
        seq=MDASequence(
            axis_order=tuple("tzc"),
            channels=["DAPI", "FITC"],
            time_plan=TIntervalLoops(loops=2, interval=0),
            z_plan=ZRangeAround(range=1, step=1),
            keep_shutter_open_across="z",
        ),
        predicate=ensure_shutter_behavior(expected_indices=[]),
    ),
    # because t is changing faster than z, the shutter will never be left open
    MDATestCase(
        name="keep_shutter_open_across_z_order_czt",
        seq=MDASequence(
            axis_order=tuple("czt"),
            channels=["DAPI", "FITC"],
            time_plan=TIntervalLoops(loops=2, interval=0),
            z_plan=ZRangeAround(range=1, step=1),
            keep_shutter_open_across="z",
        ),
        predicate=ensure_shutter_behavior(expected_indices=[]),
    ),
    # but, if we include 't' in the keep_shutter_open_across,
    # it will be left open except when it's the last t and last z
    MDATestCase(
        name="keep_shutter_open_across_zt_order_czt",
        seq=MDASequence(
            axis_order=tuple("czt"),
            channels=["DAPI", "FITC"],
            time_plan=TIntervalLoops(loops=2, interval=0),
            z_plan=ZRangeAround(range=1, step=1),
            keep_shutter_open_across=("z", "t"),
        ),
        # for event in seq:
        #     is_last_zt = bool(event.index["t"] == 1 and event.index["z"] == 1)
        #     assert event.keep_shutter_open != is_last_zt
        predicate=ensure_shutter_behavior(expected_indices=[0, 1, 2, 4, 5, 6]),
    ),
    # even though c is the last axis, and comes after g, because the grid happens
    # on a subsequence shutter will be open across the grid for each position
    MDATestCase(
        name="keep_shutter_open_across_g_order_pgc_with_subseq",
        seq=MDASequence(
            axis_order=tuple("pgc"),
            channels=["DAPI", "FITC"],
            stage_positions=[
                Position(
                    sequence=MDASequence(grid_plan=GridRowsColumns(rows=2, columns=2))
                )
            ],
            keep_shutter_open_across="g",
        ),
        # for event in seq:
        #     assert event.keep_shutter_open != (event.index["g"] == 3)
        predicate=ensure_shutter_behavior(expected_indices=[0, 1, 2, 4, 5, 6]),
    ),
]

# ##############################################################################
# Reset Event Timer Test Cases
# ##############################################################################

RESET_EVENT_TIMER_CASES: list[MDATestCase] = [
    MDATestCase(
        name="reset_event_timer_with_time_intervals",
        seq=MDASequence(
            stage_positions=[(100, 100), (0, 0)],
            time_plan={"interval": 1, "loops": 2},
            axis_order=tuple("ptgcz"),
        ),
        expected={
            "reset_event_timer": [True, False, True, False],
        },
    ),
    MDATestCase(
        name="reset_event_timer_with_nested_position_sequences",
        seq=MDASequence(
            stage_positions=[
                Position(
                    x=0,
                    y=0,
                    sequence=MDASequence(
                        channels=["Cy5"], time_plan={"interval": 1, "loops": 2}
                    ),
                ),
                Position(
                    x=1,
                    y=1,
                    sequence=MDASequence(
                        channels=["DAPI"], time_plan={"interval": 1, "loops": 2}
                    ),
                ),
            ]
        ),
        expected={
            "reset_event_timer": [True, False, True, False],
        },
    ),
]

# ##############################################################################
# Combined Test Cases
# ##############################################################################

CASES: list[MDATestCase] = (
    GRID_SUBSEQ_CASES + AF_CASES + KEEP_SHUTTER_CASES + RESET_EVENT_TIMER_CASES
)

# assert that all test cases are unique
case_names = [case.name for case in CASES]
if duplicates := {name for name in case_names if case_names.count(name) > 1}:
    raise ValueError(
        f"Duplicate test case names found: {duplicates}. "
        "Please ensure all test cases have unique names."
    )


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_mda_sequence(case: MDATestCase) -> None:
    # test case expressed the expectation as a predicate
    if case.predicate is not None:
        # (a function that returns a non-empty error message if the test fails)
        if msg := case.predicate(case.seq):
            raise AssertionError(f"\nExpectation not met in '{case.name}':\n  {msg}\n")

    # test case expressed the expectation as a list of MDAEvent
    elif isinstance(case.expected, list):
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

    # test case expressed the expectation as a dict of {Event attr -> values list}
    else:
        assert isinstance(case.expected, dict), f"Invalid test case: {case.name!r}"
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
