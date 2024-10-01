from __future__ import annotations

from contextlib import suppress
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    Iterator,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)
from uuid import UUID, uuid4
from warnings import warn

import numpy as np
from pydantic import Field, PrivateAttr, field_validator, model_validator

from useq._base_model import UseqModel
from useq._channel import Channel
from useq._grid import MultiPointPlan  # noqa: TCH001
from useq._hardware_autofocus import AnyAutofocusPlan, AxesBasedAF
from useq._iter_sequence import iter_sequence
from useq._plate import WellPlatePlan
from useq._position import Position, PositionBase
from useq._time import AnyTimePlan  # noqa: TCH001
from useq._utils import AXES, Axis, TimeEstimate, estimate_sequence_duration
from useq._z import AnyZPlan  # noqa: TCH001

if TYPE_CHECKING:
    from typing_extensions import Self

    from useq._mda_event import MDAEvent


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
    keep_shutter_open_across : tuple[str, ...]
        A tuple of axes `str` across which the illumination shutter should be kept open.
        Resulting events will have `keep_shutter_open` set to `True` if and only if
        ALL axes whose indices are changing are in this tuple. For example, if
        `keep_shutter_open_across=('z',)`, then the shutter would be kept open between
        events axes {'t': 0, 'z: 0} and {'t': 0, 'z': 1}, but not between
        {'t': 0, 'z': 0} and {'t': 1, 'z': 0}.

    Examples
    --------
    Create a MDASequence

    >>> from useq import MDASequence, Position, Channel, TIntervalDuration
    >>> seq = MDASequence(
    ...     axis_order="tpgcz",
    ...     time_plan={"interval": 0.1, "loops": 2},
    ...     stage_positions=[(1, 1, 1)],
    ...     grid_plan={"rows": 2, "columns": 2},
    ...     z_plan={"range": 3, "step": 1},
    ...     channels=[{"config": "DAPI", "exposure": 1}]
    ... )

    Print the sequence to visualize its structure

    >>> print(seq)
    ... MDASequence(
    ...     stage_positions=(Position(x=1.0, y=1.0, z=1.0, name=None),),
    ...     grid_plan=GridRowsColumns(
    ...         fov_width=None,
    ...         fov_height=None,
    ...         overlap=(0.0, 0.0),
    ...         mode=<OrderMode.row_wise_snake: 'row_wise_snake'>,
    ...         rows=2,
    ...         columns=2,
    ...         relative_to=<RelativeTo.center: 'center'>
    ...     ),
    ...     channels=(
    ...         Channel(
    ...             config='DAPI',
    ...             group='Channel',
    ...             exposure=1.0,
    ...             do_stack=True,
    ...             z_offset=0.0,
    ...             acquire_every=1,
    ...             camera=None
    ...         ),
    ...     ),
    ...     time_plan=TIntervalLoops(
    ...         prioritize_duration=False,
    ...         interval=datetime.timedelta(microseconds=100000),
    ...         loops=2
    ...     ),
    ...     z_plan=ZRangeAround(go_up=True, range=3.0, step=1.0)
    ... )

    Iterate over the events in the sequence

    >>> print(list(seq))
    ... [
    ...     MDAEvent(
    ...         index=mappingproxy({'t': 0, 'p': 0, 'g': 0, 'c': 0, 'z': 0}),
    ...         channel=Channel(config='DAPI'),
    ...         exposure=1.0,
    ...         min_start_time=0.0,
    ...         x_pos=0.5,
    ...         y_pos=1.5,
    ...         z_pos=-0.5
    ...     ),
    ...     MDAEvent(
    ...         index=mappingproxy({'t': 0, 'p': 0, 'g': 0, 'c': 0, 'z': 1}),
    ...         channel=Channel(config='DAPI'),
    ...         exposure=1.0,
    ...         min_start_time=0.0,
    ...         x_pos=0.5,
    ...         y_pos=1.5,
    ...         z_pos=0.5
    ...     ),
    ...     ...
    ... ]

    Print the sequence as yaml

    >>> print(seq.yaml())

    ```yaml
    axis_order:
       - t
       - p
       - g
       - c
       - z
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
    ```
    """

    metadata: Dict[str, Any] = Field(default_factory=dict)
    axis_order: Tuple[str, ...] = AXES
    # note that these are BOTH just `Sequence[Position]` but we retain the distinction
    # here so that WellPlatePlans are preserved in the model instance.
    stage_positions: Union[WellPlatePlan, Tuple[Position, ...]] = Field(
        default_factory=tuple, union_mode="left_to_right"
    )
    grid_plan: Optional[MultiPointPlan] = Field(
        default=None, union_mode="left_to_right"
    )
    channels: Tuple[Channel, ...] = Field(default_factory=tuple)
    time_plan: Optional[AnyTimePlan] = None
    z_plan: Optional[AnyZPlan] = None
    autofocus_plan: Optional[AnyAutofocusPlan] = None
    keep_shutter_open_across: Tuple[str, ...] = Field(default_factory=tuple)

    _uid: UUID = PrivateAttr(default_factory=uuid4)
    _sizes: Optional[Dict[str, int]] = PrivateAttr(default=None)

    @property
    def uid(self) -> UUID:
        """A unique identifier for this sequence."""
        return self._uid

    def __hash__(self) -> int:
        return hash(self.uid)

    @field_validator("z_plan", mode="before")
    def _validate_zplan(cls, v: Any) -> Optional[dict]:
        return v or None

    @field_validator("keep_shutter_open_across", mode="before")
    def _validate_keep_shutter_open_across(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        try:
            v = tuple(v)
        except (TypeError, ValueError):  # pragma: no cover
            raise ValueError(
                f"keep_shutter_open_across must be string or a sequence of strings, "
                f"got {type(v)}"
            ) from None
        return v

    @field_validator("channels", mode="before")
    def _validate_channels(cls, value: Any) -> Tuple[Channel, ...]:
        if isinstance(value, str) or not isinstance(
            value, Sequence
        ):  # pragma: no cover
            raise ValueError(f"channels must be a sequence, got {type(value)}")
        channels = []
        for v in value:
            if isinstance(v, Channel):
                channels.append(v)
            elif isinstance(v, str):
                channels.append(Channel.model_construct(config=v))
            elif isinstance(v, dict):
                channels.append(Channel(**v))
            else:  # pragma: no cover
                raise ValueError(f"Invalid Channel argument: {value!r}")
        return tuple(channels)

    @field_validator("stage_positions", mode="before")
    def _validate_stage_positions(
        cls, value: Any
    ) -> Union[WellPlatePlan, Tuple[Position, ...]]:
        if isinstance(value, np.ndarray):
            if value.ndim == 1:
                value = [value]
            elif value.ndim == 2:
                value = list(value)
        else:
            with suppress(ValueError):
                val = WellPlatePlan.model_validate(value)
                return val
        if not isinstance(value, Sequence):  # pragma: no cover
            raise ValueError(
                "stage_positions must be a WellPlatePlan or Sequence[Position], "
                f"got {type(value)}"
            )

        positions = []
        for v in value:
            if isinstance(v, Position):
                positions.append(v)
            elif isinstance(v, dict):
                positions.append(Position(**v))
            elif isinstance(v, (np.ndarray, tuple)):
                x, *v = v
                y, *v = v or (None,)
                z = v[0] if v else None
                positions.append(Position(x=x, y=y, z=z))
            else:  # pragma: no cover
                raise ValueError(f"Cannot coerce {v!r} to Position")
        return tuple(positions)

    @field_validator("time_plan", mode="before")
    def _validate_time_plan(cls, v: Any) -> Optional[dict]:
        return {"phases": v} if isinstance(v, (tuple, list)) else v or None

    @field_validator("axis_order", mode="before")
    def _validate_axis_order(cls, v: Any) -> tuple[str, ...]:
        if not isinstance(v, Iterable):
            raise ValueError(f"axis_order must be iterable, got {type(v)}")
        order = tuple(str(x).lower() for x in v)
        extra = {x for x in order if x not in AXES}
        if extra:
            raise ValueError(
                f"Can only iterate over axes: {AXES!r}. Got extra: {extra}"
            )
        if len(set(order)) < len(order):
            raise ValueError(f"Duplicate entries found in acquisition order: {order}")

        return order

    @model_validator(mode="after")
    def _validate_mda(self) -> Self:
        if self.axis_order:
            self._check_order(
                self.axis_order,
                z_plan=self.z_plan,
                stage_positions=self.stage_positions,
                channels=self.channels,
                grid_plan=self.grid_plan,
                autofocus_plan=self.autofocus_plan,
            )
        if self.stage_positions and not isinstance(self.stage_positions, WellPlatePlan):
            for p in self.stage_positions:
                if hasattr(p, "sequence") and getattr(
                    p.sequence, "keep_shutter_open_across", None
                ):  # pragma: no cover
                    raise ValueError(
                        "keep_shutter_open_across cannot currently be set on a "
                        "Position sequence"
                    )
        return self

    def __eq__(self, other: Any) -> bool:
        """Return `True` if two `MDASequences` are equal (uid is excluded)."""
        if isinstance(other, MDASequence):
            return bool(
                self.model_dump(exclude={"uid"}) == other.model_dump(exclude={"uid"})
            )
        else:
            return False

    @staticmethod
    def _check_order(
        order: tuple[str, ...],
        z_plan: Optional[AnyZPlan] = None,
        stage_positions: Sequence[Position] = (),
        channels: Sequence[Channel] = (),
        grid_plan: Optional[MultiPointPlan] = None,
        autofocus_plan: Optional[AnyAutofocusPlan] = None,
    ) -> None:
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
                "Currently, a Position sequence cannot have multiple stage positions."
            )

        # Cannot use autofocus plan with absolute z_plan
        if Axis.Z in order and z_plan and not z_plan.is_relative:
            err = "Absolute Z positions cannot be used with autofocus plan."
            if isinstance(autofocus_plan, AxesBasedAF):
                raise ValueError(err)  # pragma: no cover
            for p in stage_positions:
                if p.sequence is not None and p.sequence.autofocus_plan:
                    raise ValueError(err)  # pragma: no cover

    @property
    def shape(self) -> Tuple[int, ...]:
        """Return the shape of this sequence.

        !!! note
            This doesn't account for jagged arrays, like channels that exclude z
            stacks or skip timepoints.
        """
        return tuple(s for s in self.sizes.values() if s)

    @property
    def sizes(self) -> Mapping[str, int]:
        """Mapping of axis name to size of that axis."""
        if self._sizes is None:
            self._sizes = {k: len(list(self.iter_axis(k))) for k in self.axis_order}
        return self._sizes

    @property
    def used_axes(self) -> str:
        """Single letter string of axes used in this sequence, e.g. `ztc`."""
        return "".join(k for k in self.axis_order if self.sizes[k])

    def iter_axis(self, axis: str) -> Iterator[Channel | float | PositionBase]:
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
