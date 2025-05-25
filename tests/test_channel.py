from collections.abc import Sequence
from typing import Any

import pytest

import useq

c_inputs = [
    ("DAPI", ("Channel", "DAPI")),
    ({"config": "DAPI"}, ("Channel", "DAPI")),
    ({"config": "DAPI", "group": "Group", "acquire_every": 3}, ("Group", "DAPI")),
    (useq.Channel(config="DAPI"), ("Channel", "DAPI")),
    (useq.Channel(config="DAPI", group="Group"), ("Group", "DAPI")),
]


@pytest.mark.parametrize("channel, cexpectation", c_inputs)
def test_channel(channel: Any, cexpectation: Sequence[float]) -> None:
    channel = useq.Channel.model_validate(channel)
    assert (channel.group, channel.config) == cexpectation
