from __future__ import annotations

from typing import TYPE_CHECKING, Literal, NamedTuple, TypeVar

from pydantic import validator

import useq

if TYPE_CHECKING:
    from typing import Final

    from useq._time import SinglePhaseTimePlan


KT = TypeVar("KT")
VT = TypeVar("VT")


# could be an enum, but this more easily allows Axis.Z to be a string
class Axis:
    """Recognized axis names."""

    TIME: Final[Literal["t"]] = "t"
    POSITION: Final[Literal["p"]] = "p"
    GRID: Final[Literal["g"]] = "g"
    CHANNEL: Final[Literal["c"]] = "c"
    Z: Final[Literal["z"]] = "z"


# note: order affects the default axis_order in MDASequence
AXES: Final[tuple[str, ...]] = (
    Axis.TIME,
    Axis.POSITION,
    Axis.GRID,
    Axis.CHANNEL,
    Axis.Z,
)


def list_cast(field: str) -> classmethod:
    v = validator(field, pre=True, allow_reuse=True, check_fields=False)
    return v(list)


class TimeEstimate(NamedTuple):
    """Record of time estimation results.

    Attributes
    ----------
    total_duration : float
        Estimated total duration of the experiment, in seconds.
    per_t_duration : float
        Estimated duration of a single timepoint, in seconds.
    time_interval_exceeded : bool
        Whether the time interval between timepoints is shorter than the time it takes
        to acquire the data.  In a multi-phase time plan, this is True if any of the
        phases have this property.
    """

    total_duration: float
    per_t_duration: float
    time_interval_exceeded: bool


def estimate_sequence_duration(seq: useq.MDASequence) -> TimeEstimate:
    n_positions = len(seq.stage_positions or [0])
    num_z = seq.z_plan.num_positions() if seq.z_plan else 1
    num_grid = seq.grid_plan.num_positions() if seq.grid_plan else 1

    # NOTE:
    # technically some channels might have ch.aquire_every > 1
    # we don't account for that here.  The ONLY case where this will lead to erroneous
    # estimates is when the time plan interval is shorter than the time it takes to
    # acquire the data (i.e. when `time_interval_exceeded` is True`).  In that case,
    # we will overestimate the total time a little bit.
    s_per_timepoint: float = 0.0
    for ch in seq.channels:
        # note, using 1ms instead of 0ms when channel exposure has been omitted
        # this will likely underestimate the real time (which will then be determined
        # by the "current" exposure time), but it's better than 0 or a higher magic num.
        exposure_s = (ch.exposure or 1) / 1000
        num_ch_z = num_z if ch.do_stack else 1
        s_per_timepoint += exposure_s * n_positions * num_ch_z * num_grid

    t_interval_exceeded = False
    if tplan := seq.time_plan:
        phases = tplan.phases if isinstance(tplan, useq.MultiPhaseTimePlan) else [tplan]
        tot_duration = 0.0
        for phase in phases:
            phase_duration, exceeded = _time_phase_duration(phase, s_per_timepoint)
            tot_duration += phase_duration
            t_interval_exceeded = t_interval_exceeded or exceeded
    else:
        tot_duration = s_per_timepoint

    return TimeEstimate(tot_duration, s_per_timepoint, t_interval_exceeded)


def _time_phase_duration(
    phase: SinglePhaseTimePlan, s_per_timepoint: float
) -> tuple[float, bool]:
    time_interval_s = phase.interval.total_seconds()

    if time_interval_exceeded := (s_per_timepoint > time_interval_s):
        # the real interval between timepoints will be the greater of the
        # prescribed interval (according to the time plan) and the time it takes
        # to actually acquire the data
        time_interval_s = s_per_timepoint

    tot_duration = (phase.num_timepoints() - 1) * time_interval_s + s_per_timepoint
    return tot_duration, time_interval_exceeded
