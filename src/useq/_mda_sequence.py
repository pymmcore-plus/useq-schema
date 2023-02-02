from __future__ import annotations

from itertools import product
from typing import (
    Any,
    Dict,
    Iterator,
    Optional,
    Sequence,
    Tuple,
    Union,
    no_type_check,
)
from uuid import UUID, uuid4
from warnings import warn

import numpy as np
from pydantic import Field, PrivateAttr, root_validator, validator

from ._base_model import UseqModel
from ._channel import Channel
from ._grid import AnyGridPlan, GridPosition, NoGrid
from ._mda_event import MDAEvent
from ._position import Position
from ._time import AnyTimePlan, NoT
from ._z import AnyZPlan, NoZ

TIME = "t"
CHANNEL = "c"
POSITION = "p"
Z = "z"
GRID = "g"
INDICES = (TIME, POSITION, CHANNEL, Z, GRID)

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
        The order of the axes in the sequence. Must be a permutation of `"tpcz"`. The
        default is `"tpcz"`.
    stage_positions : tuple[Position, ...]
        The stage positions to visit. (each with `x`, `y`, `z`, `name`, and `z_plan`,
        all of which are optional).
    grid_plan : GridFromCorners, GridRelative, NoGrid
        The grid plan to follow. One of `GridFromCorners`, `GridRelative` or `NoGrid`.
    channels : tuple[Channel, ...]
        The channels to acquire. see `Channel`.
    time_plan : MultiPhaseTimePlan | TIntervalDuration | TIntervalLoops \
        | TDurationLoops | NoT
        The time plan to follow. One of `TIntervalDuration`, `TIntervalLoops`,
        `TDurationLoops`, `MultiPhaseTimePlan`, or `NoT`
    z_plan : ZTopBottom | ZRangeAround | ZAboveBelow | ZRelativePositions | \
        ZAbsolutePositions | NoZ
        The z plan to follow. One of `ZTopBottom`, `ZRangeAround`, `ZAboveBelow`,
        `ZRelativePositions`, `ZAbsolutePositions`, or `NoZ`.
    uid : UUID
        A read-only unique identifier (uuid version 4) for the sequence. This will be
        generated, do not set.

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
    stage_positions:
    - x: 1.0
      y: 1.0
      z: 1.0
    grid_plan:
      cols: 2
      rows: 2
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
    grid_plan: AnyGridPlan = Field(default_factory=NoGrid)
    channels: Tuple[Channel, ...] = Field(default_factory=tuple)
    time_plan: AnyTimePlan = Field(default_factory=NoT)
    z_plan: AnyZPlan = Field(default_factory=NoZ)

    _uid: UUID = PrivateAttr(default_factory=uuid4)
    _length: Optional[int] = PrivateAttr(default=None)
    _fov_size: Tuple[float, float] = PrivateAttr(default=(1, 1))

    @property
    def uid(self) -> UUID:
        """A unique identifier for this sequence."""
        return self._uid

    def set_fov_size(self, fov_size: Tuple[float, float]) -> None:
        """Set the field of view size.

        This is used to calculate the number of grid positions in a grid plan.
        """
        self._fov_size = fov_size

    @no_type_check
    def replace(
        self,
        metadata: Dict[str, Any] = Undefined,
        axis_order: str = Undefined,
        stage_positions: Tuple[Position, ...] = Undefined,
        grid_plan: AnyGridPlan = Undefined,
        channels: Tuple[Channel, ...] = Undefined,
        time_plan: AnyTimePlan = Undefined,
        z_plan: AnyZPlan = Undefined,
    ) -> MDASequence:
        """Return a new `MDAsequence` replacing specified kwargs with new values.

        MDASequences are immutable, so this method is useful for creating a new
        sequence with only a few fields changed.  The uid of the new sequence will
        be different from the original
        """
        kwargs = {
            k: v for k, v in locals().items() if v is not Undefined and k != "self"
        }
        state = self.dict(exclude={"uid"})
        return type(self)(**{**state, **kwargs})

    def __hash__(self) -> int:
        return hash(self.uid)

    @validator("z_plan", pre=True)
    def validate_zplan(cls, v: Any) -> Union[dict, NoZ]:
        return v or NoZ()

    @validator("time_plan", pre=True)
    def validate_time_plan(cls, v: Any) -> Union[dict, NoT]:
        return {"phases": v} if isinstance(v, (tuple, list)) else v or NoT()

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
                "{TIME!r} in the acquisition order: may not yield intended results."
            )

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
        yield from {
            TIME: self.time_plan,
            POSITION: self.stage_positions,
            Z: self.z_plan,
            CHANNEL: self.channels,
            GRID: self.grid_plan.iter_grid_positions(
                self._fov_size[0], self._fov_size[1]
            ),
        }[axis]

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

    def _combine_z(
        self,
        z_pos: float,
        z_ind: int,
        channel: Optional[Channel],
        position: Optional[Position],
    ) -> float:
        if channel:
            # only acquire on the middle plane:
            if not channel.do_stack and z_ind != len(self.z_plan) // 2:
                raise self._SkipFrame()
            if channel.z_offset is not None:
                z_pos += channel.z_offset
        if self.z_plan.is_relative:
            # TODO: either disallow without position z, or add concept of "current"
            z_pos += getattr(position, Z, None) or 0
        return z_pos

    def to_pycromanager(self) -> list[dict]:
        """Convenience to convert this sequence to a list of pycro-manager events.

        See: <https://pycro-manager.readthedocs.io/en/latest/apis.html>
        """
        return [event.to_pycromanager() for event in self]


MDAEvent.update_forward_refs(MDASequence=MDASequence)
Position.update_forward_refs(MDASequence=MDASequence)


def _get_z(
    sequence: MDASequence,
    event: dict[str, tuple],
    index: dict[str, int],
    position: Position | None,
    channel: Channel | None,
) -> float | None:
    return (
        sequence._combine_z(event[Z][1], index[Z], channel, position)
        if Z in event
        else position.z
        if position
        else None
    )


def _get_event_and_index(
    sequence: MDASequence,
    item: tuple[Any, ...],
    current_index: dict[str, int] = None,  # type: ignore
) -> tuple[dict[str, tuple], dict[str, int]]:
    if current_index is None:
        current_index = {}
    event = dict(zip(sequence.used_axes, item))
    index = current_index or {}
    for k in INDICES:
        if k in event:
            index[k] = event[k][0]
    return event, index


def _get_axis_info(
    event: dict[str, tuple]
) -> tuple[Position | None, Channel | None, float | None, GridPosition | None]:
    position: Optional[Position] = event[POSITION][1] if POSITION in event else None
    channel: Optional[Channel] = event[CHANNEL][1] if CHANNEL in event else None
    time: Optional[int] = event[TIME][1] if TIME in event else None
    grid: Optional[GridPosition] = event[GRID][1] if GRID in event else None
    return position, channel, time, grid


def _get_xy_from_grid(
    position: Position | None, grid: GridPosition
) -> tuple[float | None, float | None]:
    x_pos = getattr(position, "x", 0.0) or 0.0
    y_pos = getattr(position, "y", 0.0) or 0.0

    x_grid_pos: Optional[float] = grid.x
    y_grid_pos: Optional[float] = grid.y
    if grid.is_relative:
        x_pos = (
            x_grid_pos + x_pos
            if (x_pos is not None and x_grid_pos is not None)
            else None
        )
        y_pos = (
            y_grid_pos + y_pos
            if (y_pos is not None and y_grid_pos is not None)
            else None
        )
    else:
        x_pos = x_grid_pos
        y_pos = y_grid_pos
    return x_pos, y_pos


def iter_sequence(sequence: MDASequence) -> Iterator[MDAEvent]:
    global_index = 0
    event_iterator = (enumerate(sequence.iter_axis(ax)) for ax in sequence.used_axes)
    for item in product(*event_iterator):
        if not item:  # the case with no events
            continue  # pragma: no cover

        _ev, index = _get_event_and_index(sequence, item)
        position, channel, time, grid = _get_axis_info(_ev)

        # skip channels
        if channel and TIME in index and index[TIME] % channel.acquire_every:
            continue
        # skip if in position sequence
        if position and position.sequence and GRID in index and index[GRID] != 0:
            continue
        if position and position.sequence and Z in index and index[Z] != 0:
            continue

        try:
            z_pos = _get_z(sequence, _ev, index, position, channel)
        except sequence._SkipFrame:
            continue

        if position and position.sequence:
            sub_sequence = position.sequence
            sub_event_iterator = (
                enumerate(sub_sequence.iter_axis(ax)) for ax in sub_sequence.used_axes
            )
            for sub_item in product(*sub_event_iterator):
                yield _iter_sub_sequence(
                    sub_sequence,
                    index,
                    sub_item,
                    position,
                    z_pos,
                    channel,
                    grid,
                    global_index,
                )
                global_index += 1
            continue

        _channel = (
            {"config": channel.config, "group": channel.group} if channel else None
        )

        x_pos = getattr(position, "x", None)
        y_pos = getattr(position, "y", None)

        if grid:
            x_pos, y_pos = _get_xy_from_grid(position, grid)

        yield MDAEvent(
            index=index,
            min_start_time=time,
            pos_name=getattr(position, "name", None),
            x_pos=x_pos,
            y_pos=y_pos,
            z_pos=z_pos,
            exposure=getattr(channel, "exposure", None),
            channel=_channel,
            sequence=sequence,
            global_index=global_index,
        )
        global_index += 1


def _iter_sub_sequence(
    sequence: MDASequence,
    index: dict[str, int],
    item: tuple[Any, ...],
    position: Position | None,
    z_pos: float | None,
    channel: Channel | None,
    grid: GridPosition | None,
    global_index: int,
) -> MDAEvent:
    _sub_ev, sub_index = _get_event_and_index(sequence, item, index)
    _, sub_channel, sub_time, sub_grid = _get_axis_info(_sub_ev)

    sub_channel = sub_channel or channel
    sub_grid = sub_grid or grid

    _sub_channel = (
        {"config": sub_channel.config, "group": sub_channel.group}
        if sub_channel
        else None
    )

    x_pos = getattr(position, "x", None)
    y_pos = getattr(position, "y", None)

    if sub_grid:
        x_pos, y_pos = _get_xy_from_grid(position, sub_grid)

    z_pos = (
        _get_z(sequence, _sub_ev, sub_index, position, sub_channel)
        if sequence.z_plan
        else z_pos
    )
    return MDAEvent(
        index=sub_index,
        min_start_time=sub_time,
        pos_name=getattr(position, "name", None),
        x_pos=x_pos,
        y_pos=y_pos,
        z_pos=z_pos,
        exposure=getattr(sub_channel, "exposure", None),
        channel=_sub_channel,
        sequence=sequence,
        global_index=global_index,
    )



s = MDASequence(
    axis_order="tpgcz",
    channels=[{"config": "Cy5", "exposure": 50}],
    stage_positions=[
        (20, 20),
        {
            "x": 10,
            "y": 10,
            "z": 10,
            #"sequence": MDASequence(
            #    axis_order="tpgcz",
            #    tile_plan=TileRelative(rows=2, columns=2),
                # z_plan={"range": 3, "step": 1}
            #),
        },
    ],
    z_plan={"range": 3, "step": 1},
    time_plan={"interval": 3, "loops": 2},
)