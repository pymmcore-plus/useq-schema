from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from pydantic import field_validator

from useq.v2 import (
    Channel,
    MDAEvent,
    MDASequence,
    Position,
    SimpleValueAxis,
    TIntervalLoops,
    ZRangeAround,
)

if TYPE_CHECKING:
    from collections.abc import Mapping


# Some example subclasses of SimpleAxis, to demonstrate flexibility
class APlan(SimpleValueAxis[float]):
    axis_key: str = "a"

    def contribute_event_kwargs(
        self, value: float, index: Mapping[str, int]
    ) -> MDAEvent.Kwargs:
        return {"min_start_time": value}


class BPlan(SimpleValueAxis[Position]):
    axis_key: str = "b"

    @field_validator("values", mode="before")
    def _value_to_position(cls, values: list[float]) -> list[Position]:
        return [Position(z=v) for v in values]

    def contribute_event_kwargs(
        self, value: Position, index: Mapping[str, int]
    ) -> MDAEvent.Kwargs:
        return {"z_pos": value.z}


class CPlan(SimpleValueAxis[Channel]):
    axis_key: str = "c"

    @field_validator("values", mode="before")
    def _value_to_channel(cls, values: list[str]) -> list[Channel]:
        return [Channel(config=v, exposure=None) for v in values]

    def contribute_event_kwargs(
        self, value: Channel, index: Mapping[str, int]
    ) -> MDAEvent.Kwargs:
        return {"channel": {"config": value.config}}


def test_new_mdasequence_simple() -> None:
    seq = MDASequence(
        axes=(
            APlan(values=[0, 1]),
            BPlan(values=[0.1, 0.3]),
            CPlan(values=["red", "green", "blue"]),
        )
    )
    events = [
        x.model_dump(exclude={"sequence"}, exclude_unset=True)
        for x in seq.iter_events()
    ]
    # fmt: off
    assert events == [
        {'index': {'a': 0, 'b': 0, 'c': 0}, 'channel': {'config': 'red'}, 'min_start_time': 0.0, 'z_pos': 0.1},
        {'index': {'a': 0, 'b': 0, 'c': 1}, 'channel': {'config': 'green'}, 'min_start_time': 0.0, 'z_pos': 0.1},
        {'index': {'a': 0, 'b': 0, 'c': 2}, 'channel': {'config': 'blue'}, 'min_start_time': 0.0, 'z_pos': 0.1},
        {'index': {'a': 0, 'b': 1, 'c': 0}, 'channel': {'config': 'red'}, 'min_start_time': 0.0, 'z_pos': 0.3},
        {'index': {'a': 0, 'b': 1, 'c': 1}, 'channel': {'config': 'green'}, 'min_start_time': 0.0, 'z_pos': 0.3},
        {'index': {'a': 0, 'b': 1, 'c': 2}, 'channel': {'config': 'blue'}, 'min_start_time': 0.0, 'z_pos': 0.3},
        {'index': {'a': 1, 'b': 0, 'c': 0}, 'channel': {'config': 'red'}, 'min_start_time': 1.0, 'z_pos': 0.1},
        {'index': {'a': 1, 'b': 0, 'c': 1}, 'channel': {'config': 'green'}, 'min_start_time': 1.0, 'z_pos': 0.1},
        {'index': {'a': 1, 'b': 0, 'c': 2}, 'channel': {'config': 'blue'}, 'min_start_time': 1.0, 'z_pos': 0.1},
        {'index': {'a': 1, 'b': 1, 'c': 0}, 'channel': {'config': 'red'}, 'min_start_time': 1.0, 'z_pos': 0.3},
        {'index': {'a': 1, 'b': 1, 'c': 1}, 'channel': {'config': 'green'}, 'min_start_time': 1.0, 'z_pos': 0.3},
        {'index': {'a': 1, 'b': 1, 'c': 2}, 'channel': {'config': 'blue'}, 'min_start_time': 1.0, 'z_pos': 0.3},
    ]
    # fmt: on


def test_new_mdasequence_parity() -> None:
    seq = MDASequence(
        time_plan=TIntervalLoops(interval=0.2, loops=2),
        z_plan=ZRangeAround(range=1, step=0.5),
        channels=["DAPI", "FITC"],
    )
    events = [
        x.model_dump(exclude={"sequence"}, exclude_unset=True)
        for x in seq.iter_events()
    ]
    # fmt: off
    assert events == [
        {'index': {'t': 0, 'c': 0, 'z': 0}, 'channel': {'config': 'DAPI', 'group': 'Channel'}, 'min_start_time': 0.0, 'z_pos': -0.5, 'reset_event_timer': True},
        {'index': {'t': 0, 'c': 0, 'z': 1}, 'channel': {'config': 'DAPI', 'group': 'Channel'}, 'min_start_time': 0.0, 'z_pos': 0.0},
        {'index': {'t': 0, 'c': 0, 'z': 2}, 'channel': {'config': 'DAPI', 'group': 'Channel'}, 'min_start_time': 0.0, 'z_pos': 0.5},
        {'index': {'t': 0, 'c': 1, 'z': 0}, 'channel': {'config': 'FITC', 'group': 'Channel'}, 'min_start_time': 0.0, 'z_pos': -0.5},
        {'index': {'t': 0, 'c': 1, 'z': 1}, 'channel': {'config': 'FITC', 'group': 'Channel'}, 'min_start_time': 0.0, 'z_pos': 0.0},
        {'index': {'t': 0, 'c': 1, 'z': 2}, 'channel': {'config': 'FITC', 'group': 'Channel'}, 'min_start_time': 0.0, 'z_pos': 0.5},
        {'index': {'t': 1, 'c': 0, 'z': 0}, 'channel': {'config': 'DAPI', 'group': 'Channel'}, 'min_start_time': 0.2, 'z_pos': -0.5},
        {'index': {'t': 1, 'c': 0, 'z': 1}, 'channel': {'config': 'DAPI', 'group': 'Channel'}, 'min_start_time': 0.2, 'z_pos': 0.0},
        {'index': {'t': 1, 'c': 0, 'z': 2}, 'channel': {'config': 'DAPI', 'group': 'Channel'}, 'min_start_time': 0.2, 'z_pos': 0.5},
        {'index': {'t': 1, 'c': 1, 'z': 0}, 'channel': {'config': 'FITC', 'group': 'Channel'}, 'min_start_time': 0.2, 'z_pos': -0.5},
        {'index': {'t': 1, 'c': 1, 'z': 1}, 'channel': {'config': 'FITC', 'group': 'Channel'}, 'min_start_time': 0.2, 'z_pos': 0.0},
        {'index': {'t': 1, 'c': 1, 'z': 2}, 'channel': {'config': 'FITC', 'group': 'Channel'}, 'min_start_time': 0.2, 'z_pos': 0.5},
    ]
    # fmt: on


def serialize_mda_sequence() -> None:
    assert isinstance(MDASequence.model_json_schema(), str)
    seq = MDASequence(
        time_plan=TIntervalLoops(interval=0.2, loops=2),
        z_plan=ZRangeAround(range=1, step=0.5),
        channels=["DAPI", "FITC"],
    )
    assert isinstance(seq.model_dump_json(), str)
    assert isinstance(seq.model_dump(mode="json"), dict)


@pytest.mark.filterwarnings("ignore:.*ill-defined:FutureWarning")
def test_basic_properties() -> None:
    seq = MDASequence(
        time_plan=TIntervalLoops(interval=0.2, loops=2),
        z_plan=ZRangeAround(range=1, step=0.5),
        stage_positions=[(0, 0)],
        channels=["DAPI", "FITC"],
        axis_order=("t", "c", "z"),
    )
    assert seq.time_plan is not None
    assert seq.channels is not None
    assert seq.z_plan is not None
    assert seq.stage_positions is not None
    assert seq.grid_plan is None
    assert seq.shape
    assert seq.sizes
    assert seq.used_axes == ("t", "c", "z")
