from enum import Enum
from typing import Final, Literal


class Axis(str, Enum):
    """Recognized useq-schema axis keys.

    Attributes
    ----------
    TIME : Literal["t"]
        Time axis.
    POSITION : Literal["p"]
        XY Stage Position axis.
    GRID : Literal["g"]
        Grid axis (usually an additional row/column iteration around a position).
    CHANNEL : Literal["c"]
        Channel axis.
    Z : Literal["z"]
        Z axis.
    """

    TIME = "t"
    POSITION = "p"
    GRID = "g"
    CHANNEL = "c"
    Z = "z"

    def __str__(self) -> Literal["t", "p", "g", "c", "z"]:
        return self.value


# note: order affects the default axis_order in MDASequence
AXES: Final[tuple[Axis, ...]] = (
    Axis.TIME,
    Axis.POSITION,
    Axis.GRID,
    Axis.CHANNEL,
    Axis.Z,
)


class RelativeTo(Enum):
    """Where the coordinates of the grid are relative to.

    Attributes
    ----------
    center : Literal['center']
        Grid is centered around the origin.
    top_left : Literal['top_left']
        Grid is positioned such that the top left corner is at the origin.
    """

    center = "center"
    top_left = "top_left"


class Shape(Enum):
    """Shape of the bounding box for random points.

    Attributes
    ----------
    ELLIPSE : Literal['ellipse']
        The bounding box is an ellipse.
    RECTANGLE : Literal['rectangle']
        The bounding box is a rectangle.
    """

    ELLIPSE = "ellipse"
    RECTANGLE = "rectangle"
