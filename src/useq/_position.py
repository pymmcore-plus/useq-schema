from typing import TYPE_CHECKING, ClassVar, Literal, Optional, SupportsIndex

from pydantic import Field

from useq._base_model import FrozenModel

if TYPE_CHECKING:
    from typing_extensions import Self

    from useq import MDASequence


class PositionBase(FrozenModel):
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
    sequence : MDASequence | None
        Optional MDASequence relative this position.
    row : int | None
        Optional row index, when used in a grid.
    col : int | None
        Optional column index, when used in a grid.
    """

    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    name: Optional[str] = None
    sequence: Optional["MDASequence"] = None

    # excluded from serialization
    row: Optional[int] = Field(default=None, exclude=True)
    col: Optional[int] = Field(default=None, exclude=True)

    def __add__(self, other: "RelativePosition") -> "Self":
        """Add two positions together to create a new position."""
        if not isinstance(other, RelativePosition):
            raise ValueError(f"Cannot add a non-relative Position to {type(self)}")
        if (x := self.x) is not None and other.x is not None:
            x += other.x
        if (y := self.y) is not None and other.y is not None:
            y += other.y
        if (z := self.z) is not None and other.z is not None:
            z += other.z
        if (name := self.name) and other.name:
            name = f"{name}_{other.name}"
        kwargs = {**self.model_dump(), "x": x, "y": y, "z": z, "name": name}
        return type(self).model_construct(**kwargs)  # type: ignore [return-value]

    def __round__(self, ndigits: SupportsIndex | None = None) -> "Self":
        """Round the position to the given number of decimal places."""
        kwargs = {
            **self.model_dump(),
            "x": round(self.x, ndigits) if self.x is not None else None,
            "y": round(self.y, ndigits) if self.y is not None else None,
            "z": round(self.z, ndigits) if self.z is not None else None,
        }
        # not sure why these Self types are not working
        return type(self).model_construct(**kwargs)  # type: ignore [return-value]


class AbsolutePosition(PositionBase):
    """An absolute position in 3D space."""

    is_relative: ClassVar[Literal[False]] = False


Position = AbsolutePosition  # for backwards compatibility


class RelativePosition(PositionBase):
    """A relative position in 3D space."""

    is_relative: ClassVar[Literal[True]] = True
