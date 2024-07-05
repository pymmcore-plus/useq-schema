from typing import TYPE_CHECKING, ClassVar, Literal, Optional, Self

from useq._base_model import FrozenModel

if TYPE_CHECKING:
    from useq import MDASequence


class PositionBase(FrozenModel):
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    name: Optional[str] = None

    def __add__(self, other: "RelativePosition") -> Self:
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
        # retain rest of self args for Position
        kwargs = {**self.model_dump(), "x": x, "y": y, "z": z, "name": name}
        return self.model_validate(kwargs)


class AbsolutePosition(PositionBase):
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
    sequence: Optional["MDASequence"] = None
    is_relative: ClassVar[Literal[False]] = False


class RelativePosition(PositionBase):
    is_relative: ClassVar[Literal[True]] = True


Position = AbsolutePosition  # for backwards compatibility
