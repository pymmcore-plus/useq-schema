import itertools
import json
from collections.abc import Sequence
from typing import Any

import numpy as np
import pytest
from pydantic import BaseModel, ValidationError

from useq import (
    MDAEvent,
    MDASequence,
    TIntervalDuration,
    ZAboveBelow,
    ZRangeAround,
)
from useq._actions import CustomAction, HardwareAutofocus
from useq._mda_event import SLMImage

_T = list[tuple[Any, Sequence[float]]]


all_orders = ["".join(i) for i in itertools.permutations("tpgcz")]


def test_axis_order_errors() -> None:
    with pytest.raises(ValueError, match="axis_order must be iterable"):
        MDASequence(axis_order=1)
    with pytest.raises(ValueError, match="Duplicate entries found"):
        MDASequence(axis_order=tuple("tpgcztpgcz"))

    # p after z not ok when z_plan in stage_positions
    with pytest.raises(ValueError, match="'z' cannot precede 'p' in acquisition"):
        MDASequence(
            axis_order=tuple("zpc"),
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
        axis_order=tuple("pzc"),
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
            axis_order=tuple("ct"),
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


@pytest.mark.parametrize("cls", [MDASequence, MDAEvent])
def test_schema(cls: BaseModel) -> None:
    schema = cls.model_json_schema()
    assert schema
    assert json.dumps(schema)


def test_z_position() -> None:
    mda = MDASequence(
        axis_order=tuple("tpcz"), stage_positions=[(222, 1, 10), (111, 1, 20)]
    )
    assert not mda.z_plan
    for event in mda:
        assert event.z_pos


def test_shape_and_axes() -> None:
    mda = MDASequence(
        z_plan=ZAboveBelow(above=8, below=4, step=2),
        time_plan=TIntervalDuration(interval=1, duration=4),
        axis_order=tuple("tzp"),
    )
    assert mda.shape == (5, 7)
    assert mda.axis_order == tuple("tzp")
    assert mda.used_axes == "tz"
    assert mda.sizes == {"t": 5, "z": 7, "p": 0}

    mda2 = mda.replace(axis_order=tuple("zptc"))
    assert mda2.shape == (7, 5)
    assert mda2.axis_order == tuple("zptc")
    assert mda2.used_axes == "zt"
    assert mda2.sizes == {"z": 7, "p": 0, "t": 5, "c": 0}

    assert mda2.uid != mda.uid

    with pytest.raises(ValueError):
        mda.replace(axis_order=tuple("zptasdfs"))


def test_hashable(mda1: MDASequence) -> None:
    assert hash(mda1)
    assert mda1 == mda1
    assert mda1 != 23


def test_mda_str_repr(mda1: MDASequence) -> None:
    assert str(mda1)
    assert repr(mda1)


def test_skip_channel_do_stack_no_zplan() -> None:
    mda = MDASequence(channels=[{"config": "DAPI", "do_stack": False}])
    assert len(list(mda)) == 1


def test_event_action_union() -> None:
    # test that action unions work
    event = MDAEvent(
        action={
            "type": "hardware_autofocus",
            "autofocus_device_name": "Z",
            "autofocus_motor_offset": 25,
        }
    )
    assert isinstance(event.action, HardwareAutofocus)


def test_custom_action() -> None:
    event = MDAEvent(action={"type": "custom"})
    assert isinstance(event.action, CustomAction)

    event2 = MDAEvent(
        action=CustomAction(
            data={
                "foo": "bar",
                "alist": [1, 2, 3],
                "nested": {"a": 1, "b": 2},
                "nested_list": [{"a": 1}, {"b": 2}],
            }
        )
    )
    assert isinstance(event2.action, CustomAction)

    with pytest.raises(ValidationError, match="must be JSON serializable"):
        CustomAction(data={"not-serializable": lambda x: x})


def test_z_plan_num_position() -> None:
    for i in range(1, 100):
        plan = ZRangeAround(range=(i - 1) / 10, step=0.1)
        assert plan.num_positions() == i
        assert len(list(plan)) == i


def test_channel_str() -> None:
    assert MDAEvent(channel="DAPI") == MDAEvent(channel={"config": "DAPI"})


def test_slm_image() -> None:
    data = [[0, 0], [1, 1]]

    # directly passing data
    event = MDAEvent(slm_image=data)
    assert isinstance(event.slm_image, SLMImage)
    repr(event)

    # we can cast SLMIamge to a numpy array
    assert isinstance(np.asarray(event.slm_image), np.ndarray)
    np.testing.assert_array_equal(event.slm_image, np.array(data))

    # variant that also specifies device label
    event2 = MDAEvent(slm_image={"data": data, "device": "SLM"})
    assert event2.slm_image is not None
    np.testing.assert_array_equal(event2.slm_image, np.array(data))
    assert event2.slm_image.device == "SLM"
    repr(event2)

    # directly provide numpy array
    event3 = MDAEvent(slm_image=SLMImage(data=np.ones((10, 10))))
    print(repr(event3))

    assert event3 != event2
