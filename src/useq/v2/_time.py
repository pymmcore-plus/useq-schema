from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Annotated, Any, cast

from pydantic import (
    AfterValidator,
    BeforeValidator,
    Field,
    PlainSerializer,
    model_validator,
)
from typing_extensions import deprecated

from useq._base_model import FrozenModel
from useq._enums import Axis
from useq.v2._axes_iterator import AxisIterable

if TYPE_CHECKING:
    from collections.abc import Generator, Iterator, Mapping

    from useq._mda_event import MDAEvent

# slightly modified so that we can accept dict objects as input
# and serialize to total_seconds
TimeDelta = Annotated[
    timedelta,
    BeforeValidator(lambda v: timedelta(**v) if isinstance(v, dict) else v),
    PlainSerializer(lambda td: cast("timedelta", td).total_seconds()),
]


def _ensure_non_negative(td: timedelta) -> timedelta:
    if td.total_seconds() < 0:
        raise ValueError("TimeDelta must be non-negative")
    return td


NonNegativeTimeDelta = Annotated[TimeDelta, AfterValidator(_ensure_non_negative)]


class TimePlan(AxisIterable[float], FrozenModel):
    axis_key: str = Field(default=Axis.TIME, frozen=True, init=False)
    prioritize_duration: bool = False  # or prioritize num frames

    def _interval_s(self) -> float:
        """Return the interval in seconds.

        This is used to calculate the time between frames.
        """
        return self.interval.total_seconds()  # type: ignore

    def contribute_to_mda_event(
        self, value: float, index: Mapping[str, int]
    ) -> MDAEvent.Kwargs:
        """Contribute time data to the event being built.

        Parameters
        ----------
        value : float
            The time value for this iteration.
        index : Mapping[str, int]
            Current axis indices.

        Returns
        -------
        dict
            Event data to be merged into the MDAEvent.
        """
        return {"min_start_time": value}

    @deprecated(
        "num_timepoints() is deprecated, use len(time_plan) instead.",
        category=UserWarning,
        stacklevel=2,
    )
    def num_timepoints(self) -> int:
        """Return the number of time points in this plan.

        This is deprecated and will be removed in a future version.
        Use `len()` instead.
        """
        return len(self)  # type: ignore


class _SizedTimePlan(TimePlan):
    loops: int = Field(..., gt=0)

    def __len__(self) -> int:
        return self.loops

    def __iter__(self) -> Iterator[float]:  # type: ignore[override]
        interval_s: float = self._interval_s()
        for i in range(self.loops):
            yield i * interval_s


class TIntervalLoops(_SizedTimePlan):
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


class TDurationLoops(_SizedTimePlan):
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
    duration : str | timedelta | None
        Total duration of sequence.  If `None`, the sequence will be infinite.
    prioritize_duration : bool
        If `True`, instructs engine to prioritize duration over number of frames in case
        of conflict. By default, `True`.
    """

    interval: TimeDelta
    duration: NonNegativeTimeDelta | None = None
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

    def __len__(self) -> int:
        """Return the number of time points in this plan."""
        if self.duration is None:
            raise ValueError("Cannot determine length of infinite time plan")
        return int(self.duration.total_seconds() / self.interval.total_seconds()) + 1


# Type aliases for single-phase time plans


SinglePhaseTimePlan = TIntervalDuration | TIntervalLoops | TDurationLoops


class MultiPhaseTimePlan(TimePlan):
    """Time sequence composed of multiple phases.

    Attributes
    ----------
    phases : Sequence[TIntervalDuration | TIntervalLoops | TDurationLoops]
        Sequence of time plans.
    """

    phases: list[SinglePhaseTimePlan]

    def __iter__(self) -> Generator[float, bool | None, None]:  # type: ignore[override]
        """Yield the global elapsed time over multiple plans.

        and allow `.send(True)` to skip to the next phase.
        """
        offset = 0.0
        for ip, phase in enumerate(self.phases):
            last_t = 0.0
            phase_iter = iter(phase)
            if ip != 0:
                # skip the first time point of all the phases except the first
                next(phase_iter)
            while True:
                try:
                    t = next(phase_iter)
                except StopIteration:
                    break
                last_t = t
                # here `force = yield offset + t` allows the caller to do
                #    gen = iter(plan)
                #    next(gen)  # start
                #    gen.send(True)  # force the next phase
                force = yield offset + t
                if force:
                    break

            # advance our offset to the end of this phase
            if (duration_td := phase.duration) is not None:
                offset += duration_td.total_seconds()
            else:
                # infinite phase that we broke out of
                # leave offset where it was + last_t
                offset += last_t

    def __len__(self) -> int:
        """Return the number of time points in this plan."""
        phase_sum = sum(len(phase) for phase in self.phases)
        # subtract 1 for the first time point of each phase
        # except the first one
        return phase_sum - len(self.phases) + 1

    @model_validator(mode="before")
    @classmethod
    def _cast_list(cls, values: Any) -> Any:
        """Cast the phases to a list of time plans."""
        if isinstance(values, (list, tuple)):
            values = {"phases": values}
        return values


AnyTimePlan = MultiPhaseTimePlan | SinglePhaseTimePlan
