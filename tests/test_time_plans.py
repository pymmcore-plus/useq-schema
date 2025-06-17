from collections.abc import Sequence
from typing import Any, get_args

import pytest
from pydantic import TypeAdapter

import useq

t_inputs: list[tuple[Any, Sequence[float]]] = [
    # frame every second for 4 seconds
    (useq.TIntervalDuration(interval=1, duration=4), [0, 1, 2, 3, 4]),
    # 5 frames spanning 8 seconds
    (useq.TDurationLoops(loops=5, duration=8), [0, 2, 4, 6, 8]),
    # 5 frames, taken every 250 ms
    (useq.TIntervalLoops(loops=5, interval=0.25), [0, 0.25, 0.5, 0.75, 1]),
    (
        [
            useq.TIntervalLoops(loops=5, interval=0.25),
            useq.TIntervalDuration(interval=1, duration=4),
        ],
        [0, 0.25, 0.5, 0.75, 1, 2, 3, 4, 5],
    ),
    ({"interval": 0.5, "duration": 2}, [0, 0.5, 1, 1.5, 2]),
    ({"loops": 5, "duration": 8}, [0, 2, 4, 6, 8]),
    ({"loops": 5, "interval": 0.25}, [0, 0.25, 0.5, 0.75, 1]),
    (
        [{"loops": 5, "interval": 0.25}, {"interval": 1, "duration": 4}],
        [0, 0.25, 0.50, 0.75, 1, 2, 3, 4, 5],
    ),
    ({"loops": 5, "duration": {"milliseconds": 8}}, [0, 0.002, 0.004, 0.006, 0.008]),
    ({"loops": 5, "duration": {"seconds": 8}}, [0, 2, 4, 6, 8]),
]


@pytest.mark.parametrize("tplan, texpectation", t_inputs)
def test_time_plan(tplan: useq.AnyTimePlan, texpectation: Sequence[float]) -> None:
    time_plan: useq.AnyTimePlan = TypeAdapter(useq.AnyTimePlan).validate_python(tplan)
    assert isinstance(time_plan, get_args(useq.AnyTimePlan))
    assert time_plan and list(time_plan) == texpectation
    assert time_plan.num_timepoints() == len(texpectation)
