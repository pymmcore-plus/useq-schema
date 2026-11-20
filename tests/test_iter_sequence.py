from __future__ import annotations

import copy
import gc
import pickle
import weakref
from typing import TYPE_CHECKING, Any

import pytest

import useq
from useq._iter_sequence import _new_event
from useq._mda_event import ReadOnlyDict

if TYPE_CHECKING:
    from collections.abc import Iterator

SUB_Z = useq.MDASequence(z_plan={"range": 1, "step": 1})


@pytest.mark.parametrize("axis_order", ["tpgcz", "ptgcz", "pczgt"])
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


def test_iteration_does_not_keep_sequence_alive() -> None:
    seq = useq.MDASequence(time_plan={"interval": 0, "loops": 3}, channels=["DAPI"])
    ref = weakref.ref(seq)
    assert len(list(seq)) == 3
    del seq
    gc.collect()
    assert ref() is None


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


def test_read_only_dict() -> None:
    assert ReadOnlyDict() == ReadOnlyDict(None) == {}
    assert ReadOnlyDict({"t": 1}, c=2) == ReadOnlyDict([("t", 1), ("c", 2)])
    index = ReadOnlyDict(ReadOnlyDict({"t": 1}))
    assert dict(index) == {"t": 1}
    with pytest.raises(TypeError, match="Read-only"):
        index["t"] = 2


def test_random_points_are_the_same_each_iteration() -> None:
    seq = useq.MDASequence(grid_plan=useq.RandomPoints(num_points=5, random_seed=None))
    positions = [(e.x_pos, e.y_pos) for e in seq]
    assert positions == [(e.x_pos, e.y_pos) for e in seq]
    assert seq.sizes["g"] == 5


def test_model_copy_update() -> None:
    seq = useq.MDASequence(
        time_plan={"interval": 1, "loops": 3}, z_plan={"range": 1, "step": 1}
    )
    assert seq.sizes == {"t": 3, "p": 0, "g": 0, "c": 0, "z": 2}
    assert len(list(seq)) == 6

    updated = seq.model_copy(
        update={
            "time_plan": useq.TIntervalLoops(interval=1, loops=5),
            "z_plan": useq.ZRangeAround(range=2, step=1),
        }
    )
    assert updated.sizes == {"t": 5, "p": 0, "g": 0, "c": 0, "z": 3}
    assert updated.shape == (5, 3)
    assert len(list(updated)) == 15
    # the original is unchanged
    assert seq.sizes["t"] == 3
    assert len(list(seq)) == 6


@pytest.mark.parametrize(
    "time_plan",
    [
        {"interval": 1, "loops": 4},
        {"duration": 3, "loops": 4},
        {"interval": 1, "duration": 3},
        [{"interval": 1, "loops": 4}],
        [{"interval": 1, "loops": 4}, {"interval": 2, "duration": 4}],
        [{"interval": 1, "loops": 4}] * 3,
    ],
)
def test_time_axis_size(time_plan: Any) -> None:
    seq = useq.MDASequence(time_plan=time_plan)
    assert seq.time_plan is not None
    n_timepoints = len(list(seq.time_plan))
    assert seq.time_plan.num_timepoints() == n_timepoints
    assert seq.sizes["t"] == n_timepoints == len(list(seq))


def test_time_axis_size_with_custom_iter_axis() -> None:
    class EveryOtherTimepoint(useq.MDASequence):
        def iter_axis(self, axis: str) -> Iterator[Any]:
            items = super().iter_axis(axis)
            yield from (list(items)[::2] if axis == "t" else items)

    seq = EveryOtherTimepoint(time_plan={"interval": 1, "loops": 5})
    assert seq.sizes["t"] == 3 == len(list(seq))


@pytest.mark.parametrize("copier", [copy.copy, copy.deepcopy, pickle.loads])
def test_copied_sequence_iterates(copier: Any) -> None:
    seq = useq.MDASequence(
        time_plan={"interval": 1, "loops": 2},
        stage_positions=[useq.Position(x=1, y=2, sequence=SUB_Z)],
        channels=["DAPI"],
    )
    events = list(seq)
    copied = copier(pickle.dumps(seq) if copier is pickle.loads else seq)
    assert copied.sizes == seq.sizes
    assert [e.model_dump(exclude={"sequence"}) for e in copied] == [
        e.model_dump(exclude={"sequence"}) for e in events
    ]
