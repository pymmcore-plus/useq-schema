import warnings
from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, Generic, Optional, SupportsIndex, TypeVar

import numpy as np
from pydantic import Field, model_validator

from useq._base_model import FrozenModel, MutableModel

if TYPE_CHECKING:
    from matplotlib.axes import Axes
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

    x: float | None = None
    y: float | None = None
    z: float | None = None
    name: str | None = None
    sequence: Optional["MDASequence"] = None

    # excluded from serialization
    row: int | None = Field(default=None, exclude=True)
    col: int | None = Field(default=None, exclude=True)

    def __add__(self, other: "RelativePosition") -> "Self":
        """Add two positions together to create a new position."""
        if not isinstance(other, RelativePosition):  # pragma: no cover
            return NotImplemented
        if self.x is not None and other.x is not None:
            x = self.x + other.x
        else:
            x = self.x if other.x is None else other.x
        if self.y is not None and other.y is not None:
            y = self.y + other.y
        else:
            y = self.y if other.y is None else other.y
        if self.z is not None and other.z is not None:
            z = self.z + other.z
        else:
            z = self.z if other.z is None else other.z
        if (name := self.name) and other.name:
            name = f"{name}_{other.name}"
        kwargs = {**self.model_dump(), "x": x, "y": y, "z": z, "name": name}
        return type(self).model_construct(**kwargs)  # type: ignore [return-value]

    __radd__ = __add__

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

    @model_validator(mode="before")
    @classmethod
    def _cast(cls, value: Any) -> Any:
        if isinstance(value, (np.ndarray, tuple)):
            x = y = z = None
            if len(value) > 0:
                x = value[0]
            if len(value) > 1:
                y = value[1]
            if len(value) > 2:
                z = value[2]
            value = {"x": x, "y": y, "z": z}
        return value


class AbsolutePosition(PositionBase, FrozenModel):
    """An absolute position in 3D space."""

    @property
    def is_relative(self) -> bool:
        return False

    @model_validator(mode="after")
    def _validate_position(self) -> "Self":
        if self.sequence is None or self.sequence.grid_plan is None:
            return self
        grid = self.sequence.grid_plan
        if not grid.is_relative:
            # x/y are meaningless with an absolute sub-grid (the grid defines
            # them). Warn and clear.
            if self.x is not None or self.y is not None:
                warnings.warn(
                    f"Position x={self.x!r}, y={self.y!r} is ignored when a position "
                    f"sequence uses an absolute grid plan ({type(grid).__name__}). "
                    "Set x=None, y=None on the position to silence this warning. "
                    "In a future version this will raise an error.",
                    UserWarning,
                    stacklevel=2,
                )
                object.__setattr__(self, "x", None)
                object.__setattr__(self, "y", None)

        return self


Position = AbsolutePosition  # for backwards compatibility
PositionT = TypeVar("PositionT", bound=PositionBase)


class _MultiPointPlan(MutableModel, Generic[PositionT]):
    """Any plan that yields multiple positions."""

    fov_width: float | None = None
    fov_height: float | None = None

    @property
    def is_relative(self) -> bool:
        return True

    def __iter__(self) -> Iterator[PositionT]:  # type: ignore [override]
        raise NotImplementedError("This method must be implemented by subclasses.")

    def num_positions(self) -> int:
        raise NotImplementedError("This method must be implemented by subclasses.")

    def plot(self, *, show: bool = True) -> "Axes":
        """Plot the positions in the plan."""
        from useq._plot import plot_points

        rect = None
        if self.fov_width is not None and self.fov_height is not None:
            rect = (self.fov_width, self.fov_height)

        return plot_points(self, rect_size=rect, show=show)


class RelativePosition(PositionBase, _MultiPointPlan["RelativePosition"]):
    """A relative position in 3D space.

    Relative positions also support `fov_width` and `fov_height` attributes, and can
    be used to define a single field of view for a "multi-point" plan.
    """

    x: float = 0  # pyright: ignore[reportIncompatibleVariableOverride]
    y: float = 0  # pyright: ignore[reportIncompatibleVariableOverride]
    z: float = 0  # pyright: ignore[reportIncompatibleVariableOverride]

    def __iter__(self) -> Iterator["RelativePosition"]:  # type: ignore [override]
        yield self

    def num_positions(self) -> int:
        return 1
