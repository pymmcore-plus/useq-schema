from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

import useq
from useq._iter_sequence import _new_event
from useq._mda_event import ReadOnlyDict

if TYPE_CHECKING:
    from collections.abc import Iterator


@pytest.mark.parametrize("axis_order", ["tpgcz", "ptgcz"])
def test_timepoints_are_created_as_needed(axis_order: str) -> None:
    """The first events must not wait for (or hold) every timepoint."""
    created = 0

    class CountingSequence(useq.MDASequence):
        def iter_axis(self, axis: str) -> Iterator[Any]:
            nonlocal created
            for item in super().iter_axis(axis):
                created += axis == "t"
                yield item

    seq = CountingSequence(
        time_plan={"interval": 0, "loops": 1000},
        stage_positions=[(0, 0), (1, 1)],
        channels=["DAPI"],
        axis_order=axis_order,
    )
    events = iter(seq)
    for _ in range(3):
        next(events)
    # one timepoint is created to see whether the axis is used at all
    assert created <= 4

    assert sum(1 for _ in events) == 2000 - 3


def test_new_event_matches_model_construct() -> None:
    seq = useq.MDASequence()
    kwargs: Any = {
        "sequence": seq,
        "index": ReadOnlyDict({"t": 1}),
        "x_pos": None,
        "min_start_time": 0.0,
    }
    event = _new_event(kwargs)
    expected = useq.MDAEvent.model_construct(**kwargs)
    assert event == expected
    assert event.model_fields_set == expected.model_fields_set
    assert list(event.__dict__) == list(expected.__dict__)
    assert event.model_dump(exclude_unset=True) == expected.model_dump(
        exclude_unset=True
    )
    # metadata is mutable, and must not be shared between events
    assert event.metadata is not _new_event(kwargs).metadata
    assert _new_event({**kwargs, "metadata": {"a": 1}}).metadata == {"a": 1}
