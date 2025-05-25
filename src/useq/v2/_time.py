from collections.abc import Generator, Iterator, Sequence
from datetime import timedelta
from typing import TYPE_CHECKING, Annotated, Union, cast

from pydantic import BeforeValidator, Field, PlainSerializer, field_validator

from useq._base_model import FrozenModel
from useq._utils import Axis
from useq.v2._axis_iterator import AxisIterable

if TYPE_CHECKING:
    from collections.abc import Mapping

    from useq._mda_event import MDAEvent

# slightly modified so that we can accept dict objects as input
# and serialize to total_seconds
TimeDelta = Annotated[
    timedelta,
    BeforeValidator(lambda v: timedelta(**v) if isinstance(v, dict) else v),
    PlainSerializer(lambda td: cast("timedelta", td).total_seconds()),
]


class TimePlan(AxisIterable[float], FrozenModel):
    axis_key: str = Field(default=Axis.TIME, frozen=True, init=False)
    prioritize_duration: bool = False  # or prioritize num frames

    def _interval_s(self) -> float:
        """Return the interval in seconds.

        This is used to calculate the time between frames.
        """
        return self.interval.total_seconds()  # type: ignore

    def contribute_to_mda_event(
        self, value: float, index: "Mapping[str, int]"
    ) -> "MDAEvent.Kwargs":
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


class _SizedTimePlan(TimePlan):
    loops: int = Field(..., gt=0)

    def __len__(self) -> int:
        return self.loops

    def iter(self) -> Iterator[float]:
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

    duration: TimeDelta
    loops: int = Field(..., gt=0)

    # FIXME: add to pydantic type hint
    @field_validator("duration")
    @classmethod
    def _validate_duration(cls, v: timedelta) -> timedelta:
        if v.total_seconds() < 0:
            raise ValueError("Duration must be non-negative")
        return v

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
    duration: TimeDelta | None = None
    prioritize_duration: bool = True

    def iter(self) -> Iterator[float]:
        duration_s = self.duration.total_seconds() if self.duration else None
        interval_s = self.interval.total_seconds()
        t = 0.0
        # when `duration_s` is None, the `or` makes it always True → infinite;
        # otherwise it stops once t > duration_s
        while duration_s is None or t <= duration_s:
            yield t
            t += interval_s


# Type aliases for single-phase time plans


SinglePhaseTimePlan = Union[TIntervalDuration, TIntervalLoops, TDurationLoops]


class MultiPhaseTimePlan(TimePlan):
    """Time sequence composed of multiple phases.

    Attributes
    ----------
    phases : Sequence[TIntervalDuration | TIntervalLoops | TDurationLoops]
        Sequence of time plans.
    """

    phases: Sequence[SinglePhaseTimePlan]

    def iter(self) -> Generator[float, bool | None, None]:
        """Yield the global elapsed time over multiple plans.

        and allow `.send(True)` to skip to the next phase.
        """
        offset = 0.0
        for phase in self.phases:
            last_t = 0.0
            phase_iter = phase.iter()
            while True:
                try:
                    t = next(phase_iter)
                except StopIteration:
                    break
                last_t = t
                # here `force = yield offset + t` allows the caller to do
                #    gen = plan.iter()
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


AnyTimePlan = Union[MultiPhaseTimePlan, SinglePhaseTimePlan]
