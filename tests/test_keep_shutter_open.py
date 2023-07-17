from __future__ import annotations

from typing import Iterable

import pytest

import useq
from useq import AxesBasedAF, MDASequence, ShutterOpenAxes

ZRANGE2 = useq.ZRangeAround(range=2, step=1)
ZPOS_30 = useq.Position(z=30.0)
ZPOS_200 = useq.Position(z=200.0)
GRID_PLAN = useq.GridRelative(rows=2, columns=1)
TWO_CH = MDASequence(stage_positions=[ZPOS_30], channels=["DAPI", "FITC"])
TWO_CH_TWO_P = TWO_CH.replace(stage_positions=[ZPOS_30, ZPOS_200])
TWO_CH_TWO_P_GRID = TWO_CH_TWO_P.replace(grid_plan=GRID_PLAN)
TWO_CH_TWO_P_T = TWO_CH_TWO_P.replace(time_plan={"interval": 1, "loops": 2})
NO_CH_ZSTACK = MDASequence(stage_positions=[ZPOS_30], z_plan=ZRANGE2)
TWO_CH_ZSTACK = NO_CH_ZSTACK.replace(channels=["DAPI", "FITC"])
AF = AxesBasedAF(autofocus_device_name="Z", autofocus_motor_offset=40, axes=())
AF_C = AF.copy(update={"axes": ("c",)})
AF_G = AF.copy(update={"axes": ("g",)})
AF_P = AF.copy(update={"axes": ("p",)})
AF_Z = AF.copy(update={"axes": ("z",)})
AF_SEQ_C = MDASequence(autofocus_plan=AF_C)
SUB_P_AF_C = useq.Position(z=10, sequence=AF_SEQ_C)
SUB_P_AF_G = useq.Position(z=10, sequence=MDASequence(autofocus_plan=AF_G))
SUB_P_AF_P = useq.Position(z=10, sequence=MDASequence(autofocus_plan=AF_P))
SUB_P_AF_Z = useq.Position(z=10, sequence=MDASequence(autofocus_plan=AF_Z))
TWO_CH_SUBPAF_C = TWO_CH.replace(stage_positions=[ZPOS_30, SUB_P_AF_C])
TWO_CH_SUBPAF_Z = TWO_CH.replace(stage_positions=[ZPOS_30, SUB_P_AF_Z])

# fmt: off
SH_TESTS: list[tuple[MDASequence, tuple[str, ...], Iterable[int]]] = [
    (NO_CH_ZSTACK, ("c",), ("c",), ()),
    (TWO_CH_ZSTACK, ("c",), ("c",), (0, 1, 4, 5)),
    (TWO_CH_ZSTACK, ("z",), ("c",), (0, 1, 6, 7)),
    (TWO_CH_ZSTACK, ("z",), ("z",), range(12)),
    (TWO_CH_ZSTACK.replace(axis_order="tpgzc"), ("c",), ("c",), range(12)),
    (TWO_CH_ZSTACK.replace(axis_order="tpgzc"), ("c",), ("z",), (0, 1, 4, 5, 8, 9)),
    (TWO_CH_ZSTACK.replace(axis_order="tpgzc"), ("z",), ("c",), range(9)),
    (TWO_CH.replace(grid_plan=GRID_PLAN), ("g",), ("c",), range(6)),
    (TWO_CH.replace(grid_plan=GRID_PLAN, axis_order="tpcgz"), ("g",), ("c",), (0, 1, 4, 5)),
    (TWO_CH_TWO_P, ("g",), ("c",), range(4)),
    (TWO_CH_TWO_P_GRID, ("g",), ("c",), range(12)),
    (TWO_CH_TWO_P_GRID.replace(axis_order="tpcgz"), ("g",), ("c",), (0, 1, 4, 5, 8, 9, 12, 13)),
    (TWO_CH_TWO_P_GRID, ("p",), ("c", ), range(10)),
    (TWO_CH_TWO_P_T, ("t",), ("c",), range(10)),
    (TWO_CH_SUBPAF_C, (), ("c",), range(6)),
    (TWO_CH.replace(stage_positions=[ZPOS_30, SUB_P_AF_G]), (), ("c",), range(4)),
    (TWO_CH.replace(stage_positions=[ZPOS_30, SUB_P_AF_G], grid_plan=GRID_PLAN), (), ("c",), range(10)),
    (TWO_CH_SUBPAF_C.replace(grid_plan=GRID_PLAN), (), ("c",), range(12)),
    (TWO_CH_SUBPAF_C.replace(z_plan=ZRANGE2), (), ("c",), (0, 3, 6, 7, 10, 11)),
    (TWO_CH_SUBPAF_C.replace(z_plan=ZRANGE2), (), ("z",), range(14)),
    (TWO_CH_SUBPAF_C.replace(z_plan=ZRANGE2, axis_order="tpgzc"), (), ("z",), (0, 2, 4, 6, 7, 10, 11, 14, 15)),
    (TWO_CH_SUBPAF_C.replace(z_plan=ZRANGE2, axis_order="tpgzc"), (), ("c", "z",), range(18)),
    (TWO_CH_SUBPAF_Z.replace(z_plan=ZRANGE2), (), ("c",), (0, 3, 6, 7, 12, 13)),
    (TWO_CH_SUBPAF_Z.replace(z_plan=ZRANGE2), ("p",), ("c",), (0, 1, 4, 7, 8, 13, 14)),
    (TWO_CH_SUBPAF_C.replace(z_plan=ZRANGE2, grid_plan=GRID_PLAN), ("c",), ("c",), (tuple(x for x in range(30) if x % 4 < 2))),
    (TWO_CH.replace(stage_positions=[ZPOS_30, useq.Position(z=10, sequence=MDASequence(autofocus_plan=AF_C, grid_plan=GRID_PLAN))]), (), ("c",), (0, 1, 2, 3, 5, 6)),
    (TWO_CH.replace(stage_positions=[SUB_P_AF_C, useq.Position(z=10, sequence=MDASequence(autofocus_plan=AF_G, grid_plan=GRID_PLAN))]), (), ("c",), (0, 1, 2, 3, 4, 5, 8, 9)),
    (TWO_CH.replace(stage_positions=[SUB_P_AF_C, useq.Position(z=10, sequence=MDASequence(autofocus_plan=AF_G, grid_plan=GRID_PLAN, shutter_plan=ShutterOpenAxes(axes=("c",))))]), (), (), (4, 5, 8, 9)),
    (TWO_CH.replace(stage_positions=[SUB_P_AF_C, useq.Position(z=10, sequence=MDASequence(autofocus_plan=AF_G, z_plan=ZRANGE2, shutter_plan=ShutterOpenAxes(axes=("c",))))]), (), (), (4, 7)),
    (TWO_CH.replace(stage_positions=[SUB_P_AF_C, useq.Position(z=10, sequence=MDASequence(autofocus_plan=AF_G, z_plan=ZRANGE2, shutter_plan=ShutterOpenAxes(axes=("z",))))]), (), ("c",), range(10)),
    (TWO_CH.replace(stage_positions=[ZPOS_200, useq.Position(z=10, sequence=MDASequence(autofocus_plan=AF_G, shutter_plan=ShutterOpenAxes(axes=("c",))))]), (), (), (2, 3)),
    (TWO_CH.replace(stage_positions=[SUB_P_AF_C, useq.Position(z=10, sequence=MDASequence(autofocus_plan=AF_G, shutter_plan=ShutterOpenAxes(axes=("c",))))]), (), (), (4, 5)),
    (TWO_CH.replace(stage_positions=[ZPOS_200, useq.Position(z=10, sequence=MDASequence(autofocus_plan=AF_G, z_plan=ZRANGE2, shutter_plan=ShutterOpenAxes(axes=("z",))))]), (), ("c",), range(8)),
    (TWO_CH.replace(stage_positions=[ZPOS_200, useq.Position(z=10, sequence=MDASequence(autofocus_plan=AF_G, z_plan=ZRANGE2))]), (), ("z",), range(2, 8)),
]

@pytest.mark.parametrize("mda, af_axes, sh_axes, expected_shutter_indices", SH_TESTS)
def test_kso(
    mda: MDASequence,
    af_axes: tuple[str, ...],
    sh_axes: tuple[str, ...],
    expected_shutter_indices: Iterable[int],
) -> None:
    if af_axes:
        mda = mda.replace(autofocus_plan=AF.copy(update={"axes": af_axes}))
        assert isinstance(mda.autofocus_plan, AxesBasedAF)
        assert mda.autofocus_plan.axes == af_axes
    if sh_axes:
        mda = mda.replace(shutter_plan=ShutterOpenAxes(axes=sh_axes))
        assert mda.shutter_plan == ShutterOpenAxes(axes=sh_axes)

    actual = [i for i, e in enumerate(mda) if e.keep_shutter_open]
    expected = list(expected_shutter_indices)
    if expected != actual:
        raise AssertionError(f"Expected AF indices at {expected} but got {actual}")
