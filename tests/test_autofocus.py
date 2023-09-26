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
AF = AxesBasedAF(autofocus_device_name="Z", autofocus_motor_offset=40, axes=())
AF_C = AF.model_copy(update={"axes": ("c",)})
AF_G = AF.model_copy(update={"axes": ("g",)})
AF_P = AF.model_copy(update={"axes": ("p",)})
AF_Z = AF.model_copy(update={"axes": ("z",)})
AF_SEQ_C = MDASequence(autofocus_plan=AF_C)
SUB_P_AF_C = useq.Position(z=10, sequence=AF_SEQ_C)
SUB_P_AF_G = useq.Position(z=10, sequence=MDASequence(autofocus_plan=AF_G))
SUB_P_AF_P = useq.Position(z=10, sequence=MDASequence(autofocus_plan=AF_P))
SUB_P_AF_Z = useq.Position(z=10, sequence=MDASequence(autofocus_plan=AF_Z))
TWO_CH_SUBPAF_C = TWO_CH.replace(stage_positions=[ZPOS_30, SUB_P_AF_C])
TWO_CH_SUBPAF_Z = TWO_CH.replace(stage_positions=[ZPOS_30, SUB_P_AF_Z])

# fmt: off
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
    (TWO_CH.replace(stage_positions=[ZPOS_200, useq.Position(z=10, sequence=MDASequence(z_plan=ZRANGE2))]), ("z",), range(2, 13, 2)),
    (TWO_CH.replace(stage_positions=[ZPOS_200, useq.Position(z=10, sequence=MDASequence(z_plan=ZRANGE2))]), ("c",), (0, 2, 4, 8)),
    (TWO_CH.replace(stage_positions=[ZPOS_200, useq.Position(z=10, sequence=MDASequence(z_plan=ZRANGE2))]), (), ()),
]
# fmt: on


@pytest.mark.parametrize("mda, af_axes, expected_af_indices", AF_TESTS)
def test_autofocus(
    mda: MDASequence,
    af_axes: tuple[str, ...],
    expected_af_indices: Iterable[int],
) -> None:
    if af_axes:
        mda = mda.replace(autofocus_plan=AF.model_copy(update={"axes": af_axes}))
        assert isinstance(mda.autofocus_plan, AxesBasedAF)
        assert mda.autofocus_plan.axes == af_axes

    actual = [i for i, e in enumerate(mda) if isinstance(e.action, HardwareAutofocus)]
    expected = list(expected_af_indices)
    assert expected == actual, "Unexpected AF indices"


def test_autofocus_z_pos() -> None:
    mda = TWO_CH.replace(
        stage_positions=[ZPOS_200], z_plan=ZRANGE2, autofocus_plan=AF_C
    )
    assert all(e.z_pos == 200 for e in mda if isinstance(e.action, HardwareAutofocus))


def test_autofocus_z_pos_abovebelow() -> None:
    mda = TWO_CH.replace(
        stage_positions=[ZPOS_200],
        z_plan=useq.ZAboveBelow(above=2, below=2, step=1),
        autofocus_plan=AF_C,
    )
    assert all(e.z_pos == 200 for e in mda if isinstance(e.action, HardwareAutofocus))


def test_autofocus_z_pos_af_sub_sequence() -> None:
    mda = TWO_CH.replace(stage_positions=[SUB_P_AF_C], z_plan=ZRANGE2)
    assert all(e.z_pos == 10 for e in mda if isinstance(e.action, HardwareAutofocus))


def test_autofocus_z_pos_af_sub_sequence_zplan() -> None:
    mda = TWO_CH_SUBPAF_C
    assert all(e.z_pos == 10 for e in mda if isinstance(e.action, HardwareAutofocus))


def test_autofocus_z_pos_multi_plans() -> None:
    mda = TWO_CH.replace(
        stage_positions=[ZPOS_200],
        grid_plan=GRID_PLAN,
        z_plan=ZRANGE2,
        autofocus_plan=AF_C,
    )

    assert all(e.z_pos == 200 for e in mda if isinstance(e.action, HardwareAutofocus))


def test_af_no_name() -> None:
    list(
        MDASequence(
            time_plan={"interval": 1, "loops": 2},
            autofocus_plan=AxesBasedAF(axes=("t", "c")),
        )
    )
