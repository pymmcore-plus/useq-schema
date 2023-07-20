from __future__ import annotations

from itertools import product
from typing import Any, Dict, Iterator, Optional, Sequence, Tuple, cast
from uuid import UUID, uuid4
from warnings import warn

import numpy as np
from pydantic import Field, PrivateAttr, root_validator, validator
from typing_extensions import TypedDict

from useq._base_model import UseqModel
from useq._channel import Channel  # noqa: TCH001
from useq._grid import AnyGridPlan, GridPosition  # noqa: TCH001
from useq._hardware_autofocus import AnyAutofocusPlan, AxesBasedAF
from useq._mda_event import Channel as EventChannel
from useq._mda_event import MDAEvent
from useq._position import Position
from useq._time import AnyTimePlan  # noqa: TCH001
from useq._z import AnyZPlan  # noqa: TCH001

TIME = "t"
CHANNEL = "c"
POSITION = "p"
Z = "z"
GRID = "g"
INDICES = (TIME, POSITION, GRID, CHANNEL, Z)

Undefined = object()


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
    axis_order: str = "".join(INDICES)
    stage_positions: Tuple[Position, ...] = Field(default_factory=tuple)
    grid_plan: Optional[AnyGridPlan] = None
    channels: Tuple[Channel, ...] = Field(default_factory=tuple)
    time_plan: Optional[AnyTimePlan] = None
    z_plan: Optional[AnyZPlan] = None
    autofocus_plan: Optional[AnyAutofocusPlan] = None

    _uid: UUID = PrivateAttr(default_factory=uuid4)
    _length: Optional[int] = PrivateAttr(default=None)
    _fov_size: Tuple[float, float] = PrivateAttr(default=(1, 1))

    @property
    def uid(self) -> UUID:
        """A unique identifier for this sequence."""
        return self._uid

    def set_fov_size(self, fov_size: Tuple[float, float]) -> None:
        """Set the field of view size.

        This is used to calculate the number of positions in a grid plan.
        """
        self._fov_size = fov_size

    def __hash__(self) -> int:
        return hash(self.uid)

    @validator("z_plan", pre=True)
    def validate_zplan(cls, v: Any) -> Optional[dict]:
        return v or None

    @validator("time_plan", pre=True)
    def validate_time_plan(cls, v: Any) -> Optional[dict]:
        return {"phases": v} if isinstance(v, (tuple, list)) else v or None

    @validator("stage_positions", pre=True)
    def validate_positions(cls, v: Any) -> Any:
        if isinstance(v, np.ndarray):
            if v.ndim == 1:
                return [v]
            elif v.ndim == 2:
                return list(v)
        return v

    @validator("axis_order", pre=True)
    def validate_axis_order(cls, v: Any) -> str:
        if not isinstance(v, str):
            raise TypeError(f"acquisition order must be a string, got {type(v)}")
        order = v.lower()
        extra = {x for x in order if x not in INDICES}
        if extra:
            raise ValueError(
                f"Can only iterate over axes: {INDICES!r}. Got extra: {extra}"
            )
        if len(set(order)) < len(order):
            raise ValueError(f"Duplicate entries found in acquisition order: {order}")

        return order

    @root_validator
    def validate_mda(cls, values: Dict[str, Any]) -> Dict[str, Any]:
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
            Z in order
            and POSITION in order
            and order.index(Z) < order.index(POSITION)
            and z_plan
            and any(p.sequence.z_plan for p in stage_positions if p.sequence)
        ):
            raise ValueError(
                f"{Z!r} cannot precede {POSITION!r} in acquisition order if "
                "any position specifies a z_plan"
            )

        if (
            CHANNEL in order
            and TIME in order
            and any(c.acquire_every > 1 for c in channels)
            and order.index(CHANNEL) < order.index(TIME)
        ):
            warn(
                f"Channels with skipped frames detected, but {CHANNEL!r} precedes "
                "{TIME!r} in the acquisition order: may not yield intended results.",
                stacklevel=2,
            )

        if (
            GRID in order
            and POSITION in order
            and grid_plan
            and not grid_plan.is_relative
            and len(stage_positions) > 1
        ):
            sub_position_grid_plans = [
                p for p in stage_positions if p.sequence and p.sequence.grid_plan
            ]
            if len(stage_positions) - len(sub_position_grid_plans) > 1:
                warn(
                    "Global grid plan will override sub-position grid plans.",
                    stacklevel=2,
                )

        if (
            POSITION in order
            and stage_positions
            and any(p.sequence.stage_positions for p in stage_positions if p.sequence)
        ):
            raise ValueError(
                "Currently, a Position sequence cannot have multiple stage positions!"
            )

        # Cannot use autofocus plan with absolute z_plan
        if Z in order and z_plan and not z_plan.is_relative:
            err = "Absolute Z positions cannot be used with autofocus plan."
            if isinstance(autofocus_plan, AxesBasedAF):
                raise ValueError(err)
            for p in stage_positions:
                if p.sequence is not None and p.sequence.autofocus_plan:
                    raise ValueError(err)

        return order

    def __str__(self) -> str:
        shape = [
            f"n{k.lower()}: {len(list(self.iter_axis(k)))}" for k in self.axis_order
        ]
        return "Multi-Dimensional Acquisition ▶ " + ", ".join(shape)

    def __len__(self) -> int:
        """Return the number of events in this sequence."""
        if self._length is None:
            self._length = len(list(self.iter_events()))
        return self._length

    @property
    def shape(self) -> Tuple[int, ...]:
        """Return the shape of this sequence.

        !!! note
            This doesn't account for jagged arrays, like skipped Z or channel frames.
        """
        return tuple(s for s in self.sizes.values() if s)

    @property
    def sizes(self) -> Dict[str, int]:
        """Mapping of axis to size of that axis."""
        return {k: len(list(self.iter_axis(k))) for k in self.axis_order}

    @property
    def used_axes(self) -> str:
        """Single letter string of axes used in this sequence, e.g. `ztc`."""
        return "".join(k for k in self.axis_order if self.sizes[k])

    def iter_axis(
        self, axis: str
    ) -> Iterator[Position | Channel | float | GridPosition]:
        """Iterate over the events of a given axis."""
        plan = {
            TIME: self.time_plan,
            POSITION: self.stage_positions,
            Z: self.z_plan,
            CHANNEL: self.channels,
            GRID: (
                self.grid_plan.iter_grid_positions(self._fov_size[0], self._fov_size[1])
                if self.grid_plan
                else ()
            ),
        }[axis]
        if plan:
            yield from plan

    def __iter__(self) -> Iterator[MDAEvent]:  # type: ignore [override]
        """Same as `iter_events`. Supports `for event in sequence: ...` syntax."""
        yield from self.iter_events()

    class _SkipFrame(Exception):
        pass

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

    def to_pycromanager(self) -> list[dict]:
        """Convenience to convert this sequence to a list of pycro-manager events.

        See: <https://pycro-manager.readthedocs.io/en/latest/apis.html>
        """
        return [event.to_pycromanager() for event in self]


MDAEvent.update_forward_refs(MDASequence=MDASequence)
Position.update_forward_refs(MDASequence=MDASequence)


class MDAEventDict(TypedDict, total=False):
    index: dict[str, int]
    channel: EventChannel | None
    exposure: float | None
    min_start_time: float | None
    pos_name: str | None
    x_pos: float | None
    y_pos: float | None
    z_pos: float | None
    sequence: MDASequence | None
    properties: list[tuple] | None
    metadata: dict


class PositionDict(TypedDict, total=False):
    x_pos: float
    y_pos: float
    z_pos: float


def iter_sequence(
    sequence: MDASequence,
    *,
    base_event_kwargs: MDAEventDict | None = None,
    event_kwarg_overrides: MDAEventDict | None = None,
    position_offsets: PositionDict | None = None,
) -> Iterator[MDAEvent]:
    """Iterate over all events in the MDA sequence.'.

    !!! note
        This method will usually be used via [`useq.MDASequence.iter_events`][], or by
        simply iterating over the sequence.

    This does the job of iterating over all the frames in the MDA sequence,
    handling the logic of merging all z plans in channels and stage positions
    defined in the plans for each axis.

    The is the most "logic heavy" part of `useq-schema` (the rest of which is
    almost entirely declarative).  This iterator is useful for consuming `MDASequence`
    objects in a python runtime, but it isn't considered a "core" part of the schema.

    Parameters
    ----------
    sequence : MDASequence
        The sequence to iterate over.
    base_event_kwargs : MDAEventDict | None
        A dictionary of "global" kwargs to begin with when building the kwargs passed
        to each MDAEvent.  These will be overriden by event-specific kwargs (e.g. if
        the event specifies a channel, it will be used instead of the
        `base_event_kwargs`.)
    event_kwarg_overrides : MDAEventDict | None
        A dictionary of kwargs that will be applied to all events. Unlike
        `base_event_kwargs`, these kwargs take precedence over any event-specific
        kwargs.
    position_offsets : PositionDict | None
        A dictionary of offsets to apply to each position. This can be used to shift
        all positions in a sub-sequence.  Keys must be one of `x_pos`, `y_pos`, or
        `z_pos` and values should be floats.s

    Yields
    ------
    MDAEvent
        Each event in the MDA sequence.
    """
    order = sequence.used_axes
    axis_iterators = (enumerate(sequence.iter_axis(ax)) for ax in order)
    for item in product(*axis_iterators):
        if not item:  # the case with no events
            continue  # pragma: no cover

        # get axes objects for this event
        index, time, position, grid, channel, z_pos = _parse_axes(zip(order, item))

        # skip if necessary
        if _should_skip(position, channel, index, sequence.z_plan):
            continue

        # build kwargs that will be passed to this MDAEvent
        event_kwargs = base_event_kwargs or MDAEventDict(sequence=sequence)
        # the .update() here lets us build on top of the base_event.index if present
        event_kwargs.setdefault("index", {}).update(index)
        # determine x, y, z positions
        event_kwargs.update(_xyzpos(position, channel, sequence.z_plan, grid, z_pos))

        if position and position.name:
            event_kwargs["pos_name"] = position.name
        if channel:
            event_kwargs["channel"] = channel.to_event_channel()
            if channel.exposure is not None:
                event_kwargs["exposure"] = channel.exposure
        if time is not None:
            event_kwargs["min_start_time"] = time

        # apply any overrides
        if event_kwarg_overrides:
            event_kwargs.update(event_kwarg_overrides)

        # shift positions if position_offsets have been provided
        # (usually from sub-sequences)
        if position_offsets:
            for k, v in position_offsets.items():
                if event_kwargs[k] is not None:  # type: ignore[literal-required]
                    event_kwargs[k] += v  # type: ignore[literal-required]

        # grab global autofocus plan (may be overridden by position-specific plan below)
        autofocus_plan = sequence.autofocus_plan

        # if a position has been declared with a sub-sequence, we recurse into it
        if position:
            if position.sequence:
                # determine any relative position shifts or global overrides
                _pos, _offsets = _position_offsets(position, event_kwargs)
                # build overrides for this position
                pos_overrides = MDAEventDict(sequence=sequence, **_pos)  # type: ignore
                if position.name:
                    pos_overrides["pos_name"] = position.name

                sub_seq = position.sequence
                # if the sub-sequence doe not have an autofocus plan, we override it
                # with the parent sequence's autofocus plan
                if not sub_seq.autofocus_plan:
                    sub_seq = sub_seq.copy(update={"autofocus_plan": autofocus_plan})

                # recurse into the sub-sequence
                yield from iter_sequence(
                    sub_seq,
                    base_event_kwargs=event_kwargs.copy(),
                    event_kwarg_overrides=pos_overrides,
                    position_offsets=_offsets,
                )
                continue
            # note that position.sequence may be Falsey even if not None, for example
            # if all it has is an autofocus plan.  In that case, we don't recurse.
            # and we don't hit the continue statement, but we can use the autofocus plan
            elif position.sequence is not None and position.sequence.autofocus_plan:
                autofocus_plan = position.sequence.autofocus_plan

        event = MDAEvent(**event_kwargs)
        if autofocus_plan:
            af_event = autofocus_plan.event(event)
            if af_event:
                yield af_event
        yield event


def _position_offsets(
    position: Position, event_kwargs: MDAEventDict
) -> tuple[MDAEventDict, PositionDict]:
    """Determine shifts and position overrides for position subsequences."""
    pos_seq = cast("MDASequence", position.sequence)
    overrides = MDAEventDict()
    offsets = PositionDict()
    if not pos_seq.z_plan:
        # if this position has no z_plan, we use the z_pos from the parent
        overrides["z_pos"] = event_kwargs.get("z_pos")
    elif pos_seq.z_plan.is_relative:
        # otherwise apply z-shifts if this position has a relative z_plan
        offsets["z_pos"] = position.z or 0.0

    if not pos_seq.grid_plan:
        # if this position has no grid plan, we use the x_pos and y_pos from the parent
        overrides["x_pos"] = event_kwargs.get("x_pos")
        overrides["y_pos"] = event_kwargs.get("y_pos")
    elif pos_seq.grid_plan.is_relative:
        # otherwise apply x/y shifts if this position has a relative grid plan
        offsets["x_pos"] = position.x or 0.0
        offsets["y_pos"] = position.y or 0.0
    return overrides, offsets


def _parse_axes(
    event: zip[tuple[str, Any]],
) -> tuple[
    dict[str, int],
    float | None,  # time
    Position | None,
    GridPosition | None,
    Channel | None,
    float | None,  # z
]:
    """Parse an individual event from the product of axis iterators.

    Returns typed objects for each axis, and the index of the event.
    """
    _ev = dict(event)
    index = {ax: _ev[ax][0] for ax in INDICES if ax in _ev}
    axes = (_ev[ax][1] if ax in _ev else None for ax in INDICES)
    return (index, *axes)  # type: ignore[return-value]


def _should_skip(
    position: Position | None,
    channel: Channel | None,
    index: dict[str, int],
    z_plan: AnyZPlan | None,
) -> bool:
    """Return True if this event should be skipped."""
    if channel:
        # skip channels
        if TIME in index and index[TIME] % channel.acquire_every:
            return True

        # only acquire on the middle plane:
        if not channel.do_stack and z_plan and index[Z] != len(z_plan) // 2:
            return True

    if not position or not position.sequence:
        return False

    # NOTE: if we ever add more plans, they will need to be explicitly added
    # https://github.com/pymmcore-plus/useq-schema/pull/85

    # get if sub-sequence has any plan
    plans = any(
        (
            position.sequence.grid_plan,
            position.sequence.z_plan,
            position.sequence.time_plan,
        )
    )
    # overwriting the *global* channel index since it is no longer relevant.
    # if channel IS SPECIFIED in the position.sequence WITH any plan,
    # we skip otherwise the channel will be acquired twice. Same happens if
    # the channel IS NOT SPECIFIED but ANY plan is.
    if (
        CHANNEL in index
        and index[CHANNEL] != 0
        and ((position.sequence.channels and plans) or not plans)
    ):
        return True
    if Z in index and index[Z] != 0 and position.sequence.z_plan:
        return True
    if GRID in index and index[GRID] != 0 and position.sequence.grid_plan:
        return True
    return False


def _xyzpos(
    position: Position | None,
    channel: Channel | None,
    z_plan: AnyZPlan | None,
    grid: GridPosition | None = None,
    z_pos: float | None = None,
) -> MDAEventDict:
    if z_pos is not None:
        # combine z_pos with z_offset
        if channel and channel.z_offset is not None:
            z_pos += channel.z_offset
        if z_plan and z_plan.is_relative:
            # TODO: either disallow without position z, or add concept of "current"
            z_pos += getattr(position, Z, None) or 0
    elif position:
        z_pos = position.z

    if grid:
        x_pos: Optional[float] = grid.x
        y_pos: Optional[float] = grid.y
        if grid.is_relative:
            px = getattr(position, "x", 0) or 0
            py = getattr(position, "y", 0) or 0
            x_pos = x_pos + px if x_pos is not None else None
            y_pos = y_pos + py if y_pos is not None else None
    else:
        x_pos = getattr(position, "x", None)
        y_pos = getattr(position, "y", None)

    return {"x_pos": x_pos, "y_pos": y_pos, "z_pos": z_pos}
