from __future__ import annotations

from functools import lru_cache
from itertools import product
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Iterator, cast

from typing_extensions import TypedDict

from useq._channel import Channel  # noqa: TCH001  # noqa: TCH001
from useq._mda_event import Channel as EventChannel
from useq._mda_event import MDAEvent
from useq._utils import AXES, Axis, _has_axes
from useq._z import AnyZPlan  # noqa: TCH001  # noqa: TCH001

if TYPE_CHECKING:
    from useq._mda_sequence import MDASequence
    from useq._position import Position, PositionBase, RelativePosition


class MDAEventDict(TypedDict, total=False):
    index: MappingProxyType[str, int]
    channel: EventChannel | None
    exposure: float | None
    min_start_time: float | None
    pos_name: str | None
    x_pos: float | None
    y_pos: float | None
    z_pos: float | None
    sequence: MDASequence | None
    # properties: list[tuple] | None
    metadata: dict
    reset_event_timer: bool


class PositionDict(TypedDict, total=False):
    x_pos: float
    y_pos: float
    z_pos: float


@lru_cache(maxsize=None)
def _iter_axis(seq: MDASequence, ax: str) -> tuple[Channel | float | PositionBase, ...]:
    return tuple(seq.iter_axis(ax))


@lru_cache(maxsize=None)
def _sizes(seq: MDASequence) -> dict[str, int]:
    return {k: len(list(_iter_axis(seq, k))) for k in seq.axis_order}


@lru_cache(maxsize=None)
def _used_axes(seq: MDASequence) -> str:
    return "".join(k for k in seq.axis_order if _sizes(seq)[k])


def iter_sequence(sequence: MDASequence) -> Iterator[MDAEvent]:
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

    Yields
    ------
    MDAEvent
        Each event in the MDA sequence.
    """
    if not (keep_shutter_open_axes := sequence.keep_shutter_open_across):
        yield from _iter_sequence(sequence)
        return

    it = _iter_sequence(sequence)
    if (this_e := next(it, None)) is None:  # pragma: no cover
        return

    for next_e in it:
        # set `keep_shutter_open` to `True` if and only if ALL axes whose index
        # changes betwee this_event and next_event are in `keep_shutter_open_axes`
        if all(
            axis in keep_shutter_open_axes
            for axis, idx in this_e.index.items()
            if idx != next_e.index[axis]
        ):
            this_e = this_e.model_copy(update={"keep_shutter_open": True})
        yield this_e
        this_e = next_e
    yield this_e


def _iter_sequence(
    sequence: MDASequence,
    *,
    base_event_kwargs: MDAEventDict | None = None,
    event_kwarg_overrides: MDAEventDict | None = None,
    position_offsets: PositionDict | None = None,
    _last_t_idx: int = -1,
) -> Iterator[MDAEvent]:
    """Helper function for `iter_sequence`.

    We put most of the logic into this sub-function so that `iter_sequence` can
    easily modify the resulting sequence of events (e.g. to peek at the next event
    before yielding the current one).

    It also keeps the sub-sequence iteration kwargs out of the public API.

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
    _last_t_idx : int
        The index of the last timepoint.  This is used to determine if the event
        should reset the event timer.

    Yields
    ------
    MDAEvent
        Each event in the MDA sequence.
    """
    order = _used_axes(sequence)
    # this needs to be tuple(...) to work for mypyc
    axis_iterators = tuple(enumerate(_iter_axis(sequence, ax)) for ax in order)
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

        event_kwargs["index"] = MappingProxyType(
            {**event_kwargs.get("index", {}), **index}  # type: ignore
        )
        # determine x, y, z positions
        event_kwargs.update(_xyzpos(position, channel, sequence.z_plan, grid, z_pos))
        if position and position.name:
            event_kwargs["pos_name"] = position.name
        if channel:
            event_kwargs["channel"] = EventChannel.model_construct(
                config=channel.config, group=channel.group
            )
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
            if _has_axes(position.sequence):
                # determine any relative position shifts or global overrides
                _pos, _offsets = _position_offsets(position, event_kwargs)
                # build overrides for this position
                pos_overrides = MDAEventDict(sequence=sequence, **_pos)
                if position.name:
                    pos_overrides["pos_name"] = position.name

                sub_seq = position.sequence
                # if the sub-sequence doe not have an autofocus plan, we override it
                # with the parent sequence's autofocus plan
                if not sub_seq.autofocus_plan:
                    sub_seq = sub_seq.model_copy(
                        update={"autofocus_plan": autofocus_plan}
                    )

                # recurse into the sub-sequence
                yield from _iter_sequence(
                    sub_seq,
                    base_event_kwargs=event_kwargs.copy(),
                    event_kwarg_overrides=pos_overrides,
                    position_offsets=_offsets,
                    _last_t_idx=_last_t_idx,
                )
                continue
            # note that position.sequence may be Falsey even if not None, for example
            # if all it has is an autofocus plan.  In that case, we don't recurse.
            # and we don't hit the continue statement, but we can use the autofocus plan
            elif position.sequence is not None and position.sequence.autofocus_plan:
                autofocus_plan = position.sequence.autofocus_plan

        if event_kwargs["index"].get(Axis.TIME) == 0 and _last_t_idx != 0:
            event_kwargs["reset_event_timer"] = True
        event = MDAEvent.model_construct(**event_kwargs)
        if autofocus_plan:
            af_event = autofocus_plan.event(event)
            if af_event:
                yield af_event
        yield event
        _last_t_idx = event.index.get(Axis.TIME, _last_t_idx)


# ###################### Helper functions ######################


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
    RelativePosition | None,
    Channel | None,
    float | None,  # z
]:
    """Parse an individual event from the product of axis iterators.

    Returns typed objects for each axis, and the index of the event.
    """
    # NOTE: this is currently the biggest time sink in iter_sequence.
    # It is called for every event and takes ~40% of the cumulative time.
    _ev = dict(event)
    index = {ax: _ev[ax][0] for ax in AXES if ax in _ev}
    # this needs to be tuple(...) to work for mypyc
    axes = tuple(_ev[ax][1] if ax in _ev else None for ax in AXES)
    return (index, *axes)


def _should_skip(
    position: Position | None,
    channel: Channel | None,
    index: dict[str, int],
    z_plan: AnyZPlan | None,
) -> bool:
    """Return True if this event should be skipped."""
    if channel:
        # skip channels
        if Axis.TIME in index and index[Axis.TIME] % channel.acquire_every:
            return True

        # only acquire on the middle plane:
        if (
            not channel.do_stack
            and z_plan is not None
            and index[Axis.Z] != z_plan.num_positions() // 2
        ):
            return True

    if (
        not position
        or position.sequence is None
        or position.sequence.autofocus_plan is not None
    ):
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
    if index.get(Axis.CHANNEL, 0) != 0:
        if (position.sequence.channels and plans) or not plans:
            return True
    if Axis.Z in index and index[Axis.Z] != 0 and position.sequence.z_plan:
        return True
    if Axis.GRID in index and index[Axis.GRID] != 0 and position.sequence.grid_plan:
        return True
    return False


def _xyzpos(
    position: Position | None,
    channel: Channel | None,
    z_plan: AnyZPlan | None,
    grid: RelativePosition | None = None,
    z_pos: float | None = None,
) -> MDAEventDict:
    if z_pos is not None:
        # combine z_pos with z_offset
        if channel and channel.z_offset is not None:
            z_pos += channel.z_offset
        if z_plan and z_plan.is_relative:
            # TODO: either disallow without position z, or add concept of "current"
            z_pos += getattr(position, Axis.Z, None) or 0
    elif position:
        z_pos = position.z

    if grid:
        x_pos: float | None = grid.x
        y_pos: float | None = grid.y
        if grid.is_relative:
            px = getattr(position, "x", 0) or 0
            py = getattr(position, "y", 0) or 0
            x_pos = x_pos + px if x_pos is not None else None
            y_pos = y_pos + py if y_pos is not None else None
    else:
        x_pos = getattr(position, "x", None)
        y_pos = getattr(position, "y", None)

    return {"x_pos": x_pos, "y_pos": y_pos, "z_pos": z_pos}
