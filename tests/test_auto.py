from __future__ import annotations

import pytest

from useq import AxesBasedAF, HardwareAutofocus, MDASequence, NoAF


# fmt: off
def _assert_autofocus(
    sequence: MDASequence, expected_event_indexes: tuple[int], pos_and_z: dict[str, tuple[float, float]]  # noqa: E501
):
    """Helper function to assert autofocus events in a sequence."""
    # example of pos_and_z: {pos_index: (z, z_af)} = {0: (10, 30), 1: (50, 300)}
    for idx, e in enumerate(sequence):
        if idx in expected_event_indexes:
            action = e.action
            assert isinstance(action, HardwareAutofocus)
            assert action.type == "hardware_autofocus"
            assert action.autofocus_device_name == "Z"
            # assert action.autofocus_motor_offset == pos_and_z[e.index["p"]][1]

        else:
            assert e.action.type == 'acquire_image'

mdas = [
    # order, af axis, channels, pos_plan, z_plan, grid_plan, time_plan, expected_af_event_indexes  # noqa: E501
    ("tpgcz", ("c",), [], [{"z": 30}], {"range": 2, "step": 1}, {}, {}, ()),  # noqa: E501
    ("tpgcz", ("c",), ["DAPI", "FITC"], [{"z": 30}], {"range": 2, "step": 1}, {}, {}, (0, 3)),  # noqa: E501
    ("tpgzc", ("c",), ["DAPI", "FITC"], [{"z": 30}], {"range": 2, "step": 1}, {}, {}, tuple(range(6))),  # noqa: E501
    ("tpgcz", ("z",), ["DAPI", "FITC"], [{"z": 30}], {"range": 2, "step": 1}, {}, {}, tuple(range(6))),  # noqa: E501
    ("tpgzc", ("z",), ["DAPI", "FITC"], [{"z": 30}], {"range": 2, "step": 1}, {}, {}, (0, 2, 4)),  # noqa: E501
    ("tpgcz", ("g",), ["DAPI", "FITC"], [{"z": 30}], {}, {"rows": 2, "columns": 1}, {}, (0, 2)),  # noqa: E501
    ("tpgcz", ("g",), ["DAPI", "FITC"], [{"z": 30}, {"z": 20}], {}, {}, {}, ()),  # noqa: E501
    ("tpgcz", ("g",), ["DAPI", "FITC"], [{"z": 30}, {"z": 200}], {}, {"rows": 2, "columns": 1}, {}, (0, 2, 4, 6)),  # noqa: E501
    ("tpgcz", ("p",), ["DAPI", "FITC"], [{"z": 30}, {"z": 200}], {}, {"rows": 2, "columns": 1}, {}, (0, 4)),  # noqa: E501
    ("tpgcz", ("t",), ["DAPI", "FITC"], [{"z": 30}, {"z": 200}], {}, {}, {"interval": 1, "loops": 2}, (0, 4)),  # noqa: E501
    ("tpgcz", ("t", "p"), ["DAPI", "FITC"], [{"z": 30}, {"z": 200}], {}, {}, {"interval": 1, "loops": 2}, (0, 2, 4, 6)),  # noqa: E501
]

@pytest.mark.parametrize("order, axis, ch, pplan, zplan, gplan, tplan, expected_event_indexes", mdas)  # noqa: E501
def test_autofocus(
    order: str, axis: tuple[str, ...], ch: list, pplan: list, zplan: dict, gplan: dict, tplan: dict, expected_event_indexes: int  # noqa: E501
):
    if axis:
        autofocus_plan = AxesBasedAF(autofocus_device_name='Z', autofocus_motor_offset=40, axes=axis)
    else:
        autofocus_plan = None
    mda = MDASequence(
        axis_order=order,
        channels=ch,
        stage_positions=pplan,
        z_plan=zplan,
        grid_plan=gplan,
        time_plan=tplan,
        autofocus_plan=autofocus_plan
    )

    # get dict with p index and repextive z an z_af
    {p: (mda.stage_positions[p].z, mda.autofocus_plan.autofocus_motor_offset) for p in range(len(pplan))}  # noqa: E501
    # assert autofocus events
    # _assert_autofocus(mda, expected_event_indexes, pos_and_z)

    for e in mda:
        print(e)


def _af_seq(axis: tuple[str, ...] | None, gplan: bool = False, zplan: bool = False, tplan: bool = False):  # noqa: E501
    import numpy as np
    # sourcery skip: use-dictionary-union
    """Helper function to create a sub-sequence with autofocus."""
    af = {
        "autofocus_plan": {
            "autofocus_device_name": "Z",
            "autofocus_motor_offset": np.random.randint(1, 100),
            "axes": axis
        } if axis else {}
    }
    gp = {"grid_plan": {"rows": 2, "columns": 1}} if gplan else {}
    zp = {"z_plan": {"range": 2, "step": 1}} if zplan else {}
    tplan = {"time_plan": [{"interval": 1, "loops": 2}]} if tplan else {}

    return {**af, **gp, **zp, **tplan}


def _get_autofocus_z(mda: MDASequence):
    """Helper function to get the autofocus z and z_af positions for each position."""
    pos_and_z = {}
    for p in range(len(mda.stage_positions)):
        z = mda.stage_positions[p].z
        try:
            z_af = (
                mda.stage_positions[p].sequence.autofocus_plan.autofocus_motor_offset
                or mda.autofocus_plan.autofocus_motor_offset
            )
        except AttributeError:
            z_af = mda.autofocus_plan.autofocus_motor_offset
        pos_and_z[p] = (z, z_af)
    return pos_and_z

# order, af axis, channels, pos_plan, z_plan, grid_plan, time_plan, expected_af_event_indexes  # noqa: E501
mdas = [
    ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30}, {"z": 10, "sequence": _af_seq(("c",))}], {}, {}, {}, (2, 3)),  # noqa: E501
    ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30}, {"z": 10, "sequence": _af_seq(("g",))}], {}, {}, {}, ()),  # noqa: E501
    ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30}, {"z": 10, "sequence": _af_seq(("g",))}], {}, {"rows": 2, "columns": 1}, {}, (4, 6)),  # noqa: E501
    ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30}, {"z": 10, "sequence": _af_seq(("p",))}], {}, {"rows": 2, "columns": 1}, {}, (4,)),  # noqa: E501
    ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30}, {"z": 10, "sequence": _af_seq(("c",))}], {}, {"rows": 2, "columns": 1}, {}, (4, 5, 6, 7)),  # noqa: E501
    ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30}, {"z": 10, "sequence": _af_seq(("c",))}], {"range": 2, "step": 1}, {}, {}, (6, 9)),  # noqa: E501
    ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30}, {"z": 10, "sequence": _af_seq(("z",))}], {"range": 2, "step": 1}, {}, {}, (tuple(range(6, 12)))),  # noqa: E501
    ("tpgcz", ("p",), ["DAPI", "FITC"], [{"z": 30}, {"z": 10, "sequence": _af_seq(("z",))}], {"range": 2, "step": 1}, {}, {}, (0, *tuple(range(6, 12)))),  # noqa: E501
    ("tpgcz", ("c",), ["DAPI", "FITC"], [{"z": 30}, {"z": 10, "sequence": _af_seq(("c",))}], {"range": 2, "step": 1}, {"rows": 2, "columns": 1}, {}, (tuple(range(0, 24, 3)))),  # noqa: E501
    ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30}, {"z": 10, "sequence": _af_seq(("c",), True)}], {}, {}, {}, (2, 4)),  # noqa: E501
    ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30, "sequence": _af_seq(("c",))}, {"z": 10, "sequence": _af_seq(("g",), True)}], {}, {}, {}, tuple(range(6))),  # noqa: E501
    ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30, "sequence": _af_seq(("c",), False, True)}, {"z": 10, "sequence": _af_seq(("g",), True)}], {}, {}, {}, (0, 3, 6, 7, 8, 9)),  # noqa: E501
    ("tpgcz", ("z",), ["DAPI", "FITC"], [{"z": 30}, {"z": 10, "sequence": _af_seq(None, False, True)}], {}, {}, {}, tuple(range(2, 8))),  # noqa: E501
    ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30}, {"z": 30, "sequence": _af_seq(("p", "g"), True)},], {}, {}, {}, (2, 3, 4, 5)),  # noqa: E501
    ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30, "sequence": _af_seq(("p",), True)}, {"z": 10, "sequence": _af_seq(("p", "g"), True)},], {}, {}, {}, (0, 4, 5, 6, 7)),  # noqa: E501
    ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30, "sequence": _af_seq(("p","g"), True)}, {"z": 10, "sequence": _af_seq(("p", "g"), True)},], {}, {}, {}, tuple(range(8))),  # noqa: E501
    ("tpgcz", (), ["DAPI", "FITC"], [{"z": 30, "sequence": _af_seq(("p","c"), True)}, {"z": 10, "sequence": _af_seq(("p", "g"), True)},], {}, {}, {}, (0, 2, 4, 5, 6, 7)),  # noqa: E501
    ("tpgcz", (), ["DAPI", "FITC"], [
        {"z": 30, "sequence": _af_seq(("t","p"), True)},
        {"z": 10, "sequence": _af_seq(("t","p"), True)},
        {"z": 10, "sequence": _af_seq(("t","p"), True)},
        ], {}, {}, {"interval": 1, "loops": 2}, tuple(range(0, 24, 4))),
    ("tpgcz", (), ["DAPI", "FITC"], [
        {"z": 30, "sequence": _af_seq(("t","p","g"), True)},
        {"z": 10, "sequence": _af_seq(("t","p","g"), True)},
        {"z": 10, "sequence": _af_seq(("t","p","g"), True)},
        ], {}, {}, {"interval": 1, "loops": 2}, tuple(range(24))),
]

@pytest.mark.parametrize("order, axis, ch, pplan, zplan, gplan, tplan, expected_event_indexes", mdas)  # noqa: E501
def test_autofocus_sub_sequence(order: str, axis: tuple[str, ...], ch: list, pplan: list, zplan: dict, gplan: dict, tplan: dict, expected_event_indexes: int):  # noqa: E501
    mda = MDASequence(
        axis_order=order,
        channels=ch,
        stage_positions=pplan,
        z_plan=zplan,
        grid_plan=gplan,
        time_plan=tplan,
        autofocus_plan=AxesBasedAF(autofocus_device_name='Z', autofocus_motor_offset=50, axes=axis) if axis else NoAF()
    )

    # get dict with p index and repextive z an z_af
    pos_and_z = _get_autofocus_z(mda)
    # assert autofocus events
    _assert_autofocus(mda, expected_event_indexes, pos_and_z)

    print()
    for e in mda:
        print(e.action.type)
