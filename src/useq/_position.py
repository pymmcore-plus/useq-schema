from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, Generator, Optional

import numpy as np

from useq._base_model import FrozenModel

if TYPE_CHECKING:
    from useq import MDASequence


class Position(FrozenModel):
    """Define a position in 3D space.

    Any of the attributes can be `None` to indicate that the position is not
    defined. This is useful for defining a position relative to the current
    position.

    Attributes
    ----------
    x : float | None
        X position in microns.
    y : float | None
        Y position in microns.
    z : float | None
        Z position in microns.
    name : str | None
        Optional name for the position.
    sequence : MDASequence | None
        Optional MDASequence relative this position.
    """

    # if None, implies 'do not move this axis'
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    name: Optional[str] = None
    sequence: Optional[MDASequence] = None

    @classmethod
    def __get_validators__(cls) -> Generator[Callable[..., Any], None, None]:
        yield cls.validate

    @classmethod
    def validate(cls, value: Any) -> Position:
        if isinstance(value, Position):
            return value
        if isinstance(value, dict):
            return Position(**value)
        if isinstance(value, (np.ndarray, tuple)):
            x, *value = value
            y, *value = value or (None,)
            z = value[0] if value else None
            return Position(x=x, y=y, z=z)
        raise TypeError(f"Cannot coerce {value!r} to Position")
