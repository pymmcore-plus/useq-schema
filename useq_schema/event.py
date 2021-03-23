from __future__ import annotations

from typing import Dict, Sequence, Tuple

from pydantic import Field
from pydantic.dataclasses import dataclass


@dataclass
class Channel:
    config: str
    group: str


@dataclass
class Event:
    axes: Dict[str, int] = None
    channel: Channel = None
    channel_config: str = None
    exposure: float = Field(None, ge=0)

    # pycromanager waits on: system.current_time < (acquisition_.start_time + min_start_time)
    # could/should there be a way to enforce interval more than abs epoch?  (eg. experiment paused)
    # or should that be an implementation detail of the acqEngine
    min_start_time: int = None

    z_pos: float = None
    x_pos: float = None
    y_pos: float = None
    properties: Sequence[Tuple[str, str, str]] = None


if __name__ == "__main__":
    print(Event.__pydantic_model__.schema_json())