from typing import TYPE_CHECKING, Generic, Iterator, Optional, SupportsIndex, TypeVar

from pydantic import Field

from useq._base_model import FrozenModel, MutableModel

if TYPE_CHECKING:
    from typing_extensions import Self

    from useq import MDASequence


class PositionBase(MutableModel):
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
        if not isinstance(other, RelativePosition):  # pragma: no cover
            return NotImplemented
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

    def __round__(self, ndigits: "SupportsIndex | None" = None) -> "Self":
        """Round the position to the given number of decimal places."""
        kwargs = {
            **self.model_dump(),
            "x": round(self.x, ndigits) if self.x is not None else None,
            "y": round(self.y, ndigits) if self.y is not None else None,
            "z": round(self.z, ndigits) if self.z is not None else None,
        }
        # not sure why these Self types are not working
        return type(self).model_construct(**kwargs)  # type: ignore [return-value]


class AbsolutePosition(PositionBase, FrozenModel):
    """An absolute position in 3D space."""

    @property
    def is_relative(self) -> bool:
        return False


Position = AbsolutePosition  # for backwards compatibility
PositionT = TypeVar("PositionT", bound=PositionBase)


class _MultiPointPlan(MutableModel, Generic[PositionT]):
    """Any plan that yields multiple positions."""

    fov_width: Optional[float] = None
    fov_height: Optional[float] = None

    @property
    def is_relative(self) -> bool:
        return True

    def __iter__(self) -> Iterator[PositionT]:  # type: ignore [override]
        raise NotImplementedError("This method must be implemented by subclasses.")

    def num_positions(self) -> int:
        raise NotImplementedError("This method must be implemented by subclasses.")

    def plot(self) -> None:
        """Plot the positions in the plan."""
        from useq._plot import plot_points

        plot_points(self)


class RelativePosition(PositionBase, _MultiPointPlan["RelativePosition"]):
    """A relative position in 3D space.

    Relative positions also support `fov_width` and `fov_height` attributes, and can
    be used to define a single field of view for a "multi-point" plan.
    """

    x: float = 0
    y: float = 0
    z: float = 0

    def __iter__(self) -> Iterator["RelativePosition"]:  # type: ignore [override]
        yield self

    def num_positions(self) -> int:
        return 1
