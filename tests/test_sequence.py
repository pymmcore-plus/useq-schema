import itertools
import json
from collections.abc import Sequence
from typing import Any

import numpy as np
import pytest
from pydantic import BaseModel, ValidationError

from useq import (
    GridRelative,
    MDAEvent,
    MDASequence,
    Position,
    TIntervalDuration,
    TIntervalLoops,
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


z_plans: _T = [
    ({"above": 8, "below": 4, "step": 2}, [-4, -2, 0, 2, 4, 6, 8]),
    ({"range": 8, "step": 1}, [-4, -3, -2, -1, 0, 1, 2, 3, 4]),
]

t_plans: _T = [
    ({"loops": 5, "duration": 8}, [0, 2, 4, 6, 8]),
    ({"loops": 5, "interval": 0.25}, [0, 0.25, 0.5, 0.75, 1]),
]

c_inputs = [
    ("DAPI", ("Channel", "DAPI")),
    ({"config": "DAPI"}, ("Channel", "DAPI")),
    ({"config": "DAPI", "group": "Group", "acquire_every": 3}, ("Group", "DAPI")),
]

p_inputs = [
    ([{"x": 0, "y": 1, "z": 2}], (0, 1, 2)),
    ([{"y": 200}], (None, 200, None)),
    ([(100, 200, 300)], (100, 200, 300)),
]


@pytest.mark.parametrize("tplan, texpectation", t_plans)
@pytest.mark.parametrize("zplan, zexpectation", z_plans)
@pytest.mark.parametrize("channel, cexpectation", c_inputs)
@pytest.mark.parametrize("positions, pexpectation", p_inputs)
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
    assert mda.z_plan
    assert mda.time_plan
    assert list(mda.z_plan) == zexpectation
    assert list(mda.time_plan) == texpectation
    assert (mda.channels[0].group, mda.channels[0].config) == cexpectation
    position = mda.stage_positions[0]
    assert (position.x, position.y, position.z) == pexpectation


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


def test_keep_shutter_open() -> None:
    # with z as the last axis, the shutter will be left open
    # whenever z is the first index (since there are only 2 z planes)
    mda1 = MDASequence(
        axis_order=tuple("tcz"),
        channels=["DAPI", "FITC"],
        time_plan=TIntervalLoops(loops=2, interval=0),
        z_plan=ZRangeAround(range=1, step=1),
        keep_shutter_open_across="z",
    )
    assert all(e.keep_shutter_open for e in mda1 if e.index["z"] == 0)

    # with c as the last axis, the shutter will never be left open
    mda2 = MDASequence(
        axis_order=tuple("tzc"),
        channels=["DAPI", "FITC"],
        time_plan=TIntervalLoops(loops=2, interval=0),
        z_plan=ZRangeAround(range=1, step=1),
        keep_shutter_open_across="z",
    )
    assert not any(e.keep_shutter_open for e in mda2)

    # because t is changing faster than z, the shutter will never be left open
    mda3 = MDASequence(
        axis_order=tuple("czt"),
        channels=["DAPI", "FITC"],
        time_plan=TIntervalLoops(loops=2, interval=0),
        z_plan=ZRangeAround(range=1, step=1),
        keep_shutter_open_across="z",
    )
    assert not any(e.keep_shutter_open for e in mda3)

    # but, if we include 't' in the keep_shutter_open_across,
    # it will be left open except when it's the last t and last z
    mda4 = MDASequence(
        axis_order=tuple("czt"),
        channels=["DAPI", "FITC"],
        time_plan=TIntervalLoops(loops=2, interval=0),
        z_plan=ZRangeAround(range=1, step=1),
        keep_shutter_open_across=("z", "t"),
    )
    for event in mda4:
        is_last_zt = bool(event.index["t"] == 1 and event.index["z"] == 1)
        assert event.keep_shutter_open != is_last_zt

    # even though c is the last axis, and comes after g, because the grid happens
    # on a subsequence shutter will be open across the grid for each position
    subseq = MDASequence(grid_plan=GridRelative(rows=2, columns=2))
    mda5 = MDASequence(
        axis_order=tuple("pgc"),
        channels=["DAPI", "FITC"],
        stage_positions=[Position(sequence=subseq)],
        keep_shutter_open_across="g",
    )
    for event in mda5:
        assert event.keep_shutter_open != (event.index["g"] == 3)


def test_z_plan_num_position() -> None:
    for i in range(1, 100):
        plan = ZRangeAround(range=(i - 1) / 10, step=0.1)
        assert plan.num_positions() == i
        assert len(list(plan)) == i


def test_channel_str() -> None:
    assert MDAEvent(channel="DAPI") == MDAEvent(channel={"config": "DAPI"})


def test_reset_event_timer() -> None:
    events = list(
        MDASequence(
            stage_positions=[(100, 100), (0, 0)],
            time_plan={"interval": 1, "loops": 2},
            axis_order=tuple("ptgcz"),
        )
    )
    assert events[0].reset_event_timer
    assert not events[1].reset_event_timer
    assert events[2].reset_event_timer
    assert not events[3].reset_event_timer

    events = list(
        MDASequence(
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
        )
    )

    assert events[0].reset_event_timer
    assert not events[1].reset_event_timer
    assert events[2].reset_event_timer
    assert not events[3].reset_event_timer


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
