from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import field_validator

from useq import Axis, _channel
from useq._mda_event import Channel, MDAEvent
from useq.v2 import MDASequence, SimpleAxis
from useq.v2._position import Position

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping


class TimePlan(SimpleAxis[float]):
    axis_key: str = Axis.TIME

    def iter(self) -> Iterator[int]:
        yield from range(2)

    def contribute_to_mda_event(
        self, value: float, index: Mapping[str, int]
    ) -> MDAEvent.Kwargs:
        return {"min_start_time": value}


class ChannelPlan(SimpleAxis[_channel.Channel]):
    axis_key: str = Axis.CHANNEL

    @field_validator("values", mode="before")
    def _value_to_channel(cls, values: list[str]) -> list[_channel.Channel]:
        return [_channel.Channel(config=v, exposure=None) for v in values]

    def contribute_to_mda_event(
        self, value: _channel.Channel, index: Mapping[str, int]
    ) -> MDAEvent.Kwargs:
        return {"channel": {"config": value.config}}


class ZPlan(SimpleAxis[Position]):
    axis_key: str = Axis.Z

    @field_validator("values", mode="before")
    def _value_to_position(cls, values: list[float]) -> list[Position]:
        return [Position(z=v) for v in values]

    def contribute_to_mda_event(
        self, value: Position, index: Mapping[str, int]
    ) -> MDAEvent.Kwargs:
        return {"z_pos": value.z}


def test_new_mdasequence_simple() -> None:
    seq = MDASequence(
        time_plan=TimePlan(values=[0, 1]),
        channels=ChannelPlan(values=["red", "green", "blue"]),
        z_plan=ZPlan(values=[0.1, 0.3]),
    )
    events = list(seq.iter_events(axis_order=("t", "c", "z")))

    # fmt: off
    assert events == [
        MDAEvent(index={'t': 0, 'c': 0, 'z': 0}, channel=Channel(config='red'), min_start_time=0.0, z_pos=0.1),
        MDAEvent(index={'t': 0, 'c': 0, 'z': 1}, channel=Channel(config='red'), min_start_time=0.0, z_pos=0.3),
        MDAEvent(index={'t': 0, 'c': 1, 'z': 0}, channel=Channel(config='green'), min_start_time=0.0, z_pos=0.1),
        MDAEvent(index={'t': 0, 'c': 1, 'z': 1}, channel=Channel(config='green'), min_start_time=0.0, z_pos=0.3),
        MDAEvent(index={'t': 0, 'c': 2, 'z': 0}, channel=Channel(config='blue'), min_start_time=0.0, z_pos=0.1),
        MDAEvent(index={'t': 0, 'c': 2, 'z': 1}, channel=Channel(config='blue'), min_start_time=0.0, z_pos=0.3),
        MDAEvent(index={'t': 1, 'c': 0, 'z': 0}, channel=Channel(config='red'), min_start_time=1.0, z_pos=0.1),
        MDAEvent(index={'t': 1, 'c': 0, 'z': 1}, channel=Channel(config='red'), min_start_time=1.0, z_pos=0.3),
        MDAEvent(index={'t': 1, 'c': 1, 'z': 0}, channel=Channel(config='green'), min_start_time=1.0, z_pos=0.1),
        MDAEvent(index={'t': 1, 'c': 1, 'z': 1}, channel=Channel(config='green'), min_start_time=1.0, z_pos=0.3),
        MDAEvent(index={'t': 1, 'c': 2, 'z': 0}, channel=Channel(config='blue'), min_start_time=1.0, z_pos=0.1),
        MDAEvent(index={'t': 1, 'c': 2, 'z': 1}, channel=Channel(config='blue'), min_start_time=1.0, z_pos=0.3)
    ]
    # fmt: on

    from rich import print

    print(seq.model_dump())
