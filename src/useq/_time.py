from collections.abc import Iterator, Sequence
from datetime import timedelta
from typing import Annotated, Any, Optional, Union

from pydantic import (
    BeforeValidator,
    Field,
    PlainSerializer,
    model_validator,
)

from useq._base_model import FrozenModel


def _validate_delta(v: Any) -> timedelta:
    if isinstance(v, dict):
        v = timedelta(**v)
    elif isinstance(v, (str, int, float)):
        v = timedelta(seconds=float(v))  # assuming ISO 8601 or similar

    if not isinstance(v, timedelta):
        raise TypeError(f"Expected timedelta, str, int, or dict, got {type(v)}")
    if v.total_seconds() < 0:
        raise ValueError("Duration must be non-negative")
    return v


# slightly modified so that we can accept dict objects as input
# and serialize to total_seconds
NonNegativeTimeDelta = Annotated[
    timedelta,
    BeforeValidator(_validate_delta),
    PlainSerializer(lambda td: td.total_seconds()),
]


class TimePlan(FrozenModel):
    # TODO: probably needs to be implemented by engine
    prioritize_duration: bool = False  # or prioritize num frames

    def __iter__(self) -> Iterator[float]:  # type: ignore
        for td in self.deltas():
            yield td.total_seconds()

    def num_timepoints(self) -> int:
        return len(self)

    def __len__(self) -> int:
        return self.loops  # type: ignore  # TODO

    def deltas(self) -> Iterator[timedelta]:
        current = timedelta(0)
        for _ in range(self.loops):  # type: ignore  # TODO
            yield current
            current += self.interval  # type: ignore  # TODO


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

    interval: NonNegativeTimeDelta
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

    duration: NonNegativeTimeDelta
    loops: int = Field(..., gt=0)

    @property
    def interval(self) -> timedelta:
        if self.loops == 1:
            # Special case: with only 1 loop, interval is meaningless
            # Return zero to indicate instant
            return timedelta(0)
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

    interval: NonNegativeTimeDelta
    duration: Optional[NonNegativeTimeDelta] = None
    prioritize_duration: bool = True

    def __iter__(self) -> Iterator[float]:  # type: ignore[override]
        duration_s = self.duration.total_seconds() if self.duration else None
        interval_s = self.interval.total_seconds()
        t = 0.0
        # when `duration_s` is None, the `or` makes it always True → infinite;
        # otherwise it stops once t > duration_s
        while duration_s is None or t <= duration_s:
            yield t
            t += interval_s

    @property
    def loops(self) -> int:
        return len(self)

    def __len__(self) -> int:
        """Return the number of time points in this plan."""
        if self.duration is None:
            raise ValueError("Cannot determine length of infinite time plan")
        return int(self.duration.total_seconds() / self.interval.total_seconds()) + 1


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
            td = None
            for i, td in enumerate(phase.deltas()):
                # skip the first timepoint of later phases
                if i == 0 and td == timedelta(0):
                    continue
                yield td + accum
            if td is not None:
                accum += td

    def __len__(self) -> int:
        """Return the number of time points in this plan."""
        phase_sum = sum(len(phase) for phase in self.phases)
        # subtract 1 for the first time point of each phase
        # except the first one
        return phase_sum - len(self.phases) + 1

    @model_validator(mode="before")
    @classmethod
    def _cast(cls, value: Any) -> Any:
        if isinstance(value, Sequence) and not isinstance(value, str):
            value = {"phases": value}
        return value


AnyTimePlan = Union[MultiPhaseTimePlan, SinglePhaseTimePlan]
