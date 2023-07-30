from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any, Dict, Iterator, Optional, Sequence, Tuple
from uuid import UUID, uuid4
from warnings import warn

import numpy as np
from pydantic import Field, PrivateAttr, root_validator, validator

from useq._base_model import UseqModel
from useq._channel import Channel  # noqa: TCH001
from useq._grid import AnyGridPlan, GridPosition  # noqa: TCH001
from useq._hardware_autofocus import AnyAutofocusPlan, AxesBasedAF
from useq._iter_sequence import iter_sequence
from useq._mda_event import MDAEvent
from useq._position import Position
from useq._time import AnyTimePlan  # noqa: TCH001
from useq._utils import AXES, Axis, TimeEstimate, estimate_sequence_duration
from useq._z import AnyZPlan  # noqa: TCH001

Undefined = object()

if TYPE_CHECKING:
    from useq.pycromanager import PycroManagerEvent


class MDASequence(UseqModel):
    """A sequence of MDA (Multi-Dimensional Acquisition) events.

    This is the core object in the `useq` library, and is used define a sequence of
    events to be run on a microscope. It object may be constructed manually, or from
    file (e.g. json or yaml).

    The object itself acts as an iterator for [`useq.MDAEvent`][] objects:

    Attributes
    ----------
    metadata : dict
        A dictionary of user metadata to be stored with the sequence.
    axis_order : str
        The order of the axes in the sequence. Must be a permutation of `"tpgcz"`. The
        default is `"tpgcz"`.
    stage_positions : tuple[Position, ...]
        The stage positions to visit. (each with `x`, `y`, `z`, `name`, and `sequence`,
        all of which are optional).
    grid_plan : GridFromEdges | GridRelative | None
        The grid plan to follow. One of `GridFromEdges`, `GridRelative` or `None`.
    channels : tuple[Channel, ...]
        The channels to acquire. see `Channel`.
    time_plan : MultiPhaseTimePlan | TIntervalDuration | TIntervalLoops \
        | TDurationLoops | None
        The time plan to follow. One of `TIntervalDuration`, `TIntervalLoops`,
        `TDurationLoops`, `MultiPhaseTimePlan`, or `None`
    z_plan : ZTopBottom | ZRangeAround | ZAboveBelow | ZRelativePositions | \
        ZAbsolutePositions | None
        The z plan to follow. One of `ZTopBottom`, `ZRangeAround`, `ZAboveBelow`,
        `ZRelativePositions`, `ZAbsolutePositions`, or `None`.
    uid : UUID
        A read-only unique identifier (uuid version 4) for the sequence. This will be
        generated, do not set.
    autofocus_plan : AxesBasedAF | None
        The hardware autofocus plan to follow. One of `AxesBasedAF` or `None`.

    Examples
    --------
    >>> from useq import MDASequence, Position, Channel, TIntervalDuration
    >>> seq = MDASequence(
    ...     time_plan={"interval": 0.1, "loops": 2},
    ...     stage_positions=[(1, 1, 1)],
    ...     grid_plan={"rows": 2, "cols": 2},
    ...     z_plan={"range": 3, "step": 1},
    ...     channels=[{"config": "DAPI", "exposure": 1}]
    ... )
    >>> print(seq)
    Multi-Dimensional Acquisition ▶ nt: 2, np: 1, nc: 1, nz: 4, ng: 4

    >>> for event in seq:
    ...     print(event)

    >>> print(seq.yaml())
    channels:
    - config: DAPI
      exposure: 1.0
    grid_plan:
      columns: 2
      rows: 2
    stage_positions:
    - x: 1.0
      y: 1.0
      z: 1.0
    time_plan:
      interval: '0:00:00.100000'
      loops: 2
    z_plan:
      range: 3.0
      step: 1.0
    """

    metadata: Dict[str, Any] = Field(default_factory=dict)
    axis_order: str = "".join(AXES)
    stage_positions: Tuple[Position, ...] = Field(default_factory=tuple)
    grid_plan: Optional[AnyGridPlan] = None
    channels: Tuple[Channel, ...] = Field(default_factory=tuple)
    time_plan: Optional[AnyTimePlan] = None
    z_plan: Optional[AnyZPlan] = None
    autofocus_plan: Optional[AnyAutofocusPlan] = None

    _uid: UUID = PrivateAttr(default_factory=uuid4)
    _sizes: Optional[Dict[str, int]] = PrivateAttr(default=None)

    @property
    def uid(self) -> UUID:
        """A unique identifier for this sequence."""
        return self._uid

    def set_fov_size(self, fov_size: Tuple[float, float]) -> None:
        """Set the field of view size.

        FOV is used to calculate the number of positions in a grid plan.

        !!! warning "DEPRECATED"

            Set `fov_width` and `fov_height` directly on the `grid_plan` instead.
        """
        warn(
            "set_fov_size is deprecated and will be removed. Please use:\n"
            "  new_plan = self.grid_plan.replace(fov_width=..., fov_height=...)\n"
            "  seq = seq.replace(grid_plan=new_plan)",
            DeprecationWarning,
            stacklevel=2,
        )
        if self.grid_plan is None:  # pragma: no cover
            return
        # hack to get around immutability
        new_plan = self.grid_plan.replace(fov_width=fov_size[0], fov_height=fov_size[1])
        object.__setattr__(self, "grid_plan", new_plan)

    def __hash__(self) -> int:
        return hash(self.uid)

    @validator("z_plan", pre=True)
    def _validate_zplan(cls, v: Any) -> Optional[dict]:
        return v or None

    @validator("time_plan", pre=True)
    def _validate_time_plan(cls, v: Any) -> Optional[dict]:
        return {"phases": v} if isinstance(v, (tuple, list)) else v or None

    @validator("stage_positions", pre=True)
    def _validate_positions(cls, v: Any) -> Any:
        if isinstance(v, np.ndarray):
            if v.ndim == 1:
                return [v]
            elif v.ndim == 2:
                return list(v)
        return v

    @validator("axis_order", pre=True)
    def _validate_axis_order(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise TypeError(f"acquisition order must be a string, got {type(v)}")
        order = v.lower()
        extra = {x for x in order if x not in AXES}
        if extra:
            raise ValueError(
                f"Can only iterate over axes: {AXES!r}. Got extra: {extra}"
            )
        if len(set(order)) < len(order):
            raise ValueError(f"Duplicate entries found in acquisition order: {order}")

        return order

    @root_validator
    def _validate_mda(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if "axis_order" in values:
            values["axis_order"] = cls._check_order(
                values["axis_order"],
                z_plan=values.get("z_plan"),
                stage_positions=values.get("stage_positions", ()),
                channels=values.get("channels", ()),
                grid_plan=values.get("grid_plan"),
                autofocus_plan=values.get("autofocus_plan"),
            )
        return values

    def __eq__(self, other: Any) -> bool:
        """Return `True` if two `MDASequences` are equal (uid is excluded)."""
        if isinstance(other, MDASequence):
            return bool(self.dict(exclude={"uid"}) == other.dict(exclude={"uid"}))
        else:
            return False

    @staticmethod
    def _check_order(
        order: str,
        z_plan: Optional[AnyZPlan] = None,
        stage_positions: Sequence[Position] = (),
        channels: Sequence[Channel] = (),
        grid_plan: Optional[AnyGridPlan] = None,
        autofocus_plan: Optional[AnyAutofocusPlan] = None,
    ) -> str:
        if (
            Axis.Z in order
            and Axis.POSITION in order
            and order.index(Axis.Z) < order.index(Axis.POSITION)
            and z_plan
            and any(
                p.sequence.z_plan for p in stage_positions if p.sequence is not None
            )
        ):
            raise ValueError(
                f"{Axis.Z!r} cannot precede {Axis.POSITION!r} in acquisition order if "
                "any position specifies a z_plan"
            )

        if (
            Axis.CHANNEL in order
            and Axis.TIME in order
            and any(c.acquire_every > 1 for c in channels)
            and order.index(Axis.CHANNEL) < order.index(Axis.TIME)
        ):
            warn(
                f"Channels with skipped frames detected, but {Axis.CHANNEL!r} precedes "
                "{TIME!r} in the acquisition order: may not yield intended results.",
                stacklevel=2,
            )

        if (
            Axis.GRID in order
            and Axis.POSITION in order
            and grid_plan
            and not grid_plan.is_relative
            and len(stage_positions) > 1
        ):
            sub_position_grid_plans = [
                p
                for p in stage_positions
                if p.sequence is not None and p.sequence.grid_plan
            ]
            if len(stage_positions) - len(sub_position_grid_plans) > 1:
                warn(
                    "Global grid plan will override sub-position grid plans.",
                    stacklevel=2,
                )

        if (
            Axis.POSITION in order
            and stage_positions
            and any(
                p.sequence.stage_positions
                for p in stage_positions
                if p.sequence is not None
            )
        ):
            raise ValueError(
                "Currently, a Position sequence cannot have multiple stage positions!"
            )

        # Cannot use autofocus plan with absolute z_plan
        if Axis.Z in order and z_plan and not z_plan.is_relative:
            err = "Absolute Z positions cannot be used with autofocus plan."
            if isinstance(autofocus_plan, AxesBasedAF):
                raise ValueError(err)
            for p in stage_positions:
                if p.sequence is not None and p.sequence.autofocus_plan:
                    raise ValueError(err)

        return order

    def __str__(self) -> str:
        return "Multi-Dimensional Acquisition ▶ " + ", ".join(self.sizes)

    @property
    def shape(self) -> Tuple[int, ...]:
        """Return the shape of this sequence.

        !!! note
            This doesn't account for jagged arrays, like channels that exclude z
            stacks or skip timepoints.
        """
        return tuple(s for s in self.sizes.values() if s)

    @property
    def sizes(self) -> Dict[str, int]:
        """Mapping of axis name to size of that axis."""
        if self._sizes is None:
            self._sizes = {k: len(list(self.iter_axis(k))) for k in self.axis_order}
        return self._sizes

    @property
    def used_axes(self) -> str:
        """Single letter string of axes used in this sequence, e.g. `ztc`."""
        return "".join(k for k in self.axis_order if self.sizes[k])

    def iter_axis(
        self, axis: str
    ) -> Iterator[Position | Channel | float | GridPosition]:
        """Iterate over the positions or items of a given axis."""
        plan = {
            Axis.TIME: self.time_plan,
            Axis.POSITION: self.stage_positions,
            Axis.Z: self.z_plan,
            Axis.CHANNEL: self.channels,
            Axis.GRID: self.grid_plan,
        }[axis]
        if plan:
            yield from plan

    def __iter__(self) -> Iterator[MDAEvent]:  # type: ignore [override]
        """Same as `iter_events`. Supports `for event in sequence: ...` syntax."""
        yield from self.iter_events()

    def iter_events(self) -> Iterator[MDAEvent]:
        """Iterate over all events in the MDA sequence.

        See source of [useq._mda_sequence.iter_sequence][] for details on how
        events are constructed and yielded.

        Yields
        ------
        MDAEvent
            Each event in the MDA sequence.
        """
        return iter_sequence(self)

    def to_pycromanager(self) -> list[PycroManagerEvent]:
        warnings.warn(
            "useq.MDASequence.to_pycromanager() is deprecated and will be removed in a "
            "future version. Useq useq.pycromanager.to_pycromanager(seq) instead.",
            FutureWarning,
            stacklevel=2,
        )
        from useq.pycromanager import to_pycromanager

        return to_pycromanager(self)

    def estimate_duration(self) -> TimeEstimate:
        """Estimate duration and other timing issues of an MDASequence.

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
        return estimate_sequence_duration(self)


MDAEvent.update_forward_refs(MDASequence=MDASequence)
Position.update_forward_refs(MDASequence=MDASequence)
