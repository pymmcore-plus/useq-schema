from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Literal,
    TypeVar,
)

from pydantic import validator

if TYPE_CHECKING:
    from typing import Final

KT = TypeVar("KT")
VT = TypeVar("VT")


# could be an enum, but this more easily allows Axis.Z to be a string
class Axis:
    """Recognized axis names."""

    TIME: Final[Literal["t"]] = "t"
    POSITION: Final[Literal["p"]] = "p"
    GRID: Final[Literal["g"]] = "g"
    CHANNEL: Final[Literal["c"]] = "c"
    Z: Final[Literal["z"]] = "z"


# note: order affects the default axis_order in MDASequence
AXES: Final[tuple[str, ...]] = (
    Axis.TIME,
    Axis.POSITION,
    Axis.GRID,
    Axis.CHANNEL,
    Axis.Z,
)


def list_cast(field: str) -> classmethod:
    v = validator(field, pre=True, allow_reuse=True, check_fields=False)
    return v(list)
