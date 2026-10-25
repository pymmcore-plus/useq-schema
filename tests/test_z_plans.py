from collections.abc import Sequence
from typing import Any

import pytest
from pydantic import TypeAdapter

import useq
import useq._z

z_inputs: list[tuple[Any, Sequence[float]]] = [
    (useq.ZAboveBelow(above=8, below=4, step=2), [-4, -2, 0, 2, 4, 6, 8]),
    (useq.ZAbsolutePositions(absolute=[0, 0.5, 5]), [0, 0.5, 5]),
    (useq.ZRelativePositions(relative=[0, 0.5, 5]), [0, 0.5, 5]),
    (useq.ZRangeAround(range=8, step=1), [-4, -3, -2, -1, 0, 1, 2, 3, 4]),
    ({"above": 8, "below": 4, "step": 2}, [-4, -2, 0, 2, 4, 6, 8]),
    ({"range": 8, "step": 1}, [-4, -3, -2, -1, 0, 1, 2, 3, 4]),
    ({"absolute": [0, 0.5, 5]}, [0, 0.5, 5]),
    ({"relative": [0, 0.5, 5]}, [0, 0.5, 5]),
]


@pytest.mark.parametrize("zplan, zexpectation", z_inputs)
def test_z_plan(zplan: Any, zexpectation: Sequence[float]) -> None:
    z_plan: useq._z.ZPlan = TypeAdapter(useq.AnyZPlan).validate_python(zplan)
    assert isinstance(z_plan, useq._z.ZPlan)
    assert z_plan and list(z_plan) == zexpectation
    assert z_plan.num_positions() == len(zexpectation)


@pytest.mark.parametrize(
    "zplan",
    [
        useq.ZRangeAround(range=5, step=2),
        useq.ZRangeAround(range=0.4, step=1),
        useq.ZTopBottom(top=4.5, bottom=0, step=1),
        useq.ZAboveBelow(above=1.3, below=1, step=1),
    ],
)
def test_num_positions_matches_positions(zplan: useq._z.ZPlan) -> None:
    # the step does not divide the range evenly
    assert zplan.num_positions() == len(list(zplan))


def test_do_stack_false_uses_middle_plane() -> None:
    seq = useq.MDASequence(
        z_plan=useq.ZRangeAround(range=5, step=2),  # visits -2.5, -0.5, 1.5
        channels=["DAPI", {"config": "BF", "do_stack": False}],
    )
    bf = [e for e in seq if e.channel and e.channel.config == "BF"]
    assert [e.z_pos for e in bf] == [-0.5]

    seq = useq.MDASequence(
        z_plan=useq.ZRangeAround(range=0.4, step=1),  # visits only -0.2
        channels=["DAPI", {"config": "BF", "do_stack": False}],
    )
    bf = [e for e in seq if e.channel and e.channel.config == "BF"]
    assert [e.z_pos for e in bf] == [-0.2]


@pytest.mark.parametrize(
    "zplan, expected",
    [
        (useq.ZRangeAround(range=3, step=2), [-1.5, 0.5]),
        (useq.ZRangeAround(range=5, step=2), [-2.5, -0.5, 1.5]),
        (useq.ZTopBottom(top=1.5, bottom=0, step=1), [0, 1]),
        (
            useq.ZRangeAround(range=0.55, step=0.1),
            [-0.275, -0.175, -0.075, 0.025, 0.125, 0.225],
        ),
    ],
)
def test_half_step_rounds_down(zplan: useq._z.ZPlan, expected: list[float]) -> None:
    assert list(zplan) == pytest.approx(expected)


@pytest.mark.parametrize("step", [0.1, 0.2, 0.3, 0.6])
@pytest.mark.parametrize("range_", [round(x * 0.05, 2) for x in range(1, 40)])
def test_last_position_within_half_step_of_top(range_: float, step: float) -> None:
    # the last position may undershoot the top by up to half a step,
    # and may overshoot it by strictly less than half a step
    *_, last = useq.ZRangeAround(range=range_, step=step)
    top = range_ / 2
    assert -step / 2 - 1e-9 <= last - top < step / 2 - 1e-9
