from __future__ import annotations

import gc
import weakref
from typing import TYPE_CHECKING, Any

import pytest

import useq
from useq._iter_sequence import _new_event
from useq._mda_event import ReadOnlyDict

if TYPE_CHECKING:
    from collections.abc import Iterator

AF_ON_P = {"autofocus_motor_offset": 10, "axes": ("p",)}
SUB_Z = useq.MDASequence(z_plan={"range": 1, "step": 1})


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


def test_iteration_does_not_keep_sequence_alive() -> None:
    seq = useq.MDASequence(time_plan={"interval": 0, "loops": 3}, channels=["DAPI"])
    ref = weakref.ref(seq)
    assert len(list(seq)) == 3
    del seq
    gc.collect()
    assert ref() is None


def test_iterate_copy_with_new_plan() -> None:
    seq = useq.MDASequence(z_plan={"range": 1, "step": 1})
    assert len(list(seq)) == 2
    copied = seq.model_copy(update={"z_plan": useq.ZRangeAround(range=2, step=1)})
    assert len(list(copied)) == 3
    assert len(list(seq)) == 2


def test_autofocus_events_are_the_same_each_iteration() -> None:
    seq = useq.MDASequence(stage_positions=[(0, 0, 0)], autofocus_plan=AF_ON_P)
    events = list(seq)
    assert [e.action.type for e in events] == ["hardware_autofocus", "acquire_image"]
    assert list(seq) == events


def test_autofocus_with_concurrent_iteration() -> None:
    seq = useq.MDASequence(
        time_plan={"interval": 1, "loops": 2},
        stage_positions=[(0, 0, 0), useq.Position(x=1, y=1, z=1, sequence=SUB_Z)],
        autofocus_plan=AF_ON_P,
    )
    events = list(seq)
    assert sum(isinstance(e.action, useq.HardwareAutofocus) for e in events) == 4

    first, second = iter(seq), iter(seq)
    interleaved = [e for pair in zip(first, second, strict=True) for e in pair]
    assert interleaved[::2] == events
    assert interleaved[1::2] == events


def test_sub_sequence_exposure_does_not_carry_over() -> None:
    """A channel without an exposure must not use that of the previous channel."""
    channels = [useq.Channel(config="A", exposure=10), useq.Channel(config="B")]
    seq = useq.MDASequence(
        stage_positions=[useq.Position(x=0, y=0, sequence={"channels": channels})]
    )
    assert [(e.channel.config, e.exposure) for e in seq if e.channel] == [
        ("A", 10),
        ("B", None),
    ]
    # ... as is the case when the channels are declared on the main sequence
    seq = useq.MDASequence(stage_positions=[(0, 0)], channels=channels)
    assert [e.exposure for e in seq] == [10, None]


@pytest.mark.parametrize(
    "positions",
    [
        [useq.Position(x=0), useq.Position(x=1)],
        [useq.Position(x=0, sequence=SUB_Z), useq.Position(x=1)],
        [useq.Position(x=0), useq.Position(x=1, sequence=SUB_Z)],
        [useq.Position(x=0, sequence=SUB_Z), useq.Position(x=1, sequence=SUB_Z)],
    ],
)
def test_reset_event_timer_with_position_sequences(
    positions: list[useq.Position],
) -> None:
    """Only the first event of the first timepoint resets the event timer."""
    seq = useq.MDASequence(
        time_plan={"interval": 1, "loops": 2}, stage_positions=positions
    )
    first, *rest = seq
    assert first.reset_event_timer
    assert not any(e.reset_event_timer for e in rest)
