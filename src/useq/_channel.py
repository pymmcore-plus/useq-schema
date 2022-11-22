from __future__ import annotations

from typing import Any, Callable, Generator, Optional

from pydantic.types import PositiveFloat, PositiveInt

from ._base_model import FrozenModel


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
    exposure : PositiveFloat | None
        Exposure time in seconds. If not provided, implies use current exposure time.
        By default, `None`.
    do_stack : bool
        If `True`, instructs engine to include this channel in any Z stacks being
        acquired. By default, `True`.
    z_offset : float
        Relative Z offset from current position, in microns. By default, `0`.
    acquire_every : PositiveInt
        Acquire every Nth frame (if acquiring a time series). By default, `1`.
    camera: str | None
        Name of the camera to use for this channel. If not provided, implies use
        current camera. By default, `None`.
    """

    config: str
    group: str = "Channel"
    exposure: Optional[PositiveFloat] = None
    do_stack: bool = True
    z_offset: float = 0.0
    acquire_every: PositiveInt = 1  # acquire every n frames
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
