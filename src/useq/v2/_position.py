from __future__ import annotations

import os
import warnings
from typing import TYPE_CHECKING, Any, Optional, SupportsIndex

import numpy as np
from pydantic import model_validator

from useq._base_model import MutableModel

if TYPE_CHECKING:
    from typing_extensions import Self


class Position(MutableModel):
    """Define a position in 3D space.

    Any of the attributes can be `None` to indicate that the position is not
    defined.  For engines implementing support for useq, a position of `None` implies
    "do not move" or "stay at current position" on that axis.

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
    is_relative : bool
        If `True`, the position should be considered a delta relative to some other
        position. Relative positions support addition and subtraction, while absolute
        positions do not.
    """

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        if "sequence" in kwargs and (seq := kwargs.pop("sequence")) is not None:
            from useq.v2._mda_sequence import MDASequence

            seq2 = MDASequence.model_validate(seq)
            pos = Position.model_validate(kwargs)
            warnings.warn(
                "In useq.v2 Positions no longer have a sequence attribute. "
                "If you want to assign a subsequence to a position, "
                "use positions=[..., MDASequence(value=Position(), ...)]. "
                "We will now return an MDASequence, but this is not type safe.",
                DeprecationWarning,
                stacklevel=2,
            )
            return seq2.model_copy(update={"value": pos})  # type: ignore[return-value]
        return super().__new__(cls)

    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    name: Optional[str] = None
    is_relative: bool = False

    @model_validator(mode="before")
    @classmethod
    def _cast_any(cls, values: Any) -> Any:
        """Try to cast any value to a Position."""
        if isinstance(values, (np.ndarray, tuple)):
            x, *v = values
            y, *v = v or (None,)
            z = v[0] if v else None
            values = {"x": x, "y": y, "z": z}
        return values

    def __add__(self, other: Position) -> Self:
        """Add two positions together to create a new position."""
        if not isinstance(other, Position) or not other.is_relative:
            return NotImplemented  # pragma: no cover
        if self.name and other.name:
            new_name: str | None = f"{self.name}_{other.name}"
        else:
            new_name = self.name or other.name

        return self.model_copy(
            update={
                "x": _none_sum(self.x, other.x),
                "y": _none_sum(self.y, other.y),
                "z": _none_sum(self.z, other.z),
                "name": new_name,
            }
        )

    # allow `sum([pos1, delta, delta2], start=Position())`
    __radd__ = __add__

    def __round__(self, ndigits: SupportsIndex | None = None) -> Self:
        """Round the position to the given number of decimal places."""
        return self.model_copy(
            update={
                "x": _none_round(self.x, ndigits),
                "y": _none_round(self.y, ndigits),
                "z": _none_round(self.z, ndigits),
            }
        )

    # FIXME: before merge
    if "PYTEST_VERSION" in os.environ:

        def __eq__(self, other: object) -> bool:
            """Compare two positions for equality."""
            if isinstance(other, (float, int)):
                return self.z == other
            return super().__eq__(other)


def _none_sum(a: float | None, b: float | None) -> float | None:
    return a + b if a is not None and b is not None else a


def _none_round(v: float | None, ndigits: SupportsIndex | None) -> float | None:
    return round(v, ndigits) if v is not None else None
