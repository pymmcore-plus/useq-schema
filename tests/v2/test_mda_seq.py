from __future__ import annotations

from typing import TYPE_CHECKING

from useq import Axis
from useq._mda_event import Channel, MDAEvent
from useq.v2 import MDASequence, SimpleAxis

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


class ChannelPlan(SimpleAxis[str]):
    axis_key: str = Axis.CHANNEL

    def iter(self) -> Iterator[str]:
        yield from ["red", "green", "blue"]

    def contribute_to_mda_event(
        self, value: str, index: Mapping[str, int]
    ) -> MDAEvent.Kwargs:
        return {"channel": {"config": value}}


class ZPlan(SimpleAxis[float]):
    axis_key: str = Axis.Z

    def iter(self) -> Iterator[float]:
        yield from [0.1, 0.3]

    def contribute_to_mda_event(
        self, value: float, index: Mapping[str, int]
    ) -> MDAEvent.Kwargs:
        return {"z_pos": value}


def test_new_mdasequence_simple() -> None:
    seq = MDASequence(
        axes=(
            TimePlan(values=[0, 1]),
            ChannelPlan(values=["red", "green", "blue"]),
            ZPlan(values=[0.1, 0.3]),
        )
    )
    events = list(seq.iter_events())

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

    # seq.model_dump_json()
