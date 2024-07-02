from __future__ import annotations

import re
from datetime import timedelta
from typing import TYPE_CHECKING, Literal, NamedTuple, TypeVar

if TYPE_CHECKING:
    from typing import Final

    from typing_extensions import TypeGuard

    import useq
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

    def __add__(self, other: object) -> TimeEstimate:
        """Add two TimeEstimates."""
        if not isinstance(other, TimeEstimate):
            return NotImplemented  # pragma: no cover
        return TimeEstimate(
            self.total_duration + other.total_duration,
            self.per_t_duration + other.per_t_duration,
            self.time_interval_exceeded or other.time_interval_exceeded,
        )


def estimate_sequence_duration(seq: useq.MDASequence) -> TimeEstimate:
    """Estimate the duration of an MDASequence.

    Notable mis-estimations may include:
    - when the time interval is shorter than the time it takes to acquire the data
      and any of the channels have `acquire_every` > 1
    - when channel exposure times are omitted. In this case, we assume 1ms exposure.

    Returns
    -------
    TimeEstimate
        A named 3-tuple with the following fields:
        - total_duration: float
            Estimated total duration of the experiment, in seconds.
        - per_t_duration: float
            Estimated duration of a single timepoint, in seconds.
        - time_interval_exceeded: bool
            Whether the time interval between timepoints is shorter than the time it
            takes to acquire the data
    """
    stage_positions = tuple(seq.stage_positions)
    if not any(_has_axes(p.sequence) for p in stage_positions):
        # the simple case: no axes to iterate over in any of the positions
        return _estimate_simple_sequence_duration(seq)

    estimate = TimeEstimate(0.0, 0.0, False)
    parent_seq = seq.replace(stage_positions=[])
    for p in stage_positions:
        if not _has_axes(p.sequence):
            sub_seq = parent_seq
        else:
            updates = {
                field: getattr(parent_seq, field)
                for field in ("time_plan", "z_plan", "grid_plan", "channels")
                if getattr(parent_seq, field) and not getattr(p.sequence, field)
            }
            sub_seq = p.sequence.model_copy(update=updates)
        estimate += _estimate_simple_sequence_duration(sub_seq)
    return estimate


def _estimate_simple_sequence_duration(seq: useq.MDASequence) -> TimeEstimate:
    """Estimate the duration of an MDASequence with no sub-pos axes to iterate over.

    Helper function for estimate_sequence_duration.
    """
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
        phases = tplan.phases if hasattr(tplan, "phases") else [tplan]
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
    """Calculate duration for a single time plan phase."""
    time_interval_s = phase.interval.total_seconds()

    if time_interval_exceeded := (s_per_timepoint > time_interval_s):
        # the real interval between timepoints will be the greater of the
        # prescribed interval (according to the time plan) and the time it takes
        # to actually acquire the data
        time_interval_s = s_per_timepoint

    tot_duration = (phase.num_timepoints() - 1) * time_interval_s + s_per_timepoint
    return tot_duration, time_interval_exceeded


def _has_axes(seq: useq.MDASequence | None) -> TypeGuard[useq.MDASequence]:
    """Return True if the sequence has anything to iterate over."""
    if seq is None:
        return False
    return bool(
        seq.time_plan is not None
        or seq.stage_positions
        or seq.z_plan is not None
        or seq.channels
        or seq.grid_plan is not None
    )


# vendored from pydantic v1
def parse_duration(value: str | bytes | int | float) -> timedelta:  # pragma: no cover
    """
    Parse a duration int/float/string and return a datetime.timedelta.

    The preferred format for durations in Django is '%d %H:%M:%S.%f'.

    Also supports ISO 8601 representation.
    """
    if isinstance(value, timedelta):
        return value

    if isinstance(value, (int, float)):
        # below code requires a string
        value = f"{value:f}"
    elif isinstance(value, bytes):
        value = value.decode()

    try:
        match = standard_duration_re.match(value) or iso8601_duration_re.match(value)
    except TypeError:
        raise TypeError(
            "invalid type; expected timedelta, string, bytes, int or float"
        ) from None

    if not match:
        raise ValueError(f"{value!r} is not a valid duration")

    kw = match.groupdict()
    sign = -1 if kw.pop("sign", "+") == "-" else 1
    if kw.get("microseconds"):
        kw["microseconds"] = kw["microseconds"].ljust(6, "0")

    if kw.get("seconds") and kw.get("microseconds") and kw["seconds"].startswith("-"):
        kw["microseconds"] = "-" + kw["microseconds"]

    kw_ = {k: float(v) for k, v in kw.items() if v is not None}

    return sign * timedelta(**kw_)


standard_duration_re = re.compile(
    r"^"
    r"(?:(?P<days>-?\d+) (days?, )?)?"
    r"((?:(?P<hours>-?\d+):)(?=\d+:\d+))?"
    r"(?:(?P<minutes>-?\d+):)?"
    r"(?P<seconds>-?\d+)"
    r"(?:\.(?P<microseconds>\d{1,6})\d{0,6})?"
    r"$"
)

# Support the sections of ISO 8601 date representation that are accepted by timedelta
iso8601_duration_re = re.compile(
    r"^(?P<sign>[-+]?)"
    r"P"
    r"(?:(?P<days>\d+(.\d+)?)D)?"
    r"(?:T"
    r"(?:(?P<hours>\d+(.\d+)?)H)?"
    r"(?:(?P<minutes>\d+(.\d+)?)M)?"
    r"(?:(?P<seconds>\d+(.\d+)?)S)?"
    r")?"
    r"$"
)
