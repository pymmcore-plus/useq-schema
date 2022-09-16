from __future__ import annotations

from typing import Any, Callable, Generator, Optional

from pydantic.types import PositiveFloat, PositiveInt

from ._base_model import FrozenModel


class Channel(FrozenModel):
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
