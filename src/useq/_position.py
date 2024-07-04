from typing import TYPE_CHECKING, Optional

from useq._base_model import FrozenModel
from useq._grid import GridPosition

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
    sequence: Optional["MDASequence"] = None

    def __add__(self, other: "Position | GridPosition") -> "Position":
        """Add two positions together to create a new position."""
        if isinstance(other, GridPosition) and not other.is_relative:
            raise ValueError("Cannot add a non-relative GridPosition to a Position")
        other_name = getattr(other, "name", "")
        other_name = f"_{other_name}" if other_name else ""
        other_z = getattr(other, "z", None)
        return Position(
            x=self.x + other.x if self.x is not None and other.x is not None else None,
            y=self.y + other.y if self.y is not None and other.y is not None else None,
            z=self.z + other_z if self.z is not None and other_z is not None else None,
            name=f"{self.name}{other_name}" if self.name and other_name else self.name,
            sequence=self.sequence,
        )
