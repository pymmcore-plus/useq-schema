from __future__ import annotations

from typing import TYPE_CHECKING, Union

from pydantic import Field
from typing_extensions import deprecated

from useq import _time
from useq._enums import Axis
from useq.v2._axes_iterator import AxisIterable

if TYPE_CHECKING:
    from collections.abc import Generator, Mapping

    from useq._mda_event import MDAEvent


class TimePlan(_time.TimePlan, AxisIterable[float]):
    axis_key: str = Field(default=Axis.TIME, frozen=True, init=False)

    def contribute_event_kwargs(
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
        return len(self)


class TIntervalLoops(_time.TIntervalLoops, TimePlan): ...


class TDurationLoops(_time.TDurationLoops, TimePlan): ...


class TIntervalDuration(_time.TIntervalDuration, TimePlan): ...


SinglePhaseTimePlan = Union[TIntervalDuration, TIntervalLoops, TDurationLoops]


class MultiPhaseTimePlan(TimePlan, _time.MultiPhaseTimePlan):
    phases: list[SinglePhaseTimePlan]  # pyright: ignore[reportIncompatibleVariableOverride]

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


AnyTimePlan = Union[MultiPhaseTimePlan, SinglePhaseTimePlan]
