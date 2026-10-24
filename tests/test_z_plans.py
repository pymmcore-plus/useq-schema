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
