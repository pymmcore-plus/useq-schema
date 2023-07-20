from __future__ import annotations

from typing import Any, Callable, Generator, Optional

from pydantic import Field

from useq import _mda_event
from useq._base_model import FrozenModel


class Channel(FrozenModel):
    """Define an acquisition channel.

    Attributes
    ----------
    config : str
        Name of the configuration to use for this channel, (e.g. `"488nm"`, `"DAPI"`,
        `"FITC"`).
    group : str
        Optional name of the group to which this channel belongs. By default,
        `"Channel"`.
    exposure : float | None
        Exposure time in seconds. Must be positive.  If not provided, implies use
        current exposure time. By default, `None`.
    do_stack : bool
        If `True`, instructs engine to include this channel in any Z stacks being
        acquired. By default, `True`.
    z_offset : float
        Relative Z offset from current position, in microns. By default, `0`.
    acquire_every : int
        Acquire every Nth frame (if acquiring a time series). By default, `1`.
    camera: str | None
        Name of the camera to use for this channel. If not provided, implies use
        current camera. By default, `None`.
    """

    config: str
    group: str = "Channel"
    exposure: Optional[float] = Field(None, gt=0.0)
    do_stack: bool = True
    z_offset: float = 0.0
    acquire_every: int = Field(default=1, gt=0)  # acquire every n frames
    camera: Optional[str] = None

    @classmethod
    def __get_validators__(cls) -> Generator[Callable, None, None]:
        yield cls.validate

    @classmethod
    def validate(cls, value: Any) -> Channel:
        if isinstance(value, Channel):
            return value
        if isinstance(value, str):
            return Channel(config=value)
        if isinstance(value, dict):
            return Channel(**value)
        raise TypeError(f"invalid Channel argument: {value!r}")

    def to_event_channel(self) -> _mda_event.Channel:
        return _mda_event.Channel(config=self.config, group=self.group)
