from __future__ import annotations

from itertools import product
from typing import Any, Dict, Iterator, Optional, Sequence, Tuple, Union
from warnings import warn

import numpy as np
from pydantic import Field, root_validator, validator

from ._base_model import UseqModel
from ._channel import Channel
from ._mda_event import MDAEvent
from ._position import Position
from ._time import AnyTimePlan, NoT
from ._z import AnyZPlan, NoZ

TIME = "t"
CHANNEL = "c"
POSITION = "p"
Z = "z"
INDICES = (TIME, POSITION, CHANNEL, Z)


class MDASequence(UseqModel):
    axis_order: str = "".join(INDICES)
    stage_positions: Tuple[Position, ...] = Field(default_factory=tuple)
    channels: Tuple[Channel, ...] = Field(default_factory=tuple)
    time_plan: AnyTimePlan = Field(default_factory=NoT)
    z_plan: AnyZPlan = Field(default_factory=NoZ)

    @validator("z_plan", pre=True)
    def validate_zplan(cls, v):  # type: ignore
        if not v:
            return NoZ()
        return v

    @validator("time_plan", pre=True)
    def validate_time_plan(cls, v):  # type: ignore
        if isinstance(v, (tuple, list)):
            return {"phases": v}
        if not v:
            return NoT()
        return v

    @validator("stage_positions", pre=True)
    def validate_positions(cls, v):  # type: ignore
        if isinstance(v, np.ndarray):
            if v.ndim == 1:
                return [v]
            elif v.ndim == 2:
                return list(v)
        return v

    @validator("axis_order", pre=True)
    def validate_axis_order(cls, v):  # type: ignore
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

    @classmethod
    def _check_order(
        cls,
        order: str,
        z_plan: AnyZPlan = None,
        stage_positions: Sequence[Position] = (),
        channels: Sequence[Channel] = (),
    ) -> str:
        if (
            Z in order
            and POSITION in order
            and order.index(Z) < order.index(POSITION)
            and z_plan
            and any(p.z_plan for p in stage_positions)
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

    def add_channel(
        self,
        config: str,
        group: str = "Channel",
        exposure: int = None,
        do_stack: bool = False,
    ) -> None:
        new = Channel(config=config, group=group, exposure=exposure, do_stack=do_stack)
        self.channels = tuple(self.channels) + (new,)

    def remove_channel(self, **kwargs: Union[str, int, bool]) -> None:
        to_pop = [
            c
            for c in self.channels
            if any(getattr(c, k) == v for k, v in kwargs.items())
        ]
        self.channels = tuple(i for i in self.channels if i not in to_pop)

    def __str__(self) -> str:
        out = "Multi-Dimensional Acquisition ▶ "
        shape = [
            f"n{k.lower()}: {len(list(self.iter_axis(k)))}" for k in self.axis_order
        ]
        out += ", ".join(shape)
        return out

    # def __len__(self):
    #     # np.prod(self.shape)
    #     return len(list(self.iter_events()))

    @property
    def shape(self) -> Tuple[int, ...]:
        # NOTE: Doesn't account for skipped Z or channel frames
        shp = (len(list(self.iter_axis(k))) for k in self.axis_order)
        return tuple(s for s in shp if s)

    def iter_axis(self, axis: str) -> Iterator[Union[Position, Channel, float]]:
        yield from {
            TIME: self.time_plan,
            POSITION: self.stage_positions,
            Z: self.z_plan,
            CHANNEL: self.channels,
        }[axis]

    def __iter__(self) -> Iterator[MDAEvent]:  # type: ignore
        yield from self.iter_events(self.axis_order)

    class _SkipFrame(Exception):
        pass

    def iter_events(self, order: str = None) -> Iterator[MDAEvent]:

        order = self._check_order(order or self.axis_order)
        # strip dimensions that have no length
        order = "".join(i for i in order if list(self.iter_axis(i)))

        for item in product(*(enumerate(self.iter_axis(ax)) for ax in order)):
            if not item:  # the case with no events
                continue

            _ev = dict(zip(order, item))
            index = {k: _ev[k][0] for k in INDICES if k in _ev}

            position: Optional[Position] = _ev[POSITION][1] if POSITION in _ev else None
            channel: Optional[Channel] = _ev[CHANNEL][1] if CHANNEL in _ev else None
            time: Optional[int] = _ev[TIME][1] if TIME in _ev else None

            # skip channels
            if channel and TIME in index and index[TIME] % channel.acquire_every:
                continue

            try:
                z_pos = (
                    self._combine_z(_ev[Z][1], index[Z], channel, position)
                    if Z in _ev
                    else None
                )
            except self._SkipFrame:
                continue

            _channel = (
                {"config": channel.config, "group": channel.group} if channel else None
            )
            yield MDAEvent(
                index=index,
                min_start_time=time,
                x_pos=getattr(position, "x", None),
                y_pos=getattr(position, "y", None),
                z_pos=z_pos,
                exposure=getattr(channel, "exposure", None),
                channel=_channel,
                sequence=self,
            )

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
        return [event.to_pycromanager() for event in self]
