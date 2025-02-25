from collections.abc import Iterator, Sequence
from datetime import timedelta
from typing import Annotated, Any, Union

from pydantic import BeforeValidator, Field, PlainSerializer

from useq._base_model import FrozenModel

# slightly modified so that we can accept dict objects as input
# and serialize to total_seconds
TimeDelta = Annotated[
    timedelta,
    BeforeValidator(lambda v: timedelta(**v) if isinstance(v, dict) else v),
    PlainSerializer(lambda td: td.total_seconds()),
]


class TimePlan(FrozenModel):
    # TODO: probably needs to be implemented by engine
    prioritize_duration: bool = False  # or prioritize num frames

    def __iter__(self) -> Iterator[float]:  # type: ignore
        for td in self.deltas():
            yield td.total_seconds()

    def length(self) -> int:
        return self.num_timepoints()

    def should_skip(cls, kwargs: dict) -> bool:
        return False

    def create_event_kwargs(self, val: Any) -> dict:
        return {"min_start_time": val}

    @property
    def axis_key(self) -> str:
        """A string id representing the axis."""
        return "t"

    def num_timepoints(self) -> int:
        """Return the number of timepoints in the sequence.

        If the sequence is infinite, returns -1.
        """
        return self.loops  # type: ignore  # TODO

    def deltas(self) -> Iterator[timedelta]:
        """Iterate over the time deltas between timepoints.

        If the sequence is infinite, yields indefinitely.
        """
        current = timedelta(0)
        loops = self.num_timepoints()
        while loops != 0:
            yield current
            current += self.interval  # type: ignore  # TODO
            loops -= 1


class TIntervalLoops(TimePlan):
    """Define temporal sequence using interval and number of loops.

    Attributes
    ----------
    interval : str | timedelta | float
        Time between frames. Scalars are interpreted as seconds.
        Strings are parsed according to ISO 8601.
    loops : int
        Number of frames.
    prioritize_duration : bool
        If `True`, instructs engine to prioritize duration over number of frames in case
        of conflict. By default, `False`.
    """

    interval: TimeDelta
    loops: int = Field(..., gt=0)

    @property
    def duration(self) -> timedelta:
        return self.interval * (self.loops - 1)


class TDurationLoops(TimePlan):
    """Define temporal sequence using duration and number of loops.

    Attributes
    ----------
    duration : str | timedelta
        Total duration of sequence. Scalars are interpreted as seconds.
        Strings are parsed according to ISO 8601.
    loops : int
        Number of frames.
    prioritize_duration : bool
        If `True`, instructs engine to prioritize duration over number of frames in case
        of conflict. By default, `False`.
    """

    duration: TimeDelta
    loops: int = Field(..., gt=0)

    @property
    def interval(self) -> timedelta:
        # -1 makes it so that the last loop will *occur* at duration, not *finish*
        return self.duration / (self.loops - 1)


class TIntervalDuration(TimePlan):
    """Define temporal sequence using interval and duration.

    Attributes
    ----------
    interval : str | timedelta
        Time between frames. Scalars are interpreted as seconds.
        Strings are parsed according to ISO 8601.
    duration : str | timedelta
        Total duration of sequence.
    prioritize_duration : bool
        If `True`, instructs engine to prioritize duration over number of frames in case
        of conflict. By default, `True`.
    """

    interval: TimeDelta
    duration: TimeDelta
    prioritize_duration: bool = True

    @property
    def loops(self) -> int:
        if self.interval == timedelta(0):
            return -1
        return self.duration // self.interval + 1


SinglePhaseTimePlan = Union[TIntervalDuration, TIntervalLoops, TDurationLoops]


class MultiPhaseTimePlan(TimePlan):
    """Time sequence composed of multiple phases.

    Attributes
    ----------
    phases : Sequence[TIntervalDuration | TIntervalLoops | TDurationLoops]
        Sequence of time plans.
    """

    phases: Sequence[SinglePhaseTimePlan]

    def deltas(self) -> Iterator[timedelta]:
        accum = timedelta(0)
        yield accum
        for phase in self.phases:
            for i, td in enumerate(phase.deltas()):
                # skip the first timepoint of later phases
                if i == 0 and td == timedelta(0):
                    continue
                yield td + accum
            accum += td

    def num_timepoints(self) -> int:
        # TODO: is this correct?
        return sum(phase.loops for phase in self.phases) - 1


AnyTimePlan = Union[MultiPhaseTimePlan, SinglePhaseTimePlan]
