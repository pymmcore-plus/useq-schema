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
