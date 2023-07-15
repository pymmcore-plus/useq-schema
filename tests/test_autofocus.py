from __future__ import annotations

from typing import Iterable

import pytest

import useq
from useq import AxesBasedAF, HardwareAutofocus, MDASequence

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

AF_TESTS: list[tuple[MDASequence, tuple[str, ...], Iterable[int]]] = [
    (NO_CH_ZSTACK, ("c",), ()),
    (TWO_CH_ZSTACK, ("c",), (0, 4)),
    (TWO_CH_ZSTACK, ("z",), range(0, 11, 2)),
    (TWO_CH_ZSTACK.replace(axis_order="tpgzc"), ("c",), range(0, 11, 2)),
    (TWO_CH_ZSTACK.replace(axis_order="tpgzc"), ("z",), (0, 3, 6)),
    (TWO_CH_ZSTACK, ("z",), range(0, 11, 2)),
    (TWO_CH.replace(grid_plan=GRID_PLAN), ("g",), (0, 3)),
    (TWO_CH_TWO_P, ("g",), ()),
    (TWO_CH_TWO_P_GRID, ("g",), range(0, 10, 3)),
    (TWO_CH_TWO_P_GRID, ("p",), (0, 5)),
    (TWO_CH_TWO_P_T, ("t",), (0, 5)),
    (TWO_CH_TWO_P_T, ("t", "p"), range(0, 10, 3)),
]


@pytest.mark.parametrize("mda, af_axes, expected_af_indices", AF_TESTS)
def test_autofocus(
    mda: MDASequence,
    af_axes: tuple[str, ...],
    expected_af_indices: Iterable[int],
) -> None:
    af = AxesBasedAF(autofocus_device_name="Z", autofocus_motor_offset=40, axes=af_axes)
    mda = mda.replace(autofocus_plan=af)
    assert isinstance(mda.autofocus_plan, AxesBasedAF)
    assert mda.autofocus_plan.axes == af_axes

    actual = (i for i, e in enumerate(mda) if isinstance(e.action, HardwareAutofocus))
    assert tuple(expected_af_indices) == tuple(actual)


# def _af_seq(axis: tuple[str, ...] | None, gplan: bool = False, zplan: bool = False, tplan: bool = False):
#     import numpy as np
#     # sourcery skip: use-dictionary-union
#     """Helper function to create a sub-sequence with autofocus."""
#     af = {
#             "autofocus_plan": AxesBasedAF(autofocus_device_name="Z", autofocus_motor_offset=np.random.randint(1, 100), axes=axis)
#             if axis else NoAF()
#         }
#     gp = {"grid_plan": {"rows": 2, "columns": 1}} if gplan else {}
#     zp = {"z_plan": {"range": 2, "step": 1}} if zplan else {}
#     tplan = {"time_plan": [{"interval": 1, "loops": 2}]} if tplan else {}

#     return {**af, **gp, **zp, **tplan}

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
AF_SUB_TESTS: list[tuple[MDASequence, tuple[str, ...], Iterable[int]]] = [
    (TWO_CH_SUBPAF_C, (), (2, 4)),
    (TWO_CH.replace(stage_positions=[ZPOS_30, SUB_P_AF_G]), (), ()),
    (TWO_CH.replace(stage_positions=[ZPOS_30, SUB_P_AF_G], grid_plan=GRID_PLAN), (), (4, 7)),
    (TWO_CH.replace(stage_positions=[ZPOS_30, SUB_P_AF_P], grid_plan=GRID_PLAN), (), (4,)),
    (TWO_CH_SUBPAF_C.replace(grid_plan=GRID_PLAN), (), range(4, 11, 2)),
    (TWO_CH_SUBPAF_C.replace(z_plan=ZRANGE2), (), (6, 10)),
    (TWO_CH_SUBPAF_Z.replace(z_plan=ZRANGE2), (), range(6, 17, 2)),
    (TWO_CH_SUBPAF_Z.replace(z_plan=ZRANGE2), ("p",), (0, *tuple(range(7, 18, 2)))),
    (TWO_CH_SUBPAF_C.replace(z_plan=ZRANGE2, grid_plan=GRID_PLAN), ("c",), range(0, 29, 4)),
    (TWO_CH.replace(stage_positions=[ZPOS_30, useq.Position(z=10, sequence=MDASequence(autofocus_plan=AF_C, grid_plan=GRID_PLAN))]), (), (2, 5)),
    (TWO_CH.replace(stage_positions=[SUB_P_AF_C, useq.Position(z=10, sequence=MDASequence(autofocus_plan=AF_G, grid_plan=GRID_PLAN))]), (), range(0, 11, 2)),
]
# fmt: on
# # order, af axis, channels, pos_plan, z_plan, grid_plan, time_plan, expected_af_event_indexes
# mdas = [

#     ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30, "sequence": _af_seq(("c",))}, {"z": 10, "sequence": _af_seq(("g",), True)}], {}, {}, {}, tuple(range(0, 11, 2))),
#     ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30, "sequence": _af_seq(("c",), False, True)}, {"z": 10, "sequence": _af_seq(("g",), True)}], {}, {}, {}, (0, 4, *tuple(range(8, 15, 2)))),
#     ("tpgcz", ("z",), ["DAPI", "FITC"], [{"z": 30}, {"z": 10, "sequence": _af_seq(None, False, True)}], {}, {}, {}, tuple(range(2, 13, 2))),
#     ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30}, {"z": 30, "sequence": _af_seq(("p", "g"), True)},], {}, {}, {}, (2, 4, 6, 8)),
#     ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30, "sequence": _af_seq(("p",), True)}, {"z": 10, "sequence": _af_seq(("p", "g"), True)},], {}, {}, {}, (0, 5, 7, 9, 11)),
#     ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30, "sequence": _af_seq(("p","g"), True)}, {"z": 10, "sequence": _af_seq(("p", "g"), True)},], {}, {}, {}, tuple(range(0, 15, 2))),
#     ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30, "sequence": _af_seq(("p","c"), True)}, {"z": 10, "sequence": _af_seq(("p", "g"), True)},], {}, {}, {}, (0, 3, 6, 8, 10, 12)),
#     ("tpgcz", (), ["DAPI", "FITC"], [
#         {"z": 30, "sequence": _af_seq(("t","p","g"), True)},
#         {"z": 10, "sequence": _af_seq(("t","p","g"), True)},
#         {"z": 10, "sequence": _af_seq(("t","p","g"), True)},
#         ], {}, {}, {"interval": 1, "loops": 2}, tuple(range(0, 47, 2))),
#     ("tpgcz", (), ["DAPI", "FITC"], [
#         {"z": 30, "sequence": _af_seq(("t","p"), True)},
#         {"z": 10, "sequence": _af_seq(("t","p"), True)},
#         {"z": 10, "sequence": _af_seq(("t","p"), True)},
#         ], {}, {}, {"interval": 1, "loops": 2}, tuple(range(0, 26, 5))),
# ]


@pytest.mark.parametrize("mda, global_af_axes, expected_af_indices", AF_SUB_TESTS)
def test_autofocus_sub_sequence(
    mda: MDASequence,
    global_af_axes: tuple[str, ...],
    expected_af_indices: Iterable[int],
) -> None:
    if global_af_axes:
        af_plan = AxesBasedAF(
            autofocus_device_name="Z", autofocus_motor_offset=50, axes=global_af_axes
        )
        mda = mda.replace(autofocus_plan=af_plan)
        assert isinstance(mda.autofocus_plan, AxesBasedAF)
        assert mda.autofocus_plan.axes == global_af_axes

    actual = [i for i, e in enumerate(mda) if isinstance(e.action, HardwareAutofocus)]
    expected = list(expected_af_indices)
    if expected != actual:
        raise AssertionError(f"Expected AF indices at {expected} but got {actual}")
